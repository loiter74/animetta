"""
Anima Notifier — Plugin-based alert notification relay.

Receives Alertmanager webhooks and routes alerts to configured
notification channels (Discord, Feishu, Email, etc.).

Plugins register via @register_notifier(name) decorator.
"""

from .base import NotifierBase, get_notifier_registry, register_notifier
from .manager import Alert, NotifierManager, parse_alertmanager_payload

__all__ = [
    "NotifierBase",
    "register_notifier",
    "get_notifier_registry",
    "NotifierManager",
    "Alert",
    "parse_alertmanager_payload",
]
