"""Bilibili danmaku configuration model."""

from pydantic import Field

from ..core.base import BaseConfig


class BilibiliConfig(BaseConfig):
    """Bilibili live danmaku integration config.

    Controls whether the bilibili live danmaku service is enabled
    and which room to connect to. The sessdata cookie enables
    authenticated access for premium features.
    """
    enabled: bool = Field(default=False, description="Enable bilibili live danmaku integration")
    room_id: int = Field(default=0, ge=0, description="Bilibili live room ID to connect to")
    sessdata: str = Field(default="", description="Bilibili SESSDATA cookie for authenticated access")
