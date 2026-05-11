"""
Persona optimizer — analyzes conversation patterns and suggests persona prompt adjustments.

Runs as a scheduled task in PeriodicLearner. Output is a reviewable YAML file
that can be manually applied or (optionally) auto-applied.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# LLM analysis prompt for persona optimization
PERSONA_ANALYSIS_SYSTEM_PROMPT = """你是一个 AI 角色的"表现分析师"。你的任务是分析 Anima (一个 AI VTuber 角色) 的对话日志，找出哪些互动模式效果好、哪些需要调整。

分析维度：

1. **用户参与度**：哪些风格的回复让用户继续深入对话？哪些让对话冷场？
2. **角色一致性**：哪些回复偏离了角色人设？哪些完美契合？
3. **重复模式**：角色是否过于重复某些表达或行为？
4. **情感适当性**：角色在特定情境下的情绪反应是否恰当？
5. **改进建议**：基于以上分析，给出 1-3 条具体的人设微调建议。

返回 JSON：
{
  "strengths": [
    {"pattern": "风格描述", "evidence": "证据摘要", "confidence": 0.8}
  ],
  "weaknesses": [
    {"pattern": "问题描述", "severity": "high|medium|low", "evidence": "证据摘要"}
  ],
  "suggestions": [
    {
      "target_field": "personality.traits | personality.speaking_style | behavior.forbidden_phrases | behavior.response_to_praise | examples",
      "action": "add | modify | remove",
      "current_value": "当前内容...",
      "suggested_value": "建议改为...",
      "rationale": "理由 (引用具体对话证据)",
      "confidence": 0.6
    }
  ],
  "summary": "一句话总结本次分析的核心发现"
}

规则：
- 每条建议必须有具体对话证据支撑
- 没有足够证据时，suggestions 返回空数组
- confidence 基于证据质量和数量
- 优先关注高频出现的模式，而非偶发事件
"""

PERSONA_ANALYSIS_USER_PROMPT = """请分析以下 AI 角色的对话表现。

当前人设：
{persona_summary}

最近的对话摘要（{log_count} 条）：
{conversation_logs}

分析结果："""


async def analyze_persona_performance(
    llm_client: Any,
    persona_config: Dict[str, Any],
    conversation_logs: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Analyze persona performance from conversation logs.

    Args:
        llm_client: LLM client with chat(messages, response_format) method
        persona_config: Current persona configuration
        conversation_logs: List of {content, session_id, created_at} summaries

    Returns:
        Analysis dict with strengths, weaknesses, suggestions
    """
    if not llm_client or not conversation_logs:
        return {"suggestions": [], "summary": "Insufficient data for analysis"}

    persona_summary = _summarize_persona(persona_config)
    logs_text = _format_logs(conversation_logs)

    try:
        result = await llm_client.chat(
            messages=[
                {"role": "system", "content": PERSONA_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": PERSONA_ANALYSIS_USER_PROMPT.format(
                    persona_summary=persona_summary,
                    log_count=len(conversation_logs),
                    conversation_logs=logs_text,
                )},
            ],
            response_format={"type": "json_object"},
        )
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        content = _clean_json(content)

        data = json.loads(content)
        return data
    except Exception as e:
        logger.warning(f"[PersonaOptimizer] Analysis failed: {e}")
        return {"suggestions": [], "summary": f"Analysis failed: {e}"}


