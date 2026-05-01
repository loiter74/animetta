"""Pipeline 统计 HTTP API"""

from pathlib import Path
from loguru import logger

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ..graph.stats_store import get_stats_store

# Dashboard 前端文件目录
STATS_FRONTEND_DIR = str(
    Path(__file__).parent.parent.parent.parent.parent / "frontend" / "stats"
)


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


async def health_check(request):
    """统一健康检查端点"""
    import time
    return JSONResponse({
        "status": "ok",
        "service": "anima",
        "timestamp": time.time(),
    })


def get_stats_routes():
    """返回统计 API 的路由列表"""
    return [
        Route("/health", health_check),
        Route("/api/stats/overview", stats_overview),
        Route("/api/stats/nodes", stats_nodes),
        Route("/api/stats/traces", stats_traces),
        Route("/api/stats/traces/{trace_id}", stats_trace_detail),
        Mount("/stats", app=StaticFiles(directory=STATS_FRONTEND_DIR, html=True), name="stats_dashboard"),
    ]
