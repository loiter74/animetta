"""
FunASR Paraformer ASR implementation - Alibaba open-source speech recognition
GitHub: https://github.com/modelscope/FunASR

Features:
- Higher Chinese recognition accuracy than Whisper
- Supports real-time streaming recognition
- Optional VAD, punctuation restoration, speaker diarization
- Supports hotword functionality

Common models:
- paraformer-zh: Chinese offline speech recognition (recommended)
- paraformer-zh-streaming: Chinese streaming speech recognition
- paraformer-en: English speech recognition
"""

from typing import Union, Optional, List
from pathlib import Path
import numpy as np
from loguru import logger

from .interface import ASRInterface
from anima.config.core.registry import ProviderRegistry


@ProviderRegistry.register_service("asr", "funasr")
class FunASRASR(ASRInterface):
    """
    FunASR Paraformer ASR implementation
    Uses Alibaba's open-source Paraformer model, Chinese recognition outperforms Whisper
    """

    # Supported model list
    MODELS = {
        "paraformer-zh": "Chinese offline speech recognition (recommended)",
        "paraformer-zh-streaming": "Chinese streaming speech recognition",
        "paraformer-en": "English speech recognition",
        "paraformer-8k-zh": "Chinese 8k sample rate",
        "paraformer-large-zh": "Chinese large model",
        "paraformer-large-en": "English large model",
    }

    def __init__(
        self,
        model: str = "paraformer-zh",
        language: str = "zh",
        device: str = "cuda",
        ncpu: int = 4,
        vad_model: Optional[str] = "fsmn-vad",
        punc_model: Optional[str] = "ct-punc",
        spk_model: Optional[str] = None,
        chunk_size: List[int] = None,
        hotword: Optional[str] = None,
        model_hub: str = "ms",
        disable_update: bool = True,
    ):
        """
        Initialize FunASR Paraformer ASR

        Args:
            model: Model name (default paraformer-zh)
            language: Language code (zh=Chinese, en=English)
            device: Device (cpu/cuda)
            ncpu: Number of CPU threads
            vad_model: VAD model name, None to disable
            punc_model: Punctuation restoration model name, None to disable
            spk_model: Speaker diarization model name, None to disable
            chunk_size: Streaming recognition chunk size
            hotword: Hotword file path or string
            model_hub: Model download source (ms=ModelScope, hf=HuggingFace)
            disable_update: Disable automatic model update check
        """
        self.model_name = model
        self.language = language
        self.device = device
        self.ncpu = ncpu
        self.vad_model = vad_model
        self.punc_model = punc_model
        self.spk_model = spk_model
        self.chunk_size = chunk_size or [0, 10, 5]
        self.hotword = hotword
        self.model_hub = model_hub
        self.disable_update = disable_update
        self._model = None

        logger.info(f"FunASR Paraformer ASR initialization config:")
        logger.info(f"  Model: {model}")
        logger.info(f"  Language: {language}")
        logger.info(f"  Device: {device}")
        logger.info(f"  VAD model: {vad_model}")
        logger.info(f"  Punctuation model: {punc_model}")
        logger.info(f"  Speaker model: {spk_model}")

    def _get_model(self):
        """Lazy-load model"""
        if self._model is None:
            try:
                from funasr import AutoModel

                # Build model parameters
                model_kwargs = {
                    "model": self.model_name,
                    "device": self.device,
                    "ncpu": self.ncpu,
                    "model_hub": self.model_hub,
                    "disable_update": self.disable_update,
                }

                # Add optional auxiliary models
                if self.vad_model:
                    model_kwargs["vad_model"] = self.vad_model
                if self.punc_model:
                    model_kwargs["punc_model"] = self.punc_model
                if self.spk_model:
                    model_kwargs["spk_model"] = self.spk_model

                logger.info(f"Loading FunASR model: {self.model_name}...")
                self._model = AutoModel(**model_kwargs)
                logger.info(f"FunASR model loaded successfully")

            except ImportError:
                logger.error("funasr not installed, please run: pip install funasr modelscope")
                raise ImportError(
                    "funasr 未安装，请运行: pip install funasr modelscope"
                )
            except Exception as e:
                logger.error(f"Failed to load FunASR model: {e}")
                raise

        return self._model

    async def transcribe(
        self,
        audio_data: Union[bytes, str, Path, list, np.ndarray],
        **kwargs
    ) -> str:
        """
        Transcribe audio data to text

        Args:
            audio_data: Audio data, can be:
                - bytes: Byte data in WAV/MP3 etc. format
                - str/Path: Audio file path
                - list/numpy array: PCM audio data (float32, range [-1.0, 1.0])

        Returns:
            str: Recognized text
        """
        import asyncio
        import tempfile

        model = self._get_model()

        # FunASR requires file path as input
        if isinstance(audio_data, np.ndarray):
            # Write numpy array to temporary WAV file
            audio_path = await self._save_temp_wav(audio_data)
        elif isinstance(audio_data, list):
            audio_np = np.array(audio_data, dtype=np.float32)
            audio_path = await self._save_temp_wav(audio_np)
        elif isinstance(audio_data, (str, Path)):
            audio_path = str(audio_data)
        elif isinstance(audio_data, bytes):
            # Save bytes to temp file
            audio_path = await self._save_bytes_to_temp(audio_data)
        else:
            raise ValueError(f"Unsupported audio data type: {type(audio_data)}")

        logger.debug(f"FunASR processing audio: {audio_path}")

        # Run transcription in thread pool (CPU/GPU-intensive operation)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._transcribe_sync,
            audio_path
        )

        logger.info(f"FunASR recognition result: {result}")
        return result

    def _transcribe_sync(self, audio_path: str) -> str:
        """Synchronous transcription method"""
        model = self._get_model()

        # Build generation parameters
        gen_kwargs = {}
        if self.hotword:
            gen_kwargs["hotword"] = self.hotword

        # Execute transcription
        result = model.generate(input=audio_path, **gen_kwargs)

        # Extract text
        if not result:
            return ""

        # result is a list, each element corresponds to an input
        first_result = result[0]
        if isinstance(first_result, dict):
            text = first_result.get("text", "")
        else:
            text = str(first_result)

        return text.strip()

    async def _save_temp_wav(self, audio_np: np.ndarray) -> str:
        """Save numpy array to temporary WAV file"""
        import wave
        import tempfile

        # Ensure float32 format
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)

        # Clip range to [-1.0, 1.0]
        audio_np = np.clip(audio_np, -1.0, 1.0)

        # Convert to 16-bit PCM
        audio_int16 = (audio_np * 32767).astype(np.int16)

        # Write to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        with wave.open(tmp_path, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)  # 16kHz
            wf.writeframes(audio_int16.tobytes())

        logger.debug(f"Saved temporary WAV file: {tmp_path}")
        return tmp_path

    async def _save_bytes_to_temp(self, audio_bytes: bytes) -> str:
        """Save bytes to temp file"""
        import tempfile

        # Try to detect format
        suffix = ".wav"
        if audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            suffix = ".mp3"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            return tmp_file.name

    async def transcribe_stream(
        self,
        audio_data: Union[bytes, str, Path, list, np.ndarray],
        **kwargs
    ):
        """
        Stream recognition of audio, generator returns text chunks

        Args:
            audio_data: Audio data

        Yields:
            str: Recognized text chunks
        """
        # For streaming models, chunk mode can be used
        result = await self.transcribe(audio_data, **kwargs)

        # Split by sentences and return
        import re
        sentences = re.split(r'[。！？.!?]', result)

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                yield sentence

    async def close(self) -> None:
        """Clean up resources"""
        self._model = None
        logger.debug("FunASR ASR resources released")

    @classmethod
    def from_config(cls, config, **kwargs):
        """Create instance from configuration"""
        return cls(
            model=config.get("model", "paraformer-zh"),
            language=config.get("language", "zh"),
            device=config.get("device", "cuda"),
            ncpu=config.get("ncpu", 4),
            vad_model=config.get("vad_model", "fsmn-vad"),
            punc_model=config.get("punc_model", "ct-punc"),
            spk_model=config.get("spk_model"),
            chunk_size=config.get("chunk_size", [0, 10, 5]),
            hotword=config.get("hotword"),
            model_hub=config.get("model_hub", "ms"),
            disable_update=config.get("disable_update", True),
        )

    async def preload(self) -> None:
        """
        Preload model (called at startup to avoid delay on first use)
        """
        import asyncio

        logger.info(f"FunASR preloading model: {self.model_name}...")

        # Load model in thread pool (avoids blocking)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._get_model)

        logger.info(f"FunASR model preloaded: {self.model_name}")
