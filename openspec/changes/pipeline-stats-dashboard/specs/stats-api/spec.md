## ADDED Requirements

### Requirement: Starlette route mounting
The system SHALL mount Starlette HTTP routes alongside the existing Socket.IO ASGI app. Socket.IO connections (`/socket.io/`) SHALL be handled by `socketio.ASGIApp`; all other paths SHALL be routed by Starlette.

#### Scenario: Socket.IO still works after mounting
- **WHEN** a client connects to `ws://host:port/socket.io/`
- **THEN** Socket.IO handles the connection as before

#### Scenario: Stats API routes accessible
- **WHEN** a client sends GET to `/api/stats/overview`
- **THEN** Starlette routes the request to the stats handler

### Requirement: GET /api/stats/overview
The system SHALL return a JSON object with `total_requests`, `success_rate`, `avg_duration_ms`, `p95_duration_ms`.

#### Scenario: Normal response
- **WHEN** GET /api/stats/overview is called
- **THEN** returns HTTP 200 with `{"total_requests": N, "success_rate": X, "avg_duration_ms": Y, "p95_duration_ms": Z}`

#### Scenario: Database error
- **WHEN** SQLite query fails
- **THEN** returns HTTP 500 with `{"error": "<message>"}`

### Requirement: GET /api/stats/nodes
The system SHALL return a JSON array of per-node statistics.

#### Scenario: Node stats response
- **WHEN** GET /api/stats/nodes is called
- **THEN** returns HTTP 200 with array of `{"node_name", "call_count", "avg_duration_ms", "min_duration_ms", "max_duration_ms", "error_count", "error_rate"}`

### Requirement: GET /api/stats/traces
The system SHALL return recent traces with pagination via `limit` (default 50) and `offset` (default 0) query parameters.

#### Scenario: Paginated traces
- **WHEN** GET /api/stats/traces?limit=10&offset=0 is called
- **THEN** returns HTTP 200 with array of 10 most recent trace objects

### Requirement: GET /api/stats/traces/{trace_id}
The system SHALL return a single trace's full detail including all spans.

#### Scenario: Existing trace
- **WHEN** GET /api/stats/traces/{valid_id} is called
- **THEN** returns HTTP 200 with trace metadata and spans array

#### Scenario: Non-existent trace
- **WHEN** GET /api/stats/traces/{invalid_id} is called
- **THEN** returns HTTP 404 with `{"error": "Trace not found"}`

### Requirement: GET /stats/ serves dashboard
The system SHALL serve the Dashboard HTML page at `/stats/`.

#### Scenario: Dashboard page accessible
- **WHEN** browser navigates to `http://host:port/stats/`
- **THEN** returns the dashboard HTML page (Content-Type: text/html)
