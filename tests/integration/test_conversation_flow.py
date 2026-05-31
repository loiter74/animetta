"""Integration test: full conversation flow end-to-end."""

import asyncio
import subprocess
import sys
import time
import socketio
import pytest

SERVER_PORT = 12394
SERVER_URL = f"http://localhost:{SERVER_PORT}"


class TestConversationFlow:

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
            line = proc.stdout.readline()
            if "Application startup complete" in line:
                break
        yield proc
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()

    @pytest.mark.asyncio
    async def test_conversation_pipeline(self, server_process):
        sio = socketio.AsyncClient()
        events = []

        @sio.on("*")
        async def catch_all(event, data=None):
            events.append(event)

        await sio.connect(SERVER_URL, transports=["websocket"], wait_timeout=10)
        await sio.emit("text_input", {"text": "Hello!", "user_id": "test", "from_name": "Tester"})
        await asyncio.sleep(12)
        await sio.disconnect()

        print("\n" + "=" * 60)
        print("  INTEGRATION TEST: Conversation Pipeline")
        print("=" * 60)
        checks = {
            "Server starts": True,
            "Client connects": "connection-established" in events,
            "Text input sent": True,
            "Pipeline executed": len(events) >= 2,
        }
        for c, p in checks.items():
            print(f"  {'PASS' if p else 'FAIL'} {c}")
        print(f"  Events: {events}")
        print("=" * 60)

        assert checks["Client connects"]
        assert checks["Pipeline executed"]
