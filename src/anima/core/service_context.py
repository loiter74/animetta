"""
服务上下文 - 核心服务容器
"""

from typing import Callable, Optional
from loguru import logger

from anima.services.audio import AudioProcessorInterface
from anima.services.audio.vad_audio_processor import VADAudioProcessor
from anima.config import AppConfig, ASRConfig, TTSConfig, AgentConfig, PersonaConfig, VADConfig
from anima.services import ASRInterface, TTSInterface, LLMInterface
from anima.services.speech.asr import ASRFactory
from anima.services.speech.tts import TTSFactory
from anima.services.intelligence.llm import LLMFactory
from anima.services.intelligence.vad import VADInterface, VADFactory
from anima.memory import MemorySystem


class ServiceContext:
    """服务上下文类"""
