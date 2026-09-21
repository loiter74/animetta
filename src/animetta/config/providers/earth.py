"""Explicit-query Photon configuration; public server has no SLA."""

from typing import Literal

from pydantic import Field

from animetta.config.core.base import ProviderConfig
from animetta.config.core.registry import ProviderRegistry


@ProviderRegistry.register_config("earth", "photon")
class PhotonConfig(ProviderConfig):
    type: Literal["photon"] = "photon"
    endpoint: str = "https://photon.komoot.io/api/"
    min_interval_seconds: float = Field(default=2.0, ge=2.0)
