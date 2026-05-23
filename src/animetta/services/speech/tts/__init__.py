"""TTS service implementation module

Structure:
- Core implementations (active, minimal deps): edge_tts, qwen3_tts, gpt_sovits_tts, mock_tts
- Contrib implementations (maintained/experimental): see contrib/ subpackage
"""

from .interface import TTSInterface
from .factory import TTSFactory

# Core implementations
from .mock_tts import MockTTS
from .edge_tts import EdgeTTS
from .gpt_sovits_tts import GPTSoVITSTTS
from .qwen3_tts import Qwen3TTSTTS

# Contrib implementations (maintained separately)
from .contrib import (
    GLMTTS,
    ChatTTSTTS,
    VibeVoiceTTS,
    KokoroTTS,
    GladosEffectProcessor,
)

__all__ = [
    "TTSInterface",
    "TTSFactory",
    # Core
    "MockTTS",
    "EdgeTTS",
    "GPTSoVITSTTS",
    "Qwen3TTSTTS",
    # Contrib
    "GLMTTS",
    "ChatTTSTTS",
    "VibeVoiceTTS",
    "KokoroTTS",
    "GladosEffectProcessor",
]
