"""Registry-backed geographic provider construction at the composition boundary."""

from typing import Any

from animetta.config.core.registry import ProviderRegistry
from animetta.config.providers.earth import PhotonConfig  # noqa: F401

from .interface import GeographySearch
from .photon import PhotonSearch  # noqa: F401


def create_search(config: dict[str, Any]) -> GeographySearch:
    provider = config.get("provider", "photon")
    schema = ProviderRegistry.get_config("earth", provider)
    if schema is None:
        raise ValueError("Unknown Earth search provider")
    values = {key: config[key] for key in ("endpoint", "min_interval_seconds") if key in config}
    return ProviderRegistry.create_service(
        "earth", schema.model_validate({"type": provider, **values})
    )
