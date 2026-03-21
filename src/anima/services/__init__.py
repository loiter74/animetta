"""
服务模块

按服务种类组织：
- llm: LLM 服务
- asr: 语音识别服务
- tts: 语音合成服务
- vad: 语音活动检测
- audio: 音频处理服务（VAD + 累积）
"""

from .llm import LLMInterface, LLMFactory
from .asr import ASRInterface, ASRFactory
from .tts import TTSInterface, TTSFactory
from .vad import VADInterface, VADFactory
from .audio import AudioProcessorInterface
from .audio.implementations.vad_audio_processor import VADAudioProcessor

__all__ = [
    # LLM
    "LLMInterface",
    "LLMFactory",
    # ASR
    "ASRInterface",
    "ASRFactory",
    # TTS
    "TTSInterface",
    "TTSFactory",
    # VAD
    "VADInterface",
    "VADFactory",
    # Audio
    "AudioProcessorInterface",
    "VADAudioProcessor",
]
