"""PeriodicLearner coordinator — orchestrates summarizer → pattern extractor → meme discoverer pipeline."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.turns import MemoryTurn
from .summarizer import ConversationSummarizer, LearningLog
from .pattern_extractor import PatternExtractor
from .meme_discovery import MemeDiscoverer, MemeCandidate

logger = logging.getLogger(__name__)


class PeriodicLearner:
    """Coordinator for the AI learning pipeline.

    Pipeline: ConversationSummarizer → PatternExtractor → MemeDiscoverer
    Each stage feeds into the next, producing increasingly refined insights.

    Runs as scheduled task via AsyncScheduler.
    """

    def __init__(
        self,
        memory_system: MemorySystem,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._memory_system = memory_system
        self._llm_client = llm_client
        self._config = config or {}

        self._summarizer = ConversationSummarizer(
            llm_client=llm_client,
            config=config,
        )
        self._pattern_extractor = PatternExtractor(
            llm_client=llm_client,
            config=config,
        )
        self._meme_discoverer = MemeDiscoverer(
            llm_client=llm_client,
            config=config,
        )

        # Track which sessions / logs we've already processed
        self._processed_sessions: set = set()
        self._processed_log_ids: set = set()
        self._log_retention_days = config.get("log_retention_days", 90)

        # SQLite storage for learning logs + processed tracking
        self._db_path: Optional[str] = None
        self._conn: Optional[sqlite3.Connection] = None

    # ── Scheduled Tasks ─────────────────────────────────

    async def consolidate_conversations(self) -> None:
        """Scheduled task: summarize recent unconsolidated conversations.

        Reads from ShortTermMemory, runs summarization, stores results.
        """
        logger.info("[PeriodicLearner] Starting conversation consolidation...")

        try:
            self._ensure_db()
            # Get all sessions from short-term memory
            short_term = self._memory_system._short_term
            if not hasattr(short_term, '_cache'):
                logger.debug("[PeriodicLearner] ShortTermMemory has no _cache")
                return

            # Group unprocessed sessions' turns
            sessions: Dict[str, List[MemoryTurn]] = {}
            for session_id, turns in short_term._cache.items():
                if session_id not in self._processed_sessions:
                    sessions[session_id] = list(turns)
                    self._processed_sessions.add(session_id)
                    self._upsert_processed_session(session_id)

            if not sessions:
                logger.debug("[PeriodicLearner] No new sessions to consolidate")
                return

            # Run summarization
            logs = await self._summarizer.summarize_batch(sessions)
            if logs:
                self._store_logs(logs)
            logger.info(f"[PeriodicLearner] Consolidated {len(logs)} conversation summaries")

        except Exception as e:
            logger.warning(f"[PeriodicLearner] Consolidation failed: {e}", exc_info=True)

    async def extract_patterns(self) -> None:
        """Scheduled task: extract behavioral patterns from recent summaries.

        Reads recent LearningLogs (conversation type), runs pattern extraction.
        """
        logger.info("[PeriodicLearner] Starting pattern extraction...")

        try:
            self._ensure_db()
            # Get recent summaries from learner's own storage
            recent_summaries = self._get_recent_logs("conversation")
            if not recent_summaries:
                logger.debug("[PeriodicLearner] No summaries to extract patterns from")
                return

            max_patterns = self._config.get("patterns_per_run", 5)
            all_patterns: List[LearningLog] = []

            for log in recent_summaries:
                if log.id in self._processed_log_ids:
                    continue
                # Convert summary content into MemoryTurns for extraction
                turns = self._content_to_turns(log)
                if turns:
                    patterns = await self._pattern_extractor.extract_patterns(
                        turns=turns,
                        session_id=log.session_id,
                        max_patterns=max_patterns,
                    )
                    all_patterns.extend(patterns)
                self._processed_log_ids.add(log.id)

            logger.info(f"[PeriodicLearner] Extracted {len(all_patterns)} patterns from summaries")

            # Feed patterns → meme discovery
            if all_patterns:
                self._store_logs(all_patterns)
                await self._patterns_to_memes(all_patterns)

        except Exception as e:
            logger.warning(f"[PeriodicLearner] Pattern extraction failed: {e}")

    async def generate_meme_candidates(self) -> None:
        """Scheduled task: generate meme candidates from extracted patterns."""
        logger.info("[PeriodicLearner] Generating meme candidates...")

        try:
            recent_patterns = self._get_recent_logs("pattern")
            if not recent_patterns:
                logger.debug("[PeriodicLearner] No patterns to generate memes from")
                return

            await self._patterns_to_memes(recent_patterns)

        except Exception as e:
            logger.warning(f"[PeriodicLearner] Meme generation failed: {e}")

    async def prune_logs(self) -> None:
        """Scheduled task: prune old learning logs.

        Logs older than retention period are deleted.
        High-value patterns are promoted to wiki synthesis pages before deletion.
        """
        logger.info("[PeriodicLearner] Pruning old learning logs...")

        try:
            self._ensure_db()
            cutoff_ts = datetime.now().timestamp() - (self._log_retention_days * 86400)
            cutoff_iso = datetime.fromtimestamp(cutoff_ts).isoformat()

            if self._conn:
                # Delete stale processed sessions
                self._conn.execute(
                    "DELETE FROM processed_sessions WHERE processed_at < ?",
                    (cutoff_iso,),
                )
                # Delete stale learning logs
                self._conn.execute(
                    "DELETE FROM learning_logs WHERE created_at < ?",
                    (cutoff_iso,),
                )
                self._conn.commit()

            # Reload remaining sessions into memory
            self._processed_sessions = set(self._load_processed_sessions())

            # Also prune old wiki source pages
            wiki = getattr(self._memory_system, '_wiki_manager', None)
            if wiki:
                from ..wiki.models import PageType
                try:
                    for rel in wiki.list_pages(PageType.SOURCE):
                        page = wiki.read_page(rel)
                        if page and page.updated_at and page.updated_at.isoformat() < cutoff_iso:
                            path = wiki._wiki_dir / page.path
                            if path.exists():
                                path.unlink()
                                logger.info(f"[PeriodicLearner] Pruned wiki page: {page.path}")
                except Exception as e:
                    logger.debug(f"[PeriodicLearner] Wiki pruning failed: {e}")

            logger.info(
                f"[PeriodicLearner] Pruned entries older than {self._log_retention_days}d "
                f"(cutoff={cutoff_iso})"
            )

            # Promote high-confidence patterns to wiki before they're lost
            if self._memory_system and hasattr(self._memory_system, '_wiki_manager'):
                wiki = self._memory_system._wiki_manager
                if wiki and self._conn:
                    rows = self._conn.execute(
                        "SELECT * FROM learning_logs WHERE summary_type = 'pattern' AND created_at < ?",
                        (cutoff_iso,),
                    ).fetchall()
                    for row in rows:
                        try:
                            content = json.loads(row["content"]) if isinstance(row["content"], str) else row["content"]
                            if isinstance(content, dict) and content.get("confidence", 0) >= 0.8:
                                from ..wiki.models import WikiPage, PageType
                                from datetime import datetime as dt
                                page = WikiPage(
                                    title=f"学习模式: {content.get('pattern', '未知')[:30]}",
                                    page_type=PageType.SYNTHESIS,
                                    path=f"synthesis/learner-pattern-{row['id']}.md",
                                    content=f"# 学习模式\n\n{content.get('pattern', '')}\n\n"
                                            f"**置信度**: {content.get('confidence', 0)}\n"
                                            f"**类别**: {content.get('category', 'unknown')}\n"
                                            f"**来源**: PeriodicLearner\n",
                                    tags=["learner", "pattern", dt.now().strftime("%Y-%m-%d")],
                                    links=[],
                                    created_at=dt.now(),
                                    updated_at=dt.now(),
                                )
                                wiki.write_page(page)
                                logger.info(f"[PeriodicLearner] Promoted pattern to wiki: {row['id']}")
                        except Exception as e:
                            logger.debug(f"[PeriodicLearner] Pattern promotion failed: {e}")

        except Exception as e:
            logger.warning(f"[PeriodicLearner] Log pruning failed: {e}")

    # ── Pipeline helpers ─────────────────────────────────

    async def _patterns_to_memes(self, patterns: List[LearningLog]) -> None:
        """Feed patterns into meme discoverer."""
        max_candidates = self._config.get("meme_candidates_per_run", 3)

        candidates = await self._meme_discoverer.discover_candidates(
            patterns=patterns,
            max_candidates=max_candidates,
        )

        if candidates:
            logger.info(f"[PeriodicLearner] Generated {len(candidates)} meme candidates")
            # Store candidates — they'll be picked up by MemePool
            self._store_meme_candidates(candidates)

    def _store_meme_candidates(self, candidates: List[MemeCandidate]) -> None:
        """Store meme candidates for MemePool to consume."""
        logs: List[LearningLog] = []
        for c in candidates:
            log = LearningLog(
                id=f"meme_candidate_{uuid.uuid4().hex[:8]}",
                summary_type="meme_candidate",
                content=json.dumps({
                    "text": c.text,
                    "context_hint": c.context_hint,
                    "confidence": c.confidence,
                    "tags": c.tags,
                }, ensure_ascii=False),
            )
            logs.append(log)
            logger.info(f"[PeriodicLearner] Meme candidate: '{c.text}' (confidence={c.confidence:.2f})")
        if logs:
            self._store_logs(logs)

    # ── SQLite storage ───────────────────────────────────

    def _ensure_db(self) -> None:
        """Open SQLite connection and create tables if not yet initialized."""
        if self._conn is not None:
            return

        ws = self._config.get("workspace_dir")
        if ws:
            db_path = str(Path(ws) / "learner.sqlite")
        else:
            db_path = ":memory:"
        self._db_path = db_path

        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS learning_logs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL DEFAULT '',
                summary_type TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                source_ids TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS processed_sessions (
                session_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_ll_type ON learning_logs(summary_type);
            CREATE INDEX IF NOT EXISTS idx_ll_created ON learning_logs(created_at);
        """)
        self._conn.commit()

        # Reload processed sessions from DB
        self._processed_sessions = set(self._load_processed_sessions())
        logger.info(f"[PeriodicLearner] Storage ready at {db_path} "
                    f"({len(self._processed_sessions)} tracked sessions)")

    def _store_logs(self, logs: List[LearningLog]) -> None:
        """Batch-insert learning logs into SQLite."""
        if not logs or not self._conn:
            return
        now = datetime.now().isoformat()
        for log in logs:
            self._conn.execute(
                """INSERT OR IGNORE INTO learning_logs
                   (id, session_id, summary_type, content, source_ids, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    log.id,
                    log.session_id,
                    log.summary_type,
                    log.content,
                    log.source_ids,
                    log.created_at.isoformat() if log.created_at else now,
                ),
            )
        self._conn.commit()

    def _get_recent_logs(self, log_type: str, limit: int = 50) -> List[LearningLog]:
        """Get recent learning logs of a given type from SQLite."""
        if not self._conn:
            return []
        rows = self._conn.execute(
            "SELECT * FROM learning_logs WHERE summary_type = ? ORDER BY created_at DESC LIMIT ?",
            (log_type, limit),
        ).fetchall()
        return [self._row_to_learninglog(r) for r in rows]

    @staticmethod
    def _row_to_learninglog(row: sqlite3.Row) -> LearningLog:
        created = row["created_at"]
        return LearningLog(
            id=row["id"],
            session_id=row["session_id"],
            summary_type=row["summary_type"],
            content=row["content"],
            source_ids=row["source_ids"],
            created_at=datetime.fromisoformat(created) if created else None,
        )

    @staticmethod
    def _content_to_turns(log: LearningLog) -> List[MemoryTurn]:
        """Convert a LearningLog's stored source_ids back to MemoryTurns."""
        if not log or not log.source_ids:
            return []
        try:
            from ..models.turns import MemoryTurn as _MT
            from datetime import datetime as _dt
            turn_ids = json.loads(log.source_ids) if isinstance(log.source_ids, str) else log.source_ids
            return [
                _MT(
                    turn_id=tid,
                    session_id=log.session_id,
                    timestamp=_dt.now(),
                ) for tid in turn_ids if tid
            ]
        except (json.JSONDecodeError, TypeError):
            return []

    def _load_processed_sessions(self) -> List[str]:
        """Load processed session IDs from DB."""
        if not self._conn:
            return []
        rows = self._conn.execute(
            "SELECT session_id FROM processed_sessions ORDER BY processed_at ASC",
        ).fetchall()
        return [r["session_id"] for r in rows]

    def _upsert_processed_session(self, session_id: str) -> None:
        """Record a session as having been processed."""
        if not self._conn:
            return
        self._conn.execute(
            """INSERT OR REPLACE INTO processed_sessions (session_id, processed_at)
               VALUES (?, ?)""",
            (session_id, datetime.now().isoformat()),
        )
        self._conn.commit()

    # ── Lifecycle ────────────────────────────────────────

    async def start(self) -> None:
        self._ensure_db()
        logger.info("[PeriodicLearner] Started")

    async def stop(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
        logger.info("[PeriodicLearner] Stopped")
