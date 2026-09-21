"""Geography capability port."""

from typing import Protocol

from .contracts import Candidate


class GeographySearch(Protocol):
    async def search(self, query: str) -> list[Candidate]:
        """Resolve one explicit query into attributed candidates."""
        ...
