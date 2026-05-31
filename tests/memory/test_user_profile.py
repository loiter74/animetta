"""Tests for UserProfile model and builder."""

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestUserProfile:
    """UserProfile dataclass behavior."""

    def test_is_empty_when_no_data(self):
        p = UserProfile()
        assert p.is_empty() is True

    def test_is_empty_when_has_static(self):
        p = UserProfile(static=["likes Python"])
        assert p.is_empty() is False

    def test_is_empty_when_has_dynamic(self):
        p = UserProfile(dynamic=["debugging issue #42"])
        assert p.is_empty() is False

    def test_format_for_prompt_empty(self):
        p = UserProfile()
        assert p.format_for_prompt() == ""

    def test_format_for_prompt_with_static(self):
        p = UserProfile(static=["likes Python", "uses Vim"])
        result = p.format_for_prompt()
        assert "likes Python" in result
        assert "uses Vim" in result
        assert "current" in result or "动态" in result or "画像" in result

    def test_format_for_prompt_with_dynamic(self):
        p = UserProfile(dynamic=["debugging rate limits"])
        result = p.format_for_prompt()
        assert "debugging rate limits" in result


class TestUserProfileBuilder:
    """UserProfileBuilder build logic."""

    def test_build_empty_when_no_sources(self):

        builder = UserProfileBuilder(
            wiki_manager=None,
        )
        profile = builder.build(session_id="test")
        assert profile.is_empty() is True

    def test_build_with_short_term_memory(self):

        mock_stm = MagicMock()
        mock_stm.get_recent = MagicMock(return_value=[
            MagicMock(user_input="I love TypeScript", agent_response="That's great!"),
            MagicMock(user_input="My name is Alice", agent_response="Nice to meet you!"),
        ])

        builder = UserProfileBuilder(
            short_term=mock_stm,
            wiki_manager=None,
        )
        profile = builder.build(session_id="test")
        assert isinstance(profile, UserProfile)
