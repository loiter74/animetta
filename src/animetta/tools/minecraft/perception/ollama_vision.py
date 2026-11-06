"""Local Ollama vision client returning typed, never-raising verdicts."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

import httpx
from loguru import logger

from .models import PerceptionDanger, VisionVerdict

_DANGER_VALUES = {danger.value for danger in PerceptionDanger}
_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json_object(content: str) -> dict[str, Any] | None:
    """Parse the first JSON object from model output, tolerating code fences."""

    if not content:
        return None
    candidate = _FENCE_PATTERN.sub("", content.strip())
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _coerce_verdict(parsed: dict[str, Any], *, model: str) -> VisionVerdict:
    danger_raw = str(parsed.get("danger", "none")).strip().lower()
    danger = PerceptionDanger(danger_raw) if danger_raw in _DANGER_VALUES else PerceptionDanger.NONE
    raw_threats = parsed.get("threats", [])
    if not isinstance(raw_threats, list):
        raw_threats = []
    threats = tuple(str(item).strip()[:64] for item in raw_threats if str(item).strip())[:8]
    confidence_raw = parsed.get("confidence", 0.0)
    try:
        confidence = min(1.0, max(0.0, float(confidence_raw)))
    except (TypeError, ValueError):
        confidence = 0.0
    goal_plausible = parsed.get("goal_plausible")
    if not isinstance(goal_plausible, bool):
        goal_plausible = None
    scene_summary = str(parsed.get("scene_summary", ""))[:280]
    return VisionVerdict(
        available=True,
        danger=danger,
        scene_summary=scene_summary,
        threats=threats,
        goal_plausible=goal_plausible,
        confidence=confidence,
        model=model,
    )


def _unavailable(error: str, *, model: str) -> VisionVerdict:
    return VisionVerdict(
        available=False,
        danger=PerceptionDanger.NONE,
        model=model,
        error=error[:280],
    )


class OllamaVisionClient:
    """Chat-with-images client against a local Ollama HTTP endpoint."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5vl:7b",
        timeout_seconds: float = 12.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def judge(self, image_jpeg: bytes, prompt: str) -> VisionVerdict:
        """Return a typed verdict; every failure degrades to unavailable."""

        try:
            payload = {
                "model": self._model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [base64.b64encode(image_jpeg).decode("ascii")],
                    }
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 320},
            }
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
                response.raise_for_status()
                body = response.json()
            content = ""
            message = body.get("message")
            if isinstance(message, dict):
                content = str(message.get("content", ""))
            parsed = _extract_json_object(content)
            if parsed is None:
                logger.debug("perception vision response was not JSON: {!r}", content[:200])
                return _unavailable("vision response was not valid JSON", model=self._model)
            return _coerce_verdict(parsed, model=self._model)
        except Exception as exc:
            logger.debug("perception vision judge failed: {}", exc)
            return _unavailable(f"{type(exc).__name__}: {exc}", model=self._model)
