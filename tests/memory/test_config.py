"""Tests for MemoryConfig, ChunkConfig, SearchConfig, EmbeddingConfig."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from animetta.memory.config import (
    ChunkConfig,
    EmbeddingConfig,
    MemoryConfig,
    SearchConfig,
)


class TestChunkConfig:
    """ChunkConfig defaults and computed properties."""

    def test_defaults(self):
        cfg = ChunkConfig()
        assert cfg.target_tokens == 400
        assert cfg.overlap_tokens == 80
        assert cfg.chars_per_token == 4.0

    def test_target_chars(self):
        cfg = ChunkConfig(target_tokens=500, chars_per_token=4.0)
        assert cfg.target_chars == 2000

    def test_overlap_chars(self):
        cfg = ChunkConfig(overlap_tokens=100, chars_per_token=4.0)
        assert cfg.overlap_chars == 400

    def test_custom_values(self):
        cfg = ChunkConfig(target_tokens=256, overlap_tokens=64, chars_per_token=1.5)
        assert cfg.target_tokens == 256
        assert cfg.overlap_tokens == 64
        assert cfg.chars_per_token == 1.5
        assert cfg.target_chars == int(256 * 1.5)
        assert cfg.overlap_chars == int(64 * 1.5)


class TestSearchConfig:
    """SearchConfig defaults and customisation."""

    def test_defaults(self):
        cfg = SearchConfig()
        assert cfg.vector_weight == 0.7
        assert cfg.keyword_weight == 0.3
        assert cfg.candidate_multiplier == 4
        assert cfg.default_max_results == 10
        assert cfg.default_min_score == 0.0

    def test_weights_sum_to_one(self):
        """vector_weight + keyword_weight should sum to 1.0 by convention."""
        cfg = SearchConfig()
        assert abs(cfg.vector_weight + cfg.keyword_weight - 1.0) < 1e-9

    def test_custom_values(self):
        cfg = SearchConfig(
            vector_weight=0.5,
            keyword_weight=0.5,
            candidate_multiplier=6,
            default_max_results=20,
            default_min_score=0.1,
        )
        assert cfg.vector_weight == 0.5
        assert cfg.default_min_score == 0.1


class TestEmbeddingConfig:
    """EmbeddingConfig defaults."""

    def test_default_model_name(self):
        cfg = EmbeddingConfig()
        assert cfg.model_name == "sentence-transformers/all-MiniLM-L6-v2"

    def test_custom_model(self):
        cfg = EmbeddingConfig(model_name="shibing624/text2vec-base-chinese")
        assert "text2vec" in cfg.model_name


class TestMemoryConfig:
    """MemoryConfig defaults and resolve_paths."""

    def test_defaults(self):
        cfg = MemoryConfig()
        assert cfg.workspace_dir == "~/.myagent/workspace"
        assert cfg.db_path is None
        assert cfg.chroma_path is None
        assert cfg.agent_id == "default"
        assert isinstance(cfg.chunk, ChunkConfig)
        assert isinstance(cfg.search, SearchConfig)
        assert isinstance(cfg.embedding, EmbeddingConfig)
        assert cfg.watch_debounce_seconds == 1.5
        assert cfg.flush_enabled is True

    def test_flush_thresholds(self):
        cfg = MemoryConfig(
            flush_soft_threshold_tokens=4000,
            reserve_tokens_floor=20000,
        )
        assert cfg.flush_soft_threshold_tokens == 4000
        assert cfg.reserve_tokens_floor == 20000

    def test_resolve_paths_sets_defaults(self, tmp_path):
        """resolve_paths expands ~ and fills None db_path/chroma_path."""
        ws = str(tmp_path / "workspace")
        cfg = MemoryConfig(workspace_dir=ws)
        cfg.resolve_paths()
        assert cfg.workspace_dir == ws
        assert cfg.db_path == str(Path(ws) / "memory.sqlite")
        assert cfg.chroma_path == str(Path(ws) / "chroma_db")

    def test_resolve_paths_preserves_explicit(self, tmp_path):
        """Explicit db_path and chroma_path are kept after resolve_paths."""
        ws = str(tmp_path / "workspace")
        cfg = MemoryConfig(
            workspace_dir=ws,
            db_path=str(tmp_path / "custom.db"),
            chroma_path=str(tmp_path / "custom_chroma"),
        )
        cfg.resolve_paths()
        assert "custom.db" in cfg.db_path
        assert "custom_chroma" in cfg.chroma_path

    def test_nested_configs_are_independent(self):
        """Modifying one config object doesn't affect another."""
        a = MemoryConfig()
        b = MemoryConfig()
        b.chunk.target_tokens = 999
        assert a.chunk.target_tokens == 400
        assert b.chunk.target_tokens == 999
