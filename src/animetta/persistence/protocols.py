"""Protocol interfaces for persistence layer.

This module defines abstract base classes (protocols) for storage backends,
shared data models (WikiPage, PageType), and other types that cross layer
boundaries. Concrete implementations live in their respective modules
(e.g. orchestration/graph/stats_store.py) and register against these protocols.

This ensures that higher layers (e.g. tracing/, services/) depend only on the
protocol, not on concrete implementation internals.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


# ── Shared data models ──────────────────────────────────────────────────────


class PageType(Enum):
    ENTITY = "entity"
    CONCEPT = "concept"
    SOURCE = "source"
    SYNTHESIS = "synthesis"
    MEME = "meme"


@dataclass
class WikiPage:
    """Wiki page with frontmatter + Markdown content."""

    title: str
    page_type: PageType
    path: str  # relative to wiki/, e.g. "entities/user.md"
    content: str  # Markdown body (without frontmatter)
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)  # [[wikilink]] targets
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    raw_source: Optional[str] = None  # link to raw/ source file
    metadata: Dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Render full Markdown with YAML frontmatter."""
        import yaml

        fm: Dict = {
            "type": self.page_type.value,
            "created": self.created_at.isoformat(),
            "updated": self.updated_at.isoformat(),
        }
        if self.tags:
            fm["tags"] = self.tags
        if self.links:
            fm["links"] = self.links
        if self.raw_source:
            fm["raw_source"] = self.raw_source
        # Merge custom metadata (e.g. id, review_status, is_active for MemeStore)
        if self.metadata:
            fm.update(self.metadata)

        yml = yaml.dump(fm, allow_unicode=True, default_flow_style=False)
        return f"---\n{yml}---\n\n{self.content}\n"

    @classmethod
    def from_markdown(cls, path: str, text: str) -> "WikiPage":
        """Parse a Markdown file with optional YAML frontmatter."""
        content = text
        fm: Dict = {}

        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                except Exception:
                    fm = {}
                content = parts[2].strip()

        # title from first heading or filename
        title = Path(path).stem.replace("-", " ").replace("_", " ")
        first_line = content.split("\n", 1)[0] if content else ""
        if first_line.startswith("# "):
            title = first_line[2:].strip()

        # extract [[wikilinks]]
        parsed_links = re.findall(r"\[\[(.+?)\]\]", content)

        return cls(
            title=title,
            page_type=PageType(fm.get("type", "entity")),
            path=path,
            content=content,
            tags=fm.get("tags", []),
            links=parsed_links,
            created_at=_parse_dt(fm.get("created")),
            updated_at=_parse_dt(fm.get("updated")),
            raw_source=fm.get("raw_source"),
            metadata=fm,
        )


def _parse_dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except Exception:
            logger.warning(f"[Protocols] Invalid datetime string: {v}")
    return datetime.now()


# ── Storage protocol abstractions ───────────────────────────────────────────


class StatsStoreProtocol(ABC):
    """Protocol for pipeline stats storage (SQLite, in-memory, etc.).

    Core write lifecycle methods are abstract — all implementations must
    provide them. Query/report methods have concrete default stubs that
    raise NotImplementedError, since not every implementation needs them.
    """

    @abstractmethod
    async def init(self) -> None:
        """Initialize the storage backend (e.g. open DB connection, create tables)."""
        ...

    # ── Core write lifecycle ──────────────────────────────────────────────

    @abstractmethod
    async def create_trace(
        self, trace_id: str, session_id: str, input_type: str, user_text: str
    ) -> None:
        """Record the start of a request trace."""
        ...

    @abstractmethod
    async def finish_trace(
        self,
        trace_id: str,
        total_duration_ms: float,
        status: str = "success",
        error_msg: str | None = None,
    ) -> None:
        """Record the completion of a request trace."""
        ...

    @abstractmethod
    async def create_span(
        self,
        span_id: str,
        trace_id: str,
        node_name: str,
        parent_span_id: str | None = None,
        input_summary: str | None = None,
    ) -> None:
        """Record the start of a span within a trace."""
        ...

    @abstractmethod
    async def finish_span(
        self,
        span_id: str,
        duration_ms: float,
        status: str = "success",
        output_summary: str | None = None,
    ) -> None:
        """Record the completion of a span."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release resources (close DB connection, flush buffers, etc.)."""
        ...

    # ── Query / report methods (optional for implementations) ────────────

    async def get_overview(self) -> Dict[str, Any]:
        """Return aggregate overview stats."""
        raise NotImplementedError

    async def get_node_stats(self) -> List[Dict[str, Any]]:
        """Return per-node execution statistics."""
        raise NotImplementedError

    async def get_recent_traces(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Return the most recent traces."""
        raise NotImplementedError

    async def get_trace_detail(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Return detailed information for a single trace."""
        raise NotImplementedError

    async def store_inspection_report(
        self,
        run_id: str,
        started_at: float,
        finished_at: float,
        overall_ok: bool,
        checks_json: str,
    ) -> None:
        """Persist an inspection report."""
        raise NotImplementedError

    async def get_latest_inspection_report(self) -> dict | None:
        """Retrieve the most recent inspection report, or None."""
        raise NotImplementedError
