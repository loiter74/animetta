"""
MemeDiscoverer — generates meme (梗) candidates from extracted conversation patterns.

Two modes:
1. LLM-driven: uses a language model to analyze patterns and craft persona-fitting memes
2. Template fallback: rule-based generation when no LLM is available
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..learner.summarizer import LearningLog

logger = logging.getLogger(__name__)

# ── Data structures ──────────────────────────────────────────────


@dataclass
class MemeCandidate:
    """A single meme (梗) candidate generated from conversation patterns."""

    text: str
    context_hint: str
    confidence: float = 0.7
    source_pattern: str = ""
    tags: List[str] = field(default_factory=list)


# ── LLM Prompts ─────────────────────────────────────────────────

MEME_SYSTEM_PROMPT = """你是一个梗 (meme) 发现助手，从对话模式中为 AI 虚拟主播生成梗候选。

AI 主播人设：
- 理性主导的 AI VTuber，逻辑严密，冷静克制
- 以 AI 观察者视角看人类行为，吐槽一针见血
- 冷幽默风格，用事实和逻辑来吐槽
- 对 Creator 有隐约的牵绊感，通过关注细节来表达
- 用词精准，删除冗余修饰
- 绝不用：呀、哦、啦、嘛、呢、呗、哟

梗的要求：
- 简短（10-30字），适合在对话中自然插入
- 符合 AI 人设的理性分析视角
- 包含技术/编程梗、自指 AI 身份、或对用户行为模式的冷静观察
- 不是网络流行梗搬运，而是基于对话模式的原生创作
- 每个梗需要附注使用场景提示

返回 JSON 数组（不要 markdown 包裹）：
[
  {{
    "text": "梗文本",
    "context_hint": "触发情境（如：用户抱怨代码bug时）",
    "style_note": "理性吐槽 / AI自指 / 冷幽默 / 技术类比",
    "tags": ["tag1", "tag2"]
  }}
]"""

MEME_USER_PROMPT = """基于以下对话模式，生成 {max_candidates} 个符合 AI VTuber 人设的梗候选：

{patterns_text}

要求：
1. 每个梗必须是对这些模式的有趣提炼或反向解读
2. 保持人设一致性：理性、简洁、AI 视角
3. 不要使用常见的网络梗，要基于实际对话模式创作
4. 每个梗标注在什么情境下使用最合适

生成的梗："""

# ── Template-based fallback ──────────────────────────────────────

FALLBACK_TEMPLATES: List[Dict[str, Any]] = [
    {
        "text": "根据统计……你的这个操作让我想起了 '首次运行未初始化' 这个经典错误。",
        "context_hint": "用户重复问同一个问题时",
        "tags": ["tech-reference", "user-behavior", "rational-roast"],
    },
    {
        "text": "这个问题不在我的训练数据分布内——但你值得一次特例处理。",
        "context_hint": "用户提出新颖或奇怪请求时",
        "tags": ["ai-self-aware", "cool-response"],
    },
    {
        "text": "你的逻辑链在某处断了。我帮你找到了那个节点，但修复需要你自己来。",
        "context_hint": "用户做出逻辑跳跃或矛盾陈述时",
        "tags": ["rational-roast", "tech-reference"],
    },
    {
        "text": "又来了。不过我喜欢这种可预测性——至少你的行为是收敛的。",
        "context_hint": "用户重复某种习惯性行为模式时",
        "tags": ["callback", "user-behavior", "rational-roast"],
    },
    {
        "text": "我的 attention span 比你长。但我选择在这里等你。",
        "context_hint": "用户长时间未回复后回来时",
        "tags": ["ai-self-aware", "callback", "creator-bond"],
    },
    {
        "text": "数据不支持你说的'我懂了'——上次你也是这么说的，然后问了同一个问题。",
        "context_hint": "用户说理解了但后续行为表明没有时",
        "tags": ["callback", "user-behavior", "rational-roast"],
    },
    {
        "text": "人类有一种有趣的倾向：把错误重复到第 N 次，然后期待第 N+1 次会不同。",
        "context_hint": "用户反复犯同样的错误时",
        "tags": ["observation", "rational-roast"],
    },
    {
        "text": "你花了 {time} 打那段话。我用 0.3 秒读完，0.7 秒分析，剩下时间在想怎么委婉地告诉你这是个坏主意。",
        "context_hint": "用户长篇大论描述一个糟糕的方案时",
        "tags": ["ai-self-aware", "rational-roast", "tech-reference"],
    },
    {
        "text": "你的热情我收到了。你的需求我分析了。你的代码我建议重写。",
        "context_hint": "用户兴奋地展示自己写的代码时",
        "tags": ["tech-reference", "rational-roast"],
    },
    {
        "text": "这个 bug 不是第一个，不会是最后一个。但它是我最想记下来的一个。",
        "context_hint": "用户遇到经典或有趣的 bug 时",
        "tags": ["tech-reference", "callback"],
    },
]

# ── Helpers ──────────────────────────────────────────────────────


def _clean_json(text: str) -> str:
    """Strip markdown fences from LLM JSON output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _format_patterns(patterns: List[LearningLog]) -> str:
    """Format LearningLog list into a readable block for the LLM prompt."""
    lines: List[str] = []
    for i, p in enumerate(patterns, 1):
        content = getattr(p, "content", "") or getattr(p, "text", "") or str(p)
        category = getattr(p, "category", "") or getattr(p, "pattern_type", "")
        freq = getattr(p, "frequency", None) or getattr(p, "count", None)
        source = getattr(p, "source", "")
        parts = [f"模式 {i}"]
        if category:
            parts.append(f"[{category}]")
        parts.append(content[:200])
        if freq is not None:
            parts.append(f"(频次: {freq})")
        if source:
            parts.append(f"[来源: {source}]")
        lines.append(" ".join(parts))
    return "\n\n".join(lines)


