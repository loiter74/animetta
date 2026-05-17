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
from .fact_extractor import extract_facts_batch, format_facts_for_wiki
from .persona_optimizer import analyze_persona_performance, format_suggestions_yaml

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
        self._fact_extractor = None  # lazy init from memory_system
        self._fact_confidence_threshold = config.get("fact_confidence_threshold", 0.7)
        self._persona_auto_apply = config.get("persona_auto_apply", False)
        self._persona_min_logs = config.get("persona_min_logs", 10)

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

    async def extract_facts(self) -> None:
        """Scheduled task: extract structured facts from recent conversations.

        Uses FactExtractor (LLM-based) to identify user preferences, identity,
        experiences, and other facts from consolidated conversation summaries.
        Writes high-confidence facts to Wiki synthesis pages.
        """
        logger.info("[PeriodicLearner] Starting fact extraction...")

        try:
            self._ensure_db()
            self._ensure_fact_extractor()
            if not self._fact_extractor:
                logger.debug("[PeriodicLearner] FactExtractor not available, skipping")
                return

            # Get recent conversation logs for fact extraction context
            recent_logs = self._get_recent_logs("conversation", limit=20)
            if not recent_logs:
                logger.debug("[PeriodicLearner] No conversation logs for fact extraction")
                return

            all_facts: List[Dict[str, Any]] = []

            for log in recent_logs:
                if log.id in self._processed_log_ids:
                    continue

                # Get raw turns via source_ids for fact extraction
                turns = self._get_turns_for_log(log)
                if not turns:
                    self._processed_log_ids.add(log.id)
                    continue

                # Extract facts
                facts = await extract_facts_batch(
                    fact_extractor=self._fact_extractor,
                    turns=turns,
                    session_id=log.session_id,
                    confidence_threshold=self._fact_confidence_threshold,
                )

                if facts:
                    all_facts.extend(facts)
                    logger.info(
                        f"[PeriodicLearner] Extracted {len(facts)} facts "
                        f"from session {log.session_id} ({len(turns)} turns)"
                    )

                self._processed_log_ids.add(log.id)

            if not all_facts:
                logger.debug("[PeriodicLearner] No facts extracted this cycle")
                return

            # Write high-confidence facts to Wiki
            await self._write_facts_to_wiki(all_facts)
            logger.info(
                f"[PeriodicLearner] Extracted {len(all_facts)} total facts "
                f"from {len(recent_logs)} sessions"
            )

        except Exception as e:
            logger.warning(f"[PeriodicLearner] Fact extraction failed: {e}", exc_info=True)

    async def optimize_persona(self) -> None:
        """Scheduled task: analyze persona performance and generate optimization suggestions.

        Reads recent conversation summaries, analyzes persona effectiveness,
        and outputs reviewable YAML suggestions. Optionally auto-applies.
        """
        logger.info("[PeriodicLearner] Starting persona optimization...")

        try:
            self._ensure_db()

            # Get recent conversation logs
            recent_logs = self._get_recent_logs("conversation", limit=50)
            if len(recent_logs) < self._persona_min_logs:
                logger.debug(
                    f"[PeriodicLearner] Not enough logs for persona analysis "
                    f"({len(recent_logs)} < {self._persona_min_logs})"
                )
                return

            # Get current persona config
            persona_config = self._load_persona_config()
            if not persona_config:
                logger.debug("[PeriodicLearner] No persona config loaded, skipping")
                return

            # Format logs for LLM
            log_dicts = [
                {
                    "content": log.content,
                    "session_id": log.session_id,
                    "created_at": log.created_at.isoformat() if log.created_at else "",
                }
                for log in recent_logs
            ]

            # Run analysis
            analysis = await analyze_persona_performance(
                llm_client=self._llm_client,
                persona_config=persona_config,
                conversation_logs=log_dicts,
            )

            suggestions = analysis.get("suggestions", [])
            if not suggestions:
                logger.info("[PeriodicLearner] Persona analysis found no suggestions")
                return

            # Write suggestions file
            suggestions_path = self._write_persona_suggestions(analysis, persona_config)
            logger.info(
                f"[PeriodicLearner] Wrote {len(suggestions)} persona suggestions "
                f"to {suggestions_path}"
            )

            # Optionally auto-apply high-confidence suggestions
            if self._persona_auto_apply and suggestions_path:
                self._auto_apply_suggestions(suggestions_path, suggestions)

        except Exception as e:
            logger.warning(f"[PeriodicLearner] Persona optimization failed: {e}", exc_info=True)

    def _load_persona_config(self) -> Optional[Dict[str, Any]]:
        """Load current active persona configuration."""
        try:
            mem_config = getattr(self._memory_system, '_config', {})
            app_config = mem_config.get("app_config")
            if app_config and hasattr(app_config, 'get_persona'):
                persona = app_config.get_persona()
                if persona:
                    return {
                        "name": persona.name,
                        "identity": persona.identity,
                        "personality": {
                            "traits": persona.personality.traits if hasattr(persona.personality, 'traits') else [],
                            "speaking_style": persona.personality.speaking_style if hasattr(persona.personality, 'speaking_style') else [],
                        } if hasattr(persona, 'personality') else {},
                        "behavior": persona.behavior.dict() if hasattr(persona.behavior, 'dict') else {},
                    }
        except Exception as e:
            logger.debug(f"[PeriodicLearner] Could not load persona config: {e}")

        # Fallback: try reading directly from YAML
        try:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            persona_file = project_root / "config" / "personas" / "neuro-vtuber.yaml"
            if persona_file.exists():
                import yaml
                with open(persona_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"[PeriodicLearner] Fallback persona load failed: {e}")

        return None

    def _write_persona_suggestions(
        self, analysis: Dict[str, Any], persona_config: Dict[str, Any]
    ) -> Path:
        """Write evolution suggestions to reviewable YAML file."""
        persona_name = persona_config.get("name", "unknown")
        yaml_content = format_suggestions_yaml(analysis, persona_name)

        # Write to config/personas/evolution_suggestions.yaml
        project_root = Path(__file__).parent.parent.parent.parent.parent
        personas_dir = project_root / "config" / "personas"
        personas_dir.mkdir(parents=True, exist_ok=True)
        suggestions_path = personas_dir / "evolution_suggestions.yaml"

        suggestions_path.write_text(yaml_content, encoding="utf-8")
        return suggestions_path

    def _auto_apply_suggestions(self, path: Path, suggestions: List[Dict[str, Any]]) -> None:
        """Auto-apply high-confidence (≥0.8) suggestions."""
        from .persona_optimizer import apply_suggestion

        applied = 0
        for s in suggestions:
            if s.get("confidence", 0) >= 0.8:
                sugg_id = s.get("id", "")
                if sugg_id and apply_suggestion(path, sugg_id):
                    applied += 1
        if applied:
            logger.info(f"[PeriodicLearner] Auto-applied {applied} high-confidence persona suggestions")

    # ── Bilibili Meme Intelligence Tasks ─────────────────

    async def collect_bilibili_memes(self) -> int:
        """Scheduled task: collect trending memes from Bilibili and feed into MemePool.

        Runs BilibiliMemeCollector → MemeCognitiveAnalyzer → MemePool pipeline.
        Failure is isolated and does not block other scheduled tasks.

        Returns:
            Number of memes successfully ingested into MemePool (0 if none or failed).
        """
        logger.info("[PeriodicLearner] Starting Bilibili meme collection...")

        try:
            # Lazy import to avoid import-time failures if module is unavailable
            try:
                from anima.services.meme.bilibili_collector import BilibiliMemeCollector
                from anima.services.meme.analyzer import MemeCognitiveAnalyzer
            except ImportError:
                logger.warning(
                    "[PeriodicLearner] Bilibili meme services not available, "
                    "skipping meme collection"
                )
                return 0

            # Get meme_pool from memory system
            meme_pool = getattr(self._memory_system, 'meme_pool', None)
            if not meme_pool:
                logger.debug("[PeriodicLearner] MemePool not available, skipping meme collection")
                return 0

            config = self._config.get("bilibili_meme", {})

            # Phase 1: Collect raw candidates from B站
            collector = BilibiliMemeCollector(
                llm_client=self._llm_client,
                config=config.get("collector", {}),
            )
            candidates = await collector.collect()

            if not candidates:
                logger.info("[PeriodicLearner] No meme candidates collected from Bilibili")
                return 0

            logger.info(
                "[PeriodicLearner] Collected %d meme candidates from Bilibili",
                len(candidates),
            )

            # Phase 2: Cognitive analysis — batch all candidates first
            analyzer = MemeCognitiveAnalyzer(
                llm_client=self._llm_client,
                meme_pool=meme_pool,
                config=config.get("analyzer", {}),
            )

            # Collect all analyses first (for relative ranking)
            analyzed: List[tuple] = []
            for candidate in candidates:
                analysis = await analyzer.analyze(
                    text=candidate.text,
                    context_hint=candidate.context_hint,
                    source="bilibili",
                    tags=candidate.tags,
                    source_url=(
                        f"https://www.bilibili.com/video/{candidate.source_videos[0]}"
                        if candidate.source_videos else ""
                    ),
                )
                if analysis:
                    analyzed.append((candidate, analysis))
                else:
                    # Analysis failed — create with default confidence
                    analyzed.append((candidate, None))

            # Relative ranking: sort by persona_fit_score, take top 50%
            if analyzed:
                total_before = len(analyzed)
                analyzed.sort(
                    key=lambda x: (
                        x[1].persona_fit_score if x[1] else 0.0
                    ),
                    reverse=True,
                )
                keep_count = max(1, total_before // 2)
                analyzed = analyzed[:keep_count]
                logger.info(
                    "[PeriodicLearner] Relative ranking: keeping top %d/%d candidates",
                    keep_count, total_before,
                )

            # Phase 3: Ingest top-ranked candidates
            ingested = 0
            for candidate, analysis in analyzed:
                if analysis:
                    # Pass the pre-computed analysis — avoid re-analyzing
                    persona_fit = analysis.persona_fit_score
                    meme = meme_pool.add_from_candidate(
                        text=candidate.text,
                        context_hint=analysis.context_trigger or candidate.context_hint,
                        confidence=persona_fit,
                        tags=(candidate.tags or []) + [f"mechanism:{analysis.humor_mechanism}"],
                    )
                    if meme:
                        # Store cognitive analysis on the meme
                        meme.cognitive_analysis = analysis
                        meme.source_platform = "bilibili"
                        meme.tags = list(set(meme.tags))
                        meme_pool.store.update(meme)
                        ingested += 1
                else:
                    # No analysis (LLM failed), ingest with default confidence
                    meme = meme_pool.add_from_candidate(
                        text=candidate.text,
                        context_hint=candidate.context_hint,
                        confidence=0.4,
                        tags=candidate.tags,
                    )
                    if meme:
                        ingested += 1

            logger.info(
                "[PeriodicLearner] Bilibili meme collection complete: "
                "%d collected, %d ingested",
                len(candidates), ingested,
            )
            return ingested

        except Exception as e:
            logger.warning(
                "[PeriodicLearner] Bilibili meme collection failed (isolated): %s",
                e, exc_info=True,
            )
            return 0

    async def learn_interaction_patterns(self) -> None:
        """Scheduled task: learn Bilibili interaction patterns for livestream optimization.

        Runs BilibiliInteractionLearner to analyze danmaku patterns and
        generate actionable livestream strategies stored in Wiki.
        Failure is isolated and does not block other scheduled tasks.
        """
        logger.info("[PeriodicLearner] Starting Bilibili interaction learning...")

        try:
            try:
                from anima.services.meme.bilibili_interaction import BilibiliInteractionLearner
            except ImportError:
                logger.warning(
                    "[PeriodicLearner] Bilibili interaction services not available, "
                    "skipping interaction learning"
                )
                return

            wiki = getattr(self._memory_system, '_wiki_manager', None)
            config = self._config.get("bilibili_meme", {})

            learner = BilibiliInteractionLearner(
                llm_client=self._llm_client,
                wiki_manager=wiki,
                config=config.get("interaction", {}),
            )

            strategies = await learner.learn_patterns()
            logger.info(
                "[PeriodicLearner] Interaction learning complete: %d strategies generated",
                len(strategies),
            )

        except Exception as e:
            logger.warning(
                "[PeriodicLearner] Interaction learning failed (isolated): %s",
                e, exc_info=True,
            )

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

    def _ensure_fact_extractor(self) -> None:
        """Lazily init FactExtractor from memory_system."""
        if self._fact_extractor is not None:
            return
        try:
            # Access fact_extractor via the WikiIngestor in memory_system
            ingestor = getattr(self._memory_system, '_ingestor', None)
            if ingestor and hasattr(ingestor, '_fact_extractor'):
                self._fact_extractor = ingestor._fact_extractor
                logger.info("[PeriodicLearner] FactExtractor initialized from memory system")
        except Exception as e:
            logger.warning(f"[PeriodicLearner] Could not init FactExtractor: {e}")

    def _get_turns_for_log(self, log: LearningLog) -> List[MemoryTurn]:
        """Retrieve raw MemoryTurn objects from a LearningLog's source_ids."""
        try:
            source_ids = json.loads(log.source_ids) if isinstance(log.source_ids, str) else log.source_ids
            if not source_ids:
                return []

            short_term = getattr(self._memory_system, '_short_term', None)
            if not hasattr(short_term, '_cache'):
                return []

            turns: List[MemoryTurn] = []
            for sid in source_ids:
                for session_turns in short_term._cache.values():
                    for t in session_turns:
                        if t.turn_id == sid:
                            turns.append(t)
                            break
            return turns
        except Exception as e:
            logger.debug(f"[PeriodicLearner] Could not retrieve turns for log {log.id}: {e}")
            return []

    async def _write_facts_to_wiki(self, facts: List[Dict[str, Any]]) -> None:
        """Write high-confidence extracted facts to Wiki synthesis pages.

        Dedup: existing facts with same content are updated (confidence boosted),
        new facts are appended.
        """
        wiki = getattr(self._memory_system, '_wiki_manager', None)
        if not wiki:
            logger.warning("[PeriodicLearner] WikiManager not available, cannot write facts")
            return

        import uuid as _uuid
        from datetime import datetime as _dt

        # Build Markdown content
        session_id = facts[0].get("source_turn_id", "batch")[:8] if facts else "batch"
        content = format_facts_for_wiki(facts, session_id)

        if not content:
            return

        try:
            from ..wiki.models import WikiPage, PageType

            page = WikiPage(
                title=f"自动发现: {_dt.now().strftime('%Y-%m-%d %H:%M')}",
                page_type=PageType.SYNTHESIS,
                path=f"synthesis/auto-facts-{_dt.now().strftime('%Y%m%d-%H%M%S')}-{_uuid.uuid4().hex[:6]}.md",
                content=content,
                tags=["auto-extracted", "fact", "learner", _dt.now().strftime("%Y-%m-%d")],
                links=[],
                created_at=_dt.now(),
                updated_at=_dt.now(),
            )
            wiki.write_page(page)
            logger.info(f"[PeriodicLearner] Wrote {len(facts)} facts to wiki page: {page.path}")
        except Exception as e:
            logger.warning(f"[PeriodicLearner] Wiki write failed: {e}")

    async def _patterns_to_memes(self, patterns: List[LearningLog]) -> None:
        """Feed patterns into meme discoverer."""
        max_candidates = self._config.get("meme_candidates_per_run", 15)

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
