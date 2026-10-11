# syntax=docker/dockerfile:1
# Shared dependency stages for the web runtime and Compose Watch development.
# Qwen and RVC remain Windows host services; no GPU packages enter this image.

FROM node:22-bookworm-slim AS frontend-deps
ARG VITE_EARTH_ENABLED=false
RUN corepack enable \
    && corepack prepare pnpm@11.7.0 --activate \
    && pnpm config set registry https://registry.npmmirror.com \
    && pnpm config set store-dir /pnpm/store
WORKDIR /build/frontend
ENV ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm_config_electron_skip_binary_download=true
COPY frontend/.npmrc frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
COPY frontend/optional/earth/package.json ./optional/earth/package.json
COPY frontend/optional/desktop/package.json ./optional/desktop/package.json
COPY frontend/optional/review/package.json ./optional/review/package.json
RUN --mount=type=cache,id=animetta-pnpm-11,target=/pnpm/store \
    if [ "$VITE_EARTH_ENABLED" = "true" ]; then \
      pnpm --filter animetta-desktop --filter @animetta/earth install --frozen-lockfile --prefer-offline; \
    else \
      pnpm --filter animetta-desktop install --frozen-lockfile --prefer-offline; \
    fi

FROM frontend-deps AS frontend-source
ARG VITE_EARTH_ENABLED=false
ENV VITE_EARTH_ENABLED=${VITE_EARTH_ENABLED}
COPY frontend/*.html frontend/vite.config.ts frontend/uno.config.ts frontend/tsconfig.json ./
COPY frontend/src/ ./src/
COPY frontend/public/ ./public/
COPY frontend/scripts/earth-assets.ts ./scripts/earth-assets.ts
COPY config/socket-events.json /build/config/socket-events.json

FROM frontend-source AS frontend-dev
ARG ANIMETTA_BUILD_FINGERPRINT=untracked
LABEL org.animetta.build-fingerprint="${ANIMETTA_BUILD_FINGERPRINT}"
EXPOSE 3000
CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0"]

FROM frontend-source AS frontend-builder
# The affected quality gate runs the full typecheck and build contract.
RUN pnpm exec vite build

FROM ghcr.io/astral-sh/uv:0.11.19 AS uv
FROM python:3.13-slim-bookworm AS python-builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /build
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ UV_LINK_MODE=copy
COPY requirements.txt requirements-bilibili.txt requirements-search.txt requirements-memory-semantic.txt ./
ARG ANIMETTA_PYTHON_EXTRAS=""
RUN --mount=type=cache,id=animetta-uv-013,target=/root/.cache/uv \
    set -- requirements.txt; \
    for extra in $ANIMETTA_PYTHON_EXTRAS; do \
      case "$extra" in bilibili|search|memory-semantic) ;; *) echo "Invalid Python extra" >&2; exit 1 ;; esac; \
      set -- "$@" "requirements-$extra.txt"; \
    done; \
    uv venv --python /usr/local/bin/python /opt/venv \
    && uv pip sync --python /opt/venv/bin/python --compile-bytecode "$@" \
    && uv pip check --python /opt/venv/bin/python
# Ship the native, hash-verified encoding with the copied venv so fresh
# containers do not download it during service initialization or first use.
ENV TIKTOKEN_CACHE_DIR=/opt/venv/tokenizer-cache
RUN timeout 60s /opt/venv/bin/python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

FROM python:3.13-slim-bookworm AS backend-base
ARG ANIMETTA_MEDIA_ENABLED=false
WORKDIR /app
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get install -y --no-install-recommends nginx curl \
    && if [ "$ANIMETTA_MEDIA_ENABLED" = "true" ]; then apt-get install -y --no-install-recommends ffmpeg; fi
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/app/src PYTHONUNBUFFERED=1 \
    TIKTOKEN_CACHE_DIR=/opt/venv/tokenizer-cache
ENV ANIMETTA_HOST=0.0.0.0 ANIMETTA_PORT=12394 ANIMETTA_PROFILE=test
COPY src/animetta/ src/animetta/
COPY config/ config/
COPY .env.example .env.example
RUN python -m compileall -q --invalidation-mode checked-hash src/animetta

FROM backend-base AS backend-dev
ARG ANIMETTA_BUILD_FINGERPRINT=untracked
LABEL org.animetta.build-fingerprint="${ANIMETTA_BUILD_FINGERPRINT}"
EXPOSE 12394
CMD ["python", "-m", "animetta.core.socketio_server"]

FROM backend-base AS runtime
COPY scripts/validate-events.py scripts/validate-events.py
RUN --mount=type=bind,from=frontend-source,source=/build/frontend,target=/app/frontend \
    python scripts/validate-events.py
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
EXPOSE 80 12394
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1
# Volatile build identity belongs after every expensive layer.
ARG ANIMETTA_BUILD_FINGERPRINT=untracked
LABEL org.animetta.build-fingerprint="${ANIMETTA_BUILD_FINGERPRINT}"
ENTRYPOINT ["/app/entrypoint.sh"]
