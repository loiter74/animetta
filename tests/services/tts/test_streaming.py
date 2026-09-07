"""Transport-independent streaming lifecycle contracts."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from animetta.services.tts import streaming
from animetta.services.tts.remote_tts import RemoteTTSError


class PCMEngine:
    sample_rate = 24000

    def __init__(self, attempts):
        self.attempts = attempts
        self.calls = []
        self.closed = 0

    async def synthesize_stream(self, text, **kwargs):
        attempt = self.attempts[len(self.calls)]
        self.calls.append((text, kwargs.copy()))
        try:
            for item in attempt:
                if isinstance(item, Exception):
                    raise item
                if isinstance(item, asyncio.Event):
                    await item.wait()
                else:
                    yield item
        finally:
            self.closed += 1


async def run_stream(engine, emit, signal=None):
    return await streaming.synthesize_stream(
        engine,
        "hello",
        synthesis_kwargs={"voice": "fixed-voice", "emotion": "happy"},
        interrupt_signal=signal or asyncio.Event(),
        emit=emit,
        timeout_seconds=1,
    )


async def test_retry_keeps_voice_and_exposes_only_raw_pcm():
    engine = PCMEngine([[RuntimeError("before audio")], [b"\x00\x01", b"\x02\x03"]])
    emit = AsyncMock()
    result = await run_stream(engine, emit)

    assert engine.calls[0] == engine.calls[1]
    assert engine.closed == 2
    events = [call.args for call in emit.await_args_list]
    assert [event for event, _ in events] == ["start", "chunk", "chunk", "end"]
    assert events[1][1]["pcm"] == b"\x00\x01"
    assert events[2][1]["sequence"] == 1
    assert all(payload["stream_id"] == result.stream_id for _, payload in events)
    assert not any("audio_data" in payload or "message_id" in payload for _, payload in events)
    assert events[-1][1]["status"] == "completed"
    assert result.streamed and not result.interrupted
    assert 0 <= result.first_audio_ms <= result.duration_ms


async def test_remote_retries_keep_existing_backoff_and_attempt_limit(monkeypatch):
    error = RemoteTTSError("busy", category="busy", retryable=True)
    engine = PCMEngine([[error]] * 5)
    sleep = AsyncMock()
    monkeypatch.setattr(streaming.asyncio, "sleep", sleep)
    emit = AsyncMock()

    with pytest.raises(RemoteTTSError):
        await run_stream(engine, emit)

    assert [call.args[0] for call in sleep.await_args_list] == [0.25, 0.75, 1.5, 3.0]
    assert len(engine.calls) == engine.closed == 5
    emit.assert_not_awaited()


@pytest.mark.parametrize(
    "error,reason", [(RuntimeError("failed"), "provider_error"), (TimeoutError(), "timeout")]
)
async def test_failure_after_first_chunk_emits_one_terminal_without_retry(error, reason):
    engine = PCMEngine([[b"\x00\x01", error]])
    emit = AsyncMock()

    with pytest.raises(type(error)):
        await run_stream(engine, emit)

    events = [call.args for call in emit.await_args_list]
    assert [event for event, _ in events] == ["start", "chunk", "end"]
    assert events[-1][1]["status"] == "failed"
    assert events[-1][1]["reason"] == reason
    assert events[-1][1]["final_sequence"] == 0
    assert len(engine.calls) == engine.closed == 1


@pytest.mark.parametrize("chunks", [[], [b""], [b"x"], ["not pcm"]])
async def test_empty_and_invalid_pcm_never_start_delivery(chunks):
    engine = PCMEngine([chunks, chunks])
    emit = AsyncMock()
    with pytest.raises(RuntimeError):
        await run_stream(engine, emit)
    assert len(engine.calls) == engine.closed == 2
    emit.assert_not_awaited()


@pytest.mark.parametrize("caller_cancel", [False, True])
async def test_interrupt_and_call_cancellation_close_provider_and_emit_one_terminal(caller_cancel):
    blocked = asyncio.Event()
    delivered = asyncio.Event()
    signal = asyncio.Event()
    events = []
    engine = PCMEngine([[b"\x00\x01", blocked]])

    async def emit(event, payload):
        events.append((event, payload))
        if event == "chunk":
            delivered.set()

    task = asyncio.create_task(run_stream(engine, emit, signal))
    try:
        await asyncio.wait_for(delivered.wait(), timeout=1)
        if caller_cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            signal.set()
            result = await asyncio.wait_for(task, timeout=1)
            assert result.interrupted and result.streamed
        assert [event for event, _ in events] == ["start", "chunk", "end"]
        assert events[-1][1]["status"] == "cancelled"
        assert len(engine.calls) == engine.closed == 1
    finally:
        blocked.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
