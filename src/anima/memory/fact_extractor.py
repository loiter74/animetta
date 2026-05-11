"""
Fact extractor: extracts atomic facts from conversations and manages MemoryEntry versions.

Workflow:
1. Extract structured facts from conversation turns (MemoryTurn)
2. Version-match against existing MemoryEntry (create vs update)
3. Persist via MemoryEntryStore
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .models.memory_entry import MemoryEntry
from .models.turns import MemoryTurn
from .storage.memory_entry_store import MemoryEntryStore

logger = logging.getLogger(__name__)

# ── LLM Prompt templates (Task 2.1) ─────────────────────────

FACT_EXTRACTION_SYSTEM_PROMPT = """你是一个对话事实提取助手。从用户和 AI 的对话中提取原子事实。

每条事实应该是:
- 单个、明确的信息点 (subject + predicate + object)
- 以陈述句形式表达 (如 "用户喜欢 TypeScript")
- 不包含对话中的临时性、模糊性内容

返回格式: JSON 数组
[
  {
    "fact": "事实文本",
    "category": "preference | identity | experience | opinion | behavior | goal | other",
    "confidence": 0.0-1.0,
    "is_static": true/false
  }
]

规则:
- preference: 用户表达的好恶、偏好
- identity: 用户的身份、属性信息
- experience: 用户的经历、经验
- opinion: 用户的观点、看法
- behavior: 用户的行为习惯
- goal: 用户的目标、计划
- confidence: 0.3(推测) / 0.7(较明确) / 1.0(直接陈述)
- is_static: true 如果该事实预计长期有效
"""

FACT_EXTRACTION_USER_PROMPT = """从以下对话中提取关于用户的事实:

用户: {user_input}
AI: {agent_response}

提取的事实:"""

# ── LLM Prompt templates (Task 3.1: Memory relation judgment) ──

RELATION_ANALYSIS_SYSTEM_PROMPT = """你是一个记忆关系分析助手。判断两个事实之间的关系。

关系类型:
- "updates": 新事实取代/覆盖了旧事实 (如 "用户喜欢 TypeScript" → "用户现在更喜欢 Python")
- "extends": 新事实扩展/补充了旧事实 (如 "用户喜欢编程" → "用户正在学习 Rust")
- "derives": 新事实衍生自旧事实 (旧事实是新事实的上下文/来源)
- "none": 两个事实没有直接关系

返回 JSON: {"relation": "updates | extends | derives | none", "reason": "简短理由"}
"""

RELATION_ANALYSIS_USER_PROMPT = """判断新事实与旧事实之间的关系:

旧事实: {old_fact}
新事实: {new_fact}

