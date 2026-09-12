"""Content-aware Compose startup and ownership of the development watcher."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.request import getproxies

from tooling.execution_feedback.lifecycle import BuildStepController, LeasedSubprocessBuildDriver
from tooling.execution_feedback.models import ActionResult, FeedbackStatus, ResourceIdentity
from tooling.quality.hashing import canonical_json_hash
from tooling.quality.image_fingerprint import image_fingerprint
from tooling.quality.manifest import load_catalog

BUILD_LABEL = "org.animetta.build-fingerprint"
RUNTIME_LABEL = "org.animetta.runtime-fingerprint"
RUNTIME_VARIABLES = {
    "animetta": "ANIMETTA_RUNTIME_FINGERPRINT",
    "redis": "ANIMETTA_REDIS_FINGERPRINT",
    "frontend": "ANIMETTA_FRONTEND_FINGERPRINT",
}


def proxy_environment() -> dict[str, str]:
    """Expose the user's existing proxy to CLI clients that ignore Windows settings."""
    proxies = getproxies()
    environment = {}
    for scheme in ("http", "https", "all"):
        name = f"{scheme.upper()}_PROXY"
        if name in os.environ:
            environment[name] = os.environ[name]
        elif proxies.get(scheme):
            environment[name] = proxies[scheme]
    if environment:
        bypass = os.environ.get("NO_PROXY", proxies.get("no", ""))
        hosts = [host.strip() for host in bypass.split(",") if host.strip()]
        hosts.extend(("localhost", "127.0.0.1", "::1", "host.docker.internal"))
        environment["NO_PROXY"] = ",".join(dict.fromkeys(hosts))
    return environment


