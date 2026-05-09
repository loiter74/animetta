## ADDED Requirements

### Requirement: Vite proxy for API requests
The Vite dev server SHALL proxy `/api/stats/*` requests to the backend at `localhost:12394`.

#### Scenario: API request reaches backend
- **WHEN** the frontend fetches `/api/stats/overview` in development mode
- **THEN** the Vite dev server SHALL forward the request to `http://localhost:12394/api/stats/overview`
- **THEN** the frontend SHALL receive the JSON response from the backend

### Requirement: Frontend types align with backend API
The `useDashboardStore` TypeScript interfaces SHALL match the actual backend API response shapes.

#### Scenario: Overview data renders correctly
- **WHEN** the backend returns `{"total_requests": 10, "success_rate": 90.0, "avg_duration_ms": 500, "p95_duration_ms": 1200}`
- **THEN** the KPI cards SHALL display "10" for sessions, "500ms" for avg latency, "90%" for error-free rate
- **THEN** the "Total Tokens" card SHALL be replaced or repurposed to show "Total Requests"

#### Scenario: Trace data renders correctly
- **WHEN** the backend returns a trace with `user_text`, `created_at`, `total_duration_ms`, `status`
- **THEN** the Session Timeline SHALL display `user_text` as the message preview
- **THEN** the Session Timeline SHALL display `created_at` as the timestamp
- **THEN** the Latency Trend chart SHALL render using `created_at` for X-axis labels

### Requirement: Error rate card uses real data
The ErrorRateCard SHALL use real data from the store instead of hardcoded values.

#### Scenario: Error rate reflects actual pipeline errors
- **WHEN** `overview.success_rate` is 95%
- **THEN** the ErrorRateCard SHALL show 5% error rate
- **THEN** the doughnut chart SHALL display success/error proportion from real data
