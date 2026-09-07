from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from animetta.config.manifest import EffectiveConfig, load_effective_config
from animetta.orchestration.server.session import SessionManager
from animetta.orchestration.server.websocket import create_server
from animetta.runtime.provider_pool import ProviderPool

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def effective_config(monkeypatch: pytest.MonkeyPatch) -> EffectiveConfig:
    for name in (
        "ANIMETTA_CONFIG",
        "ANIMETTA_LLM",
        "ANIMETTA_ASR",
        "ANIMETTA_TTS",
        "ANIMETTA_VAD",
        "ANIMETTA_LOCAL_LLM",
        "VITE_API_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANIMETTA_HOST", "127.0.0.1")
    monkeypatch.setenv("ANIMETTA_PORT", "12394")
    return load_effective_config(
        PROJECT_ROOT / "config" / "animetta.yaml",
        profile="test",
    )


def test_run_002_server_holders_share_one_effective_config_object(
    effective_config: EffectiveConfig,
) -> None:
    server = create_server(effective_config)

    assert server.config is effective_config
    assert server.runtime_reloader is not None
    assert server.runtime_reloader.config is effective_config
    assert server.route_handlers is not None
    assert server.route_handlers.global_config is effective_config
    assert server.provider_pool._runtime_config is effective_config
    assert server.asgi_app.state.runtime_context.config is effective_config
    assert server.inspection_runtime().readiness_snapshot().profile == "test"


def test_two_servers_reload_only_their_own_application_context(effective_config):
    first, second = create_server(effective_config), create_server(effective_config)
    changed = effective_config.model_copy(deep=True)
    first.set_config(changed)
    assert first.asgi_app.state.runtime_context is first
    assert second.asgi_app.state.runtime_context is second
    assert first.provider_pool is not second.provider_pool
    assert first.config is changed
    assert first.provider_pool._runtime_config is changed
    assert second.config is effective_config
    assert second.provider_pool._runtime_config is effective_config
    first.auth_session_readiness["ready"] = True
    assert second.auth_session_readiness["ready"] is False


@pytest.mark.asyncio
async def test_run_003_new_session_inherits_config_version_and_hash(
    effective_config: EffectiveConfig,
) -> None:
    pool = ProviderPool()
    manager = SessionManager(provider_pool=pool)
    pooled = {
        "llm_engine": object(),
        "tts_engine": object(),
        "asr_engine": object(),
    }

    with (
        patch.object(pool, "get_context", return_value=pooled),
        patch(
            "animetta.runtime.session_context.ServiceContext.init_vad",
            new=AsyncMock(),
        ),
        patch(
            "animetta.runtime.session_context.ServiceContext.init_memory",
            new=AsyncMock(),
        ),
        patch(
            "animetta.runtime.session_context.ServiceContext.init_emotion_analyzer",
            new=AsyncMock(),
        ),
    ):
        context = await manager.get_or_create_context(
            "session-1",
            effective_config,
            AsyncMock(),
        )

    assert context.config is effective_config
    assert context.runtime_config_version == effective_config.version
    assert context.runtime_config_hash == effective_config.effective_hash