关系:"""


# ── Rule-based extraction (fallback) ────────────────────────

RULES: List[Tuple[str, str, str, float, bool]] = [
    # pattern, category, confidence, is_static
    (r"我[叫是](\S{1,10}?)[，。！？\s,]", "identity", 0.9, True),
    (r"我的名字[是为](\S{1,10}?)[，。！？\s,]", "identity", 0.9, True),
    (r"我(?:今年)?(\d{1,3})岁", "identity", 0.9, True),
    (r"我住在(\S{2,15}?)[，。！？\s]", "identity", 0.8, True),
    (r"我(?:是|从事|做)(.{2,20}?)(?:的|工作|职业|[，。！？])", "identity", 0.7, True),
    (r"我(?:喜欢|爱|热爱)(.{2,30}?)(?:[，。！？]|$)", "preference", 0.9, True),
    (r"我(?:不喜欢|讨厌|反感)(.{2,30}?)(?:[，。！？]|$)", "preference", 0.9, True),
    (r"我对(.{2,20}?)很感兴趣", "preference", 0.8, True),
    (r"我(?:想|希望|想要|打算)(.{2,30}?)(?:[，。！？]|$)", "goal", 0.7, False),
    (r"我(?:去过|去过|曾经去)(.{2,20}?)[，。！？]", "experience", 0.8, True),
    (r"我有(.{2,30}?)(?:的经历|的经验|的经验)", "experience", 0.7, True),
    (r"(?:在|正在)(.{2,30}?)[，。！？]", "behavior", 0.6, False),
    (r"我(?:觉得|认为|以为)(.{2,30}?)[，。！？]", "opinion", 0.6, False),
    (r"我(?:的爱好|的兴趣|喜欢做)(.{2,30}?)[，。！？]", "preference", 0.8, True),
]


@dataclass
class ExtractedFact:
    """A single fact extracted from conversation."""
    fact: str
    category: str
    confidence: float
    is_static: bool


class FactExtractorConfig:
    """FactExtractor configuration."""

    def __init__(
        self,
        enable_relation_analysis: bool = True,
        relation_analysis_rate: float = 0.5,
    ):
        """
        Fact extractor configuration

        Args:
            enable_relation_analysis: Whether to enable LLM relation analysis
            relation_analysis_rate: Sampling rate [0.0, 1.0], controls what proportion of new facts undergo relation analysis
        """
        self.enable_relation_analysis = enable_relation_analysis
        self.relation_analysis_rate = min(max(relation_analysis_rate, 0.0), 1.0)


class FactExtractor:
    """
    Extracts structured facts from conversations and manages MemoryEntry versions.

    Supports LLM-driven extraction (preferred) and rule-based fallback extraction.
    """

    def __init__(
        self,
        entry_store: MemoryEntryStore,
        llm_client: Optional[Any] = None,
        config: Optional[FactExtractorConfig] = None,
    ):
        self._store = entry_store
        self._llm_client = llm_client
        self._config = config or FactExtractorConfig()

    # ── Main entry ────────────────────────────────────────────

    async def extract_and_store(
        self,
        turn: MemoryTurn,
        space_id: str = "default",
    ) -> List[MemoryEntry]:
        """Extract facts from MemoryTurn and store them in MemoryEntryStore.

        Returns:
            List of created (or updated) MemoryEntry objects
        """
        # 1. Extract facts
        facts = await self._extract_facts(turn)

        if not facts:
            logger.debug(f"[FactExtractor] no facts extracted from turn {turn.turn_id}")
            return []

        # Compute emotion intensity from turn for memory weighting
        from .search.scorer import MemoryScorer
        emotion_value = MemoryScorer.emotion_intensity(turn) if turn.emotions else None

        # 2. Store and perform version matching
        stored: List[MemoryEntry] = []
        for fact in facts:
            entry = await self._store_fact(fact, space_id, emotion_value)
            if entry:
                stored.append(entry)

        if stored:
            logger.info(
                f"[FactExtractor] extracted {len(facts)} facts "
                f"→ {len(stored)} stored (turn {turn.turn_id})"
            )
        return stored

    # ── Fact extraction (Task 2.1, 2.2) ──────────────────────

    async def _extract_facts(self, turn: MemoryTurn) -> List[ExtractedFact]:
        """Extract facts: prefer LLM, fallback to rules."""
        if self._llm_client:
            try:
                return await self._extract_with_llm(turn)
            except Exception as e:
                logger.warning(f"[FactExtractor] LLM extraction failed, fallback to rules: {e}")

        return self._extract_with_rules(turn)

    async def _extract_with_llm(self, turn: MemoryTurn) -> List[ExtractedFact]:
        """LLM-driven fact extraction."""
        user_prompt = FACT_EXTRACTION_USER_PROMPT.format(
            user_input=turn.user_input,
            agent_response=turn.agent_response,
        )

        result = await self._llm_client.chat(
            messages=[
                {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = result.get("content", "") if isinstance(result, dict) else str(result)
        content = self._clean_json(content)

        try:
            data = json.loads(content)
            facts_list = data if isinstance(data, list) else data.get("facts", data.get("extracted_facts", []))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[FactExtractor] LLM response parse failed: {e}")
            return []

        extracted: List[ExtractedFact] = []
        for item in facts_list:
            if isinstance(item, dict) and "fact" in item:
                extracted.append(ExtractedFact(
                    fact=item["fact"],
                    category=item.get("category", "other"),
                    confidence=min(max(float(item.get("confidence", 0.5)), 0.0), 1.0),
                    is_static=bool(item.get("is_static", False)),
                ))
        return extracted

    def _extract_with_rules(self, turn: MemoryTurn) -> List[ExtractedFact]:
        """Rule-based fact extraction (fallback)."""
        combined = f"{turn.user_input}\n{turn.agent_response}"
        extracted: List[ExtractedFact] = []
        seen: set = set()

        for pattern, category, confidence, is_static in RULES:
            m = re.search(pattern, combined)
            if m:
                value = m.group(1).strip()
                if value and value not in seen:
                    seen.add(value)
                    extracted.append(ExtractedFact(
                        fact=value,
                        category=category,
                        confidence=confidence,
                        is_static=is_static,
                    ))
        return extracted

    # ── Version matching (Task 2.3) ──────────────────────────

    async def _store_fact(self, fact: ExtractedFact, space_id: str, emotion_value: Optional[float] = None) -> Optional[MemoryEntry]:
        # Normalize: strip whitespace, lowercase
        normalized = fact.fact.strip()

        # Check if a similar fact already exists
        existing = self._store.get_latest_by_memory(normalized, space_id)

        if existing:
            # Content unchanged => skip
            if existing.memory == normalized:
                logger.debug(f"[FactExtractor] fact unchanged, skipping: {normalized[:40]}")
                return existing

            # Fact changed → create new version
            new_entry = MemoryEntry(
                id="",
                memory=normalized,
                space_id=space_id,
                version=existing.version + 1,
                is_latest=True,
                is_static=fact.is_static,
                is_forgotten=False,
                confidence=self._compute_confidence(fact, existing),
                emotion_value=emotion_value if emotion_value is not None else existing.emotion_value,
            )
            new_id = self._store.create_new_version(new_entry, existing.id)
            new_entry.id = new_id

            # Relation analysis (Task 3.2, 3.3)
            relation = await self._analyze_relation(normalized, existing)
            if relation:
                from .models.memory_entry import MemoryRelation, RelationType
                self._store.add_relation(MemoryRelation(
                    source_id=new_id,
                    target_id=existing.id,
                    relation=RelationType(relation),
                ))
                logger.debug(f"[FactExtractor] relation: {existing.id} → {relation} → {new_id}")

            logger.info(f"[FactExtractor] updated version {existing.version}→{existing.version + 1}: {normalized[:50]}")
            return new_entry
        else:
            # Brand new fact
            entry = MemoryEntry(
                id="",
                memory=normalized,
                space_id=space_id,
                version=1,
                is_latest=True,
                is_static=fact.is_static,
                confidence=fact.confidence,
                emotion_value=emotion_value,
            )
            entry_id = self._store.create(entry)
            entry.id = entry_id
            logger.debug(f"[FactExtractor] new fact: {normalized[:50]}")
            return entry

    # ── Confidence (Task 2.5) ─────────────────────────────────

    def _compute_confidence(self, new_fact: ExtractedFact, existing: MemoryEntry) -> float:
        """Compute combined confidence.

        Strategy: weighted average of old and new confidence; higher version favors newer value.
        """
        old_conf = existing.confidence
        new_conf = new_fact.confidence
        version = existing.version

        # As version increases, new confidence weight gradually grows
        new_weight = min(0.5 + version * 0.1, 0.9)
        old_weight = 1.0 - new_weight
        return round(new_conf * new_weight + old_conf * old_weight, 2)

    # ── Relation analysis (Task 3.1, 3.2) ──────────────────

    async def _analyze_relation(
        self,
        new_fact: str,
        existing_entry: MemoryEntry,
    ) -> Optional[str]:
        """Determine the relationship between a new fact and an existing entry.

        Returns:
            "updates" | "extends" | "derives" | None (cannot determine)
        """
        if not self._config.enable_relation_analysis:
            return None

        # Sampling: control the proportion of relation analysis
        import hashlib
        sample_key = f"{new_fact}:{existing_entry.id}"
        sample_hash = int(hashlib.sha256(sample_key.encode()).hexdigest(), 16)
        if (sample_hash % 100) / 100 > self._config.relation_analysis_rate:
            return None

        if not self._llm_client:
            return None

        user_prompt = RELATION_ANALYSIS_USER_PROMPT.format(
            old_fact=existing_entry.memory,
            new_fact=new_fact,
        )

        try:
            result = await self._llm_client.chat(
                messages=[
                    {"role": "system", "content": RELATION_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = result.get("content", "") if isinstance(result, dict) else str(result)
            content = self._clean_json(content)
            data = json.loads(content)
            relation = data.get("relation", "none")
            if relation in ("updates", "extends", "derives"):
                return relation
        except Exception as e:
            logger.debug(f"[FactExtractor] relation analysis failed: {e}")

        return None

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _clean_json(text: str) -> str:
        """Clean JSON string returned by LLM."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
