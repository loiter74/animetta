"""Inspection checks — individual verification probes.

Each check returns a CheckResult:
- health.py — component-level async probes (LLM, TTS, ASR, Chroma, etc.)
- pipeline.py — end-to-end conversation smoke test via Socket.IO
- consistency.py — data layer health (StatsStore, Chroma, log files)
- metrics.py — observability pipeline self-check (Prometheus metrics endpoint)
"""

from anima.inspection.checks.health import check_all_components
from anima.inspection.checks.pipeline import check_conversation_pipeline
from anima.inspection.checks.consistency import check_data_consistency
from anima.inspection.checks.metrics import check_metrics_pipeline

__all__ = [
    "check_all_components",
    "check_conversation_pipeline",
    "check_data_consistency",
    "check_metrics_pipeline",
]
