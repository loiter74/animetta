"""Photon geocoding; public instance is explicit-query-only and bounded.

Policy: https://github.com/komoot/photon#demo-server
Attribution: https://www.openstreetmap.org/copyright
No imagery or machine-vision permission is inferred from geocoding access.
"""

import asyncio
import time

import httpx

from animetta.config.core.registry import ProviderRegistry
from animetta.config.providers.earth import PhotonConfig

from .contracts import Candidate, EarthError, Source


@ProviderRegistry.register_service("earth", "photon")
class PhotonSearch:
    @classmethod
    def from_config(cls, config: PhotonConfig) -> "PhotonSearch":
        return cls(endpoint=config.endpoint, min_interval=config.min_interval_seconds)

    def __init__(
        self,
        endpoint: str = "https://photon.komoot.io/api/",
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        min_interval: float = 2.0,
    ) -> None:
        self.endpoint = endpoint
        self.transport = transport
        self.min_interval = min_interval
        self._last_request = float("-inf")
        self._lock = asyncio.Lock()

    async def search(self, query: str) -> list[Candidate]:
        query = query.strip()
        if not query or len(query) > 200:
            raise EarthError("INVALID_QUERY", "请输入简短的地名。")
        async with self._lock:
            now = time.monotonic()
            if now - self._last_request < self.min_interval:
                raise EarthError("SEARCH_RATE_LIMITED", "查询过于频繁，请稍候再试。")
            self._last_request = now
            try:
                async with httpx.AsyncClient(transport=self.transport, timeout=12) as client:
                    response = await client.get(
                        self.endpoint,
                        params={"q": query, "limit": 5},
                        headers={"User-Agent": "Animetta-Earth/1.0"},
                    )
                    response.raise_for_status()
                    features = response.json()["features"]
                candidates = []
                for feature in features[:5]:
                    properties = feature["properties"]
                    longitude, latitude = feature["geometry"]["coordinates"][:2]
                    extent = properties.get("extent")
                    bounds = (extent[0], extent[3], extent[2], extent[1]) if extent else None
                    span = max(bounds[2] - bounds[0], bounds[3] - bounds[1]) if bounds else 0.1
                    osm_type = {"N": "node", "W": "way", "R": "relation"}.get(
                        properties.get("osm_type"), "node"
                    )
                    osm_id = properties["osm_id"]
                    candidates.append(
                        Candidate(
                            id=f"{osm_type}:{osm_id}",
                            name=", ".join(
                                dict.fromkeys(
                                    str(properties[key])
                                    for key in ("name", "city", "state", "country")
                                    if properties.get(key)
                                )
                            ),
                            longitude=longitude,
                            latitude=latitude,
                            height=max(800, min(5_000_000, span * 140_000)),
                            bounds=bounds,
                            source=Source(
                                name="Photon / OpenStreetMap",
                                url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                                attribution="© OpenStreetMap contributors · ODbL",
                            ),
                            category=properties.get("osm_value"),
                        )
                    )
                return candidates
            except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
                raise EarthError(
                    "SEARCH_UNAVAILABLE", "地名检索暂时不可用，请手动探索或稍后重试。"
                ) from exc
