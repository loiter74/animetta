"""Tests for Bilibili Meme Intelligence subsystem.

Covers:
- CognitiveAnalysis model serialization/deserialization
- Meme model with new fields
- MemePool semantic matching upgrade
- MemeCognitiveAnalyzer JSON parsing and validation
- BilibiliMemeCollector with mock API responses
- BilibiliInteractionLearner with mock danmaku data
"""

import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from animetta.memory.meme.models import (
    CognitiveAnalysis,
    Meme,
    MemeSource,
)
from animetta.memory.meme.engine import MemePool


# ═══════════════════════════════════════════════════════════════════
# CognitiveAnalysis model tests
# ═══════════════════════════════════════════════════════════════════


class TestCognitiveAnalysis:
    def test_default_values(self):
        ca = CognitiveAnalysis()
        assert ca.humor_mechanism == ""
        assert ca.persona_fit_score == 0.5
        assert ca.source_url == ""

    def test_full_construction(self):
        ca = CognitiveAnalysis(
            humor_mechanism="双关",
            context_trigger="用户提到相关话题时",
            emotional_tone="幽默",
            persona_fit_score=0.8,
            usage_example="这就是传说中的双关梗吧",
            source_url="https://www.bilibili.com/video/BV12345",
        )
        assert ca.humor_mechanism == "双关"
        assert ca.persona_fit_score == 0.8

    def test_to_dict(self):
        ca = CognitiveAnalysis(
            humor_mechanism="反讽",
            context_trigger="吐槽时",
            emotional_tone="讽刺",
            persona_fit_score=0.7,
            usage_example="这个操作很专业呢（反讽）",
            source_url="https://example.com",
        )
        d = ca.to_dict()
        assert d["humor_mechanism"] == "反讽"
        assert d["persona_fit_score"] == 0.7
        assert d["usage_example"] == "这个操作很专业呢（反讽）"

    def test_from_dict_with_data(self):
        data = {
            "humor_mechanism": "荒诞",
            "context_trigger": "听到离谱言论时",
            "emotional_tone": "荒诞",
            "persona_fit_score": 0.6,
            "usage_example": "这个逻辑比我的算法还离谱",
            "source_url": "https://bilibili.com/video/xxx",
        }
        ca = CognitiveAnalysis.from_dict(data)
        assert ca is not None
        assert ca.humor_mechanism == "荒诞"
        assert ca.persona_fit_score == 0.6

    def test_from_dict_with_none(self):
        ca = CognitiveAnalysis.from_dict(None)
        assert ca is None

    def test_from_dict_with_empty(self):
        ca = CognitiveAnalysis.from_dict({})
        assert ca is not None
        assert ca.humor_mechanism == ""


# ═══════════════════════════════════════════════════════════════════
# Meme model with new fields tests
# ═══════════════════════════════════════════════════════════════════


class TestMemeExtended:
    def test_default_source_platform(self):
        meme = Meme(text="test meme")
        assert meme.source_platform == "internal"

    def test_source_platform_bilibili(self):
        meme = Meme(text="b站梗", source_platform="bilibili")
        assert meme.source_platform == "bilibili"

    def test_cognitive_analysis_none_by_default(self):
        meme = Meme(text="test")
        assert meme.cognitive_analysis is None

    def test_cognitive_analysis_set(self):
        ca = CognitiveAnalysis(humor_mechanism="双关", persona_fit_score=0.8)
        meme = Meme(text="test", cognitive_analysis=ca)
        assert meme.cognitive_analysis is not None
        assert meme.cognitive_analysis.humor_mechanism == "双关"

    def test_to_dict_includes_source_platform(self):
        meme = Meme(text="test", source_platform="bilibili")
        d = meme.to_dict()
        assert d["source_platform"] == "bilibili"

    def test_to_dict_includes_cognitive_analysis(self):
        ca = CognitiveAnalysis(
            humor_mechanism="自指",
            persona_fit_score=0.9,
            usage_example="作为AI，我觉得这个梗很适合我",
        )
        meme = Meme(text="AI自指梗", cognitive_analysis=ca, source_platform="bilibili")
        d = meme.to_dict()
        assert "cognitive_analysis" in d
        assert d["cognitive_analysis"]["humor_mechanism"] == "自指"

    def test_to_dict_omits_cognitive_analysis_when_none(self):
        meme = Meme(text="test")
        d = meme.to_dict()
        assert "cognitive_analysis" not in d


