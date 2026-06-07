#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DIST_DIR="$FRONTEND_DIR/dist"

echo "=== Building Animetta Frontend ==="

# Check Node.js availability
if ! command -v node &>/dev/null; then
    echo "ERROR: Node.js is not installed or not in PATH"
    exit 1
fi

echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# Install dependencies if node_modules is missing or package.json is newer
if [ ! -d "$FRONTEND_DIR/node_modules" ] || \
   [ "$FRONTEND_DIR/package.json" -nt "$FRONTEND_DIR/node_modules/.package-lock.json" ] 2>/dev/null; then
    echo "--- Installing frontend dependencies ---"
    cd "$FRONTEND_DIR"
    npm ci --prefer-offline 2>/dev/null || npm install
    cd "$PROJECT_ROOT"
fi

# Clean previous build
if [ -d "$DIST_DIR" ]; then
    echo "--- Cleaning previous build output ---"
    rm -rf "$DIST_DIR"
fi

# Build frontend (skip type-check in Docker to speed up build; CI should run typecheck separately)
echo "--- Running vite build ---"
cd "$FRONTEND_DIR"
npx vite build
cd "$PROJECT_ROOT"

# Verify build output
if [ ! -f "$DIST_DIR/index.html" ]; then
    echo "ERROR: Build failed — $DIST_DIR/index.html not found"
    exit 1
fi

echo "=== Frontend build complete ==="
echo "Output: $DIST_DIR"
echo "Files: $(find "$DIST_DIR" -type f | wc -l)"