def format_suggestions_yaml(analysis: Dict[str, Any], persona_name: str) -> str:
    """Format analysis results as a reviewable YAML file.

    This YAML is intended for human review before application.
    """
    now = datetime.now()
    lines = [
        f"# Persona Evolution Suggestions",
        f"# Generated: {now.isoformat()}",
        f"# Persona: {persona_name}",
        f"# Status: review",
        f"# Auto-apply: false  # 设为 true 允许自动应用",
        f"",
        f"analysis_date: \"{now.isoformat()}\"",
        f"persona: \"{persona_name}\"",
        f"summary: \"{analysis.get('summary', '')}\"",
        f"",
    ]

    strengths = analysis.get("strengths", [])
    if strengths:
        lines.append("strengths:")
        for s in strengths:
            lines.append(f"  - pattern: \"{s.get('pattern', '')}\"")
            lines.append(f"    evidence: \"{s.get('evidence', '')}\"")
            lines.append(f"    confidence: {s.get('confidence', 0.5)}")

    weaknesses = analysis.get("weaknesses", [])
    if weaknesses:
        lines.append("")
        lines.append("weaknesses:")
        for w in weaknesses:
            lines.append(f"  - pattern: \"{w.get('pattern', '')}\"")
            lines.append(f"    severity: \"{w.get('severity', 'medium')}\"")
            lines.append(f"    evidence: \"{w.get('evidence', '')}\"")

    suggestions = analysis.get("suggestions", [])
    if suggestions:
        lines.append("")
        lines.append("suggestions:")
        for i, s in enumerate(suggestions):
            lines.append(f"  - id: \"suggestion_{now.strftime('%Y%m%d')}_{i + 1}\"")
            lines.append(f"    target_field: \"{s.get('target_field', 'unknown')}\"")
            lines.append(f"    action: \"{s.get('action', 'add')}\"")
            lines.append(f"    current_value: \"{s.get('current_value', '')}\"")
            lines.append(f"    suggested_value: \"{s.get('suggested_value', '')}\"")
            lines.append(f"    rationale: \"{s.get('rationale', '')}\"")
            lines.append(f"    confidence: {s.get('confidence', 0.5)}")
            lines.append(f"    applied: false")
    else:
        lines.append("")
        lines.append("suggestions: []  # No suggestions this cycle")

    return "\n".join(lines)


def apply_suggestion(yaml_path: Path, suggestion_id: str) -> bool:
    """Mark a suggestion as applied in the YAML file.

    Args:
        yaml_path: Path to the evolution suggestions file
        suggestion_id: ID of suggestion to mark as applied

    Returns:
        True if successfully applied
    """
    if not yaml_path.exists():
        return False
    content = yaml_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    updated = False
    in_target = False
    for i, line in enumerate(lines):
        if f"id: \"{suggestion_id}\"" in line:
            in_target = True
        if in_target and "applied:" in line:
            lines[i] = line.replace("applied: false", "applied: true")
            updated = True
            break
    if updated:
        yaml_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"[PersonaOptimizer] Applied suggestion: {suggestion_id}")
    return updated


# ── Helpers ──────────────────────────────────────────────────


def _summarize_persona(config: Dict[str, Any]) -> str:
    """Create a concise persona summary for the LLM analysis prompt."""
    parts = []
    if config.get("name"):
        parts.append(f"Name: {config['name']}")
    if config.get("identity"):
        identity = config["identity"].replace("\n", " ")[:300]
        parts.append(f"Identity: {identity}")
    if config.get("personality"):
        p = config["personality"]
        if isinstance(p, dict):
            if p.get("traits"):
                parts.append(f"Traits: {', '.join(p['traits'])}")
            if p.get("speaking_style"):
                parts.append(f"Style: {', '.join(p['speaking_style'])}")
    if config.get("behavior"):
        b = config["behavior"]
        if isinstance(b, dict) and b.get("forbidden_phrases"):
            parts.append(f"Forbidden: {', '.join(b['forbidden_phrases'])}")
    return "\n".join(parts)


def _format_logs(logs: List[Dict[str, str]]) -> str:
    """Format conversation logs for the LLM prompt."""
    lines = []
    for i, log in enumerate(logs[:20]):  # limit to 20
        content = log.get("content", "")[:500]
        session = log.get("session_id", "unknown")[:8]
        date = log.get("created_at", "")[:10]
        lines.append(f"### 会话 {i + 1} ({date}, {session})")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


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
