"""Pipeline 统计 Callback Handler - 采集 LangGraph 节点执行耗时"""

import time
import uuid
import asyncio
import threading
from typing import Any, Dict, Optional
from loguru import logger

from langchain_core.callbacks import BaseCallbackHandler

from .stats_store import get_stats_store

# 已知的业务节点名（过滤 LangGraph 内部节点）
KNOWN_NODES = frozenset({
    "asr_node", "llm_node", "tts_node", "emotion_node",
    "output_node", "tool_node",
    "asr", "llm", "tts", "emotion", "output", "tools",
})


class StatsCallbackHandler(BaseCallbackHandler):
    """采集 LangGraph 节点执行耗时"""

    def __init__(self):
        self._active_spans: Dict[str, dict] = {}
        self._trace_id: Optional[str] = None
        self._trace_start: Optional[float] = None
        self._lock = threading.Lock()

    def start_trace(self, session_id: str, input_type: str, user_text: str) -> str:
        """开始一次 trace（在 orchestrator 层调用）"""
        self._trace_id = str(uuid.uuid4())
        self._trace_start = time.perf_counter()
        self._active_spans.clear()
        self._schedule_async(
            self._async_create_trace(session_id, input_type, user_text)
        )
        return self._trace_id

    def finish_trace(self, status: str = "success", error_msg: str = None):
        """结束一次 trace"""
        if not self._trace_id or not self._trace_start:
            return
        duration = (time.perf_counter() - self._trace_start) * 1000
        self._schedule_async(
            self._async_finish_trace(duration, status, error_msg)
        )

    # -- LangChain Callback 接口 --

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], *,
        run_id: Any, parent_run_id: Any = None, **kwargs: Any
    ) -> None:
        # Guard: LangGraph internal chains may pass None serialized/inputs
        if not serialized or not isinstance(serialized, dict):
            return
        if inputs is None:
            inputs = {}
        name = serialized.get("name") or kwargs.get("name") or ""
        if name not in KNOWN_NODES:
            return

        with self._lock:
            span_id = str(uuid.uuid4())
            self._active_spans[str(run_id)] = {
                "span_id": span_id,
                "node_name": name,
                "start_time": time.perf_counter(),
                "trace_id": self._trace_id,
            }

        input_summary = self._summarize_input(name, inputs)
        self._schedule_async(
            self._async_create_span(span_id, self._trace_id, name, input_summary)
        )

    def on_chain_end(
        self, outputs: Dict[str, Any], *, run_id: Any, **kwargs: Any
    ) -> None:
        run_key = str(run_id)
        with self._lock:
            span_info = self._active_spans.pop(run_key, None)
            if not span_info:
                return

        duration = (time.perf_counter() - span_info["start_time"]) * 1000
        output_summary = self._summarize_output(span_info["node_name"], outputs)
        self._schedule_async(
            self._async_finish_span(span_info["span_id"], duration, output_summary)
        )

    def on_chain_error(
        self, error: BaseException, *, run_id: Any, **kwargs: Any
    ) -> None:
        run_key = str(run_id)
        with self._lock:
            span_info = self._active_spans.pop(run_key, None)
            if not span_info:
                return

        duration = (time.perf_counter() - span_info["start_time"]) * 1000
        self._schedule_async(
            self._async_finish_span(
                span_info["span_id"], duration, str(error)[:200], status="error"
            )
        )

    # -- 异步存储方法 --

    async def _async_create_trace(
        self, session_id: str, input_type: str, user_text: str
    ):
        try:
            store = await get_stats_store()
            await store.create_trace(self._trace_id, session_id, input_type, user_text)
        except Exception as e:
            logger.warning(f"[StatsHandler] 创建 trace 失败: {e}")

    async def _async_finish_trace(
        self, duration: float, status: str, error_msg: str
    ):
        try:
            store = await get_stats_store()
            await store.finish_trace(self._trace_id, duration, status, error_msg)
        except Exception as e:
            logger.warning(f"[StatsHandler] 完成 trace 失败: {e}")

    async def _async_create_span(
        self, span_id: str, trace_id: str, node_name: str, input_summary: str
    ):
        try:
            store = await get_stats_store()
            await store.create_span(span_id, trace_id, node_name, input_summary=input_summary)
        except Exception as e:
            logger.warning(f"[StatsHandler] 创建 span 失败: {e}")

    async def _async_finish_span(
        self, span_id: str, duration: float, output_summary: str,
        status: str = "success",
    ):
        try:
            store = await get_stats_store()
            await store.finish_span(span_id, duration, status, output_summary)
        except Exception as e:
            logger.warning(f"[StatsHandler] 完成 span 失败: {e}")

    # -- 辅助方法 --

    @staticmethod
    def _schedule_async(coro):
        """在线程安全的异步上下文中调度协程"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(coro)
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(coro)

    @staticmethod
    def _summarize_input(node_name: str, inputs: Dict) -> str:
        state = inputs.get("state") or inputs
        if isinstance(state, dict):
            text = state.get("user_text", "")
            if text:
                return text[:200]
        return ""

    @staticmethod
    def _summarize_output(node_name: str, outputs: Dict) -> str:
        if isinstance(outputs, dict):
            for key in ("response_text", "user_text", "emotion"):
                text = outputs.get(key, "")
                if text:
                    return str(text)[:200]
        return ""
