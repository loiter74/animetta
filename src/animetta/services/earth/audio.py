"""Reuse the application's audio analysis without retaining private audio files."""

import asyncio
import io
import os
import subprocess
import wave
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryDirectory

MAX_PCM_BYTES = 60 * 16000 * 2


async def normalize_asr_audio(data: bytes, audio_format: str) -> bytes:
    """Decode bounded browser audio into real 16kHz mono WAV, never relabel bytes."""
    if audio_format not in {"wav", "webm", "ogg"} or not data or len(data) > 8_000_000:
        raise ValueError("Invalid Earth audio input")
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-protocol_whitelist",
        "pipe,fd",
        "-f",
        audio_format,
        "-i",
        "pipe:0",
        "-vn",
        "-t",
        "60",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-acodec",
        "pcm_s16le",
        "-f",
        "s16le",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    assert process.stdin is not None and process.stdout is not None

    async def feed() -> None:
        assert process.stdin is not None
        try:
            process.stdin.write(data)
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            process.stdin.close()

    feeder = asyncio.create_task(feed())
    pcm = bytearray()
    try:
        async with asyncio.timeout(15):
            while chunk := await process.stdout.read(min(65536, MAX_PCM_BYTES - len(pcm) + 1)):
                pcm.extend(chunk)
                if len(pcm) > MAX_PCM_BYTES:
                    raise ValueError("Earth audio decoder exceeded output limit")
            await feeder
            if await process.wait() != 0 or not pcm or len(pcm) % 2:
                raise ValueError("Invalid decoded Earth audio")
    finally:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
        await process.wait()
        feeder.cancel()
        await asyncio.gather(feeder, return_exceptions=True)
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(pcm)
    return output.getvalue()


def volume_envelope(data: bytes, audio_format: str) -> list[float]:
    from animetta.avatar.analyzers.audio import AudioAnalyzer

    extension = audio_format if audio_format in {"wav", "mp3", "ogg", "opus"} else "wav"
    with TemporaryDirectory(prefix="animetta-earth-") as folder:
        path = Path(folder) / f"narration.{extension}"
        path.write_bytes(data)
        values = AudioAnalyzer().compute_volume_envelope(
            str(path), normalize=False, gain=3.5, use_peak=True
        )
        return [min(1.0, max(0.0, value)) for value in values]
