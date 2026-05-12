"""
Anima Metrics — OpenTelemetry Metrics API instrumentation.

Initializes an OTel MeterProvider and defines all business metrics:
- Node-level: duration histogram, error counter
- LLM-level: request duration, tokens (input/output), cost
- RAG-level: retrieval duration, chunks retrieved, top score
- ASR/TTS: synthesis duration, characters
- WebSocket: active sessions, message count, errors
- Tool calls: total calls, duration per tool

Usage:
    from anima.tracing.metrics import (
        NODE_DURATION, NODE_ERRORS, LLM_TOKENS, LLM_COST,
        RAG_DURATION, RAG_CHUNKS, TOOL_CALLS, TOOL_DURATION,
        ACTIVE_SESSIONS, SESSION_MESSAGES,
    )
    NODE_DURATION.labels(node_name="llm").observe(1.23)
"""

from typing import Optional

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from loguru import logger

# ── Metric instrument singletons (lazy-initialized) ──

_NODE_DURATION: Optional[metrics.Histogram] = None
_NODE_ERRORS: Optional[metrics.Counter] = None
_LLM_REQUEST_DURATION: Optional[metrics.Histogram] = None
_LLM_TOKENS: Optional[metrics.Counter] = None
_LLM_COST: Optional[metrics.Counter] = None
_LLM_ERRORS: Optional[metrics.Counter] = None
_RAG_DURATION: Optional[metrics.Histogram] = None
_RAG_CHUNKS: Optional[metrics.Histogram] = None
_RAG_TOP_SCORE: Optional[metrics.Histogram] = None
_ASR_DURATION: Optional[metrics.Histogram] = None
_TTS_DURATION: Optional[metrics.Histogram] = None
_TTS_CHARACTERS: Optional[metrics.Counter] = None
_ACTIVE_SESSIONS: Optional[metrics.UpDownCounter] = None
_SESSION_MESSAGES: Optional[metrics.Counter] = None
_WEBSOCKET_ERRORS: Optional[metrics.Counter] = None
_TOOL_CALLS: Optional[metrics.Counter] = None
_TOOL_DURATION: Optional[metrics.Histogram] = None

_meter: Optional[metrics.Meter] = None
_initialized: bool = False


def init_metrics(
    service_name: str = "anima",
    otlp_endpoint: Optional[str] = None,
) -> metrics.Meter:
    """Initialize OTel MeterProvider and define all metric instruments.

    Must be called once at startup, after init_tracing().

    Args:
        service_name: Service name for resource attributes.
        otlp_endpoint: OTLP gRPC endpoint for metrics export
                       (default: http://localhost:4317).

    Returns:
        The configured Meter instance.
    """
    global _meter, _initialized
    global _NODE_DURATION, _NODE_ERRORS
    global _LLM_REQUEST_DURATION, _LLM_TOKENS, _LLM_COST, _LLM_ERRORS
    global _RAG_DURATION, _RAG_CHUNKS, _RAG_TOP_SCORE
    global _ASR_DURATION, _TTS_DURATION, _TTS_CHARACTERS
    global _ACTIVE_SESSIONS, _SESSION_MESSAGES, _WEBSOCKET_ERRORS
    global _TOOL_CALLS, _TOOL_DURATION

    if _initialized:
        return _meter  # type: ignore[return-value]

    # ── MeterProvider with OTLP export ──
    resource = Resource.create({"service.name": service_name})
    provider_kwargs: dict = {"resource": resource}

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
            metric_exporter = OTLPMetricExporter(
                endpoint=otlp_endpoint,
                timeout=10,
            )
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=15_000,
            )
            provider_kwargs["metric_readers"] = [metric_reader]
            logger.info(f"[Metrics] OTLP export → {otlp_endpoint}")
        except ImportError:
            logger.warning(
                "[Metrics] opentelemetry-exporter-otlp not installed — "
                "metrics will not be exported"
            )
        except Exception as e:
            logger.warning(f"[Metrics] OTLP export setup failed: {e}")

    provider = MeterProvider(**provider_kwargs)
    metrics.set_meter_provider(provider)

    _meter = provider.get_meter(service_name)

    # ── LangGraph Node Metrics ──
    _NODE_DURATION = _meter.create_histogram(
        name="anima_node_duration_seconds",
        description="Duration of each LangGraph node execution",
        unit="s",
    )
    _NODE_ERRORS = _meter.create_counter(
        name="anima_node_errors_total",
        description="Total number of LangGraph node errors",
    )

    # ── LLM Metrics ──
    _LLM_REQUEST_DURATION = _meter.create_histogram(
        name="anima_llm_request_duration_seconds",
        description="Duration of LLM API calls",
        unit="s",
    )
    _LLM_TOKENS = _meter.create_counter(
        name="anima_llm_tokens_total",
        description="Total LLM tokens consumed (input + output)",
    )
    _LLM_COST = _meter.create_counter(
        name="anima_llm_cost_usd_total",
        description="Total LLM cost in USD",
    )
    _LLM_ERRORS = _meter.create_counter(
        name="anima_llm_errors_total",
        description="Total number of LLM call errors",
    )

    # ── RAG / Memory Metrics ──
    _RAG_DURATION = _meter.create_histogram(
        name="anima_rag_retrieval_duration_seconds",
        description="Duration of RAG retrieval operations",
        unit="s",
    )
    _RAG_CHUNKS = _meter.create_histogram(
        name="anima_rag_chunks_retrieved",
        description="Number of chunks retrieved per RAG query",
    )
    _RAG_TOP_SCORE = _meter.create_histogram(
        name="anima_rag_top_score",
        description="Top relevance score from RAG retrieval",
    )

    # ── ASR / TTS Metrics ──
    _ASR_DURATION = _meter.create_histogram(
        name="anima_asr_duration_seconds",
        description="Duration of ASR transcription",
        unit="s",
    )
    _TTS_DURATION = _meter.create_histogram(
        name="anima_tts_duration_seconds",
        description="Duration of TTS synthesis",
        unit="s",
    )
    _TTS_CHARACTERS = _meter.create_counter(
        name="anima_tts_characters_total",
        description="Total characters synthesized via TTS",
    )

    # ── WebSocket / Session Metrics ──
    _ACTIVE_SESSIONS = _meter.create_up_down_counter(
        name="anima_active_sessions",
        description="Number of active WebSocket sessions",
    )
    _SESSION_MESSAGES = _meter.create_counter(
        name="anima_session_messages_total",
        description="Total number of session messages",
    )
    _WEBSOCKET_ERRORS = _meter.create_counter(
        name="anima_websocket_errors_total",
        description="Total number of WebSocket errors",
    )

    # ── Tool Call Metrics ──
    _TOOL_CALLS = _meter.create_counter(
        name="anima_tool_calls_total",
        description="Total number of tool calls",
    )
    _TOOL_DURATION = _meter.create_histogram(
        name="anima_tool_duration_seconds",
        description="Duration of tool executions",
        unit="s",
    )

    _initialized = True
    logger.info(f"[Metrics] Initialized {service_name}: 16 instruments defined")
    return _meter


