"""Wiki memory architecture.

Karpathy-style wiki management for AI companion memory:
- raw/   : immutable conversation logs
- wiki/  : curated knowledge base (AI-managed)
  - entities/  : people, characters, projects
  - concepts/  : preferences, interests, patterns
  - sources/   : per-day conversation summaries
  - synthesis/ : cross-source analysis
"""

from .manager import WikiManager
from .ingestor import WikiIngestor
from .query import WikiQuery
from .lint import WikiLint, LintReport
from .organizer import WikiOrganizer
from .models import WikiPage, PageType

__all__ = [
    "WikiManager",
    "WikiIngestor",
    "WikiQuery",
    "WikiLint",
    "LintReport",
    "WikiOrganizer",
    "WikiPage",
    "PageType",
]
