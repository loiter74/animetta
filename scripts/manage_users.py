"""Host wrapper for account recovery in Animetta's named data volume."""

from __future__ import annotations

import argparse
import getpass
import subprocess
import sys

PASSWORD_MIN_BYTES = 8
PASSWORD_MAX_BYTES = 1024


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Animetta 用户恢复工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    reset = subparsers.add_parser("reset-admin-password", help="重置管理员临时密码")
    reset.add_argument("--username", required=True)
    reset.add_argument("--enable", action="store_true", help="同时恢复已禁用的管理员")
    initial = subparsers.add_parser("ensure-admin-bootstrap", help="初始化首次登录管理员")
    initial.add_argument("--username", default="admin")
    return parser


def main() -> int:
    args = _parser().parse_args()
    password = None
    if args.command == "reset-admin-password":
        password = getpass.getpass("新临时密码：")
        confirmation = getpass.getpass("再次输入：")
        if password != confirmation:
            print("两次输入的密码不一致。", file=sys.stderr)
            return 2
    if (
        password is not None
        and not PASSWORD_MIN_BYTES <= len(password.encode("utf-8")) <= PASSWORD_MAX_BYTES
    ):
        print("密码必须为 8–1024 个 UTF-8 字节。", file=sys.stderr)
        return 2
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "animetta",
        "python",
        "-m",
        "animetta.orchestration.server.auth_admin_cli",
        args.command,
        "--username",
        str(args.username),
    ]
    if getattr(args, "enable", False):
        command.append("--enable")
    try:
        completed = subprocess.run(
            command,
            input=password + "\n" if password is not None else None,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("Docker 不可用；请先安装或启动 Docker Desktop。", file=sys.stderr)
        return 3
    if completed.returncode != 0:
        print(
            "管理员密码应用失败；请确认 Animetta 已就绪且镜像支持对应账号命令。",
            file=sys.stderr,
        )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
