"""
Anima Tracing — OpenTelemetry-based distributed tracing for service-level calls.

Provides:
- StatsSpanExporter: writes OTel spans to StatsStore SQLite
- TracingProxy: auto-wraps service instances with OTel span creation
- init_tracing(): one-call bootstrap for TracerProvider
- init_metrics(): one-call bootstrap for MeterProvider
- attach_trace_context(): links OTel context to StatsHandler's trace_id
"""

from .bootstrap import init_tracing
from .context import attach_trace_context, detach_trace_context
from .exporter import StatsSpanExporter
from .proxy import TracingProxy

__all__ = [
    "StatsSpanExporter",
    "TracingProxy",
    "init_tracing",
    "attach_trace_context",
    "detach_trace_context",
]
