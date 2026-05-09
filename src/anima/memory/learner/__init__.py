"""PeriodicLearner — scheduled AI-driven learning module.

Provides conversation summarization, pattern extraction, and meme candidate generation.
Runs on configurable intervals via AsyncScheduler.
"""

from .summarizer import ConversationSummarizer
from .pattern_extractor import PatternExtractor
from .meme_discovery import MemeDiscoverer
from .engine import PeriodicLearner

__all__ = [
    "ConversationSummarizer",
    "PatternExtractor",
    "MemeDiscoverer",
    "PeriodicLearner",
]
