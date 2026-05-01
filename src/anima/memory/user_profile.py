"""
User Profile 模块.

提供 static (长期稳定事实) + dynamic (当前上下文) 双轨用户画像.
- static: 从 wiki/entities/ 和 wiki/concepts/ 自动提炼
- dynamic: 从 ShortTermMemory 最近 N 轮构建
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
    """用户画像数据."""

    static: List[str] = field(default_factory=list)
    """长期稳定事实, 如 ["喜欢 TypeScript", "使用 Vim", "住在上海"]"""

    dynamic: List[str] = field(default_factory=list)
    """当前对话上下文的动态信息, 如 ["正在调试 API 限流问题"]"""

    def is_empty(self) -> bool:
        return len(self.static) == 0 and len(self.dynamic) == 0

    def format_for_prompt(self) -> str:
        """格式化为 system prompt 可注入的文本."""
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
    """UserProfile 构建器.

    从 wiki entities/concepts 构建 static profile,
    从 ShortTermMemory 构建 dynamic profile.
    """

    def __init__(
        self,
        wiki_manager: Optional[WikiManager] = None,
        short_term: Optional[ShortTermMemory] = None,
    ):
        self._wiki = wiki_manager
        self._short_term = short_term

    def build_static(self, max_items: int = 20) -> List[str]:
        """从 wiki/entities/ 和 wiki/concepts/ 提取用户相关事实.

        Args:
            max_items: 最大提取数

        Returns:
            事实文本列表
        """
        if not self._wiki:
            logger.debug("[UserProfile] WikiManager not available, static profile empty")
            return []

        facts: List[str] = []

        # 从 entities/ 提取
        entity_pages = self._wiki.list_pages(PageType.ENTITY)
        for rel in entity_pages:
            page = self._wiki.read_page(rel)
            if page and page.title:
                # 从页面标题和内容中提取关键信息
                title = page.title.strip()
                # 跳过过于泛化或无意义的条目
                if title and len(title) > 1:
                    entity_type = self._infer_entity_type(rel, page.content)
                    if entity_type:
                        facts.append(f"用户{entity_type}: {title}")
                    else:
                        facts.append(f"用户相关信息: {title}")

        # 从 concepts/ 提取
        concept_pages = self._wiki.list_pages(PageType.CONCEPT)
        for rel in concept_pages:
            page = self._wiki.read_page(rel)
            if page and page.title:
                title = page.title.strip()
                if title and len(title) > 1:
                    # 尝试推断概念类型 (preference-, dislike-, etc.)
                    concept_type = self._infer_concept_type(rel)
                    if concept_type:
                        facts.append(f"用户{concept_type}: {title}")
                    else:
                        facts.append(f"用户偏好: {title}")

        # 限制数量
        return facts[:max_items]

    def build_dynamic(self, session_id: str, recent_n: int = 5) -> List[str]:
        """从最近 N 轮短期记忆构建动态上下文.

        Args:
            session_id: 会话 ID
            recent_n: 读取最近多少轮

        Returns:
            上下文描述列表
        """
        if not self._short_term:
            logger.debug("[UserProfile] ShortTermMemory not available, dynamic profile empty")
            return []

        turns = self._short_term.get_recent(session_id, recent_n)
        if not turns:
            return []

        summaries: List[str] = []
        for turn in turns:
            # 提取本轮的关键词/主题
            user_text = turn.user_input[:80] if turn.user_input else ""
            agent_text = turn.agent_response[:60] if turn.agent_response else ""
            if user_text:
                summaries.append(f"用户: {user_text}")
            if agent_text:
                summaries.append(f"AI: {agent_text}")

        # 控制在合理数量
        return summaries[:recent_n * 2]

    def build(self, session_id: str) -> UserProfile:
        """完整构建 UserProfile."""
        return UserProfile(
            static=self.build_static(),
            dynamic=self.build_dynamic(session_id),
        )

    # ── 类型推断 ─────────────────────────────────────────

    @staticmethod
    def _infer_entity_type(rel: str, content: str) -> Optional[str]:
        """从 entity 页面路径推断实体类型."""
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
        """从 concept 页面路径推断概念类型."""
        rel_lower = rel.lower()
        if "like" in rel_lower or "prefer" in rel_lower:
            return "喜欢"
        if "dislike" in rel_lower or "hate" in rel_lower:
            return "不喜欢"
        if "want" in rel_lower or "goal" in rel_lower:
            return "想要"
        if "interest" in rel_lower:
            return "感兴趣"
        # 尝试从文件名前缀推断
        from pathlib import Path
        stem = Path(rel).stem
        for prefix, label in [("like-", "喜欢"), ("dislike-", "不喜欢"),
                               ("want-", "想要"), ("interest-", "感兴趣")]:
            if stem.startswith(prefix):
                return label
        return None
