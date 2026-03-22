"""语音服务模块 - ASR + TTS"""

from .asr import ASRInterface, ASRFactory
from .tts import TTSInterface, TTSFactory

__all__ = ["ASRInterface", "ASRFactory", "TTSInterface", "TTSFactory"]
