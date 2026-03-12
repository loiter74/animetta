"""记忆模块配置."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ChunkConfig:
    """分块参数 (对齐 OpenClaw 默认值)."""

    target_tokens: int = 400  # 每块目标 token 数
    overlap_tokens: int = 80  # 相邻块重叠 token 数
    chars_per_token: float = 4.0  # 粗略的字符/token 比 (中文可调为 ~1.5)

    @property
    def target_chars(self) -> int:
        return int(self.target_tokens * self.chars_per_token)

    @property
    def overlap_chars(self) -> int:
        return int(self.overlap_tokens * self.chars_per_token)


@dataclass
class SearchConfig:
    """混合搜索参数."""

    vector_weight: float = 0.7  # 向量得分权重
    keyword_weight: float = 0.3  # 关键词 (BM25) 得分权重
    candidate_multiplier: int = 4  # 候选池 = max_results * multiplier
    default_max_results: int = 10
    default_min_score: float = 0.0


@dataclass
class EmbeddingConfig:
    """Embedding 模型配置."""

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    # 中文项目推荐: "shibing624/text2vec-base-chinese"
    # 或: "BAAI/bge-small-zh-v1.5"


@dataclass
class MemoryConfig:
    """记忆模块总配置."""

    workspace_dir: str = "~/.myagent/workspace"
    db_path: Optional[str] = None  # 默认 workspace_dir/memory.sqlite
    chroma_path: Optional[str] = None  # 默认 workspace_dir/chroma_db
    agent_id: str = "default"

    chunk: ChunkConfig = field(default_factory=ChunkConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    # 文件监控去抖时间 (秒)
    watch_debounce_seconds: float = 1.5

    # 记忆 flush 配置 (上下文压缩前自动保存)
    flush_enabled: bool = True
    flush_soft_threshold_tokens: int = 4000
    reserve_tokens_floor: int = 20000

    def resolve_paths(self) -> MemoryConfig:
        """展开 ~ 并设置默认路径."""
        ws = Path(self.workspace_dir).expanduser()
        self.workspace_dir = str(ws)
        if self.db_path is None:
            self.db_path = str(ws / "memory.sqlite")
        if self.chroma_path is None:
            self.chroma_path = str(ws / "chroma_db")
        return self
