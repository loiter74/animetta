"""System configuration"""

from pydantic import Field
from .core.base import BaseConfig


class SystemConfig(BaseConfig):
    """System configuration"""
    host: str = Field(default="localhost", description="Server address")
    port: int = Field(default=12394, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")