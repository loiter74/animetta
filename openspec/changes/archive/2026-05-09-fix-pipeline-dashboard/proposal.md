## Why

The Dashboard page is broken in development mode and shows no data. The Vite dev server doesn't proxy `/api/stats/*` requests to the backend, and the frontend store types don't match the actual backend API response fields. Since the dashboard is intended for interview demo / pipeline visualization, fixing it will showcase the LangGraph pipeline chain (ASR → LLM → TTS → Emotion → Output) with live traces and latency breakdown.

## What Changes

- **Fix Vite proxy** — add `/api` proxy rule in `vite.config.ts` to forward requests to the backend
- **Fix frontend field alignment** — update `useDashboardStore` types to match actual backend API response shapes:
  - `StatsOverview`: align fields with backend's `get_overview()` (total_requests, success_rate, avg_duration_ms, p95_duration_ms)
  - `Trace`: align fields with backend's `get_recent_traces()` (user_text → input_summary, created_at → started_at)
- **Fix ErrorRateCard** — remove hardcoded `[1, 0]` data, use real data from the store
- **Retain** all existing dashboard components and layout — only fix data binding

## Capabilities

### New Capabilities
- `dashboard-api-integration`: Fix the API proxy and frontend-backend data contract so the dashboard works with real pipeline data

### Modified Capabilities
<!-- No existing specs to modify — this is a new integration fix -->

## Impact

- **Frontend** — `vite.config.ts` (proxy), `stores/dashboardStore.ts` (types), `components/dashboard/StatsKpiCards.vue` (field refs), `components/dashboard/SessionTimeline.vue` (field refs), `components/dashboard/TokenUsageChart.vue` (field refs), `components/dashboard/ErrorRateCard.vue` (data source)
- **No backend changes** — the API and data pipeline already work correctly
