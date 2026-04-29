## ADDED Requirements

### Requirement: KPI cards display
The dashboard SHALL display three KPI cards at the top: Total Requests, Success Rate (%), and P95 Latency (ms), each updating every 5 seconds.

#### Scenario: KPI values populated
- **WHEN** dashboard loads and API returns `{"total_requests": 100, "success_rate": 98.0, "p95_duration_ms": 1520}`
- **THEN** cards display "100", "98.0%", "1520ms" respectively

#### Scenario: No data shows dashes
- **WHEN** API returns `{"total_requests": 0, "success_rate": 0, "p95_duration_ms": 0}`
- **THEN** cards display "0", "0%", "-" (P95 not applicable)

### Requirement: Node performance chart
The dashboard SHALL display a horizontal bar chart showing average duration (ms) and error count per node, using Chart.js.

#### Scenario: Chart renders with node data
- **WHEN** API returns node stats for "llm" (850ms avg, 2 errors) and "tts" (320ms avg, 0 errors)
- **THEN** chart shows two horizontal bars with "llm" bar longer than "tts" bar, and error count in second dataset

### Requirement: Recent traces table
The dashboard SHALL display a table of recent traces showing: Time, Type (text/audio), Input (user_text), Duration (ms), Status (success/error with color coding).

#### Scenario: Trace row renders
- **WHEN** API returns a trace with `created_at="2026-04-29T10:23:45"`, `input_type="text"`, `user_text="你好"`, `total_duration_ms=1195`, `status="success"`
- **THEN** table row shows formatted time, "text", "你好", "1195ms", green "success"

### Requirement: Trace detail modal
The dashboard SHALL open a modal when a trace row is clicked, showing trace metadata and an ordered list of spans with node_name, duration, and input/output summary.

#### Scenario: Click trace row opens detail
- **WHEN** user clicks a trace row
- **THEN** modal appears with trace metadata grid (ID, total duration, status, time) and span list ordered by execution time

#### Scenario: Close modal
- **WHEN** user clicks the X button or outside the modal
- **THEN** modal closes

### Requirement: Auto-refresh
The dashboard SHALL auto-refresh all data (KPI, chart, traces table) every 5 seconds via polling.

#### Scenario: Data updates periodically
- **WHEN** dashboard is open for 10 seconds
- **THEN** data has been fetched at least 2 times automatically

### Requirement: Dark theme styling
The dashboard SHALL use a dark color scheme (background #0f172a, cards #1e293b, text #e2e8f0) for visual consistency with VTuber aesthetic.

#### Scenario: Page renders with dark theme
- **WHEN** dashboard loads
- **THEN** background is dark, text is light, matching the specified color palette
