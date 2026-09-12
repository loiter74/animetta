from __future__ import annotations

import argparse
import copy
import json
import subprocess
import time

import pytest

from scripts import runtime_lifecycle
from tooling import runtime_startup
from tooling.execution_feedback.lifecycle import freeze_lifecycle_plan
from tooling.quality.image_fingerprint import image_fingerprint
from tooling.quality.models import DockerImageInputs
from tooling.runtime_startup import (
    BUILD_LABEL,
    RUNTIME_LABEL,
    StartupContext,
    development_environment,
    write_state,
)


@pytest.mark.parametrize("explicit_https", [None, "", "http://preferred.invalid:9090"])
def test_compose_inherits_system_proxy_and_preserves_explicit_environment(
    tmp_path, monkeypatch, explicit_https
):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    monkeypatch.setattr(runtime_lifecycle, "ROOT", tmp_path)
    monkeypatch.setattr(
        runtime_startup,
        "getproxies",
        lambda: {
            "http": "http://system.invalid:7890",
            "https": "http://system.invalid:7890",
            "no": "*.internal",
        },
    )
    if explicit_https is not None:
        monkeypatch.setenv("HTTPS_PROXY", explicit_https)
    environment = runtime_lifecycle._compose_environment()
    assert environment["HTTP_PROXY"] == "http://system.invalid:7890"
    assert environment["HTTPS_PROXY"] == (
        "http://system.invalid:7890" if explicit_https is None else explicit_https
    )
    assert set(environment["NO_PROXY"].split(",")) >= {
        "*.internal",
        "localhost",
        "127.0.0.1",
        "::1",
        "host.docker.internal",
    }


def test_source_identity_detects_content_additions_and_deletions_without_mtime(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    file = source / "app.py"
    file.write_text("a = 1", encoding="utf-8")
    inputs = DockerImageInputs(paths=("src/**",), exclude_paths=("**/__pycache__/**",))
    first = image_fingerprint(tmp_path, inputs)
    stat = file.stat()
    file.write_text("a = 2", encoding="utf-8")
    import os

    os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert image_fingerprint(tmp_path, inputs)[0] != first[0]
    file.write_text("a = 1", encoding="utf-8")
    extra = source / "untracked.py"
    extra.write_text("", encoding="utf-8")
    assert image_fingerprint(tmp_path, inputs)[1] == 2
    assert image_fingerprint(tmp_path, inputs)[0] != first[0]
    extra.unlink()
    assert image_fingerprint(tmp_path, inputs) == first


def test_image_identity_is_portable_and_excludes_secrets_and_runtime_cache(tmp_path):
    inputs = DockerImageInputs(paths=("src/**",), exclude_paths=("**/__pycache__/**",))
    identities = []
    for directory in ("before", "after"):
        root = tmp_path / directory
        source = root / "src"
        source.mkdir(parents=True)
        (source / "app.py").write_bytes(b"a = 1\n")
        (source / ".env").write_text(directory, encoding="utf-8")
        cache = source / "__pycache__"
        cache.mkdir()
        (cache / "app.pyc").write_text(directory, encoding="utf-8")
        identities.append(image_fingerprint(root, inputs))
    assert identities[0] == identities[1]
    assert identities[0][1] == 1


def _context(tmp_path):
    context = StartupContext(
        tmp_path,
        {
            "ANIMETTA_RUNTIME_FINGERPRINT": "runtime-app",
            "ANIMETTA_REDIS_FINGERPRINT": "runtime-redis",
        },
    )
    context.fingerprints = {"animetta": "source-a"}
    context.configuration = {
        "services": {"animetta": {"image": "app:local"}, "redis": {"image": "redis:8"}}
    }
    return context


@pytest.mark.parametrize("label", [None, "old-schema", "source-b", "source-a"])
def test_only_current_image_label_can_hit(tmp_path, monkeypatch, label):
    context = _context(tmp_path)
    monkeypatch.setattr(
        context,
        "command",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            json.dumps([{"Id": "sha256:a", "Config": {"Labels": {BUILD_LABEL: label}}}]),
            "",
        ),
    )
    assert context.images_match() is (label == "source-a")


