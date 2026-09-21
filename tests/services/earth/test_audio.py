"""Bounded decoder lifecycle and real MiMo payload construction, without network."""

import asyncio
import base64
import io
import json
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from animetta.services.asr.mimo_asr import MimoASR
from animetta.services.earth.audio import MAX_PCM_BYTES, normalize_asr_audio
from animetta.services.earth.exploration import ExplorationService


def decoder(monkeypatch, pcm: bytes | None):
    stdout = asyncio.StreamReader()
    if pcm is not None:
        stdout.feed_data(pcm)
        stdout.feed_eof()
    process = SimpleNamespace(
        stdin=SimpleNamespace(write=Mock(), drain=AsyncMock(), close=Mock()),
        stdout=stdout,
        returncode=None,
    )

    async def wait():
        if process.returncode is None:
            process.returncode = 0
        return process.returncode

    def kill():
        process.returncode = -9

    process.wait = AsyncMock(side_effect=wait)
    process.kill = Mock(side_effect=kill)
    create = AsyncMock(return_value=process)
    monkeypatch.setattr("animetta.services.earth.audio.asyncio.create_subprocess_exec", create)
    return process, create


@pytest.mark.parametrize("audio_format", ["wav", "webm", "ogg"])
async def test_decoder_wraps_pcm_and_limits_demuxer_protocols(monkeypatch, audio_format) -> None:
    pcm = b"\x01\x00" * 1600
    process, create = decoder(monkeypatch, pcm)
    result = await normalize_asr_audio(b"encoded-container", audio_format)
    with wave.open(io.BytesIO(result)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 16000)
        assert wav.readframes(wav.getnframes()) == pcm
    args = create.call_args.args
    assert args[args.index("-protocol_whitelist") + 1] == "pipe,fd"
    assert args[args.index("-t") + 1] == "60"
    assert args[args.index("-f") + 1] == audio_format
    process.stdin.write.assert_called_once_with(b"encoded-container")
    process.stdin.close.assert_called_once()
    process.kill.assert_not_called()
    assert process.wait.await_count >= 1


async def test_output_limit_kills_and_reaps_decoder(monkeypatch) -> None:
    process, _ = decoder(monkeypatch, b"x" * (MAX_PCM_BYTES + 1))
    with pytest.raises(ValueError, match="output limit"):
        await normalize_asr_audio(b"container", "webm")
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()


async def test_cancellation_kills_and_reaps_decoder(monkeypatch) -> None:
    process, create = decoder(monkeypatch, None)
    task = asyncio.create_task(normalize_asr_audio(b"container", "ogg"))
    while not create.await_count:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()
    assert process.returncode == -9


async def test_decoder_error_never_produces_fake_wav(monkeypatch) -> None:
    process, _ = decoder(monkeypatch, b"")
    process.returncode = 1
    with pytest.raises(ValueError, match="Invalid decoded"):
        await normalize_asr_audio(b"corrupt", "webm")
    assert process.wait.await_count >= 1


async def test_timeout_kills_and_reaps_decoder(monkeypatch) -> None:
    process, _ = decoder(monkeypatch, None)
    timeout = asyncio.timeout
    monkeypatch.setattr("animetta.services.earth.audio.asyncio.timeout", lambda _: timeout(0))
    with pytest.raises(TimeoutError):
        await normalize_asr_audio(b"container", "webm")
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()


async def test_earth_sends_real_decoded_wav_through_mimo_adapter(monkeypatch) -> None:
    pcm = b"\x01\x00" * 1600
    decoder(monkeypatch, pcm)
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "杭州"}}]})

    async with httpx.AsyncClient(
        base_url="https://example.test/v1", transport=httpx.MockTransport(respond)
    ) as client:
        asr = MimoASR(api_key="test-only", http_client=client)
        service = ExplorationService(
            SimpleNamespace(search=AsyncMock(return_value=[])), clock=lambda: 100, asr=asr
        )
        state = await service.apply(
            {}, {"operation": "open", "conversation_id": "private", "control_revision": 0}
        )
        state = await service.apply(
            state,
            {
                "operation": "audio",
                "audio_data": base64.b64encode(b"webm-container").decode(),
                "format": "webm",
                "control_revision": 1,
            },
        )
        assert state["transcript"][0] == {"role": "user", "text": "杭州"}
    data = json.loads(requests[0].content)["messages"][0]["content"][0]["input_audio"]["data"]
    assert data.startswith("data:audio/wav;base64,")
    with wave.open(io.BytesIO(base64.b64decode(data.split(",", 1)[1]))) as wav:
        assert wav.getnframes() == 1600
        assert wav.readframes(1600) == pcm
