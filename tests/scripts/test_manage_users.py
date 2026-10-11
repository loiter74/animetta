from __future__ import annotations

from subprocess import CompletedProcess

from scripts import manage_users


def test_initial_admin_command_does_not_prompt_or_pass_a_secret(monkeypatch) -> None:
    monkeypatch.setattr(manage_users.sys, "argv", ["manage_users.py", "ensure-admin-bootstrap"])
    monkeypatch.setattr(
        manage_users.getpass,
        "getpass",
        lambda _prompt: (_ for _ in ()).throw(AssertionError("prompted")),
    )
    calls = []
    monkeypatch.setattr(
        manage_users.subprocess,
        "run",
        lambda command, **kw: calls.append((command, kw)) or CompletedProcess(command, 0),
    )
    assert manage_users.main() == 0
    command, kwargs = calls[0]
    assert command[-3:] == ["ensure-admin-bootstrap", "--username", "admin"]
    assert "123456" not in command
    assert kwargs["input"] is None


def test_reset_admin_password_uses_hidden_stdin_not_process_arguments(
    monkeypatch,
) -> None:
    password = "private-recovery-password"
    prompts = iter((password, password))
    monkeypatch.setattr(manage_users.getpass, "getpass", lambda _prompt: next(prompts))
    monkeypatch.setattr(
        manage_users.sys,
        "argv",
        [
            "manage_users.py",
            "reset-admin-password",
            "--username",
            "admin",
            "--enable",
        ],
    )
    run_calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        run_calls.append((command, kwargs))
        return CompletedProcess(command, 0)

    monkeypatch.setattr(manage_users.subprocess, "run", run)

    assert manage_users.main() == 0
    command, kwargs = run_calls[0]
    assert password not in command
    assert kwargs["input"] == f"{password}\n"
    assert "env" not in kwargs
    assert command[-3:] == ["--username", "admin", "--enable"]


def test_reset_admin_password_rejects_mismatched_hidden_inputs(monkeypatch) -> None:
    prompts = iter(("first-password", "second-password"))
    monkeypatch.setattr(manage_users.getpass, "getpass", lambda _prompt: next(prompts))
    monkeypatch.setattr(
        manage_users.sys,
        "argv",
        ["manage_users.py", "reset-admin-password", "--username", "admin"],
    )

    def fail_run(*_args, **_kwargs):
        raise AssertionError("must not run")

    monkeypatch.setattr(manage_users.subprocess, "run", fail_run)

    assert manage_users.main() == 2
