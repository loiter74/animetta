"""Dual-perception domain: local vision agent plus deterministic environment judge."""

from .consensus import combine
from .environment import EnvironmentJudge, EnvironmentThresholds
from .models import (
    EnvironmentVerdict,
    PerceptionConsensus,
    PerceptionDanger,
    VisionVerdict,
)
from .service import DualPerceptionService, build_default_service

__all__ = [
    "DualPerceptionService",
    "EnvironmentJudge",
    "EnvironmentThresholds",
    "EnvironmentVerdict",
    "PerceptionConsensus",
    "PerceptionDanger",
    "VisionVerdict",
    "build_default_service",
    "combine",
]
