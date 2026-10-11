"""Singing module — AI Cover via GPT-SoVITS SVC pipeline."""

from importlib import import_module
from typing import Any

from .interface import LyricLine, PipelineProgress, PipelineStage, SingingService, SongResult


def __getattr__(name: str) -> Any:
    if name != "SVCPipeline":
        raise AttributeError(name)
    value = import_module(".svc_pipeline", __name__).SVCPipeline
    globals()[name] = value
    return value


__all__ = [
    "SingingService",
    "SVCPipeline",
    "PipelineStage",
    "LyricLine",
    "SongResult",
    "PipelineProgress",
]
