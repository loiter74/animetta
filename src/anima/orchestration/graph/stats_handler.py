"""Pipeline stats Callback Handler - collect LangGraph node execution timing"""

import time
import uuid
import asyncio
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, List, AsyncIterator
from loguru import logger

from langchain_core.callbacks import BaseCallbackHandler

from .stats_store import get_stats_store, StatsStore

# Known business node names (filter out LangGraph internal nodes)
KNOWN_NODES = frozenset({
    "asr_node", "llm_node", "tts_node", "emotion_node",
    "output_node", "tool_node",
    "asr", "llm", "tts", "emotion", "output", "tools",
})


# ---------------------------------------------------------------------------
# NodeTimer – lightweight sub-node checkpoint timer
# ---------------------------------------------------------------------------

class NodeTimer:
    """Records named checkpoints within a graph node.
    
    Usage inside any node::
    
        timer = NodeTimer("llm_node", trace_id, parent_span_id)
        with timer.checkpoint("rag_retrieval"):
            memories = await retrieve(...)
        with timer.checkpoint("llm_api_call"):
            response = await llm.chat(...)
        await timer.finish()
    
    All checkpoints are flushed to StatsStore on finish().
    """

    def __init__(
        self,
        node_name: str,
        trace_id: str,
        parent_span_id: Optional[str] = None,
    ):
        self.node_name = node_name
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self._checkpoints: List[dict] = []
        self._active: Optional[dict] = None
        self._done = False

    # -- context manager checkpoint (sync start async end) --

    @asynccontextmanager
    async def checkpoint(self, label: str) -> AsyncIterator[None]:
        """Time a sub-operation within the node."""
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._checkpoints.append({
                "label": label,
                "duration_ms": round(elapsed_ms, 2),
            })

    # -- manual timing helpers --

    def mark(self, label: str) -> None:
        """Record an instant checkpoint (zero duration marker)."""
        self._checkpoints.append({
            "label": label,
            "duration_ms": 0.0,
        })

    async def time(self, label: str, coro) -> Any:
        """Await *coro* while timing it under *label*."""
        started = time.perf_counter()
        try:
            return await coro
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._checkpoints.append({
                "label": label,
                "duration_ms": round(elapsed_ms, 2),
            })

    async def finish(self) -> None:
        """Write all buffered checkpoints as sub-spans and reset."""
        if self._done:
            return
        self._done = True
        if not self._checkpoints:
            return
        try:
            store = await get_stats_store()
            for cp in self._checkpoints:
                span_id = f"{self.trace_id}_{cp['label']}_{uuid.uuid4().hex[:8]}"
                await store.create_span(
                    span_id=span_id,
                    trace_id=self.trace_id,
                    node_name=f"{self.node_name}.{cp['label']}",
                    parent_span_id=self.parent_span_id,
                    input_summary="",
                )
                await store.finish_span(
                    span_id=span_id,
                    duration_ms=cp["duration_ms"],
                    status="success",
                )
        except Exception as e:
            logger.debug(f"[NodeTimer] flush failed: {e}")


class StatsCallbackHandler(BaseCallbackHandler):
    """Collect LangGraph node execution timing"""

    def __init__(self):
        self._active_spans: Dict[str, dict] = {}
        self._trace_id: Optional[str] = None
        self._trace_start: Optional[float] = None
        self._lock = threading.Lock()

    def start_trace(self, session_id: str, input_type: str, user_text: str) -> str:
        """Start a trace (called from orchestrator layer)"""
        self._trace_id = str(uuid.uuid4())
        self._trace_start = time.perf_counter()
        self._active_spans.clear()
        self._schedule_async(
            self._async_create_trace(session_id, input_type, user_text)
        )
        return self._trace_id

    def finish_trace(self, status: str = "success", error_msg: str = None):
        """Finish a trace"""
        if not self._trace_id or not self._trace_start:
            return
        duration = (time.perf_counter() - self._trace_start) * 1000
        self._schedule_async(
            self._async_finish_trace(duration, status, error_msg)
        )

    # -- LangChain Callback interface --

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

        # OTel metrics: node duration histogram
        try:
            from anima.tracing.metrics import get_node_duration
            metric = get_node_duration()
            if metric is not None:
                metric.observe(duration / 1000.0, {"node_name": span_info["node_name"]})
        except Exception:
            pass

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

        # OTel metrics: node error counter
        try:
            from anima.tracing.metrics import get_node_errors
            metric = get_node_errors()
            if metric is not None:
                metric.add(1, {"node_name": span_info["node_name"], "error_type": "exception"})
        except Exception:
            pass

    # -- Async storage methods --

    async def _async_create_trace(
        self, session_id: str, input_type: str, user_text: str
    ):
        try:
            store = await get_stats_store()
            await store.create_trace(self._trace_id, session_id, input_type, user_text)
        except Exception as e:
            logger.debug(f"[StatsHandler] Failed to create trace: {e}")

    async def _async_finish_trace(
        self, duration: float, status: str, error_msg: str
    ):
        try:
            store = await get_stats_store()
            await store.finish_trace(self._trace_id, duration, status, error_msg)
        except Exception as e:
            logger.warning(f"[StatsHandler] Failed to finish trace: {e}")

    async def _async_create_span(
        self, span_id: str, trace_id: str, node_name: str, input_summary: str
    ):
        try:
            store = await get_stats_store()
            await store.create_span(span_id, trace_id, node_name, input_summary=input_summary)
        except Exception as e:
            logger.warning(f"[StatsHandler] Failed to create span: {e}")

    async def _async_finish_span(
        self, span_id: str, duration: float, output_summary: str,
        status: str = "success",
    ):
        try:
            store = await get_stats_store()
            await store.finish_span(span_id, duration, status, output_summary)
        except Exception as e:
            logger.warning(f"[StatsHandler] Failed to finish span: {e}")

    # -- Helper methods --

    @staticmethod
    def _schedule_async(coro):
        """Schedule a coroutine in a thread-safe async context.
        
        Uses run_coroutine_threadsafe when a loop is running to avoid
        "loop already running" errors, and falls back to run_until_complete
        when no loop is available (e.g. in unit tests or startup).
        """
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, loop)
                return
        except RuntimeError:
            pass
        # No running loop — create one or use existing
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, loop)
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
