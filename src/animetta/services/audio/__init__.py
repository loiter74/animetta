"""
Audio processor service

Provides VAD audio processing functionality for speech input detection and accumulation.
"""

from .processor import AudioProcessorInterface
from .simple_vad_processor import SimpleVADProcessor
from .vad_audio_processor import VADAudioProcessor

__all__ = [
    "AudioProcessorInterface",
    "VADAudioProcessor",
    "SimpleVADProcessor",
]
