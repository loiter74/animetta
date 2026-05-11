"""
Fact extraction adapter for PeriodicLearner.

Wraps FactExtractor to run as a scheduled batch task: reads recent
conversation summaries, extracts facts from raw turns, and persists
high-confidence facts as Wiki synthesis pages.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..fact_extractor import FactExtractor
from ..models.turns import MemoryTurn

logger = logging.getLogger(__name__)

# Minimum confidence threshold for writing facts to Wiki
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


async def extract_facts_batch(
    fact_extractor: FactExtractor,
    turns: List[MemoryTurn],
    session_id: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Extract facts from a batch of conversation turns.

    Uses the existing FactExtractor's LLM pipeline on each turn,
    then filters by confidence.

    Returns:
        List of extracted fact dicts with {fact, category, confidence, is_static, source}
    """
    extracted: List[Dict[str, Any]] = []

    for turn in turns:
        if not turn.user_input or not turn.agent_response:
            continue
        try:
            entries = await fact_extractor.extract_and_store(turn, space_id=session_id)
            for entry in entries:
                if entry.confidence >= confidence_threshold:
                    extracted.append({
                        "id": entry.id,
                        "fact": entry.memory,
                        "category": getattr(entry, "category", "other"),
                        "confidence": entry.confidence,
                        "is_static": entry.is_static,
                        "source": "auto-extraction",
                        "source_timestamp": turn.timestamp.isoformat() if turn.timestamp else None,
                        "source_turn_id": turn.turn_id,
                    })
        except Exception as e:
            logger.warning(
                f"[FactExtractionAdapter] extraction failed for turn {turn.turn_id}: {e}"
            )
            continue

    return extracted


def format_facts_for_wiki(
    facts: List[Dict[str, Any]],
    session_id: str,
) -> str:
    """Format extracted facts as a Wiki Markdown page.

    Returns Markdown content suitable for writing as a synthesis page.
    """
    if not facts:
        return ""

    now = datetime.now()
    lines = [
        f"# 自动提取事实 — {now.strftime('%Y-%m-%d')}",
        "",
        f"**来源会话**: {session_id}",
        f"**提取时间**: {now.isoformat()}",
        f"**提取数量**: {len(facts)}",
        "",
        "---",
        "",
    ]

    # Group by category
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for f in facts:
        cat = f.get("category", "other")
        by_category.setdefault(cat, []).append(f)

    category_names = {
        "preference": "🎯 偏好",
        "identity": "👤 身份",
        "experience": "📖 经历",
        "opinion": "💭 观点",
        "behavior": "🔁 行为习惯",
        "goal": "🎯 目标 / 计划",
        "other": "📋 其他",
    }

    for cat, cat_facts in sorted(by_category.items()):
        lines.append(f"## {category_names.get(cat, cat)}")
        lines.append("")
        for f in cat_facts:
            confidence_bar = "█" * min(int(f["confidence"] * 10), 10) + "░" * max(10 - int(f["confidence"] * 10), 0)
            lines.append(
                f"- {f['fact']} "
                f"`置信度: {confidence_bar} {f['confidence']:.0%}`"
            )
        lines.append("")

    lines.append("---")
    lines.append("*由 PeriodicLearner 自动提取*")
    return "\n".join(lines)
