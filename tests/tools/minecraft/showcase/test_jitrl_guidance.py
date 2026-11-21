"""JitRL guidance rendering: thresholds, shrinkage, and malformed-table rejection."""

from __future__ import annotations

import json

import pytest

from animetta.acceptance.minecraft_jitrl import (
    JitrlGuidanceError,
    format_jitrl_guidance,
    load_advantage_table,
    shrunken_advantage,
)


def _table(*entries: dict) -> dict:
    return {"schema": 1, "entries": list(entries), "source": "unit"}


def test_blacklist_and_recommend_partition_at_thresholds() -> None:
    table = _table(
        {
            "pattern": "fill_water_bucket 在无水视图时",
            "advantage": -2.24,
            "samples": 41,
            "attribution": "world",
            "gate": "water_in_view=false",
            "note": "8% 成功率",
        },
        {
            "pattern": "有桶后长距探索",
            "advantage": 5.76,
            "samples": 35,
            "gate": "bucket=true",
            "note": "探索收益窗口",
        },
        {"pattern": "craft 集中在铁器后", "advantage": 0.05, "samples": 50},
    )
    guidance = format_jitrl_guidance(table)
    assert len(guidance["blacklist"]) == 1
    assert "无水视图" in guidance["blacklist"][0]
    assert "限 world、water_in_view=false" in guidance["blacklist"][0]
    assert len(guidance["recommend"]) == 1
    assert "有桶后长距探索" in guidance["recommend"][0]
    assert len(guidance["reading_rules"]) == 4


def test_small_samples_are_shrunk_below_threshold() -> None:
    assert shrunken_advantage(-2.0, 5) == pytest.approx(-1.0)
    assert shrunken_advantage(-2.0, 30) == pytest.approx(-2.0)
    # A strong negative with only 4 samples shrinks to -0.89 → still blacklisted.
    assert shrunken_advantage(-2.5, 4) == pytest.approx(-2.5 * 4 / 9)
    # -0.5 with 4 samples shrinks to -0.22 → drops below the -0.30 threshold.
    table = _table({"pattern": "被收缩淘汰项", "advantage": -0.5, "samples": 4})
    assert format_jitrl_guidance(table)["blacklist"] == []
    # -0.9 with 4 samples shrinks to -0.4 → still blacklisted.
    table = _table({"pattern": "浅样本黑名单项", "advantage": -0.9, "samples": 4})
    guidance = format_jitrl_guidance(table)
    assert guidance["blacklist"] == ["浅样本黑名单项"]


def test_tiny_samples_are_dropped_entirely() -> None:
    table = _table({"pattern": "噪音项", "advantage": -9.0, "samples": 2})
    guidance = format_jitrl_guidance(table)
    assert guidance["blacklist"] == []
    assert guidance["recommend"] == []


def test_load_rejects_malformed_tables() -> None:
    with pytest.raises(JitrlGuidanceError):
        load_advantage_table("{not json")
    with pytest.raises(JitrlGuidanceError):
        load_advantage_table(json.dumps({"schema": 2, "entries": []}))
    with pytest.raises(JitrlGuidanceError):
        load_advantage_table(json.dumps({"schema": 1}))
    with pytest.raises(JitrlGuidanceError):
        load_advantage_table(json.dumps({"schema": 1, "entries": [{"advantage": -1.0}]}))
    with pytest.raises(JitrlGuidanceError):
        load_advantage_table(
            json.dumps(
                {"schema": 1, "entries": [{"pattern": "p", "advantage": "low", "samples": 3}]}
            )
        )


def test_load_normalizes_optional_fields() -> None:
    table = load_advantage_table(
        json.dumps({"schema": 1, "entries": [{"pattern": "p", "advantage": -1, "samples": 9}]})
    )
    assert table["entries"][0]["note"] == ""
    assert table["entries"][0]["attribution"] == ""
    guidance = format_jitrl_guidance(table)
    assert guidance["blacklist"] == ["p"]  # -9/14 ≈ -0.64 still ≤ -0.30