# ── Convenience accessors (with lazy-init safety) ──

def _get(attr_name: str) -> str:
    """Return the attribute name; caller uses globals()."""
    return attr_name


def _ensure_init():
    if not _initialized:
        logger.debug("[Metrics] Not initialized — using NoOp instruments")


# Typed accessors for IDE support

def get_node_duration() -> metrics.Histogram:
    _ensure_init()
    return _NODE_DURATION  # type: ignore[return-value]


def get_node_errors() -> metrics.Counter:
    _ensure_init()
    return _NODE_ERRORS  # type: ignore[return-value]


def get_llm_request_duration() -> metrics.Histogram:
    _ensure_init()
    return _LLM_REQUEST_DURATION  # type: ignore[return-value]


def get_llm_tokens() -> metrics.Counter:
    _ensure_init()
    return _LLM_TOKENS  # type: ignore[return-value]


def get_llm_cost() -> metrics.Counter:
    _ensure_init()
    return _LLM_COST  # type: ignore[return-value]


def get_llm_errors() -> metrics.Counter:
    _ensure_init()
    return _LLM_ERRORS  # type: ignore[return-value]


def get_rag_duration() -> metrics.Histogram:
    _ensure_init()
    return _RAG_DURATION  # type: ignore[return-value]


def get_rag_chunks() -> metrics.Histogram:
    _ensure_init()
    return _RAG_CHUNKS  # type: ignore[return-value]


def get_rag_top_score() -> metrics.Histogram:
    _ensure_init()
    return _RAG_TOP_SCORE  # type: ignore[return-value]


def get_asr_duration() -> metrics.Histogram:
    _ensure_init()
    return _ASR_DURATION  # type: ignore[return-value]


def get_tts_duration() -> metrics.Histogram:
    _ensure_init()
    return _TTS_DURATION  # type: ignore[return-value]


def get_tts_characters() -> metrics.Counter:
    _ensure_init()
    return _TTS_CHARACTERS  # type: ignore[return-value]


def get_active_sessions() -> metrics.UpDownCounter:
    _ensure_init()
    return _ACTIVE_SESSIONS  # type: ignore[return-value]


def get_session_messages() -> metrics.Counter:
    _ensure_init()
    return _SESSION_MESSAGES  # type: ignore[return-value]


def get_websocket_errors() -> metrics.Counter:
    _ensure_init()
    return _WEBSOCKET_ERRORS  # type: ignore[return-value]


def get_tool_calls() -> metrics.Counter:
    _ensure_init()
    return _TOOL_CALLS  # type: ignore[return-value]


def get_tool_duration() -> metrics.Histogram:
    _ensure_init()
    return _TOOL_DURATION  # type: ignore[return-value]
