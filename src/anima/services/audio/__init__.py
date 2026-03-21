"""
音频处理器服务

提供 VAD 音频处理功能，用于语音输入的检测和累积。
"""

from .processor import AudioProcessorInterface
from .implementations.vad_audio_processor import VADAudioProcessor
from .implementations.simple_vad_processor import SimpleVADProcessor

__all__ = [
    "AudioProcessorInterface",
    "VADAudioProcessor",
    "SimpleVADProcessor",
]