# ═══════════════════════════════════════════════════════════════════
# MemePool semantic matching tests
# ═══════════════════════════════════════════════════════════════════


class FakeMemeStore:
    """In-memory store for testing MemePool."""

    def __init__(self):
        self._memes: dict = {}
        self._active: set = set()
        self._discarded: set = set()

    def list_active(self):
        return [m for mid, m in self._memes.items() if mid in self._active]

    def list_discarded(self):
        return [m for mid, m in self._memes.items() if mid in self._discarded]

    def save(self, meme):
        self._memes[meme.id] = meme
        self._active.add(meme.id)
        return meme.id

    def insert(self, meme):
        return self.save(meme)

    def update(self, meme):
        self._memes[meme.id] = meme

    def discard(self, meme_id):
        self._active.discard(meme_id)
        self._discarded.add(meme_id)

    def resurrect(self, meme_id):
        self._discarded.discard(meme_id)
        self._active.add(meme_id)

    def set_active(self, meme_id, active):
        if active:
            self._discarded.discard(meme_id)
            self._active.add(meme_id)
        else:
            self._active.discard(meme_id)
            self._discarded.add(meme_id)


class TestMemePoolMatching:
    def setup_method(self):
        self.store = FakeMemeStore()
        self.pool = MemePool(store=self.store, config={"max_active": 10})

    def test_text_overlap_substring_match(self):
        assert self.pool._text_overlap("今天天气真好", "天气")
        assert self.pool._text_overlap("bug", "这个bug好烦")

    def test_text_overlap_no_match(self):
        assert not self.pool._text_overlap("今天天气真好", "xyzabc完全不相关的词")
        assert not self.pool._text_overlap("", "")

    def test_text_overlap_case_insensitive(self):
        assert self.pool._text_overlap("Hello World", "hello")
        assert self.pool._text_overlap("BUG", "bug")

    def test_text_overlap_word_partial(self):
        # 25% word overlap threshold: 4 words in shorter, need 1 match
        assert self.pool._text_overlap("a b c d", "a b e f g")  # 2/4 = 50%
        assert not self.pool._text_overlap("a b c d e f g h", "x y z")  # 0 overlap

    def test_context_match_with_hint(self):
        meme = Meme(
            text="经典bug梗",
            context_hint="用户提到bug时使用",
        )
        # "bug" is a substring of the search text
        assert self.pool._context_match("bug", meme)

    def test_context_match_with_cognitive_trigger(self):
        ca = CognitiveAnalysis(context_trigger="用户抱怨时使用")
        meme = Meme(
            text="吐槽专用梗",
            context_hint="吐槽场景",
            cognitive_analysis=ca,
        )
        # "吐槽" is a substring of the combined search text
        assert self.pool._context_match("吐槽", meme)

    def test_context_match_no_match(self):
        meme = Meme(text="美食分享梗", context_hint="用户分享好吃的食物时")
        assert not self.pool._context_match("帮我写一个排序算法并解释时间复杂度", meme)

    def test_select_for_context_filters_by_source_platform(self):
        bilibili_meme = Meme(
            text="b站热门梗", context_hint="用户聊天时",
            source_platform="bilibili",
        )
        internal_meme = Meme(
            text="内部梗", context_hint="用户聊天时",
            source_platform="internal",
        )
        self.store.save(bilibili_meme)
        self.store.save(internal_meme)

        result = self.pool.select_for_context(
            "用户聊天时", source_platform="bilibili",
        )
        assert result is not None
        assert result.source_platform == "bilibili"

    def test_select_for_context_filters_by_persona_fit(self):
        ca_low = CognitiveAnalysis(persona_fit_score=0.3)
        ca_high = CognitiveAnalysis(persona_fit_score=0.8)

        low_fit = Meme(
            text="低匹配梗", context_hint="测试场景",
            cognitive_analysis=ca_low,
        )
        high_fit = Meme(
            text="高匹配梗", context_hint="测试场景",
            cognitive_analysis=ca_high,
        )
        self.store.save(low_fit)
        self.store.save(high_fit)

        result = self.pool.select_for_context("测试场景")
        assert result is not None
        assert result.text == "高匹配梗"

    def test_select_for_context_returns_none_when_no_match(self):
        meme = Meme(text="美食分享", context_hint="用户分享好吃的东西时")
        self.store.save(meme)
        result = self.pool.select_for_context("请帮我写一个Python脚本处理CSV数据")
        assert result is None

    def test_select_for_context_streaming_mode(self):
        ca = CognitiveAnalysis(persona_fit_score=0.8)
        meme = Meme(
            text="直播梗", cognitive_analysis=ca,
            context_hint="任何场景",
        )
        self.store.save(meme)
        result = self.pool.select_for_context(
            "弹幕消息", personality_mode="streaming",
        )
        assert result is not None


