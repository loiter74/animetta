"""
SQLite storage layer.

Responsibilities:
- File metadata (files table): tracks indexed files and their hashes
- Text chunk metadata (chunks table): stores chunk text, path, line numbers
- FTS5 full-text index (chunks_fts): supports BM25 keyword search
- Embedding cache (embedding_cache): caches by content hash, avoids recomputation

References OpenClaw's memory-schema.ts and manager.ts
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from ..models.base import Chunk, FileEntry
from .memory_entry_store import MemoryEntryStore

logger = logging.getLogger(__name__)


class SQLiteStore:
    """SQLite metadata + FTS5 keyword search storage."""

    def __init__(self, db_path: str):
        logger.info(f"[SQLiteStore] >>> Initializing: db_path={db_path}")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"[SQLiteStore] Parent directory confirmed")

        logger.info(f"[SQLiteStore] Creating SQLite connection...")
        self.conn = sqlite3.connect(db_path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout = 5000")
        logger.info(f"[SQLiteStore] ✅ Connection created")

        logger.info(f"[SQLiteStore] Setting PRAGMA journal_mode=WAL...")
        self.conn.execute("PRAGMA journal_mode=WAL")
        logger.info(f"[SQLiteStore] ✅ WAL mode set")

        self.conn.execute("PRAGMA foreign_keys=ON")
        logger.info(f"[SQLiteStore] Foreign keys enabled")

        logger.info(f"[SQLiteStore] Creating tables...")
        self._create_tables()
        logger.info(f"[SQLiteStore] ✅ All tables created")

    def _create_tables(self):
        """Create core table structures."""
        all_ddl = """
            -- 已索引文件追踪
            CREATE TABLE IF NOT EXISTS files (
                path         TEXT PRIMARY KEY,
                source       TEXT NOT NULL,       -- 'memory' | 'daily' | 'session'
                file_hash    TEXT NOT NULL,
                indexed_at   REAL NOT NULL,
                chunk_count  INTEGER NOT NULL DEFAULT 0
            );

            -- 文本块
            CREATE TABLE IF NOT EXISTS chunks (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                path          TEXT NOT NULL,
                source        TEXT NOT NULL,
                start_line    INTEGER NOT NULL,
                end_line      INTEGER NOT NULL,
                text          TEXT NOT NULL,
                content_hash  TEXT NOT NULL,
                chunk_index   INTEGER NOT NULL,
                FOREIGN KEY (path) REFERENCES files(path) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
            CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(content_hash);

            -- FTS5 全文索引 (BM25 关键词搜索)
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                text,
                path,
                content='chunks',
                content_rowid='id',
                tokenize='unicode61'
            );

            -- FTS5 触发器: 保持同步
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, text, path)
                VALUES (new.id, new.text, new.path);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, text, path)
                VALUES ('delete', old.id, old.text, old.path);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, text, path)
                VALUES ('delete', old.id, old.text, old.path);
                INSERT INTO chunks_fts(rowid, text, path)
                VALUES (new.id, new.text, new.path);
            END;

            -- Embedding 缓存 (按内容哈希, 避免重复计算)
            CREATE TABLE IF NOT EXISTS embedding_cache (
                content_hash  TEXT PRIMARY KEY,
                model_name    TEXT NOT NULL,
                created_at    REAL NOT NULL
            );
        """
        # Append MemoryEntry + MemoryRelation tables
        all_ddl += MemoryEntryStore.ddl()
        self.conn.executescript(all_ddl)
        self.conn.commit()

    # ── File operations ──────────────────────────────────

    def get_file_entry(self, path: str) -> FileEntry | None:
        """Get file index record."""
        row = self.conn.execute(
            "SELECT * FROM files WHERE path = ?", (path,)
        ).fetchone()
        if row is None:
            return None
        return FileEntry(
            path=row["path"],
            source=row["source"],
            file_hash=row["file_hash"],
            indexed_at=row["indexed_at"],
            chunk_count=row["chunk_count"],
        )

    def upsert_file(self, entry: FileEntry):
        """Insert or update a file record."""
        self.conn.execute(
            """
            INSERT INTO files (path, source, file_hash, indexed_at, chunk_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                source=excluded.source,
                file_hash=excluded.file_hash,
                indexed_at=excluded.indexed_at,
                chunk_count=excluded.chunk_count
            """,
            (entry.path, entry.source, entry.file_hash, entry.indexed_at, entry.chunk_count),
        )
        self.conn.commit()

    # ── Chunk operations ─────────────────────────────────

    def delete_chunks_by_path(self, path: str):
        """Delete all chunks for a file (cascade delete also cleans up FTS)."""
        self.conn.execute("DELETE FROM chunks WHERE path = ?", (path,))
        self.conn.commit()

    def insert_chunks(self, chunks: list[Chunk]) -> list[int]:
        """Batch insert chunks, returns list of rowids."""
        cur = self.conn.cursor()
        rowids = []
        for c in chunks:
            cur.execute(
                """
                INSERT INTO chunks (path, source, start_line, end_line, text, content_hash, chunk_index)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (c.path, c.source, c.start_line, c.end_line, c.text, c.content_hash, c.chunk_index),
            )
            rowids.append(cur.lastrowid)
        self.conn.commit()
        return rowids

    def get_chunk_by_rowid(self, rowid: int) -> Chunk | None:
        """Get chunk by rowid."""
        row = self.conn.execute(
            "SELECT * FROM chunks WHERE id = ?", (rowid,)
        ).fetchone()
        if row is None:
            return None
        return Chunk(
            text=row["text"],
            path=row["path"],
            source=row["source"],
            start_line=row["start_line"],
            end_line=row["end_line"],
            content_hash=row["content_hash"],
            chunk_index=row["chunk_index"],
        )

    # ── FTS5 BM25 Search ────────────────────────────────

    def keyword_search(self, query: str, limit: int = 24) -> list[tuple[int, float]]:
        """
        FTS5 BM25 keyword search.

        Returns:
            [(rowid, bm25_rank), ...] — smaller rank is better (SQLite FTS5 rank is negative, larger absolute value = more relevant)
        """
        rows = self.conn.execute(
            """
            SELECT chunks.id, chunks_fts.rank
            FROM chunks_fts
            JOIN chunks ON chunks.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY chunks_fts.rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [(row["id"], row["rank"]) for row in rows]

    # ── Embedding cache ─────────────────────────────────

    def get_cached_hashes(self, content_hashes: list[str], model_name: str) -> set[str]:
        """Check which content hashes have cached embeddings."""
        if not content_hashes:
            return set()
        placeholders = ",".join("?" for _ in content_hashes)
        rows = self.conn.execute(
            f"""
            SELECT content_hash FROM embedding_cache
            WHERE content_hash IN ({placeholders}) AND model_name = ?
            """,
            (*content_hashes, model_name),
        ).fetchall()
        return {row["content_hash"] for row in rows}

    def mark_embedded(self, content_hashes: list[str], model_name: str):
        """Mark these contents as having completed embedding."""
        now = time.time()
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO embedding_cache (content_hash, model_name, created_at)
            VALUES (?, ?, ?)
            """,
            [(h, model_name, now) for h in content_hashes],
        )
        self.conn.commit()

    # ── Lifecycle ─────────────────────────────────────────

    def close(self):
        self.conn.close()
