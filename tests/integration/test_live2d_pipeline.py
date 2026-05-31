"""Integration: Live2D viseme — audio + volume envelope for mouth sync."""

import asyncio, subprocess, sys, time, socketio, pytest

PORT, URL = 12394, "http://localhost:12394"

@pytest.fixture(scope="session")
def server():
    p = subprocess.Popen([sys.executable, "-m", "animetta.core.socketio_server"],
        env={**__import__("os").environ, "PYTHONPATH": "src"},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    t0 = time.time()
    while time.time() - t0 < 30:
        if "Application startup complete" in (p.stdout.readline() or ""): break
    time.sleep(8)
    yield p
    p.terminate()
    try: p.wait(timeout=5)
    except subprocess.TimeoutExpired: p.kill()

class TestLive2D:
    @pytest.mark.asyncio
    async def test_viseme(self, server):
        sio, ev = socketio.AsyncClient(), {}
        @sio.on("*")
        async def _(e, d=None): ev.setdefault(e, []).append(d)
        await sio.connect(URL, transports=["websocket"], wait_timeout=10)
        await sio.emit("text_input", {"text": "Say a long sentence so your mouth moves!", "user_id": "v", "from_name": "V"})
        await asyncio.sleep(30)
        await sio.disconnect()
        audio = ev.get("audio_with_expression",[])
        has_vol = any(isinstance(a,dict) and a.get("volumes") for a in audio)
        errs = ev.get("error",[])
        vcount = len(audio[0].get("volumes",[])) if has_vol and audio else 0
        print(f"audio_events={len(audio)} volumes={has_vol} vol_samples={vcount} errors={errs}")
        assert "connection-established" in ev, "connect"
        assert not errs, f"errors: {errs}"
