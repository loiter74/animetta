"""Session-injected exploration operations, called only by the Earth graph."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from .audio import normalize_asr_audio
from .contracts import EarthError, Interpretation, View
from .domain import ExplorationRules, explicit_intent, fallback_query
from .interface import GeographySearch


class ExplorationService:
    def __init__(
        self,
        search: GeographySearch,
        *,
        clock: Callable[[], float],
        llm: Any = None,
        tts: Any = None,
        asr: Any = None,
        volumes: Callable[[bytes, str], list[float]] | None = None,
        rules: ExplorationRules | None = None,
    ) -> None:
        self.search = search
        self.clock = clock
        self.llm = llm
        self.tts = tts
        self.asr = asr
        self.volumes = volumes
        self.rules = rules or ExplorationRules()

    async def apply(
        self,
        previous: dict[str, Any],
        event: dict[str, Any],
        tool_factory: Any = None,
    ) -> dict[str, Any]:
        state = {**previous, "outbox": [], "error": None}
        if event.get("voice_enabled") is not None:
            state["voice_enabled"] = event["voice_enabled"]
        tools = tool_factory(state) if tool_factory else None
        operation = event["operation"]
        if operation == "audio":
            if self.asr is None:
                raise EarthError("ASR_UNAVAILABLE", "语音识别暂不可用，请使用文字。")
            try:
                raw = base64.b64decode(event.get("audio_data", ""), validate=True)
                if not raw or len(raw) > 8_000_000:
                    raise ValueError("invalid audio size")
                async with asyncio.timeout(30):
                    wav = await normalize_asr_audio(raw, event.get("format", "wav"))
                    text = await self.asr.transcribe(wav, audio_format="wav")
            except Exception as exc:
                raise EarthError("ASR_UNAVAILABLE", "语音识别失败，请使用文字。") from exc
            event = {
                "operation": "text",
                "text": text,
                "control_revision": event["control_revision"],
            }
            operation = "text"
        now = self.clock()
        state["control_revision"] = event["control_revision"]
        if operation == "open":
            state.update(
                conversation_id=event["conversation_id"],
                phase="paused",
                candidates=[],
                transcript=[],
                steps=0,
                started=now,
                selected=None,
                view_revision=0,
                voice_enabled=event.get("voice_enabled", False),
                feedback_deadline=None,
                capabilities={
                    "search": True,
                    "voice": self.tts is not None,
                    "vision": False,
                    "auto_search": False,
                    "asr": self.asr is not None,
                },
            )
        elif operation in {"pause", "close"}:
            state.update(
                phase="closed" if operation == "close" else "paused",
                feedback_deadline=None,
                task_id=None,
                action_id=None,
            )
            self._emit(state, "command", {"kind": "cancel", "action_id": str(uuid4())})
        elif operation == "text":
            text = str(event.get("text") or "").strip()
            if not text:
                raise EarthError("INVALID_QUERY", "请输入地名或地理线索。")
            state["transcript"] = [*state.get("transcript", []), {"role": "user", "text": text}][
                -40:
            ]
            state.update(action_id=None, task_id=None, feedback_deadline=None)
            intent = await self._interpret(text, state)
            if intent.intent == "pause":
                state["phase"] = "paused"
                self._say(state, "好，我停在这里，等你。")
            elif intent.intent == "retract":
                state.update(
                    phase="waiting_input", selected=None, candidates=[], selected_point=None
                )
                self._say(state, "已撤回上一个地点判断，镜头保持不动。你可以补充线索或重新指认。")
            elif intent.intent == "continue":
                self._continue(state)
            elif intent.intent == "identify":
                state.update(phase="waiting_identification")
                self._say(
                    state,
                    "我先保持这个视角。请点一下你认出的道路或位置；这只记录你的线索，不会认定为住址。",
                )
            elif intent.intent == "observe" or not intent.query:
                state.update(phase="waiting_input")
                observed = await tools("earth_observe", {}) if tools else state
                selected = observed.get("selected")
                self._say(
                    state,
                    f"当前选定地点是{selected['name']}，来源为{selected['source']['name']}。"
                    + (f"来源分类为 {selected['category']}。" if selected.get("category") else "")
                    + "目前没有获授权的图像分析或更细的用途资料，不能仅凭画面确认具体建筑或道路用途。"
                    if selected
                    else "告诉我一个你记得的地名，或直接在地图上点选；我不会猜测你的住址。",
                )
            else:
                candidates = (
                    await tools("earth_search", {"query": intent.query})
                    if tools
                    else [c.model_dump() for c in await self.search.search(intent.query)]
                )
                state.update(phase="waiting_selection", selected=None, candidates=candidates)
                self._say(
                    state,
                    "找到这些地点，请选择与你记忆相符的一个。"
                    if candidates
                    else "没有找到明确匹配，可以补充地区名称或直接在地图上点选。",
                )
        elif operation == "select":
            selected = next(
                (c for c in state.get("candidates", []) if c["id"] == event.get("candidate_id")),
                None,
            )
            if event.get("point"):
                state.update(
                    selected_point=event["point"],
                    phase="waiting_identification",
                    action_id=None,
                    task_id=None,
                    feedback_deadline=None,
                )
                self._say(
                    state,
                    "记下了你点的位置，视角保持不动。这是一条待确认的线索；你还记得路名或附近的标志吗？",
                )
                return state
            if not selected:
                raise EarthError("CANDIDATE_NOT_FOUND", "请重新选择当前候选地点。")
            state.update(
                selected=selected,
                selected_point=None,
                steps=0,
                started=now,
                navigation_reason=f"根据你选择的候选，先把 {selected['name']} 的范围放到画面中，方便核对周围地形。",
            )
            if tools:
                await tools("earth_navigate", {"candidate_id": selected["id"]})
            else:
                self.navigate(state, selected)
        elif operation == "context":
            if event["view_revision"] >= state.get("view_revision", 0):
                state.update(view=event["view"], view_revision=event["view_revision"])
                if event.get("selected_point"):
                    state["selected_point"] = event["selected_point"]
        elif operation == "result":
            if event["action_id"] != state.get("action_id") or state["phase"] != "moving":
                return state
            if event["view_revision"] < state.get("view_revision", 0):
                return state
            state["view_revision"] = event["view_revision"]
            if event.get("view"):
                state["view"] = event["view"]
            status = event["status"]
            if status == "ready":
                await self._narrate(state)
            elif status in {"degraded", "failed", "cancelled"}:
                state.update(phase="paused", feedback_deadline=None)
                self._say(state, "画面尚未准备好，我先停在这里。你可以手动探索或继续。")
        elif operation == "playback_started":
            if (
                event.get("task_id") == state.get("task_id")
                and state["phase"] == "awaiting_playback"
            ):
                state.update(phase="playing", feedback_deadline=None)
        elif operation in {"playback_ended", "playback_failed"}:
            if event.get("task_id") != state.get("task_id"):
                return state
            if operation == "playback_ended" and state["phase"] == "playing":
                state.update(phase="feedback", feedback_deadline=now + self.rules.feedback_seconds)
            elif operation == "playback_failed" and state["phase"] in {
                "playing",
                "awaiting_playback",
            }:
                state.update(phase="reading", feedback_deadline=now + self.rules.reading_seconds)
        elif operation == "tick":
            deadline = state.get("feedback_deadline")
            if deadline is None or now < deadline:
                return state
            if state["phase"] == "reading":
                state.update(phase="feedback", feedback_deadline=now + self.rules.feedback_seconds)
            elif self.rules.can_continue(
                selected=bool(state.get("selected")),
                steps=state["steps"],
                started=state["started"],
                now=now,
                phase=state["phase"],
            ):
                self._zoom(state)
            else:
                state.update(phase="waiting_input", feedback_deadline=None)
        elif operation == "continue":
            self._continue(state)
        return state

    async def _interpret(self, text: str, state: dict[str, Any]) -> Interpretation:
        explicit = explicit_intent(text)
        if explicit:
            return Interpretation(intent=explicit)
        if self.llm is None:
            return Interpretation(query=fallback_query(text))
        messages = [
            {
                "role": "system",
                "content": "解析用户探索意图，只输出JSON。intent取search/observe/pause/continue/retract/identify。"
                "从用户已明确说出的地名提取检索词query，保留用户给出的地区上下文，不推断住址、道路名或坐标。"
                "不同层级的地名用空格分隔，不把城市、区县与地标连写成一个名称。"
                "用户明确切换城市或地区时，不沿用不兼容的旧地区；旧候选或讲解里的机构名称不是新线索。"
                "问当前地方是什么用observe，否定地点用retract，认出熟悉道路用identify，暂缓用pause。"
                '格式 {"intent":"search","query":"地名"}；没有明确地名时query为空。',
            },
            *[{"role": row["role"], "content": row["text"]} for row in state["transcript"][-10:]],
        ]
        try:
            result = ""
            async with asyncio.timeout(20):
                async for chunk in self.llm.chat_messages_stream(messages):
                    result += chunk
                    if len(result) > 4096:
                        raise ValueError("query too long")
            result = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            return Interpretation.model_validate(json.loads(result))
        except (ValueError, TypeError, NotImplementedError, TimeoutError):
            return Interpretation(query=fallback_query(text))

    def navigate(self, state: dict[str, Any], candidate: dict[str, Any]) -> None:
        target = View.model_validate(
            {
                key: candidate[key]
                for key in ("longitude", "latitude", "height", "bounds", "heading", "pitch")
                if key in candidate
            }
        ).model_dump(exclude_none=True)
        state.update(
            phase="moving",
            action_id=str(uuid4()),
            target=target,
            steps=state.get("steps", 0) + 1,
            feedback_deadline=None,
            task_id=None,
        )
        self._emit(
            state,
            "command",
            {
                "kind": "navigate",
                "action_id": state["action_id"],
                "target": target,
                "duration_seconds": 4.0,
            },
        )

    def _zoom(self, state: dict[str, Any]) -> None:
        target = {**(state.get("view") or state.get("target") or state["selected"])}
        previous_height = target["height"]
        target.update(height=max(400, target["height"] * 0.65), bounds=None)
        state["navigation_reason"] = (
            f"保持当前观察中心，把视高从约 {previous_height:.0f} 米降到 {target['height']:.0f} 米，"
            "让你更容易辨认道路、水岸或建筑的相对位置；具体名称仍需你确认。"
        )
        self.navigate(state, target)

    def _continue(self, state: dict[str, Any]) -> None:
        if state.get("selected_point"):
            state.update(phase="waiting_identification", feedback_deadline=None)
            self._say(state, "我会保持你指认的位置，先等你补充这条线索。")
        elif state.get("selected"):
            state.update(steps=0, started=self.clock())
            self._zoom(state)
        else:
            state["phase"] = "waiting_selection"

    async def _narrate(self, state: dict[str, Any]) -> None:
        text = (
            state.get("navigation_reason", "已完成这一步地图移动。")
            + "现在停下来，让你对照记忆。如果不对，可以直接拖动地图、重新输入或点选熟悉的位置。"
        )
        self._say(state, text)
        state["task_id"] = str(uuid4())
        payload: dict[str, Any] = {"task_id": state["task_id"], "text": text, "status": "text_only"}
        state.update(phase="reading", feedback_deadline=self.clock() + self.rules.reading_seconds)
        if state.get("voice_enabled") and self.tts is not None:
            try:
                async with asyncio.timeout(30):
                    data = await self.tts.synthesize(text)
                if not isinstance(data, bytes) or len(data) > 8_000_000:
                    raise ValueError("unsupported audio payload")
                payload.update(
                    status="ready",
                    audio={
                        "data": base64.b64encode(data).decode("ascii"),
                        "format": self.tts.audio_format,
                    },
                )
                if self.volumes:
                    try:
                        envelope = await asyncio.to_thread(
                            self.volumes, data, self.tts.audio_format
                        )
                        if envelope:
                            payload["audio"]["volumes"] = envelope
                    except Exception:
                        # Optional lip-sync analysis must not suppress valid speech.
                        pass
                state.update(phase="awaiting_playback", feedback_deadline=None)
            except Exception:
                # Text remains available; synthesis success is never a playback receipt.
                state["error"] = {
                    "code": "VOICE_UNAVAILABLE",
                    "message": "语音暂不可用，继续文字探索。",
                }
        self._emit(state, "narration", payload)

    @staticmethod
    def _say(state: dict[str, Any], text: str) -> None:
        state["transcript"] = [*state.get("transcript", []), {"role": "assistant", "text": text}][
            -40:
        ]

    @staticmethod
    def _emit(state: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
        state["outbox"].append(
            {
                "event": kind,
                "payload": {
                    "conversation_id": state["conversation_id"],
                    "control_revision": state["control_revision"],
                    **payload,
                },
            }
        )
