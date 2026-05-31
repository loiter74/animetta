"""VC (Voice Conversion) node — deterministic singing voice replacement pipeline

Optional node in the LangGraph. When activated, chains:
  1. Audio source separation (vocals / instrumental)
  2. Voice conversion (timbre change via RVC/SoVITS)
  3. Audio mixing (converted vocals + instrumental)

The result is stored in state["vc_audio"].
"""

import asyncio
import io
import time as time_module
from typing import Any

from langgraph.types import RunnableConfig
from loguru import logger

from .node_error import log_node_error
from .state import AgentState


def _get_service_context(config: RunnableConfig | None) -> Any | None:
    """Get service_context from LangGraph config"""
    if config:
        return config.get("configurable", {}).get("service_context")
    return None


def _mix_audio(vocals: bytes, instrumental: bytes) -> bytes:
    """Mix two WAV audio streams by summing samples with normalization.

    Both inputs must have the same sample rate and format.
    Normalizes output to prevent clipping.
    """
    import struct

    import numpy as np

    # Parse WAV headers
    def _read_wav(data: bytes) -> tuple[np.ndarray, int]:
        bio = io.BytesIO(data)
        riff = bio.read(4)
        if riff != b'RIFF':
            raise ValueError("Not a valid WAV file")
        bio.read(4)  # file size
        wave = bio.read(4)
        if wave != b'WAVE':
            raise ValueError("Not a valid WAV file")
        fmt = bio.read(4)
        while fmt != b'fmt ':
            size = struct.unpack('<I', bio.read(4))[0]
            bio.read(size)
            fmt = bio.read(4)
        bio.read(4)  # chunk size
        struct.unpack('<H', bio.read(2))[0]
        num_channels = struct.unpack('<H', bio.read(2))[0]
        sample_rate = struct.unpack('<I', bio.read(4))[0]
        bio.read(6)  # byte rate, block align
        bits_per_sample = struct.unpack('<H', bio.read(2))[0]
        # Find data chunk
        data_tag = bio.read(4)
        while data_tag != b'data':
            size = struct.unpack('<I', bio.read(4))[0]
            bio.read(size)
            data_tag = bio.read(4)
        data_size = struct.unpack('<I', bio.read(4))[0]
        raw_data = bio.read(data_size)
        dtype = {8: np.uint8, 16: np.int16, 32: np.int32}[bits_per_sample]
        samples = np.frombuffer(raw_data, dtype=dtype).astype(np.float32)
        if num_channels > 1:
            samples = samples.reshape(-1, num_channels)
        return samples, sample_rate

    samples_v, sr_v = _read_wav(vocals)
    samples_i, sr_i = _read_wav(instrumental)

    if sr_v != sr_i:
        raise ValueError(f"Sample rate mismatch: {sr_v} vs {sr_i}")

    # Pad shorter array
    max_len = max(len(samples_v), len(samples_i))
    if len(samples_v) < max_len:
        samples_v = np.pad(samples_v, (0, max_len - len(samples_v)) if samples_v.ndim == 1 else
                           ((0, max_len - len(samples_v)), (0, 0)))
    if len(samples_i) < max_len:
        samples_i = np.pad(samples_i, (0, max_len - len(samples_i)) if samples_i.ndim == 1 else
                           ((0, max_len - len(samples_i)), (0, 0)))

    mixed = samples_v + samples_i
    # Normalize to prevent clipping
    peak = np.max(np.abs(mixed))
    if peak > 0.99:
        mixed = mixed / peak * 0.95

    # Convert back to int16 WAV
    mixed_int = (mixed * 32767).clip(-32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    data_bytes = mixed_int.tobytes()
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + len(data_bytes)))
    buf.write(b'WAVE')
    buf.write(b'fmt ')
    buf.write(struct.pack('<I', 16))  # chunk size
    buf.write(struct.pack('<H', 1))   # PCM
    buf.write(struct.pack('<H', 1 if mixed_int.ndim == 1 else mixed_int.shape[1]))
    buf.write(struct.pack('<I', sr_v))
    buf.write(struct.pack('<I', sr_v * (2 if mixed_int.ndim == 1 else mixed_int.shape[1] * 2)))
    buf.write(struct.pack('<H', 2 if mixed_int.ndim == 1 else mixed_int.shape[1] * 2))
    buf.write(struct.pack('<H', 16))
    buf.write(b'data')
    buf.write(struct.pack('<I', len(data_bytes)))
    buf.write(data_bytes)
    return buf.getvalue()


