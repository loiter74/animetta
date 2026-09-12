"""Probe the actual Vite frontend outside the cached HTTP readiness route."""

from __future__ import annotations

import asyncio

import httpx


async def probe_development_frontend(client: httpx.AsyncClient) -> dict[str, str | bool | None]:
    """Require both product pages and their transformed entry modules to load."""
    checks = (
        ("/index.html", "text/html", "/src/main.ts"),
        ("/live.html", "text/html", "/src/live/main.ts"),
        ("/src/main.ts", "javascript", ""),
        ("/src/live/main.ts", "javascript", ""),
    )
    try:
        async with asyncio.timeout(3):
            # The Vite host may not exist until backend liveness succeeds.
            # Reuse one connection instead of filling the resolver pool before
            # provider startup can resolve its own hosts.
            responses = [await client.get(path) for path, _, _ in checks]
        ready = all(
            response.status_code == 200
            and content_type in response.headers.get("content-type", "")
            and bool(response.text.strip())
            and (not entry or (entry in response.text and "/@vite/client" in response.text))
            for response, (_, content_type, entry) in zip(responses, checks, strict=True)
        )
    except (httpx.HTTPError, TimeoutError):
        return {"state": "failed", "ready": False, "reason": "assets_unavailable"}
    return {
        "state": "ready" if ready else "failed",
        "ready": ready,
        "reason": None if ready else "assets_missing",
    }
