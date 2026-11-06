"""Ollama vision client: parsing, coercion, and graceful degradation."""

from __future__ import annotations

import base64

from animetta.tools.minecraft.perception import ollama_vision
from animetta.tools.minecraft.perception.models import PerceptionDanger
from animetta.tools.minecraft.perception.ollama_vision import (
    OllamaVisionClient,
    _coerce_verdict,
    _extract_json_object,
)


class TestExtractJsonObject:
    def test_plain_json_object(self) -> None:
        assert _extract_json_object('{"danger":"none"}') == {"danger": "none"}

    def test_fenced_json_object(self) -> None:
        content = '```json\n{"danger":"critical"}\n```'

        assert _extract_json_object(content) == {"danger": "critical"}

    def test_json_embedded_in_prose(self) -> None:
        content = '好的，评估结果：{"danger":"warning","threats":["岩浆"]} 以上。'

        assert _extract_json_object(content) == {"danger": "warning", "threats": ["岩浆"]}

    def test_empty_or_non_object_returns_none(self) -> None:
        assert _extract_json_object("") is None
        assert _extract_json_object("看起来很安全") is None
        assert _extract_json_object("[1,2,3]") is None


class TestCoerceVerdict:
    def test_unknown_danger_falls_back_to_none(self) -> None:
        verdict = _coerce_verdict({"danger": "catastrophic"}, model="m")

        assert verdict.danger is PerceptionDanger.NONE

    def test_threats_are_cleaned_and_capped(self) -> None:
        parsed = {
            "threats": ["", "  岩浆  ", *["x" * 100] * 9],
        }

        verdict = _coerce_verdict(parsed, model="m")

        assert len(verdict.threats) <= 8
        assert verdict.threats[0] == "岩浆"
        assert all(len(item) <= 64 for item in verdict.threats)

    def test_non_list_threats_become_empty(self) -> None:
        verdict = _coerce_verdict({"threats": "岩浆"}, model="m")

        assert verdict.threats == ()

    def test_confidence_is_clamped(self) -> None:
        high = _coerce_verdict({"confidence": 1.7}, model="m")
        low = _coerce_verdict({"confidence": -2}, model="m")
        bogus = _coerce_verdict({"confidence": "abc"}, model="m")

        assert high.confidence == 1.0
        assert low.confidence == 0.0
        assert bogus.confidence == 0.0

    def test_goal_plausible_requires_real_boolean(self) -> None:
        as_bool = _coerce_verdict({"goal_plausible": True}, model="m")
        as_text = _coerce_verdict({"goal_plausible": "false"}, model="m")

        assert as_bool.goal_plausible is True
        assert as_text.goal_plausible is None


class _StubResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"message": {"content": self._content}}


class _StubClient:
    next_response: _StubResponse | None = None
    instances: list[_StubClient] = []

    def __init__(self, **_kwargs: object) -> None:
        self.requests: list[dict[str, object]] = []
        self.response = type(self).next_response
        _StubClient.instances.append(self)

    async def __aenter__(self) -> _StubClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def post(self, url: str, *, json: dict[str, object]) -> _StubResponse:
        self.requests.append({"url": url, "json": json})
        assert self.response is not None
        return self.response


class TestOllamaVisionClientJudge:
    def setup_method(self) -> None:
        _StubClient.instances = []
        _StubClient.next_response = None

    async def test_connection_failure_degrades_to_unavailable(self) -> None:
        client = OllamaVisionClient(base_url="http://127.0.0.1:1", timeout_seconds=0.5)

        verdict = await client.judge(b"\xff\xd8not-really-jpeg", "评估画面")

        assert verdict.available is False
        assert verdict.danger is PerceptionDanger.NONE
        assert verdict.error is not None

    async def test_valid_json_response_parses_verdict(self, monkeypatch) -> None:
        _StubClient.next_response = _StubResponse(
            '{"danger":"critical","threats":["苦力怕贴身"],'
            '"scene_summary":"夜晚草地","confidence":0.9}'
        )
        monkeypatch.setattr(ollama_vision.httpx, "AsyncClient", _StubClient)

        verdict = await OllamaVisionClient().judge(b"image-bytes", "评估画面")

        assert verdict.available is True
        assert verdict.danger is PerceptionDanger.CRITICAL
        assert verdict.threats == ("苦力怕贴身",)
        assert verdict.confidence == 0.9
        assert verdict.model == "qwen2.5vl:7b"
        stub = _StubClient.instances[0]
        request = stub.requests[0]
        assert request["url"].endswith("/api/chat")
        payload = request["json"]
        assert payload["format"] == "json"
        assert payload["stream"] is False
        message = payload["messages"][0]  # type: ignore[index]
        assert message["images"] == [base64.b64encode(b"image-bytes").decode("ascii")]

    async def test_non_json_response_degrades_to_unavailable(self, monkeypatch) -> None:
        _StubClient.next_response = _StubResponse("画面看起来很安全")
        monkeypatch.setattr(ollama_vision.httpx, "AsyncClient", _StubClient)

        verdict = await OllamaVisionClient().judge(b"image-bytes", "评估画面")

        assert verdict.available is False
        assert verdict.error is not None
        assert "JSON" in verdict.error
