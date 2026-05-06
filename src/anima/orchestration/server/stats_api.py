"""Pipeline stats HTTP API"""

import json
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ..graph.stats_store import get_stats_store

# Dashboard frontend file directory
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
        logger.error(f"[StatsAPI] overview failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def stats_nodes(request: Request) -> JSONResponse:
    """GET /api/stats/nodes"""
    try:
        store = await get_stats_store()
        data = await store.get_node_stats()
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"[StatsAPI] nodes failed: {e}")
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
        logger.error(f"[StatsAPI] traces failed: {e}")
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
        logger.error(f"[StatsAPI] trace_detail failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def stats_trace_tree(request: Request) -> JSONResponse:
    """GET /api/stats/traces/{trace_id}/tree — returns spans as a nested tree."""
    try:
        trace_id = request.path_params["trace_id"]
        store = await get_stats_store()
        detail = await store.get_trace_detail(trace_id)
        if not detail:
            return JSONResponse({"error": "Trace not found"}, status_code=404)

        spans: List[Dict[str, Any]] = detail.get("spans", [])
        tree = _build_span_tree(spans)
        return JSONResponse({
            "trace_id": trace_id,
            "total_duration_ms": detail.get("total_duration_ms"),
            "status": detail.get("status"),
            "created_at": detail.get("created_at"),
            "spans": spans,
            "tree": tree,
        })
    except Exception as e:
        logger.error(f"[StatsAPI] trace_tree failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


def _build_span_tree(spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group flat span list into a parent-child nested tree.

    Returns a list of root spans (parent_span_id is None), each with a ``children`` list.
    """
    by_id: Dict[str, Dict] = {}
    roots: List[Dict] = []

    for s in spans:
        node = dict(s)
        node["children"] = []
        by_id[s["span_id"]] = node

    for node in by_id.values():
        pid = node.get("parent_span_id")
        if pid and pid in by_id:
            by_id[pid]["children"].append(node)
        else:
            roots.append(node)

    return roots


async def health_check(request):
    """Unified health check endpoint"""
    import time
    return JSONResponse({
        "status": "ok",
        "service": "anima",
        "timestamp": time.time(),
    })


def get_stats_routes():
    """Return the route list for the stats API"""
    return [
        Route("/health", health_check),
        Route("/api/stats/overview", stats_overview),
        Route("/api/stats/nodes", stats_nodes),
        Route("/api/stats/traces", stats_traces),
        Route("/api/stats/traces/{trace_id}", stats_trace_detail),
        Route("/api/stats/traces/{trace_id}/tree", stats_trace_tree),
        Mount("/stats", app=StaticFiles(directory=STATS_FRONTEND_DIR, html=True), name="stats_dashboard"),
    ]
