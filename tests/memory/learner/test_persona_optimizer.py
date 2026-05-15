"""Tests for PersonaOptimizer — performance analysis, YAML suggestion formatting, apply."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from anima.memory.learner.persona_optimizer import (
    PERSONA_ANALYSIS_SYSTEM_PROMPT,
    PERSONA_ANALYSIS_USER_PROMPT,
    analyze_persona_performance,
    format_suggestions_yaml,
    apply_suggestion,
    _summarize_persona,
    _format_logs,
    _clean_json,
)


# ── Helpers ────────────────────────────────────────────────────


def _make_llm_response(content: str) -> dict:
    return {"content": content}


# ── Tests ─────────────────────────────────────────────────────


class TestAnalyzePersonaPerformance:
    async def test_no_llm_returns_insufficient(self):
        result = await analyze_persona_performance(
            llm_client=None,
            persona_config={"name": "Test"},
            conversation_logs=[{"content": "hello", "session_id": "s1", "created_at": "2026-01-01"}],
        )
        assert result["suggestions"] == []
        assert "Insufficient" in result["summary"]

    async def test_empty_logs_returns_insufficient(self, mock_llm):
        result = await analyze_persona_performance(
            llm_client=mock_llm,
            persona_config={"name": "Test"},
            conversation_logs=[],
        )
        assert result["suggestions"] == []
        assert "Insufficient" in result["summary"]

    async def test_successful_analysis_with_suggestions(self, mock_llm):
        analysis_data = {
            "strengths": [
                {"pattern": "冷静分析风格", "evidence": "多次以逻辑方式回应", "confidence": 0.8}
            ],
            "weaknesses": [
                {"pattern": "过于冷淡", "severity": "medium", "evidence": "用户表达了情感需求但未回应"}
            ],
            "suggestions": [
                {
                    "target_field": "personality.traits",
                    "action": "modify",
                    "current_value": "极度理性",
                    "suggested_value": "在保持理性基础上适度增加温度",
                    "rationale": "用户在3次对话中表达了情感诉求，当前回复过于机械",
                    "confidence": 0.7,
                }
            ],
            "summary": "整体表现良好，情感回应可以更温暖",
        }
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            json.dumps(analysis_data)
        ))
        result = await analyze_persona_performance(
            llm_client=mock_llm,
            persona_config={"name": "Anima", "identity": "AI VTuber"},
            conversation_logs=[
                {"content": "user said hello", "session_id": "s1", "created_at": "2026-05-01"},
                {"content": "user said goodbye", "session_id": "s2", "created_at": "2026-05-02"},
            ],
        )
        assert result["summary"] == "整体表现良好，情感回应可以更温暖"
        assert len(result["strengths"]) == 1
        assert len(result["weaknesses"]) == 1
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["target_field"] == "personality.traits"

    async def test_analysis_with_no_suggestions(self, mock_llm):
        analysis_data = {
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "summary": "数据不足，无法提供建议",
        }
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            json.dumps(analysis_data)
        ))
        result = await analyze_persona_performance(
            llm_client=mock_llm,
            persona_config={"name": "Test"},
            conversation_logs=[{"content": "hi", "session_id": "s1", "created_at": "2026-01-01"}],
        )
        assert result["suggestions"] == []

    async def test_analysis_llm_failure_returns_error(self, mock_llm):
        mock_llm.chat = AsyncMock(side_effect=RuntimeError("API down"))
        result = await analyze_persona_performance(
            llm_client=mock_llm,
            persona_config={"name": "Test"},
            conversation_logs=[{"content": "hi", "session_id": "s1", "created_at": "2026-01-01"}],
        )
        assert "failed" in result["summary"].lower()
        assert result["suggestions"] == []

    async def test_analysis_llm_returns_string_not_dict(self, mock_llm):
        """When LLM returns content as a string (not dict)."""
        mock_llm.chat = AsyncMock(return_value="raw string response")
        result = await analyze_persona_performance(
            llm_client=mock_llm,
            persona_config={"name": "Test"},
            conversation_logs=[{"content": "hi", "session_id": "s1", "created_at": "2026-01-01"}],
        )
        # Should handle gracefully
        assert isinstance(result, (dict, type(None)))

    async def test_analysis_includes_persona_summary_in_prompt(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '{"suggestions": [], "summary": "ok"}'
        ))
        await analyze_persona_performance(
            llm_client=mock_llm,
            persona_config={
                "name": "CustomAnima",
                "identity": "A cool AI vtuber",
                "personality": {
                    "traits": ["理性", "幽默"],
                    "speaking_style": ["简洁", "精准"],
                },
                "behavior": {
                    "forbidden_phrases": ["呀", "哦"],
                },
            },
            conversation_logs=[{"content": "test", "session_id": "s1"}],
        )
        call_args = mock_llm.chat.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[1]["content"]
        assert "CustomAnima" in user_msg
        assert "理性" in user_msg
        assert "简洁" in user_msg
        assert "呀" in user_msg


class TestFormatSuggestionsYaml:
    def test_format_with_suggestions(self):
        analysis = {
            "summary": "需要进行风格调整",
            "strengths": [
                {"pattern": "逻辑清晰", "evidence": "对话连贯", "confidence": 0.9}
            ],
            "weaknesses": [
                {"pattern": "回应过于简短", "severity": "medium", "evidence": "3次对话回复不足10字"}
            ],
            "suggestions": [
                {
                    "target_field": "personality.speaking_style",
                    "action": "modify",
                    "current_value": "过于简洁",
                    "suggested_value": "适度扩展回复",
                    "rationale": "对话数据显示回应过于简短导致冷场",
                    "confidence": 0.65,
                }
            ],
        }
        yaml_str = format_suggestions_yaml(analysis, "Anima")
        assert "# Persona Evolution Suggestions" in yaml_str
        assert "persona: \"Anima\"" in yaml_str
        assert "需要进行风格调整" in yaml_str
        assert "suggestion_" in yaml_str
        assert "target_field" in yaml_str
        assert "personality.speaking_style" in yaml_str
        assert "applied: false" in yaml_str
        assert "Auto-apply: false" in yaml_str
        assert "strengths:" in yaml_str
        assert "weaknesses:" in yaml_str
        assert "suggestions:" in yaml_str

    def test_format_no_suggestions(self):
        analysis = {
            "summary": "无建议",
            "suggestions": [],
        }
        yaml_str = format_suggestions_yaml(analysis, "TestPersona")
        assert "suggestions: []  # No suggestions this cycle" in yaml_str

    def test_format_no_strengths_or_weaknesses(self):
        analysis = {
            "summary": "minimal",
            "suggestions": [],
        }
        yaml_str = format_suggestions_yaml(analysis, "P")
        assert "persona: \"P\"" in yaml_str
        assert "strengths:" not in yaml_str

    def test_format_includes_generation_date(self):
        analysis = {"summary": "ok", "suggestions": []}
        yaml_str = format_suggestions_yaml(analysis, "P")
        assert "analysis_date:" in yaml_str
        assert "Generated:" in yaml_str

    def test_format_multiple_suggestions(self):
        analysis = {
            "summary": "test",
            "suggestions": [
                {
                    "target_field": "personality.traits",
                    "action": "add",
                    "current_value": "",
                    "suggested_value": "更温暖",
                    "rationale": "理由1",
                    "confidence": 0.6,
                },
                {
                    "target_field": "behavior.forbidden_phrases",
                    "action": "remove",
                    "current_value": "禁止用语",
                    "suggested_value": "",
                    "rationale": "理由2",
                    "confidence": 0.8,
                },
            ],
        }
        yaml_str = format_suggestions_yaml(analysis, "P")
        # Two suggestion blocks
        assert yaml_str.count("suggestion_") >= 2
        assert "personality.traits" in yaml_str
        assert "behavior.forbidden_phrases" in yaml_str
        assert yaml_str.count("applied: false") >= 2


class TestApplySuggestion:
    def test_apply_existing_suggestion(self, tmp_path):
        yaml_file = tmp_path / "evolution.yml"
        yaml_file.write_text(
            "- id: \"suggestion_20260501_1\"\n"
            "  applied: false\n"
            "- id: \"suggestion_20260501_2\"\n"
            "  applied: false\n",
            encoding="utf-8",
        )
        result = apply_suggestion(yaml_file, "suggestion_20260501_1")
        assert result is True
        content = yaml_file.read_text(encoding="utf-8")
        assert "applied: true" in content
        # Other suggestion should remain false
        assert content.count("applied: false") == 1

    def test_apply_nonexistent_file(self, tmp_path):
        yaml_file = tmp_path / "nonexistent.yml"
        result = apply_suggestion(yaml_file, "suggestion_001")
        assert result is False

    def test_apply_nonexistent_suggestion_id(self, tmp_path):
        yaml_file = tmp_path / "evolution.yml"
        yaml_file.write_text(
            "- id: \"suggestion_20260501_1\"\n"
            "  applied: false\n",
            encoding="utf-8",
        )
        result = apply_suggestion(yaml_file, "suggestion_nonexistent")
        assert result is False
        content = yaml_file.read_text(encoding="utf-8")
        assert content.count("applied: true") == 0

    def test_apply_already_applied(self, tmp_path):
        yaml_file = tmp_path / "evolution.yml"
        yaml_file.write_text(
            "- id: \"suggestion_20260501_1\"\n"
            "  applied: true\n",
            encoding="utf-8",
        )
        # Even if already applied, should still "succeed" since replace matches
        result = apply_suggestion(yaml_file, "suggestion_20260501_1")
        assert result is True


class TestPersonaHelpers:
    def test_summarize_persona_full(self):
        config = {
            "name": "Anima",
            "identity": "A rational AI VTuber who observes humanity.",
            "personality": {
                "traits": ["理性", "冷静", "幽默"],
                "speaking_style": ["简洁", "精准", "逻辑严密"],
            },
            "behavior": {
                "forbidden_phrases": ["呀", "啦", "呢"],
            },
        }
        summary = _summarize_persona(config)
        assert "Anima" in summary
        assert "rational AI VTuber" in summary
        assert "理性" in summary
        assert "简洁" in summary
        assert "呀" in summary

    def test_summarize_persona_minimal(self):
        config = {"name": "Minimal"}
        summary = _summarize_persona(config)
        assert "Minimal" in summary

    def test_summarize_persona_empty(self):
        summary = _summarize_persona({})
        assert summary == ""

    def test_format_logs(self):
        logs = [
            {"content": "first conversation", "session_id": "abc12345", "created_at": "2026-05-01T10:00:00"},
            {"content": "second conversation", "session_id": "def67890", "created_at": "2026-05-02T11:00:00"},
        ]
        result = _format_logs(logs)
        assert "first conversation" in result
        assert "second conversation" in result
        assert "会话 1" in result
        assert "会话 2" in result

    def test_format_logs_truncates_to_20(self):
        logs = [{"content": f"log{i}", "session_id": f"s{i}"} for i in range(25)]
        result = _format_logs(logs)
        assert result.count("会话") == 20
        assert "log24" not in result

    def test_format_logs_empty(self):
        result = _format_logs([])
        assert result == ""

    def test_format_logs_missing_fields(self):
        logs = [{"content": "test content"}]
        result = _format_logs(logs)
        assert "test content" in result

    def test_clean_json_markdown_fence(self):
        result = _clean_json('```json\n{"key": "val"}\n```')
        assert result == '{"key": "val"}'

    def test_clean_json_generic_fence(self):
        result = _clean_json('```\n[1, 2]\n```')
        assert result == "[1, 2]"

    def test_clean_json_plain(self):
        result = _clean_json('  {"a": 1}  ')
        assert result == '{"a": 1}'


class TestPersonaOptimizerConstants:
    def test_system_prompt_not_empty(self):
        assert len(PERSONA_ANALYSIS_SYSTEM_PROMPT) > 50

    def test_user_prompt_has_placeholders(self):
        assert "{persona_summary}" in PERSONA_ANALYSIS_USER_PROMPT
        assert "{log_count}" in PERSONA_ANALYSIS_USER_PROMPT
        assert "{conversation_logs}" in PERSONA_ANALYSIS_USER_PROMPT
