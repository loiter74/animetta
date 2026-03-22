"""
SQLite 存储层.

负责:
- 文件元数据 (files 表): 追踪已索引文件及其哈希
- 文本块元数据 (chunks 表): 存储块文本、路径、行号
- FTS5 全文索引 (chunks_fts): 支持 BM25 关键词搜索
- Embedding 缓存 (embedding_cache): 按内容哈希缓存, 避免重复计算

参考 OpenClaw 的 memory-schema.ts 和 manager.ts
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from ..models.base import Chunk, FileEntry

logger = logging.getLogger(__name__)


class SQLiteStore:
    """SQLite 元数据 + FTS5 关键词搜索存储."""

    def __init__(self, db_path: str):
        logger.info(f"[SQLiteStore] >>> 开始初始化: db_path={db_path}")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"[SQLiteStore] 父目录已确认")

        logger.info(f"[SQLiteStore] 创建 SQLite 连接...")
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"[SQLiteStore] ✅ 连接已创建")

        logger.info(f"[SQLiteStore] 设置 PRAGMA journal_mode=WAL...")
        self.conn.execute("PRAGMA journal_mode=WAL")
        logger.info(f"[SQLiteStore] ✅ WAL 模式已设置")

        self.conn.execute("PRAGMA foreign_keys=ON")
        logger.info(f"[SQLiteStore] 外键已启用")

        logger.info(f"[SQLiteStore] 创建表结构...")
        self._create_tables()
        logger.info(f"[SQLiteStore] ✅ 所有表已创建")

    def _create_tables(self):
        """创建核心表结构."""
        self.conn.executescript(
            """
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
        )
        self.conn.commit()

    # ── 文件操作 ──────────────────────────────────────────

    def get_file_entry(self, path: str) -> FileEntry | None:
        """获取文件索引记录."""
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
        """插入或更新文件记录."""
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

    # ── 块操作 ────────────────────────────────────────────

    def delete_chunks_by_path(self, path: str):
        """删除某文件的所有块 (级联删除也会清理 FTS)."""
        self.conn.execute("DELETE FROM chunks WHERE path = ?", (path,))
        self.conn.commit()

    def insert_chunks(self, chunks: list[Chunk]) -> list[int]:
        """批量插入块, 返回 rowid 列表."""
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
        """按 rowid 获取块."""
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

    # ── FTS5 BM25 搜索 ───────────────────────────────────

    def keyword_search(self, query: str, limit: int = 24) -> list[tuple[int, float]]:
        """
        FTS5 BM25 关键词搜索.

        Returns:
            [(rowid, bm25_rank), ...] — rank 越小越好 (SQLite FTS5 的 rank 是负数, 绝对值越大越相关)
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

    # ── Embedding 缓存 ───────────────────────────────────

    def get_cached_hashes(self, content_hashes: list[str], model_name: str) -> set[str]:
        """检查哪些内容哈希已有缓存的 embedding."""
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
        """标记这些内容已完成 embedding."""
        now = time.time()
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO embedding_cache (content_hash, model_name, created_at)
            VALUES (?, ?, ?)
            """,
            [(h, model_name, now) for h in content_hashes],
        )
        self.conn.commit()

    # ── 生命周期 ──────────────────────────────────────────

    def close(self):
        self.conn.close()
