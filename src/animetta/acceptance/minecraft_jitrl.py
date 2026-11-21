"""Offline-derived advantage guidance for bounded mission proposal prompts.

The evaluator behind this module is not part of the runtime: kernel-weighted
advantages are computed offline from audited round journals and shipped to the
planner as a small JSON table. The runtime only renders that table into three
bounded prompt sections (blacklist / recommendation / reading rules), so a bad
table degrades guidance text, never mission authority or host budgets.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

BLACKLIST_ADVANTAGE = -0.30
RECOMMEND_SCORE = 0.20
SHRINKAGE_PRIOR = 5.0
SHRINKAGE_FULL_SAMPLES = 30
MIN_SAMPLES = 3
TABLE_SCHEMA = 1


class JitrlGuidanceError(ValueError):
    """Raised when an advantage table cannot be trusted for prompt injection."""


def load_advantage_table(source: str | Path) -> dict[str, Any]:
    """Parse and validate an advantage table; text content or a file path."""
    text = Path(source).read_text(encoding="utf-8") if isinstance(source, Path) else source
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise JitrlGuidanceError(f"advantage table is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != TABLE_SCHEMA:
        raise JitrlGuidanceError(f"advantage table schema must be {TABLE_SCHEMA}")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise JitrlGuidanceError("advantage table needs a non-empty entries list")
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise JitrlGuidanceError("each entry must be an object")
        pattern = entry.get("pattern")
        advantage = entry.get("advantage")
        samples = entry.get("samples")
        if not isinstance(pattern, str) or not pattern.strip():
            raise JitrlGuidanceError("each entry needs a non-empty pattern string")
        if not isinstance(advantage, (int, float)) or isinstance(advantage, bool):
            raise JitrlGuidanceError(f"entry {pattern!r}: advantage must be numeric")
        if not isinstance(samples, int) or isinstance(samples, bool) or samples < 0:
            raise JitrlGuidanceError(f"entry {pattern!r}: samples must be a non-negative int")
        normalized.append(
            {
                "pattern": pattern,
                "advantage": float(advantage),
                "samples": int(samples),
                "note": str(entry.get("note", "")),
                "attribution": str(entry.get("attribution", "")),
                "gate": str(entry.get("gate", "")),
            }
        )
    return {"schema": TABLE_SCHEMA, "entries": normalized, "source": data.get("source", "")}


def shrunken_advantage(advantage: float, samples: int) -> float:
    """Dampen small-sample advantages toward zero (empirical-Bayes style)."""
    if samples >= SHRINKAGE_FULL_SAMPLES:
        return advantage
    return advantage * samples / (samples + SHRINKAGE_PRIOR)


def _render(entries: Iterable[dict[str, Any]], threshold: float, *, blacklist: bool) -> list[str]:
    lines = []
    for entry in sorted(entries, key=lambda item: item["advantage"]):
        pattern = entry["pattern"]
        value = shrunken_advantage(entry["advantage"], entry["samples"])
        meets = value <= threshold if blacklist else value >= threshold
        if entry["samples"] < MIN_SAMPLES or not meets:
            continue
        scope = "、".join(
            part for part in (entry.get("attribution", ""), entry.get("gate", "")) if part
        )
        suffix = f"（限 {scope}）" if scope else ""
        note = f"：{entry.get('note', '')}" if entry.get("note") else ""
        lines.append(f"{pattern}{suffix}{note}")
    return lines


def format_jitrl_guidance(
    table: Mapping[str, Any],
    *,
    blacklist_threshold: float = BLACKLIST_ADVANTAGE,
    recommend_threshold: float = RECOMMEND_SCORE,
) -> dict[str, Any]:
    """Render the three-part guidance block injected into proposal prompts."""
    if not isinstance(table, Mapping) or table.get("schema") != TABLE_SCHEMA:
        raise JitrlGuidanceError("format_jitrl_guidance expects a validated table")
    entries = list(table["entries"])
    blacklist = _render(entries, blacklist_threshold, blacklist=True)
    recommend = _render(
        (entry for entry in entries if entry["advantage"] > 0), recommend_threshold, blacklist=False
    )
    return {
        "blacklist": blacklist,
        "recommend": recommend,
        "reading_rules": [
            "以下条目来自历史轮次离线统计（动作×归因×门控），只影响提案取舍，不改变任务、预算或成功谓词。",
            "blacklist 是同一条件下重复亏损的模式：提案中不得再现这些组合，除非给出了新的前置条件说明。",
            "recommend 是历史高回报模式：优先采用，但仍需满足当前 observation 的实际条件。",
            "样本量小的条目已被收缩；表中数值不是奖励，禁止在程序里复现或优化这些数字。",
        ],
    }
