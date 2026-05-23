"""
Mock VC implementation - for testing and development
"""

from typing import Union, Optional
from pathlib import Path

from .interface import VCInterface
from animetta import $$$
from animetta import $$$


@ProviderRegistry.register_service("vc", "mock")
class MockVC(VCInterface):
    """
    Mock VC implementation.

    Passes audio through unchanged (identity conversion).
    Used for testing and development.
    """

    def __init__(self):
        pass

    @classmethod
    def from_config(cls, config: MockVCConfig, **kwargs):
        """Create instance from configuration."""
        return cls()

    async def convert(
        self,
        audio: bytes,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Union[bytes, str]:
        """Return audio unchanged (identity pass-through)."""
        import asyncio
        await asyncio.sleep(0.1)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio)
            return str(output_path)
        return audio

    async def close(self) -> None:
        """No resources to clean up."""
        pass
