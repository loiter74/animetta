# Interview Demo Walkthrough

**Total time:** 15-20 minutes
**Goal:** Showcase engineering depth across AI orchestration, observability, and system design.

---

## Step 1: Basic Chat (2 min)

**Action:** Open Anima desktop app, type "你好！今天天气怎么样？"

**What to show:**
- Text input → streaming response appears token by token
- Live2D avatar reacts with appropriate emotion expression
- Response is coherent and contextually relevant

**Engineering story:**
> "The conversation is orchestrated by a LangGraph state machine. Each step — LLM generation, emotion analysis, TTS synthesis — is a separate graph node with explicit state transitions. Streaming is built into the graph via LangGraph's `astream()` API."

---

## Step 2: Live Dashboard (3 min)

**Action:** Click the "Dashboard" button in the title bar

**What to show:**
- KPI cards: total sessions, average latency, token usage, error rate
- Pipeline latency breakdown bar chart (per-node)
- Latency trend line chart over recent conversations
- Error rate doughnut chart
- Recent session timeline with drill-down

**Engineering story:**
> "Every conversation trace is recorded by the StatsCallbackHandler, which hooks into LangGraph's lifecycle events. The data is stored in a local SQLite database and exposed via REST endpoints. The dashboard is a Vue 3 page with Chart.js visualizations — it auto-refreshes every 10 seconds."

---

## Step 3: Memory Recall (2 min)

**Action:** Say "还记得我们上次聊了什么吗？"

**Prerequisite:** Have a previous conversation saved.

**What to show:**
- The AI retrieves and references past conversation content
- Shows awareness of user's previous statements

**Engineering story:**
> "Memory uses a hybrid search approach — 70% vector similarity via Chroma DB and 30% BM25 keyword matching via SQLite FTS5. The weighted fusion gives us both semantic understanding and keyword precision. All conversation data is stored as human-readable Markdown files, with the vector and keyword indexes being derived views."

---

## Step 4: Tool Calling (2 min)

**Action:** Say "搜索一下最近的AI新闻" or "今天北京天气怎么样？"

**What to show:**
- LLM detects a tool call intent
- Graph branches: LLM → tool_node → LLM
- Response incorporates real-time external data

**Engineering story:**
> "Tool calling is a first-class branch in the LangGraph. When the LLM emits `tool_calls` in its response, the graph routes to the tool execution node. Results are fed back into the LLM for a final response. Tools can be built-in (web_search, calculator), LangChain-integrated (Python REPL), or external MCP servers running in Docker containers."

---

## Step 5: Architecture Tour (3 min)

**Action:** Open `ARCHITECTURE.md` and `docs/adrs/`

**What to show:**
- System Context diagram (C4 Level 1) — overview of all components
- Sequence diagram — full request lifecycle
- ADR-001: Why LangGraph over EventBus
- ADR-003: How the plugin-based provider architecture works

**Suggested talking points:**
- "The original architecture used EventBus. We migrated to LangGraph for explicit state management and native streaming support."
- "Providers are pluggable — adding a new LLM requires just two files and two decorators."
- "This design decision is documented in ADR-001 with alternatives considered."

---

## Step 6: Test & CI Quality (2 min)

**Action:** Open the GitHub repository page and `TESTING.md`

**What to show:**
- CI badge showing 81 passing tests
- GitHub Actions workflow running pytest, ruff, mypy
- TESTING.md with test philosophy and conventions

**Engineering story:**
> "Every external service (LLM, TTS, ASR, VAD) has a mock fixture in conftest.py. This lets us test the entire LangGraph pipeline without any real API calls. Each graph node has its own test suite with error path coverage. The CI pipeline runs linting, type checking, and tests on every PR."

---

## Step 7: Deployment & Containerization (2 min)

**Action:** Show `Dockerfile`, `docker-compose.yml`, `fly.toml`

**What to show:**
- Multi-stage Dockerfile (builder → runtime)
- docker-compose with health checks
- Fly.io deployment config with auto-scaling

**Engineering story:**
> "The Docker image is only ~150MB using multi-stage builds with python:3.13-slim. The Fly.io config supports auto-scaling to zero on the free tier. Deployment is a single `flyctl deploy` command."

---

## Step 8: Code Walkthrough (remaining time)

**Optional, if there's extra time:**

- Open `llm_node.py` — show the node function pattern (state in, state out)
- Open `registry.py` — show the decorator-based plugin registration
- Open `orchestrator.py` — show the graph builder
- Open a test file — show the mock-based testing pattern

---

## Pro Tips

1. **Prepare the demo environment**: Have a few conversations saved so memory recall works.
2. **Pre-warm**: Run the app before the interview starts.
3. **Keep Dashboard open**: Let traces accumulate during the demo to show live data.
4. **Mention ADRs naturally**: "We chose X because of Y, which is documented in ADR-N."
5. **Know your numbers**: "P50 latency with DeepSeek is about 1.2 seconds."
6. **Be ready to deep-dive**: If the interviewer asks about a specific component, open the corresponding file and walk through it.
