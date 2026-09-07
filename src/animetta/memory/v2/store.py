"""AtomStore — unified persistence layer for MemoryAtoms.

SQLite for structured data + FTS5 for full-text search.
Chroma for vector semantic search.
Wiki export layer for human-readable backups.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import partial
from typing import Any

import aiosqlite

from animetta.memory.v2.atom import (
    Layer,
    MemoryAtom,
    MemoryScope,
    MemoryVisibility,
    Relation,
)

logger = logging.getLogger(__name__)

# Optional Chroma support
try:
    import chromadb
    from chromadb.core.config import Settings

    _HAS_CHROMA = True
except ImportError:
    _HAS_CHROMA = False
    chromadb = None  # type: ignore[assignment]


class AtomStore:
    """Unified persistence for MemoryAtoms.

    Replaces MemoryEntryStore + WikiManager with a single store.
    Reuses existing SQLite patterns from storage/sqlite.py.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        db_path: str = "memory_db/living_memory.sqlite",
        *,
        enable_chroma: bool = True,
    ):
        self.db_path = db_path
        self.enable_chroma = enable_chroma
        self._conn: aiosqlite.Connection | None = None
        self._db_lock = asyncio.Lock()
        self._index_lock = asyncio.Lock()
        self._vector_slot = asyncio.Semaphore(1)
        self._vector_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="memory-vector"
        )
        self._vector_tasks: set[asyncio.Future] = set()
        self._closing = False
        self._close_task: asyncio.Task | None = None
        self._chroma_client: Any = None
        self._chroma_collection: Any = None
        self._index_degraded = False
        self._index_last_error = ""

    async def initialize(self) -> None:
        async with self._db_lock:
            if self._closing:
                raise RuntimeError("Memory store is closing")
            if self._conn is not None:
                return
            connection = aiosqlite.connect(self.db_path)
            try:
                await connection
                self._conn = connection
                connection.row_factory = aiosqlite.Row
                await self._execute("PRAGMA journal_mode=WAL")
                legacy_schema = await self._is_legacy_schema()
                await self._create_tables()
                await self._migrate_schema(legacy_schema=legacy_schema)
                await self._settle(asyncio.create_task(connection.commit()))
            except BaseException:
                await self._settle(asyncio.create_task(connection.close()))
                self._conn = None
                raise
        if self.enable_chroma and _HAS_CHROMA:
            await self._run_vector(self._init_chroma)

    @staticmethod
    async def _settle(task: asyncio.Future) -> Any:
        """Finish queued cleanup/commit even if the caller is cancelled repeatedly."""
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        result = task.result()
        if cancelled:
            raise asyncio.CancelledError
        return result

    @asynccontextmanager
    async def _database(self, *, write: bool = False) -> AsyncIterator[None]:
        async with self._db_lock:
            if self._closing or self._conn is None:
                raise RuntimeError("Memory store is unavailable")
            if not write:
                yield
                return
            try:
                await self._execute("BEGIN IMMEDIATE")
                yield
            except BaseException:
                await self._settle(asyncio.create_task(self._conn.rollback()))
                raise
            else:
                # Once commit is queued its outcome must be observed before unlocking.
                current = asyncio.current_task()
                if current is not None and current.cancelling():
                    await self._settle(asyncio.create_task(self._conn.rollback()))
                    raise asyncio.CancelledError
                try:
                    await self._settle(asyncio.create_task(self._conn.commit()))
                except asyncio.CancelledError:
                    raise
                except BaseException:
                    await self._settle(asyncio.create_task(self._conn.rollback()))
                    raise

    async def _execute(self, sql: str, parameters: tuple = ()) -> int:
        assert self._conn is not None
        async with self._conn.execute(sql, parameters) as cursor:
            return cursor.rowcount

    async def _fetchone(self, sql: str, parameters: tuple = ()) -> aiosqlite.Row | None:
        assert self._conn is not None
        async with self._conn.execute(sql, parameters) as cursor:
            return await cursor.fetchone()

    async def _fetchall(self, sql: str, parameters: tuple = ()) -> list[aiosqlite.Row]:
        assert self._conn is not None
        async with self._conn.execute(sql, parameters) as cursor:
            return list(await cursor.fetchall())

    async def _run_vector(self, operation: Callable, *args: Any, **kwargs: Any) -> Any:
        # Admission occurs before submission, so cancelled waiters cannot fill an executor queue.
        await self._vector_slot.acquire()
        if self._closing:
            self._vector_slot.release()
            raise RuntimeError("Memory store is closing")
        try:
            future = asyncio.get_running_loop().run_in_executor(
                self._vector_executor, partial(operation, *args, **kwargs)
            )
        except BaseException:
            self._vector_slot.release()
            raise
        self._vector_tasks.add(future)
        future.add_done_callback(self._vector_finished)
        return await asyncio.shield(future)

    def _vector_finished(self, future: asyncio.Future) -> None:
        self._vector_tasks.discard(future)
        self._vector_slot.release()
        if not future.cancelled():
            future.exception()  # Observe failures even after a recall deadline cancelled its waiter.

    async def _is_legacy_schema(self) -> bool:
        exists = await self._fetchone(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_atoms'"
        )
        if not exists:
            return False
        columns = {row["name"] for row in (await self._fetchall("PRAGMA table_info(memory_atoms)"))}
        return "scope" not in columns

    def _init_chroma(self) -> None:
        """Initialize Chroma vector store if available."""
        if not self.enable_chroma or not _HAS_CHROMA:
            return
        try:
            self._chroma_client = chromadb.Client(
                Settings(
                    is_persistent=True,
                    persist_directory="memory_db/chroma_v2",
                    anonymized_telemetry=False,
                )
            )
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="memory_atoms_v2",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.warning(f"Chroma init failed, vector search disabled: {e}")
            self._chroma_client = None

    async def _vector_search(self, query_text: str, limit: int = 50) -> list[tuple[str, float]]:
        """Vector similarity search via Chroma. Returns [(atom_id, score), ...]."""
        if not self._chroma_collection:
            return []
        try:
            results = await self._run_vector(
                self._chroma_collection.query,
                query_texts=[query_text],
                n_results=limit,
                include=["distances"],
            )
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0]
            # Convert cosine distance to similarity score (1 - distance)
            return [(id_, 1.0 - float(dist)) for id_, dist in zip(ids, distances)]
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []

    async def _upsert_chroma(self, atom: MemoryAtom) -> None:
        """Add or update atom embedding in Chroma."""
        if not self._chroma_collection:
            return
        text = atom.summary or atom.content
        await self._run_vector(
            self._chroma_collection.upsert,
            ids=[atom.id],
            documents=[text],
            metadatas=[
                {
                    "layer": atom.layer.value,
                    "scope": atom.scope.value,
                    "confidence": atom.confidence,
                    "salience": atom.salience,
                }
            ],
        )

    async def close(self) -> None:
        if self._close_task is None:
            self._closing = True
            self._close_task = asyncio.create_task(self._close())
        await asyncio.shield(self._close_task)

    async def _close(self) -> None:
        if self._vector_tasks:
            await asyncio.gather(*self._vector_tasks, return_exceptions=True)
        self._vector_executor.shutdown(wait=True)
        async with self._db_lock:
            if self._conn is not None:
                await self._conn.close()
                self._conn = None

    async def _create_tables(self) -> None:
        assert self._conn is not None
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memory_atoms (
                id TEXT PRIMARY KEY,
                layer INTEGER NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                occurred_at TEXT NOT NULL,
                rewritten_at TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                version_chain TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.5,
                salience REAL DEFAULT 0.5,
                retrieval_count INTEGER DEFAULT 0,
                last_accessed_at TEXT,
                emotion_valence REAL DEFAULT 0.0,
                emotion_arousal REAL DEFAULT 0.0,
                emotion_dominance REAL DEFAULT 0.0,
                source_ids TEXT DEFAULT '[]',
                relations TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                scope TEXT NOT NULL DEFAULT 'community',
                visibility TEXT NOT NULL DEFAULT 'internal',
                subject_ids TEXT NOT NULL DEFAULT '[]',
                origin TEXT NOT NULL DEFAULT '{}',
                trust_level REAL NOT NULL DEFAULT 0.5,
                retention_policy TEXT NOT NULL DEFAULT 'standard',
                index_state TEXT NOT NULL DEFAULT 'pending',
                decay_rate REAL DEFAULT 0.1,
                forget_at TEXT,
                is_archived INTEGER DEFAULT 0
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                content, summary
            );

            CREATE TABLE IF NOT EXISTS memory_relations (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                PRIMARY KEY (source_id, target_id, relation_type)
            );

            CREATE TABLE IF NOT EXISTS memory_versions (
                atom_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                rewritten_at TEXT NOT NULL,
                emotion_valence REAL,
                emotion_arousal REAL,
                emotion_dominance REAL,
                PRIMARY KEY (atom_id, version)
            );

            CREATE TABLE IF NOT EXISTS memory_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory_index_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atom_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                revision INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

    async def _migrate_schema(self, *, legacy_schema: bool) -> None:
        """Apply additive migrations and preserve all legacy atom data."""

        columns = {row["name"] for row in (await self._fetchall("PRAGMA table_info(memory_atoms)"))}
        additions = {
            "scope": "TEXT NOT NULL DEFAULT 'community'",
            "visibility": "TEXT NOT NULL DEFAULT 'internal'",
            "subject_ids": "TEXT NOT NULL DEFAULT '[]'",
            "origin": "TEXT NOT NULL DEFAULT '{}'",
            "trust_level": "REAL NOT NULL DEFAULT 0.5",
            "retention_policy": "TEXT NOT NULL DEFAULT 'standard'",
            "index_state": "TEXT NOT NULL DEFAULT 'pending'",
        }
        for name, declaration in additions.items():
            if name not in columns:
                await self._execute(f"ALTER TABLE memory_atoms ADD COLUMN {name} {declaration}")

        if legacy_schema:
            await self._execute(
                "UPDATE memory_atoms SET origin = ? WHERE origin = '{}'",
                (json.dumps({"legacy": True}),),
            )
            # A legacy database may not have populated the newly-created FTS table.
            await self._execute("DELETE FROM memory_fts")
            await self._execute(
                "INSERT INTO memory_fts(rowid, content, summary) "
                "SELECT rowid, content, COALESCE(summary, '') FROM memory_atoms"
            )

        await self._execute(
            "INSERT OR IGNORE INTO memory_metadata(key, value) VALUES ('revision', '0')"
        )
        await self._execute(
            "INSERT INTO memory_metadata(key, value) VALUES ('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(self.SCHEMA_VERSION),),
        )

    async def get_schema_version(self) -> int:
        async with self._database():
            row = await self._fetchone(
                "SELECT value FROM memory_metadata WHERE key='schema_version'"
            )
            return int(row["value"]) if row else 0

    async def get_revision(self) -> int:
        async with self._database():
            row = await self._fetchone("SELECT value FROM memory_metadata WHERE key='revision'")
            return int(row["value"]) if row else 0

    async def _next_revision(self) -> int:
        current = await self._fetchone("SELECT value FROM memory_metadata WHERE key='revision'")
        revision = (int(current["value"]) if current else 0) + 1
        await self._execute(
            "INSERT INTO memory_metadata(key, value) VALUES ('revision', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(revision),),
        )
        return revision

    async def _enqueue_index(self, atom_id: str, operation: str, revision: int) -> None:
        now = datetime.now(UTC).isoformat()
        await self._execute(
            """
            INSERT INTO memory_index_outbox(
                atom_id, operation, revision, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (atom_id, operation, revision, now, now),
        )

    async def get_index_backlog(self) -> int:
        async with self._database():
            row = await self._fetchone(
                "SELECT COUNT(*) AS count FROM memory_index_outbox WHERE status='pending'"
            )
            assert row is not None
            return int(row["count"])

    def get_index_health(self) -> dict[str, object]:
        """Return synchronous derived-index health for probes and runtime status."""

        return {
            "degraded": self._index_degraded,
            "last_error": self._index_last_error,
        }

    async def process_index_outbox(self, limit: int = 100) -> dict[str, int]:
        """Snapshot pending work, index outside SQLite, then acknowledge exactly that work."""
        async with self._index_lock:
            async with self._database():
                rows = await self._fetchall(
                    "SELECT * FROM memory_index_outbox WHERE status='pending' "
                    "ORDER BY revision, id LIMIT ?",
                    (limit,),
                )
                snapshots = [(row, await self._get(row["atom_id"])) for row in rows]
            failed = 0
            for row, atom in snapshots:
                error: str | None = None
                try:
                    if atom is not None:
                        await self._upsert_chroma(atom)
                except Exception as exc:
                    error = str(exc)
                    failed += 1
                    logger.warning(
                        "Memory vector indexing failed for %s: %s", row["atom_id"], error
                    )
                async with self._database(write=True):
                    await self._acknowledge_index(row["atom_id"], [row["id"]], error)
            if failed == 0 and await self.get_index_backlog() == 0:
                self._index_degraded = False
                self._index_last_error = ""
            return {"processed": len(rows), "succeeded": len(rows) - failed, "failed": failed}

    async def _acknowledge_index(self, atom_id: str, ids: list[int], error: str | None) -> None:
        now = datetime.now(UTC).isoformat()
        for record_id in ids:
            if error is not None:
                await self._execute(
                    "UPDATE memory_index_outbox SET attempts=attempts+1, last_error=?, "
                    "updated_at=? WHERE id=? AND status='pending'",
                    (error, now, record_id),
                )
            else:
                await self._execute(
                    "UPDATE memory_index_outbox SET status='done', last_error=NULL, "
                    "updated_at=? WHERE id=?",
                    (now, record_id),
                )
        if error is not None:
            self._index_degraded = True
            self._index_last_error = error
            await self._execute(
                "UPDATE memory_atoms SET index_state='pending' WHERE id=?", (atom_id,)
            )
        else:
            await self._execute(
                "UPDATE memory_atoms SET index_state=CASE WHEN EXISTS "
                "(SELECT 1 FROM memory_index_outbox WHERE atom_id=? AND status='pending') "
                "THEN 'pending' ELSE 'ready' END WHERE id=?",
                (atom_id, atom_id),
            )

    async def rebuild_indexes(self) -> int:
        """Rebuild derived indexes without acknowledging writes made after the snapshot."""
        async with self._index_lock:
            async with self._database(write=True):
                atoms = [
                    self._row_to_atom(row)
                    for row in await self._fetchall(
                        "SELECT * FROM memory_atoms WHERE is_archived=0 ORDER BY salience DESC LIMIT 1000"
                    )
                ]
                pending: dict[str, list[int]] = {}
                for row in await self._fetchall(
                    "SELECT id, atom_id FROM memory_index_outbox WHERE status='pending'"
                ):
                    pending.setdefault(row["atom_id"], []).append(row["id"])
                await self._execute("DELETE FROM memory_fts")
                await self._execute(
                    "INSERT INTO memory_fts(rowid, content, summary) "
                    "SELECT rowid, content, COALESCE(summary, '') FROM memory_atoms WHERE is_archived=0"
                )
            failures: list[str] = []
            for atom in atoms:
                error: str | None = None
                try:
                    await self._upsert_chroma(atom)
                except Exception as exc:
                    error = str(exc)
                    failures.append(f"{atom.id}: {error}")
                async with self._database(write=True):
                    await self._acknowledge_index(atom.id, pending.get(atom.id, []), error)
            if failures:
                self._index_degraded = True
                self._index_last_error = "; ".join(failures)
            elif await self.get_index_backlog() == 0:
                self._index_degraded = False
                self._index_last_error = ""
            return len(atoms)

    # ── CRUD ──

    async def create(self, atom: MemoryAtom) -> str:
        async with self._database(write=True):
            await self._execute(
                """
                INSERT INTO memory_atoms (id, layer, content, summary, occurred_at,
                    rewritten_at, version, version_chain, confidence, salience,
                    retrieval_count, last_accessed_at, emotion_valence, emotion_arousal,
                    emotion_dominance, source_ids, relations, tags, scope, visibility,
                    subject_ids, origin, trust_level, retention_policy, index_state,
                    decay_rate, forget_at, is_archived)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    atom.id,
                    atom.layer.value,
                    atom.content,
                    atom.summary,
                    atom.occurred_at.isoformat(),
                    atom.rewritten_at.isoformat()
                    if atom.rewritten_at
                    else atom.occurred_at.isoformat(),
                    atom.version,
                    json.dumps(atom.version_chain),
                    atom.confidence,
                    atom.salience,
                    atom.retrieval_count,
                    atom.last_accessed_at.isoformat() if atom.last_accessed_at else None,
                    atom.emotion_valence,
                    atom.emotion_arousal,
                    atom.emotion_dominance,
                    json.dumps(atom.source_ids),
                    json.dumps([self._relation_to_dict(r) for r in atom.relations]),
                    json.dumps(atom.tags),
                    atom.scope.value,
                    atom.visibility.value,
                    json.dumps(atom.subject_ids),
                    json.dumps(atom.origin),
                    atom.trust_level,
                    atom.retention_policy,
                    "pending",
                    atom.decay_rate,
                    atom.forget_at.isoformat() if atom.forget_at else None,
                    1 if atom.is_archived else 0,
                ),
            )
            # Sync FTS5 index
            row = await self._fetchone("SELECT rowid FROM memory_atoms WHERE id=?", (atom.id,))
            assert row is not None
            rowid = row[0]
            await self._execute(
                "INSERT INTO memory_fts(rowid, content, summary) VALUES (?, ?, ?)",
                (rowid, atom.content, atom.summary or ""),
            )
            revision = await self._next_revision()
            await self._enqueue_index(atom.id, "upsert", revision)
            return atom.id

    async def get(self, atom_id: str) -> MemoryAtom | None:
        async with self._database():
            return await self._get(atom_id)

    async def update(self, atom: MemoryAtom) -> None:
        async with self._database(write=True):
            await self._update(atom)

    async def _get(self, atom_id: str) -> MemoryAtom | None:
        row = await self._fetchone("SELECT * FROM memory_atoms WHERE id = ?", (atom_id,))
        if row is None:
            return None
        return self._row_to_atom(row)

    async def _update(self, atom: MemoryAtom) -> None:
        await self._execute(
            """
            UPDATE memory_atoms SET content=?, summary=?, rewritten_at=?,
                version=?, version_chain=?, confidence=?, salience=?,
                retrieval_count=?, last_accessed_at=?, emotion_valence=?,
                emotion_arousal=?, emotion_dominance=?, decay_rate=?,
                forget_at=?, is_archived=?, relations=?, tags=?, source_ids=?,
                scope=?, visibility=?, subject_ids=?, origin=?, trust_level=?,
                retention_policy=?, index_state=?
            WHERE id=?
        """,
            (
                atom.content,
                atom.summary,
                atom.rewritten_at.isoformat()
                if atom.rewritten_at
                else atom.occurred_at.isoformat(),
                atom.version,
                json.dumps(atom.version_chain),
                atom.confidence,
                atom.salience,
                atom.retrieval_count,
                atom.last_accessed_at.isoformat() if atom.last_accessed_at else None,
                atom.emotion_valence,
                atom.emotion_arousal,
                atom.emotion_dominance,
                atom.decay_rate,
                atom.forget_at.isoformat() if atom.forget_at else None,
                1 if atom.is_archived else 0,
                json.dumps([self._relation_to_dict(r) for r in atom.relations]),
                json.dumps(atom.tags),
                json.dumps(atom.source_ids),
                atom.scope.value,
                atom.visibility.value,
                json.dumps(atom.subject_ids),
                json.dumps(atom.origin),
                atom.trust_level,
                atom.retention_policy,
                "pending",
                atom.id,
            ),
        )
        # Update FTS5 index
        await self._execute(
            "UPDATE memory_fts SET content=?, summary=? WHERE rowid=("
            "SELECT rowid FROM memory_atoms WHERE id=?)",
            (atom.content, atom.summary or "", atom.id),
        )
        revision = await self._next_revision()
        await self._enqueue_index(atom.id, "upsert", revision)

    async def create_version(
        self,
        atom_id: str,
        new_summary: str,
        new_confidence: float,
        new_emotion: tuple[float, float, float],
    ) -> MemoryAtom:
        """Create a new version after reconsolidation. Saves old version to history."""
        async with self._database(write=True):
            old = await self._get(atom_id)
            if old is None:
                raise ValueError(f"Atom {atom_id} not found")

            # Save old version to history
            await self._execute(
                """
                INSERT OR REPLACE INTO memory_versions (atom_id, version, content, summary,
                    rewritten_at, emotion_valence, emotion_arousal, emotion_dominance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    atom_id,
                    old.version,
                    old.content,
                    old.summary,
                    old.rewritten_at.isoformat()
                    if old.rewritten_at
                    else old.occurred_at.isoformat(),
                    old.emotion_valence,
                    old.emotion_arousal,
                    old.emotion_dominance,
                ),
            )

            # Update with new version
            now = datetime.now(UTC)
            old.summary = new_summary
            old.confidence = new_confidence
            old.emotion_valence = new_emotion[0]
            old.emotion_arousal = new_emotion[1]
            old.emotion_dominance = new_emotion[2]
            old.version += 1
            old.version_chain = list(old.version_chain) + [atom_id]
            old.rewritten_at = now
            old.retrieval_count += 1
            old.last_accessed_at = now
            await self._update(old)
            return old

    async def get_all_active(self, limit: int = 1000) -> list[MemoryAtom]:
        """Get all non-archived atoms, ordered by salience descending."""
        async with self._database():
            rows = await self._fetchall(
                "SELECT * FROM memory_atoms WHERE is_archived = 0 ORDER BY salience DESC LIMIT ?",
                (limit,),
            )
            return [self._row_to_atom(r) for r in rows]

    async def update_salience(self, atom_id: str, salience: float) -> None:
        async with self._database(write=True):
            await self._execute(
                "UPDATE memory_atoms SET salience = ? WHERE id = ?",
                (salience, atom_id),
            )

    async def archive_below_threshold(self, threshold: float) -> int:
        """Archive all atoms with salience below threshold. Returns count."""
        async with self._database(write=True):
            cursor = await self._execute(
                "UPDATE memory_atoms SET is_archived = 1 WHERE is_archived = 0 AND salience < ?",
                (threshold,),
            )
            return cursor

    async def count_active(self) -> int:
        async with self._database():
            row = await self._fetchone(
                "SELECT COUNT(*) as cnt FROM memory_atoms WHERE is_archived = 0"
            )
            assert row is not None
            return int(row["cnt"])

    async def search_fts(self, query: str, limit: int = 50) -> list[MemoryAtom]:
        """Full-text search via FTS5. Falls back to LIKE for CJK."""
        async with self._database():
            # For CJK text — FTS5 can't tokenize, use LIKE instead
            if any("\u4e00" <= c <= "\u9fff" for c in query):
                rows = await self._fetchall(
                    "SELECT * FROM memory_atoms WHERE (content LIKE ? OR summary LIKE ?) "
                    "AND is_archived = 0 ORDER BY salience DESC LIMIT ?",
                    (f"%{query}%", f"%{query}%", limit),
                )
                return [self._row_to_atom(r) for r in rows]

            try:
                rows = await self._fetchall(
                    "SELECT a.* FROM memory_atoms a "
                    "JOIN memory_fts f ON a.rowid = f.rowid "
                    "WHERE memory_fts MATCH ? AND a.is_archived = 0 "
                    "ORDER BY rank LIMIT ?",
                    (query, limit),
                )
            except Exception:
                return []
            return [self._row_to_atom(r) for r in rows]

    async def hybrid_search(self, query: str, limit: int = 50) -> list[MemoryAtom]:
        """Hybrid search: vector (Chroma) + keyword (FTS5)."""
        results: dict[str, MemoryAtom] = {}
        scores: dict[str, float] = {}

        # Vector search
        vector_results = await self._vector_search(query, limit)
        for atom_id, score in vector_results:
            scores[atom_id] = scores.get(atom_id, 0) + 0.55 * score

        # Keyword search (FTS5)
        keyword_results = await self.search_fts(query, limit)
        for i, atom in enumerate(keyword_results):
            # BM25-like: higher rank = higher score
            kw_score = 1.0 / (1.0 + i)
            scores[atom.id] = scores.get(atom.id, 0) + 0.25 * kw_score
            results[atom.id] = atom

        # Fetch atoms not yet loaded (from vector search only)
        missing = [atom_id for atom_id in scores if atom_id not in results]
        if missing:
            async with self._database():
                placeholders = ",".join("?" for _ in missing)
                rows = await self._fetchall(
                    f"SELECT * FROM memory_atoms WHERE id IN ({placeholders}) AND is_archived=0",
                    tuple(missing),
                )
                results.update((row["id"], self._row_to_atom(row)) for row in rows)

        # Sort by combined score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [results[aid] for aid, _ in ranked if aid in results][:limit]

    # ── Serialization ──

    def _row_to_atom(self, row: aiosqlite.Row) -> MemoryAtom:
        return MemoryAtom(
            id=row["id"],
            layer=Layer(row["layer"]),
            content=row["content"],
            summary=row["summary"],
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            rewritten_at=datetime.fromisoformat(row["rewritten_at"]),
            version=row["version"],
            version_chain=json.loads(row["version_chain"]),
            confidence=row["confidence"],
            salience=row["salience"],
            retrieval_count=row["retrieval_count"],
            last_accessed_at=(
                datetime.fromisoformat(row["last_accessed_at"]) if row["last_accessed_at"] else None
            ),
            emotion_valence=row["emotion_valence"],
            emotion_arousal=row["emotion_arousal"],
            emotion_dominance=row["emotion_dominance"],
            source_ids=json.loads(row["source_ids"]),
            relations=[self._dict_to_relation(d) for d in json.loads(row["relations"])],
            tags=json.loads(row["tags"]),
            scope=MemoryScope(row["scope"]),
            visibility=MemoryVisibility(row["visibility"]),
            subject_ids=json.loads(row["subject_ids"]),
            origin=json.loads(row["origin"]),
            trust_level=row["trust_level"],
            retention_policy=row["retention_policy"],
            index_state=row["index_state"],
            decay_rate=row["decay_rate"],
            forget_at=(datetime.fromisoformat(row["forget_at"]) if row["forget_at"] else None),
            is_archived=bool(row["is_archived"]),
        )

    @staticmethod
    def _relation_to_dict(r: Relation) -> dict:
        return {
            "source_id": r.source_id,
            "target_id": r.target_id,
            "relation_type": r.relation_type,
            "created_at": r.created_at.isoformat(),
            "metadata": r.metadata,
        }

    @staticmethod
    def _dict_to_relation(d: dict) -> Relation:
        return Relation(
            source_id=d["source_id"],
            target_id=d["target_id"],
            relation_type=d["relation_type"],
            created_at=datetime.fromisoformat(d["created_at"]),
            metadata=d.get("metadata", {}),
        )
