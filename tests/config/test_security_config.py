from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from animetta.config.manifest import ManifestValidationError, load_effective_config
from animetta.config.security import SecurityConfig


def test_security_config_rejects_wildcard_origin() -> None:
    with pytest.raises(ValidationError, match="wildcard origins are forbidden"):
        SecurityConfig(allowed_origins=("*",))


@pytest.mark.parametrize(
    "origin",
    [
        "http://animetta.example",
        "http://1.1.1.1",
        "http://100.64.0.1",
        "http://169.254.1.1",
        "http://192.0.2.22",
        "http://172.15.255.255",
        "http://172.32.0.1",
        "http://[fd00::1]",
        "http://192.168.5.22.example",
    ],
)
def test_security_config_requires_https_for_non_local_origin(origin: str) -> None:
    with pytest.raises(ValidationError, match="must use HTTPS"):
        SecurityConfig(allowed_origins=(origin,))


@pytest.mark.parametrize(
    "origin",
    [
        "http://10.0.0.22:8000",
        "http://172.16.0.1",
        "http://172.31.255.254",
        "http://192.168.5.22",
    ],
)
def test_security_config_accepts_explicit_private_ipv4_http_origin(origin: str) -> None:
    assert SecurityConfig(allowed_origins=(origin,)).allowed_origins == (origin,)


def test_security_config_accepts_exact_https_and_loopback_http() -> None:
    config = SecurityConfig(allowed_origins=("https://animetta.example", "http://127.0.0.1:8000"))

    assert config.allowed_origins == (
        "https://animetta.example",
        "http://127.0.0.1:8000",
    )


def test_schema_v1_is_rejected_for_production(
    tmp_path,
    manifest_data,
    isolated_manifest_env,
) -> None:
    manifest_data["schema_version"] = 1
    path = tmp_path / "animetta.yaml"
    path.write_text(yaml.safe_dump(manifest_data), encoding="utf-8")
    isolated_manifest_env.setenv("ANIMETTA_HOST", "127.0.0.1")
    isolated_manifest_env.setenv("ANIMETTA_PORT", "8000")

    with pytest.raises(ManifestValidationError, match="schema v2"):
        load_effective_config(path, profile="production")


def test_production_manifest_serializes_typed_pricing_date(monkeypatch) -> None:
    env = {
        "ANIMETTA_HOST": "127.0.0.1",
        "ANIMETTA_PORT": "12394",
        "DEEPSEEK_API_KEY": "test-deepseek",
        "MIMO_API_KEY": "test-mimo",
        "DASHSCOPE_API_KEY": "test-dashscope",
        "QWEN_TTS_API_KEY": "test-qwen",
        "QWEN_HOST_TTS_URL": "http://127.0.0.1:8767",
    }
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    effective = load_effective_config(Path("config/animetta.yaml"), profile="production")

    pricing = effective.providers["llm"].declaration["pricing"]
    assert pricing["verified_on"] == "2026-08-15"
    assert effective.runtime.enable_tools is False
    assert "http://127.0.0.1:12394" in effective.security.allowed_origins
