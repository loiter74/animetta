"""
服务模块

重组后的结构：
- speech/asr: 语音识别服务
- speech/tts: 语音合成服务
- intelligence/llm: 大语言模型
- intelligence/vad: 语音活动检测
- audio: 音频处理服务
- live2d: Live2D 控制
"""

from .intelligence.llm import LLMInterface, LLMFactory
from .speech.asr import ASRInterface, ASRFactory
from .speech.tts import TTSInterface, TTSFactory
from .intelligence.vad import VADInterface, VADFactory
from .audio import AudioProcessorInterface
from .audio.vad_audio_processor import VADAudioProcessor

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
