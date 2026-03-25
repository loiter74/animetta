"""
口语化记忆处理 Worker

独立的异步后台服务，使用 LLM 将原始对话转换为口语化记忆版本。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass
from enum import Enum

from loguru import logger

from .prompts import MemoryPrompts


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OralTask:
    """口语化转换任务"""
    task_id: str
    text: str
    content_hash: str
    session_id: str
    timestamp: float
    callback: Optional[Callable[[str], None]] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0


class OralMemoryWorker:
    """
    口语化记忆处理 Worker

    独立异步后台服务，负责：
    1. 从队列接收待处理文本
    2. 调用 LLM 生成口语化版本
    3. 回调通知或缓存结果
    4. 失败重试和错误处理
    """

    def __init__(
        self,
        llm_client=None,
        queue_size: int = 1000,
        max_retries: int = 2,
        batch_size: int = 5,
        batch_timeout: float = 2.0,
    ):
        """
        初始化 Worker

        Args:
            llm_client: LLM 客户端（需实现 chat 方法）
            queue_size: 队列大小上限
            max_retries: 失败重试次数
            batch_size: 批量处理大小
            batch_timeout: 批量等待超时（秒）
        """
        self._llm_client = llm_client
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._max_retries = max_retries
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout

        # 结果缓存 (content_hash -> oral_version)
        self._result_cache: Dict[str, str] = {}

        # 任务追踪 (task_id -> Task)
        self._tasks: Dict[str, OralTask] = {}

        # Worker 控制
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False

        # 统计
        self._stats = {
            "total_received": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cache_hits": 0,
        }

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def stats(self) -> Dict[str, int]:
        return self._stats.copy()

    async def start(self) -> None:
        """启动 Worker"""
        if self._is_running:
            logger.warning("[OralMemoryWorker] Worker 已在运行")
            return

        self._is_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("[OralMemoryWorker] Worker 已启动")

    async def stop(self) -> None:
        """停止 Worker"""
        if not self._is_running:
            return

        logger.info("[OralMemoryWorker] 正在停止 Worker...")
        self._is_running = False

        # 发送结束信号
        try:
            await asyncio.wait_for(self._queue.put(None), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("[OralMemoryWorker] 停止信号发送超时")

        # 等待 Worker 完成
        if self._worker_task and not self._worker_task.done():
            try:
                await asyncio.wait_for(self._worker_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("[OralMemoryWorker] Worker 停止超时，强制取消")
                self._worker_task.cancel()

        logger.info("[OralMemoryWorker] Worker 已停止")

    async def submit(
        self,
        text: str,
        content_hash: str,
        session_id: str = "default",
        callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        提交口语化转换任务

        Args:
            text: 原始文本
            content_hash: 内容哈希（用于缓存和去重）
            session_id: 会话 ID
            callback: 完成后的回调函数（在主线程调用）

        Returns:
            任务 ID
        """
        # 检查缓存
        if content_hash in self._result_cache:
            self._stats["total_cache_hits"] += 1
            cached_result = self._result_cache[content_hash]
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(cached_result)
                    else:
                        callback(cached_result)
                except Exception as e:
                    logger.error(f"[OralMemoryWorker] 回调执行失败: {e}")
            logger.debug(f"[OralMemoryWorker] 缓存命中: {content_hash[:12]}...")
            return f"cached_{content_hash[:12]}"

        # 创建任务
        task_id = f"{session_id}_{content_hash[:12]}_{datetime.now().timestamp()}"
        task = OralTask(
            task_id=task_id,
            text=text,
            content_hash=content_hash,
            session_id=session_id,
            timestamp=datetime.now().timestamp(),
            callback=callback,
        )

        # 加入队列
        try:
            await asyncio.wait_for(self._queue.put(task), timeout=5.0)
            self._tasks[task_id] = task
            self._stats["total_received"] += 1
            logger.debug(f"[OralMemoryWorker] 任务已提交: {task_id}")
            return task_id
        except asyncio.TimeoutError:
            logger.error("[OralMemoryWorker] 队列已满，任务提交失败")
            raise

    async def get_result(self, task_id: str, timeout: float = 30.0) -> Optional[str]:
        """
        等待任务结果

        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）

        Returns:
            口语化结果，超时或失败返回 None
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if task.status == TaskStatus.COMPLETED:
                return task.result
            elif task.status == TaskStatus.FAILED:
                return None

            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning(f"[OralMemoryWorker] 等待结果超时: {task_id}")
                return None

            await asyncio.sleep(0.1)

    def get_cached(self, content_hash: str) -> Optional[str]:
        """获取缓存的口语化版本"""
        return self._result_cache.get(content_hash)

    async def _worker_loop(self) -> None:
        """Worker 主循环"""
        logger.info("[OralMemoryWorker] Worker 循环已启动")

        while self._is_running:
            try:
                # 批量获取任务
                batch = await self._fetch_batch()
                if not batch:
                    # 收到结束信号
                    break

                # 处理批次
                await self._process_batch(batch)

            except asyncio.CancelledError:
                logger.info("[OralMemoryWorker] Worker 被取消")
                break
            except Exception as e:
                logger.error(f"[OralMemoryWorker] Worker 循环错误: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # 错误后稍作等待

        logger.info("[OralMemoryWorker] Worker 循环已退出")

    async def _fetch_batch(self) -> list[OralTask]:
        """批量获取任务"""
        tasks = []

        # 等待第一个任务
        try:
            first_task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            if first_task is None:  # 结束信号
                return []
            tasks.append(first_task)
        except asyncio.TimeoutError:
            return []  # 没有任务，继续循环

        # 收集更多任务（直到达到批次大小或超时）
        deadline = asyncio.get_event_loop().time() + self._batch_timeout
        while len(tasks) < self._batch_size and asyncio.get_event_loop().time() < deadline:
            try:
                remaining = deadline - asyncio.get_event_loop().time()
                task = await asyncio.wait_for(self._queue.get(), timeout=max(0.01, remaining))
                if task is None:
                    return []  # 结束信号
                tasks.append(task)
            except asyncio.TimeoutError:
                break

        return tasks

    async def _process_batch(self, batch: list[OralTask]) -> None:
        """批量处理任务"""
        logger.debug(f"[OralMemoryWorker] 处理批次: {len(batch)} 个任务")

        # 并行处理所有任务
        processing_tasks = [self._process_single_task(task) for task in batch]
        await asyncio.gather(*processing_tasks, return_exceptions=True)

    async def _process_single_task(self, task: OralTask) -> None:
        """处理单个任务"""
        task.status = TaskStatus.PROCESSING

        try:
            # 调用 LLM 生成口语化版本
            oral_version = await self._call_llm(task.text)

            if oral_version:
                # 成功
                task.result = oral_version
                task.status = TaskStatus.COMPLETED
                self._result_cache[task.content_hash] = oral_version
                self._stats["total_completed"] += 1

                logger.debug(f"[OralMemoryWorker] 任务完成: {task.task_id}")

                # 执行回调
                if task.callback:
                    try:
                        if asyncio.iscoroutinefunction(task.callback):
                            await task.callback(oral_version)
                        else:
                            task.callback(oral_version)
                    except Exception as e:
                        logger.error(f"[OralMemoryWorker] 回调执行失败: {e}")
            else:
                # 失败
                await self._handle_failure(task, "LLM 返回空结果")

        except Exception as e:
            logger.error(f"[OralMemoryWorker] 任务处理失败: {task.task_id}, error: {e}")
            await self._handle_failure(task, str(e))

    async def _call_llm(self, text: str) -> Optional[str]:
        """
        调用 LLM 生成口语化版本

        Args:
            text: 原始文本

        Returns:
            口语化版本，失败返回 None
        """
        if not self._llm_client:
            # 没有 LLM 客户端，返回 None（会使用规则后备方案）
            return None

        try:
            # 构建 prompt
            prompt = MemoryPrompts.build_oral_memory_prompt(text)

            # 调用 LLM
            response = await self._llm_client.chat(
                user_input=prompt,
                system_prompt=None,  # prompt 已包含完整指令
            )

            if response:
                # 清理响应
                return self._clean_response(response)
            return None

        except Exception as e:
            logger.warning(f"[OralMemoryWorker] LLM 调用失败: {e}")
            return None

    def _clean_response(self, response: str) -> str:
        """清理 LLM 响应"""
        # 去除引号
        text = response.strip()
        if len(text) >= 2:
            if (text.startswith('"') and text.endswith('"')) or \
               (text.startswith("'") and text.endswith("'")):
                text = text[1:-1]

        # 去除可能的 markdown 标记
        if text.startswith("```"):
            lines = text.split('\n')
            if len(lines) > 1:
                text = '\n'.join(lines[1:-1]) if text.endswith("```") else '\n'.join(lines[1:])

        return text.strip()

    async def _handle_failure(self, task: OralTask, error: str) -> None:
        """处理任务失败"""
        task.error = error
        task.retry_count += 1

        if task.retry_count <= self._max_retries:
            # 重试
            logger.info(f"[OralMemoryWorker] 重试任务: {task.task_id}, 次数: {task.retry_count}")
            task.status = TaskStatus.PENDING
            await self._queue.put(task)
        else:
            # 最终失败
            task.status = TaskStatus.FAILED
            self._stats["total_failed"] += 1
            logger.warning(f"[OralMemoryWorker] 任务最终失败: {task.task_id}")

    async def clear_cache(self) -> None:
        """清空缓存"""
        self._result_cache.clear()
        logger.info("[OralMemoryWorker] 缓存已清空")

    def get_queue_size(self) -> int:
        """获取当前队列大小"""
        return self._queue.qsize()

    def get_task_count(self) -> int:
        """获取追踪中的任务数量"""
        return len(self._tasks)
