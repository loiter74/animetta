"""
Tracing bootstrap — one-call initialization of OpenTelemetry TracerProvider.

Reads config/observability.yaml and sets up:
- TracerProvider with BatchSpanProcessor(StatsSpanExporter)
- Or NoOpTracerProvider when disabled
"""

import os
import signal
from typing import Optional
from pathlib import Path
from loguru import logger

import yaml


def _load_tracing_config() -> dict:
    """Load tracing config from config/observability.yaml."""
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "observability.yaml"
    if not config_path.exists():
        logger.info("[Tracing] No observability.yaml found — using defaults (tracing=disabled)")
        return {"enabled": False}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("tracing", {"enabled": False})
    except Exception as e:
        logger.warning(f"[Tracing] Failed to load config: {e}")
        return {"enabled": False}


def init_tracing(
    service_name: Optional[str] = None,
    enabled: Optional[bool] = None,
    max_export_batch_size: int = 512,
    schedule_delay_millis: int = 5000,
):
    """Initialize the OpenTelemetry tracing pipeline.

    Args:
        service_name: Service name for Resource attributes.
        enabled: Override config file's enabled flag.
        max_export_batch_size: BatchSpanProcessor batch size.
        schedule_delay_millis: BatchSpanProcessor interval (ms).

    Returns:
        The configured Tracer (or NoOpTracer if disabled).
    """
    cfg = _load_tracing_config()

    if enabled is None:
        enabled = cfg.get("enabled", True)
    if service_name is None:
        service_name = cfg.get("service_name", "anima")
    bsize = max_export_batch_size or cfg.get("max_export_batch_size", 512)
    delay = schedule_delay_millis or cfg.get("schedule_delay_millis", 5000)

    if not enabled:
        logger.info("[Tracing] Tracing disabled — using NoOpTracerProvider")
        from opentelemetry import trace
        trace.set_tracer_provider(trace.ProxyTracerProvider())
        return trace.get_tracer(service_name)

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    from .exporter import StatsSpanExporter

    resource = Resource.create({
        "service.name": service_name,
        "service.version": __import__("anima").__version__ if hasattr(__import__("anima"), "__version__") else "unknown",
    })

    provider = TracerProvider(resource=resource)

    exporter = StatsSpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    logger.info(f"[Tracing] Initialized: service={service_name} (sync write)")

    return trace.get_tracer(service_name)
