"""Inspection checks — individual verification probes.

Each check returns a CheckResult:
- health.py — component-level async probes (LLM, TTS, ASR, Chroma, etc.)
- pipeline.py — end-to-end conversation smoke test via Socket.IO
- consistency.py — data layer health (StatsStore, Chroma, log files)
- metrics.py — observability pipeline self-check (Prometheus metrics endpoint)
"""


__all__ = [
    "check_all_components",
    "check_conversation_pipeline",
    "check_data_consistency",
    "check_metrics_pipeline",
]