# ═══════════════════════════════════════════════════════════════════
# MemeCognitiveAnalyzer tests
# ═══════════════════════════════════════════════════════════════════


class TestMemeCognitiveAnalyzer:
    @pytest.fixture
    def analyzer(self):
        from animetta.services.meme.analyzer import MemeCognitiveAnalyzer
        return MemeCognitiveAnalyzer(llm_client=None, meme_pool=None)

    def test_parse_json_valid(self, analyzer):
        result = analyzer._parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_with_markdown_fence(self, analyzer):
        result = analyzer._parse_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_invalid(self, analyzer):
        result = analyzer._parse_json("not json")
        assert result == {}

    def test_validate_analysis_valid(self, analyzer):
        data = {
            "humor_mechanism": "双关",
            "context_trigger": "场景",
            "emotional_tone": "幽默",
            "persona_fit_score": 0.7,
            "usage_example": "示例",
        }
        assert analyzer._validate_analysis(data) is True

    def test_validate_analysis_missing_field(self, analyzer):
        data = {
            "humor_mechanism": "双关",
            # missing context_trigger
            "emotional_tone": "幽默",
            "persona_fit_score": 0.7,
            "usage_example": "示例",
        }
        assert analyzer._validate_analysis(data) is False

    def test_validate_analysis_invalid_score(self, analyzer):
        data = {
            "humor_mechanism": "双关",
            "context_trigger": "场景",
            "emotional_tone": "幽默",
            "persona_fit_score": 1.5,  # out of range
            "usage_example": "示例",
        }
        assert analyzer._validate_analysis(data) is False

    def test_basic_analysis_fallback(self, analyzer):
        result = analyzer._basic_analysis("测试梗", "测试场景")
        assert result.humor_mechanism == ""
        assert result.context_trigger == "测试场景"
        assert result.persona_fit_score == 0.5

    def test_analyze_without_llm_returns_basic(self, analyzer):
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            analyzer.analyze("测试梗", "测试场景"),
        )
        assert result is not None
        assert result.persona_fit_score == 0.5


# ═══════════════════════════════════════════════════════════════════
# BilibiliMemeCollector tests
# ═══════════════════════════════════════════════════════════════════


