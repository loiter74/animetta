from __future__ import annotations

import subprocess

import pytest
from dotenv import dotenv_values

from animetta.orchestration.server.auth_password import (
    INITIAL_ADMIN_PASSWORD_HASH,
    verify_password,
)
from scripts import bootstrap, runtime_lifecycle


@pytest.fixture
def installation(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    password_code = "src/animetta/orchestration/server/auth_password.py"
    (root / password_code).parent.mkdir(parents=True)
    (root / password_code).write_bytes((bootstrap.ROOT / password_code).read_bytes())
    (root / ".env.example").write_text(
        "ANIMETTA_PROFILE=production\nDEEPSEEK_API_KEY=\nQWEN_TTS_API_KEY=\n", encoding="utf-8"
    )
    monkeypatch.setattr(bootstrap, "ROOT", root)
    monkeypatch.setattr(bootstrap.os, "environ", {})
    return root, bootstrap._parser().parse_args([])


def test_first_preparation_and_repeat_preserve_credentials(installation):
    root, args = installation
    assert bootstrap.prepare_settings(args) == "admin"
    before = (root / ".env").read_bytes()
    values = dotenv_values(root / ".env")
    assert len(values["ANIMETTA_ACCESS_TOKEN"]) >= 32
    assert len(values["ANIMETTA_REDIS_PASSWORD"]) >= 32
    assert values["DEEPSEEK_API_KEY"] == values["QWEN_TTS_API_KEY"] == ""
    assert verify_password("123456", values["ANIMETTA_AUTH_PASSWORD_HASH"])
    assert "ANIMETTA_ADMIN_PASSWORD_FILE" not in values
    assert "ANIMETTA_PYTHON_EXTRAS" not in values
    assert bootstrap.prepare_settings(args) == "admin"
    assert (root / ".env").read_bytes() == before


def test_existing_service_keys_are_preserved_and_obsolete_file_is_not_read(installation):
    root, args = installation
    (root / ".env").write_text(
        "DEEPSEEK_API_KEY=existing-key\nQWEN_TTS_API_KEY=host-key\n"
        "ANIMETTA_ACCESS_TOKEN=existing-machine-token-with-32-bytes\n"
        "ANIMETTA_REDIS_PASSWORD=existing-redis-password\n"
        "ANIMETTA_ADMIN_PASSWORD_FILE=does-not-exist.txt\n",
        encoding="utf-8",
    )
    bootstrap.prepare_settings(args)
    values = dotenv_values(root / ".env")
    assert values["DEEPSEEK_API_KEY"] == "existing-key"
    assert values["QWEN_TTS_API_KEY"] == "host-key"
    assert values["ANIMETTA_ACCESS_TOKEN"] == "existing-machine-token-with-32-bytes"
    assert values["ANIMETTA_REDIS_PASSWORD"] == "existing-redis-password"
    assert "ANIMETTA_ADMIN_PASSWORD_FILE" not in values


def test_optional_selection_is_explicit_persistent_and_can_return_to_core(installation):
    root, args = installation
    args.extra = ["search", "bilibili", "search"]
    bootstrap.prepare_settings(args)
    args.extra = None
    bootstrap.prepare_settings(args)
    assert dotenv_values(root / ".env")["ANIMETTA_PYTHON_EXTRAS"] == "bilibili search"
    args.extra = []
    bootstrap.prepare_settings(args)
    assert dotenv_values(root / ".env")["ANIMETTA_PYTHON_EXTRAS"] == ""


def test_stale_process_hash_cannot_rotate_initial_credential(installation, monkeypatch):
    root, args = installation
    bootstrap.prepare_settings(args)
    original = (root / ".env").read_bytes()
    monkeypatch.setenv("ANIMETTA_AUTH_PASSWORD_HASH", "stale-process-hash")
    bootstrap.prepare_settings(args)
    assert (root / ".env").read_bytes() == original
    assert bootstrap.os.environ["ANIMETTA_AUTH_PASSWORD_HASH"] == INITIAL_ADMIN_PASSWORD_HASH


def test_start_delegates_one_waiting_lifecycle_and_initializes_admin_after_ready(monkeypatch):
    from animetta.config import manifest

    args = bootstrap._parser().parse_args([])
    monkeypatch.setattr(bootstrap, "prepare_settings", lambda _args: "admin")
    monkeypatch.setenv("ANIMETTA_PROFILE", "production")
    monkeypatch.setattr(runtime_lifecycle, "_compose_environment", lambda **_kw: {})
    monkeypatch.setattr(
        manifest, "load_build_capabilities", lambda *_a, **_kw: {"ANIMETTA_EARTH_ENABLED": "false"}
    )
    calls = []
    monkeypatch.setattr(runtime_lifecycle, "main", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(
        bootstrap.subprocess,
        "run",
        lambda command, **_kw: calls.append(command) or subprocess.CompletedProcess(command, 0),
    )
    assert bootstrap.start(args) == 0
    assert calls[0] == ["anima-up", "--wait"]
    assert calls[1][-3:] == ["ensure-admin-bootstrap", "--username", "admin"]
    calls.clear()
    monkeypatch.setattr(runtime_lifecycle, "main", lambda argv: calls.append(argv) or 1)
    assert bootstrap.start(args) == 1
    assert calls == [["anima-up", "--wait"]]


def test_controller_cache_still_checks_actual_imports(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("pydantic==2.12.5\n", encoding="utf-8")
    launcher = tmp_path / "launcher"
    launcher.mkdir()
    python = launcher / "python"
    python.touch()
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setattr(bootstrap, "LAUNCHER", launcher)
    monkeypatch.setattr(bootstrap, "launcher_python", lambda: python)
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(bootstrap.subprocess, "run", run)
    bootstrap.ensure_launcher()
    install = calls[-1]
    assert install[-4:] == list(bootstrap.CONTROLLER_PACKAGES)
    assert "--isolated" in install
    assert install[install.index("--index-url") + 1] == "https://pypi.org/simple"
    assert "-r" not in install
    calls.clear()
    bootstrap.ensure_launcher()
    assert len(calls) == 1 and "-I" in calls[0]
