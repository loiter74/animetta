"""
VAD (Voice Activity Detection) module
"""

from .interface import VADInterface, VADState, VADResult
from .factory import VADFactory

# Import implementations to trigger ProviderRegistry registration
try:
    from . import silero_vad, mock_vad
except ImportError:
    pass

__all__ = [
    "VADInterface",
    "VADState",
    "VADResult",
    "VADFactory",
]