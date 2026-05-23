"""
Pattern extractor: uses LLM to identify behavioral patterns, preferences,
and recurring themes from conversation data.

Workflow:
1. Analyze conversation turns via LLM (preferred) or frequency-based heuristics
2. Extract patterns: recurring topics, preferences, communication/emotional/behavioral patterns
3. Return as LearningLog objects with summary_type='pattern'
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.turns import MemoryTurn
from ..learner.summarizer import LearningLog

logger = logging.getLogger(__name__)

PATTERN_CATEGORIES = ["preference", "behavior", "interest", "emotion", "communication"]

EXTRACTION_SYSTEM_PROMPT = """你是一个对话模式分析助手。你的任务是从一组对话轮次中识别用户的重复行为模式、偏好和主题。

请仔细分析以下对话，找出：

1. **兴趣话题**：用户反复提及或表现出浓厚兴趣的领域（如编程、音乐、游戏等）
2. **偏好与反感**：用户明确或暗示喜欢/不喜欢的事物
3. **沟通风格**：用户说话的惯用方式（如简洁直接、喜欢开玩笑、经常提问等）
4. **情绪模式**：用户在特定话题上的情绪反应模式
5. **行为习惯**：用户的日常行为规律或做事方式

返回格式为 JSON 数组：
[
  {{
    "pattern": "模式描述（清晰、具体的陈述句）",
    "category": "preference | behavior | interest | emotion | communication",
    "confidence": 0.0-1.0,
    "evidence": ["turn_id_1", "turn_id_2"]
  }}
]

要求：
- 每条模式必须用证据（对话轮次ID）支持
- confidence 基于证据充分程度：0.5(较少证据) / 0.7(多个证据) / 0.9(大量一致证据)
- pattern 描述要具体，如"用户对 Rust 编程语言表现出持续兴趣"而非"用户喜欢编程"
- 最多返回 {max_patterns} 条模式
- 如果没有任何明显模式，返回空数组
"""

EXTRACTION_USER_PROMPT = """请分析以下 {turn_count} 轮对话，找出用户的重复模式和偏好：

{conversation_text}

