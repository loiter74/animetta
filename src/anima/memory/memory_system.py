"""
记忆系统协调器

基于 OpenClaw 架构的新版记忆系统：
- Markdown 文件是唯一事实来源 (MEMORY.md + daily logs)
- 混合检索: 向量语义搜索 (70%) + BM25 关键词搜索 (30%)
- 滑动窗口分块: ~400 token/块, 80 token 重叠
- 增量索引: 基于文件哈希检测变更
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
import asyncio

from .memory_turn import MemoryTurn
from .config import MemoryConfig
from .memory_manager import MemoryManager
from .models import SearchResult
from .scorer import MemoryScorer
from .stores import ShortTermMemory, LongTermMemory


class MemorySystem:
    """
    记忆系统统一入口

    职责：
    1. 协调短期记忆和长期记忆
    2. 提供统一的存储和检索接口
    3. 管理生命周期

    Example:
        >>> memory = MemorySystem({
        ...     "workspace_dir": "~/.anima/workspace",
        ...     "short_term_max_turns": 20,
        ... })
        >>> turn = MemoryTurn(...)
        >>> await memory.store_turn(turn)
        >>> results = await memory.retrieve_context(
        ...     query="你好",
        ...     session_id="session_123"
        ... )
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化记忆系统

        Args:
            config: 配置字典
                - workspace_dir: 工作目录
                - db_path: SQLite 数据库路径 (可选)
                - chroma_path: Chroma 向量库路径 (可选)
                - short_term_max_turns: 短期记忆容量
                - embedding_model: embedding 模型名称
        """
        # 构建配置
        workspace = config.get("workspace_dir", "~/.anima/workspace")
        memory_config = MemoryConfig(
            workspace_dir=workspace,
            db_path=config.get("db_path"),
            chroma_path=config.get("chroma_path"),
        )

        # 设置 embedding 模型
        if "embedding_model" in config:
            from .config import EmbeddingConfig
            memory_config.embedding = EmbeddingConfig(model_name=config["embedding_model"])

        # 初始化组件
        self._scorer = MemoryScorer()
        self._short_term = ShortTermMemory(
            max_turns=config.get("short_term_max_turns", 20)
        )

        # 初始化长期记忆 (可能降级)
        self._long_term: Optional[LongTermMemory] = None
        try:
            manager = MemoryManager(config=memory_config)
            self._long_term = LongTermMemory(manager)
            logger.info(f"[MemorySystem] 初始化成功, workspace: {memory_config.workspace_dir}")
        except Exception as e:
            logger.warning(f"[MemorySystem] MemoryManager 初始化失败， 降级为纯短期记忆模式: {e}")

    async def start(self) -> None:
        """启动记忆系统"""
        if self._long_term:
            await self._long_term.start()
            logger.info("[MemorySystem] 长期记忆已启动")

    async def stop(self) -> None:
        """停止记忆系统"""
        if self._long_term:
            await self._long_term.stop()
        self._short_term.clear_all()
        logger.info("[MemorySystem] 记忆系统已停止")

    async def store_turn(self, turn: MemoryTurn) -> None:
        """
        存储对话轮次

        流程:
        1. 计算重要性分数
        2. 根据分数决定存储策略
        3. 存储到短期记忆 (同步)
        4. 存储到长期记忆 (异步, 如果分数足够)

        Args:
            turn: 对话轮次数据
        """
        # 1. 计算重要性分数
        score = self._scorer.score(turn)
        turn.importance = score  # 更新重要性

        # 2. 存储到短期记忆 (同步, 总是存储)
        self._short_term.append(turn.session_id, turn)
        logger.debug(f"[MemorySystem] 短期记忆已存储 (分数: {score:.2f})")

        # 3. 存储到长期记忆 (异步, 根据分数决定)
        if self._long_term and self._scorer.should_store(score):
            # 异步存储, 不等待
            asyncio.create_task(self._store_to_long_term(turn, score))
            logger.debug(f"[MemorySystem] 长期记忆存储任务已提交 (分数: {score:.2f})")
        else:
            logger.debug(f"[MemorySystem] 跳过长期存储 (分数: {score:.2f})")

    async def _store_to_long_term(self, turn: MemoryTurn, score: float) -> None:
        """
        异步存储到长期记忆

        Args:
            turn: 对话轮次
            score: 重要性分数
        """
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
        """
        检索相关记忆

        策略: 多路召回
        1. 短期记忆: 最近 N 轮
        2. 混合搜索: 向量语义 + BM25 关键词

        Args:
            query: 查询文本
            session_id: 会话 ID
            max_turns: 短期记忆返回数量

        Returns:
            相关记忆列表
        """
        results = []

        # 1. 短期记忆: 最近 N 轮
        recent = self._short_term.get_recent(session_id, max_turns)
        results.extend(recent)

        # 2. 混合搜索长期记忆
        if self._long_term:
            try:
                search_results = await self._long_term.search(
                    query=query,
                    session_id=session_id,
                    max_results=5
                )

                # 转换 SearchResult 为 MemoryTurn
                for sr in search_results:
                    memory_turn = MemoryTurn(
                        turn_id=f"search_{sr.path}_{sr.start_line}",
                        session_id=session_id,
                        timestamp=datetime.now(),
                        user_input=self._extract_user_input(sr.text),
                        agent_response=self._extract_agent_response(sr.text),
                        emotions=[],
                        metadata={
                            "path": sr.path,
                            "score": sr.score,
                            "source": sr.source,
                        },
                        importance=sr.score
                    )
                    results.append(memory_turn)

                logger.debug(f"[MemorySystem] 混合搜索返回 {len(search_results)} 条结果")

            except Exception as e:
                logger.warning(f"[MemorySystem] 混合搜索失败: {e}")

        # 3. 去重 (按 turn_id)
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
            if line.startswith("**User**:"):
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
            if line.startswith("**AI**:"):
                return line[6:].strip()
            elif line.startswith("AI: "):
                return line[4:].strip()
        return ""

    async def get_user_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[MemoryTurn]:
        """
        获取用户历史记录

        Args:
            session_id: 会话 ID
            limit: 返回记录数量

        Returns:
            历史对话列表 (按时间倒序)
        """
        return list(reversed(self._short_term.get_recent(session_id, limit)))

    async def clear_session(self, session_id: str) -> None:
        """
        清除会话 (短期记忆)

        Args:
            session_id: 会话 ID
        """
        self._short_term.clear(session_id)

    def write_memory(self, content: str, append: bool = True) -> None:
        """
        写入长期记忆 (MEMORY.md)

        Args:
            content: 要写入的内容
            append: True=追加, False=覆盖
        """
        if self._long_term:
            self._long_term.write_memory(content, append=append)

    def write_daily_log(self, content: str) -> None:
        """
        写入每日日志

        Args:
            content: 日志内容
        """
        if self._long_term:
            self._long_term.write_daily_log(content)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        直接搜索记忆 (不转换为 MemoryTurn)

        Args:
            query: 查询文本
            max_results: 返回结果数量

        Returns:
            SearchResult 列表
        """
        if self._long_term:
            return self._long_term.sync_search(query, max_results=max_results)
        return []

    def load_session_context(self, query: str = "") -> str:
        """
        加载会话启动时的记忆上下文

        Args:
            query: 当前用户输入, 用于语义检索相关记忆
        """
        if self._long_term:
            return self._long_term.get_context(query=query)
        return ""

    def should_flush(self, current_tokens: int, context_window: int) -> bool:
        """
        判断是否需要触发记忆 flush

        Args:
            current_tokens: 当前会话消耗的 token 数
            context_window: 模型上下文窗口大小

        Returns:
            True 表示应该触发 flush
        """
        if self._long_term:
            return self._long_term.should_flush(current_tokens, context_window)
        return False

    def sync(self) -> None:
        """全量同步索引"""
        if self._long_term:
            self._long_term.sync()

    def close(self) -> None:
        """关闭记忆系统"""
        if self._long_term:
            self._long_term.close()
        self._short_term.clear_all()
