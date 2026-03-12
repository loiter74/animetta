"""
核心记忆管理器.

对应 OpenClaw 的 MemoryIndexManager, 是整个记忆模块的入口:
- 管理 Markdown 文件的读写
- 增量索引: 检测文件变更, 只重建有改动的文件
- 暴露 search / get 接口供 Agent 调用
- 支持上下文压缩前自动 flush
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path

from .config import MemoryConfig
from .chunker import chunk_markdown, RawChunk
from .models import Chunk, FileEntry, SearchResult
from .sqlite_store import SQLiteStore
from .chroma_store import ChromaStore
from .hybrid_search import hybrid_search

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆模块核心管理器."""

    def __init__(self, config: MemoryConfig | None = None, **kwargs):
        """
        初始化记忆管理器.

        Args:
            config: 完整配置. 也可以用 kwargs 快速构建:
                MemoryManager(workspace_dir="~/.myagent/workspace")
        """
        if config is None:
            config = MemoryConfig(**kwargs)
        self.config = config.resolve_paths()

        ws = Path(self.config.workspace_dir)
        ws.mkdir(parents=True, exist_ok=True)
        (ws / "memory").mkdir(exist_ok=True)

        # 初始化存储层
        self.sqlite = SQLiteStore(self.config.db_path)
        self.chroma = ChromaStore(
            persist_dir=self.config.chroma_path,
            collection_name=f"memory_{self.config.agent_id}",
        )

        # 初始化 MEMORY.md 基础文件
        memory_file = ws / "MEMORY.md"
        if not memory_file.exists():
            memory_file.write_text("# Long-term Memory\n\n重要对话和用户偏好记录。\n", encoding="utf-8")
            logger.info(f"Created MEMORY.md at {memory_file}")

        # 尝试加载 sentence-transformers 用于 embedding
        self._embedder = None
        try:
            from sentence_transformers import SentenceTransformer

            # 强制使用 CPU，避免 CUDA 兼容性问题
            import os
            os.environ['CUDA_VISIBLE_DEVICES'] = ''

            self._embedder = SentenceTransformer(self.config.embedding.model_name, device='cpu')
            logger.info(f"Loaded embedding model: {self.config.embedding.model_name} (CPU)")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Vector search disabled, falling back to keyword-only."
            )
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            self._embedder = None
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            self._embedder = None

    # ── 文件读写 ──────────────────────────────────────────

    @property
    def _workspace(self) -> Path:
        return Path(self.config.workspace_dir)

    @property
    def _memory_file(self) -> Path:
        return self._workspace / "MEMORY.md"

    def _daily_log_path(self, date: datetime | None = None) -> Path:
        if date is None:
            date = datetime.now()
        return self._workspace / "memory" / f"{date.strftime('%Y-%m-%d')}.md"

    def write_memory(self, content: str, append: bool = True):
        """
        写入长期记忆 (MEMORY.md).

        Args:
            content: 要写入的内容
            append: True=追加, False=覆盖
        """
        path = self._memory_file
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            if append:
                f.write(f"\n{content}\n")
            else:
                f.write(content)
        logger.info(f"Wrote to MEMORY.md ({'append' if append else 'overwrite'})")
        # 自动增量索引
        self._index_file(str(path.relative_to(self._workspace)), "memory")

    def write_daily_log(self, content: str, date: datetime | None = None):
        """
        写入每日日志 (memory/YYYY-MM-DD.md), 始终追加.

        Args:
            content: 日志内容
            date: 指定日期, 默认今天
        """
        path = self._daily_log_path(date)
        with open(path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%H:%M")
            f.write(f"\n## {timestamp}\n{content}\n")
        logger.info(f"Wrote daily log: {path.name}")
        self._index_file(str(path.relative_to(self._workspace)), "daily")

    def get(
        self, relative_path: str, start_line: int | None = None, end_line: int | None = None
    ) -> str:
        """
        读取指定记忆文件 (对应 OpenClaw 的 memory_get).

        Args:
            relative_path: 相对于 workspace 的路径, 如 "MEMORY.md" 或 "memory/2026-03-13.md"
            start_line: 起始行 (1-based), None 表示从头
            end_line: 结束行 (1-based, inclusive), None 表示到尾

        Returns:
            文件内容 (或指定行范围的内容). 文件不存在返回空字符串.
        """
        path = self._workspace / relative_path
        if not path.exists():
            return ""  # 优雅降级, 和 OpenClaw 一致
        text = path.read_text(encoding="utf-8")
        if start_line is None and end_line is None:
            return text
        lines = text.split("\n")
        s = (start_line - 1) if start_line else 0
        e = end_line if end_line else len(lines)
        return "\n".join(lines[s:e])

    # ── 索引 ──────────────────────────────────────────────

    def sync(self):
        """
        全量同步: 扫描 workspace 下所有 .md 文件, 增量索引有变更的.

        类似 OpenClaw 的 MemoryIndexManager.sync().
        """
        files_to_index: list[tuple[str, str]] = []  # (relative_path, source)

        # MEMORY.md
        if self._memory_file.exists():
            files_to_index.append(("MEMORY.md", "memory"))

        # memory/*.md (每日日志)
        memory_dir = self._workspace / "memory"
        if memory_dir.exists():
            for md_file in sorted(memory_dir.glob("*.md")):
                rel = str(md_file.relative_to(self._workspace))
                files_to_index.append((rel, "daily"))

        indexed = 0
        skipped = 0
        for rel_path, source in files_to_index:
            changed = self._index_file(rel_path, source)
            if changed:
                indexed += 1
            else:
                skipped += 1

        logger.info(f"Sync complete: {indexed} indexed, {skipped} unchanged")

    def _index_file(self, relative_path: str, source: str) -> bool:
        """
        对单个文件进行增量索引.

        1. 计算文件哈希, 和已索引的比对
        2. 如果没变, 跳过
        3. 如果有变, 重新分块 → 存 SQLite → 算 embedding → 存 Chroma

        Returns:
            True 如果实际执行了索引, False 如果跳过
        """
        abs_path = self._workspace / relative_path
        if not abs_path.exists():
            return False

        content = abs_path.read_text(encoding="utf-8")
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # 检查是否需要重建
        existing = self.sqlite.get_file_entry(relative_path)
        if existing and existing.file_hash == file_hash:
            return False  # 文件没变, 跳过

        logger.info(f"Indexing: {relative_path}")

        # 分块
        raw_chunks = chunk_markdown(content, self.config.chunk)
        if not raw_chunks:
            return False

        # 构建 Chunk 对象
        chunks = [
            Chunk(
                text=rc.text,
                path=relative_path,
                source=source,
                start_line=rc.start_line,
                end_line=rc.end_line,
                content_hash=rc.content_hash,
                chunk_index=rc.chunk_index,
            )
            for rc in raw_chunks
        ]

        # 事务性更新: 先删旧的 chunks 和 vectors
        self.sqlite.delete_chunks_by_path(relative_path)
        self.chroma.delete_by_path(relative_path)

        # 先插入/更新文件记录（外键约束要求）
        self.sqlite.upsert_file(
            FileEntry(
                path=relative_path,
                source=source,
                file_hash=file_hash,
                indexed_at=time.time(),
                chunk_count=len(chunks),
            )
        )

        # 再插入 chunks
        rowids = self.sqlite.insert_chunks(chunks)

        # 计算 embedding (带缓存)
        embeddings = self._compute_embeddings(chunks)

        # 写入 Chroma
        self.chroma.upsert_chunks(chunks, rowids, embeddings)

        logger.info(f"Indexed {relative_path}: {len(chunks)} chunks")
        return True

    def _compute_embeddings(self, chunks: list[Chunk]) -> list[list[float]] | None:
        """
        计算 embedding, 利用内容哈希缓存避免重复计算.

        参考 OpenClaw 的 seedEmbeddingCache + batch embedding 策略.
        """
        if self._embedder is None:
            return None  # 无模型, Chroma 会用自带的 default embedding

        model_name = self.config.embedding.model_name

        # 检查缓存: 哪些块需要新计算
        all_hashes = [c.content_hash for c in chunks]
        cached = self.sqlite.get_cached_hashes(all_hashes, model_name)

        texts_to_embed = []
        indices_to_embed = []
        for i, chunk in enumerate(chunks):
            if chunk.content_hash not in cached:
                texts_to_embed.append(chunk.text)
                indices_to_embed.append(i)

        # 批量计算新的 embedding
        if texts_to_embed:
            new_embeddings = self._embedder.encode(
                texts_to_embed, show_progress_bar=False, normalize_embeddings=True
            )
            # 标记缓存
            new_hashes = [chunks[i].content_hash for i in indices_to_embed]
            self.sqlite.mark_embedded(new_hashes, model_name)
        else:
            new_embeddings = []

        # 所有块都需要 embedding (包括缓存的也要重新算, 因为我们不存向量本身在 SQLite)
        # 优化: 一次性 encode 全部, 缓存只用于跨文件去重
        all_embeddings = self._embedder.encode(
            [c.text for c in chunks], show_progress_bar=False, normalize_embeddings=True
        )
        return [emb.tolist() for emb in all_embeddings]

    # ── 搜索 ──────────────────────────────────────────────

    def search(
        self,
        query: str,
        max_results: int | None = None,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """
        混合搜索记忆 (对应 OpenClaw 的 memory_search).

        结合向量语义搜索和 BM25 关键词搜索, 加权融合后返回最相关的记忆片段.

        Args:
            query: 查询文本
            max_results: 返回结果数上限
            min_score: 最低分数阈值

        Returns:
            按相关性降序排列的 SearchResult 列表
        """
        query_embedding = None
        if self._embedder is not None:
            emb = self._embedder.encode([query], normalize_embeddings=True)
            query_embedding = emb[0].tolist()

        return hybrid_search(
            query=query,
            sqlite_store=self.sqlite,
            chroma_store=self.chroma,
            config=self.config.search,
            max_results=max_results,
            min_score=min_score,
            query_embedding=query_embedding,
        )

    # ── 上下文压缩前 flush ────────────────────────────────

    def should_flush(self, current_tokens: int, context_window: int) -> bool:
        """
        判断是否需要触发记忆 flush.

        参考 OpenClaw 的逻辑:
        当 current_tokens > context_window - reserve_floor - soft_threshold 时触发.

        Args:
            current_tokens: 当前会话消耗的 token 数
            context_window: 模型上下文窗口大小

        Returns:
            True 表示应该触发 flush
        """
        if not self.config.flush_enabled:
            return False
        threshold = (
            context_window
            - self.config.reserve_tokens_floor
            - self.config.flush_soft_threshold_tokens
        )
        return current_tokens > threshold

    def get_flush_prompt(self) -> str:
        """获取 flush 提示语, 注入到 Agent 的系统提示中."""
        return (
            "Session nearing compaction. "
            "Please write any important facts, decisions, or preferences "
            "to MEMORY.md or today's daily log before context is compressed. "
            "Reply with NO_REPLY if nothing to store."
        )

    # ── 会话上下文加载 ────────────────────────────────────

    def load_session_context(self) -> str:
        """
        加载会话启动时的记忆上下文.

        参考 OpenClaw: 加载 MEMORY.md + 今天日志 + 昨天日志.

        Returns:
            组合后的记忆上下文文本
        """
        parts = []

        # 长期记忆
        memory_content = self.get("MEMORY.md")
        if memory_content.strip():
            parts.append("# Long-term Memory (MEMORY.md)\n" + memory_content)

        # 今天日志
        today = datetime.now()
        today_log = self.get(f"memory/{today.strftime('%Y-%m-%d')}.md")
        if today_log.strip():
            parts.append(f"# Today's Log ({today.strftime('%Y-%m-%d')})\n" + today_log)

        # 昨天日志
        from datetime import timedelta

        yesterday = today - timedelta(days=1)
        yesterday_log = self.get(f"memory/{yesterday.strftime('%Y-%m-%d')}.md")
        if yesterday_log.strip():
            parts.append(
                f"# Yesterday's Log ({yesterday.strftime('%Y-%m-%d')})\n" + yesterday_log
            )

        return "\n\n---\n\n".join(parts) if parts else ""

    # ── 生命周期 ──────────────────────────────────────────

    def close(self):
        """释放资源."""
        self.sqlite.close()
        logger.info("MemoryManager closed")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
