# Deployment Guide

## Prerequisites

- [flyctl](https://fly.io/docs/flyctl/install/) CLI installed
- Fly.io account (free tier: 3 VMs, 3GB storage)
- API keys for the services you want to use

## One-Click Deploy

```bash
# 1. Login
flyctl auth login

# 2. Set secrets (API keys)
flyctl secrets set GLM_API_KEY=your_key_here
flyctl secrets set OPENAI_API_KEY=your_key_here
flyctl secrets set OPENAI_BASE_URL=https://api.deepseek.com/v1

# 3. Launch
flyctl launch --ha=false

# 4. Verify
curl https://anima-demo.fly.dev/health
```

Expected response:
```json
{"status": "ok", "service": "anima", "timestamp": 1714512345.678}
```

## Free Tier Config

The `fly.toml` is configured for Fly's free tier:
- **Scale to zero**: VMs stop when idle, start on first request
- **512MB RAM**: Sufficient for mock/API-only mode
- **Hong Kong region**: Low latency for Asia

## Mock Mode (No API Keys)

For a demo without API keys, switch all services to mock:

```yaml
# config/config.yaml
services:
  agent: mock
  asr: mock
  tts: mock
  vad: mock
```

The app will respond with canned responses. Socket.IO and Live2D still work.

## Production Mode

```bash
# More resources
flyctl scale vm shared-cpu-2x --group web
flyctl scale memory 1024

# Custom domain
flyctl certs add your-domain.com
```

## Health Check

Endpoint: `GET /health`

```json
{
  "status": "ok",
  "service": "anima",
  "timestamp": 1714512345.678
}
```

The Dockerfile includes a Docker HEALTHCHECK that pings this endpoint every 30s.
