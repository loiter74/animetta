"""Singing module — AI Cover via GPT-SoVITS SVC pipeline."""

from .interface import LyricLine, PipelineProgress, PipelineStage, SingingService, SongResult
from .svc_pipeline import SVCPipeline

__all__ = [
    "SingingService",
    "SVCPipeline",
    "PipelineStage",
    "LyricLine",
    "SongResult",
    "PipelineProgress",
]
