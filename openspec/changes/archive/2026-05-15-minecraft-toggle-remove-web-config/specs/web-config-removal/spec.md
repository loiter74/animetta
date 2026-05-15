## REMOVED Requirements

### Requirement: Web Config HTTP server on port 8080
**Reason**: The standalone Web Config page (`scripts/start/web_config_server.py`) is superseded by the Vue 3 frontend Settings panel (port 3000). It adds an unnecessary subprocess and port.

**Migration**: Use the Vue 3 frontend at `http://localhost:3000` for all configuration. The Settings panel already contains all configurable options (persona, translation, Bilibili, background).
