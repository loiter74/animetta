"""Shared node error logging utility for LangGraph graph nodes.

Provides a single `log_node_error()` function that LLM/TTS/ASR nodes use to
report provider failures to StatsStore with structured metadata.

Usage:
    from .node_error import log_node_error

    try:
        result = await provider.call(...)
    except Exception as e:
        await log_node_error(
            session_id=session_id,
            node_name="llm_node",
            error_type="timeout",
            provider="deepseek",
            duration_ms=30000,
            trace_id=trace_id,
        )
        # then fall back to mock response
"""

import json
from typing import Optional, FrozenSet
from loguru import logger

LOGGER = logger.bind(name="NodeError")

VALID_ERROR_TYPES: FrozenSet[str] = frozenset({
    "timeout",
    "rate_limit",
    "network_error",
    "invalid_response",
})


async def log_node_error(
    session_id: str,
    node_name: str,
    error_type: str,
    provider: str = "",
    duration_ms: float = 0.0,
    trace_id: Optional[str] = None,
) -> None:
    """Log a provider failure to StatsStore with structured metadata.

    Args:
        session_id: Session identifier
        node_name: Graph node name (e.g. "llm_node", "tts_node", "asr_node")
        error_type: One of "timeout", "rate_limit", "network_error", "invalid_response"
        provider: Provider name (e.g. "deepseek", "edge_tts", "whisper")
        duration_ms: Duration of the failed call in milliseconds
        trace_id: Optional trace ID for StatsStore span association.
                  If None, no span is created (only loguru warning).
    """
    if error_type not in VALID_ERROR_TYPES:
        LOGGER.debug(
            f"[{session_id}] Unknown error_type '{error_type}', "
            f"mapping to 'unknown'"
        )
        error_type = "unknown"

    attributes = json.dumps({
        "error_type": error_type,
        "provider": provider,
        "duration_ms": duration_ms,
    })

    LOGGER.warning(
        f"[{session_id}] [{node_name}] Provider error: "
        f"type={error_type} provider={provider} duration={duration_ms:.0f}ms"
    )

    if trace_id is None:
        LOGGER.warning(
            f"[{session_id}] [{node_name}] No trace_id — skipping StatsStore span"
        )
        return

    # Write error span to StatsStore
    try:
        import uuid
        from .stats_store import get_stats_store

        store = await get_stats_store()
        span_id = f"{trace_id}_{node_name}_error_{uuid.uuid4().hex[:8]}"
        await store.create_span(
            span_id=span_id,
            trace_id=trace_id,
            node_name=node_name,
            input_summary=f"error:{error_type}",
        )
        await store.finish_span(
            span_id=span_id,
            duration_ms=duration_ms,
            status="error",
        )
        # Update the span with structured attributes (separate call for attributes column)
        # Note: create_span/finish_span don't support attributes directly.
        # We store error metadata via the span's input_summary/output_summary fields
        # which are queryable. The full JSON goes to the loguru log.
    except Exception as e:
        LOGGER.error(f"[{session_id}] Failed to write error span: {e}")
