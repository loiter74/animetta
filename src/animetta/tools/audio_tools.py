"""
Audio processing tools for LLM-orchestrated singing voice replacement workflow.

These tools allow an LLM to self-orchestrate the pipeline:
  1. separate_vocals(audio_path) → stems
  2. voice_convert(input_path, key, formant) → converted audio
  3. mix_audio(vocal_path, instrumental_path) → final mix

The LLM can chain them dynamically based on user requests.
"""

import io
import os
import struct
import tempfile
from typing import Optional, Dict
from pathlib import Path

import numpy as np
from loguru import logger
from langchain_core.tools import tool


def _read_audio_bytes(path: str) -> bytes:
    """Read audio file to bytes."""
    with open(path, "rb") as f:
        return f.read()


def _write_audio_bytes(data: bytes, suffix: str = ".wav") -> str:
    """Write audio bytes to a temp file and return path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(data)
    return path


@tool
async def separate_vocals(
    audio_path: str,
    target: str = "vocals",
    output_dir: Optional[str] = None,
) -> str:
    """Separate vocals from an audio mixture (song) into stems.

    Uses Demucs/MDX-based Music Source Separation to extract vocal and
    instrumental stems. The vocal stem can then be voice-converted.

    Args:
        audio_path: Path to the input audio file (WAV, MP3, etc.)
        target: Stem to extract. 'vocals' extracts the singing voice.
                Use 'all' to get all available stems.
        output_dir: Directory to save output stems (optional).
                    Defaults to a temp directory.

    Returns:
        JSON string with stem file paths, e.g.:
        {"vocals": "/tmp/vocals.wav", "other": "/tmp/other.wav"}
    """
    import json

    try:
        # Try to access the separation engine from the tool call context
        # Note: In LangGraph, the tool node passes configurable context
        # For standalone tool use, we fall back to a direct import
        separation_engine = None
        try:
            from langchain_core.runnables import RunnableConfig
            import inspect
            # Walk up the call stack to find RunnableConfig
            frame = inspect.currentframe()
            while frame:
                if 'config' in frame.f_locals:
                    cfg = frame.f_locals['config']
                    if isinstance(cfg, RunnableConfig):
                        svc_ctx = cfg.get("configurable", {}).get("service_context")
                        if svc_ctx:
                            separation_engine = svc_ctx.separation_engine
                        break
                if 'service_context' in frame.f_locals:
                    svc_ctx = frame.f_locals['service_context']
                    if hasattr(svc_ctx, 'separation_engine'):
                        separation_engine = svc_ctx.separation_engine
                    break
                frame = frame.f_back
        except Exception:
            pass

        if separation_engine is None:
            return json.dumps({
                "error": "Separation engine not available. "
                         "Please configure a separation provider in services.yaml."
            })

        audio_bytes = _read_audio_bytes(audio_path)
        stems = await separation_engine.separate(
            audio_bytes,
            target=None if target == "all" else target,
            output_dir=output_dir,
        )

        # Convert stems dict to paths
        result = {}
        for stem_name, stem_data in stems.items():
            if isinstance(stem_data, bytes):
                result[stem_name] = _write_audio_bytes(stem_data)
            elif isinstance(stem_data, str):
                result[stem_name] = stem_data

        logger.info(f"[separate_vocals] Success: {len(result)} stems extracted")
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"[separate_vocals] Failed: {e}")
        import json
        return json.dumps({"error": str(e)})


@tool
async def voice_convert(
    input_audio_path: str,
    key: int = 0,
    formant: int = 0,
    output_path: Optional[str] = None,
) -> str:
    """Convert the voice timbre of an audio file to a target voice.

    Uses RVC (Retrieval-based Voice Conversion) to change the speaker
    identity while preserving the linguistic/musical content. Perfect
    for replacing singing voices.

    Args:
        input_audio_path: Path to the input audio (e.g., separated vocals)
        key: Pitch shift in semitones (-24 to +24). Positive = higher pitch.
        formant: Formant shift (-12 to +12). Adjusts voice character.

    Returns:
        Path to the converted audio file.
    """
    try:
        # Try to access the VC engine from the tool call context
        vc_engine = None
        try:
            import inspect
            from langchain_core.runnables import RunnableConfig
            frame = inspect.currentframe()
            while frame:
                if 'config' in frame.f_locals:
                    cfg = frame.f_locals['config']
                    if isinstance(cfg, RunnableConfig):
                        svc_ctx = cfg.get("configurable", {}).get("service_context")
                        if svc_ctx:
                            vc_engine = svc_ctx.vc_engine
                        break
                if 'service_context' in frame.f_locals:
                    svc_ctx = frame.f_locals['service_context']
                    if hasattr(svc_ctx, 'vc_engine'):
                        vc_engine = svc_ctx.vc_engine
                    break
                frame = frame.f_back
        except Exception:
            pass

        if vc_engine is None:
            return f"Error: VC engine not available. Please configure a vc provider in services.yaml."

        audio_bytes = _read_audio_bytes(input_audio_path)
        result = await vc_engine.convert(
            audio_bytes,
            output_path=output_path,
            key=key,
            formant=formant,
        )

        if isinstance(result, bytes):
            result_path = output_path or _write_audio_bytes(result)
            return str(result_path)
        elif isinstance(result, str):
            return result
        else:
            return f"Error: Unexpected VC result type: {type(result)}"

    except Exception as e:
        logger.error(f"[voice_convert] Failed: {e}")
        return f"Error converting voice: {str(e)}"


@tool
async def mix_audio(
    vocal_path: str,
    instrumental_path: str,
    output_path: Optional[str] = None,
) -> str:
    """Mix vocal and instrumental tracks into a single audio file.

    Combines separated/converted vocals with the instrumental backing
    track. Handles sample rate matching and normalization.

    Args:
        vocal_path: Path to the vocal track (converted or original)
        instrumental_path: Path to the instrumental backing track
        output_path: Output path for the mixed file (optional).

    Returns:
        Path to the mixed audio file.
    """
    try:
        vocals = _read_audio_bytes(vocal_path)
        instrumental = _read_audio_bytes(instrumental_path)

        # Parse and mix WAV files
        def _parse_wav_samples(data: bytes) -> tuple[np.ndarray, int]:
            bio = io.BytesIO(data)
            bio.read(4)  # RIFF
            bio.read(4)  # size
            bio.read(4)  # WAVE
            while True:
                chunk_id = bio.read(4)
                chunk_size = struct.unpack('<I', bio.read(4))[0]
                if chunk_id == b'fmt ':
                    fmt_data = bio.read(chunk_size)
                    num_channels = struct.unpack_from('<H', fmt_data, 2)[0]
                    sample_rate = struct.unpack_from('<I', fmt_data, 4)[0]
                    bits = struct.unpack_from('<H', fmt_data, 14)[0]
                elif chunk_id == b'data':
                    raw = bio.read(chunk_size)
                    break
                else:
                    bio.read(chunk_size)
            dtype = {8: np.uint8, 16: np.int16, 32: np.int32}[bits]
            samples = np.frombuffer(raw, dtype=dtype).astype(np.float32)
            if num_channels > 1:
                samples = samples.reshape(-1, num_channels)
            return samples, sample_rate

        samples_v, sr_v = _parse_wav_samples(vocals)
        samples_i, sr_i = _parse_wav_samples(instrumental)

        if sr_v != sr_i:
            return f"Error: Sample rate mismatch: {sr_v}Hz vs {sr_i}Hz"

        # Pad shorter
        max_len = max(len(samples_v), len(samples_i))
        if len(samples_v) < max_len:
            samples_v = np.pad(samples_v, (0, max_len - len(samples_v)) if samples_v.ndim == 1 else
                              ((0, max_len - len(samples_v)), (0, 0)))
        if len(samples_i) < max_len:
            samples_i = np.pad(samples_i, (0, max_len - len(samples_i)) if samples_i.ndim == 1 else
                              ((0, max_len - len(samples_i)), (0, 0)))

        mixed = samples_v + samples_i
        peak = np.max(np.abs(mixed))
        if peak > 0.99:
            mixed = mixed / peak * 0.95

        mixed_int = (mixed * 32767).clip(-32768, 32767).astype(np.int16)
        buf = io.BytesIO()
        data_bytes = mixed_int.tobytes()
        num_ch = 1 if mixed_int.ndim == 1 else mixed_int.shape[1]
        buf.write(b'RIFF')
        buf.write(struct.pack('<I', 36 + len(data_bytes)))
        buf.write(b'WAVE')
        buf.write(b'fmt ')
        buf.write(struct.pack('<I', 16))
        buf.write(struct.pack('<H', 1))
        buf.write(struct.pack('<H', num_ch))
        buf.write(struct.pack('<I', sr_v))
        buf.write(struct.pack('<I', sr_v * num_ch * 2))
        buf.write(struct.pack('<H', num_ch * 2))
        buf.write(struct.pack('<H', 16))
        buf.write(b'data')
        buf.write(struct.pack('<I', len(data_bytes)))
        buf.write(data_bytes)

        result = buf.getvalue()
        result_path = output_path or _write_audio_bytes(result)
        logger.info(f"[mix_audio] Success: {len(result)}B → {result_path}")
        return str(result_path)

    except Exception as e:
        logger.error(f"[mix_audio] Failed: {e}")
        return f"Error mixing audio: {str(e)}"


def get_audio_tools():
    """Get all audio processing tools for tool registration."""
    return [separate_vocals, voice_convert, mix_audio]
