"""
记忆中间件: 在 LLM 调用前后自动处理记忆.

工作流程:
- before_llm_call: 检索相关记忆 + 用户画像, 注入 system prompt
- after_llm_call: 存储对话到记忆系统 (委托 output_node)

可安全降级: 任何失败记录 warning, 不阻塞主流程.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryMiddleware:
    """自动记忆注入中间件.

    在 LangGraph llm_node 中集成, 调用 before/after 方法.
    遵循现有 ConfigStore 模式获取 MemorySystem 实例.
    """

    def __init__(self, memory_system: Optional[Any] = None):
        self._memory_system = memory_system

    # ── before LLM call (Task 5.2) ──────────────────────────

    async def before_llm_call(
        self,
        session_id: str,
        user_input: str,
        base_prompt: Optional[str] = None,
    ) -> Tuple[str, Optional[Dict]]:
        """LLM 调用前: 检索记忆 + 画像 → 构建注入文本.

        Args:
            session_id: 会话 ID
            user_input: 用户输入文本
            base_prompt: 基础的 system prompt

        Returns:
            (enriched_prompt, metadata)
            - enriched_prompt: 注入后的 system prompt
            - metadata: 包含记忆和画像信息的元数据 (用于调试/日志)
        """
        if not self._memory_system:
            logger.debug("[MemoryMiddleware] MemorySystem not configured, skipping")
            return base_prompt or "", None

        metadata: Dict = {}
        injection_parts: List[str] = []

        try:
            # 1. 检索相关记忆 (MemoryTurns + MemoryEntries)
            memory_turns = await self._memory_system.retrieve_context(
                query=user_input,
                session_id=session_id,
                max_turns=5,
            )
            if memory_turns:
                memory_text = self._format_memory_turns(memory_turns)
                if memory_text:
                    injection_parts.append(memory_text)
                    metadata["memory_count"] = len(memory_turns)
        except Exception as e:
            logger.warning(f"[MemoryMiddleware] memory retrieval failed: {e}")

        try:
            # 2. 检索用户画像
            profile = self._memory_system.get_profile(session_id)
            if profile and not profile.is_empty():
                profile_text = profile.format_for_prompt()
                if profile_text:
                    injection_parts.append(profile_text)
                    metadata["profile_static"] = len(profile.static)
                    metadata["profile_dynamic"] = len(profile.dynamic)
        except Exception as e:
            logger.warning(f"[MemoryMiddleware] profile retrieval failed: {e}")

        if not injection_parts:
            logger.debug(f"[MemoryMiddleware] no memory or profile to inject")
            return base_prompt or "", metadata

        # 3. 組裝注入文本
        injection_block = "\n\n---\n\n".join(injection_parts)

        # 4. 注入到 system prompt
        enriched = self._inject_into_prompt(base_prompt or "", injection_block)

        logger.info(
            f"[MemoryMiddleware] injected: "
            f"memory={metadata.get('memory_count', 0)}, "
            f"profile_static={metadata.get('profile_static', 0)}, "
            f"profile_dynamic={metadata.get('profile_dynamic', 0)}"
        )
        return enriched, metadata

    # ── after LLM call (Task 5.3) ───────────────────────────

    async def after_llm_call(
        self,
        session_id: str,
        user_input: str,
        agent_response: str,
    ) -> None:
        """LLM 调用后: 标记轮次结束 (如需额外后处理).

        注意: 实际记忆存储由 output_node._store_conversation_to_memory 完成。
        此方法用于可能需要的额外后处理（如通知事实提取器）。
        """
        # 存储由 output_node 负责, 此处仅做后处理标记
        logger.debug(f"[MemoryMiddleware] turn completed: {session_id}")

    # ── 格式化 ──────────────────────────────────────────────

    @staticmethod
    def _format_memory_turns(memory_turns: List[Any], max_items: int = 5) -> str:
        """格式化记忆轮次为文本."""
        selected = memory_turns[:max_items]
        lines = ["## Related Memories"]
        for i, turn in enumerate(selected, 1):
            user_text = getattr(turn, "user_input", "")
            agent_text = getattr(turn, "agent_response", "")
            if user_text or agent_text:
                lines.append(f"{i}. You said: {user_text}")
                if agent_text:
                    lines.append(f"   I replied: {agent_text}")
        return "\n".join(lines) if len(lines) > 1 else ""

    @staticmethod
    def _inject_into_prompt(base_prompt: str, injection_block: str) -> str:
        """将记忆/画像内容注入到 system prompt."""
        parts = [base_prompt, injection_block]
        parts.append(
            "Please refer to the above memories and user profile when responding. "
            "If no relevant information is available, respond naturally."
        )
        return "\n\n---\n\n".join(parts)
