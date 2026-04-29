"""记忆系统协调器 - Wiki 架构 (Karpathy-style).

- raw/   不可变的原始对话日志
- wiki/  AI 维护的知识库 (entities / concepts / sources / synthesis)
"""

from typing import List, Dict, Any
from loguru import logger
import asyncio

from .models.turns import MemoryTurn
from .config import MemoryConfig
from .manager import MemoryManager
from .models.base import SearchResult
from .search.scorer import MemoryScorer
from .stores import ShortTermMemory
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

        self._wiki_manager = None
        self._ingestor = None
        self._wiki_query = None
        self._wiki_lint = None

        try:
            manager = MemoryManager(config=memory_config)
            self._wiki_manager = WikiManager(manager)
            self._ingestor = WikiIngestor(
                self._wiki_manager,
                llm_client=config.get("llm_client"),
            )
            self._wiki_query = WikiQuery(self._wiki_manager)
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

    # ── 检索 ────────────────────────────────────────────────

    async def retrieve_context(
        self, query: str, session_id: str, max_turns: int = 5,
    ) -> List[MemoryTurn]:
        """检索相关记忆: 短期 + wiki search"""
        results = list(self._short_term.get_recent(session_id, max_turns))

        if self._wiki_query:
            try:
                results.extend(self._wiki_query.search_turns(
                    query=query, session_id=session_id, max_results=5,
                ))
            except Exception as e:
                logger.warning(f"[MemorySystem] Wiki 搜索失败: {e}")

        seen: set = set()
        return [t for t in results if t.turn_id not in seen and not seen.add(t.turn_id)]

    async def get_user_history(self, session_id: str, limit: int = 50) -> List[MemoryTurn]:
        return list(reversed(self._short_term.get_recent(session_id, limit)))

    async def clear_session(self, session_id: str) -> None:
        self._short_term.clear(session_id)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """直接搜索记忆"""
        if self._wiki_manager:
            return self._wiki_manager.search(query, max_results=max_results)
        return []

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
