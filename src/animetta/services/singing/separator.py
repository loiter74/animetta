"""Source separation — supports Demucs (default) and UVR."""

import asyncio
import os
import shutil
from pathlib import Path
from abc import ABC, abstractmethod

from loguru import logger


class BaseSeparator(ABC):
    """Abstract base for source separation engines."""

    def __init__(self, output_dir: str = "./data/singing/separated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    async def separate(self, audio_path: str) -> tuple[str, str]:
        """Separate audio into (vocals_path, backing_path)."""
        ...

    async def close(self) -> None:
        pass


class DemucsSeparator(BaseSeparator):
    """Separate vocals from backing track using Demucs."""

    def __init__(self, model: str = "htdemucs", output_dir: str = "./data/singing/separated"):
        super().__init__(output_dir)
        self.model = model

    def __init__(
        self,
        model: str = "htdemucs",
        output_dir: str = "./data/singing/separated",
    ):
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def separate(self, audio_path: str) -> tuple[str, str]:
        """Separate audio into vocals and backing track.
        
        Returns:
            Tuple of (vocals_path, backing_path).
        """
        logger.info(f"Separating audio: {audio_path} (model={self.model})")

        session_dir = self.output_dir / Path(audio_path).stem
        session_dir.mkdir(parents=True, exist_ok=True)

        vocals_path = session_dir / "vocals.wav"
        backing_path = session_dir / "backing.wav"

        if vocals_path.exists() and backing_path.exists():
            logger.info(f"Using cached separation: {session_dir}")
            return str(vocals_path), str(backing_path)

        # Demucs separates into model_dir/original_name/stem.wav
        cmd = [
            "python", "-m", "demucs",
            "-n", self.model,
            "--two-stems", "vocals",
            "-d", "cpu",
            "-o", str(session_dir),
            audio_path,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "TORCHAUDIO_BACKEND": "soundfile"},
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

            if proc.returncode != 0:
                err_text = stderr.decode("utf-8", errors="replace")[:500] if stderr else "(no output)"
                raise RuntimeError(
                    f"Demucs failed (code {proc.returncode}): {err_text}"
                )

            # Demucs output: <session_dir>/<model>/<song_name>/vocals.wav + no_vocals.wav
            original_stem = Path(audio_path).stem
            demucs_output = session_dir / self.model / original_stem
            src_vocals = demucs_output / "vocals.wav"
            src_backing = demucs_output / "no_vocals.wav"

            if not src_vocals.exists():
                raise RuntimeError(f"Demucs vocals not found: {src_vocals}")
            if not src_backing.exists():
                raise RuntimeError(f"Demucs backing not found: {src_backing}")

            # Copy to expected locations
            shutil.copy2(src_vocals, vocals_path)
            shutil.copy2(src_backing, backing_path)

            logger.info(f"Separation complete: vocals={vocals_path}, backing={backing_path}")
            return str(vocals_path), str(backing_path)

        except asyncio.TimeoutError:
            raise RuntimeError("Demucs processing timed out (>10 min)")


class UVRSeparator(BaseSeparator):
    """Separate vocals from backing track using UVR (Ultimate Vocal Remover)."""

    def __init__(self, model: str = "UVR-MDX-NET-Inst_HQ_3", output_dir: str = "./data/singing/separated"):
        super().__init__(output_dir)
        self.model = model

    async def separate(self, audio_path: str) -> tuple[str, str]:
        """Separate audio into vocals and backing track using UVR.

        Returns:
            Tuple of (vocals_path, backing_path).
        """
        logger.info(f"Separating audio (UVR): {audio_path} (model={self.model})")

        session_dir = self.output_dir / Path(audio_path).stem
        session_dir.mkdir(parents=True, exist_ok=True)

        vocals_path = session_dir / "vocals.wav"
        backing_path = session_dir / "backing.wav"

        if vocals_path.exists() and backing_path.exists():
            logger.info(f"Using cached UVR separation: {session_dir}")
            return str(vocals_path), str(backing_path)

        cmd = [
            "python", "-m", "uvr",
            "--model", self.model,
            "--input", audio_path,
            "--output", str(session_dir),
            "--vocals-only", "false",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

            if proc.returncode != 0:
                err_text = stderr.decode("utf-8", errors="replace")[:500] if stderr else "(no output)"
                raise RuntimeError(f"UVR failed (code {proc.returncode}): {err_text}")

            if not vocals_path.exists():
                raise RuntimeError(f"UVR vocals not found: {vocals_path}")
            if not backing_path.exists():
                raise RuntimeError(f"UVR backing not found: {backing_path}")

            logger.info(f"UVR separation complete: vocals={vocals_path}, backing={backing_path}")
            return str(vocals_path), str(backing_path)

        except asyncio.TimeoutError:
            raise RuntimeError("UVR processing timed out (>10 min)")


def create_separator(engine: str, model: str, output_dir: str) -> BaseSeparator:
    """Factory: create source separator by engine name.

    Args:
        engine: "demucs" or "uvr"
        model: Model name (e.g. "htdemucs" or "UVR-MDX-NET-Inst_HQ_3")
        output_dir: Output directory path
    """
    if engine == "uvr":
        return UVRSeparator(model=model, output_dir=output_dir)
    return DemucsSeparator(model=model, output_dir=output_dir)


# Alias for backward compatibility
SourceSeparator = DemucsSeparator
