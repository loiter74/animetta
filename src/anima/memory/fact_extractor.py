"""
事实提取器: 从对话中提取原子事实并管理 MemoryEntry 版本.

工作流程:
1. 从对话轮次 (MemoryTurn) 提取结构化事实
2. 与已有 MemoryEntry 做版本匹配 (create vs update)
3. 通过 MemoryEntryStore 持久化
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

# ── LLM Prompt 模板 (Task 2.1) ──────────────────────────────

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

# ── LLM Prompt 模板 (Task 3.1: Memory 关系判断) ────────────

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


# ── 规则提取 (fallback) ────────────────────────────────────

RULES: List[Tuple[str, str, str, float, bool]] = [
    # pattern, category, is_static, confidence
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
    """从对话中提取的一条事实."""
    fact: str
    category: str
    confidence: float
    is_static: bool


class FactExtractorConfig:
    """FactExtractor 配置."""

    def __init__(
        self,
        enable_relation_analysis: bool = True,
        relation_analysis_rate: float = 0.5,
    ):
        """
        Args:
            enable_relation_analysis: 是否启用 LLM 关系分析
            relation_analysis_rate: 采样率 [0.0, 1.0], 控制多少比例的新事实做关系分析
        """
        self.enable_relation_analysis = enable_relation_analysis
        self.relation_analysis_rate = min(max(relation_analysis_rate, 0.0), 1.0)


class FactExtractor:
    """从对话中提取原子事实.

    支持 LLM 驱动的提取 (优先) 和基于规则的 fallback 提取.
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

    # ── 主入口 ───────────────────────────────────────────────

    async def extract_and_store(
        self,
        turn: MemoryTurn,
        space_id: str = "default",
    ) -> List[MemoryEntry]:
        """从 MemoryTurn 提取事实并存储到 MemoryEntryStore.

        Returns:
            创建的 (或更新后的) MemoryEntry 列表
        """
        # 1. 提取事实
        facts = await self._extract_facts(turn)

        if not facts:
            logger.debug(f"[FactExtractor] no facts extracted from turn {turn.turn_id}")
            return []

        # 2. 存储并做版本匹配
        stored: List[MemoryEntry] = []
        for fact in facts:
            entry = await self._store_fact(fact, space_id)
            if entry:
                stored.append(entry)

        if stored:
            logger.info(
                f"[FactExtractor] extracted {len(facts)} facts "
                f"→ {len(stored)} stored (turn {turn.turn_id})"
            )
        return stored

    # ── 事实提取 (Task 2.1, 2.2) ────────────────────────────

    async def _extract_facts(self, turn: MemoryTurn) -> List[ExtractedFact]:
        """提取事实: 优先 LLM, fallback 规则."""
        if self._llm_client:
            try:
                return await self._extract_with_llm(turn)
            except Exception as e:
                logger.warning(f"[FactExtractor] LLM extraction failed, fallback to rules: {e}")

        return self._extract_with_rules(turn)

    async def _extract_with_llm(self, turn: MemoryTurn) -> List[ExtractedFact]:
        """LLM 驱动的事实提取."""
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
        """基于规则的事实提取 (fallback)."""
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

    # ── 版本匹配 (Task 2.3) ─────────────────────────────────

    async def _store_fact(self, fact: ExtractedFact, space_id: str) -> Optional[MemoryEntry]:
        """存储事实, 自动做版本匹配."""
        # 标准化: 去空格、转小写
        normalized = fact.fact.strip()

        # 查找是否有相似事实已存在
        existing = self._store.get_latest_by_memory(normalized, space_id)

        if existing:
            # 事实已存在但内容相同 → 跳过
            if existing.memory == normalized:
                logger.debug(f"[FactExtractor] fact unchanged, skipping: {normalized[:40]}")
                return existing

            # 事实有变化 → 创建新版本
            new_entry = MemoryEntry(
                id="",
                memory=normalized,
                space_id=space_id,
                version=existing.version + 1,
                is_latest=True,
                is_static=fact.is_static,
                is_forgotten=False,
                confidence=self._compute_confidence(fact, existing),
            )
            new_id = self._store.create_new_version(new_entry, existing.id)
            new_entry.id = new_id

            # 关系分析 (Task 3.2, 3.3)
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
            # 全新事实
            entry = MemoryEntry(
                id="",
                memory=normalized,
                space_id=space_id,
                version=1,
                is_latest=True,
                is_static=fact.is_static,
                confidence=fact.confidence,
            )
            entry_id = self._store.create(entry)
            entry.id = entry_id
            logger.debug(f"[FactExtractor] new fact: {normalized[:50]}")
            return entry

    # ── 置信度 (Task 2.5) ───────────────────────────────────

    def _compute_confidence(self, new_fact: ExtractedFact, existing: MemoryEntry) -> float:
        """综合计算置信度.

        策略: 取新旧置信度的加权平均, 版本越高越偏向新值.
        """
        old_conf = existing.confidence
        new_conf = new_fact.confidence
        version = existing.version

        # 随着版本增加, 新置信度权重逐渐增大
        new_weight = min(0.5 + version * 0.1, 0.9)
        old_weight = 1.0 - new_weight
        return round(new_conf * new_weight + old_conf * old_weight, 2)

    # ── 关系分析 (Task 3.1, 3.2) ──────────────────────────

    async def _analyze_relation(
        self,
        new_fact: str,
        existing_entry: MemoryEntry,
    ) -> Optional[str]:
        """判断新事实与已有条目的关系.

        Returns:
            "updates" | "extends" | "derives" | None (无法判断)
        """
        if not self._config.enable_relation_analysis:
            return None

        # 采样: 控制关系分析的比例
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

    # ── 辅助 ─────────────────────────────────────────────────

    @staticmethod
    def _clean_json(text: str) -> str:
        """清理 LLM 返回的 JSON 字符串."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