async def vc_node(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """
    Singing voice replacement node.

    Pipeline: separate vocals → convert voice → mix with instrumental

    Input:  state["raw_audio"] (the input song/mixture) or state["tts_audio"]
    Output: state["vc_audio"] (converted and mixed final audio)
    """
    session_id = state.get("session_id", "unknown")
    input_audio = state.get("raw_audio") or state.get("tts_audio")

    if not input_audio:
        logger.info(f"[{session_id}] [VCNode] No audio input, skipping")
        return {"vc_audio": None}

    service_context = _get_service_context(config)
    if not service_context:
        logger.warning(f"[{session_id}] [VCNode] service_context not configured")
        return {"vc_audio": None}

    separation_engine = service_context.separation_engine
    vc_engine = service_context.vc_engine

    if not separation_engine and not vc_engine:
        logger.info(f"[{session_id}] [VCNode] No VC or separation engine configured, skipping")
        return {"vc_audio": None}

    t0 = time_module.perf_counter()
    logger.info(f"[{session_id}] [VCNode] Starting voice conversion pipeline...")

    try:
        # Step 1: Separate vocals from instrumental
        if separation_engine and isinstance(input_audio, bytes):
            logger.info(f"[{session_id}] [VCNode] Step 1: Separating audio...")
            stems = await asyncio.wait_for(
                separation_engine.separate(input_audio, target="vocals"),
                timeout=300.0,
            )
            vocals = stems.get("vocals", input_audio)
            instrumental = stems.get("other", stems.get("instrumental"))
            # Convert paths to bytes if needed
            if isinstance(vocals, str):
                with open(vocals, "rb") as f:
                    vocals = f.read()
            if instrumental and isinstance(instrumental, str):
                with open(instrumental, "rb") as f:
                    instrumental = f.read()
            logger.info(f"[{session_id}] [VCNode] Separation complete: vocals={len(vocals)}B, instrumental={len(instrumental) if instrumental else 0}B")
        else:
            vocals = input_audio if isinstance(input_audio, bytes) else None
            instrumental = None
            logger.info(f"[{session_id}] [VCNode] Step 1: Skipped (no separation engine or non-bytes input)")

        # Step 2: Convert voice timbre
        if vc_engine and vocals:
            logger.info(f"[{session_id}] [VCNode] Step 2: Converting voice...")
            converted = await asyncio.wait_for(
                vc_engine.convert(vocals),
                timeout=300.0,
            )
            if isinstance(converted, str):
                with open(converted, "rb") as f:
                    converted = f.read()
            logger.info(f"[{session_id}] [VCNode] Voice conversion complete: {len(converted)}B")
        else:
            converted = vocals
            logger.info(f"[{session_id}] [VCNode] Step 2: Skipped (no VC engine)")

        # Step 3: Mix back
        if converted and instrumental:
            logger.info(f"[{session_id}] [VCNode] Step 3: Mixing audio...")
            final_audio = _mix_audio(converted, instrumental)
            logger.info(f"[{session_id}] [VCNode] Mix complete: {len(final_audio)}B")
        else:
            final_audio = converted
            logger.info(f"[{session_id}] [VCNode] Step 3: Skipped (no instrumental)")

        elapsed = (time_module.perf_counter() - t0) * 1000
        logger.info(f"[{session_id}] [VCNode] Pipeline complete ({elapsed:.0f}ms)")

        return {"vc_audio": final_audio}

    except TimeoutError:
        logger.error(f"[{session_id}] [VCNode] Pipeline timed out")
        await log_node_error(session_id, "vc_node", "timeout", duration_ms=300000)
        return {"vc_audio": None, "error": "Voice conversion pipeline timed out"}
    except Exception as e:
        logger.error(f"[{session_id}] [VCNode] Pipeline failed: {type(e).__name__}: {e}")
        await log_node_error(session_id, "vc_node", "pipeline_error", duration_ms=0)
        return {"vc_audio": None, "error": str(e)}
