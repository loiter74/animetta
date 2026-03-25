"""记忆系统协调器 - OpenClaw 架构"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
import asyncio

from .models.turns import MemoryTurn
from .config import MemoryConfig
from .manager import MemoryManager
from .models.base import SearchResult
from .search.scorer import MemoryScorer
from .stores import ShortTermMemory, LongTermMemory
from .oral_worker import OralMemoryWorker


class MemorySystem:
    """记忆系统统一入口"""

    def __init__(self, config: Dict[str, Any]):
        workspace = config.get("workspace_dir", "~/.anima/workspace")
        memory_config = MemoryConfig(
            workspace_dir=workspace,
            db_path=config.get("db_path"),
            chroma_path=config.get("chroma_path"),
        )

        if "embedding_model" in config:
            from .config import EmbeddingConfig
            memory_config.embedding = EmbeddingConfig(model_name=config["embedding_model"])

        self._scorer = MemoryScorer()
        self._short_term = ShortTermMemory(max_turns=config.get("short_term_max_turns", 20))

        self._long_term: Optional[LongTermMemory] = None
        self._oral_worker: Optional[OralMemoryWorker] = None

        try:
            manager = MemoryManager(config=memory_config)
            self._long_term = LongTermMemory(manager)
            logger.info(f"[MemorySystem] 初始化成功, workspace: {memory_config.workspace_dir}")
        except Exception as e:
            logger.warning(f"[MemorySystem] 降级为纯短期记忆模式: {e}")

        # 初始化口语化 Worker
        llm_client = config.get("llm_client")
        if llm_client:
            self._oral_worker = OralMemoryWorker(
                llm_client=llm_client,
                queue_size=config.get("oral_queue_size", 1000),
                max_retries=config.get("oral_max_retries", 2),
                batch_size=config.get("oral_batch_size", 5),
            )
            logger.info("[MemorySystem] 口语化 Worker 已初始化")
        else:
            logger.info("[MemorySystem] 未配置 LLM 客户端，口语化功能使用规则后备方案")

    async def start(self) -> None:
        """启动记忆系统"""
        if self._long_term:
            await self._long_term.start()
            logger.info("[MemorySystem] 长期记忆已启动")

        if self._oral_worker:
            await self._oral_worker.start()
            # 将 Worker 设置给 LongTermMemory
            if self._long_term:
                self._long_term.set_oral_worker(self._oral_worker)
            logger.info("[MemorySystem] 口语化 Worker 已启动")

    async def stop(self) -> None:
        """停止记忆系统"""
        if self._oral_worker:
            await self._oral_worker.stop()
            logger.info("[MemorySystem] 口语化 Worker 已停止")

        if self._long_term:
            await self._long_term.stop()
        self._short_term.clear_all()
        logger.info("[MemorySystem] 记忆系统已停止")

    async def store_turn(self, turn: MemoryTurn) -> None:
        """存储对话轮次"""
        score = self._scorer.score(turn)
        turn.importance = score
        self._short_term.append(turn.session_id, turn)
        logger.debug(f"[MemorySystem] 短期记忆已存储 (分数: {score:.2f})")

        if self._long_term and self._scorer.should_store(score):
            asyncio.create_task(self._store_to_long_term(turn, score))
            logger.debug(f"[MemorySystem] 长期记忆存储任务已提交 (分数: {score:.2f})")

    async def _store_to_long_term(self, turn: MemoryTurn, score: float) -> None:
        """异步存储到长期记忆"""
        try:
            await self._long_term.store(turn, score)
        except Exception as e:
            logger.warning(f"[MemorySystem] 长期记忆存储失败: {e}")

    async def retrieve_context(
        self,
        query: str,
        session_id: str,
        max_turns: int = 5
    ) -> List[MemoryTurn]:
        """检索相关记忆"""
        results = []
        recent = self._short_term.get_recent(session_id, max_turns)
        results.extend(recent)

        if self._long_term:
            try:
                search_results = await self._long_term.search(
                    query=query,
                    session_id=session_id,
                    max_results=5
                )

                for sr in search_results:
                    memory_turn = MemoryTurn(
                        turn_id=f"search_{sr.path}_{sr.start_line}",
                        session_id=session_id,
                        timestamp=datetime.now(),
                        user_input=self._extract_user_input(sr.text),
                        agent_response=self._extract_agent_response(sr.text),
                        emotions=[],
                        metadata={"path": sr.path, "score": sr.score, "source": sr.source},
                        importance=sr.score
                    )
                    results.append(memory_turn)

                logger.debug(f"[MemorySystem] 混合搜索返回 {len(search_results)} 条结果")

            except Exception as e:
                logger.warning(f"[MemorySystem] 混合搜索失败: {e}")

        # 去重
        seen = set()
        unique_results = []
        for turn in results:
            if turn.turn_id not in seen:
                seen.add(turn.turn_id)
                unique_results.append(turn)

        return unique_results

    def _extract_user_input(self, text: str) -> str:
        """从 Markdown 格式中提取用户输入"""
        lines = text.split("\n")
        for line in lines:
            if line.startswith("**User:**"):
                return line[9:].strip()
            elif line.startswith("User: "):
                return line[6:].strip()
            elif line.startswith("- 用户说："):
                return line[5:].strip()
        return ""

    def _extract_agent_response(self, text: str) -> str:
        """从 Markdown 格式中提取 AI 响应"""
        lines = text.split("\n")
        for line in lines:
            if line.startswith("**AI:**"):
                return line[6:].strip()
            elif line.startswith("AI: "):
                return line[4:].strip()
        return ""

    async def get_user_history(self, session_id: str, limit: int = 50) -> List[MemoryTurn]:
        """获取用户历史记录"""
        return list(reversed(self._short_term.get_recent(session_id, limit)))

    async def clear_session(self, session_id: str) -> None:
        """清除会话"""
        self._short_term.clear(session_id)

    def write_memory(self, content: str, append: bool = True) -> None:
        """写入长期记忆"""
        if self._long_term:
            self._long_term.write_memory(content, append=append)

    def write_daily_log(self, content: str) -> None:
        """写入每日日志"""
        if self._long_term:
            self._long_term.write_daily_log(content)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """直接搜索记忆"""
        if self._long_term:
            return self._long_term.sync_search(query, max_results=max_results)
        return []

    def load_session_context(self, query: str = "") -> str:
        """加载会话启动时的记忆上下文"""
        if self._long_term:
            return self._long_term.get_context(query=query)
        return ""

    def should_flush(self, current_tokens: int, context_window: int) -> bool:
        """判断是否需要触发记忆 flush"""
        if self._long_term:
            return self._long_term.should_flush(current_tokens, context_window)
        return False

    def sync(self) -> None:
        """全量同步索引"""
        if self._long_term:
            self._long_term.sync()

    def get_oral_worker(self) -> Optional[OralMemoryWorker]:
        """获取口语化 Worker（供 MemoryManager 使用）"""
        return self._oral_worker

    def close(self) -> None:
        """关闭记忆系统"""
        if self._oral_worker:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._oral_worker.stop())
                else:
                    asyncio.run(self._oral_worker.stop())
            except Exception as e:
                logger.warning(f"[MemorySystem] 关闭 Worker 失败: {e}")

        if self._long_term:
            self._long_term.close()
        self._short_term.clear_all()
