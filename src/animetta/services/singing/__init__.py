"""Singing module — AI Cover via GPT-SoVITS SVC pipeline."""

from .interface import SingingService, PipelineStage, LyricLine, SongResult, PipelineProgress
from .svc_pipeline import SVCPipeline

__all__ = [
    "SingingService",
    "SVCPipeline",
    "PipelineStage",
    "LyricLine",
    "SongResult",
    "PipelineProgress",
]