def write_state(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextlib.contextmanager
def operation_lock(path: Path) -> Iterator[None]:
    """An OS lock releases on process death; never guess ownership from a PID file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        while True:
            try:
                handle.seek(0)
                if sys.platform == "win32":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, BlockingIOError):
                time.sleep(1)
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle, fcntl.LOCK_UN)


def target_key(root: Path, environment: dict[str, str]) -> str:
    return canonical_json_hash(
        {
            "root": str(root.resolve()),
            "project": environment.get("COMPOSE_PROJECT_NAME", root.name.lower()),
            "files": environment.get("COMPOSE_FILE", "docker-compose.yml"),
        }
    )[:20]


def development_environment(root: Path, environment: dict[str, str]) -> dict[str, str]:
    result = dict(environment)
    project = result.get("COMPOSE_PROJECT_NAME", root.name.lower())
    if not project.endswith("-dev"):
        project += "-dev"
    result.update(
        COMPOSE_PROJECT_NAME=project,
        COMPOSE_FILE=str(root / "docker-compose.dev.yml"),
        ANIMETTA_IMAGE=f"animetta:{project}",
        ANIMETTA_FRONTEND_IMAGE=f"animetta:{project}-frontend",
        ANIMETTA_DEV_PORT=result.get("ANIMETTA_DEV_PORT", "3000"),
        ANIMETTA_DEV_BACKEND_PORT=result.get("ANIMETTA_DEV_BACKEND_PORT", "12395"),
        ANIMETTA_HTTP_PORT=result.get("ANIMETTA_DEV_PORT", "3000"),
        ANIMETTA_PORT=result.get("ANIMETTA_DEV_BACKEND_PORT", "12395"),
    )
    return result


@dataclass
class StartupContext:
    root: Path
    environment: dict[str, str]
    development: bool = False
    force_build: bool = False
    fingerprints: dict[str, str] = field(default_factory=dict)
    configuration: dict = field(default_factory=dict)

    def command(self, *arguments: str, required: bool = True) -> subprocess.CompletedProcess[str]:
        environment = {**os.environ, **self.environment}
        result = subprocess.run(
            arguments,
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        if required and result.returncode:
            # Compose's resolved configuration can contain credentials. Never echo it.
            raise RuntimeError(f"{' '.join(arguments[:3])} failed (exit {result.returncode})")
        return result

    @property
    def services(self) -> tuple[str, ...]:
        return ("animetta", "frontend") if self.development else ("animetta",)

    @property
    def state_root(self) -> Path:
        return self.root / "artifacts/runtime-targets" / target_key(self.root, self.environment)

    @property
    def build_command(self) -> tuple[str, ...]:
        return ("docker", "compose", "build", *self.services)

    def current_fingerprints(self) -> dict[str, str]:
        scope = load_catalog(self.root / "tooling/quality.yml").catalog.docker_scopes["animetta"]
        selected = (
            scope.development_inputs if self.development else {"animetta": scope.image_inputs}
        )
        if not all(selected.values()):
            raise RuntimeError("the quality catalog does not declare image inputs")
        return {name: image_fingerprint(self.root, inputs)[0] for name, inputs in selected.items()}

    def prepare(self) -> None:
        if self.command("docker", "info", "--format", "{{.OSType}}").stdout.strip() != "linux":
            raise RuntimeError("Animetta requires the Linux Docker engine")
        if self.development:
            version = (
                self.command("docker", "compose", "version", "--short").stdout.strip().lstrip("v")
            )
            parts = tuple(int(item) for item in version.split("-")[0].split(".")[:2])
            if parts < (2, 32):
                raise RuntimeError("Compose Watch requires Docker Compose 2.32 or later")
        self.fingerprints = self.current_fingerprints()
        self.environment["ANIMETTA_BUILD_FINGERPRINT"] = self.fingerprints["animetta"]
        if self.development:
            self.environment["ANIMETTA_FRONTEND_BUILD_FINGERPRINT"] = self.fingerprints["frontend"]
        self.configuration = json.loads(
            self.command("docker", "compose", "config", "--format", "json").stdout
        )
        services = self.configuration["services"]
        for name, service in services.items():
            material = {
                key: value for key, value in service.items() if key not in {"build", "labels"}
            }
            material["labels"] = {
                key: value
                for key, value in service.get("labels", {}).items()
                if key != RUNTIME_LABEL
            }
            if name in RUNTIME_VARIABLES:
                self.environment[RUNTIME_VARIABLES[name]] = canonical_json_hash(material)
        for name in self.services:
            build = services[name].get("build", {})
            if (
                Path(build.get("context", "")).resolve() != self.root.resolve()
                or build.get("dockerfile", "Dockerfile") != "Dockerfile"
            ):
                raise RuntimeError(
                    "source startup requires this checkout's Dockerfile and build context"
                )

    def images_match(self, *, attest_build: bool = False) -> bool:
        tags = [self.configuration["services"][name]["image"] for name in self.services]
        result = self.command("docker", "image", "inspect", *tags, required=False)
        if result.returncode:
            return False
        images = json.loads(result.stdout)
        matching = all(
            image.get("Config", {}).get("Labels", {}).get(BUILD_LABEL) == self.fingerprints[name]
            for name, image in zip(self.services, images, strict=True)
        )
        if not matching or not self.development:
            return matching
        # Watch rebuilds inherit the old build arguments. An image label alone
        # therefore cannot attest to a development image's actual inputs.
        attestation = {
            name: {"id": image["Id"], "fingerprint": self.fingerprints[name]}
            for name, image in zip(self.services, images, strict=True)
        }
        path = self.state_root / "images.json"
        if attest_build:
            write_state(path, attestation)
        try:
            return json.loads(path.read_text(encoding="utf-8")) == attestation
        except (OSError, ValueError):
            return False

    def containers_match(self) -> bool:
        services = self.configuration["services"]
        ids = self.command(
            "docker", "compose", "ps", "--all", "--quiet", required=False
        ).stdout.split()
        if not ids:
            return False
        inspected = self.command("docker", "inspect", *ids, required=False)
        if inspected.returncode:
            return False
        containers = {
            item["Config"]["Labels"].get("com.docker.compose.service"): item
            for item in json.loads(inspected.stdout)
        }
        if set(containers) != set(services):
            return False
        images = self.command(
            "docker",
            "image",
            "inspect",
            *(service["image"] for service in services.values()),
            required=False,
        )
        if images.returncode:
            return False
        for (name, service), image in zip(services.items(), json.loads(images.stdout), strict=True):
            container = containers[name]
            state = container.get("State", {})
            if (
                state.get("Status") != "running"
                or state.get("Health", {}).get("Status") != "healthy"
            ):
                return False
            if (
                container.get("Image") != image["Id"]
                or container.get("RestartCount", 0)
                or state.get("OOMKilled")
            ):
                return False
            if (
                container["Config"]["Labels"].get(RUNTIME_LABEL)
                != self.environment[RUNTIME_VARIABLES[name]]
            ):
                return False
        return True

    def assert_current_images(self, *, attest_build: bool = False) -> None:
        if self.current_fingerprints() != self.fingerprints:
            raise RuntimeError("build inputs changed during startup; start a new run")
        if not self.images_match(attest_build=attest_build):
            raise RuntimeError("built image identity does not match the frozen source inputs")

    def _watch_driver(self) -> LeasedSubprocessBuildDriver:
        return LeasedSubprocessBuildDriver(
            workspace_root=self.root,
            artifacts_root=self.state_root,
            receipt_path=self.state_root / "watch-receipt.json",
            environment=self.environment,
        )

    def stop_watch(self) -> None:
        path = self.state_root / "watch.json"
        if not path.exists():
            return
        identity = ResourceIdentity.model_validate(
            json.loads(path.read_text(encoding="utf-8"))["identity"]
        )
        driver = self._watch_driver()
        driver.terminate(identity)
        path.unlink(missing_ok=True)

    def start_watch(self) -> str:
        path = self.state_root / "watch.json"
        driver = self._watch_driver()
        digest = canonical_json_hash(
            {"configuration": self.configuration, "environment": self.environment}
        )
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            identity = ResourceIdentity.model_validate(saved["identity"])
            observation = driver.inspect(identity)
            if (
                observation.running
                and observation.identity == identity
                and saved["digest"] == digest
            ):
                return "reused"
            self.stop_watch()
        (self.state_root / "watch.log").unlink(missing_ok=True)
        launch = driver.launch(("docker", "compose", "watch", "--no-up"), log_path="watch.log")
        write_state(path, {"identity": launch.identity.model_dump(mode="json"), "digest": digest})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if not driver.inspect(launch.identity).running:
                path.unlink(missing_ok=True)
                raise RuntimeError(f"Compose Watch exited; inspect {self.state_root / 'watch.log'}")
            contents = (self.state_root / "watch.log").read_text(encoding="utf-8", errors="replace")
            if "Watch enabled" in contents or "Watch is enabled" in contents:
                return "started"
            time.sleep(0.5)
        self.stop_watch()
        raise RuntimeError(
            f"Compose Watch did not confirm readiness; inspect {self.state_root / 'watch.log'}"
        )


class CachedBuildController:
    """Keep the existing process lease, with a content-verified fast path."""

    def __init__(self, context: StartupContext, delegate: BuildStepController) -> None:
        self.context = context
        self.delegate = delegate
        self.started = delegate.has_lease()

    def run(self, *, now: datetime) -> ActionResult:
        if not self.started and not self.context.force_build and self.context.images_match():
            self.context.assert_current_images()
            return ActionResult(
                status=FeedbackStatus.PASSED,
                progress_summary="Reused images with matching source content",
                next_action="check the current runtime",
            )
        self.started = True
        result = self.delegate.run(now=now)
        if result.status is FeedbackStatus.PASSED:
            self.context.assert_current_images(attest_build=True)
        return result

    def cancel(self) -> None:
        if self.started:
            self.delegate.cancel()
