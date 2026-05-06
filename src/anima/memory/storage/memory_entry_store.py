"""
MemoryEntry storage layer.

Wraps all operations for the memory_entries and memory_relations SQLite tables,
including CRUD, version chain queries, relation queries, and expiration cleanup.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from ..models.memory_entry import MemoryEntry, MemoryRelation, RelationType

logger = logging.getLogger(__name__)


class MemoryEntryStore:
    """MemoryEntry + MemoryRelation storage wrapper."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ── DDL ───────────────────────────────────────────────────

    @staticmethod
    def ddl() -> str:
        """Returns DDL for creating memory_entries and memory_relations tables.

        Called by SQLiteStore._create_tables() during initialization.
        """
        return """
        CREATE TABLE IF NOT EXISTS memory_entries (
            id                TEXT PRIMARY KEY,
            memory            TEXT NOT NULL,
            space_id          TEXT NOT NULL,
            version           INTEGER NOT NULL DEFAULT 1,
            is_latest         INTEGER NOT NULL DEFAULT 1,
            is_static         INTEGER NOT NULL DEFAULT 0,
            is_forgotten      INTEGER NOT NULL DEFAULT 0,
            forget_after      TEXT,
            parent_memory_id  TEXT,
            root_memory_id    TEXT,
            confidence        REAL NOT NULL DEFAULT 1.0,
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_mem_latest ON memory_entries(space_id, is_latest);
        CREATE INDEX IF NOT EXISTS idx_mem_root ON memory_entries(root_memory_id);
        CREATE INDEX IF NOT EXISTS idx_mem_forgotten ON memory_entries(is_forgotten);

        CREATE TABLE IF NOT EXISTS memory_relations (
            source_id   TEXT NOT NULL,
            target_id   TEXT NOT NULL,
            relation    TEXT NOT NULL CHECK(relation IN ('updates', 'extends', 'derives')),
            created_at  TEXT NOT NULL,
            PRIMARY KEY (source_id, target_id, relation)
        );

        CREATE INDEX IF NOT EXISTS idx_rel_target ON memory_relations(target_id);
        """

    # ── MemoryEntry CRUD ──────────────────────────────────────

    def create(self, entry: MemoryEntry) -> str:
        """Create a new memory entry.

        Auto-generates UUID if entry.id is empty.
        """
        now = datetime.now(timezone.utc).isoformat()
        entry_id = entry.id or str(uuid.uuid4())
        root_id = entry.root_memory_id or entry_id  # Root version points to itself

        self.conn.execute(
            """
            INSERT INTO memory_entries
                (id, memory, space_id, version, is_latest, is_static,
                 is_forgotten, forget_after, parent_memory_id, root_memory_id,
                 confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id, entry.memory, entry.space_id, entry.version,
                int(entry.is_latest), int(entry.is_static),
                int(entry.is_forgotten), entry.forget_after,
                entry.parent_memory_id, root_id,
                entry.confidence, now, now,
            ),
        )
        self.conn.commit()
        logger.debug(f"[MemoryEntryStore] created: {entry_id}")
        return entry_id

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get memory entry by ID."""
        row = self.conn.execute(
            "SELECT * FROM memory_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def get_latest_by_memory(self, memory: str, space_id: str) -> Optional[MemoryEntry]:
        """Find latest version by fact text and space."""
        row = self.conn.execute(
            "SELECT * FROM memory_entries WHERE memory = ? AND space_id = ? AND is_latest = 1",
            (memory, space_id),
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def search_by_space(self, space_id: str, query: str = "", limit: int = 20) -> List[MemoryEntry]:
        """Search latest/unforgotten memories by space.

        Supports optional fuzzy matching of memory text.
        """
        if query:
            rows = self.conn.execute(
                """
                SELECT * FROM memory_entries
                WHERE space_id = ? AND is_latest = 1 AND is_forgotten = 0
                  AND memory LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (space_id, f"%{query}%", limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT * FROM memory_entries
                WHERE space_id = ? AND is_latest = 1 AND is_forgotten = 0
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (space_id, limit),
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def update(self, entry: MemoryEntry) -> bool:
        """Update memory entry (metadata update)."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            """
            UPDATE memory_entries SET
                memory = ?, version = ?, is_latest = ?, is_static = ?,
                is_forgotten = ?, forget_after = ?, parent_memory_id = ?,
                root_memory_id = ?, confidence = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                entry.memory, entry.version, int(entry.is_latest),
                int(entry.is_static), int(entry.is_forgotten),
                entry.forget_after, entry.parent_memory_id,
                entry.root_memory_id, entry.confidence, now,
                entry.id,
            ),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, entry_id: str) -> bool:
        """Hard delete a memory entry."""
        cur = self.conn.execute(
            "DELETE FROM memory_entries WHERE id = ?", (entry_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    # ── Version chain ──────────────────────────────────────────

    def create_new_version(self, entry: MemoryEntry, old_entry_id: str) -> str:
        """Create new version: mark old version as non-latest, insert new version.

        Args:
            entry: New MemoryEntry (version should be > old version)
            old_entry_id: ID of the old version being superseded

        Returns:
            New version ID
        """
        old = self.get(old_entry_id)
        if old is None:
            logger.warning(f"[MemoryEntryStore] old version not found: {old_entry_id}")
            return self.create(entry)

        # Mark old version as non-latest
        self.conn.execute(
            "UPDATE memory_entries SET is_latest = 0, updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), old_entry_id),
        )

        # Link new version to old version
        entry.parent_memory_id = old_entry_id
        entry.root_memory_id = old.root_memory_id or old_entry_id
        entry.is_latest = True

        new_id = self.create(entry)
        return new_id

    def get_version_chain(self, root_memory_id: str) -> List[MemoryEntry]:
        """Get full version chain, sorted by version ASC."""
        rows = self.conn.execute(
            """
            SELECT * FROM memory_entries
            WHERE root_memory_id = ?
            ORDER BY version ASC
            """,
            (root_memory_id,),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    # ── Expiration cleanup ─────────────────────────────────────

    def expire_old(self) -> int:
        """Mark all non-forgotten memories with forget_after < now as forgotten.

        Returns:
            Number of processed records
        """
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            """
            UPDATE memory_entries
            SET is_forgotten = 1, updated_at = ?
            WHERE is_forgotten = 0 AND forget_after IS NOT NULL AND forget_after < ?
            """,
            (now, now),
        )
        self.conn.commit()
        count = cur.rowcount
        if count:
            logger.info(f"[MemoryEntryStore] expired {count} old entries")
        return count

    # ── MemoryRelation CRUD ───────────────────────────────────

    def add_relation(self, relation: MemoryRelation) -> bool:
        """Add a relation record."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO memory_relations (source_id, target_id, relation, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (relation.source_id, relation.target_id, relation.relation.value, now),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"[MemoryEntryStore] add_relation failed: {e}")
            return False

    def get_relations(self, entry_id: str) -> List[MemoryRelation]:
        """Get all relations associated with the given entry (source or target)."""
        rows = self.conn.execute(
            """
            SELECT * FROM memory_relations
            WHERE source_id = ? OR target_id = ?
            ORDER BY created_at DESC
            """,
            (entry_id, entry_id),
        ).fetchall()
        return [self._row_to_relation(r) for r in rows]

    def get_related_entries(self, entry_id: str) -> List[Tuple[MemoryEntry, RelationType]]:
        """Get sibling entries related to the given entry along with relation type."""
        rows = self.conn.execute(
            """
            SELECT me.*, mr.relation
            FROM memory_relations mr
            JOIN memory_entries me ON (
                (mr.source_id = ? AND me.id = mr.target_id)
                OR (mr.target_id = ? AND me.id = mr.source_id)
            )
            WHERE me.is_latest = 1 AND me.is_forgotten = 0
            """,
            (entry_id, entry_id),
        ).fetchall()
        result: List[Tuple[MemoryEntry, RelationType]] = []
        for r in rows:
            entry = self._row_to_entry(r)
            rel = RelationType(r["relation"])
            result.append((entry, rel))
        return result

    def delete_relations_for_entry(self, entry_id: str) -> int:
        """Delete all relations associated with the given entry (hard delete)."""
        cur = self.conn.execute(
            "DELETE FROM memory_relations WHERE source_id = ? OR target_id = ?",
            (entry_id, entry_id),
        )
        self.conn.commit()
        return cur.rowcount

    # ── Batch operations ───────────────────────────────────────

    def get_all_latest(self, space_id: str, limit: int = 100) -> List[MemoryEntry]:
        """Get all latest and unforgotten memories within a space."""
        rows = self.conn.execute(
            """
            SELECT * FROM memory_entries
            WHERE space_id = ? AND is_latest = 1 AND is_forgotten = 0
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (space_id, limit),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def count_by_space(self, space_id: str) -> int:
        """Count memory entries in a space."""
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM memory_entries WHERE space_id = ?",
            (space_id,),
        ).fetchone()
        return row["cnt"] if row else 0

    # ── Internal helpers ────────────────────────────────────────

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            memory=row["memory"],
            space_id=row["space_id"],
            version=row["version"],
            is_latest=bool(row["is_latest"]),
            is_static=bool(row["is_static"]),
            is_forgotten=bool(row["is_forgotten"]),
            forget_after=row["forget_after"],
            parent_memory_id=row["parent_memory_id"],
            root_memory_id=row["root_memory_id"],
            confidence=row["confidence"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_relation(row: sqlite3.Row) -> MemoryRelation:
        return MemoryRelation(
            source_id=row["source_id"],
            target_id=row["target_id"],
            relation=RelationType(row["relation"]),
            created_at=row["created_at"],
        )
