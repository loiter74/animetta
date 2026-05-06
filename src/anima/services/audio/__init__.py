"""
Audio processor service

Provides VAD audio processing functionality for speech input detection and accumulation.
"""

from .processor import AudioProcessorInterface
from .vad_audio_processor import VADAudioProcessor
from .simple_vad_processor import SimpleVADProcessor

__all__ = [
    "AudioProcessorInterface",
    "VADAudioProcessor",
    "SimpleVADProcessor",
]
