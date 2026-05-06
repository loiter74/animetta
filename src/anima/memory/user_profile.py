"""
User Profile module.

Provides dual-track user profiling: static (long-term stable facts) + dynamic (current context).
- static: auto-extracted from wiki/entities/ and wiki/concepts/
- dynamic: built from ShortTermMemory recent N turns
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .models.turns import MemoryTurn
from .stores.short_term import ShortTermMemory
from .wiki.manager import WikiManager
from .wiki.models import PageType

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile data."""

    static: List[str] = field(default_factory=list)
    """Long-term stable facts, e.g. ["likes TypeScript", "uses Vim", "lives in Shanghai"]"""

    dynamic: List[str] = field(default_factory=list)
    """Dynamic information from current conversation context, e.g. ["currently debugging API rate limiting"]"""

    def is_empty(self) -> bool:
        return len(self.static) == 0 and len(self.dynamic) == 0

    def format_for_prompt(self) -> str:
        """Format as text injectable into system prompt."""
        parts: List[str] = []
        if self.static:
            parts.append("## 用户画像 (长期)")
            for s in self.static:
                parts.append(f"- {s}")
        if self.dynamic:
            parts.append("## 当前上下文")
            for d in self.dynamic:
                parts.append(f"- {d}")
        return "\n".join(parts) if parts else ""


class UserProfileBuilder:
    """UserProfile builder.

    Builds static profile from wiki entities/concepts,
    builds dynamic profile from ShortTermMemory.
    """

    def __init__(
        self,
        wiki_manager: Optional[WikiManager] = None,
        short_term: Optional[ShortTermMemory] = None,
    ):
        self._wiki = wiki_manager
        self._short_term = short_term

    def build_static(self, max_items: int = 20) -> List[str]:
        """Extract user-related facts from wiki/entities/ and wiki/concepts/.

        Args:
            max_items: Maximum extraction count

        Returns:
            List of fact texts
        """
        if not self._wiki:
            logger.debug("[UserProfile] WikiManager not available, static profile empty")
            return []

        facts: List[str] = []

        # Extract from entities/
        entity_pages = self._wiki.list_pages(PageType.ENTITY)
        for rel in entity_pages:
            page = self._wiki.read_page(rel)
            if page and page.title:
                # Extract key information from page title and content
                title = page.title.strip()
                # Skip overly generic or meaningless entries
                if title and len(title) > 1:
                    entity_type = self._infer_entity_type(rel, page.content)
                    if entity_type:
                        facts.append(f"用户{entity_type}: {title}")
                    else:
                        facts.append(f"用户相关信息: {title}")

        # Extract from concepts/
        concept_pages = self._wiki.list_pages(PageType.CONCEPT)
        for rel in concept_pages:
            page = self._wiki.read_page(rel)
            if page and page.title:
                title = page.title.strip()
                if title and len(title) > 1:
                    # Attempt to infer concept type (preference, dislike, etc.)
                    concept_type = self._infer_concept_type(rel)
                    if concept_type:
                        facts.append(f"用户{concept_type}: {title}")
                    else:
                        facts.append(f"用户偏好: {title}")

        # Limit count
        return facts[:max_items]

    def build_dynamic(self, session_id: str, recent_n: int = 5) -> List[str]:
        """Build dynamic context from recent N short-term memory turns.

        Args:
            session_id: Session ID
            recent_n: Number of most recent turns to read

        Returns:
            List of context descriptions
        """
        if not self._short_term:
            logger.debug("[UserProfile] ShortTermMemory not available, dynamic profile empty")
            return []

        turns = self._short_term.get_recent(session_id, recent_n)
        if not turns:
            return []

        summaries: List[str] = []
        for turn in turns:
            # Extract keywords/topics from this turn
            user_text = turn.user_input[:80] if turn.user_input else ""
            agent_text = turn.agent_response[:60] if turn.agent_response else ""
            if user_text:
                summaries.append(f"用户: {user_text}")
            if agent_text:
                summaries.append(f"AI: {agent_text}")

        # Limit to reasonable quantity
        return summaries[:recent_n * 2]

    def build(self, session_id: str) -> UserProfile:
        """Fully build UserProfile."""
        return UserProfile(
            static=self.build_static(),
            dynamic=self.build_dynamic(session_id),
        )

    # ── Type inference ──────────────────────────────────

    @staticmethod
    def _infer_entity_type(rel: str, content: str) -> Optional[str]:
        """Infer entity type from entity page path."""
        rel_lower = rel.lower()
        if "pet" in rel_lower or "猫" in content or "狗" in content:
            return "的宠物"
        if "location" in rel_lower or "住" in rel_lower:
            return "的所在地"
        if "name" in rel_lower:
            return "的名字"
        return None

    @staticmethod
    def _infer_concept_type(rel: str) -> Optional[str]:
        """Infer concept type from concept page path."""
        rel_lower = rel.lower()
        if "like" in rel_lower or "prefer" in rel_lower:
            return "喜欢"
        if "dislike" in rel_lower or "hate" in rel_lower:
            return "不喜欢"
        if "want" in rel_lower or "goal" in rel_lower:
            return "想要"
        if "interest" in rel_lower:
            return "感兴趣"
        # Try to infer from filename prefix
        from pathlib import Path
        stem = Path(rel).stem
        for prefix, label in [("like-", "喜欢"), ("dislike-", "不喜欢"),
                               ("want-", "想要"), ("interest-", "感兴趣")]:
            if stem.startswith(prefix):
                return label
        return None
