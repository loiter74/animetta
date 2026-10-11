"""
VAD (Voice Activity Detection) module
"""

from importlib import import_module
from typing import Any

from .factory import VADFactory
from .interface import VADInterface, VADResult, VADState
from .mock_vad import MockVAD

_LAZY_EXPORTS = {
    "SileroDetector": ".detector",
    "SileroVAD": ".silero_vad",
    "SileroStateMachine": ".silero_vad",
    "MimoVAD": ".mimo_vad",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    value = getattr(import_module(_LAZY_EXPORTS[name], __name__), name)
    globals()[name] = value
    return value


__all__ = [
    "VADInterface",
    "VADState",
    "VADResult",
    "VADFactory",
    "SileroDetector",
    "SileroVAD",
    "SileroStateMachine",
    "MockVAD",
    "MimoVAD",
]
