FROM python:3.13-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.13-slim

WORKDIR /app

# Runtime deps only (no gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY src/ src/
COPY config/ config/
COPY scripts/ scripts/
COPY .env.example .env.example

ENV PYTHONPATH=/app/src
ENV ANIMETTA_HOST=0.0.0.0
ENV ANIMETTA_PORT=12394
ENV ANIMETTA_LOG_LEVEL=INFO

EXPOSE 12394

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:12394/health')" || exit 1

CMD ["python", "-m", "animetta.core.socketio_server"]
