"""Global test fixtures and configuration for Anima tests."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure src/ is on the Python path
_src_path = str(Path(__file__).resolve().parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


# ── Shared Mock Fixtures ─────────────────────────────────────────


@pytest.fixture
def mock_llm():
    """Mock LLM service returning canned responses."""
    mock = MagicMock()
    mock.chat_stream = AsyncMock()

    async def _stream():
        yield "mock response chunk"

    mock.chat_stream.return_value = _stream()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_tts():
    """Mock TTS service returning dummy audio bytes."""
    mock = MagicMock()
    mock.synthesize = AsyncMock(return_value=b"mock_audio_data")
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_asr():
    """Mock ASR service returning canned transcription."""
    mock = MagicMock()
    mock.transcribe = AsyncMock(return_value="mock transcription text")
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_vad():
    """Mock VAD service always detecting speech."""
    mock = MagicMock()
    mock.is_speech = AsyncMock(return_value=True)
    mock.process_audio = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_socketio():
    """Mock Socket.IO server for testing event emission."""
    mock = MagicMock()
    mock.emit = MagicMock()
    mock.enter_room = MagicMock()
    mock.leave_room = MagicMock()
    return mock


@pytest.fixture
def mock_service_context(mock_llm, mock_tts, mock_asr, mock_vad):
    """Create a ServiceContext with all external services mocked."""
    ctx = MagicMock()
    ctx.llm_engine = mock_llm
    ctx.tts_engine = mock_tts
    ctx.asr_engine = mock_asr
    ctx.vad_engine = mock_vad
    ctx.emotion_analyzer = MagicMock()
    ctx.emotion_analyzer.analyze = MagicMock(return_value="neutral")
    ctx.memory_system = MagicMock()
    ctx.memory_system.query = AsyncMock(return_value=[])
    ctx.memory_system.store_turn = AsyncMock()
    ctx.memory_system.retrieve_context = AsyncMock(return_value=[])
    ctx.close = AsyncMock()
    return ctx
