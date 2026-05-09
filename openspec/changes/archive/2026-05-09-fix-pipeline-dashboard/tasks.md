## 1. Vite proxy fix

- [x] 1.1 Add `/api` proxy rule in `frontend/vite.config.ts` — forward `/api` requests to `http://localhost:12394`

## 2. Frontend store type alignment

- [x] 2.1 Update `StatsOverview` interface in `stores/dashboardStore.ts` — align with backend response: `total_requests`, `success_rate`, `avg_duration_ms`, `p95_duration_ms`
- [x] 2.2 Update `Trace` interface — rename `input_summary` → `user_text`, `started_at` → `created_at`
- [x] 2.3 Update `avgLatency` computed to use `avg_duration_ms` instead of `avg_latency_ms`
- [x] 2.4 Update `totalSessions` computed to use `total_requests` instead of `total_traces`
- [x] 2.5 Update `errorRate` computed to use `success_rate` (derive error_rate = 100 - success_rate)

## 3. Dashboard component fixes

- [x] 3.1 Update `StatsKpiCards.vue` — replace "Total Tokens" card with "Total Requests" (use `total_requests`)
- [x] 3.2 Update `SessionTimeline.vue` — use `trace.user_text` for message preview, `trace.created_at` for timestamp
- [x] 3.3 Update `TokenUsageChart.vue` — use `trace.created_at` for X-axis labels instead of `started_at`
- [x] 3.4 Update `ErrorRateCard.vue` — replace hardcoded `[1, 0]` with real data from `store.overview.success_rate`
