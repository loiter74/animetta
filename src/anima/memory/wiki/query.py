"""QUERY workflow - retrieve context from wiki for LLM prompts."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..models.base import SearchResult
from ..models.turns import MemoryTurn
from .manager import WikiManager
from .models import PageType

logger = logging.getLogger(__name__)


class WikiQuery:
    """
    QUERY workflow.

    When the LLM needs context:
    1. Read wiki/index.md to locate relevant pages.
    2. Use hybrid search (SQLite FTS5 + Chroma) for semantic retrieval.
    3. Load recent source summaries.
    4. Format as context for the system prompt.
    """

    def __init__(self, wiki: WikiManager):
        self._wiki = wiki

    async def search(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0.3,
    ) -> List[SearchResult]:
        """Search the wiki via hybrid search."""
        try:
            return self._wiki.search(query, max_results=max_results)
        except Exception as e:
            logger.warning(f"[WikiQuery] search failed: {e}")
            return []

    def load_context(self, query: str = "", max_results: int = 5) -> str:
        """
        Build a context string for the LLM system prompt.

        Combines:
        - Recent source summaries (today + yesterday)
        - Search results for the query (if provided)
        """
        parts: List[str] = []

        # 1. today's source summary
        today = datetime.now()
        today_src = self._wiki.read_page(f"sources/{today.strftime('%Y-%m-%d')}.md")
        if today_src:
            parts.append(f"## 今日对话摘要\n{today_src.content}")

        # 2. yesterday's summary (for continuity)
        from datetime import timedelta
        yesterday = today - timedelta(days=1)
        yest_src = self._wiki.read_page(f"sources/{yesterday.strftime('%Y-%m-%d')}.md")
        if yest_src:
            parts.append(f"## 昨日对话摘要\n{yest_src.content}")

        # 3. semantic search
        if query:
            try:
                results = self._wiki.search(query, max_results=max_results)
                if results:
                    search_parts = []
                    for r in results[:max_results]:
                        search_parts.append(f"- [{r.path}] (score={r.score:.2f})\n  {r.text[:200]}")
                    parts.append("## 相关记忆\n" + "\n".join(search_parts))
            except Exception as e:
                logger.debug(f"[WikiQuery] semantic search skipped: {e}")

        return "\n\n---\n\n".join(parts) if parts else ""

    def search_turns(
        self,
        query: str,
        session_id: str,
        max_results: int = 5,
    ) -> List[MemoryTurn]:
        """
        Convert search results into MemoryTurn objects for backward compat.

        Called by MemorySystem.retrieve_context().
        """
        turns: List[MemoryTurn] = []
        try:
            results = self._wiki.search(query, max_results=max_results)
            for sr in results:
                turns.append(MemoryTurn(
                    turn_id=f"wiki_{sr.path}_{sr.start_line}",
                    session_id=session_id,
                    timestamp=datetime.now(),
                    user_input=self._extract_user(sr.text),
                    agent_response=self._extract_agent(sr.text),
                    emotions=[],
                    metadata={"path": sr.path, "score": sr.score, "source": "wiki"},
                    importance=sr.score,
                ))
        except Exception as e:
            logger.warning(f"[WikiQuery] search_turns failed: {e}")
        return turns

    # ── helpers ─────────────────────────────────────────────

    @staticmethod
    def _extract_user(text: str) -> str:
        for line in text.split("\n"):
            if line.startswith("**User**") or line.startswith("**User**:"):
                return line.split(":", 1)[-1].strip()
        return ""

    @staticmethod
    def _extract_agent(text: str) -> str:
        for line in text.split("\n"):
            if line.startswith("**AI**") or line.startswith("**AI**:"):
                return line.split(":", 1)[-1].strip()
        return ""
