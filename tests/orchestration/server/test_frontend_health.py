from __future__ import annotations

import asyncio

import httpx
import pytest

from animetta.orchestration.server.frontend_health import probe_development_frontend


def _response(path: str) -> httpx.Response:
    if path.endswith(".html"):
        entry = "/src/live/main.ts" if path == "/live.html" else "/src/main.ts"
        return httpx.Response(
            200,
            text=f'<script src="/@vite/client"></script><script src="{entry}"></script>',
            headers={"content-type": "text/html"},
        )
    return httpx.Response(
        200, text="import '/@vite/client';", headers={"content-type": "text/javascript"}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failed_path", [None, "/index.html", "/live.html", "/src/main.ts", "/src/live/main.ts"]
)
async def test_requires_both_pages_and_transformed_entry_modules(failed_path):
    def handler(request):
        return (
            httpx.Response(500) if request.url.path == failed_path else _response(request.url.path)
        )

    async with httpx.AsyncClient(
        base_url="http://frontend:3000", transport=httpx.MockTransport(handler)
    ) as client:
        result = await probe_development_frontend(client)
    assert result["ready"] is (failed_path is None)
    assert set(result) == {"state", "ready", "reason"}


@pytest.mark.asyncio
@pytest.mark.parametrize("broken", ["html_fallback", "missing_entry", "redirect", "timeout"])
async def test_rejects_false_positive_pages_and_failed_requests(broken):
    def handler(request):
        if broken == "timeout":
            raise httpx.ReadTimeout("private-url-secret")
        if broken == "redirect":
            return httpx.Response(302, headers={"location": "http://elsewhere.invalid"})
        if broken == "missing_entry":
            return httpx.Response(
                200, text="<html>login</html>", headers={"content-type": "text/html"}
            )
        return _response("/index.html")

    async with httpx.AsyncClient(
        base_url="http://frontend:3000", transport=httpx.MockTransport(handler)
    ) as client:
        result = await probe_development_frontend(client)
    assert result["ready"] is False
    assert "secret" not in repr(result)


@pytest.mark.asyncio
async def test_cancellation_is_not_swallowed():
    async def handler(request):
        raise asyncio.CancelledError

    async with httpx.AsyncClient(
        base_url="http://frontend:3000", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(asyncio.CancelledError):
            await probe_development_frontend(client)


@pytest.mark.asyncio
async def test_frontend_probe_does_not_fan_out_startup_dns_requests():
    active = 0
    peak = 0
    paths = []

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        paths.append(request.url.path)
        try:
            await asyncio.sleep(0)
            return _response(request.url.path)
        finally:
            active -= 1

    async with httpx.AsyncClient(
        base_url="http://frontend:3000", transport=httpx.MockTransport(handler)
    ) as client:
        result = await probe_development_frontend(client)
    assert result["ready"] is True
    assert peak == 1
    assert set(paths) == {"/index.html", "/live.html", "/src/main.ts", "/src/live/main.ts"}