def test_missing_image_forces_build(tmp_path, monkeypatch):
    context = _context(tmp_path)
    monkeypatch.setattr(
        context,
        "command",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", "missing"),
    )
    assert not context.images_match()


def test_ready_false_cannot_be_overridden_by_a_generic_ok_status():
    assert not runtime_lifecycle._valid_http_body(
        "http://localhost/ready", '{"status":"ok","ready":false}'
    )
    assert runtime_lifecycle._valid_http_body("http://localhost/ready", '{"ready":true}')


@pytest.mark.parametrize("mutation", ["none", "image", "configuration", "health", "stopped", "oom"])
def test_container_reuse_requires_current_identity_and_health(tmp_path, monkeypatch, mutation):
    context = _context(tmp_path)
    containers = [
        {
            "Image": f"sha256:{name}",
            "RestartCount": 0,
            "State": {"Status": "running", "Health": {"Status": "healthy"}},
            "Config": {
                "Labels": {
                    "com.docker.compose.service": name,
                    RUNTIME_LABEL: f"runtime-{'app' if name == 'animetta' else 'redis'}",
                }
            },
        }
        for name in ("animetta", "redis")
    ]
    if mutation == "image":
        containers[0]["Image"] = "sha256:old"
    elif mutation == "configuration":
        containers[0]["Config"]["Labels"][RUNTIME_LABEL] = "old"
    elif mutation == "health":
        containers[0]["State"]["Health"]["Status"] = "unhealthy"
    elif mutation == "stopped":
        containers[0]["State"]["Status"] = "exited"
    elif mutation == "oom":
        containers[0]["State"]["OOMKilled"] = True

    def command(*args, **kwargs):
        if args[:3] == ("docker", "compose", "ps"):
            result = "one\ntwo"
        elif args[:2] == ("docker", "inspect"):
            result = json.dumps(containers)
        else:
            result = json.dumps([{"Id": "sha256:animetta"}, {"Id": "sha256:redis"}])
        return subprocess.CompletedProcess(args, 0, result, "")

    monkeypatch.setattr(context, "command", command)
    assert context.containers_match() is (mutation == "none")


def test_configuration_change_invalidates_only_affected_service(tmp_path, monkeypatch):
    config = {
        "services": {
            "animetta": {
                "image": "app",
                "build": {"context": str(tmp_path), "dockerfile": "Dockerfile"},
                "environment": {"KEY": "old"},
            },
            "redis": {"image": "redis", "environment": {"PASSWORD": "unchanged"}},
        }
    }
    contexts = []
    for value in ("old", "new"):
        config["services"]["animetta"]["environment"]["KEY"] = value
        context = _context(tmp_path)
        monkeypatch.setattr(context, "current_fingerprints", lambda: {"animetta": "a" * 64})

        def command(*args, **kwargs):
            return subprocess.CompletedProcess(
                args, 0, "linux" if args[1] == "info" else json.dumps(config), ""
            )

        monkeypatch.setattr(context, "command", command)
        context.prepare()
        contexts.append(copy.deepcopy(context.environment))
    assert contexts[0]["ANIMETTA_REDIS_FINGERPRINT"] == contexts[1]["ANIMETTA_REDIS_FINGERPRINT"]
    assert (
        contexts[0]["ANIMETTA_RUNTIME_FINGERPRINT"] != contexts[1]["ANIMETTA_RUNTIME_FINGERPRINT"]
    )
    assert contexts[0]["ANIMETTA_BUILD_FINGERPRINT"] == contexts[1]["ANIMETTA_BUILD_FINGERPRINT"]


def test_development_does_not_trust_inherited_watch_build_label(tmp_path, monkeypatch):
    context = _context(tmp_path)
    context.development = True
    context.fingerprints["frontend"] = "front-a"
    context.configuration["services"]["frontend"] = {"image": "front"}
    images = [
        {"Id": "sha256:a", "Config": {"Labels": {BUILD_LABEL: "source-a"}}},
        {"Id": "sha256:f", "Config": {"Labels": {BUILD_LABEL: "front-a"}}},
    ]
    monkeypatch.setattr(
        context,
        "command",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, json.dumps(images), ""),
    )
    assert not context.images_match()
    assert context.images_match(attest_build=True)
    assert context.images_match()
    images[1]["Id"] = "sha256:watch-rebuilt"
    assert not context.images_match()


