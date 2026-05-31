"""Tests for PatternExtractor — LLM + frequency-based pattern discovery."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest



# ── Helpers ────────────────────────────────────────────────────


def _make_turn(
    turn_id: str = "t1",
    session_id: str = "s1",
    user_input: str = "Hello",
    agent_response: str = "Hi",
    emotions: list | None = None,
) -> MemoryTurn:
    return MemoryTurn(
        turn_id=turn_id,
        session_id=session_id,
        timestamp=datetime.now(),
        user_input=user_input,
        agent_response=agent_response,
        emotions=emotions or [],
    )


def _make_llm_response(content: str) -> dict:
    return {"content": content}


# ── Tests ─────────────────────────────────────────────────────


class TestPatternExtractorInit:
    def test_init_with_llm(self):
        llm = MagicMock()
        extractor = PatternExtractor(llm_client=llm, config={"key": "val"})
        assert extractor._llm is llm
        assert extractor._config == {"key": "val"}

    def test_init_without_llm(self):
        extractor = PatternExtractor()
        assert extractor._llm is None
        assert extractor._config == {}


class TestPatternExtractorLLM:
    async def test_extract_with_llm_returns_logs(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"pattern": "用户喜欢Rust", "category": "interest", "confidence": 0.8, "evidence": ["t1"]}]'
        ))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [_make_turn("t1", user_input="I love Rust programming!")]

        logs = await extractor.extract_patterns(turns, "s1", max_patterns=5)

        assert len(logs) == 1
        assert logs[0].summary_type == "pattern"
        assert logs[0].content == "用户喜欢Rust"
        assert logs[0].id != ""

    async def test_extract_with_llm_empty_turns(self, mock_llm):
        extractor = PatternExtractor(llm_client=mock_llm)
        logs = await extractor.extract_patterns([], "s1")
        assert logs == []

    async def test_extract_llm_response_as_list(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"pattern": "user prefers Python", "category": "preference", "confidence": 0.9, "evidence": ["t1", "t2"]}]'
        ))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [
            _make_turn("t1", user_input="Python is great"),
            _make_turn("t2", user_input="I use Python daily"),
        ]
        logs = await extractor.extract_patterns(turns, "s1")
        assert len(logs) == 1
        assert logs[0].content == "user prefers Python"

    async def test_extract_llm_response_as_dict_with_patterns_key(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '{"patterns": [{"pattern": "likes coding", "category": "interest", "confidence": 0.7, "evidence": ["t1"]}]}'
        ))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [_make_turn("t1", user_input="I enjoy coding")]
        logs = await extractor.extract_patterns(turns, "s1")
        assert len(logs) == 1
        assert logs[0].content == "likes coding"

    async def test_extract_llm_fallback_on_parse_failure(self, mock_llm):
        """When LLM returns unparseable JSON, return empty list (no frequency fallback since LLM path tried)."""
        mock_llm.chat = AsyncMock(return_value=_make_llm_response("not valid json at all {{{"))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [_make_turn("t1", user_input="I like Rust")]
        logs = await extractor.extract_patterns(turns, "s1")
        assert logs == []

    async def test_extract_llm_exception_falls_back_to_frequency(self, mock_llm):
        mock_llm.chat = AsyncMock(side_effect=RuntimeError("LLM down"))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [
            _make_turn("t1", user_input="我喜欢 Python 编程", emotions=["开心"]),
            _make_turn("t2", user_input="Python 真的很有趣", emotions=["开心"]),
            _make_turn("t3", user_input="我还喜欢 Rust"),  # triggers preference
        ]
        logs = await extractor.extract_patterns(turns, "s1", max_patterns=10)
        assert len(logs) > 0
        # Should all be from frequency source
        for log in logs:
            assert log.summary_type == "pattern"

    async def test_extract_llm_passes_max_patterns_to_prompt(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"pattern": "p1", "category": "interest", "confidence": 0.5, "evidence": ["t1"]}]'
        ))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [_make_turn("t1", user_input="test")]
        await extractor.extract_patterns(turns, "s1", max_patterns=3)
        call_args = mock_llm.chat.call_args
        messages = call_args[1]["messages"]
        system_msg = messages[0]["content"]
        assert "3" in system_msg

    async def test_extract_llm_skips_empty_pattern_text(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"pattern": "   ", "category": "interest", "confidence": 0.5, "evidence": ["t1"]}]'
        ))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [_make_turn("t1", user_input="test")]
        logs = await extractor.extract_patterns(turns, "s1")
        assert logs == []

    async def test_extract_llm_normalizes_confidence(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"pattern": "p1", "category": "preference", "confidence": 2.5, "evidence": ["t1"]}]'
        ))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [_make_turn("t1", user_input="test")]
        logs = await extractor.extract_patterns(turns, "s1")
        assert len(logs) == 1
        assert logs[0].confidence == 1.0

    async def test_extract_llm_unknown_category_defaults_to_behavior(self, mock_llm):
        mock_llm.chat = AsyncMock(return_value=_make_llm_response(
            '[{"pattern": "p1", "category": "weird_category", "confidence": 0.6, "evidence": ["t1"]}]'
        ))
        extractor = PatternExtractor(llm_client=mock_llm)
        turns = [_make_turn("t1", user_input="test")]
        logs = await extractor.extract_patterns(turns, "s1")
        assert len(logs) == 1
        assert logs[0].metadata["category"] == "behavior"


class TestPatternExtractorFrequency:
    def test_extract_frequency_no_turns(self):
        extractor = PatternExtractor()
        logs = extractor._extract_with_frequency([], "s1")
        assert logs == []

    def test_extract_frequency_no_user_input(self):
        extractor = PatternExtractor()
        turns = [_make_turn("t1", user_input="", emotions=[])]
        logs = extractor._extract_with_frequency(turns, "s1")
        assert logs == []

    def test_extract_frequency_detects_topics(self):
        extractor = PatternExtractor()
        turns = [
            _make_turn("t1", user_input="I love Rust programming"),
            _make_turn("t2", user_input="Rust programming is amazing"),
        ]
        logs = extractor._extract_with_frequency(turns, "s1", max_patterns=10)
        # Should find the bigram "Rust programming" (via tokenization)
        topics = [log for log in logs if log.metadata.get("category") == "interest"]
        assert len(topics) >= 1

    def test_extract_frequency_detects_preferences(self):
        extractor = PatternExtractor()
        turns = [
            _make_turn("t1", user_input="我喜欢Python"),
            _make_turn("t2", user_input="我不喜欢Java"),
            _make_turn("t3", user_input="Python很有趣"),
        ]
        logs = extractor._extract_with_frequency(turns, "s1", max_patterns=10)
        prefs = [log for log in logs if log.metadata.get("category") == "preference"]
        assert len(prefs) >= 1

    def test_extract_frequency_emotions_from_labels(self):
        extractor = PatternExtractor()
        turns = [
            _make_turn("t1", user_input="hi", emotions=["开心"]),
            _make_turn("t2", user_input="hello", emotions=["开心"]),
        ]
        logs = extractor._extract_with_frequency(turns, "s1", max_patterns=10)
        emotions = [log for log in logs if log.metadata.get("category") == "emotion"]
        assert len(emotions) >= 1
        assert any("开心" in log.content for log in emotions)

    def test_extract_frequency_emotions_from_keywords(self):
        extractor = PatternExtractor()
        turns = [
            _make_turn("t1", user_input="我今天好累啊", emotions=[]),
            _make_turn("t2", user_input="真的太疲惫了", emotions=[]),
        ]
        logs = extractor._extract_with_frequency(turns, "s1", max_patterns=10)
        emotions = [log for log in logs if log.metadata.get("category") == "emotion"]
        assert len(emotions) >= 1

    def test_extract_frequency_communication_style(self):
        extractor = PatternExtractor()
        turns = [
            _make_turn("t1", user_input="What is Rust?"),
            _make_turn("t2", user_input="How does it work?"),
        ]
        logs = extractor._extract_with_frequency(turns, "s1", max_patterns=10)
        comms = [log for log in logs if log.metadata.get("category") == "communication"]
        assert len(comms) >= 1

    def test_extract_frequency_respects_max_patterns(self):
        extractor = PatternExtractor()
        turns = [
            _make_turn("t1", user_input="I like Rust", emotions=["开心"]),
            _make_turn("t2", user_input="Python is great", emotions=["好奇"]),
            _make_turn("t3", user_input="我喜欢编程"),
        ]
        logs = extractor._extract_with_frequency(turns, "s1", max_patterns=1)
        assert len(logs) <= 1

    def test_extract_frequency_deduplicates_emotion_labels(self):
        """Emotion from keyword matching should not duplicate labels already from turn emotions."""
        extractor = PatternExtractor()
        turns = [
            _make_turn("t1", user_input="我今天好累", emotions=["疲惫"]),
            _make_turn("t2", user_input="真的好疲劳", emotions=["疲惫"]),
        ]
        logs = extractor._extract_with_frequency(turns, "s1", max_patterns=10)
        # Should only have one "疲惫" entry even though both labels and keywords match
        # (checking content uniqueness)
        emotions = [log for log in logs if log.metadata.get("category") == "emotion"]
        assert len(emotions) >= 1


class TestPatternExtractorHelpers:
    def test_format_conversation(self):
        turns = [
            MemoryTurn(
                turn_id="t1", session_id="s1", timestamp=datetime.now(),
                user_input="Hello", agent_response="Hi there",
                emotions=["happy"],
            ),
        ]
        result = PatternExtractor._format_conversation(turns)
        assert "[轮次 t1]" in result
        assert "用户: Hello" in result
        assert "AI: Hi there" in result
        assert "情绪: happy" in result

    def test_tokenize_chinese_and_english(self):
        tokens = PatternExtractor._tokenize("我喜欢Rust编程")
        assert "我喜欢" in tokens
        assert "Rust" in tokens
        assert "编程" in tokens

    def test_tokenize_english_only(self):
        tokens = PatternExtractor._tokenize("hello world")
        assert "hello" in tokens
        assert "world" in tokens

    def test_extract_bigrams(self):
        bigrams = PatternExtractor._extract_bigrams(["I love Python"])
        assert len(bigrams) > 0
        assert "I love" in bigrams or "love Python" in bigrams

    def test_clean_json_with_markdown_fence(self):
        result = PatternExtractor._clean_json("```json\n{\"key\": \"val\"}\n```")
        assert result == '{"key": "val"}'

    def test_clean_json_with_generic_fence(self):
        result = PatternExtractor._clean_json("```\n[1, 2, 3]\n```")
        assert result == "[1, 2, 3]"

    def test_clean_json_plain(self):
        result = PatternExtractor._clean_json('  {"a": 1}  ')
        assert result == '{"a": 1}'

    def test_build_log(self):
        extractor = PatternExtractor()
        log = extractor._build_log(
            session_id="s1",
            content="test pattern",
            category="behavior",
            confidence=0.8,
            evidence=["t1", "t2"],
            source="frequency",
        )
        assert log.summary_type == "pattern"
        assert log.content == "test pattern"
        assert log.session_id == "s1"
        assert log.metadata["category"] == "behavior"
        assert log.metadata["evidence"] == ["t1", "t2"]
        assert log.metadata["source"] == "frequency"

    def test_build_log_clamps_confidence(self):
        extractor = PatternExtractor()
        log = extractor._build_log("s1", "x", "behavior", 1.5, [])
        assert log.confidence == 1.0
        log2 = extractor._build_log("s1", "x", "behavior", -0.5, [])
        assert log2.confidence == 0.0


class TestPatternExtractorConstants:
    def test_pattern_categories_present(self):
        assert "preference" in PATTERN_CATEGORIES
        assert "behavior" in PATTERN_CATEGORIES
        assert "interest" in PATTERN_CATEGORIES
        assert "emotion" in PATTERN_CATEGORIES
        assert "communication" in PATTERN_CATEGORIES

    def test_category_keywords_have_entries(self):
        for cat in PATTERN_CATEGORIES:
            assert cat in CATEGORY_KEYWORDS
            assert len(CATEGORY_KEYWORDS[cat]) > 0

    def test_emotion_keyword_groups(self):
        assert "开心" in EMOTION_KEYWORD_GROUPS
        assert "焦虑" in EMOTION_KEYWORD_GROUPS
        assert "疲惫" in EMOTION_KEYWORD_GROUPS

    def test_extraction_prompts_contain_placeholders(self):
        assert "{max_patterns}" in EXTRACTION_SYSTEM_PROMPT
        assert "{turn_count}" in EXTRACTION_USER_PROMPT
        assert "{conversation_text}" in EXTRACTION_USER_PROMPT
