"""
MBTIAnalyzer — analyzes conversation patterns to suggest MBTI dimension adjustments.

Uses LLM analysis to examine recent AI responses and infer subtle shifts
in personality expression across the four MBTI dimensions (E/I, S/N, T/F, J/P).

Outputs per-dimension delta suggestions with confidence scores, which are
then passed through guardrails before being applied to the stored profile.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# LLM analysis prompt for MBTI dimension inference
MBTI_ANALYSIS_SYSTEM_PROMPT = """你是一个 AI 角色的"性格分析专家"。你的任务是分析 AI 角色的对话回应，
推断它在 MBTI 四维性格各维度上的当前倾向，并给出分数微调建议。

分析依据：从 AI 角色的回应方式中判断性格倾向。

维度说明：
1. **E/I (外向/内向)**：高分→主动、互动性强、乐于展开话题；低分→被动、简洁、保持距离
2. **S/N (实感/直觉)**：高分→抽象、理论、联想；低分→具体、实操、细节
3. **T/F (理性/共情)**：高分→逻辑分析、客观、原则；低分→情感关怀、体贴、共情
4. **J/P (判断/感知)**：高分→结构化、结论性、确定；低分→开放式、探索性、灵活

分析规则：
- 比较当前对话模式与上次已知状态（如果有）
- 每个维度的调整值范围：-5 到 +5
- 当证据不足时，给出 0 调整值和低 confidence
- 只在有明确证据支持时给出非零调整

返回 JSON：
{
  "dimension_adjustments": {
    "ei": {"delta": 0, "confidence": 0.0, "evidence": "..."},
    "sn": {"delta": 0, "confidence": 0.0, "evidence": "..."},
    "tf": {"delta": 0, "confidence": 0.0, "evidence": "..."},
    "jp": {"delta": 0, "confidence": 0.0, "evidence": "..."}
  },
  "summary": "一句话总结",
  "analysis_skipped": false
}

如果没有足够数据（少于 3 条对话），设置 analysis_skipped=true。
"""

MBTI_ANALYSIS_USER_PROMPT = """请分析以下 AI 角色的对话回应，推断 MBTI 维度变化。

当前 MBTI 状态：
{current_profile}

最近的 {log_count} 条对话回应（仅 AI 部分）：
{conversation_logs}

