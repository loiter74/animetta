"""Tests for TTS synthesis node."""

import pytest
from unittest.mock import AsyncMock
from langgraph.types import RunnableConfig

from anima.orchestration.graph.state import create_initial_state


class TestTTSNode:
    """TTS node: text-to-speech synthesis."""

    def _make_state(session_id="test", response_text=""):
        state = create_initial_state(session_id=session_id)
        state["response_text"] = response_text
        return state

    @pytest.mark.asyncio
    async def test_empty_text_skips_tts(self):
        """Empty response_text should skip TTS and return None."""
        from anima.orchestration.graph.tts_node import tts_node

        state = self._make_state(response_text="")
        result = await tts_node(state)
        assert result["tts_audio"] is None

    @pytest.mark.asyncio
    async def test_no_service_context_returns_error(self):
        """Missing service_context returns error."""
        from anima.orchestration.graph.tts_node import tts_node

        state = self._make_state(response_text="Hello world")
        config = RunnableConfig(configurable={})
        result = await tts_node(state, config)
        assert result.get("error") is not None
        assert result["tts_audio"] is None

    @pytest.mark.asyncio
    async def test_no_tts_engine_skips(self, mock_service_context):
        """Service context without tts_engine skips TTS."""
        from anima.orchestration.graph.tts_node import tts_node

        ctx = mock_service_context
        ctx.tts_engine = None

        state = self._make_state(response_text="Hello world")
        config = RunnableConfig(
            configurable={"service_context": ctx}
        )
        result = await tts_node(state, config)
        assert result["tts_audio"] is None

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio_bytes(self, mock_service_context):
        """TTS engine returns audio bytes, stored in state."""
        from anima.orchestration.graph.tts_node import tts_node

        mock_service_context.tts_engine.synthesize = AsyncMock(
            return_value=b"fake_audio_bytes"
        )

        state = self._make_state(response_text="Hello world")
        config = RunnableConfig(
            configurable={"service_context": mock_service_context}
        )
        result = await tts_node(state, config)
        assert result["tts_audio"] == b"fake_audio_bytes"
