"""Memory module configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ChunkConfig:
    """Chunking parameters (aligning with OpenClaw defaults)."""

    target_tokens: int = 400  # Target tokens per chunk
    overlap_tokens: int = 80  # Overlap tokens between adjacent chunks
    chars_per_token: float = 4.0  # Rough character/token ratio (adjust to ~1.5 for Chinese)

    @property
    def target_chars(self) -> int:
        return int(self.target_tokens * self.chars_per_token)

    @property
    def overlap_chars(self) -> int:
        return int(self.overlap_tokens * self.chars_per_token)


@dataclass
class SearchConfig:
    """Hybrid search parameters."""

    vector_weight: float = 0.7  # Vector score weight
    keyword_weight: float = 0.3  # Keyword (BM25) score weight
    candidate_multiplier: int = 4  # Candidate pool = max_results * multiplier
    default_max_results: int = 10
    default_min_score: float = 0.0


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Recommended for Chinese projects: "shibing624/text2vec-base-chinese"
    # Or: "BAAI/bge-small-zh-v1.5"


@dataclass
class MemoryConfig:
    """Memory module master configuration."""

    workspace_dir: str = "~/.myagent/workspace"
    db_path: Optional[str] = None  # Defaults to workspace_dir/memory.sqlite
    chroma_path: Optional[str] = None  # Defaults to workspace_dir/chroma_db
    agent_id: str = "default"

    chunk: ChunkConfig = field(default_factory=ChunkConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    # File watch debounce time (seconds)
    watch_debounce_seconds: float = 1.5

    # Memory flush configuration (auto-save before context compression)
    flush_enabled: bool = True
    flush_soft_threshold_tokens: int = 4000
    reserve_tokens_floor: int = 20000

    def resolve_paths(self) -> MemoryConfig:
        """Expand ~ and set default paths."""
        ws = Path(self.workspace_dir).expanduser()
        self.workspace_dir = str(ws)
        if self.db_path is None:
            self.db_path = str(ws / "memory.sqlite")
        if self.chroma_path is None:
            self.chroma_path = str(ws / "chroma_db")
        return self