def test_development_and_shutdown_keep_isolated_target_and_host_models(tmp_path):
    result = development_environment(
        tmp_path, {"COMPOSE_PROJECT_NAME": "formal", "ANIMETTA_IMAGE": "formal:image"}
    )
    assert result["COMPOSE_PROJECT_NAME"] == "formal-dev"
    assert result["ANIMETTA_IMAGE"] != "formal:image"
    assert result["ANIMETTA_DEV_PORT"] == "3000"
    assert result["ANIMETTA_DEV_BACKEND_PORT"] == "12395"
    plan = freeze_lifecycle_plan("anima-dev-down", input_fingerprint="a" * 64)
    assert [step.id for step in plan.steps] == ["development-watch-stop", "animetta-cleanup"]
    plan = freeze_lifecycle_plan("anima-dev", input_fingerprint="a" * 64)
    assert next(step for step in plan.steps if step.id == "animetta-build").command[-2:] == (
        "animetta",
        "frontend",
    )
    assert any(step.id == "development-watch" for step in plan.steps)


def test_formal_and_development_port_overrides_do_not_cross(tmp_path):
    environment = {
        "ANIMETTA_HTTP_PORT": "80",
        "ANIMETTA_DEV_PORT": "3001",
        "ANIMETTA_DEV_BACKEND_PORT": "12396",
    }
    assert runtime_lifecycle._http_base_url(environment) == "http://localhost"
    development = development_environment(tmp_path, environment)
    assert runtime_lifecycle._http_base_url(development) == "http://localhost:3001"
    assert development["ANIMETTA_PORT"] == "12396"
    assert development["COMPOSE_PROJECT_NAME"] == tmp_path.name.lower() + "-dev"


@pytest.mark.parametrize("codes", [(2, 2, 0), (2, 1)])
def test_wait_reuses_one_run_and_stops_at_terminal_failure(tmp_path, monkeypatch, codes):
    monkeypatch.setattr(runtime_lifecycle, "ROOT", tmp_path)
    monkeypatch.setattr(
        runtime_lifecycle,
        "_compose_environment",
        lambda **kwargs: {"ANIMETTA_PROFILE": "production"},
    )
    monkeypatch.setattr(
        runtime_lifecycle, "_bounded_input_fingerprint", lambda *args, **kwargs: "a" * 64
    )
    monkeypatch.setattr(runtime_lifecycle.time, "sleep", lambda seconds: None)
    pending = iter(codes)
    runs = []

    async def operation(*args, **kwargs):
        runs.append(kwargs["run_id"])
        return next(pending)

    monkeypatch.setattr(runtime_lifecycle, "run_bounded_operation", operation)
    assert (
        runtime_lifecycle.main(["anima-up", "--wait", "--artifacts-root", str(tmp_path / "runs")])
        == codes[-1]
    )
    assert len(runs) == len(codes)
    assert len(set(runs)) == 1


def test_duplicate_click_reuses_the_completed_inflight_result(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_lifecycle, "ROOT", tmp_path)
    monkeypatch.setattr(
        runtime_lifecycle,
        "_compose_environment",
        lambda **kwargs: {"ANIMETTA_PROFILE": "production"},
    )
    monkeypatch.setattr(
        runtime_lifecycle, "_bounded_input_fingerprint", lambda *args, **kwargs: "a" * 64
    )
    write_state(
        tmp_path / "pending/anima-up.json",
        {
            "fingerprint": "a" * 64,
            "rebuild": False,
            "exit_code": 0,
            "finished_at": time.time(),
            "run_id": "one",
        },
    )
    args = argparse.Namespace(
        operation="anima-up", image=None, run_id=None, rebuild=False, artifacts_root=tmp_path
    )
    assert runtime_lifecycle._run_cli(args, requested_at=0) == 0