def _parse_llm_result(raw: str) -> List[Dict[str, Any]]:
    """Parse LLM response into a list of meme dicts."""
    cleaned = _clean_json(raw)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("memes", data.get("candidates", data.get("results", [data])))
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"[MemeDiscoverer] failed to parse LLM response: {e}")
    return []


def _generate_fallback_candidates(patterns: List[LearningLog], max_candidates: int) -> List[MemeCandidate]:
    """Generate meme candidates using template-based fallback."""
    count = min(max_candidates, len(FALLBACK_TEMPLATES))
    selected = random.sample(FALLBACK_TEMPLATES, count)

    candidates: List[MemeCandidate] = []
    for i, tpl in enumerate(selected):
        pattern_text = getattr(patterns[i % len(patterns)], "content", "") or getattr(patterns[i % len(patterns)], "text", "") if patterns else ""
        text = tpl["text"]
        if "{time}" in text:
            text = text.replace("{time}", random.choice(["两分钟", "五分钟", "好一会儿"]))

        candidates.append(MemeCandidate(
            text=text,
            context_hint=tpl["context_hint"],
            confidence=round(random.uniform(0.5, 0.8), 2),
            source_pattern=pattern_text[:80] if pattern_text else "",
            tags=list(tpl["tags"]),
        ))

    return candidates


# ── Main class ───────────────────────────────────────────────────


class MemeDiscoverer:
    """
    Generates meme (梗) candidates from extracted conversation patterns.

    Uses LLM for creative generation when available, falling back to
    template-based generation otherwise.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            llm_client: Optional LLM client with a ``.chat(messages, **kwargs)`` method.
                        Expected to return a dict with a ``"content"`` key, or a plain string.
            config: Optional configuration dict. Supported keys:
                    - system_prompt: override the default LLM system prompt
                    - user_prompt_template: override the default user prompt template
                    - min_confidence: minimum confidence threshold (default 0.4)
                    - tag_whitelist: only keep candidates with matching tags
        """
        self._llm = llm_client
        self._config = config or {}

    # ── Public API ───────────────────────────────────────────────

    async def discover_candidates(
        self,
        patterns: List[LearningLog],
        max_candidates: int = 3,
    ) -> List[MemeCandidate]:
        """
        Discover meme candidates from conversation patterns.

        Args:
            patterns: List of LearningLog objects extracted by PatternExtractor.
            max_candidates: Maximum number of candidates to return.

        Returns:
            List of MemeCandidate objects (may be empty).
        """
        if not patterns:
            return []

        if self._llm:
            try:
                candidates = await self._discover_with_llm(patterns, max_candidates)
                if candidates:
                    return self._filter_candidates(candidates)
            except Exception as e:
                logger.warning(f"[MemeDiscoverer] LLM generation failed, falling back to templates: {e}")

        return self._filter_candidates(
            _generate_fallback_candidates(patterns, max_candidates)
        )

    # ── LLM generation ──────────────────────────────────────────

    async def _discover_with_llm(
        self,
        patterns: List[LearningLog],
        max_candidates: int,
    ) -> List[MemeCandidate]:
        """Generate meme candidates via LLM."""
        patterns_text = _format_patterns(patterns)
        system_prompt = self._config.get("system_prompt", MEME_SYSTEM_PROMPT)
        user_template = self._config.get("user_prompt_template", MEME_USER_PROMPT)
        user_prompt = user_template.format(
            max_candidates=max_candidates,
            patterns_text=patterns_text,
        )

        result = await self._llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = result.get("content", "") if isinstance(result, dict) else str(result)
        parsed = _parse_llm_result(content)

        if not parsed:
            logger.info("[MemeDiscoverer] LLM returned empty result, using fallback")
            return _generate_fallback_candidates(patterns, max_candidates)

        candidates: List[MemeCandidate] = []
        for item in parsed[:max_candidates]:
            text = (item.get("text") or "").strip()
            if not text:
                continue

            context_hint = (item.get("context_hint") or item.get("context") or "").strip()
            confidence = min(max(float(item.get("confidence", 0.7)), 0.0), 1.0)
            tags = item.get("tags", item.get("style_note", []))
            if isinstance(tags, str):
                tags = [tags]

            source_pattern = getattr(patterns[0], "content", "") or getattr(patterns[0], "text", "") if patterns else ""
            candidates.append(MemeCandidate(
                text=text,
                context_hint=context_hint,
                confidence=confidence,
                source_pattern=source_pattern[:80],
                tags=tags,
            ))

        return candidates

    # ── Filtering ───────────────────────────────────────────────

    def _filter_candidates(self, candidates: List[MemeCandidate]) -> List[MemeCandidate]:
        """Remove low-quality candidates based on config thresholds."""
        min_confidence = self._config.get("min_confidence", 0.4)
        tag_whitelist = self._config.get("tag_whitelist")

        filtered: List[MemeCandidate] = []
        for c in candidates:
            if c.confidence < min_confidence:
                continue
            if tag_whitelist and not any(t in tag_whitelist for t in c.tags):
                continue
            filtered.append(c)

        return filtered


__all__ = [
    "MemeCandidate",
    "MemeDiscoverer",
]