分析结果（JSON 数组）："""

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "preference": ["喜欢", "不喜欢", "讨厌", "最爱", "更好", "推荐", "偏好"],
    "behavior": ["每天", "总是", "经常", "通常", "习惯", "平时", "日常"],
    "interest": ["感兴趣", "想学", "想了解", "好奇", "有趣", "有意思"],
    "emotion": ["开心", "难过", "焦虑", "压力", "累", "疲惫", "烦", "生气", "感动"],
    "communication": ["?", "？", "哈哈", "嘿嘿", "开玩笑"],
}

EMOTION_KEYWORD_GROUPS: Dict[str, List[str]] = {
    "开心": ["开心", "快乐", "高兴", "棒", "太好的"],
    "焦虑": ["焦虑", "担心", "紧张", "不安"],
    "疲惫": ["累", "疲惫", "疲劳", "困"],
    "失落": ["失落", "难过", "伤心", "失望"],
    "好奇": ["好奇", "想知道", "为什么", "怎么回事"],
}


class PatternExtractor:
    """Uses LLM to identify behavioral patterns, preferences, and recurring themes from conversation data.

    Supports LLM-driven extraction (preferred) and frequency-based fallback extraction.

    Args:
        llm_client: Optional LLM client with async chat(messages, response_format) method
        config: Optional configuration dict
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._llm = llm_client
        self._config = config or {}

    async def extract_patterns(
        self,
        turns: List[MemoryTurn],
        session_id: str,
        max_patterns: int = 5,
    ) -> List[LearningLog]:
        """Extract patterns from conversation turns.

        Args:
            turns: List of conversation turns to analyze
            session_id: Session identifier
            max_patterns: Maximum number of patterns to extract

        Returns:
            List of LearningLog objects with summary_type='pattern'
        """
        if not turns:
            return []

        if self._llm:
            try:
                return await self._extract_with_llm(turns, session_id, max_patterns)
            except Exception as e:
                logger.warning(
                    f"[PatternExtractor] LLM extraction failed, "
                    f"falling back to frequency analysis: {e}"
                )

        return self._extract_with_frequency(turns, session_id, max_patterns)

    # ── LLM-based extraction ──────────────────────────────────

    async def _extract_with_llm(
        self,
        turns: List[MemoryTurn],
        session_id: str,
        max_patterns: int = 5,
    ) -> List[LearningLog]:
        """Use LLM to identify patterns from conversation turns."""
        conversation_text = self._format_conversation(turns)

        system_prompt = EXTRACTION_SYSTEM_PROMPT.format(max_patterns=max_patterns)
        user_prompt = EXTRACTION_USER_PROMPT.format(
            turn_count=len(turns),
            conversation_text=conversation_text,
        )

        result = await self._llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = result.get("content", "") if isinstance(result, dict) else str(result)
        content = self._clean_json(content)

        try:
            data = json.loads(content)
            patterns_list = data if isinstance(data, list) else data.get("patterns", [])
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[PatternExtractor] LLM response parse failed: {e}")
            return []

        now = datetime.now()
        logs: List[LearningLog] = []
        for item in patterns_list[:max_patterns]:
            if not isinstance(item, dict) or "pattern" not in item:
                continue
            pattern_text = item["pattern"].strip()
            if not pattern_text:
                continue
            category = item.get("category", "behavior")
            if category not in PATTERN_CATEGORIES:
                category = "behavior"
            confidence = min(max(float(item.get("confidence", 0.5)), 0.0), 1.0)
            evidence = item.get("evidence", [])

            logs.append(LearningLog(
                id=str(uuid.uuid4()),
                session_id=session_id,
                summary_type="pattern",
                content=pattern_text,
                confidence=confidence,
                created_at=now,
                metadata={
                    "category": category,
                    "evidence": evidence,
                    "source": "llm",
                },
            ))

        return logs

    @staticmethod
    def _format_conversation(turns: List[MemoryTurn]) -> str:
        """Format conversation turns into readable text for LLM prompt."""
        lines: List[str] = []
        for turn in turns:
            lines.append(f"[轮次 {turn.turn_id}]")
            lines.append(f"用户: {turn.user_input}")
            lines.append(f"AI: {turn.agent_response}")
            if turn.emotions:
                lines.append(f"情绪: {', '.join(turn.emotions)}")
            lines.append("")
        return "\n".join(lines)

    # ── Frequency-based fallback ─────────────────────────────

    def _extract_with_frequency(
        self,
        turns: List[MemoryTurn],
        session_id: str,
        max_patterns: int = 5,
    ) -> List[LearningLog]:
        """Simple frequency-based pattern detection (fallback when no LLM)."""
        user_turns = [t for t in turns if t.user_input]
        if not user_turns:
            return []

        patterns: List[LearningLog] = []

        # 1. Frequent topic detection via bigram frequency
        topic_patterns = self._detect_frequent_topics(user_turns, session_id)
        patterns.extend(topic_patterns)

        if len(patterns) >= max_patterns:
            return patterns[:max_patterns]

        # 2. Preference detection via keyword matching
        pref_patterns = self._detect_preferences(user_turns, session_id)
        patterns.extend(pref_patterns)

        if len(patterns) >= max_patterns:
            return patterns[:max_patterns]

        # 3. Emotional pattern detection
        emotion_patterns = self._detect_emotion_patterns(turns, session_id)
        patterns.extend(emotion_patterns)

        return patterns[:max_patterns]

    def _detect_frequent_topics(
        self,
        turns: List[MemoryTurn],
        session_id: str,
    ) -> List[LearningLog]:
        """Detect frequently mentioned topics via bigram frequency analysis."""
        user_texts = [t.user_input for t in turns]
        bigrams = self._extract_bigrams(user_texts)
        bigram_freq = Counter(bigrams)

        patterns: List[LearningLog] = []
        for bigram, count in bigram_freq.most_common(5):
            if count < 2:
                break
            evidence = [
                t.turn_id for t in turns
                if bigram.lower() in t.user_input.lower()
            ]
            if evidence:
                patterns.append(self._build_log(
                    session_id=session_id,
                    content=f"用户频繁提及「{bigram}」，表明对此话题有持续关注",
                    category="interest",
                    confidence=min(0.5 + count * 0.1, 0.9),
                    evidence=evidence,
                    source="frequency",
                ))
        return patterns

    def _detect_preferences(
        self,
        turns: List[MemoryTurn],
        session_id: str,
    ) -> List[LearningLog]:
        """Detect user preferences using keyword matching."""
        seen_categories: set = set()
        patterns: List[LearningLog] = []

        for keyword, category in [
            ("喜欢", "preference"), ("prefer", "preference"),
            ("不喜欢", "preference"), ("讨厌", "preference"),
            ("感兴趣", "interest"), ("有趣", "interest"),
        ]:
            matching = [t for t in turns if keyword in t.user_input]
            if len(matching) >= 2 and category not in seen_categories:
                seen_categories.add(category)
                is_positive = keyword in ("喜欢", "prefer", "感兴趣", "有趣")
                label = "偏好" if is_positive else "反感"
                patterns.append(self._build_log(
                    session_id=session_id,
                    content=f"用户在对话中多次表达{label}（关键词：{keyword}）",
                    category=category,
                    confidence=min(0.5 + len(matching) * 0.1, 0.9),
                    evidence=[t.turn_id for t in matching],
                    source="frequency",
                ))

        # Communication style detection
        question_turns = [t for t in turns if "?" in t.user_input or "？" in t.user_input]
        if len(question_turns) >= max(len(turns) * 0.3, 2):
            patterns.append(self._build_log(
                session_id=session_id,
                content="用户在对话中频繁提问，表现出探究型沟通风格",
                category="communication",
                confidence=min(0.5 + len(question_turns) * 0.05, 0.8),
                evidence=[t.turn_id for t in question_turns],
                source="frequency",
            ))

        return patterns

    def _detect_emotion_patterns(
        self,
        turns: List[MemoryTurn],
        session_id: str,
    ) -> List[LearningLog]:
        """Detect emotional patterns from turn emotions and keyword matching."""
        patterns: List[LearningLog] = []

        # From turn emotion labels
        emotion_counts: Counter = Counter()
        turn_emotion_map: Dict[str, List[str]] = {}
        for t in turns:
            for e in t.emotions:
                emotion_counts[e] += 1
                turn_emotion_map.setdefault(e, []).append(t.turn_id)

        for emotion, count in emotion_counts.most_common():
            if count >= 2:
                patterns.append(self._build_log(
                    session_id=session_id,
                    content=f"用户在对话中反复出现「{emotion}」情绪",
                    category="emotion",
                    confidence=min(0.5 + count * 0.15, 0.9),
                    evidence=turn_emotion_map[emotion],
                    source="frequency",
                ))

        # From keyword matching
        for emotion_label, keywords in EMOTION_KEYWORD_GROUPS.items():
            matching = [
                t for t in turns
                if any(k in t.user_input for k in keywords)
            ]
            if len(matching) >= 2:
                # Check if similar pattern already exists
                already_exists = any(
                    emotion_label in p.content for p in patterns
                )
                if not already_exists:
                    patterns.append(self._build_log(
                        session_id=session_id,
                        content=f"用户在对话中表现出「{emotion_label}」情绪倾向",
                        category="emotion",
                        confidence=min(0.5 + len(matching) * 0.1, 0.8),
                        evidence=[t.turn_id for t in matching],
                        source="frequency",
                    ))

        return patterns

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenization for mixed Chinese/English text."""
        return re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", text)

    @classmethod
    def _extract_bigrams(cls, texts: List[str]) -> List[str]:
        """Extract adjacent token pairs as potential topic indicators."""
        bigrams: List[str] = []
        for text in texts:
            tokens = cls._tokenize(text)
            for i in range(len(tokens) - 1):
                bigram = f"{tokens[i]} {tokens[i+1]}"
                if len(bigram) >= 3:
                    bigrams.append(bigram)
        return bigrams

    def _build_log(
        self,
        session_id: str,
        content: str,
        category: str,
        confidence: float,
        evidence: List[str],
        source: str = "frequency",
    ) -> LearningLog:
        """Build a LearningLog object for an extracted pattern."""
        return LearningLog(
            id=str(uuid.uuid4()),
            session_id=session_id,
            summary_type="pattern",
            content=content,
            confidence=min(max(confidence, 0.0), 1.0),
            created_at=datetime.now(),
            metadata={
                "category": category,
                "evidence": evidence,
                "source": source,
            },
        )

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
