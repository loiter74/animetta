"""INGEST workflow - process conversations into wiki pages.

VTuber-specific extraction rules:
- Entities: user names, pets, characters, projects
- Concepts: preferences, interests, emotions, routines
- Persona: AI character traits, catchphrases
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..models.turns import MemoryTurn
from ..search.scorer import MemoryScorer
from ..fact_extractor import FactExtractor
from .manager import WikiManager
from .models import PageType, WikiPage

logger = logging.getLogger(__name__)

# ── extraction patterns ─────────────────────────────────────

ENTITY_PATTERNS: Dict[str, List[str]] = {
    "name": [
        r"我[叫是](\S{1,10}?)[，。！？\s,]",
        r"我的名字[是为](\S{1,10}?)[，。！？\s,]",
        r"叫我(\S{1,10}?)[吧就好]",
    ],
    "age": [
        r"我今年(\d+)岁",
        r"我(\d{1,3})岁",
    ],
    "pet": [
        r'(?:养了|有)一只(?:猫|狗|兔子|仓鼠|鸟|鱼|宠物)?(?:叫|名为|名字叫)?(\S{1,8}?)(?:了|[，。！？\s"]|$)',
        r"(?:猫|狗|宠物)(?:叫|名|名为)(\S{1,8}?)(?:了|[，。！？\s]|$)",
    ],
    "location": [
        r"我住在(\S{2,10}?)[，。！？\s]",
        r"我在(\S{2,10}?)[上班工作生活]",
    ],
}

PREFERENCE_PATTERNS: Dict[str, List[str]] = {
    "like": [
        r"我(比较|特别|非常|最)?(?:喜欢|爱|热爱)(.{2,20}?)(?:了|[，。！？]|$)",
        r"(.{2,10}?)是我的最爱",
        r"我对(.{2,15}?)很感兴趣",
    ],
    "dislike": [
        r"我(比较|特别|非常|最)?(?:讨厌|不喜欢|反感|恨)(.{2,20}?)(?:了|[，。！？]|$)",
    ],
    "want": [
        r"我(?:想|希望|想要|打算)(.{2,20}?)(?:了|[，。！？]|$)",
    ],
}

# important / remember-me patterns  (force high score)
IMPORTANT_PATTERNS = [
    r"记住(.+)",
    r"别忘了(.+)",
    r"重要[的是](.+)",
    r"(?:记录|记一下|写下来)(.+)",
]


class WikiIngestor:
    """
    INGEST workflow.

    For every conversation turn:
    1. Write raw log (immutable).
    2. Score importance.
    3. Extract entities & concepts via rules.
    4. Create / update wiki entity / concept pages.
    5. Update source summary for the day.
    6. Rebuild wiki index.
    7. Append to operation log.
    """

    def __init__(self, wiki: WikiManager, llm_client=None, fact_extractor: Optional[FactExtractor] = None):
        self._wiki = wiki
        self._scorer = MemoryScorer()
        self._llm_client = llm_client
        self._fact_extractor = fact_extractor

    # ── public API ──────────────────────────────────────────

    async def ingest_turn(self, turn: MemoryTurn) -> None:
        """Process one conversation turn into the wiki."""
        # 1. raw
        self._write_raw(turn)

        # 2. score
        score = self._scorer.score(turn)
        # boost score if matches IMPORTANT_PATTERNS
        for pat in IMPORTANT_PATTERNS:
            if re.search(pat, turn.user_input):
                score = max(score, 0.6)
                break

        if score < 0.3:
            logger.debug(f"[Ingestor] skip low-score turn ({score:.2f})")
            return

        # 3. extract
        entities = self._extract_entities(turn)
        concepts = self._extract_concepts(turn)

        # 4. update pages
        for etype, ename in entities:
            self._update_entity_page(etype, ename, turn)

        for ctype, cname in concepts:
            self._update_concept_page(ctype, cname, turn)

        # 5. MemoryEntry 事实提取 (若配置了 fact_extractor)
        if self._fact_extractor:
            try:
                await self._fact_extractor.extract_and_store(turn)
            except Exception as e:
                logger.warning(f"[Ingestor] MemoryEntry fact extraction failed: {e}")

        # 6. source summary
        self._update_source_summary(turn)

        # 7. index
        self._wiki.rebuild_index()

        # 7. log
        parts = []
        if entities:
            parts.append(f"entities: {', '.join(e[1] for e in entities)}")
        if concepts:
            parts.append(f"concepts: {', '.join(c[1] for c in concepts)}")
        self._wiki.append_log("ingest", turn.turn_id, "; ".join(parts) or "basic")

        logger.debug(
            f"[Ingestor] turn ingested: score={score:.2f}, "
            f"entities={len(entities)}, concepts={len(concepts)}"
        )

    async def ingest_batch(self, turns: List[MemoryTurn]) -> None:
        for t in turns:
            await self.ingest_turn(t)

    # ── raw ─────────────────────────────────────────────────

    def _write_raw(self, turn: MemoryTurn) -> None:
        lines = [f"**User**: {turn.user_input}", f"**AI**: {turn.agent_response}"]
        if turn.emotions:
            names = []
            for e in turn.emotions:
                names.append(e.get("emotion", str(e)) if isinstance(e, dict) else str(e))
            lines.append(f"*Emotions: {', '.join(names)}*")
        self._wiki.write_raw(turn.timestamp, "\n".join(lines))

    # ── extraction helpers ──────────────────────────────────

    def _extract_entities(self, turn: MemoryTurn) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []
        seen: Set[str] = set()
        for etype, patterns in ENTITY_PATTERNS.items():
            for pat in patterns:
                m = re.search(pat, turn.user_input)
                if m:
                    val = m.group(1).strip()
                    key = f"{etype}:{val}"
                    if key not in seen:
                        seen.add(key)
                        results.append((etype, val))
                    break
        return results

    def _extract_concepts(self, turn: MemoryTurn) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []
        seen: Set[str] = set()
        for ctype, patterns in PREFERENCE_PATTERNS.items():
            for pat in patterns:
                m = re.search(pat, turn.user_input)
                if m:
                    # last non-None group is the content
                    val = [g for g in m.groups() if g][-1].strip()
                    key = f"{ctype}:{val}"
                    if key not in seen:
                        seen.add(key)
                        results.append((ctype, val))
                    break
        return results

    # ── page builders ───────────────────────────────────────

    @staticmethod
    def _safe_name(name: str) -> str:
        return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "-")[:60]

    def _update_entity_page(self, etype: str, ename: str, turn: MemoryTurn) -> None:
        safe = self._safe_name(ename)
        rel = f"entities/{safe}.md"
        date = turn.timestamp.strftime("%Y-%m-%d")
        time = turn.timestamp.strftime("%H:%M")

        existing = self._wiki.read_page(rel)
        if existing:
            existing.content += (
                f"\n### {date} {time}\n"
                f"- {turn.user_input[:120]}\n"
            )
            existing.updated_at = datetime.now()
            if date not in existing.tags:
                existing.tags.append(date)
            self._wiki.write_page(existing)
        else:
            content = (
                f"# {ename}\n\n"
                f"**类型**: {etype}\n\n"
                f"## 提及记录\n\n"
                f"### {date} {time}\n"
                f"- {turn.user_input[:120]}\n"
                f"- 来源: [[sources/{date}]]\n"
            )
            self._wiki.write_page(WikiPage(
                title=ename,
                page_type=PageType.ENTITY,
                path=rel,
                content=content,
                tags=[etype, date],
                links=[f"sources/{date}"],
                created_at=turn.timestamp,
                updated_at=datetime.now(),
            ))

    def _update_concept_page(self, ctype: str, cname: str, turn: MemoryTurn) -> None:
        safe = self._safe_name(cname)
        rel = f"concepts/{ctype}-{safe}.md"
        date = turn.timestamp.strftime("%Y-%m-%d")
        time = turn.timestamp.strftime("%H:%M")

        existing = self._wiki.read_page(rel)
        if existing:
            existing.content += (
                f"\n### {date} {time}\n"
                f"- {turn.user_input[:120]}\n"
            )
            existing.updated_at = datetime.now()
            self._wiki.write_page(existing)
        else:
            content = (
                f"# {cname}\n\n"
                f"**类型**: {ctype}\n\n"
                f"## 相关对话\n\n"
                f"### {date} {time}\n"
                f"- 用户表达了{ctype}: {cname}\n"
                f"- 原话: \"{turn.user_input[:120]}\"\n"
                f"- 来源: [[sources/{date}]]\n"
            )
            self._wiki.write_page(WikiPage(
                title=cname,
                page_type=PageType.CONCEPT,
                path=rel,
                content=content,
                tags=[ctype, date],
                links=[f"sources/{date}"],
                created_at=turn.timestamp,
                updated_at=datetime.now(),
            ))

    def _update_source_summary(self, turn: MemoryTurn) -> None:
        date = turn.timestamp.strftime("%Y-%m-%d")
        time = turn.timestamp.strftime("%H:%M")
        rel = f"sources/{date}.md"

        existing = self._wiki.read_page(rel)
        if existing:
            existing.content += (
                f"\n#### {time}\n"
                f"- User: {turn.user_input[:100]}\n"
                f"- AI: {turn.agent_response[:100]}\n"
            )
            existing.updated_at = datetime.now()
            self._wiki.write_page(existing)
        else:
            content = (
                f"# 对话摘要 {date}\n\n"
                f"**原始日志**: [raw/{date}.md](../../raw/{date}.md)\n\n"
                f"## 对话记录\n\n"
                f"#### {time}\n"
                f"- User: {turn.user_input[:100]}\n"
                f"- AI: {turn.agent_response[:100]}\n"
            )
            self._wiki.write_page(WikiPage(
                title=f"对话摘要 {date}",
                page_type=PageType.SOURCE,
                path=rel,
                content=content,
                tags=[date, "daily"],
                links=[],
                raw_source=f"raw/{date}.md",
                created_at=turn.timestamp,
                updated_at=datetime.now(),
            ))
