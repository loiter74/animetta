"""AtomStore — unified persistence layer for MemoryAtoms.

SQLite for structured data + FTS5 for full-text search.
Chroma integration for vector search (future).
Wiki export layer for human-readable backups.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from animetta.memory.v2.atom import MemoryAtom, Layer, Relation


class AtomStore:
    """Unified persistence for MemoryAtoms.

    Replaces MemoryEntryStore + WikiManager with a single store.
    Reuses existing SQLite patterns from storage/sqlite.py.
    """

    def __init__(self, db_path: str = "memory_db/living_memory.sqlite"):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    async def initialize(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self) -> None:
        self._conn.executescript("""
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
                decay_rate REAL DEFAULT 0.1,
                forget_at TEXT,
                is_archived INTEGER DEFAULT 0
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                content, summary, content='memory_atoms', content_rowid='rowid'
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
        """)

    # ── CRUD ──

    async def create(self, atom: MemoryAtom) -> str:
        self._conn.execute("""
            INSERT INTO memory_atoms (id, layer, content, summary, occurred_at,
                rewritten_at, version, version_chain, confidence, salience,
                retrieval_count, last_accessed_at, emotion_valence, emotion_arousal,
                emotion_dominance, source_ids, relations, tags, decay_rate,
                forget_at, is_archived)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            atom.id, atom.layer.value, atom.content, atom.summary,
            atom.occurred_at.isoformat(), atom.rewritten_at.isoformat(),
            atom.version, json.dumps(atom.version_chain),
            atom.confidence, atom.salience, atom.retrieval_count,
            atom.last_accessed_at.isoformat() if atom.last_accessed_at else None,
            atom.emotion_valence, atom.emotion_arousal, atom.emotion_dominance,
            json.dumps(atom.source_ids),
            json.dumps([self._relation_to_dict(r) for r in atom.relations]),
            json.dumps(atom.tags), atom.decay_rate,
            atom.forget_at.isoformat() if atom.forget_at else None,
            1 if atom.is_archived else 0,
        ))
        self._conn.commit()
        return atom.id

    async def get(self, atom_id: str) -> MemoryAtom | None:
        row = self._conn.execute(
            "SELECT * FROM memory_atoms WHERE id = ?", (atom_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_atom(row)

    async def update(self, atom: MemoryAtom) -> None:
        self._conn.execute("""
            UPDATE memory_atoms SET content=?, summary=?, rewritten_at=?,
                version=?, version_chain=?, confidence=?, salience=?,
                retrieval_count=?, last_accessed_at=?, emotion_valence=?,
                emotion_arousal=?, emotion_dominance=?, decay_rate=?,
                forget_at=?, is_archived=?, relations=?, tags=?, source_ids=?
            WHERE id=?
        """, (
            atom.content, atom.summary, atom.rewritten_at.isoformat(),
            atom.version, json.dumps(atom.version_chain),
            atom.confidence, atom.salience, atom.retrieval_count,
            atom.last_accessed_at.isoformat() if atom.last_accessed_at else None,
            atom.emotion_valence, atom.emotion_arousal, atom.emotion_dominance,
            atom.decay_rate,
            atom.forget_at.isoformat() if atom.forget_at else None,
            1 if atom.is_archived else 0,
            json.dumps([self._relation_to_dict(r) for r in atom.relations]),
            json.dumps(atom.tags), json.dumps(atom.source_ids),
            atom.id,
        ))
        self._conn.commit()

    async def create_version(
        self, atom_id: str, new_summary: str,
        new_confidence: float, new_emotion: tuple[float, float, float],
    ) -> MemoryAtom:
        """Create a new version after reconsolidation. Saves old version to history."""
        old = await self.get(atom_id)
        if old is None:
            raise ValueError(f"Atom {atom_id} not found")

        # Save old version to history
        self._conn.execute("""
            INSERT OR REPLACE INTO memory_versions (atom_id, version, content, summary,
                rewritten_at, emotion_valence, emotion_arousal, emotion_dominance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (atom_id, old.version, old.content, old.summary,
              old.rewritten_at.isoformat(),
              old.emotion_valence, old.emotion_arousal, old.emotion_dominance))

        # Update with new version
        now = datetime.now(timezone.utc)
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
        await self.update(old)
        return old

    async def get_all_active(self, limit: int = 1000) -> list[MemoryAtom]:
        """Get all non-archived atoms, ordered by salience descending."""
        rows = self._conn.execute(
            "SELECT * FROM memory_atoms WHERE is_archived = 0 "
            "ORDER BY salience DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_atom(r) for r in rows]

    async def update_salience(self, atom_id: str, salience: float) -> None:
        self._conn.execute(
            "UPDATE memory_atoms SET salience = ? WHERE id = ?",
            (salience, atom_id),
        )
        self._conn.commit()

    async def archive_below_threshold(self, threshold: float) -> int:
        """Archive all atoms with salience below threshold. Returns count."""
        cursor = self._conn.execute(
            "UPDATE memory_atoms SET is_archived = 1 "
            "WHERE is_archived = 0 AND salience < ?",
            (threshold,),
        )
        self._conn.commit()
        return cursor.rowcount

    async def count_active(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM memory_atoms WHERE is_archived = 0"
        ).fetchone()
        return row["cnt"]

    async def search_fts(self, query: str, limit: int = 50) -> list[MemoryAtom]:
        """Full-text search via FTS5."""
        rows = self._conn.execute(
            "SELECT a.* FROM memory_atoms a "
            "JOIN memory_fts f ON a.rowid = f.rowid "
            "WHERE memory_fts MATCH ? AND a.is_archived = 0 "
            "ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [self._row_to_atom(r) for r in rows]

    # ── Serialization ──

    def _row_to_atom(self, row: sqlite3.Row) -> MemoryAtom:
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
                datetime.fromisoformat(row["last_accessed_at"])
                if row["last_accessed_at"] else None
            ),
            emotion_valence=row["emotion_valence"],
            emotion_arousal=row["emotion_arousal"],
            emotion_dominance=row["emotion_dominance"],
            source_ids=json.loads(row["source_ids"]),
            relations=[
                self._dict_to_relation(d)
                for d in json.loads(row["relations"])
            ],
            tags=json.loads(row["tags"]),
            decay_rate=row["decay_rate"],
            forget_at=(
                datetime.fromisoformat(row["forget_at"])
                if row["forget_at"] else None
            ),
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
