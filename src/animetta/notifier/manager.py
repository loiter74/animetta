"""
NotifierManager — orchestrates alert delivery across channels.

Receives Alertmanager webhook payload, parses to Alert objects,
and fans out to all enabled notifier plugins concurrently.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Normalized alert representation from Alertmanager payload."""

    status: str  # "firing" or "resolved"
    name: str
    severity: str = "warning"
    summary: str = ""
    description: str = ""
    starts_at: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "name": self.name,
            "severity": self.severity,
            "summary": self.summary,
            "description": self.description,
            "starts_at": self.starts_at,
            "labels": self.labels,
            "annotations": self.annotations,
        }


def parse_alertmanager_payload(payload: dict[str, Any]) -> list[Alert]:
    """Parse Alertmanager webhook JSON into a list of Alert objects.

    Standard Alertmanager v4 webhook format:
        {"version": "4", "status": "firing|resolved", "alerts": [...]}
    """
    alerts: list[Alert] = []
    status = payload.get("status", "firing")

    for a in payload.get("alerts", []):
        labels = a.get("labels", {})
        annotations = a.get("annotations", {})

        severity = labels.get("severity", "warning")
        alert = Alert(
            status=a.get("status", status),
            name=labels.get("alertname", "Unknown"),
            severity=severity,
            summary=annotations.get("summary", a.get("annotations", {}).get("description", "")),
            description=annotations.get("description", ""),
            starts_at=a.get("startsAt", ""),
            labels=labels,
            annotations=annotations,
        )
        alerts.append(alert)

    return alerts


class NotifierManager:
    """Orchestrates alert delivery across all enabled notifier channels.

    Reads notifier config from environment variables (no YAML dependency
    since this runs in a lightweight Docker container).
    """

    def __init__(self):
        from .base import get_notifier_registry

        self._registry = get_notifier_registry()
        self._enabled: list[str] = []

        # Determine which channels are enabled based on env vars
        if os.getenv("NOTIFIER_DISCORD_WEBHOOK_URL"):
            self._enabled.append("discord")
        if os.getenv("NOTIFIER_FEISHU_WEBHOOK_URL"):
            self._enabled.append("feishu")
        if os.getenv("NOTIFIER_SMTP_HOST") and os.getenv("NOTIFIER_EMAIL_TO"):
            self._enabled.append("email")

        logger.info(
            "NotifierManager initialized: enabled=%s, registered=%s",
            self._enabled,
            list(self._registry.keys()),
        )

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process an Alertmanager webhook payload.

        Returns a dict mapping channel_name → success (bool).
        """
        import asyncio

        alerts = parse_alertmanager_payload(payload)
        status = payload.get("status", "firing")

        if not alerts:
            logger.warning("No alerts found in payload")
            return {"error": "no alerts"}

        # Fan out to all enabled notifiers concurrently
        tasks: dict[str, asyncio.Task] = {}
        for channel in self._enabled:
            cls = self._registry.get(channel)
            if cls is None:
                logger.warning("Notifier '%s' not registered, skipping", channel)
                continue

            instance = cls()
            alert_dicts = [a.to_dict() for a in alerts]
            tasks[channel] = asyncio.ensure_future(instance.send(alert_dicts, status))

        results: dict[str, bool] = {}
        for channel, task in tasks.items():
            try:
                results[channel] = await task
            except Exception:
                logger.exception("Notifier '%s' failed", channel)
                results[channel] = False

        return results