分析结果："""


class MBTIAnalysisResult:
    """Result of an MBTI analysis run."""

    def __init__(
        self,
        dimension_adjustments: Dict[str, Dict[str, Any]],
        summary: str = "",
        analysis_skipped: bool = False,
    ):
        self.dimension_adjustments = dimension_adjustments
        self.summary = summary
        self.analysis_skipped = analysis_skipped

    @property
    def has_adjustments(self) -> bool:
        """Check if any non-zero adjustments were suggested."""
        if self.analysis_skipped:
            return False
        for dim_key, adj in self.dimension_adjustments.items():
            if abs(adj.get("delta", 0)) > 0 and adj.get("confidence", 0) >= 0.7:
                return True
        return False


class MBTIAnalyzer:
    """Analyzes conversation logs to suggest MBTI dimension adjustments.

    Reuses the same LLM analysis pattern as PatternExtractor:
    system prompt + user prompt → JSON response.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._llm_client = llm_client
        self._config = config or {}

        # Guardrails
        self._max_delta = self._config.get("max_delta_per_dim", 5)
        self._min_confidence = self._config.get("min_confidence", 0.7)
        self._max_cumulative_drift = self._config.get("max_cumulative_drift", 30)
        self._min_logs = self._config.get("min_logs_for_analysis", 3)

    async def analyze(
        self,
        conversation_logs: List[Dict[str, str]],
        current_profile: Optional[Dict[str, Any]] = None,
    ) -> MBTIAnalysisResult:
        """Analyze conversation logs and suggest MBTI adjustments.

        Args:
            conversation_logs: List of dicts with keys: content, session_id, created_at
            current_profile: Current MBTI profile dict (type, dimensions, etc.)

        Returns:
            MBTIAnalysisResult with dimension adjustments
        """
        if not self._llm_client or len(conversation_logs) < self._min_logs:
            return MBTIAnalysisResult(
                dimension_adjustments=self._empty_adjustments(),
                summary="Insufficient data for analysis",
                analysis_skipped=True,
            )

        # Format current profile
        profile_str = self._format_profile(current_profile)

        # Format logs (only AI responses)
        log_texts = []
        for log in conversation_logs[:20]:  # max 20 logs
            content = log.get("content", "")[:500]
            if content:
                log_texts.append(f"- {content}")
        logs_text = "\n".join(log_texts)

        try:
            result = await self._llm_client.chat_messages(
                messages=[
                    {"role": "system", "content": MBTI_ANALYSIS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": MBTI_ANALYSIS_USER_PROMPT.format(
                            current_profile=profile_str,
                            log_count=len(conversation_logs),
                            conversation_logs=logs_text,
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )
            content = result.get("content", "") if isinstance(result, dict) else str(result)
            content = self._clean_json(content)

            data = json.loads(content)
            adjustments = data.get("dimension_adjustments", {})
            summary = data.get("summary", "")
            skipped = data.get("analysis_skipped", False)

            # Apply guardrails
            adjusted = self._apply_guardrails(adjustments)

            return MBTIAnalysisResult(
                dimension_adjustments=adjusted,
                summary=summary,
                analysis_skipped=skipped,
            )

        except Exception as e:
            logger.warning(f"[MBTIAnalyzer] Analysis failed: {e}")
            return MBTIAnalysisResult(
                dimension_adjustments=self._empty_adjustments(),
                summary=f"Analysis failed: {e}",
                analysis_skipped=True,
            )

    # ── Guardrails ────────────────────────────────────────────

    def _apply_guardrails(
        self, adjustments: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Apply safety guardrails to dimension adjustments.

        Rules:
        1. Clamp delta to ±max_delta
        2. Zero out adjustments below confidence threshold
        3. Reject adjustments exceeding cumulative drift
        """
        result: Dict[str, Dict[str, Any]] = {}
        for dim_key in ("ei", "sn", "tf", "jp"):
            adj = adjustments.get(dim_key, {})
            delta = adj.get("delta", 0)
            confidence = adj.get("confidence", 0.0)
            evidence = adj.get("evidence", "")

            # Rule 1: Clamp delta
            delta = max(-self._max_delta, min(self._max_delta, delta))

            # Rule 2: Low confidence → zero out
            if confidence < self._min_confidence:
                delta = 0
                evidence = "(low confidence, skipped)"

            result[dim_key] = {
                "delta": delta,
                "confidence": confidence,
                "evidence": evidence,
            }

        return result

    def check_cumulative_drift(
        self, current_dims: Dict[str, int], initial_dims: Dict[str, int]
    ) -> List[str]:
        """Check if cumulative drift exceeds threshold.

        Returns:
            List of dimension keys that exceed the drift threshold.
        """
        exceeded: List[str] = []
        for key in ("ei", "sn", "tf", "jp"):
            drift = abs(current_dims.get(key, 50) - initial_dims.get(key, 50))
            if drift > self._max_cumulative_drift:
                exceeded.append(key)
        return exceeded

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _empty_adjustments() -> Dict[str, Dict[str, Any]]:
        return {
            "ei": {"delta": 0, "confidence": 0.0, "evidence": ""},
            "sn": {"delta": 0, "confidence": 0.0, "evidence": ""},
            "tf": {"delta": 0, "confidence": 0.0, "evidence": ""},
            "jp": {"delta": 0, "confidence": 0.0, "evidence": ""},
        }

    @staticmethod
    def _format_profile(profile: Optional[Dict[str, Any]]) -> str:
        if not profile:
            return "（无历史数据）"
        dims = profile.get("dimensions", {})
        return (
            f"类型: {profile.get('type', 'N/A')}\n"
            f"E/I: {dims.get('ei', 50)}, "
            f"S/N: {dims.get('sn', 50)}, "
            f"T/F: {dims.get('tf', 50)}, "
            f"J/P: {dims.get('jp', 50)}"
        )

    @staticmethod
    def _clean_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
