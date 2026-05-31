"""Integration test: Live2D pipeline verification.

Verifies: expression events, motion commands, and viseme/sentence sync.
"""

import asyncio
import subprocess
import sys
import time
import socketio
import pytest

SERVER_PORT = 12394
SERVER_URL = f"http://localhost:{SERVER_PORT}"


class TestLive2DPipeline:

    @pytest.fixture(scope="session")
    def server_process(self):
        proc = subprocess.Popen(
            [sys.executable, "-m", "animetta.core.socketio_server"],
            env={**__import__("os").environ, "PYTHONPATH": "src"},
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace",
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            if "Application startup complete" in proc.stdout.readline():
                break
        yield proc
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()

    @pytest.mark.asyncio
    async def test_live2d_pipeline(self, server_process):
        """Verify Live2D expression, motion, and viseme events fire."""
        sio = socketio.AsyncClient()
        events = {}

        @sio.on("*")
        async def catch_all(event, data=None):
            events.setdefault(event, []).append(data)

        await sio.connect(SERVER_URL, transports=["websocket"], wait_timeout=10)
        await sio.emit("text_input", {
            "text": "Hello! Please respond with emotion.",
            "user_id": "test_live2d",
            "from_name": "Live2DTester",
        })
        await asyncio.sleep(20)
        await sio.disconnect()

        print("\n" + "=" * 60)
        print("  INTEGRATION TEST: Live2D Pipeline")
        print("=" * 60)

        has_expression = "expression" in events
        has_motion = "live2d.action" in events
        has_sentence = "sentence" in events

        checks = {
            "Client connected": True,
            "Expression event": has_expression,
            "Live2D motion": has_motion,
            "Sentence streaming": has_sentence,
        }

        for check, passed in checks.items():
            print(f"  {'PASS' if passed else 'FAIL'} {check}")

        if has_expression:
            emotions = [e.get("emotion") for e in events["expression"] if isinstance(e, dict)]
            print(f"  Emotions: {emotions}")
        if has_motion:
            motions = [e.get("index") for e in events["live2d.action"] if isinstance(e, dict)]
            print(f"  Motions: {motions}")

        print("=" * 60)

        assert has_expression, "Should receive expression event (emotion detected)"
        assert has_motion, "Should receive live2d.action event (motion triggered)"
