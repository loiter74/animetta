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
from .wiki.mbti_store import MBTIStore
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
        mbti_store: Optional[MBTIStore] = None,
    ):
        self._wiki = wiki
        self._short_term = short_term
        self._mbti_store = mbti_store
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

        # 4. MBTI personality profile (if configured)
        mbti_context = self._build_mbti_context()
        if mbti_context:
            parts.append(mbti_context)

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

    # ── MBTI context ──────────────────────────────────────────

    def _build_mbti_context(self) -> str:
        """Build MBTI personality context section.

        Reads the current MBTI profile from MBTIStore and formats
        it as a contextual note for the LLM.

        Returns:
            str: Formatted MBTI section, or empty string if not configured.
        """
        if not self._mbti_store:
            return ""

        profile = self._mbti_store.load_profile()
        if not profile:
            return ""

        dims = profile.get("dimensions", {})
        mbti_type = profile.get("type", "N/A")
        description = profile.get("description", "")

        lines = ["## MBTI 人格状态"]

        ei = dims.get("ei", 50)
        sn = dims.get("sn", 50)
        tf = dims.get("tf", 50)
        jp = dims.get("jp", 50)

        # Dimension descriptions (range-based for flexibility)
        def _dim_label(val: int, low_label: str, high_label: str) -> str:
            if val <= 35:
                return f"明显{low_label}"
            elif val <= 45:
                return f"偏{low_label}"
            elif val <= 55:
                return "平衡状态"
            elif val <= 65:
                return f"偏{high_label}"
            else:
                return f"明显{high_label}"

        ei_label = _dim_label(100 - ei, "内向", "外向")  # inverted: lower ei = more introverted
        sn_label = _dim_label(sn, "实感", "直觉")
        tf_label = _dim_label(tf, "共情", "理性")
        jp_label = _dim_label(jp, "随性", "计划")

        lines.append(f"当前类型：{mbti_type}（E/I {ei_label}，S/N {sn_label}，T/F {tf_label}，J/P {jp_label}）")
        if description:
            lines.append(f"\n{description}")

        lines.append("\n（该人格倾向动态调整于对话观察，为你的回应风格提供参考——你仍然可以自由发挥）")

        return "\n".join(lines)

    def invalidate_cache(self, path: Optional[str] = None) -> None:
        if path:
            self._cache.pop(path, None)
        else:
            self._cache.clear()
