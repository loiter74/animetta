"""
TTS (Text-to-Speech) interface definition
"""

from abc import ABC, abstractmethod
from typing import Union, Optional
from pathlib import Path


class TTSInterface(ABC):
    """
    Abstract base class for speech synthesis interfaces
    All TTS implementations must inherit from this class and implement its abstract methods
    """

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Union[bytes, str]:
        """
        Synthesize text to speech

        Args:
            text: Text to synthesize
            output_path: Output file path (optional)
            **kwargs: Additional parameters

        Returns:
            Union[bytes, str]: If output_path is specified, returns the file path string
                               Otherwise returns audio byte data
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources"""
        pass