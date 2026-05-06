"""TTS service implementation module"""

from .interface import TTSInterface
from .factory import TTSFactory

from .mock_tts import MockTTS
from .glm_tts import GLMTTS
from .edge_tts import EdgeTTS
from .chattts_tts import ChatTTSTTS
from .vibe_voice_tts import VibeVoiceTTS
from .kokoro_tts import KokoroTTS
from .glados_effect import GladosEffectProcessor

__all__ = [
    "TTSInterface",
    "TTSFactory",
    "MockTTS",
    "GLMTTS",
    "EdgeTTS",
    "ChatTTSTTS",
    "VibeVoiceTTS",
    "KokoroTTS",
    "GladosEffectProcessor",
]
