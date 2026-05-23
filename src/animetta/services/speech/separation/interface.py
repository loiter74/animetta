"""
Audio Source Separation interface definition
"""

from abc import ABC, abstractmethod
from typing import Dict, Union, Optional
from pathlib import Path


class SeparationInterface(ABC):
    """
    Abstract base class for audio source separation interfaces.

    Source separation decomposes an audio mixture into its constituent
    stems (e.g., vocals, drums, bass, other).
    """

    @abstractmethod
    async def separate(
        self,
        audio: bytes,
        target: Optional[str] = None,
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Dict[str, Union[bytes, str]]:
        """
        Separate audio mixture into constituent stems.

        Args:
            audio: Input audio bytes (WAV format)
            target: Specific stem to extract (e.g., 'vocals'). If None, extracts all.
            output_dir: Directory for output stem files (optional)
            **kwargs: Additional separation parameters

        Returns:
            Dict mapping stem name to audio bytes or file path.
            e.g., {"vocals": b"...", "other": b"..."}
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources (GPU memory, loaded models, etc.)"""
        pass
