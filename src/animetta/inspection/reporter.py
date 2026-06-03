"""Inspection reporter — persistence and alerting.

store_report(): serialize InspectionReport to StatsStore SQLite.
send_alert(): format Alertmanager webhook payload and fan out via NotifierManager.
"""

from __future__ import annotations

import json

from loguru import logger

from animetta.notifier.manager import NotifierManager
from animetta.orchestration.graph.stats_store import get_stats_store

from .models import InspectionReport


async def store_report(report: InspectionReport) -> None:
    """Persist an inspection report to the StatsStore SQLite database.

    Serializes the checks dict to JSON and delegates to
    StatsStore.store_inspection_report().

    Args:
        report: Completed InspectionReport to persist.
    """
    checks_json = json.dumps(
        {name: c.model_dump() for name, c in report.checks.items()},
        ensure_ascii=False,
    )
    store = await get_stats_store()
    await store.store_inspection_report(
        run_id=report.run_id,
        started_at=report.started_at,
        finished_at=report.finished_at,
        overall_ok=report.overall_ok,
        checks_json=checks_json,
    )
    logger.info(f"[inspection:reporter] Report stored: {report.summary}")


async def send_alert(report: InspectionReport) -> None:
    """Send alert notification if the inspection report indicates failures.

    Formats a synthetic Alertmanager v4 webhook payload with failed check
    details and fans out via NotifierManager.handle().

    If NotifierManager is not configured (no env vars set), silently skips
    with a debug log — does not crash.

    Args:
        report: InspectionReport to check for failures.
    """
    if report.overall_ok:
        return

    # Build a human-readable message with failed check names and errors
    failed_details: list[str] = []
    for name, check in report.checks.items():
        if not check.ok:
            err = check.error or "no error detail"
            failed_details.append(f"  • {name}: {err}")

    message = (
        f"Inspection {report.run_id[:8]} FAILED\n"
        f"Started: {report.started_at}\n"
        f"Failed checks:\n"
        + "\n".join(failed_details)
    )

    # Synthetic Alertmanager v4 webhook payload
    payload = {
        "version": "4",
        "status": "firing",
        "alerts": [
            {
                "labels": {
                    "alertname": "InspectionFailed",
                    "severity": "warning",
                },
                "annotations": {
                    "summary": message,
                },
            }
        ],
    }

    try:

        notifier = NotifierManager()
        if not notifier._enabled:
            logger.debug(
                "[inspection:reporter] NotifierManager has no enabled channels, "
                "skipping alert send."
            )
            return

        await notifier.handle(payload)
        logger.info(f"[inspection:reporter] Alert sent for {report.run_id[:8]}")
    except Exception:
        logger.warning(
            f"[inspection:reporter] Failed to send alert for {report.run_id[:8]} "
            f"(NotifierManager not available or misconfigured)"
        )
