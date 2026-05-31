"""
服务模块 — 扁平化后的结构：
  llm/  asr/  tts/  vad/  vc/  separation/  audio/  singing/  live2d/  live/  meme/
"""

from .asr import ASRFactory, ASRInterface
from .audio import AudioProcessorInterface
from .audio.vad_audio_processor import VADAudioProcessor
from .llm import LLMFactory, LLMInterface
from .singing import SingingService, SVCPipeline
from .tts import TTSFactory, TTSInterface
from .vad import VADFactory, VADInterface

__all__ = [
    "LLMInterface", "LLMFactory",
    "ASRInterface", "ASRFactory",
    "TTSInterface", "TTSFactory",
    "VADInterface", "VADFactory",
    "AudioProcessorInterface", "VADAudioProcessor",
    "SingingService", "SVCPipeline",
]
