"""Pipeline 统计 HTTP API"""

from pathlib import Path
from loguru import logger

from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route

from ..graph.stats_store import get_stats_store


async def stats_overview(request: Request) -> JSONResponse:
    """GET /api/stats/overview"""
    try:
        store = await get_stats_store()
        data = await store.get_overview()
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"[StatsAPI] overview 失败: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def stats_nodes(request: Request) -> JSONResponse:
    """GET /api/stats/nodes"""
    try:
        store = await get_stats_store()
        data = await store.get_node_stats()
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"[StatsAPI] nodes 失败: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def stats_traces(request: Request) -> JSONResponse:
    """GET /api/stats/traces?limit=50&offset=0"""
    try:
        limit = int(request.query_params.get("limit", "50"))
        offset = int(request.query_params.get("offset", "0"))
        store = await get_stats_store()
        data = await store.get_recent_traces(limit, offset)
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"[StatsAPI] traces 失败: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def stats_trace_detail(request: Request) -> JSONResponse:
    """GET /api/stats/traces/{trace_id}"""
    try:
        trace_id = request.path_params["trace_id"]
        store = await get_stats_store()
        data = await store.get_trace_detail(trace_id)
        if not data:
            return JSONResponse({"error": "Trace not found"}, status_code=404)
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"[StatsAPI] trace_detail 失败: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def stats_dashboard(request: Request) -> HTMLResponse:
    """GET /stats/ — 仪表盘页面"""
    dashboard_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "frontend" / "stats" / "index.html"
    )
    if dashboard_path.exists():
        return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard not found</h1><p>请先构建前端: frontend/stats/index.html</p>")


def get_stats_routes():
    """返回统计 API 的路由列表"""
    return [
        Route("/api/stats/overview", stats_overview),
        Route("/api/stats/nodes", stats_nodes),
        Route("/api/stats/traces", stats_traces),
        Route("/api/stats/traces/{trace_id}", stats_trace_detail),
        Route("/stats/", stats_dashboard),
    ]
