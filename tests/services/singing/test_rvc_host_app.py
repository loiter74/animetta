from __future__ import annotations

import asyncio
import base64
import gc
import importlib.util
import io
import json
import sys
import threading
import zipfile
from pathlib import Path
from typing import Any

import pytest
from starlette.responses import Response
from starlette.testclient import TestClient

# Load only the HTTP boundary: the package initializer imports the native Torch engine.
_app_path = Path(__file__).resolve().parents[3] / "src/animetta_rvc_host/app.py"
_app_spec = importlib.util.spec_from_file_location("_rvc_host_app_boundary_tests", _app_path)
assert _app_spec is not None and _app_spec.loader is not None
rvc_app = importlib.util.module_from_spec(_app_spec)
sys.modules[_app_spec.name] = rvc_app
_app_spec.loader.exec_module(rvc_app)
RVCService = rvc_app.RVCService
RVCServiceSettings = rvc_app.RVCServiceSettings
create_app = rvc_app.create_app

_separator_spec = importlib.util.spec_from_file_location(
    "_rvc_host_separator_boundary_tests", _app_path.with_name("separator.py")
)
assert _separator_spec is not None and _separator_spec.loader is not None
rvc_separator = importlib.util.module_from_spec(_separator_spec)
sys.modules[_separator_spec.name] = rvc_separator
_separator_spec.loader.exec_module(rvc_separator)


class FakeEngine:
    def __init__(self) -> None:
        self.preloaded = False
        self.closed = False
        self.payloads: list[bytes] = []

    async def preload(self) -> None:
        self.preloaded = True

    async def convert(self, audio: bytes, **_kwargs: Any) -> bytes:
        self.payloads.append(audio)
        return b"RIFF" + (b"x" * 64)

    async def close(self) -> None:
        self.closed = True


class FakeSeparator:
    model = "htdemucs"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.preloaded = False
        self.closed = False
        self.payloads: list[bytes] = []

    async def preload(self) -> None:
        self.preloaded = True

    async def separate(self, audio: bytes) -> Path:
        self.payloads.append(audio)
        session = self.root / "session"
        session.mkdir()
        archive_path = session / "stems.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("vocals.wav", b"RIFFvocals")
            archive.writestr("backing.wav", b"RIFFbacking")
        return archive_path

    async def close(self) -> None:
        self.closed = True


def test_host_rvc_publishes_identity_and_converted_audio() -> None:
    engine = FakeEngine()
    settings = RVCServiceSettings(
        api_key="secret",
        provider="rvc-webui-host",
        model="shige_utage.pth",
        revision="f8e22f8c",
        voice="shige_utage",
        sample_rate=40000,
        index="added_IVF677_shige_utage.index",
        index_revision="index-sha256",
    )
    service = RVCService(settings, engine)

    with TestClient(create_app(service)) as client:
        ready = client.get("/ready", headers={"Authorization": "Bearer secret"})
        converted = client.post(
            "/v1/convert",
            headers={"Authorization": "Bearer secret"},
            json={
                "model": "shige_utage.pth",
                "audio_base64": base64.b64encode(b"RIFF" + (b"s" * 64)).decode("ascii"),
                "f0_method": "rmvpe",
            },
        )

    assert ready.status_code == 200
    assert ready.json()["ready"] is True
    assert ready.json()["revision"] == "f8e22f8c"
    assert ready.json()["index"] == "added_IVF677_shige_utage.index"
    assert ready.json()["index_revision"] == "index-sha256"
    assert converted.status_code == 200
    assert converted.content == b"RIFF" + (b"x" * 64)
    assert converted.headers["x-rvc-model"] == "shige_utage.pth"
    assert converted.headers["x-rvc-revision"] == "f8e22f8c"
    assert engine.payloads == [b"RIFF" + (b"s" * 64)]
    assert engine.closed is True


