"""
Memory middleware: automatically handles memory before and after LLM calls.

Workflow:
- before_llm_call: Retrieve relevant memories + user profile, inject into system prompt
- after_llm_call: Store conversation into memory system (delegated to output_node)

Safe degradation: any failure logs warning, does not block main flow.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryMiddleware:
    """Automatic memory injection middleware.

    Integrated in LangGraph llm_node, calls before/after methods.
    Follows the existing ConfigStore pattern to obtain MemorySystem instances.
    """

    def __init__(self, memory_system: Optional[Any] = None):
        self._memory_system = memory_system

    # ── before LLM call ──────────────────────────

    async def before_llm_call(
        self,
        session_id: str,
        user_input: str,
        base_prompt: Optional[str] = None,
    ) -> Tuple[str, Optional[Dict]]:
        """Before LLM call: retrieve memory + profile → build injection text.

        Args:
            session_id: Session ID
            user_input: User input text
            base_prompt: Base system prompt

        Returns:
            (enriched_prompt, metadata)
            - enriched_prompt: Injected system prompt
            - metadata: Contains memory and profile info (for debugging/logging)
        """
        if not self._memory_system:
            logger.debug("[MemoryMiddleware] MemorySystem not configured, skipping")
            return base_prompt or "", None

        metadata: Dict = {}
        injection_parts: List[str] = []

        try:
            # 1. Retrieve relevant memories (MemoryTurns + MemoryEntries)
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
            # 2. Retrieve user profile
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

        # 3. Assemble injection block
        injection_block = "\n\n---\n\n".join(injection_parts)

        # 4. Inject into system prompt
        enriched = self._inject_into_prompt(base_prompt or "", injection_block)

        logger.info(
            f"[MemoryMiddleware] injected: "
            f"memory={metadata.get('memory_count', 0)}, "
            f"profile_static={metadata.get('profile_static', 0)}, "
            f"profile_dynamic={metadata.get('profile_dynamic', 0)}"
        )
        return enriched, metadata

    # ── after LLM call ───────────────────────────

    async def after_llm_call(
        self,
        session_id: str,
        user_input: str,
        agent_response: str,
    ) -> None:
        """After LLM call: mark turn complete (for any additional post-processing).

        Note: Actual memory storage is done by output_node._store_conversation_to_memory.
        This method is for any additional post-processing that may be needed (e.g. notifying fact extractors).
        """
        # Storage is handled by output_node, only post-processing marker here
        logger.debug(f"[MemoryMiddleware] turn completed: {session_id}")

    # ── Formatting ──────────────────────────────────────────────

    @staticmethod
    def _format_memory_turns(memory_turns: List[Any], max_items: int = 5) -> str:
        """Format memory turns as text."""
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
        """Inject memory/profile content into the system prompt."""
        parts = [base_prompt, injection_block]
        parts.append(
            "Please refer to the above memories and user profile when responding. "
            "If no relevant information is available, respond naturally."
        )
        return "\n\n---\n\n".join(parts)
