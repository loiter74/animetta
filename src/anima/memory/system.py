"""记忆系统协调器 - Wiki 架构 (Karpathy-style).

- raw/   不可变的原始对话日志
- wiki/  AI 维护的知识库 (entities / concepts / sources / synthesis)
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


class MemorySystem:
    """记忆系统统一入口 (Wiki 架构)."""

    def __init__(self, config: Dict[str, Any]):
        workspace = config.get("workspace_dir", "~/.anima/workspace")
        memory_config = MemoryConfig(
            workspace_dir=workspace,
            db_path=config.get("db_path"),
            chroma_path=config.get("chroma_path"),
        )

        if "embedding_model" in config:
            from .config import EmbeddingConfig
            memory_config.embedding = EmbeddingConfig(
                model_name=config["embedding_model"]
            )

        self._scorer = MemoryScorer()
        self._short_term = ShortTermMemory(
            max_turns=config.get("short_term_max_turns", 20)
        )

        # Turn cache: 同轮检索去重
        self._turn_cache: Dict[str, Any] = {}
        self._turn_cache_enabled: bool = config.get("enable_turn_cache", True)
        self._last_session_id: Optional[str] = None
        self._last_query: Optional[str] = None

        self._wiki_manager = None
        self._ingestor = None
        self._wiki_query = None
        self._wiki_lint = None

        try:
            manager = MemoryManager(config=memory_config)
            self._wiki_manager = WikiManager(manager)
            # 事实提取器 (MemoryEntry 版本化记忆)
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
                f"[MemorySystem] Wiki 架构初始化成功, "
                f"workspace: {memory_config.workspace_dir}"
            )
        except Exception as e:
            logger.warning(f"[MemorySystem] 降级为纯短期记忆模式: {e}")

    # ── 生命周期 ────────────────────────────────────────────

    async def start(self) -> None:
        logger.info("[MemorySystem] 已启动 (wiki 架构)")

    async def stop(self) -> None:
        if self._wiki_manager:
            self._wiki_manager.manager.close()
        self._short_term.clear_all()
        logger.info("[MemorySystem] 记忆系统已停止")

    # ── 存储 ────────────────────────────────────────────────

    async def store_turn(self, turn: MemoryTurn) -> None:
        """存储对话轮次: 短期记忆 + wiki INGEST"""
        score = self._scorer.score(turn)
        turn.importance = score
        self._short_term.append(turn.session_id, turn)

        if self._ingestor:
            asyncio.create_task(self._ingestor.ingest_turn(turn))

    # ── 用户画像 ────────────────────────────────────────────

    def get_profile(self, session_id: str) -> UserProfile:
        """获取用户画像 (static + dynamic).

        需要在 wiki 模式和 short_term 都可用时才能完整构建.
        """
        if not hasattr(self, '_profile_builder') or self._profile_builder is None:
            return UserProfile()
        return self._profile_builder.build(session_id)

    # ── Turn Cache ───────────────────────────────────────────

    def _invalidate_turn_cache(self, session_id: str, query: str) -> None:
        """检测是否为新轮次, 若是则清空缓存."""
        if session_id != self._last_session_id or query != self._last_query:
            self._turn_cache.clear()
            self._last_session_id = session_id
            self._last_query = query

    def _make_cache_key(self, session_id: str, query: str, max_turns: int) -> str:
        """构建缓存 key."""
        raw = f"{session_id}:{query}:{max_turns}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ── 检索 ────────────────────────────────────────────────

    async def retrieve_context(
        self, query: str, session_id: str, max_turns: int = 5,
    ) -> List[MemoryTurn]:
        """检索相关记忆: 短期 + wiki search + MemoryEntry (可选).

        启用 turn cache 时, 同轮同参数的检索只执行一次.
        """
        # 缓存检查 (Task 6.1, 6.2)
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
                logger.warning(f"[MemorySystem] Wiki 搜索失败: {e}")

        # 附加 MemoryEntry 结果 (Task 7.2)
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

        # 缓存结果 (Task 6.3)
        if self._turn_cache_enabled:
            self._turn_cache[cache_key] = deduped

        return deduped

    async def get_user_history(self, session_id: str, limit: int = 50) -> List[MemoryTurn]:
        return list(reversed(self._short_term.get_recent(session_id, limit)))

    async def clear_session(self, session_id: str) -> None:
        self._short_term.clear(session_id)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """直接搜索记忆: 合并 chunk 结果 + MemoryEntry 结果."""
        results: List[SearchResult] = []
        if self._wiki_manager:
            results = self._wiki_manager.search(query, max_results=max_results)

        # 附加 MemoryEntry 结果 (Task 7.1)
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
        """加载会话启动时的记忆上下文"""
        if self._wiki_query:
            return self._wiki_query.load_context(query=query)
        return ""

    def should_flush(self, current_tokens: int, context_window: int) -> bool:
        if self._wiki_manager:
            return self._wiki_manager.manager.should_flush(current_tokens, context_window)
        return False

    def sync(self) -> None:
        """全量同步索引"""
        if self._wiki_manager:
            self._wiki_manager.manager.sync()
            self._wiki_manager.rebuild_index()

    def lint(self):
        """运行 wiki 健康检查"""
        if self._wiki_lint:
            return self._wiki_lint.run()
        return None

    def close(self) -> None:
        if self._wiki_manager:
            self._wiki_manager.manager.close()
        self._short_term.clear_all()
