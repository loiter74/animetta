"""Authenticated private Earth transport and session composition boundary."""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langsmith import tracing_context
from pydantic import ValidationError

from animetta.orchestration.graph.earth_graph import build_earth_graph
from animetta.orchestration.socket_events import event_name
from animetta.services.earth import Context, Control, EarthError, Result
from animetta.services.earth.audio import volume_envelope
from animetta.services.earth.exploration import ExplorationService
from animetta.services.earth.factory import create_search

from ..security import PUBLIC_LIVE_SOURCE


@dataclass
class EarthSession:
    sid: str
    owner: str
    conversation_id: str
    config: dict[str, Any]
    revision: int = 0
    tasks: set[asyncio.Task[Any]] = field(default_factory=set)
    timer: asyncio.TimerHandle | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class EarthHandlers:
    def __init__(self, sio: Any, base: Any, security: Any) -> None:
        self.sio, self.base, self.security = sio, base, security
        self.saver: Any = None
        self.graph: Any = None
        self.durable = False
        self.search: Any = None
        self.settings: dict[str, Any] | None = None
        self.sessions: dict[str, EarthSession] = {}
        self.owners: dict[tuple[str, str], str] = {}
        self.open_lock = asyncio.Lock()

    def _owner(self, sid: str) -> str:
        principal = self.security.socket_principal(sid)
        if principal is None or principal.source == PUBLIC_LIVE_SOURCE:
            raise EarthError("UNAUTHORIZED", "地球探索需要私密登录会话。")
        if principal.password_change_required:
            raise EarthError("PASSWORD_CHANGE_REQUIRED", "请先修改初始密码。")
        return str(principal.user_id or principal.session_id)

    def _session(self, sid: str, conversation_id: str, revision: int) -> EarthSession:
        owner = self._owner(sid)
        session = self.sessions.get(sid)
        if not session or session.owner != owner or session.conversation_id != conversation_id:
            raise EarthError("EARTH_NOT_OPEN", "请先打开地球探索。")
        if session.revision != revision:
            raise EarthError("STALE_CONTROL", "操作已过期，请使用最新视图。")
        return session

    async def _open(self, sid: str, control: Control, owner: str) -> dict[str, Any]:
        if self.settings is None:
            loaded = await self.base.session_manager._load_tools_config()
            self.settings = loaded.get("config", {}).get("earth", {})
        if not self.settings.get("enabled", False) or os.getenv(
            "ANIMETTA_EARTH_ENABLED", "true"
        ).lower() not in {"true", "1"}:
            raise EarthError("EARTH_DISABLED", "地球探索未启用。")
        if self.search is None:
            self.search = create_search(
                {
                    **self.settings,
                    **(
                        {"endpoint": os.environ["ANIMETTA_EARTH_PHOTON_URL"]}
                        if "ANIMETTA_EARTH_PHOTON_URL" in os.environ
                        else {}
                    ),
                }
            )
        if self.graph is None:
            runtime = getattr(self.base.session_manager, "checkpoint_runtime", None)
            saver = getattr(runtime, "saver", None)
            self.saver = saver if saver is not None else InMemorySaver()
            self.durable = saver is not None
            self.graph = build_earth_graph(self.saver)
        claimed = self.owners.get((owner, control.conversation_id))
        if claimed and claimed != sid:
            raise EarthError("EARTH_OWNED", "此探索已由另一个页面控制。")
        if sid in self.sessions:
            existing = self.sessions[sid]
            if existing.conversation_id == control.conversation_id:
                return {"ok": True, "state": await self._snapshot(existing)}
            await self.disconnect(sid)
        ctx = await self.base.get_or_create_context(sid)
        service = ExplorationService(
            self.search,
            clock=time.time,
            llm=ctx.llm_engine,
            tts=ctx.tts_engine,
            asr=ctx.asr_engine,
            volumes=volume_envelope,
        )
        key = hashlib.sha256(f"{owner}:{control.conversation_id}".encode()).hexdigest()
        session = EarthSession(
            sid,
            owner,
            control.conversation_id,
            {
                "configurable": {
                    "thread_id": f"program:earth:{key}",
                    "earth_service": service,
                }
            },
        )
        self.sessions[sid] = session
        self.owners[(owner, control.conversation_id)] = sid
        event = control.model_dump(exclude_none=True)
        event["control_revision"] = 0
        return await self._dispatch(session, event, initial=True)

    async def control(self, sid: str, data: dict[str, Any]) -> dict[str, Any]:
        try:
            control = Control.model_validate(data)
            owner = self._owner(sid)
            if control.operation == "open":
                async with self.open_lock:
                    return await self._open(sid, control, owner)
            session = self._session(sid, control.conversation_id, control.control_revision)
            if control.operation == "close":
                result = await self._replace(session, control.model_dump(exclude_none=True))
                await self.disconnect(sid)
                return result
            event = control.model_dump(exclude_none=True)
            if control.operation in {"text", "audio", "select", "pause", "continue"}:
                return await self._replace(session, event)
            return await self._dispatch(session, event)
        except (EarthError, ValidationError) as exc:
            if isinstance(exc, EarthError) and exc.code == "STALE_CONTROL":
                existing = self.sessions.get(sid)
                if existing is not None:
                    return {**self._error(exc), "state": await self._snapshot(existing)}
            return self._error(exc)

    async def context(self, sid: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self._receipt(sid, data, Context, "context")

    async def result(self, sid: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self._receipt(sid, data, Result, "result")

    async def _receipt(
        self, sid: str, data: dict[str, Any], model: Any, operation: str
    ) -> dict[str, Any]:
        try:
            value = model.model_validate(data)
            session = self._session(sid, value.conversation_id, value.control_revision)
            return await self._dispatch(
                session, {**value.model_dump(exclude_none=True), "operation": operation}
            )
        except (EarthError, ValidationError) as exc:
            return self._error(exc)

    async def _replace(self, session: EarthSession, event: dict[str, Any]) -> dict[str, Any]:
        session.revision += 1
        if session.timer:
            session.timer.cancel()
            session.timer = None
        tasks = tuple(session.tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        event["control_revision"] = session.revision
        # Invalidate client camera/audio immediately, including while search is pending.
        await self._emit(
            session,
            "command",
            {
                "conversation_id": session.conversation_id,
                "control_revision": session.revision,
                "action_id": f"cancel-{session.revision}",
                "kind": "cancel",
            },
        )
        return await self._dispatch(session, event, replace=True)

    async def _dispatch(
        self,
        session: EarthSession,
        event: dict[str, Any],
        *,
        initial: bool = False,
        replace: bool = False,
    ) -> dict[str, Any]:
        revision = session.revision

        async def run() -> dict[str, Any]:
            async with session.lock:
                if revision != session.revision:
                    raise EarthError("STALE_CONTROL", "操作已被新的输入取消。")
                snapshot = await self.graph.aget_state(session.config)
                if initial or not snapshot.values:
                    await self.graph.ainvoke({"snapshot": {}, "event": event}, session.config)
                elif replace or not snapshot.tasks or not any(t.interrupts for t in snapshot.tasks):
                    await self.graph.aupdate_state(session.config, {"event": event}, as_node="wait")
                    await self.graph.ainvoke(None, session.config)
                else:
                    await self.graph.ainvoke(Command(resume=event), session.config)
                if revision != session.revision:
                    raise EarthError("STALE_CONTROL", "操作已被新的输入取消。")
                state = await self._snapshot(session)
                stored = (await self.graph.aget_state(session.config)).values["snapshot"]
                await self._emit(session, "state", state)
                for output in stored.get("outbox", []):
                    await self._emit(session, output["event"], output["payload"])
                self._schedule(session, state)
                return {"ok": True, "state": state}

        with tracing_context(enabled=False):
            task = asyncio.create_task(run())
        session.tasks.add(task)
        try:
            return await task
        except asyncio.CancelledError:
            return {"ok": False, "error": {"code": "CANCELLED", "message": "操作已取消。"}}
        except EarthError as exc:
            return await self._failure(session, revision, exc)
        except Exception:
            return await self._failure(
                session, revision, EarthError("EARTH_UNAVAILABLE", "探索服务暂不可用。")
            )
        finally:
            session.tasks.discard(task)

    async def _failure(
        self, session: EarthSession, revision: int, exc: EarthError
    ) -> dict[str, Any]:
        if revision != session.revision or self.sessions.get(session.sid) is not session:
            return self._error(exc)
        saved = await self.graph.aget_state(session.config)
        service = session.config["configurable"]["earth_service"]
        snapshot = {
            "conversation_id": session.conversation_id,
            "candidates": [],
            "transcript": [],
            "capabilities": {
                "search": True,
                "voice": service.tts is not None,
                "asr": service.asr is not None,
                "vision": False,
                "auto_search": False,
            },
            **saved.values.get("snapshot", {}),
            "phase": "paused",
            "control_revision": revision,
            "error": exc.payload(),
            "outbox": [],
            "feedback_deadline": None,
            "task_id": None,
            "action_id": None,
        }
        await self.graph.aupdate_state(session.config, {"snapshot": snapshot}, as_node="apply")
        state = await self._snapshot(session)
        self._schedule(session, state)
        await self._emit(session, "state", state)
        return {**self._error(exc), "state": state}

    async def _snapshot(self, session: EarthSession) -> dict[str, Any]:
        saved = await self.graph.aget_state(session.config)
        state = saved.values.get("snapshot", {})
        fields = (
            "conversation_id",
            "phase",
            "candidates",
            "selected",
            "transcript",
            "action_id",
            "task_id",
            "feedback_deadline",
            "capabilities",
            "error",
            "view_revision",
        )
        return {
            **{
                key: state[key]
                for key in fields
                if key in state and (key != "selected" or state[key] is not None)
            },
            "control_revision": session.revision,
            "checkpoint_durable": self.durable,
        }

    async def _emit(self, session: EarthSession, kind: str, payload: dict[str, Any]) -> None:
        if self.sessions.get(session.sid) is session and self._owner(session.sid) == session.owner:
            await self.sio.emit(event_name("earth", kind), payload, to=session.sid)

    def _schedule(self, session: EarthSession, state: dict[str, Any]) -> None:
        if session.timer:
            session.timer.cancel()
            session.timer = None
        deadline = state.get("feedback_deadline")
        if deadline is None:
            return
        revision = session.revision

        def wake() -> None:
            if self.sessions.get(session.sid) is session and session.revision == revision:
                asyncio.create_task(
                    self._dispatch(session, {"operation": "tick", "control_revision": revision})
                )

        session.timer = asyncio.get_running_loop().call_later(max(0, deadline - time.time()), wake)

    async def disconnect(self, sid: str) -> None:
        session = self.sessions.pop(sid, None)
        if session is None:
            return
        self.owners.pop((session.owner, session.conversation_id), None)
        session.revision += 1
        if session.timer:
            session.timer.cancel()
        tasks = tuple(session.tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.saver.adelete_thread(session.config["configurable"]["thread_id"])

    @staticmethod
    def _error(exc: EarthError | ValidationError) -> dict[str, Any]:
        error = (
            exc.payload()
            if isinstance(exc, EarthError)
            else {"code": "INVALID_PAYLOAD", "message": "探索操作格式不正确。"}
        )
        return {"ok": False, "error": error}