def test_host_rvc_streams_authenticated_demucs_stems(tmp_path: Path) -> None:
    engine = FakeEngine()
    separator = FakeSeparator(tmp_path)
    settings = RVCServiceSettings(
        api_key="secret",
        provider="rvc-webui-host",
        model="shige_utage.pth",
        revision="f8e22f8c",
        voice="shige_utage",
        sample_rate=40000,
        separation_model="htdemucs",
    )
    service = RVCService(settings, engine, separator)

    with TestClient(create_app(service)) as client:
        ready = client.get("/ready", headers={"Authorization": "Bearer secret"})
        separated = client.post(
            "/v1/separate",
            headers={
                "Authorization": "Bearer secret",
                "Content-Type": "application/octet-stream",
                "X-Separation-Model": "htdemucs",
            },
            content=b"RIFF" + (b"s" * 64),
        )

    assert ready.json()["separation_ready"] is True
    assert ready.json()["separation_model"] == "htdemucs"
    assert separated.status_code == 200
    assert separated.headers["x-separation-model"] == "htdemucs"
    with zipfile.ZipFile(io.BytesIO(separated.content)) as archive:
        assert archive.read("vocals.wav") == b"RIFFvocals"
        assert archive.read("backing.wav") == b"RIFFbacking"
    assert separator.payloads == [b"RIFF" + (b"s" * 64)]
    assert separator.closed is True
    assert not (tmp_path / "session").exists()


