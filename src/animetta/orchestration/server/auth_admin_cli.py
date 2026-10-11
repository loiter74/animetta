"""Container-side account recovery commands for the persistent auth volume."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from animetta.utils.env_helper import get_data_dir

from .auth_password import (
    INITIAL_ADMIN_PASSWORD,
    INITIAL_ADMIN_PASSWORD_HASH,
    hash_password,
    validate_password,
    verify_password,
)
from .auth_session import RedisAuthSessionStore
from .auth_user import AuthUserStore


async def reset_admin_password(
    username: str, *, enable: bool, password: str, initial_only: bool = False
) -> int:
    """Reset one administrator credential without accepting the secret in argv."""
    if initial_only:
        if password != INITIAL_ADMIN_PASSWORD:
            raise ValueError("initial password must match the public bootstrap credential")
    else:
        validate_password(password)
    store = AuthUserStore(
        get_data_dir() / "auth.db",
        bootstrap_username=os.environ.get("ANIMETTA_AUTH_USERNAME", "admin"),
        bootstrap_password_hash=os.environ.get("ANIMETTA_AUTH_PASSWORD_HASH", ""),
    )
    health = await store.start()
    if not health.available:
        print(json.dumps({"ok": False, "error_code": "AUTH_USER_STORE_UNAVAILABLE"}))
        return 2
    try:
        account = await store.get_by_username(username)
        if account is None:
            print(json.dumps({"ok": False, "error_code": "USER_NOT_FOUND"}))
            return 3
        if account.role != "admin":
            print(json.dumps({"ok": False, "error_code": "ACCOUNT_ADMIN_REQUIRED"}))
            return 4
        if initial_only and not account.enabled:
            print(json.dumps({"ok": False, "error_code": "ACCOUNT_DISABLED"}))
            return 4
        if initial_only and (
            not account.must_change_password
            or account.credential_version > 1
            or verify_password(password, account.password_hash)
        ):
            print(
                json.dumps(
                    {
                        "ok": True,
                        "changed": False,
                        "password_change_required": account.must_change_password,
                    }
                )
            )
            return 0
        account = await store.update_password(
            account.id,
            password_hash=INITIAL_ADMIN_PASSWORD_HASH if initial_only else hash_password(password),
            must_change_password=True,
            actor_user_id=account.id,
            action="bootstrap_admin_initialized" if initial_only else "local_admin_password_reset",
            enable=True if enable else None,
        )
        session_store = RedisAuthSessionStore(
            os.environ.get("ANIMETTA_REDIS_URL"),
            ttl_seconds=8 * 3600,
        )
        session_health = await session_store.start()
        sessions_cleaned = session_health.available
        if sessions_cleaned:
            try:
                await session_store.revoke_user(account.id)
            except Exception:
                sessions_cleaned = False
        await session_store.close()
        print(
            json.dumps(
                {
                    "ok": True,
                    "username": account.username,
                    "enabled": account.enabled,
                    "password_change_required": True,
                    "changed": True,
                    "sessions_cleaned": sessions_cleaned,
                }
            )
        )
        return 0
    finally:
        await store.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Animetta 本地管理员恢复")
    subparsers = parser.add_subparsers(dest="command", required=True)
    reset = subparsers.add_parser("reset-admin-password", help="重置管理员临时密码")
    reset.add_argument("--username", required=True)
    reset.add_argument("--enable", action="store_true")
    initial = subparsers.add_parser("ensure-admin-bootstrap", help="初始化尚未改密的管理员")
    initial.add_argument("--username", default="admin")
    return parser


def main() -> int:
    args = _parser().parse_args()
    initial_only = args.command == "ensure-admin-bootstrap"
    password = INITIAL_ADMIN_PASSWORD if initial_only else sys.stdin.readline().rstrip("\r\n")
    if not password:
        print(json.dumps({"ok": False, "error_code": "PASSWORD_REQUIRED"}))
        return 5
    try:
        return asyncio.run(
            reset_admin_password(
                str(args.username),
                enable=bool(getattr(args, "enable", False)),
                password=password,
                initial_only=initial_only,
            )
        )
    except ValueError:
        print(json.dumps({"ok": False, "error_code": "PASSWORD_POLICY_VIOLATION"}))
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
