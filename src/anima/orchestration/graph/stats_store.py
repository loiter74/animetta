"""Pipeline stats data storage - SQLite"""

import asyncio
import aiosqlite
from typing import Optional, Dict, Any, List
from pathlib import Path
from loguru import logger


class StatsStore:
    """SQLite stats storage"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(
                Path(__file__).parent.parent.parent.parent.parent / "data" / "stats.db"
            )
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._write_lock = asyncio.Lock()

    async def init(self):
        """Initialize database connection and table structure"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        # WAL mode allows concurrent reads + single writer; busy_timeout retries instead of failing
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA busy_timeout=5000")
        await self._create_tables()
        await self._migrate_schema()
        logger.info(f"[StatsStore] Database initialized: {self.db_path}")

    async def _migrate_schema(self):
        """Add OTel columns to spans table (safe for existing DBs)."""
        migrations = [
            "ALTER TABLE spans ADD COLUMN attributes TEXT",
            "ALTER TABLE spans ADD COLUMN events TEXT",
            "ALTER TABLE spans ADD COLUMN kind INTEGER",
        ]
        for sql in migrations:
            try:
                await self._db.execute(sql)
                await self._db.commit()
            except Exception:
                pass  # column already exists

    async def _create_tables(self):
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                session_id TEXT,
                input_type TEXT,
                user_text TEXT,
                total_duration_ms REAL,
                status TEXT DEFAULT 'running',
                error_msg TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS spans (
                span_id TEXT PRIMARY KEY,
                trace_id TEXT REFERENCES traces(trace_id),
                parent_span_id TEXT,
                node_name TEXT,
                duration_ms REAL,
                status TEXT DEFAULT 'running',
                input_summary TEXT,
                output_summary TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
            CREATE INDEX IF NOT EXISTS idx_spans_node ON spans(node_name);
        """)
        await self._db.commit()

    async def create_trace(
        self, trace_id: str, session_id: str, input_type: str, user_text: str
    ) -> None:
        truncated = user_text[:100] if user_text else ""
        async with self._write_lock:
            await self._db.execute(
                "INSERT INTO traces (trace_id, session_id, input_type, user_text) VALUES (?, ?, ?, ?)",
                (trace_id, session_id, input_type, truncated),
            )
            await self._db.commit()

    async def finish_trace(
        self,
        trace_id: str,
        total_duration_ms: float,
        status: str = "success",
        error_msg: str = None,
    ) -> None:
        async with self._write_lock:
            await self._db.execute(
                "UPDATE traces SET total_duration_ms=?, status=?, error_msg=? WHERE trace_id=?",
                (total_duration_ms, status, error_msg, trace_id),
            )
            await self._db.commit()

    async def create_span(
        self,
        span_id: str,
        trace_id: str,
        node_name: str,
        parent_span_id: str = None,
        input_summary: str = None,
    ) -> None:
        async with self._write_lock:
            await self._db.execute(
                "INSERT INTO spans (span_id, trace_id, parent_span_id, node_name, input_summary) VALUES (?, ?, ?, ?, ?)",
                (span_id, trace_id, parent_span_id, node_name, input_summary),
            )
            await self._db.commit()

    async def finish_span(
        self,
        span_id: str,
        duration_ms: float,
        status: str = "success",
        output_summary: str = None,
    ) -> None:
        async with self._write_lock:
            await self._db.execute(
                "UPDATE spans SET duration_ms=?, status=?, output_summary=? WHERE span_id=?",
                (duration_ms, status, output_summary, span_id),
            )
            await self._db.commit()

    async def get_overview(self) -> Dict[str, Any]:
        cursor = await self._db.execute("""
            SELECT
                COUNT(*) as total_requests,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success_count,
                AVG(total_duration_ms) as avg_duration
            FROM traces
        """)
        row = await cursor.fetchone()

        total = row[0] or 0
        success = row[1] or 0

        p95_cursor = await self._db.execute("""
            SELECT total_duration_ms FROM traces
            WHERE status='success' AND total_duration_ms IS NOT NULL
            ORDER BY total_duration_ms DESC
            LIMIT 1 OFFSET (
                SELECT COUNT(*) * 5 / 100
                FROM traces
                WHERE status='success' AND total_duration_ms IS NOT NULL
            )
        """)
        p95_row = await p95_cursor.fetchone()

        return {
            "total_requests": total,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
            "avg_duration_ms": round(row[2], 1) if row[2] else 0,
            "p95_duration_ms": round(p95_row[0], 1) if p95_row else 0,
        }

    async def get_node_stats(self) -> List[Dict[str, Any]]:
        cursor = await self._db.execute("""
            SELECT
                node_name,
                COUNT(*) as call_count,
                AVG(duration_ms) as avg_duration_ms,
                MIN(duration_ms) as min_duration_ms,
                MAX(duration_ms) as max_duration_ms,
                SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as error_count
            FROM spans
            WHERE duration_ms IS NOT NULL
            GROUP BY node_name
            ORDER BY avg_duration_ms DESC
        """)
        rows = await cursor.fetchall()
        return [
            {
                "node_name": row[0],
                "call_count": row[1],
                "avg_duration_ms": round(row[2], 1),
                "min_duration_ms": round(row[3], 1),
                "max_duration_ms": round(row[4], 1),
                "error_count": row[5],
                "error_rate": round(row[5] / row[1] * 100, 1) if row[1] > 0 else 0,
            }
            for row in rows
        ]

    async def get_recent_traces(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        cursor = await self._db.execute(
            "SELECT trace_id, session_id, input_type, user_text, total_duration_ms, status, created_at "
            "FROM traces ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            {
                "trace_id": row[0],
                "session_id": row[1],
                "input_type": row[2],
                "user_text": row[3],
                "total_duration_ms": row[4],
                "status": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]

    async def get_trace_detail(self, trace_id: str) -> Optional[Dict[str, Any]]:
        cursor = await self._db.execute(
            "SELECT trace_id, session_id, input_type, user_text, total_duration_ms, status, error_msg, created_at "
            "FROM traces WHERE trace_id=?",
            (trace_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        span_cursor = await self._db.execute(
            "SELECT span_id, parent_span_id, node_name, duration_ms, status, "
            "input_summary, output_summary, attributes, events, kind, created_at "
            "FROM spans WHERE trace_id=? ORDER BY created_at",
            (trace_id,),
        )
        spans = [
            {
                "span_id": s[0],
                "parent_span_id": s[1],
                "node_name": s[2],
                "duration_ms": s[3],
                "status": s[4],
                "input_summary": s[5],
                "output_summary": s[6],
                "attributes": s[7],
                "events": s[8],
                "kind": s[9],
                "created_at": s[10],
            }
            for s in await span_cursor.fetchall()
        ]

        return {
            "trace_id": row[0],
            "session_id": row[1],
            "input_type": row[2],
            "user_text": row[3],
            "total_duration_ms": row[4],
            "status": row[5],
            "error_msg": row[6],
            "created_at": row[7],
            "spans": spans,
        }

    async def close(self):
        if self._db:
            await self._db.close()


# Global singleton (with async lock to prevent race conditions)
_store: Optional[StatsStore] = None
_store_lock = asyncio.Lock()


async def get_stats_store() -> StatsStore:
    global _store
    if _store is not None:
        return _store
    async with _store_lock:
        if _store is None:
            _store = StatsStore()
            await _store.init()
    return _store
