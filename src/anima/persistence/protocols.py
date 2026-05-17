"""Protocol interfaces for persistence layer.

This module defines abstract base classes (protocols) for storage backends.
Concrete implementations live in their respective modules (e.g.
orchestration/graph/stats_store.py) and register against these protocols.

This ensures that higher layers (e.g. tracing/) depend only on the protocol,
not on concrete orchestration internals.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


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
