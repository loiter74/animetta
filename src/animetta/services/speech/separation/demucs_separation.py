from __future__ import annotations

"""
Demucs / MDX-based audio source separation via Music-Source-Separation-Training (MSST)

Uses pre-trained MSST models for high-quality stem separation.
Supports mel_band_roformer, htdemucs, scnet, bs_roformer, apollo, and other MSST model types.

The underlying MSST demix() function is a blocking synchronous call — wrapped in
asyncio.to_thread() to avoid blocking the event loop.
"""

import asyncio
import io as _io
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from .interface import SeparationInterface

MSST_ROOT = "C:/Users/30262/Music-Source-Separation-Training"


from animetta.config.core.registry import ProviderRegistry


@ProviderRegistry.register_service("separation", "demucs")
class DemucsSeparation(SeparationInterface):
    """
    Demucs / MDX-based audio source separation using MSST framework.

    Lazy-loads the MSST model on first :meth:`separate()` call to avoid
    startup overhead.  The heavy PyTorch model + checkpoint are only
    initialized when actually needed.

    Inference is run in a background thread via :func:`asyncio.to_thread`
    so the event loop stays responsive.
    """

    def __init__(self, config: DemucsSeparationConfig) -> None:
        self._config = config

        # Lazily initialized on first separate() / preload()
        self._model: Any = None
        self._msst_config: Any = None
        self._device: Any = None
        self._demix_fn: Any = None
        self._is_loaded: bool = False

    # ── classmethod ────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config: DemucsSeparationConfig) -> DemucsSeparation:
        """Create instance from provider configuration."""
        return cls(config)

    # ── public interface ───────────────────────────────────────────

    async def separate(
        self,
        audio: bytes,
        target: str | None = None,
        output_dir: str | Path | None = None,
        **kwargs: Any,
    ) -> dict[str, bytes | str]:
        """
        Separate audio mixture into constituent stems.

        Args:
            audio: Input audio bytes (WAV format).
            target: Specific stem to extract (e.g. ``"vocals"``).
                    If ``None``, returns all available stems.
            output_dir: Directory to write stem WAV files to.
                        If ``None``, returns in-memory bytes.
            **kwargs: Additional parameters (currently unused).

        Returns:
            Dict mapping stem name to either audio ``bytes`` or file ``str``
            (when *output_dir* is provided).
        """
        if not audio:
            logger.warning("DemucsSeparation: empty audio, returning empty dict")
            return {}

        original_path = sys.path.copy()
        try:
            sys.path.insert(0, MSST_ROOT)
            self._ensure_model_loaded()

            import soundfile as sf

            # ── bytes → numpy (channels, samples) ──
            data, original_sr = sf.read(_io.BytesIO(audio))
            if data.ndim == 1:
                data = data.reshape(1, -1)  # (samples,) → (1, samples)
            else:
                data = data.T  # (samples, ch) → (ch, samples)

            if original_sr != self._config.sample_rate:
                import librosa

                data = librosa.resample(
                    data, orig_sr=original_sr, target_sr=self._config.sample_rate
                )

            # ── blocking demix → background thread ──
            waveforms: dict[str, np.ndarray] = await asyncio.to_thread(
                self._demix_fn,
                self._msst_config,
                self._model,
                data,
                self._device,
                model_type=self._config.model_type,
                pbar=False,
            )

            # ── filter by target stem ──
            if target is not None:
                if target in waveforms:
                    waveforms = {target: waveforms[target]}
                else:
                    logger.warning(
                        f"DemucsSeparation: target stem '{target}' not in "
                        f"{list(waveforms.keys())}, returning all stems"
                    )

            # ── numpy → output ──
            if output_dir is not None:
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)
                result: dict[str, bytes | str] = {}
                for stem_name, waveform in waveforms.items():
                    stem_path = out / f"{stem_name}.wav"
                    sf.write(str(stem_path), waveform.T, self._config.sample_rate, subtype="FLOAT")
                    result[stem_name] = str(stem_path)
                return result

            result = {}
            for stem_name, waveform in waveforms.items():
                buf = _io.BytesIO()
                sf.write(buf, waveform.T, self._config.sample_rate, format="WAV", subtype="FLOAT")
                result[stem_name] = buf.getvalue()
            return result

        except Exception as e:
            logger.error(f"DemucsSeparation failed: {e}")
            raise RuntimeError(f"Audio source separation failed: {e}") from e
        finally:
            sys.path = original_path

    async def preload(self) -> None:
        """
        Warm up the separation model with a silent-audio forward pass.

        Called during server startup (via ModelLoadingManager) so the first
        real user request does not pay cold-start cost.
        """
        original_path = sys.path.copy()
        try:
            sys.path.insert(0, MSST_ROOT)
            self._ensure_model_loaded()

            silent = np.zeros((2, self._config.sample_rate), dtype=np.float32)
            await asyncio.to_thread(
                self._demix_fn,
                self._msst_config,
                self._model,
                silent,
                self._device,
                model_type=self._config.model_type,
                pbar=False,
            )
            logger.info("DemucsSeparation: preload warmup completed")
        except Exception as e:
            logger.warning(f"DemucsSeparation: preload warmup failed (non-fatal): {e}")
        finally:
            sys.path = original_path

    async def close(self) -> None:
        """Release model and free GPU memory."""
        self._model = None
        self._msst_config = None
        self._demix_fn = None
        self._device = None
        self._is_loaded = False

        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.debug("DemucsSeparation: resources released")

    # ── internal helpers ───────────────────────────────────────────

    def _ensure_model_loaded(self) -> None:
        """
        Load the MSST model, config, and checkpoint lazily.

        Must be called from within a ``try/finally`` block that has
        ``MSST_ROOT`` on ``sys.path``.
        """
        if self._is_loaded:
            return

        import torch
        from utils.model_utils import demix as _demix
        from utils.settings import get_model_from_config

        # ── device ──
        device_str = self._config.device
        if device_str.startswith("cuda") and not torch.cuda.is_available():
            logger.warning("DemucsSeparation: CUDA not available, falling back to CPU")
            device_str = "cpu"
        elif device_str.startswith("mps") and not torch.backends.mps.is_available():
            logger.warning("DemucsSeparation: MPS not available, falling back to CPU")
            device_str = "cpu"

        self._device = torch.device(device_str)

        # ── model + config from YAML ──
        model, msst_config = get_model_from_config(
            self._config.model_type,
            self._config.config_path,
        )

        # ── override inference knobs from our Python config ──
        _apply_inference_overrides(msst_config, self._config)

        # ── load checkpoint ──
        if self._config.checkpoint_path:
            self._load_checkpoint(model, self._config.checkpoint_path)

        # ── FP16 if requested ──
        if self._config.is_half and self._device.type == "cuda":
            model = model.half()

        model = model.to(self._device)
        model.eval()

        # ── store references ──
        self._model = model
        self._msst_config = msst_config
        self._demix_fn = _demix
        self._is_loaded = True

        instruments = getattr(msst_config.training, "instruments", ["unknown"])
        logger.info(
            f"DemucsSeparation: model loaded "
            f"(type={self._config.model_type}, device={device_str}, "
            f"instruments={instruments})"
        )

    def _load_checkpoint(self, model: Any, checkpoint_path: str) -> None:
        """
        Load a state-dict checkpoint into *model*.

        Mirrors MSST's ``load_start_checkpoint`` inference path.
        """
        import torch

        if self._config.model_type in ("htdemucs", "apollo"):
            state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            if "state" in state_dict:
                state_dict = state_dict["state"]
            if "state_dict" in state_dict:
                state_dict = state_dict["state_dict"]
        else:
            state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        logger.debug(f"DemucsSeparation: checkpoint loaded from {checkpoint_path}")


# ── helpers ────────────────────────────────────────────────────────────

def _apply_inference_overrides(
    msst_config: Any,
    cfg: DemucsSeparationConfig,
) -> None:
    """
    Apply our Python‑side inference parameters onto the MSST ConfigDict.

    Only writes keys that already exist in *msst_config* (to avoid
    polluting the config with unknown keys).
    """
    # audio.chunk_size (generic mode only — htdemucs derives chunk_size differently)
    if hasattr(msst_config, "audio") and hasattr(msst_config.audio, "chunk_size"):
        msst_config.audio.chunk_size = cfg.chunk_size

    # inference section
    if hasattr(msst_config, "inference"):
        if hasattr(msst_config.inference, "batch_size"):
            msst_config.inference.batch_size = cfg.batch_size
        if hasattr(msst_config.inference, "num_overlap"):
            msst_config.inference.num_overlap = cfg.num_overlap
        if hasattr(msst_config.inference, "normalize"):
            msst_config.inference.normalize = cfg.normalize