class TestBilibiliMemeCollector:
    @pytest.fixture
    def collector(self):
        from animetta.services.meme.bilibili_collector import BilibiliMemeCollector
        return BilibiliMemeCollector(llm_client=None, config={"max_videos": 5})

    def test_parse_tags(self, collector):
        assert collector._parse_tags("") == []
        assert collector._parse_tags("搞笑, 吐槽") == ["搞笑", "吐槽"]
        assert collector._parse_tags("单标签") == ["单标签"]

    def test_parse_llm_json_array(self, collector):
        result = collector._parse_llm_json('[{"text": "test", "context_hint": "hint"}]')
        assert len(result) == 1
        assert result[0]["text"] == "test"

    def test_parse_llm_json_dict_wrapped(self, collector):
        result = collector._parse_llm_json(
            '{"candidates": [{"text": "meme1"}, {"text": "meme2"}]}'
        )
        assert len(result) == 2

    def test_parse_llm_json_markdown_fence(self, collector):
        result = collector._parse_llm_json(
            '```json\n[{"text": "test"}]\n```'
        )
        assert len(result) == 1

    def test_parse_llm_json_invalid(self, collector):
        result = collector._parse_llm_json("not json at all")
        assert result == []

    def test_build_candidates(self, collector):
        from animetta.services.meme.bilibili_collector import CollectedVideo

        parsed = [
            {"text": "梗A", "context_hint": "场景A", "frequency": 3, "tags": ["幽默"]},
            {"text": "梗B", "context_hint": "场景B", "frequency": 1, "tags": ["吐槽"]},
        ]
        videos = [CollectedVideo(bvid="BV123", title="test", tags=["测试"])]

        result = collector._build_candidates(parsed, videos)
        assert len(result) == 2
        assert result[0].text == "梗A"
        assert result[0].tags == ["幽默"]
        assert result[0].source_videos == ["BV123"]

    def test_heuristic_identify(self, collector):
        from animetta.services.meme.bilibili_collector import CollectedVideo

        videos = [
            CollectedVideo(bvid="BV1", title="视频1", tags=["鬼畜", "搞笑"]),
            CollectedVideo(bvid="BV2", title="视频2", tags=["鬼畜", "翻唱"]),
            CollectedVideo(bvid="BV3", title="视频3", tags=["搞笑"]),
        ]
        comments = {}

        result = collector._heuristic_identify(videos, comments)
        # "鬼畜" appears in 2 videos, "搞笑" appears in 2
        assert len(result) >= 2


# ═══════════════════════════════════════════════════════════════════
# BilibiliInteractionLearner tests
# ═══════════════════════════════════════════════════════════════════


class TestBilibiliInteractionLearner:
    @pytest.fixture
    def learner(self):
        from animetta.services.meme.bilibili_interaction import BilibiliInteractionLearner
        return BilibiliInteractionLearner(
            llm_client=None,
            wiki_manager=None,
            config={"room_ids": [], "min_samples_per_room": 100},
        )

    def test_parse_json_valid(self, learner):
        result = learner._parse_json('{"patterns": [], "strategies": []}')
        assert result == {"patterns": [], "strategies": []}

    def test_parse_json_invalid(self, learner):
        result = learner._parse_json("not json")
        assert result == {}

    def test_empty_room_ids_skips(self, learner):
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            learner.learn_patterns(),
        )
        assert result == []

    def test_interaction_pattern_model(self):
        from animetta.services.meme.bilibili_interaction import InteractionPattern, LivestreamStrategy

        pattern = InteractionPattern(
            name="高频互动",
            description="主播对弹幕快速回应",
            applicable_scenarios=["直播高潮期"],
            confidence=0.8,
        )
        d = pattern.to_dict()
        assert d["name"] == "高频互动"
        assert d["confidence"] == 0.8

        strategy = LivestreamStrategy(
            trigger_condition="弹幕数量激增时",
            suggested_behavior="选择高赞弹幕快速回复",
            expected_effect="提高观众参与感",
            priority="high",
        )
        d2 = strategy.to_dict()
        assert d2["priority"] == "high"
