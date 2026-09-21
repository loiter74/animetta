"""Engine-neutral private exploration contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Point(Contract):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class View(Point):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    height: float = Field(ge=1, le=40_000_000)
    bounds: tuple[float, float, float, float] | None = None
    heading: float | None = None
    pitch: float | None = None


class Source(Contract):
    name: str
    url: str
    attribution: str


class Candidate(View):
    id: str
    name: str
    source: Source
    category: str | None = None


class Interpretation(Contract):
    intent: Literal["search", "observe", "pause", "continue", "retract", "identify"] = "search"
    query: str = Field(default="", max_length=200)


class Control(Contract):
    operation: Literal[
        "open",
        "text",
        "audio",
        "pause",
        "continue",
        "select",
        "close",
        "playback_started",
        "playback_ended",
        "playback_failed",
    ]
    conversation_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    control_revision: int = Field(ge=0)
    text: str | None = Field(default=None, max_length=4000)
    candidate_id: str | None = Field(default=None, max_length=128)
    point: Point | None = None
    task_id: str | None = None
    voice_enabled: bool | None = None
    audio_data: str | None = Field(default=None, max_length=11_000_000)
    format: Literal["wav", "webm", "ogg"] | None = None


class Context(Contract):
    conversation_id: str
    control_revision: int = Field(ge=0)
    view_revision: int = Field(ge=0)
    view: View
    selected_point: Point | None = None


class Result(Contract):
    conversation_id: str
    control_revision: int = Field(ge=0)
    view_revision: int = Field(ge=0)
    action_id: str
    status: Literal["accepted", "arrived", "ready", "degraded", "failed", "cancelled"]
    view: View | None = None


class EarthError(Exception):
    """Content-free error safe for private transport responses."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

    def payload(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}
