"""
Context propagation — bridges Anima's StatsCallbackHandler trace_id with OTel SpanContext.

Usage in LangGraph node functions::

    from anima.tracing import attach_trace_context, detach_trace_context

    async def llm_node(state, config):
        token = attach_trace_context(state)
        try:
            # ... service calls here get auto-parented to this trace
            return result
        finally:
            detach_trace_context(token)
"""

import uuid

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags


def _uuid_to_otel_trace_id(uuid_str: str) -> int:
    """Convert a StatsHandler UUID string to a 128-bit OTel trace_id."""
    return uuid.UUID(hex=uuid_str).int


def _make_otel_span_context(trace_id_int: int) -> SpanContext:
    """Build an OTel SpanContext from a trace_id (span_id=0, non-recording)."""
    return SpanContext(
        trace_id=trace_id_int,
        span_id=0,  # non-recording; real spans get unique IDs from Tracer
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )


def attach_trace_context(trace_id_str: str) -> object | None:
    """Attach an OTel SpanContext derived from a StatsHandler trace_id.

    After calling this, any ``tracer.start_span()`` in the same async context
    will automatically inherit this trace_id, creating a child span.

    Args:
        trace_id_str: UUID string from StatsCallbackHandler._trace_id.

    Returns:
        A token to pass to ``detach_trace_context()``, or None if the
        trace_id is empty.
    """
    if not trace_id_str:
        return None

    try:
        tid = _uuid_to_otel_trace_id(trace_id_str)
        sc = _make_otel_span_context(tid)
        span = NonRecordingSpan(sc)
        ctx = trace.set_span_in_context(span)
        return otel_context.attach(ctx)
    except Exception:
        return None


def detach_trace_context(token: object | None) -> None:
    """Detach a previously attached OTel context."""
    if token is not None:
        otel_context.detach(token)
