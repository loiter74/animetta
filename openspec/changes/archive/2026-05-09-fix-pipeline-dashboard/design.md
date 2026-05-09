## Context

The Dashboard page (`DashboardPage.vue`) uses `useDashboardStore` to fetch data from `/api/stats/*` endpoints. In development mode (Vite on port 3000), these requests are not proxied to the backend (port 12394). Additionally, the frontend store's TypeScript interfaces were written based on an earlier API contract that no longer matches the actual backend response.

Backend data flow is intact:

```
LangGraph pipeline → StatsCallbackHandler → StatsStore (SQLite) → StatsAPI → JSON
```

The database at `data/stats.db` records traces and spans correctly. Only the frontend integration is broken.

## Goals / Non-Goals

**Goals:**
- Make the Dashboard display real LangGraph pipeline data from the backend
- Fix Vite proxy so `/api/stats/*` requests reach the backend in dev mode
- Align frontend types with actual backend API responses
- Ensure all 5 dashboard components render meaningful data (KPI cards, latency breakdown, token usage chart, error rate, session timeline)

**Non-Goals:**
- Not adding new dashboard features or charts
- Not modifying the backend API or stats store schema
- Not adding token tracking (backend doesn't store it yet — out of scope)
- Not redesigning the dashboard layout or styling

## Decisions

### Decision 1: Fix frontend types to match backend (not vice versa)
**Choice**: Update `useDashboardStore` TypeScript interfaces to match the actual API response.
**Rationale**: The backend API is already working and serving data. Changing the frontend types is less risky than modifying the backend schema and data pipeline.

### Decision 2: Overview fields mapping
**Choice**: Map the backend's `total_requests` → frontend's stats display as "Sessions", `avg_duration_ms` → "Avg Latency". Remove KPI cards that depend on token counts (backend doesn't store them yet).
**Rationale**: The 4 KPI cards show Sessions, Avg Latency, Total Tokens, Error Rate. Token data isn't available, so the Total Tokens card will show "N/A" style display or be repurposed to show Total Requests instead.

### Decision 3: ErrorRateCard pulls from real data
**Choice**: Remove hardcoded `[1, 0]` and use `overview.success_rate` from the API.
**Rationale**: The backend already returns `success_rate` in the overview. No reason to hardcode.

### Decision 4: Trace fields alignment
**Choice**: Use `user_text` for the message preview, `created_at` for the timestamp.
**Rationale**: The backend stores user input as `user_text` (not `input_summary`) and the timestamp as `created_at` (not `started_at`).

## Risks / Trade-offs

- **[Missing Data] Token KPI card**: The backend doesn't track input/output token counts. The "Total Tokens" card will show 0. Mitigation: Repurpose this card to show "Total Requests" instead (values from `total_requests`).
- **[Compatibility] Relative imports**: Dashboard components use `'../../stores/...'` relative imports instead of `@/` aliases. Mitigation: Not changing these — they work, just inconsistent.
