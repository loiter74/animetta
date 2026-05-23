"""Memory system coordinator - Wiki architecture (Karpathy-style).

- raw/   Immutable raw conversation logs
- wiki/  AI-maintained knowledge base (entities / concepts / sources / synthesis)
"""

import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger
import asyncio

from .models.turns import MemoryTurn
from .config import MemoryConfig
from .manager import MemoryManager
from .models.base import SearchResult
from .models.memory_entry import MemoryEntry
from .search.scorer import MemoryScorer
from .stores import ShortTermMemory
from .fact_extractor import FactExtractor
from .user_profile import UserProfile, UserProfileBuilder
from .wiki import WikiManager, WikiIngestor, WikiQuery, WikiLint
from .wiki.mbti_store import MBTIStore
from ..orchestration.graph.scheduler import AsyncScheduler
from .fuzzy_layer import FuzzyLayer
from .meme import MemeStore, MemePool
from .learner import PeriodicLearner


class MemorySystem:
    """Memory system unified entry point (Wiki architecture)."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        workspace = config.get("workspace_dir", "~/.anima/workspace")
        memory_config = MemoryConfig(
            workspace_dir=workspace,
            db_path=config.get("db_path"),
            chroma_path=config.get("chroma_path"),
        )

        # Apply search configuration from config dict (overrides dataclass defaults)
        search_cfg = config.get("search", {})
        if search_cfg:
            if "vector_weight" in search_cfg:
                memory_config.search.vector_weight = float(search_cfg["vector_weight"])
            if "keyword_weight" in search_cfg:
                memory_config.search.keyword_weight = float(search_cfg["keyword_weight"])
            if "default_max_results" in search_cfg:
                memory_config.search.default_max_results = int(search_cfg["default_max_results"])

        # Apply chunk configuration from config dict
        chunk_cfg = config.get("chunk", {})
        if chunk_cfg:
            if "target_tokens" in chunk_cfg:
                memory_config.chunk.target_tokens = int(chunk_cfg["target_tokens"])
            if "overlap_tokens" in chunk_cfg:
                memory_config.chunk.overlap_tokens = int(chunk_cfg["overlap_tokens"])
            if "chars_per_token" in chunk_cfg:
                memory_config.chunk.chars_per_token = float(chunk_cfg["chars_per_token"])

        if "embedding_model" in config:
            from .config import EmbeddingConfig
            memory_config.embedding = EmbeddingConfig(
                model_name=config["embedding_model"]
            )

        self._scorer = MemoryScorer()
        self._short_term = ShortTermMemory(
            max_turns=config.get("short_term_max_turns", 20)
        )

        # Turn cache: deduplicate retrievals within the same turn
        self._turn_cache: Dict[str, Any] = {}
        self._turn_cache_enabled: bool = config.get("enable_turn_cache", True)
        self._last_session_id: Optional[str] = None
        self._last_query: Optional[str] = None

        self._wiki_manager = None
        self._ingestor = None
        self._wiki_query = None
        self._wiki_lint = None

        # Scheduler (Phase 1: Memory Evolution)
        self._scheduler = AsyncScheduler()
        self._scheduler_enabled: bool = config.get("scheduler", {}).get("enabled", True)

        # Fuzzy memory — replaced by FuzzyLayer (initialized after WikiManager below)
        self.fuzzy: Optional[Any] = None   # backward compat, set to FuzzyLayer later
        self._fuzzy_consolidator: Optional[Any] = None

        # PeriodicLearner (Phase 4: Memory Evolution)
        self._learner: Optional[PeriodicLearner] = None
        learner_config = config.get("learner", {})
        if learner_config.get("enabled", True):
            try:
                from pathlib import Path as _Path
                learner_config["workspace_dir"] = str(_Path(workspace).expanduser().resolve())
                self._learner = PeriodicLearner(
                    memory_system=self,
                    llm_client=config.get("llm_client"),
                    config=learner_config,
                )
                logger.info("[MemorySystem] PeriodicLearner initialized")
            except Exception as e:
                logger.warning(f"[MemorySystem] PeriodicLearner init failed: {e}")

        self.meme_pool: Optional[MemePool] = None  # declared early for resilience

        try:
            manager = MemoryManager(config=memory_config)
            self._wiki_manager = WikiManager(manager)

            # MemePool (wiki-backed, requires WikiManager)
            meme_config = config.get("meme_pool", {})
            if meme_config.get("enabled", True):
                try:
                    self.meme_pool = MemePool(wiki=self._wiki_manager, config=meme_config)
                    logger.info("[MemorySystem] MemePool initialized (wiki-backed)")
                except Exception as e:
                    logger.warning(f"[MemorySystem] MemePool init failed: {e}")

            # FuzzyLayer (replaces FuzzyMemoryStore, wiki + short-term fuzzification)
            self.fuzzy_layer: Optional[FuzzyLayer] = None
            try:
                self.fuzzy_layer = FuzzyLayer(
                    wiki=self._wiki_manager,
                    short_term=self._short_term,
                    mbti_store=self.mbti_store,
                )
                self.fuzzy = self.fuzzy_layer  # backward compat
                logger.info("[MemorySystem] FuzzyLayer initialized")
            except Exception as e:
                logger.warning(f"[MemorySystem] FuzzyLayer init failed: {e}")

            # MBTIStore (wiki-backed MBTI personality profile storage)
            self.mbti_store: Optional[MBTIStore] = None
            try:
                self.mbti_store = MBTIStore(wiki=self._wiki_manager)
                logger.info("[MemorySystem] MBTIStore initialized")
            except Exception as e:
                logger.warning(f"[MemorySystem] MBTIStore init failed: {e}")
            # Fact extractor (MemoryEntry versioned memory)
            fact_extractor = FactExtractor(
                entry_store=manager.memory_entries,
                llm_client=config.get("llm_client"),
            )
            self._ingestor = WikiIngestor(
                self._wiki_manager,
                llm_client=config.get("llm_client"),
                fact_extractor=fact_extractor,
            )
            self._wiki_query = WikiQuery(self._wiki_manager)
            self._profile_builder = UserProfileBuilder(
                wiki_manager=self._wiki_manager,
                short_term=self._short_term,
            )
            self._wiki_lint = WikiLint(self._wiki_manager)
            logger.info(
                f"[MemorySystem] Wiki architecture initialized successfully, "
                f"workspace: {memory_config.workspace_dir}"
            )
        except Exception as e:
            logger.warning(f"[MemorySystem] Degraded to pure short-term memory mode: {e}")

    # ── Lifecycle ─────────────────────────────────────────

    async def start(self) -> None:
        logger.info("[MemorySystem] Started (wiki architecture)")

        # Register scheduler tasks
        if self._scheduler_enabled and self._scheduler:
            sched_config = self._config if hasattr(self, '_config') else {}
            tasks_cfg = sched_config.get("scheduler", {}).get("tasks", {})
            default_cfg = {"timeout": 300}

            if self._learner:
                consolidate_cfg = tasks_cfg.get("consolidate_conversations", default_cfg)
                self._scheduler.add_task(
                    "consolidate_conversations",
                    self._learner.consolidate_conversations,
                    interval=consolidate_cfg.get("interval", 3600),
                    timeout=consolidate_cfg.get("timeout", 120),
                )
                extract_cfg = tasks_cfg.get("extract_patterns", default_cfg)
                self._scheduler.add_task(
                    "extract_patterns",
                    self._learner.extract_patterns,
                    interval=extract_cfg.get("interval", 86400),
                    timeout=extract_cfg.get("timeout", 300),
                )
                meme_cfg = tasks_cfg.get("generate_meme_candidates", default_cfg)
                self._scheduler.add_task(
                    "generate_meme_candidates",
                    self._learner.generate_meme_candidates,
                    interval=meme_cfg.get("interval", 21600),
                    timeout=meme_cfg.get("timeout", 120),
                )
                fact_cfg = tasks_cfg.get("extract_facts", default_cfg)
                self._scheduler.add_task(
                    "extract_facts",
                    self._learner.extract_facts,
                    interval=fact_cfg.get("interval", 7200),
                    timeout=fact_cfg.get("timeout", 300),
                )
                persona_cfg = tasks_cfg.get("optimize_persona", default_cfg)
                self._scheduler.add_task(
                    "optimize_persona",
                    self._learner.optimize_persona,
                    interval=persona_cfg.get("interval", 86400),
                    timeout=persona_cfg.get("timeout", 300),
                )
                mbti_cfg = tasks_cfg.get("analyze_mbti", default_cfg)
                self._scheduler.add_task(
                    "analyze_mbti",
                    self._learner.analyze_mbti,
                    interval=mbti_cfg.get("interval", 86400),
                    timeout=mbti_cfg.get("timeout", 120),
                )
                archive_cfg = tasks_cfg.get("archive_decayed", default_cfg)
                self._scheduler.add_task(
                    "archive_decayed",
                    self._archive_decayed_entries,
                    interval=archive_cfg.get("interval", 43200),
                    timeout=archive_cfg.get("timeout", 120),
                )

            if self.meme_pool:
                maintain_cfg = tasks_cfg.get("maintain_meme_pool", default_cfg)
                self._scheduler.add_task(
                    "maintain_meme_pool",
                    lambda: asyncio.to_thread(self.meme_pool.maintain_pool),
                    interval=maintain_cfg.get("interval", 3600),
                    timeout=maintain_cfg.get("timeout", 30),
                )

            if self._learner:
                prune_cfg = tasks_cfg.get("prune_learning_logs", default_cfg)
                self._scheduler.add_task(
                    "prune_learning_logs",
                    self._learner.prune_logs,
                    interval=prune_cfg.get("interval", 86400),
                    timeout=prune_cfg.get("timeout", 60),
                )

            await self._scheduler.start()
            logger.info("[MemorySystem] Scheduler started with registered tasks")

    async def stop(self) -> None:
        if self._scheduler:
            await self._scheduler.stop()
            _log_scheduler_metrics(self._scheduler)
        if self._learner:
            await self._learner.stop()
        if self.fuzzy and hasattr(self.fuzzy, 'close'):
            self.fuzzy.close()
        if self._wiki_manager:
            self._wiki_manager.manager.close()
        self._short_term.clear_all()
        logger.info("[MemorySystem] Memory system stopped")

    async def _archive_decayed_entries(self) -> None:
        """Scheduled task: archive MemoryEntry objects below decay threshold."""
        try:
            store = self._wiki_manager.manager.memory_entries if self._wiki_manager else None
            if store:
                store.archive_decayed()
        except Exception as e:
            logger.warning(f"[MemorySystem] Archive decayed entries failed: {e}")

    # ── Storage ───────────────────────────────────────────

    async def store_turn(self, turn: MemoryTurn) -> None:
        """Store conversation turn: short-term memory + wiki INGEST + fuzzy consolidation"""
        score = self._scorer.score(turn)
        turn.importance = score
        self._short_term.append(turn.session_id, turn)

        if self._ingestor:
            asyncio.create_task(self._ingestor.ingest_turn(turn))

        # Fuzzy consolidation (async, non-blocking)
        if self._fuzzy_consolidator and turn.importance >= 0.3:
            asyncio.create_task(self._fuzzy_consolidator.consolidate_lightweight(turn))

    # ── User profile ──────────────────────────────────────

    def get_profile(self, session_id: str) -> UserProfile:
        """Get user profile (static + dynamic).

        Requires both wiki mode and short_term to be available for complete construction.
        """
        if not hasattr(self, '_profile_builder') or self._profile_builder is None:
            return UserProfile()
        return self._profile_builder.build(session_id)

    # ── Turn cache ────────────────────────────────────────

    def _invalidate_turn_cache(self, session_id: str, query: str) -> None:
        """Detect if new turn, clear cache if so."""
        if session_id != self._last_session_id or query != self._last_query:
            self._turn_cache.clear()
            self._last_session_id = session_id
            self._last_query = query

    def _make_cache_key(self, session_id: str, query: str, max_turns: int) -> str:
        """Build cache key."""
        raw = f"{session_id}:{query}:{max_turns}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ── Retrieval ─────────────────────────────────────────

    async def retrieve_context(
        self, query: str, session_id: str, max_turns: int = 5,
    ) -> List[MemoryTurn]:
        """Retrieve relevant memories: short-term + wiki search + MemoryEntry (optional).

        When turn cache is enabled, same-turn same-parameter retrieval executes only once.
        """
        # Cache check (Task 6.1, 6.2)
        if self._turn_cache_enabled:
            self._invalidate_turn_cache(session_id, query)
            cache_key = self._make_cache_key(session_id, query, max_turns)
            if cache_key in self._turn_cache:
                logger.debug(f"[MemorySystem] turn cache hit: {cache_key[:12]}")
                return list(self._turn_cache[cache_key])

        results = list(self._short_term.get_recent(session_id, max_turns))

        if self._wiki_query:
            try:
                results.extend(self._wiki_query.search_turns(
                    query=query, session_id=session_id, max_results=5,
                ))
            except Exception as e:
                logger.warning(f"[MemorySystem] Wiki search failed: {e}")

        # Append MemoryEntry results (Task 7.2)
        try:
            if self._wiki_manager and hasattr(self._wiki_manager.manager, 'memory_entries'):
                entries = self._wiki_manager.manager.memory_entries.search_by_space(
                    space_id="default", query=query, limit=3,
                )
                for entry in entries:
                    turn = MemoryTurn(
                        turn_id=f"mem_entry_{entry.id}",
                        session_id=session_id,
                        timestamp=datetime.fromisoformat(entry.created_at) if entry.created_at else datetime.now(),
                        user_input="",
                        agent_response=entry.memory,
                        emotions=[],
                        metadata={"source": "memory_entry", "confidence": entry.confidence, "version": entry.version},
                        importance=entry.confidence,
                    )
                    results.append(turn)
        except Exception as e:
            logger.debug(f"[MemorySystem] MemoryEntry retrieval failed: {e}")

        seen: set = set()
        deduped = [t for t in results if t.turn_id not in seen and not seen.add(t.turn_id)]

        # Cache results (Task 6.3)
        if self._turn_cache_enabled:
            self._turn_cache[cache_key] = deduped

        return deduped

    async def get_user_history(self, session_id: str, limit: int = 50) -> List[MemoryTurn]:
        return list(reversed(self._short_term.get_recent(session_id, limit)))

    async def clear_session(self, session_id: str) -> None:
        self._short_term.clear(session_id)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Direct memory search: merge chunk results + MemoryEntry results."""
        results: List[SearchResult] = []
        if self._wiki_manager:
            results = self._wiki_manager.search(query, max_results=max_results)

        # Append MemoryEntry results (Task 7.1)
        try:
            if self._wiki_manager and hasattr(self._wiki_manager.manager, 'memory_entries'):
                entries = self._wiki_manager.manager.memory_entries.search_by_space(
                    space_id="default", query=query, limit=max_results,
                )
                for entry in entries:
                    results.append(SearchResult(
                        text=entry.memory,
                        path=f"memory_entry/{entry.id}",
                        start_line=0,
                        end_line=0,
                        score=entry.confidence,
                        source="memory_entry",
                    ))
        except Exception as e:
            logger.debug(f"[MemorySystem] MemoryEntry search failed: {e}")

        return results

    def load_session_context(self, query: str = "") -> str:
        """Load memory context at session startup"""
        if self._wiki_query:
            return self._wiki_query.load_context(query=query)
        return ""

    def should_flush(self, current_tokens: int, context_window: int) -> bool:
        if self._wiki_manager:
            return self._wiki_manager.manager.should_flush(current_tokens, context_window)
        return False

    def sync(self) -> None:
        """Full index sync"""
        if self._wiki_manager:
            self._wiki_manager.manager.sync()
            self._wiki_manager.rebuild_index()

    def lint(self):
        """Run wiki health check"""
        if self._wiki_lint:
            return self._wiki_lint.run()
        return None

    def close(self) -> None:
        if self._wiki_manager:
            self._wiki_manager.manager.close()
        self._short_term.clear_all()


def _log_scheduler_metrics(scheduler) -> None:
    """Log scheduler metrics for all tasks (called on shutdown)."""
    try:
        metrics_list = scheduler.get_metrics()
        for m in metrics_list:
            if m.total_runs > 0:
                logger.info(
                    f"[MemorySystem] Scheduler task '{m.name}': "
                    f"runs={m.total_runs}, success={m.success_count}, "
                    f"failure={m.failure_count}, last_duration={m.last_duration:.1f}s"
                )
    except Exception as e:
        logger.debug(f"[MemorySystem] Failed to log scheduler metrics: {e}")
