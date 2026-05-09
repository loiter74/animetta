"""
Memory middleware: automatically handles memory before and after LLM calls.

Workflow:
- before_llm_call: Uses FuzzyLayer for runtime fuzzification from wiki + short-term,
  then injects into system prompt with user profile.
- after_llm_call: Post-processing marker

Safe degradation: any failure logs warning, does not block main flow.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryMiddleware:
    """Automatic memory injection middleware.

    Integrated in LangGraph llm_node, calls before/after methods.
    Uses MemoryLayer for tiered injection strategy.
    """

    def __init__(self, memory_system: Optional[Any] = None):
        self._memory_system = memory_system

    # ── before LLM call ──────────────────────────

    async def before_llm_call(
        self,
        session_id: str,
        user_input: str,
        base_prompt: Optional[str] = None,
        injection_tier: int = 1,
    ) -> Tuple[str, Optional[Dict]]:
        """Before LLM call: retrieve memory via FuzzyLayer → build injection text."""
        if not self._memory_system:
            logger.debug("[MemoryMiddleware] MemorySystem not configured, skipping")
            return base_prompt or "", None

        metadata: Dict[str, Any] = {"tier": injection_tier}
        injection_parts: List[str] = []

        # Use FuzzyLayer for runtime fuzzification from wiki + short-term
        fuzzy_layer = getattr(self._memory_system, "fuzzy_layer", None)
        if fuzzy_layer:
            try:
                ctx = await fuzzy_layer.build_fuzzy_context(
                    session_id=session_id,
                    query=user_input,
                )
                if ctx:
                    injection_parts.append(ctx)
                    metadata["mode"] = "fuzzy_layer"
            except Exception as e:
                logger.warning(f"[MemoryMiddleware] FuzzyLayer failed: {e}")

        # 3. Retrieve user profile
        try:
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

        # 4. Assemble injection block
        injection_block = "\n\n---\n\n".join(injection_parts)

        # 5. Inject into system prompt
        enriched = self._inject_into_prompt(base_prompt or "", injection_block, injection_tier)

        logger.info(
            f"[MemoryMiddleware] tier={injection_tier}, "
            f"memory={metadata.get('memory_count', 0)}, "
            f"fuzzy={metadata.get('fuzzy_count', 0)}, "
            f"profile_static={metadata.get('profile_static', 0)}"
        )
        return enriched, metadata

    # ── after LLM call ───────────────────────────

    async def after_llm_call(
        self,
        session_id: str,
        user_input: str,
        agent_response: str,
    ) -> None:
        """After LLM call: mark turn complete.

        Storage is handled by output_node._store_conversation_to_memory.
        """
        logger.debug(f"[MemoryMiddleware] turn completed: {session_id}")

    # ── Injection ───────────────────────────────────────────────

    @staticmethod
    def _inject_into_prompt(base_prompt: str, injection_block: str, tier: int = 1) -> str:
        """Inject memory content into the system prompt with tier-aware instruction."""
        parts = [base_prompt, injection_block]

        if tier == 1:
            parts.append(
                "以上是我对用户的模糊记忆。请自然地参考这些记忆来回应，"
                "就像你真正记得这些事一样。如果记忆不太确定，用自然的语气表达。"
            )
        elif tier == 2:
            parts.append(
                "以上是较精确的相关记忆和用户画像。请参考它们来回答用户的问题。"
                "标注了可信度的信息请酌情使用。"
            )
        elif tier == 3:
            parts.append(
                "以上是精确的对话引用。用户似乎想确认某些细节，请尽量准确地参考这些记录。"
            )
        else:
            parts.append(
                "Please refer to the above memories and user profile when responding. "
                "If no relevant information is available, respond naturally."
            )

        return "\n\n---\n\n".join(parts)
