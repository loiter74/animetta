from __future__ import annotations

from animetta.runtime.provider_pool import ProviderPool

"""ProviderPool lifecycle contracts use independent fixtures and mocked engines."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def pool():
    return ProviderPool()


async def test_legacy_facade_forwards_without_owning_state(pool, monkeypatch):
    from animetta.core.service_pool import ServicePool
    from animetta.runtime import provider_pool

    monkeypatch.setattr(provider_pool, "default_provider_pool", pool)
    engine = MagicMock(close=AsyncMock())
    pool._llm = engine
    pool._ready = True
    assert ServicePool.get_context()["llm_engine"] is engine
    assert ServicePool.is_ready() is True
    assert not any(name.startswith("_init") or name == "_state" for name in vars(ServicePool))
    await ServicePool.shutdown()
    engine.close.assert_awaited_once()
    assert ServicePool.is_ready() is False


# ── Helpers ─────────────────────────────────────────────────────────


def _mock_context_base(mock_llm, mock_tts, mock_asr, **kwargs):
    """Build a MagicMock ServiceContext with the given engines and optional extras.

    ``load_from_config`` and ``close`` are set as ``AsyncMock`` so the
    caller can ``await`` them — this mirrors the real ``ServiceContext``
    API used inside ``ServicePool.init()``.

    Per-session services (VAD, memory, emotion, audio) default to
    ``None`` so tests can explicitly opt in when they want to verify
    cleanup logic.
    """
    ctx = MagicMock()
    ctx.llm_engine = mock_llm
    ctx.tts_engine = mock_tts
    ctx.asr_engine = mock_asr
    ctx.load_from_config = AsyncMock()
    ctx.close_session_resources = AsyncMock()

    per_session_defaults = {
        "vad_engine": None,
        "memory_system": None,
        "emotion_analyzer": None,
        "audio_processor": None,
    }
    for key, default in per_session_defaults.items():
        setattr(ctx, key, kwargs.get(key, default))
    return ctx


# ═══════════════════════════════════════════════════════════════════════
# Tests for init()
# ═══════════════════════════════════════════════════════════════════════


class TestInit:
    """ServicePool.init() — lifecycle start."""

    # ── Happy path ──────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_creates_service_context(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """init() creates a ServiceContext and calls load_from_config."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        MockServiceContext.assert_called_once_with(model_manager=None)
        mock_ctx.load_from_config.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_extracts_shared_engines(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """After init, _llm / _tts / _asr point to the engines from ServiceContext."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        assert pool._llm is mock_llm
        assert pool._tts is mock_tts
        assert pool._asr is mock_asr

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_sets_ready_flag(self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr):
        """After successful init, _ready is True."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        assert pool._ready is True

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_sets_session_id(self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr):
        """The ServiceContext gets session_id == '__pool__'."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        assert mock_ctx.session_id == "__pool__"

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_forwards_model_manager(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """model_manager is passed through to ServiceContext."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        MockServiceContext.return_value = mock_ctx
        manager = MagicMock()

        await pool.init(MagicMock(), model_manager=manager)

        MockServiceContext.assert_called_once_with(model_manager=manager)

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_selftest_waits_for_warmup_and_llm_connectivity(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """Self-test keeps the production-like DeepSeek readiness contract."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        mock_ctx.wait_for_llm_connectivity = AsyncMock(
            return_value={"state": "ready", "ready": True, "reason": None}
        )
        MockServiceContext.return_value = mock_ctx
        manager = MagicMock()
        manager.warmup = AsyncMock()
        config = MagicMock()
        config.profile = "selftest"

        with patch.object(pool, "_compute_engine_readiness", return_value=True):
            await pool.init(config, model_manager=manager)

        manager.warmup.assert_awaited_once_with()
        mock_ctx.wait_for_llm_connectivity.assert_awaited_once_with()

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_keeps_ctx_alive(self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr):
        """_ctx is stored on the class so shared engines stay in memory."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        assert pool._ctx is mock_ctx

    # ── Idempotency / early return ──────────────────────────────

    @pytest.mark.asyncio
    async def test_skip_when_already_ready(self, pool):
        """When _ready is True, init() returns immediately without creating ServiceContext."""
        pool._ready = True

        with patch("animetta.runtime.provider_pool.ServiceContext") as MockServiceContext:
            await pool.init(MagicMock())

        MockServiceContext.assert_not_called()

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_idempotent_second_call_does_not_create_new_context(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """Calling init() twice does not replace the first ServiceContext."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())
        first_ctx = pool._ctx

        MockServiceContext.reset_mock()

        await pool.init(MagicMock())

        MockServiceContext.assert_not_called()
        assert pool._ctx is first_ctx

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_idempotent_engines_preserved(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """Engines from the first init remain after a second call."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())
        first_llm, first_tts, first_asr = pool._llm, pool._tts, pool._asr

        MockServiceContext.reset_mock()

        await pool.init(MagicMock())

        assert pool._llm is first_llm
        assert pool._tts is first_tts
        assert pool._asr is first_asr

    # ── Error handling ──────────────────────────────────────────

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_error_closes_context(self, MockServiceContext, pool):
        """When load_from_config raises, init() calls ctx.close_session_resources() and re-raises."""
        mock_ctx = _mock_context_base(None, None, None)
        mock_ctx.load_from_config.side_effect = RuntimeError("boom")
        MockServiceContext.return_value = mock_ctx

        with pytest.raises(RuntimeError, match="boom"):
            await pool.init(MagicMock())

        mock_ctx.close_session_resources.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_error_does_not_set_ready(self, MockServiceContext, pool):
        """When load_from_config fails, _ready stays False."""
        mock_ctx = _mock_context_base(None, None, None)
        mock_ctx.load_from_config.side_effect = ValueError("fail")
        MockServiceContext.return_value = mock_ctx

        with pytest.raises(ValueError):
            await pool.init(MagicMock())

        assert pool._ready is False

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_error_does_not_set_engines(self, MockServiceContext, pool):
        """After a failed init, _llm / _tts / _asr remain None."""
        mock_ctx = _mock_context_base(None, None, None)
        mock_ctx.load_from_config.side_effect = ValueError("fail")
        MockServiceContext.return_value = mock_ctx

        with pytest.raises(ValueError):
            await pool.init(MagicMock())

        assert pool._llm is None
        assert pool._tts is None
        assert pool._asr is None

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_error_closes_partially_initialized_shared_engines(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """Engines opened before a failed init are closed instead of leaked."""
        mock_ctx = _mock_context_base(None, None, None)

        async def fail_after_shared_engines(_config, **_kwargs):
            mock_ctx.llm_engine = mock_llm
            mock_ctx.tts_engine = mock_tts
            mock_ctx.asr_engine = mock_asr
            raise RuntimeError("boom")

        mock_ctx.load_from_config.side_effect = fail_after_shared_engines
        MockServiceContext.return_value = mock_ctx

        with pytest.raises(RuntimeError, match="boom"):
            await pool.init(MagicMock())

        mock_ctx.close_session_resources.assert_awaited_once()
        mock_llm.close.assert_awaited_once()
        mock_tts.close.assert_awaited_once()
        mock_asr.close.assert_awaited_once()
        assert pool._llm is None
        assert pool._tts is None
        assert pool._asr is None
        assert pool._ready is False

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_error_preserves_original_exception_when_engine_close_fails(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """Cleanup failures do not hide the original initialization error."""
        mock_ctx = _mock_context_base(None, None, None)
        mock_llm.close.side_effect = RuntimeError("close failed")

        async def fail_after_shared_engines(_config, **_kwargs):
            mock_ctx.llm_engine = mock_llm
            mock_ctx.tts_engine = mock_tts
            mock_ctx.asr_engine = mock_asr
            raise RuntimeError("load failed")

        mock_ctx.load_from_config.side_effect = fail_after_shared_engines
        MockServiceContext.return_value = mock_ctx

        with pytest.raises(RuntimeError, match="load failed"):
            await pool.init(MagicMock())

        mock_llm.close.assert_awaited_once()
        mock_tts.close.assert_awaited_once()
        mock_asr.close.assert_awaited_once()
        assert mock_ctx.llm_engine is None
        assert mock_ctx.tts_engine is None
        assert mock_ctx.asr_engine is None

    # ── Per-session service cleanup ─────────────────────────────

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_closes_vad_engine(self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr):
        """VAD (per-session) engine is closed during init."""
        mock_vad = MagicMock()
        mock_vad.close = AsyncMock()
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr, vad_engine=mock_vad)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        mock_vad.close.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_closes_memory_system(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """Memory system (per-session) is shut down during init."""
        mock_memory = MagicMock()
        mock_memory.shutdown = AsyncMock()
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr, memory_system=mock_memory)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        mock_memory.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_clears_emotion_analyzer(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """Emotion analyzer reference is set to None after extraction."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr, emotion_analyzer=MagicMock())
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        assert mock_ctx.emotion_analyzer is None

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_clears_audio_processor(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """Audio processor reference is set to None after extraction."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr, audio_processor=MagicMock())
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        assert mock_ctx.audio_processor is None

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_skips_vad_close_when_none(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """When VAD engine is None, init does not crash."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr, vad_engine=None)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        assert pool._ready is True

    @pytest.mark.asyncio
    @patch("animetta.runtime.provider_pool.ServiceContext")
    async def test_skips_memory_close_when_none(
        self, MockServiceContext, pool, mock_llm, mock_tts, mock_asr
    ):
        """When memory system is None, init does not crash."""
        mock_ctx = _mock_context_base(mock_llm, mock_tts, mock_asr, memory_system=None)
        MockServiceContext.return_value = mock_ctx

        await pool.init(MagicMock())

        assert pool._ready is True


# ═══════════════════════════════════════════════════════════════════════
# Tests for get_context()
# ═══════════════════════════════════════════════════════════════════════


class TestGetContext:
    """ServicePool.get_context() — returns engine dict for cache loading."""

    def test_returns_engine_dict_when_ready(self, pool, mock_llm, mock_tts, mock_asr):
        """When ready, returns a dict with llm_engine, tts_engine, asr_engine."""
        pool._ready = True
        pool._llm = mock_llm
        pool._tts = mock_tts
        pool._asr = mock_asr

        result = pool.get_context()

        assert result == {
            "llm_engine": mock_llm,
            "tts_engine": mock_tts,
            "asr_engine": mock_asr,
        }

    def test_returns_empty_dict_when_not_ready(self, pool):
        """When _ready is False, returns an empty dict."""
        result = pool.get_context()

        assert result == {}

    def test_selftest_rejects_unready_pool_instead_of_initializing_per_session(self, pool):
        """Self-test must not allocate a second set of real provider engines."""
        pool._runtime_config = MagicMock(profile="selftest")

        with pytest.raises(RuntimeError, match="Real-profile ServicePool is not ready"):
            pool.get_context()


# ═══════════════════════════════════════════════════════════════════════
# Tests for shutdown()
# ═══════════════════════════════════════════════════════════════════════


class TestShutdown:
    """ServicePool.shutdown() — lifecycle end."""

    @pytest.mark.asyncio
    async def test_closes_llm(self, pool, mock_llm):
        """LLM engine is closed on shutdown."""
        pool._ready = True
        pool._llm = mock_llm

        await pool.shutdown()

        mock_llm.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_closes_tts(self, pool, mock_tts):
        """TTS engine is closed on shutdown."""
        pool._ready = True
        pool._tts = mock_tts

        await pool.shutdown()

        mock_tts.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_closes_asr(self, pool, mock_asr):
        """ASR engine is closed on shutdown."""
        pool._ready = True
        pool._asr = mock_asr

        await pool.shutdown()

        mock_asr.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resets_engines_to_none(self, pool, mock_llm, mock_tts, mock_asr):
        """Engine references are set to None after shutdown."""
        pool._ready = True
        pool._llm = mock_llm
        pool._tts = mock_tts
        pool._asr = mock_asr

        await pool.shutdown()

        assert pool._llm is None

    @pytest.mark.asyncio
    async def test_resets_ready_to_false(self, pool, mock_llm):
        """_ready is set to False after shutdown."""
        pool._ready = True
        pool._llm = mock_llm

        await pool.shutdown()

        assert pool._ready is False

    @pytest.mark.asyncio
    async def test_resets_ctx_to_none(self, pool, mock_llm):
        """_ctx is set to None after shutdown."""
        pool._ready = True
        pool._llm = mock_llm
        pool._ctx = MagicMock()

        await pool.shutdown()

        assert pool._ctx is None

    @pytest.mark.asyncio
    async def test_safe_when_not_ready(self, pool):
        """shutdown() is a no-op when _ready is False."""
        pool._ready = False

        await pool.shutdown()

        assert pool._ready is False

    @pytest.mark.asyncio
    async def test_safe_with_partial_none_engines(self, pool):
        """shutdown() handles some engines being None without error."""
        pool._ready = True
        pool._llm = None
        pool._tts = None
        pool._asr = None

        await pool.shutdown()

        assert pool._ready is False


# ═══════════════════════════════════════════════════════════════════════
# Tests for is_ready()
# ═══════════════════════════════════════════════════════════════════════


class TestIsReady:
    """ServicePool.is_ready() — status check."""

    def test_returns_true_when_ready(self, pool):
        pool._ready = True
        assert pool.is_ready() is True

    def test_returns_false_when_not_ready(self, pool):
        assert pool.is_ready() is False


class TestApplyLlmConfig:
    """ServicePool.apply_llm_config() — runtime lightweight updates."""

    def test_updates_pooled_llm_engine(self, pool):
        class Engine:
            model = "old-model"
            temperature = 0.1
            top_p = 0.2
            max_tokens = 64

        class Config:
            model = "new-model"
            temperature = 0.7
            top_p = 0.8
            max_tokens = 256

        engine = Engine()
        pool._llm = engine

        pool.apply_llm_config(Config())

        assert engine.model == "old-model"
        assert engine.temperature == 0.7
        assert engine.top_p == 0.8
        assert engine.max_tokens == 256

    def test_updates_pooled_llm_prompt_without_recreating_shared_engines(self, pool):
        class Engine:
            model = "old-model"
            temperature = 0.1
            top_p = 0.2
            max_tokens = 64

            def __init__(self):
                self.system_prompt = "old prompt"

            def set_system_prompt(self, prompt: str) -> None:
                self.system_prompt = prompt

        class Config:
            model = "new-model"
            temperature = 0.7
            top_p = 0.8
            max_tokens = 256

        engine = Engine()
        tts = object()
        asr = object()
        pool._llm = engine
        pool._tts = tts
        pool._asr = asr

        pool.apply_llm_config(Config(), system_prompt="new prompt")

        assert pool._llm is engine
        assert pool._tts is tts
        assert pool._asr is asr
        assert engine.model == "old-model"
        assert engine.temperature == 0.7
        assert engine.top_p == 0.8
        assert engine.max_tokens == 256
        assert engine.system_prompt == "new prompt"


def test_provider_pool_instances_own_isolated_runtime_state() -> None:
    first = ProviderPool()
    second = ProviderPool()
    config = object()

    first.configure_runtime(config)

    assert first is not second
    assert first._runtime_config is config
    assert second._runtime_config is None
