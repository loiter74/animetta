## 1. Storage Layer

- [ ] 1.1 Create `src/anima/orchestration/graph/stats_store.py` with StatsStore class: SQLite init, traces/spans tables with indexes, create/finish methods for traces and spans, aggregation queries (overview, node_stats, recent_traces, trace_detail), global singleton `get_stats_store()`
- [ ] 1.2 Add `data/stats.db` and `data/stats.db-*` to `.gitignore`
- [ ] 1.3 Check and add `aiosqlite>=0.20.0` to `requirements.txt` if missing, run `pip install aiosqlite`
- [ ] 1.4 Verify StatsStore import: `python -c "from anima.orchestration.graph.stats_store import StatsStore; print('OK')"`

## 2. Callback Handler

- [ ] 2.1 Create `src/anima/orchestration/graph/stats_handler.py` with StatsCallbackHandler extending `BaseCallbackHandler`: track active spans in `_active_spans` dict, `start_trace()`/`finish_trace()` lifecycle, `on_chain_start`/`on_chain_end`/`on_chain_error` callbacks filtering known nodes, async writes via `asyncio.ensure_future()`, input/output summary helpers
- [ ] 2.2 Verify StatsCallbackHandler import: `python -c "from anima.orchestration.graph.stats_handler import StatsCallbackHandler; print('OK')"`

## 3. Orchestrator Integration

- [ ] 3.1 Modify `src/anima/orchestration/graph/orchestrator.py`: import StatsCallbackHandler, instantiate in `__init__` and append to `self._callbacks`, wrap `graph.ainvoke()` in `_run_graph()` with `start_trace()`/`finish_trace()` calls, catch exceptions and record error status
- [ ] 3.2 Verify orchestrator import: `python -c "from anima.orchestration.graph.orchestrator import LangGraphOrchestrator; print('OK')"`

## 4. HTTP API

- [ ] 4.1 Create `src/anima/orchestration/server/stats_api.py` with Starlette route handlers: `stats_overview`, `stats_nodes`, `stats_traces`, `stats_trace_detail`, `stats_dashboard`, and `get_stats_routes()` returning route list
- [ ] 4.2 Modify `src/anima/orchestration/server/websocket.py`: import Starlette and stats_api, replace `self.asgi_app = socketio.ASGIApp(self.sio)` with Starlette app wrapping stats routes + Socket.IO mount
- [ ] 4.3 Verify ASGI app creation: `python -c "from anima.orchestration.server.websocket import WebSocketServer; s = WebSocketServer(); print(type(s.asgi_app).__name__)"` → should print `Starlette`

## 5. Dashboard Frontend

- [ ] 5.1 Create `frontend/stats/index.html`: dark theme page with KPI cards section, node chart canvas, traces table, trace detail modal; load Chart.js from CDN and local stats.js/stats.css
- [ ] 5.2 Create `frontend/stats/stats.css`: dark color palette (#0f172a background, #1e293b cards, #e2e8f0 text), KPI card grid, chart section, traces table with hover, modal overlay, span list items
- [ ] 5.3 Create `frontend/stats/stats.js`: fetchOverview/fetchNodeStats/fetchTraces functions calling API, Chart.js horizontal bar chart initialization, trace row click handler opening modal with trace detail, escapeHtml utility, 5s auto-refresh interval

## 6. End-to-End Verification

- [ ] 6.1 Start backend: `python -m anima.core.socketio_server` — verify no import errors, logs show "统计 handler 已注入"
- [ ] 6.2 Send a text message via frontend chat, then verify API returns data: `curl http://localhost:12394/api/stats/overview`, `curl http://localhost:12394/api/stats/nodes`, `curl http://localhost:12394/api/stats/traces`
- [ ] 6.3 Open `http://localhost:12394/stats/` in browser — verify KPI cards, chart, traces table render with real data
- [ ] 6.4 Click a trace row — verify modal opens with trace detail and span list
