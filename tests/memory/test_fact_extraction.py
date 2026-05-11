"""Unit tests: fact extraction adapter + persona optimizer."""

import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime, timezone


class TestFormatFactsForWiki:
    def test_empty_facts_returns_empty(self):
        from src.anima.memory.learner.fact_extractor import format_facts_for_wiki
        result = format_facts_for_wiki([], "test-session")
        assert result == ""

    def test_single_fact_formatted(self):
        from src.anima.memory.learner.fact_extractor import format_facts_for_wiki
        facts = [{
            "id": "fact-1",
            "fact": "User likes TypeScript",
            "category": "preference",
            "confidence": 0.9,
            "is_static": True,
            "source": "auto-extraction",
            "source_turn_id": "turn-1",
            "source_timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        result = format_facts_for_wiki(facts, "test-session")
        assert "User likes TypeScript" in result
        assert "preference" in result.lower() or "偏好" in result
        assert "test-session" in result
        assert "0.9" in result or "90%" in result

    def test_multiple_facts_grouped_by_category(self):
        from src.anima.memory.learner.fact_extractor import format_facts_for_wiki
        facts = [
            {"id": "1", "fact": "Likes Python", "category": "preference", "confidence": 0.8, "is_static": True, "source": "auto", "source_turn_id": "t1", "source_timestamp": datetime.now(timezone.utc).isoformat()},
            {"id": "2", "fact": "Works at ACME", "category": "identity", "confidence": 0.9, "is_static": True, "source": "auto", "source_turn_id": "t2", "source_timestamp": datetime.now(timezone.utc).isoformat()},
            {"id": "3", "fact": "Prefers dark mode", "category": "preference", "confidence": 0.7, "is_static": True, "source": "auto", "source_turn_id": "t3", "source_timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        result = format_facts_for_wiki(facts, "test-session")
        assert "Likes Python" in result
        assert "Works at ACME" in result
        assert "Prefers dark mode" in result
        # Should appear exactly once each
        assert result.count("Likes Python") == 1


class TestPersonaOptimizer:
    def test_summarize_persona_basic(self):
        from src.anima.memory.learner.persona_optimizer import _summarize_persona
        config = {
            "name": "TestBot",
            "identity": "A test bot for testing things.",
            "personality": {
                "traits": ["helpful", "concise"],
                "speaking_style": ["short sentences"],
            },
        }
        result = _summarize_persona(config)
        assert "TestBot" in result
        assert "helpful" in result

    def test_format_suggestions_yaml(self):
        from src.anima.memory.learner.persona_optimizer import format_suggestions_yaml
        analysis = {
            "summary": "All good",
            "strengths": [{"pattern": "Good at explaining", "evidence": "3 sessions", "confidence": 0.8}],
            "weaknesses": [],
            "suggestions": [{
                "target_field": "personality.traits",
                "action": "add",
                "current_value": "",
                "suggested_value": "Be more patient with new users",
                "rationale": "Users frequently ask for clarification",
                "confidence": 0.75,
            }],
        }
        result = format_suggestions_yaml(analysis, "TestBot")
        assert "# Persona Evolution Suggestions" in result
        assert "TestBot" in result
        assert "Be more patient" in result
        assert "applied: false" in result

    def test_suggestions_yaml_respects_auto_apply_flag(self):
        from src.anima.memory.learner.persona_optimizer import format_suggestions_yaml
        analysis = {"suggestions": [], "summary": "Nothing to suggest"}
        result = format_suggestions_yaml(analysis, "TestBot")
        assert "# Status: review" in result
        assert "Auto-apply: false" in result


class TestCleanJson:
    def test_removes_markdown_fence(self):
        from src.anima.memory.learner.persona_optimizer import _clean_json
        assert _clean_json("```json\n{}\n```") == "{}"

    def test_passes_through_clean_json(self):
        from src.anima.memory.learner.persona_optimizer import _clean_json
        assert _clean_json('{"key": "value"}') == '{"key": "value"}'
