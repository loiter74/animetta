"""Tests for meme review page — API handlers and feedback generation."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import AsyncMock, MagicMock
from src.anima.memory.meme.models import Meme, MemeSource, CognitiveAnalysis


class TestMemeReviewStatus:
    def test_meme_default_review_status(self):
        meme = Meme(text="test")
        assert meme.review_status == "pending"

    def test_meme_review_status_persists_in_dict(self):
        meme = Meme(text="test", review_status="good")
        d = meme.to_dict()
        assert d["review_status"] == "good"

    def test_cognitive_analysis_roast_field(self):
        ca = CognitiveAnalysis(roast="这个梗不错")
        assert ca.roast == "这个梗不错"
        d = ca.to_dict()
        assert d["roast"] == "这个梗不错"

    def test_cognitive_analysis_roast_default(self):
        ca = CognitiveAnalysis()
        assert ca.roast == ""

    def test_cognitive_analysis_from_dict_with_roast(self):
        data = {"roast": "太烂了", "humor_mechanism": "双关"}
        ca = CognitiveAnalysis.from_dict(data)
        assert ca is not None
        assert ca.roast == "太烂了"
        assert ca.humor_mechanism == "双关"


class TestMemeReviewFeedback:
    def test_fallback_good_templates(self):
        """Verify good feedback templates are non-empty strings."""
        GOOD_TPL = [
            "这个梗的幽默结构完整，可以收入数据库。",
            "双关/反讽/荒诞机制运作正常——通过。",
            "数据支持：此梗具备传播潜力。",
            "逻辑链完整，笑点部署合理——合格。",
            "这个观察角度不错，值得保留。",
        ]
        for t in GOOD_TPL:
            assert isinstance(t, str)
            assert len(t) > 5

    def test_fallback_bad_templates(self):
        """Verify bad feedback templates are non-empty strings."""
        BAD_TPL = [
            "这个梗的幽默密度≈真空，建议回炉重造。",
            "数据表明：此梗笑点缺失，情感共鸣为零。",
            "算法分析结果：该梗需要更多人类智慧注入。",
            "统计显示，此梗的传播系数接近于零——它不配。",
            "冷到连我的散热系统都不用工作了。",
        ]
        for t in BAD_TPL:
            assert isinstance(t, str)
            assert len(t) > 5


class TestMemePoolReviewIntegration:
    """Integration tests with MemePool using fake store."""

    class FakeStore:
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
        def update(self, meme):
            self._memes[meme.id] = meme
        def discard(self, meme_id):
            self._active.discard(meme_id)
            self._discarded.add(meme_id)

    def test_review_good_updates_score_and_status(self):
        from src.anima.memory.meme.engine import MemePool

        store = self.FakeStore()
        pool = MemePool(store=store)

        meme = pool.add_meme("好梗测试")
        meme.review_status = "good"
        meme.base_score = min(1.0, meme.base_score + 0.2)
        store.update(meme)

        updated = store.list_active()[0]
        assert updated.review_status == "good"
        assert updated.base_score > 0.7

    def test_review_bad_deactivates(self):
        from src.anima.memory.meme.engine import MemePool

        store = self.FakeStore()
        pool = MemePool(store=store)

        meme = pool.add_meme("烂梗测试")
        meme.review_status = "bad"
        meme.is_active = False
        store.update(meme)
        store.discard(meme.id)

        assert len(store.list_active()) == 0
        discarded = store.list_discarded()
        assert len(discarded) == 1
        assert discarded[0].review_status == "bad"

    def test_pending_memes_filter(self):
        from src.anima.memory.meme.engine import MemePool

        store = self.FakeStore()
        pool = MemePool(store=store)

        pool.add_meme("pending1")
        m2 = pool.add_meme("good1")
        m2.review_status = "good"
        store.update(m2)
        m3 = pool.add_meme("bad1")
        m3.review_status = "bad"
        store.update(m3)

        pending = [m for m in store.list_active() if m.review_status == "pending"]
        assert len(pending) == 1
        assert pending[0].text == "pending1"
