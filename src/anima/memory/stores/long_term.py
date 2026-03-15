"""
长期记忆存储

基于 Markdown + SQLite + Chroma 的持久化存储实现。
"""

import asyncio
from datetime import datetime
from typing import List, Optional
from loguru import logger

from ..memory_turn import MemoryTurn
from ..models import SearchResult
from ..memory_manager import MemoryManager


class LongTermMemory:
    """
    长期记忆存储

    特点:
    - 持久化存储 (Markdown + SQLite + Chroma)
    - 异步写入, 不阻塞响应
    - 混合检索 (向量 + 关键词)
    """

    def __init__(self, manager: MemoryManager):
        """
        初始化

        Args:
            manager: MemoryManager 实例
        """
        self._manager = manager
        self._write_queue: asyncio.Queue = asyncio.Queue()
        self._writer_task: Optional[asyncio.Task] = None
        logger.info("[LongTermMemory] 初始化完成")

    async def start(self) -> None:
        """启动异步写入任务"""
        if self._writer_task is None or self._writer_task.done():
            self._writer_task = asyncio.create_task(self._write_worker())
            logger.info("[LongTermMemory] 异步写入任务已启动")

    async def stop(self) -> None:
        """停止异步写入任务"""
        if self._writer_task and not self._writer_task.done():
            # 发送结束信号
            await self._write_queue.put(None)
            await self._writer_task
            logger.info("[LongTermMemory] 异步写入任务已停止")

    async def _write_worker(self) -> None:
        """异步写入工作协程"""
        while True:
            try:
                item = await self._write_queue.get()

                # 结束信号
                if item is None:
                    break

                action, *args = item
                await action(*args)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[LongTermMemory] 写入失败: {e}")

    async def store(self, turn: MemoryTurn, score: float) -> None:
        """
        异步存储对话

        Args:
            turn: 对话轮次
            score: 评分
        """
        if score < 0.3:
            logger.debug(f"[LongTermMemory] 跳过低分对话 (score={score:.2f})")
            return

        # 将写入任务加入队列
        await self._write_queue.put((self._do_store_turn, turn, score))
        logger.debug(f"[LongTermMemory] 对话已加入写入队列 (score={score:.2f})")

    async def _do_store_turn(self, turn: MemoryTurn, score: float) -> None:
        """实际执行存储操作"""
        try:
            # 格式化对话为 Markdown
            content = f"""**User**: {turn.user_input}
**AI**: {turn.agent_response}
"""
            if turn.emotions:
                if turn.emotions and isinstance(turn.emotions[0], dict):
                    emotion_names = [e.get("emotion", str(e)) for e in turn.emotions]
                else:
                    emotion_names = [str(e) for e in turn.emotions]
                content += f"*Emotions: {', '.join(emotion_names)}*\n"

            # 写入每日日志
            self._manager.write_daily_log(content)

            # 如果重要性足够， 也写入 MEMORY.md
            if score >= 0.5:
                await self._store_important(turn)

        except Exception as e:
            logger.error(f"[LongTermMemory] 存储失败: {e}")

    async def _store_important(self, turn: MemoryTurn) -> None:
        """存储重要对话到 MEMORY.md"""
        date_str = turn.timestamp.strftime('%Y-%m-%d')

        # 格式: [日期] 用户原话
        memory_entry = f"""
## {date_str}
- 用户说：{turn.user_input}
"""
        self._manager.write_memory(memory_entry)
        logger.info(f"[LongTermMemory] 写入 MEMORY.md (timestamp={date_str})")

    async def search(self, query: str, session_id: str = "", max_results: int = 5, min_score: float = 0.3) -> List[SearchResult]:
        """
        搜索相关记忆

        Args:
            query: 查询文本
            session_id: 会话 ID (未使用, 保持接口一致)
            max_results: 最大结果数
            min_score: 最低分数

        Returns:
            搜索结果列表
        """
        try:
            results = self._manager.search(
                query=query,
                max_results=max_results,
                min_score=min_score
            )
            logger.debug(f"[LongTermMemory] 搜索完成: query={query[:30]}..., results={len(results)}")
            return results
        except Exception as e:
            logger.error(f"[LongTermMemory] 搜索失败: {e}")
            return []

    def get_context(self, query: str = "", max_results: int = 5) -> str:
        """
        获取记忆上下文

        Args:
            query: 当前输入 (用于语义检索)
            max_results: 最大结果数

        Returns:
            格式化的记忆上下文文本
        """
        try:
            context = self._manager.load_session_context(query=query, max_results=max_results)
            logger.debug(f"[LongTermMemory] 获取上下文: length={len(context)}")
            return context
        except Exception as e:
            logger.error(f"[LongTermMemory] 获取上下文失败: {e}")
            return ""

    # ── 代理方法 (透传到 MemoryManager) ────────────────────────────────

    def write_memory(self, content: str, append: bool = True) -> None:
        """写入长期记忆 (MEMORY.md)"""
        self._manager.write_memory(content, append=append)

    def write_daily_log(self, content: str) -> None:
        """写入每日日志"""
        self._manager.write_daily_log(content)

    def sync_search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """同步搜索 (不转换为 MemoryTurn)"""
        return self._manager.search(query, max_results=max_results)

    def should_flush(self, current_tokens: int, context_window: int) -> bool:
        """判断是否需要触发记忆 flush"""
        return self._manager.should_flush(current_tokens, context_window)

    def sync(self) -> None:
        """全量同步索引"""
        self._manager.sync()

    def close(self) -> None:
        """关闭存储"""
        self._manager.close()
