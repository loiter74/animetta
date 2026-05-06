#!/usr/bin/env python3
"""
Web configuration HTTP server for Anima.

Serves static files from the frontend/web/ directory.
When accessing /, serves index.html (or templates/config.html if index doesn't exist).

Usage:
    python -m scripts.start.web_config_server <web_dir> [port]
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler


class ConfigHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the config page with CORS support."""

    def __init__(self, *args, web_dir="", **kwargs):
        self._web_dir = web_dir  # Must be set BEFORE super().__init__()
        super().__init__(*args, directory=web_dir, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self):
        # Serve index.html at root
        if self.path in ("/", ""):
            index = os.path.join(self._web_dir, "index.html")
            fallback = os.path.join(self._web_dir, "templates", "config.html")
            if os.path.exists(index):
                self.path = "/index.html"
            elif os.path.exists(fallback):
                self.path = "/templates/config.html"
        super().do_GET()

    def log_message(self, *args):
        pass


def serve(web_dir: str, port: int = 8080):
    """Start the web config HTTP server."""
    server = HTTPServer(
        ("0.0.0.0", port),
        lambda *a: ConfigHandler(*a, web_dir=web_dir),
    )
    print(f"[Config] Web configuration interface started: http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    args = sys.argv[1:]
    web_dir = args[0] if len(args) > 0 else "."
    port = int(args[1]) if len(args) > 1 else 8080
    serve(web_dir, port)
