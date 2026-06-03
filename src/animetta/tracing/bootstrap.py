"""
Tracing bootstrap — one-call initialization of OpenTelemetry TracerProvider.

Reads config/observability.yaml and sets up:
- TracerProvider with SimpleSpanProcessor(StatsSpanExporter) → SQLite
- Optional: BatchSpanProcessor(OTLPSpanExporter) → OTel Collector (dual-write)
- Or NoOpTracerProvider when disabled
"""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger

_TRACER_INITIALIZED = False


def _load_full_config() -> dict[str, Any]:
    """Load full observability config from config/observability.yaml."""
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "observability.yaml"
    if not config_path.exists():
        logger.info("[Tracing] No observability.yaml found — using defaults")
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"[Tracing] Failed to load config: {e}")
        return {}


def init_tracing(
    service_name: str | None = None,
    enabled: bool | None = None,
    max_export_batch_size: int = 512,
    schedule_delay_millis: int = 5000,
):
    """Initialize the OpenTelemetry tracing pipeline.

    Dual-write mode: spans go to both StatsStore (SQLite) and OTel Collector (OTLP).
    Metrics (if configured) are exported via OTLP to the Collector.

    Idempotent: subsequent calls after the first are no-ops.

    Args:
        service_name: Service name for Resource attributes.
        enabled: Override config file's enabled flag.
        max_export_batch_size: BatchSpanProcessor batch size.
        schedule_delay_millis: BatchSpanProcessor interval (ms).

    Returns:
        The configured Tracer (or NoOpTracer if disabled).
    """
    full_cfg = _load_full_config()
    tracing_cfg = full_cfg.get("tracing", {})
    otlp_cfg = full_cfg.get("otlp", {})

    global _TRACER_INITIALIZED
    if _TRACER_INITIALIZED:
        from opentelemetry import trace
        return trace.get_tracer(service_name or "anima")

    if enabled is None:
        enabled = tracing_cfg.get("enabled", True)
    if service_name is None:
        service_name = tracing_cfg.get("service_name", "anima")
    bsize = max_export_batch_size or tracing_cfg.get("max_export_batch_size", 512)
    delay = schedule_delay_millis or tracing_cfg.get("schedule_delay_millis", 5000)

    if not enabled:
        logger.info("[Tracing] Tracing disabled — using NoOpTracerProvider")
        from opentelemetry import trace
        trace.set_tracer_provider(trace.ProxyTracerProvider())
        _TRACER_INITIALIZED = True
        return trace.get_tracer(service_name)

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    from .exporter import StatsSpanExporter

    resource = Resource.create({
        "service.name": service_name,
        "service.version": (
            __import__("anima").__version__
            if hasattr(__import__("anima"), "__version__")
            else "unknown"
        ),
    })

    provider = TracerProvider(resource=resource)

    # ── StatsStore SQLite exporter (always on when tracing enabled) ──
    stats_exporter = StatsSpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(stats_exporter))
    logger.info("[Tracing] StatsSpanExporter → SQLite (sync write)")

    # ── OTLP gRPC exporter (dual-write to OTel Collector) ──
    if otlp_cfg.get("enabled", False):
        _init_otlp_exporter(provider, otlp_cfg, bsize, delay)

    trace.set_tracer_provider(provider)
    logger.info(f"[Tracing] Initialized: service={service_name}")
    _TRACER_INITIALIZED = True

    # ── Initialize OTel Metrics ──
    otlp_metrics_endpoint = otlp_cfg.get("endpoint") if otlp_cfg.get("enabled") else None
    try:
        from .metrics import init_metrics
        init_metrics(service_name=service_name, otlp_endpoint=otlp_metrics_endpoint)
    except Exception as e:
        logger.warning(f"[Tracing] Metrics init failed (non-fatal): {e}")

    return trace.get_tracer(service_name)


def _init_otlp_exporter(
    provider: Any,
    otlp_cfg: dict[str, Any],
    batch_size: int,
    schedule_delay: int,
) -> None:
    """Add OTLP gRPC exporter to the TracerProvider for dual-write.

    Gracefully degrades if the exporter package is missing or the endpoint
    is unreachable — spans still go to StatsStore.
    """
    endpoint = otlp_cfg.get("endpoint", "http://localhost:4317")
    protocol = otlp_cfg.get("protocol", "grpc")

    try:
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        if protocol == "grpc":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
        else:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
    except ImportError:
        logger.warning(
            "[Tracing] opentelemetry-exporter-otlp not installed — OTLP export disabled. "
            "Run: pip install opentelemetry-exporter-otlp-proto-grpc"
        )
        return

    otlp_exporter_kwargs: dict[str, Any] = {
        "endpoint": endpoint,
        "timeout": 10,
    }
    headers = otlp_cfg.get("headers")
    if headers and isinstance(headers, dict):
        otlp_exporter_kwargs["headers"] = headers

    otlp_exporter = OTLPSpanExporter(**otlp_exporter_kwargs)
    provider.add_span_processor(
        BatchSpanProcessor(
            otlp_exporter,
            max_export_batch_size=batch_size,
            schedule_delay_millis=schedule_delay,
        )
    )
    logger.info(
        f"[Tracing] OTLPSpanExporter → {endpoint} (batch, {protocol}) — dual-write enabled"
    )
