"""Tests for output distribution node — Socket.IO + memory storage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langgraph.types import RunnableConfig

from anima.orchestration.graph.state import create_initial_state


class TestOutputNode:
    """Output node: emit events via Socket.IO and store to memory."""

    @pytest.mark.asyncio
    async def test_no_socketio_returns_error(self):
        """Without Socket.IO in config, returns error."""
        from anima.orchestration.graph.output_node import output_node

        state = create_initial_state(session_id="test")
        config = RunnableConfig(configurable={})
        result = await output_node(state, config)
        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_emits_conversation_start_and_end(self, mock_socketio, mock_service_context):
        """Always emits conversation-start and conversation-end control signals."""
        from anima.orchestration.graph.output_node import output_node

        state = create_initial_state(session_id="test")
        state["response_text"] = "Hello"
        config = RunnableConfig(configurable={
            "socketio": mock_socketio,
            "service_context": mock_service_context,
        })
        await output_node(state, config)

        # Check control signals
        control_calls = [
            c for c in mock_socketio.emit.call_args_list
            if c[0][0] == "control"
        ]
        signals = [c[0][1]["signal"] for c in control_calls]
        assert "conversation-start" in signals
        assert "conversation-end" in signals

    @pytest.mark.asyncio
    async def test_emits_text_when_response_exists(self, mock_socketio, mock_service_context):
        """response_text triggers sentence events."""
        from anima.orchestration.graph.output_node import output_node

        state = create_initial_state(session_id="test")
        state["response_text"] = "Hello world"
        config = RunnableConfig(configurable={
            "socketio": mock_socketio,
            "service_context": mock_service_context,
        })
        await output_node(state, config)

        sentence_calls = [
            c for c in mock_socketio.emit.call_args_list
            if c[0][0] == "sentence"
        ]
        assert len(sentence_calls) >= 1
        # First sentence call should have the text
        assert sentence_calls[0][0][1]["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_emits_expression_for_emotion(self, mock_socketio, mock_service_context):
        """Emotion in state triggers expression event + Live2D motion."""
        from anima.orchestration.graph.output_node import output_node

        state = create_initial_state(session_id="test")
        state["response_text"] = "I'm happy"
        state["emotion"] = "happy"
        config = RunnableConfig(configurable={
            "socketio": mock_socketio,
            "service_context": mock_service_context,
        })
        await output_node(state, config)

        expr_calls = [
            c for c in mock_socketio.emit.call_args_list
            if c[0][0] == "expression"
        ]
        assert len(expr_calls) >= 1
        assert expr_calls[0][0][1]["emotion"] == "happy"

        action_calls = [
            c for c in mock_socketio.emit.call_args_list
            if c[0][0] == "live2d.action"
        ]
        assert len(action_calls) >= 1
        assert action_calls[0][0][1]["index"] == 3  # happy -> 3

    @pytest.mark.asyncio
    async def test_memory_storage_called(self, mock_socketio, mock_service_context):
        """Memory system store_turn should be called with conversation data."""
        from anima.orchestration.graph.output_node import output_node

        mock_service_context.memory_system.store_turn = AsyncMock()

        state = create_initial_state(
            session_id="test",
            user_text="Hi there",
            user_name="Alice",
        )
        state["response_text"] = "Hello Alice!"
        state["emotion"] = "neutral"
        config = RunnableConfig(configurable={
            "socketio": mock_socketio,
            "service_context": mock_service_context,
        })
        await output_node(state, config)

        # Verify memory storage was called
        mock_service_context.memory_system.store_turn.assert_called_once()
        call_arg = mock_service_context.memory_system.store_turn.call_args[0][0]
        assert call_arg.user_input == "Hi there"
        assert call_arg.agent_response == "Hello Alice!"
