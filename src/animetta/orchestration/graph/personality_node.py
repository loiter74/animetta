"""Personality node — determines current personality mode/mood and assembles personality overlay prompt.

Sits before llm_node in the graph to ensure personality context is available
before memory injection and LLM inference.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import RunnableConfig

from .state import AgentState

logger = logging.getLogger(__name__)

# Mood priority order (higher index = higher priority)
MOOD_ORDER = ["neutral", "thinking", "surprised", "sad", "angry", "happy"]


async def personality_node(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """Determine personality mode and mood, building overlay prompt.

    Reads from state:
        - session_id, channel_id (to determine streaming mode)
        - metadata (for mood hints from emotion_node)

    Sets:
        - personality_mode: 'default' | 'streaming'
        - personality_mood: current mood or None
        - system_prompt: personality-overlaid prompt

    For streaming personality: activates when channel is Bilibili danmaku.
    For mood: updated from emotion detection if available.
    """
    session_id = state.get("session_id", "unknown")
    channel_id = state.get("channel_id", "")
    metadata = state.get("metadata", {})
    current_mood = state.get("personality_mood")

    # Determine mode
    personality_mode = "streaming" if "bilibili" in (channel_id or "").lower() else "default"

    # Determine mood
    emotion = state.get("emotion") or metadata.get("emotion")
    if emotion and emotion in MOOD_ORDER:
        personality_mood = emotion
    else:
        personality_mood = current_mood  # keep existing

    # Build personality overlay instruction
    overlay_parts = []

    if personality_mode == "streaming":
        overlay_parts.append(
            "当前为直播模式。回复要简短有趣，适合弹幕互动。"
        )

    if personality_mood:
        mood_descriptions = {
            "happy": "保持积极愉快的语气",
            "sad": "语气温和一些",
            "angry": "保持冷静理性的态度",
            "surprised": "可以适当表达惊讶",
            "thinking": "用思考和分析的语气",
            "neutral": "保持自然平稳的语气",
        }
        desc = mood_descriptions.get(personality_mood, "")
        if desc:
            overlay_parts.append(f"当前情绪：{desc}")

    personality_overlay = " ".join(overlay_parts) if overlay_parts else ""

    logger.info(
        f"[{session_id}] [PersonalityNode] mode={personality_mode}, "
        f"mood={personality_mood}, overlay={bool(personality_overlay)}"
    )

    return {
        "personality_mode": personality_mode,
        "personality_mood": personality_mood,
        "metadata": {
            **metadata,
            "personality_overlay": personality_overlay,
            "personality_mode": personality_mode,
            "personality_mood": personality_mood,
        },
    }
