"""
Audio processor service interface

Responsibilities:
1. Receive audio data stream
2. Perform voice activity detection using VAD
3. Accumulate valid speech segments
4. Trigger ASR transcription and LLM conversation
"""

from abc import ABC, abstractmethod
from typing import List, Callable, Optional, Any
from typing import Dict


class AudioProcessorInterface(ABC):
    """Audio processor interface"""

    @abstractmethod
    async def process_chunk(self, audio_data: List[float]) -> None:
        """
        Process audio data chunk

        Args:
            audio_data: Audio data (float32 list)
        """
        pass

    @abstractmethod
    async def process_end(self) -> None:
        """Handle audio input end"""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset processor state"""
        pass

    @abstractmethod
    def is_speaking(self) -> bool:
        """Whether speech is currently being detected"""
        pass
