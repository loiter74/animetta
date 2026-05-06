## ADDED Requirements

### Requirement: One-command startup
`python scripts/start.py` SHALL start all three services: backend (port 12394), Vite frontend (port 3000), and web config (port 8080).

#### Scenario: Default startup starts all services
- **WHEN** user runs `python scripts/start.py` without arguments
- **THEN** backend starts on port 12394
- **AND** Vite frontend starts on port 3000
- **AND** web config starts on port 8080
- **AND** browser opens health check, then web config, then frontend

### Requirement: Remove --mode parameter
The `--mode` flag SHALL be removed. `--mode desktop` and `--mode web` SHALL produce the same behavior (start all services).

#### Scenario: --mode still accepted but ignored
- **WHEN** user runs `python scripts/start.py --mode web`
- **THEN** all services start (same as default)
- **AND** deprecation warning is printed

#### Scenario: --mode desktop behaves same as default
- **WHEN** user runs `python scripts/start.py --mode desktop`
- **THEN** all services start (same as no --mode)

### Requirement: --no-frontend parameter
A `--no-frontend` flag SHALL replace `--no-app`. It SHALL skip starting the Vite frontend.

#### Scenario: --no-frontend skips frontend
- **WHEN** user runs `python scripts/start.py --no-frontend`
- **THEN** backend and web config start
- **AND** Vite frontend does NOT start

### Requirement: --no-app backward compatibility
`--no-app` SHALL be accepted as an alias for `--no-frontend` with a deprecation warning.

#### Scenario: --no-app maps to --no-frontend
- **WHEN** user runs `python scripts/start.py --no-app`
- **THEN** deprecation warning is printed
- **AND** behavior is identical to `--no-frontend`

### Requirement: Auto-open browser
Browser SHALL auto-open three URLs in order: `http://localhost:12394/health` (2s delay), `http://localhost:8080` (3s delay), `http://localhost:3000` (4s delay).

#### Scenario: All URLs opened in sequence
- **WHEN** startup completes
- **THEN** browser opens health check after 2s
- **AND** browser opens web config after 3s
- **AND** browser opens frontend after 4s

#### Scenario: --no-frontend skips frontend URL
- **WHEN** user runs `python scripts/start.py --no-frontend`
- **THEN** browser opens health check and web config
- **AND** browser does NOT open frontend URL
