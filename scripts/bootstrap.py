"""Prepare the small host controller and delegate startup to the canonical lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import secrets
import subprocess
import sys
import venv
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / ".venv" / "launcher"
CONTROLLER_PACKAGES = ("pydantic", "pyyaml", "python-dotenv", "loguru")
CONTROLLER_INDEX = "https://pypi.org/simple"
EXTRAS = ("bilibili", "search", "memory-semantic")
CANONICAL_PYTHON = (3, 13)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def launcher_python() -> Path:
    """Locate the isolated controller without modifying an application/model venv."""
    return LAUNCHER / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def ensure_launcher() -> Path:
    """Install the constrained controller only when its inputs or imports change."""
    interpreter = launcher_python()
    fingerprint = hashlib.sha256(
        (ROOT / "requirements.txt").read_bytes()
        + json.dumps((sys.version_info[:2], CONTROLLER_PACKAGES, CONTROLLER_INDEX)).encode()
    ).hexdigest()
    receipt = LAUNCHER / "controller-inputs.sha256"
    if not interpreter.is_file():
        venv.EnvBuilder(with_pip=True).create(LAUNCHER)
    probe = subprocess.run(
        [str(interpreter), "-I", "-c", "import pydantic, yaml, dotenv, loguru"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if (
        not receipt.is_file()
        or receipt.read_text(encoding="ascii") != fingerprint
        or probe.returncode
    ):
        print("正在准备轻量启动工具（应用依赖安装在 Docker 中）……", flush=True)
        subprocess.run(
            [
                str(interpreter),
                "-m",
                "pip",
                "--isolated",
                "install",
                "--disable-pip-version-check",
                "--index-url",
                CONTROLLER_INDEX,
                "-c",
                str(ROOT / "requirements.txt"),
                *CONTROLLER_PACKAGES,
            ],
            cwd=ROOT,
            check=True,
        )
        receipt.write_text(fingerprint, encoding="ascii")
    return interpreter


def prepare_settings(args: argparse.Namespace) -> str:
    """Prepare bootstrap credentials while account passwords remain in the user store."""
    from dotenv import dotenv_values, set_key, unset_key

    # Reuse the standalone stdlib password contract without importing the ASGI package.
    password_contract = runpy.run_path(
        str(ROOT / "src/animetta/orchestration/server/auth_password.py")
    )
    env_file = ROOT / ".env"
    if not env_file.exists():
        env_file.write_bytes((ROOT / ".env.example").read_bytes())
    values = dotenv_values(env_file)

    def selected(name: str, fallback: str = "") -> str:
        return os.environ.get(name, values.get(name) or fallback)

    changes = {
        "ANIMETTA_AUTH_USERNAME": selected("ANIMETTA_AUTH_USERNAME", "admin"),
        "ANIMETTA_AUTH_PASSWORD_HASH": password_contract["INITIAL_ADMIN_PASSWORD_HASH"],
        "ANIMETTA_ACCESS_TOKEN": selected("ANIMETTA_ACCESS_TOKEN") or secrets.token_urlsafe(32),
        "ANIMETTA_REDIS_PASSWORD": selected("ANIMETTA_REDIS_PASSWORD") or secrets.token_urlsafe(32),
    }
    if args.extra is not None:
        changes["ANIMETTA_PYTHON_EXTRAS"] = " ".join(sorted(set(args.extra)))
    # Remove only the superseded local password-file input; never read that file.
    if "ANIMETTA_ADMIN_PASSWORD_FILE" in values:
        unset_key(str(env_file), "ANIMETTA_ADMIN_PASSWORD_FILE")
    os.environ.pop("ANIMETTA_ADMIN_PASSWORD_FILE", None)
    for name, value in changes.items():
        if values.get(name) != value:
            set_key(str(env_file), name, value, quote_mode="always")
    environment = {**dotenv_values(env_file), **os.environ, **changes}
    os.environ.update(
        {name: value for name, value in environment.items() if isinstance(value, str)}
    )
    return changes["ANIMETTA_AUTH_USERNAME"]


def start(args: argparse.Namespace) -> int:
    """Use existing locks, resume checkpoints, build cache and strict readiness."""
    from animetta.config.manifest import load_build_capabilities
    from scripts import runtime_lifecycle

    if args.image:
        runtime_lifecycle._validate_deploy_image(args.image)
        if args.extra is not None:
            raise ValueError("发布镜像不能追加依赖；请选择源码启动并使用 --extra。")
    username = prepare_settings(args)
    runtime_lifecycle._compose_environment(operation="anima-up")
    profile = os.environ.get("ANIMETTA_PROFILE", "production")
    if profile != "production":
        raise ValueError("默认启动入口要求 production；开发/测试使用 runtime_lifecycle.py。")
    build = load_build_capabilities(ROOT / "config/animetta.yaml", profile=profile)
    print(f"管理员账号：{username}；首次登录密码：123456，登录后必须设置新密码。", flush=True)
    print(
        f"可选 Python 依赖：{os.environ.get('ANIMETTA_PYTHON_EXTRAS') or '无'}；地图：{build['ANIMETTA_EARTH_ENABLED']}",
        flush=True,
    )
    if args.prepare_only:
        print("准备完成；请在 .env 填写所选 LLM 与现有 Qwen 服务的密钥，再运行同一入口。")
        return 0
    command = ["anima-deploy", "--image", args.image] if args.image else ["anima-up"]
    command.append("--wait")
    if args.rebuild:
        command.append("--rebuild")
    if args.run_id:
        command.extend(("--run-id", args.run_id))
    if args.artifacts_root:
        command.extend(("--artifacts-root", str(args.artifacts_root)))
    result = runtime_lifecycle.main(command)
    if result:
        return result
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/manage_users.py"),
            "ensure-admin-bootstrap",
            "--username",
            username,
        ],
        cwd=ROOT,
        check=False,
    ).returncode
    if not result and args.open:
        import webbrowser

        environment = runtime_lifecycle._compose_environment(image=args.image)
        webbrowser.open(f"{runtime_lifecycle._http_base_url(environment)}/live.html")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="一条命令准备并启动 Animetta 核心")
    parser.add_argument("--prepare-only", action="store_true", help="只准备工具和本地配置")
    parser.add_argument("--image", help="使用已发布 GHCR 镜像，跳过源码构建")
    parser.add_argument(
        "--extra",
        nargs="*",
        choices=EXTRAS,
        help="选择完整可选依赖集合；不传则保留，空参数恢复核心",
    )
    parser.add_argument("--open", action="store_true", help="就绪后打开直播页")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--wait", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--artifacts-root", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if sys.version_info < CANONICAL_PYTHON:
        print("请使用 Python 3.13：py -3.13 scripts/bootstrap.py", file=sys.stderr)
        return 2
    arguments = list(argv if argv is not None else sys.argv[1:])
    args = _parser().parse_args(arguments)
    try:
        if not args.worker:
            interpreter = ensure_launcher()
            return subprocess.run(
                [str(interpreter), str(Path(__file__).resolve()), *arguments, "--worker"],
                cwd=ROOT,
                check=False,
            ).returncode
        return start(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        print("启动准备失败；请检查 Python、Docker、.env 及上方生命周期回执。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
