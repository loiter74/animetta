"""
Low-level storage engine (SQLite FTS5 + Chroma vector), called by WikiManager.
- Incremental indexing: detects file changes, rebuilds only modified files
- Hybrid search: vector semantic + BM25 keyword
- Embedding computation (sentence-transformers)
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path

from .config import MemoryConfig
from .models.chunks import chunk_markdown, RawChunk
from .models.base import Chunk, FileEntry, SearchResult
from .storage.sqlite import SQLiteStore
from .storage.chroma import ChromaStore
from .storage.memory_entry_store import MemoryEntryStore
from .search.hybrid import hybrid_search

logger = logging.getLogger(__name__)


class MemoryManager:
    """Low-level storage manager (SQLite + Chroma + file indexing)."""

    def __init__(self, config: MemoryConfig | None = None, **kwargs):
        if config is None:
            config = MemoryConfig(**kwargs)
        self.config = config.resolve_paths()
        logger.info(f"[MemoryManager] workspace={self.config.workspace_dir}")

        ws = Path(self.config.workspace_dir)
        ws.mkdir(parents=True, exist_ok=True)

        # Initialize storage layer
        self.sqlite = SQLiteStore(self.config.db_path)
        self.chroma = ChromaStore(
            persist_dir=self.config.chroma_path,
            collection_name=f"memory_{self.config.agent_id}",
            embedding_dim=512,
        )
        self.memory_entries = MemoryEntryStore(self.sqlite.conn)

        # Embedding model
        self._embedder = None
        try:
            import os
            os.environ['CUDA_VISIBLE_DEVICES'] = ''
            os.environ.setdefault('TORCH_CODEC_DISABLE', '1')  # suppress libtorchcodec noise
            from sentence_transformers import SentenceTransformer
            logger.info(f"[MemoryManager] loading embedding: {self.config.embedding.model_name}")
            start = time.time()
            self._embedder = SentenceTransformer(self.config.embedding.model_name, device='cpu')
            logger.info(f"[MemoryManager] embedding ready ({time.time() - start:.1f}s)")
        except ImportError:
            logger.info("[MemoryManager] sentence-transformers not installed, keyword-only search")
        except Exception as e:
            logger.info(f"[MemoryManager] embedding unavailable (keyword-only): {e}")

    # ── Workspace ──────────────────────────────────────────

    @property
    def _workspace(self) -> Path:
        return Path(self.config.workspace_dir)

    def get(
        self, relative_path: str, start_line: int | None = None, end_line: int | None = None
    ) -> str:
        """Read a file under workspace."""
        path = self._workspace / relative_path
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        if start_line is None and end_line is None:
            return text
        lines = text.split("\n")
        s = (start_line - 1) if start_line else 0
        e = end_line if end_line else len(lines)
        return "\n".join(lines[s:e])

    # ── Indexing ──────────────────────────────────────────

    def sync(self):
        """Full sync: scan all .md files under raw/ + wiki/."""
        files_to_index: list[tuple[str, str]] = []

        # raw/ directory
        raw_dir = self._workspace / "raw"
        if raw_dir.exists():
            for md in sorted(raw_dir.glob("*.md")):
                files_to_index.append((f"raw/{md.name}", "raw"))

        # wiki/ directory
        wiki_dir = self._workspace / "wiki"
        if wiki_dir.exists():
            for md in sorted(wiki_dir.rglob("*.md")):
                rel = str(md.relative_to(self._workspace))
                files_to_index.append((rel, "wiki"))

        indexed = 0
        for rel, src in files_to_index:
            if self._index_file(rel, src):
                indexed += 1
        logger.info(f"[MemoryManager] sync: {indexed} indexed, {len(files_to_index) - indexed} unchanged")

    def _index_file(self, relative_path: str, source: str) -> bool:
        """Incremental index for a single file."""
        abs_path = self._workspace / relative_path
        if not abs_path.exists():
            return False

        content = abs_path.read_text(encoding="utf-8")
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        existing = self.sqlite.get_file_entry(relative_path)
        if existing and existing.file_hash == file_hash:
            return False

        raw_chunks = chunk_markdown(content, self.config.chunk)
        if not raw_chunks:
            return False

        chunks = [
            Chunk(
                text=rc.text, path=relative_path, source=source,
                start_line=rc.start_line, end_line=rc.end_line,
                content_hash=rc.content_hash, chunk_index=rc.chunk_index,
                oral_version=None,
            )
            for rc in raw_chunks
        ]

        self.sqlite.delete_chunks_by_path(relative_path)
        self.chroma.delete_by_path(relative_path)
        self.sqlite.upsert_file(FileEntry(
            path=relative_path, source=source, file_hash=file_hash,
            indexed_at=time.time(), chunk_count=len(chunks),
        ))
        rowids = self.sqlite.insert_chunks(chunks)
        embeddings = self._compute_embeddings(chunks)
        self.chroma.upsert_chunks(chunks, rowids, embeddings)
        logger.info(f"[MemoryManager] indexed {relative_path}: {len(chunks)} chunks")
        return True

    def _compute_embeddings(self, chunks: list[Chunk]) -> list[list[float]] | None:
        if self._embedder is None:
            return None
        model_name = self.config.embedding.model_name
        all_hashes = [c.content_hash for c in chunks]
        cached = self.sqlite.get_cached_hashes(all_hashes, model_name)
        new_indices = [i for i, c in enumerate(chunks) if c.content_hash not in cached]
        if new_indices:
            texts = [chunks[i].text for i in new_indices]
            self._embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            new_hashes = [chunks[i].content_hash for i in new_indices]
            self.sqlite.mark_embedded(new_hashes, model_name)

        all_embeddings = self._embedder.encode(
            [c.text for c in chunks], show_progress_bar=False, normalize_embeddings=True
        )
        return [emb.tolist() for emb in all_embeddings]

    # ── Search ─────────────────────────────────────────────

    def search(
        self, query: str, max_results: int | None = None, min_score: float | None = None,
    ) -> list[SearchResult]:
        """Hybrid search (vector + BM25)."""
        query_embedding = None
        if self._embedder is not None:
            emb = self._embedder.encode([query], normalize_embeddings=True)
            query_embedding = emb[0].tolist()

        return hybrid_search(
            query=query, sqlite_store=self.sqlite, chroma_store=self.chroma,
            config=self.config.search, max_results=max_results,
            min_score=min_score, query_embedding=query_embedding,
        )

    # ── Flush ──────────────────────────────────────────────

    def should_flush(self, current_tokens: int, context_window: int) -> bool:
        if not self.config.flush_enabled:
            return False
        threshold = context_window - self.config.reserve_tokens_floor - self.config.flush_soft_threshold_tokens
        return current_tokens > threshold

    # ── Lifecycle ─────────────────────────────────────────

    def close(self):
        self.sqlite.close()
        logger.info("[MemoryManager] closed")
