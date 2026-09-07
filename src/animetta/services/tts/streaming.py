"""Provider-neutral PCM streaming, retry and cancellation lifecycle."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from loguru import logger

from .remote_tts import RemoteTTSError

StreamEvent = Literal["start", "chunk", "end"]
StreamCallback = Callable[[StreamEvent, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class StreamResult:
    stream_id: str
    streamed: bool
    interrupted: bool
    duration_ms: float
    first_audio_ms: float = 0.0
    rtf: float = 0.0


_INTERRUPT_CLEANUP_GRACE_SECONDS = 0.2

_RETRYABLE_REMOTE_STREAM_DELAYS_SECONDS = (0.25, 0.75, 1.5, 3.0)


class _UserInterruptedError(Exception):
    """Internal control flow for a prompt user interruption."""


def _consume_background_task(task: asyncio.Task[Any]) -> None:
    """Consume a detached cleanup result so it cannot warn at shutdown."""
    with suppress(BaseException):
        task.result()


async def _settle_cancelled_task(task: asyncio.Task[Any]) -> None:
    """Cancel provider I/O without allowing cleanup to hold the turn lock."""
    if task.done():
        _consume_background_task(task)
        return
    task.cancel()
    done, _ = await asyncio.wait({task}, timeout=_INTERRUPT_CLEANUP_GRACE_SECONDS)
    if task in done:
        _consume_background_task(task)
    else:
        task.add_done_callback(_consume_background_task)


async def _close_async_stream(
    stream: Any | None,
    *,
    timeout_seconds: float | None = None,
) -> None:
    """Finalize a provider iterator before retrying or returning."""
    if stream is None:
        return
    close = getattr(stream, "aclose", None)
    if close is None:
        return

    async def _run_close() -> None:
        await close()

    if timeout_seconds is None:
        try:
            await _run_close()
        except (Exception, asyncio.CancelledError):
            logger.debug("[TTSStream] Provider stream cleanup was unavailable")
        return

    task = asyncio.create_task(_run_close())
    done, _ = await asyncio.wait({task}, timeout=timeout_seconds)
    if task in done:
        _consume_background_task(task)
    else:
        task.add_done_callback(_consume_background_task)


async def _next_chunk_or_interrupt(
    stream: Any,
    interrupt_signal: asyncio.Event,
    *,
    timeout_seconds: float,
) -> bytes:
    """Wait for the next provider chunk while remaining promptly interruptible."""
    if interrupt_signal.is_set():
        raise _UserInterruptedError

    async def _read_next() -> bytes:
        return await anext(stream)

    next_task = asyncio.create_task(_read_next())
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError("TTS stream idle timeout")
            done, _ = await asyncio.wait(
                {next_task},
                timeout=min(remaining, 0.05),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if interrupt_signal.is_set():
                raise _UserInterruptedError
            if done:
                return next_task.result()
    finally:
        pending = [next_task] if not next_task.done() else []
        if pending:
            await _settle_cancelled_task(next_task)


async def synthesize_stream(
    engine: Any,
    text: str,
    *,
    synthesis_kwargs: dict[str, Any],
    interrupt_signal: asyncio.Event,
    emit: StreamCallback,
    timeout_seconds: float,
    started: float | None = None,
) -> StreamResult:
    """Consume PCM while callbacks own transport, identity and presentation metadata."""
    started = time.perf_counter() if started is None else started
    stream_id = str(uuid4())
    sequence = -1
    stream_started = False
    first_audio_at: float | None = None
    pcm_bytes = 0

    async def finish(status: str, reason: str | None = None) -> None:
        payload: dict[str, Any] = {
            "stream_id": stream_id,
            "final_sequence": sequence,
            "status": status,
        }
        if reason is not None:
            payload["reason"] = reason
        await emit("end", payload)

    async def finish_after_error(status: str, reason: str) -> None:
        if stream_started:
            try:
                await finish(status, reason)
            except Exception:
                logger.warning("[TTSStream] Failed to emit terminal stream event")

    retry_delays = _RETRYABLE_REMOTE_STREAM_DELAYS_SECONDS
    for attempt in range(len(retry_delays) + 1):
        stream: Any | None = None
        try:
            stream = aiter(engine.synthesize_stream(text, **synthesis_kwargs))
            while True:
                try:
                    chunk = await _next_chunk_or_interrupt(
                        stream, interrupt_signal, timeout_seconds=timeout_seconds
                    )
                except StopAsyncIteration:
                    break
                if not isinstance(chunk, bytes) or not chunk or len(chunk) % 2:
                    raise RuntimeError("TTS stream returned invalid PCM")
                pcm_bytes += len(chunk)
                if not stream_started:
                    first_audio_at = time.perf_counter()
                    await emit(
                        "start",
                        {
                            "stream_id": stream_id,
                            "format": "pcm_s16le",
                            "sample_rate": int(getattr(engine, "sample_rate", 24000)),
                            "channels": 1,
                        },
                    )
                    stream_started = True
                sequence += 1
                await emit("chunk", {"stream_id": stream_id, "sequence": sequence, "pcm": chunk})
            if interrupt_signal.is_set():
                raise _UserInterruptedError
            if sequence < 0:
                raise RuntimeError("TTS stream completed without audio")
        except (_UserInterruptedError, asyncio.CancelledError) as exc:
            await _close_async_stream(stream, timeout_seconds=_INTERRUPT_CLEANUP_GRACE_SECONDS)
            await finish_after_error("cancelled", "cancelled")
            if isinstance(exc, asyncio.CancelledError):
                raise
            return StreamResult(
                stream_id, stream_started, True, (time.perf_counter() - started) * 1000
            )
        except Exception as exc:
            await _close_async_stream(stream)
            retryable_remote = isinstance(exc, RemoteTTSError) and exc.retryable
            should_retry = not stream_started and (
                attempt == 0 or (retryable_remote and attempt < len(retry_delays))
            )
            if should_retry:
                logger.warning("[TTSStream] Failed before first chunk; retrying same voice")
                if retryable_remote:
                    await asyncio.sleep(retry_delays[attempt])
                continue
            await finish_after_error(
                "failed", "timeout" if isinstance(exc, TimeoutError) else "provider_error"
            )
            raise
        else:
            await _close_async_stream(stream)
            await finish("completed")
            completed_at = time.perf_counter()
            audio_seconds = pcm_bytes / (2 * int(getattr(engine, "sample_rate", 24000)))
            return StreamResult(
                stream_id,
                True,
                False,
                (completed_at - started) * 1000,
                ((first_audio_at or completed_at) - started) * 1000,
                (completed_at - started) / audio_seconds if audio_seconds > 0 else 0.0,
            )
    raise AssertionError("stream retry loop must return or raise")
