"""Tests for MemeDiscoverer — candidate generation with LLM and template fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from animetta import $$$
from animetta import $$$


# ── Helpers ────────────────────────────────────────────────────


def _make_log(content: str = "test pattern", session_id: str = "s1") -> LearningLog:
    return LearningLog(
        id="id1",
        session_id=session_id,
        summary_type="pattern",
        content=content,
    )


def _make_llm_response(content: str) -> dict:
    return {"content": content}


# ── Tests ─────────────────────────────────────────────────────


class TestMemeCandidateDataClass:
    def test_default_values(self):
        c = MemeCandidate(text="hello", context_hint="when greeting")
        assert c.text == "hello"
        assert c.context_hint == "when greeting"
        assert c.confidence == 0.7
        assert c.source_pattern == ""
        assert c.tags == []

    def test_full_constructor(self):
        c = MemeCandidate(
            text="meme text",
            context_hint="in context X",
            confidence=0.9,
            source_pattern="original pattern",
            tags=["tag1", "tag2"],
        )
        assert c.text == "meme text"
        assert c.context_hint == "in context X"
        assert c.confidence == 0.9
        assert c.source_pattern == "original pattern"
        assert c.tags == ["tag1", "tag2"]


class TestMemeDiscovererInit:
    def test_init_with_llm(self):
        llm = MagicMock()
        md = MemeDiscoverer(llm_client=llm, config={"min_confidence": 0.5})
        assert md._llm is llm
        assert md._config == {"min_confidence": 0.5}

    def test_init_without_llm(self):
        md = MemeDiscoverer()
        assert md._llm is None
        assert md._config == {}


class TestMemeDiscovererLLM:
    async def test_discover_with_llm_success(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"text": "理性吐槽梗", "context_hint": "用户反复犯错时", "tags": ["rational-roast"]}]'
        ))
        md = MemeDiscoverer(llm_client=mock_llm)
        patterns = [_make_log("user keeps making same mistake")]

        candidates = await md.discover_candidates(patterns, max_candidates=3)

        assert len(candidates) == 1
        assert candidates[0].text == "理性吐槽梗"
        assert candidates[0].context_hint == "用户反复犯错时"
        assert "rational-roast" in candidates[0].tags

    async def test_discover_llm_with_confidence_field(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"text": "meme1", "context_hint": "ctx", "confidence": 0.85, "tags": ["t1"]}]'
        ))
        md = MemeDiscoverer(llm_client=mock_llm)
        patterns = [_make_log("test")]
        candidates = await md.discover_candidates(patterns)
        assert len(candidates) == 1
        assert candidates[0].confidence == 0.85

    async def test_discover_empty_patterns(self, mock_llm):
        md = MemeDiscoverer(llm_client=mock_llm)
        candidates = await md.discover_candidates([], max_candidates=3)
        assert candidates == []

    async def test_discover_llm_empty_result_falls_back(self, mock_llm):
        """When LLM returns empty JSON array, fall back to templates."""
        mock_llm.chat = AsyncMock(return_value=_make_llm_response("[]"))
        md = MemeDiscoverer(llm_client=mock_llm, config={"min_confidence": 0.0})
        patterns = [_make_log("test pattern")]
        candidates = await md.discover_candidates(patterns, max_candidates=2)
        assert len(candidates) > 0
        assert len(candidates) <= 2

    async def test_discover_llm_parse_failure_falls_back(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response("not valid json {{{"))
        md = MemeDiscoverer(llm_client=mock_llm, config={"min_confidence": 0.0})
        patterns = [_make_log("test")]
        candidates = await md.discover_candidates(patterns, max_candidates=1)
        assert len(candidates) >= 1

    async def test_discover_llm_exception_falls_back(self, mock_llm):
        mock_llm.chat = AsyncMock(side_effect=RuntimeError("LLM error"))
        md = MemeDiscoverer(llm_client=mock_llm, config={"min_confidence": 0.0})
        patterns = [_make_log("test")]
        candidates = await md.discover_candidates(patterns, max_candidates=2)
        assert len(candidates) > 0

    async def test_discover_llm_skips_empty_text(self, mock_llm):
        """When LLM returns items with empty text, _discover_with_llm returns [].
        The empty list is falsy, so discover_candidates falls back to templates."""
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"text": "", "context_hint": "ctx", "tags": []}]'
        ))
        md = MemeDiscoverer(llm_client=mock_llm, config={"min_confidence": 0.0})
        patterns = [_make_log("test")]
        candidates = await md.discover_candidates(patterns)
        # Falls back to templates because LLM result is empty after skipping blank text
        assert len(candidates) >= 1
        assert isinstance(candidates[0], MemeCandidate)


class TestMemeDiscovererFallback:
    def test_generate_fallback_no_llm(self):
        md = MemeDiscoverer()
        patterns = [_make_log("test pattern")]
        # Synchronous call — discover_candidates is async but fallback path is synchronous
        import asyncio
        candidates = asyncio.run(md.discover_candidates(patterns, max_candidates=3))
        assert len(candidates) <= 3
        assert all(isinstance(c, MemeCandidate) for c in candidates)

    def test_generate_fallback_respects_max(self):
        candidates = _generate_fallback_candidates(
            [_make_log("test")], max_candidates=2
        )
        assert len(candidates) == 2

    def test_generate_fallback_has_context_hints(self):
        candidates = _generate_fallback_candidates(
            [_make_log("test")], max_candidates=1
        )
        assert len(candidates) == 1
        assert candidates[0].context_hint != ""
        assert candidates[0].text != ""

    def test_generate_fallback_replaces_time_placeholder(self):
        """If a template has {time}, it should be replaced."""
        # Force selection of a template with {time}
        original_len = len(FALLBACK_TEMPLATES)
        with pytest.MonkeyPatch.context() as mp:
            import random as random_mod
            # We know FALLBACK_TEMPLATES[7] has {time}
            if original_len > 7:
                time_template = FALLBACK_TEMPLATES[7]
                if "{time}" in time_template["text"]:
                    # Just verify the function replaces {time}
                    candidates = _generate_fallback_candidates(
                        [_make_log("test")], max_candidates=original_len
                    )
                    texts_with_time = [c.text for c in candidates if "{time}" in c.text]
                    assert len(texts_with_time) == 0, (
                        f"Found unreplaced {{time}} in: {texts_with_time}"
                    )


class TestMemeDiscovererFiltering:
    def test_filter_by_confidence(self):
        md = MemeDiscoverer(config={"min_confidence": 0.6})
        candidates = [
            MemeCandidate(text="high", context_hint="ctx", confidence=0.8, tags=[]),
            MemeCandidate(text="low", context_hint="ctx", confidence=0.3, tags=[]),
        ]
        filtered = md._filter_candidates(candidates)
        assert len(filtered) == 1
        assert filtered[0].text == "high"

    def test_filter_by_tag_whitelist(self):
        md = MemeDiscoverer(config={"tag_whitelist": ["tech-reference"]})
        candidates = [
            MemeCandidate(text="a", context_hint="ctx", tags=["tech-reference"]),
            MemeCandidate(text="b", context_hint="ctx", tags=["other"]),
        ]
        filtered = md._filter_candidates(candidates)
        assert len(filtered) == 1
        assert filtered[0].text == "a"

    def test_filter_default_config(self):
        md = MemeDiscoverer()
        candidates = [
            MemeCandidate(text="a", context_hint="ctx", confidence=0.2, tags=[]),
        ]
        # Default min_confidence is 0.4, so 0.2 should be filtered out
        filtered = md._filter_candidates(candidates)
        assert len(filtered) == 0


class TestMemeHelpers:
    def test_clean_json_markdown_fence(self):
        result = _clean_json('```json\n[{"a": 1}]\n```')
        assert result == '[{"a": 1}]'

    def test_clean_json_generic_fence(self):
        result = _clean_json('```\n{"key": "val"}\n```')
        assert result == '{"key": "val"}'

    def test_clean_json_plain(self):
        result = _clean_json('  [1, 2]  ')
        assert result == "[1, 2]"

    def test_format_patterns(self):
        logs = [
            _make_log("pattern content one", "s1"),
            _make_log("pattern content two", "s1"),
        ]
        result = _format_patterns(logs)
        assert "pattern content one" in result
        assert "pattern content two" in result

    def test_format_patterns_empty(self):
        result = _format_patterns([])
        assert result == ""

    def test_parse_llm_result_list(self):
        result = _parse_llm_result('[{"text": "meme1"}, {"text": "meme2"}]')
        assert len(result) == 2
        assert result[0]["text"] == "meme1"

    def test_parse_llm_result_dict_with_keys(self):
        result = _parse_llm_result('{"memes": [{"text": "meme1"}]}')
        assert len(result) == 1
        assert result[0]["text"] == "meme1"

    def test_parse_llm_result_dict_with_candidates(self):
        result = _parse_llm_result('{"candidates": [{"text": "c1"}]}')
        assert len(result) == 1
        assert result[0]["text"] == "c1"

    def test_parse_llm_result_invalid(self):
        result = _parse_llm_result("not json at all")
        assert result == []


class TestMemeDiscovererConstants:
    def test_meme_system_prompt_not_empty(self):
        assert len(MEME_SYSTEM_PROMPT) > 50

    def test_meme_user_prompt_has_placeholders(self):
        assert "{max_candidates}" in MEME_USER_PROMPT
        assert "{patterns_text}" in MEME_USER_PROMPT

    def test_fallback_templates_not_empty(self):
        assert len(FALLBACK_TEMPLATES) > 0

    def test_fallback_templates_have_required_fields(self):
        for tpl in FALLBACK_TEMPLATES:
            assert "text" in tpl
            assert "context_hint" in tpl
            assert "tags" in tpl
            assert len(tpl["text"]) > 0
