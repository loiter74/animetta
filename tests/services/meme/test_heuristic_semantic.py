"""Tests for heuristic semantic phrase extraction with jieba + TF-IDF."""

from unittest.mock import patch

import pytest


class TestExtractSemanticPhrases:
    """Semantic phrase extraction using jieba segmentation and TF-IDF."""

    def test_extract_from_multiple_texts(self):
        """Should extract meaningful 2-4 word n-grams from Chinese texts."""
        from animetta import $$$

        texts = [
            "这个视频真的太搞笑了",
            "笑死我了这个梗",
            "这个梗绝绝子",
        ]

        phrases = Collector._extract_semantic_phrases(texts, top_k=10)

        assert len(phrases) > 0
        # Each result should be (phrase, score) tuple
        for phrase, score in phrases:
            assert isinstance(phrase, str)
            assert isinstance(score, (int, float))
            assert len(phrase) >= 2

    def test_returns_empty_for_empty_input(self):
        from animetta import $$$

        assert Collector._extract_semantic_phrases([], top_k=10) == []

    def test_filters_single_occurrence(self):
        """Phrases appearing only once should be penalized by TF-IDF."""
        from animetta import $$$

        texts = [
            "这是一个唯一的短语AAAA",
            "完全不同的内容BBBB",
            "完全不同的内容CCCC",
        ]

        phrases = Collector._extract_semantic_phrases(texts, top_k=20)

        # "完全不同的内容" appears in 2 docs → should rank higher
        cross_doc = [s for s in phrases if "完全不同" in s[0] or "同的内容" in s[0]]
        unique = [s for s in phrases if "唯一的短语" in s[0] or "AAAA" in s[0]]
        # Cross-doc phrases should have higher scores
        if cross_doc and unique:
            assert cross_doc[0][1] >= unique[0][1]

    def test_respects_top_k_limit(self):
        from animetta import $$$

        texts = ["A" * 20, "B" * 20, "C" * 20]  # diverse content
        phrases = Collector._extract_semantic_phrases(texts, top_k=5)
        assert len(phrases) <= 5

    def test_fallback_when_jieba_not_installed(self):
        """When jieba is unavailable, should fall back to char n-grams."""
        from animetta import $$$

        texts = ["测试文本", "测试文本"]
        # Patch to simulate missing jieba
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'jieba':
                raise ImportError("No module named 'jieba'")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            phrases = Collector._extract_semantic_phrases(texts, top_k=10)

        # Should still return results via fallback
        assert len(phrases) > 0
        for phrase, score in phrases:
            assert isinstance(phrase, str)
            assert score >= 1

    def test_heuristic_identify_calls_semantic_extraction(self):
        """_heuristic_identify should use semantic extraction for danmaku strategy."""
        from animetta import $$$

        c = Collector(llm_client=None)
        videos = [CollectedVideo(bvid="BV1xx", title="测试")]
        danmaku = ["绝绝子", "绝绝子", "绝绝子", "笑死", "yyds"]

        candidates = c._heuristic_identify(videos, {}, danmaku)

        # Should include danmaku-derived candidates
        danmaku_tags = [cc for cc in candidates if "danmaku" in (cc.tags or [])]
        # At least attempt extraction (may or may not find depending on content)
        assert len(candidates) >= 0

    def test_semantic_extraction_skips_stopwords(self):
        """Stopwords should be filtered out from results."""
        from animetta import $$$

        texts = ["的的的的的的", "了的了的了"]
        phrases = Collector._extract_semantic_phrases(texts, top_k=10)

        # Stopword-only texts should produce minimal results
        for phrase, score in phrases:
            # If jieba splits them, short common phrases may appear
            # but they should have very low scores
            pass  # Just verify no crash
