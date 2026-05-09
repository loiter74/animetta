"""FuzzyLayer — runtime fuzzification layer.

No persistent storage. Reads from Wiki + ShortTermMemory at runtime,
produces natural language fuzzy narratives for LLM context injection.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .wiki.manager import WikiManager
from .wiki.models import PageType
from .stores.short_term import ShortTermMemory
from .models.turns import MemoryTurn

logger = logging.getLogger(__name__)


class FuzzyLayer:
    """Runtime fuzzification layer — no independent storage.

    On each LLM call, synthesizes "I remember..." style narratives
    from wiki + short-term memory. Replaces the old FuzzyMemoryStore +
    FuzzyConsolidator architecture.
    """

    def __init__(
        self,
        wiki: Optional[WikiManager] = None,
        short_term: Optional[ShortTermMemory] = None,
    ):
        self._wiki = wiki
        self._short_term = short_term
        self._cache: Dict[str, Tuple[str, float]] = {}

    async def build_fuzzy_context(
        self,
        session_id: str,
        query: str,
        max_synthesis: int = 3,
        include_recent_turns: bool = True,
    ) -> str:
        """Build fuzzy narrative context for LLM injection.

        Returns formatted markdown string, empty string if nothing found.
        """
        parts: List[str] = []

        # 1. Recent short-term turns
        if include_recent_turns:
            turns = self._get_recent_turns(session_id, 5)
            if turns:
                lines = ["## 最近对话"]
                for t in turns:
                    user = (t.user_input or "")[:100]
                    agent = (t.agent_response or "")[:100]
                    lines.append(f"- 用户: {user}")
                    if agent:
                        lines.append(f"  回应: {agent}")
                parts.append("\n".join(lines))

        # 2. Wiki synthesis pages
        synthesis = self._get_relevant_synthesis(query, max_synthesis)
        if synthesis:
            parts.append("## 我记得的\n" + "\n".join(f"- {s}" for s in synthesis))

        # 3. User profile from wiki entities
        profile = self._get_profile_text(session_id)
        if profile:
            parts.append(f"## 用户画像\n{profile}")

        return "\n\n---\n\n".join(parts) if parts else ""

    # ── internal helpers ────────────────────────────────────

    def _get_recent_turns(self, session_id: str, n: int) -> List[MemoryTurn]:
        if not self._short_term:
            return []
        return self._short_term.get_recent(session_id, n)

    def _get_relevant_synthesis(self, query: str, max_items: int) -> List[str]:
        if not self._wiki:
            return []
        now = datetime.now().timestamp()

        # Check cache (5min TTL)
        for path, (text, ts) in list(self._cache.items()):
            if now - ts > 300:
                del self._cache[path]

        # Read from wiki synthesis pages (newest first)
        pages = self._wiki.list_pages(PageType.SYNTHESIS)
        results: List[str] = []
        for rel in reversed(pages):
            if len(results) >= max_items:
                break
            if rel in self._cache:
                text, _ = self._cache[rel]
                results.append(text)
                continue
            page = self._wiki.read_page(rel)
            if page:
                text = page.content[:200]
                self._cache[rel] = (text, now)
                results.append(text)
        return results[:max_items]

    def _get_profile_text(self, session_id: str) -> str:
        if not self._wiki:
            return ""
        parts: List[str] = []
        for rel in self._wiki.list_pages():
            if rel.startswith("entities/"):
                page = self._wiki.read_page(rel)
                if page and page.content:
                    parts.append(f"- {page.content[:150]}")
        return "\n".join(parts)

    def invalidate_cache(self, path: Optional[str] = None) -> None:
        if path:
            self._cache.pop(path, None)
        else:
            self._cache.clear()