def test_host_rvc_rejects_decoded_audio_over_the_bounded_limit(monkeypatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr(rvc_app, "MAX_RVC_AUDIO_BYTES", 64)
    settings = RVCServiceSettings(
        api_key="secret",
        provider="rvc-webui-host",
        model="shige_utage.pth",
        revision="f8e22f8c",
        voice="shige_utage",
        sample_rate=40000,
    )
    service = RVCService(settings, engine)

    with TestClient(create_app(service)) as client:
        response = client.post(
            "/v1/convert",
            headers={"Authorization": "Bearer secret"},
            json={
                "model": "shige_utage.pth",
                "audio_base64": base64.b64encode(b"R" * 65).decode("ascii"),
            },
        )

    assert response.status_code == 422
    assert response.json()["category"] == "invalid_audio"
    assert engine.payloads == []


class NativeGate:
    """A bounded thread that survives cancellation of its awaiting coroutine."""

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.finished = asyncio.Event()
        self.settled = asyncio.Event()
        self.release = threading.Event()
        self.calls = 0
        self.active = 0
        self.failure = False

    async def wait(self) -> None:
        loop = asyncio.get_running_loop()

        def native_work() -> None:
            self.calls += 1
            self.active += 1
            loop.call_soon_threadsafe(self.started.set)
            try:
                if not self.release.wait(5):
                    raise RuntimeError("Test worker was not released")
                if self.failure:
                    raise RuntimeError("Native worker failed")
            finally:
                self.active -= 1
                loop.call_soon_threadsafe(self.finished.set)

        try:
            await asyncio.to_thread(native_work)
        finally:
            self.settled.set()

    async def finish(self) -> None:
        self.release.set()
        await asyncio.wait_for(self.finished.wait(), 1)
        await asyncio.wait_for(self.settled.wait(), 1)
        # Allow the executor future and worker completion callbacks to run.
        await asyncio.sleep(0)
        await asyncio.sleep(0)


class GatedEngine(FakeEngine):
    def __init__(self, gate: NativeGate) -> None:
        super().__init__()
        self.gate = gate
        self.lock = asyncio.Lock()

    async def convert(self, audio: bytes, **kwargs: Any) -> bytes:
        async with self.lock:
            await self.gate.wait()
            return await super().convert(audio, **kwargs)

    async def close(self) -> None:
        assert self.gate.active == 0
        await super().close()


class GatedSeparator(FakeSeparator):
    def __init__(self, root: Path, gate: NativeGate) -> None:
        super().__init__(root)
        self.gate = gate

    async def separate(self, audio: bytes) -> Path:
        await self.gate.wait()
        return await super().separate(audio)

    async def close(self) -> None:
        assert self.gate.active == 0
        await super().close()


def gated_service(tmp_path: Path, operation: str, timeout: float = 1.0):
    gate = NativeGate()
    engine = GatedEngine(gate) if operation == "convert" else FakeEngine()
    separator = (
        GatedSeparator(tmp_path, gate) if operation == "separate" else FakeSeparator(tmp_path)
    )
    settings = RVCServiceSettings(
        api_key="secret",
        provider="rvc-webui-host",
        model="shige_utage.pth",
        revision="f8e22f8c",
        voice="shige_utage",
        sample_rate=40000,
        separation_model="htdemucs",
        conversion_timeout_seconds=timeout,
    )
    return RVCService(settings, engine, separator), gate


async def request_operation(service, operation: str, request_id: str) -> Response:
    audio = b"RIFF" + b"s" * 64
    if operation == "convert":
        return await service.convert(
            {
                "model": "shige_utage.pth",
                "audio_base64": base64.b64encode(audio).decode("ascii"),
                "request_id": request_id,
            }
        )
    return await service.separate(audio, model="htdemucs", request_id=request_id)


def assert_busy(response: Response, request_id: str) -> None:
    assert response.status_code == 503
    assert json.loads(response.body) == {"category": "busy", "request_id": request_id}


async def test_host_rvc_timeout_retains_slot_until_native_worker_finishes(tmp_path: Path) -> None:
    service, gate = gated_service(tmp_path, "convert", timeout=0.02)
    await service.preload()
    try:
        timed_out = await request_operation(service, "convert", "timed-out")
        assert timed_out.status_code == 504
        assert json.loads(timed_out.body) == {"category": "timeout", "request_id": "timed-out"}
        assert gate.active == 1
        assert_busy(await request_operation(service, "convert", "second"), "second")
        assert_busy(await request_operation(service, "separate", "separate"), "separate")
        assert gate.calls == 1
        await gate.finish()
        resumed = await request_operation(service, "convert", "resumed")
        assert resumed.status_code == 200
        assert gate.calls == 2
    finally:
        gate.release.set()
        await service.close()


@pytest.mark.parametrize("operation", ["convert", "separate"])
async def test_host_rvc_client_cancel_retains_slot_until_worker_finishes(
    tmp_path: Path, operation: str
) -> None:
    service, gate = gated_service(tmp_path, operation)
    await service.preload()
    request = asyncio.create_task(request_operation(service, operation, "cancelled"))
    try:
        await asyncio.wait_for(gate.started.wait(), 1)
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        assert gate.active == 1
        assert_busy(await request_operation(service, "convert", "convert-busy"), "convert-busy")
        assert_busy(await request_operation(service, "separate", "separate-busy"), "separate-busy")
        assert gate.calls == 1
        await gate.finish()
        resumed = await request_operation(service, "convert", "resumed")
        assert resumed.status_code == 200
    finally:
        gate.release.set()
        await asyncio.gather(request, return_exceptions=True)
        await service.close()


@pytest.mark.parametrize("operation,other", [("convert", "separate"), ("separate", "convert")])
async def test_host_rvc_conversion_and_separation_share_one_slot(
    tmp_path: Path, operation: str, other: str
) -> None:
    service, gate = gated_service(tmp_path, operation)
    await service.preload()
    request = asyncio.create_task(request_operation(service, operation, "first"))
    try:
        await asyncio.wait_for(gate.started.wait(), 1)
        assert_busy(await request_operation(service, other, "other"), "other")
        assert gate.calls == 1
        await gate.finish()
        response = await request
        assert response.status_code == 200
        if response.background is not None:
            await response.background()
        resumed = await request_operation(service, other, "resumed")
        assert resumed.status_code == 200
        if resumed.background is not None:
            await resumed.background()
    finally:
        gate.release.set()
        await asyncio.gather(request, return_exceptions=True)
        await service.close()


@pytest.mark.parametrize("operation", ["convert", "separate"])
async def test_host_rvc_abandoned_worker_failure_is_observed_and_slot_recovers(
    tmp_path: Path, operation: str
) -> None:
    service, gate = gated_service(tmp_path, operation)
    gate.failure = True
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    unobserved = []
    loop.set_exception_handler(lambda _loop, context: unobserved.append(context))
    await service.preload()
    request = asyncio.create_task(request_operation(service, operation, "cancelled"))
    try:
        await asyncio.wait_for(gate.started.wait(), 1)
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        await gate.finish()
        gate.failure = False
        resumed = await request_operation(service, "convert", "resumed")
        assert resumed.status_code == 200
        gc.collect()
        await asyncio.sleep(0)
        assert unobserved == []
    finally:
        gate.release.set()
        await asyncio.gather(request, return_exceptions=True)
        await service.close()
        loop.set_exception_handler(previous_handler)


@pytest.mark.parametrize("operation", ["convert", "separate"])
async def test_host_rvc_shutdown_drains_worker_before_closing_engines(
    tmp_path: Path, operation: str
) -> None:
    service, gate = gated_service(tmp_path, operation)
    await service.preload()
    request = asyncio.create_task(request_operation(service, operation, "cancelled"))
    closing = None
    try:
        await asyncio.wait_for(gate.started.wait(), 1)
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        closing = asyncio.create_task(service.close())
        await asyncio.sleep(0)
        assert not closing.done()
        assert service.engine.closed is False
        assert service.separator.closed is False
        during_close = await request_operation(service, "convert", "closing")
        assert during_close.status_code == 503
        assert json.loads(during_close.body) == {"category": "not_ready", "request_id": "closing"}
        await gate.finish()
        await closing
        assert service.engine.closed is True
        assert service.separator.closed is True
    finally:
        gate.release.set()
        await asyncio.gather(request, return_exceptions=True)
        if closing is not None:
            await asyncio.gather(closing, return_exceptions=True)
        else:
            await service.close()


async def test_host_rvc_cancelled_separation_cleans_late_archive(tmp_path: Path) -> None:
    service, gate = gated_service(tmp_path, "separate")
    await service.preload()
    request = asyncio.create_task(request_operation(service, "separate", "cancelled"))
    try:
        await asyncio.wait_for(gate.started.wait(), 1)
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        await gate.finish()
        await service.close()
        assert service.separator.payloads == [b"RIFF" + b"s" * 64]
        assert not (tmp_path / "session").exists()
    finally:
        gate.release.set()
        await asyncio.gather(request, return_exceptions=True)
        await service.close()


@pytest.mark.parametrize("cancel_request", [False, True])
async def test_host_rvc_demucs_timeout_holds_slot_until_subprocess_exit(
    tmp_path: Path, monkeypatch, cancel_request: bool
) -> None:
    class FakeProcess:
        def __init__(self, *, preflight: bool = False) -> None:
            self.returncode = 0 if preflight else None
            self.waiting_for_exit = asyncio.Event()
            self.exited = asyncio.Event()
            self.killed = False

        async def communicate(self):
            if self.returncode == 0:
                return b"", b""
            await asyncio.Event().wait()

        def kill(self):
            self.killed = True

        async def wait(self):
            self.waiting_for_exit.set()
            await self.exited.wait()
            self.returncode = -9
            return self.returncode

    process = FakeProcess()
    calls = 0

    async def spawn(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return FakeProcess(preflight=True) if calls == 1 else process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    service, _gate = gated_service(tmp_path, "convert")
    service.separator = rvc_separator.DemucsHostSeparator(
        python_executable=Path(sys.executable),
        wrapper_path=_app_path,
        model="htdemucs",
        device="cuda",
        temp_root=tmp_path / "separation",
        timeout_seconds=0.02,
    )
    await service.preload()
    request = asyncio.create_task(request_operation(service, "separate", "demucs-timeout"))
    closing = None
    try:
        await asyncio.wait_for(process.waiting_for_exit.wait(), 1)
        assert process.killed is True
        assert process.returncode is None
        assert not request.done()
        if cancel_request:
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
        assert_busy(await request_operation(service, "convert", "second"), "second")
        assert_busy(await request_operation(service, "separate", "second-stems"), "second-stems")
        assert calls == 2
        closing = asyncio.create_task(service.close())
        await asyncio.sleep(0)
        assert not closing.done()
        assert service.engine.closed is False
        process.exited.set()
        await asyncio.wait_for(closing, 1)
        if not cancel_request:
            response = await request
            assert response.status_code == 504
            assert json.loads(response.body) == {
                "category": "timeout",
                "request_id": "demucs-timeout",
            }
        assert process.returncode == -9
        assert service.engine.closed is True
        assert list(service.separator.temp_root.iterdir()) == []
    finally:
        process.exited.set()
        await asyncio.gather(request, return_exceptions=True)
        if closing is not None:
            await asyncio.gather(closing, return_exceptions=True)
        else:
            await service.close()
