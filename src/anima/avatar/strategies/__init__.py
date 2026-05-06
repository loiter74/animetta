"""
Timeline Strategy Module

This module defines the interface for emotion timeline calculation strategies.
All strategies must implement the ITimelineStrategy interface.
"""

from .base import ITimelineStrategy, TimelineSegment, TimelineConfig
from .position import PositionBasedStrategy
from .duration import DurationBasedStrategy
from .intensity import IntensityBasedStrategy

__all__ = [
    "ITimelineStrategy",
    "TimelineSegment",
    "TimelineConfig",
    "PositionBasedStrategy",
    "DurationBasedStrategy",
    "IntensityBasedStrategy",
]
