"""
VAD (Voice Activity Detection) module
"""

from .interface import VADInterface, VADState, VADResult
from .factory import VADFactory
from .detector import SileroDetector

# Import implementations to trigger ProviderRegistry registration
try:
    from . import silero_vad, mock_vad
    from .silero_vad import SileroVAD, SileroStateMachine
    from .mock_vad import MockVAD
except ImportError:
    SileroVAD = None  # type: ignore
    SileroStateMachine = None  # type: ignore
    MockVAD = None  # type: ignore

__all__ = [
    "VADInterface",
    "VADState",
    "VADResult",
    "VADFactory",
    "SileroDetector",
    "SileroVAD",
    "SileroStateMachine",
    "MockVAD",
]
