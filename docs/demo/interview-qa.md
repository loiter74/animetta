# Interview Q&A Preparation

Anticipated interview questions with structured answers referencing specific code and design decisions.

---

## Architecture & Design

### Q: Why LangGraph instead of a simple event loop or pipeline?

**A:** We originally used EventBus, but faced three problems: (1) no visibility into pipeline state, (2) no branching support for tool calling, and (3) no native streaming. LangGraph gives us an explicit state machine where each node is a pure function `state → state_update`. This makes the pipeline testable in isolation — each node has its own test suite with mocked state. The branching for tool calls is a first-class graph pattern, not a workaround. See [ADR-001](../docs/adrs/ADR-001-langgraph-over-eventbus.md).

### Q: How does the plugin architecture work?

**A:** Services register themselves via decorators: `@ProviderRegistry.register_service("llm", "openai")`. The config uses Pydantic discriminated unions, so deserializing `config.yaml` automatically picks the right class based on a `type: openai` field. Adding a new provider requires exactly two files — a config class and a service class — and two decorators. No framework code changes. See [ADR-003](../docs/adrs/ADR-003-plugin-architecture.md).

### Q: How would you handle 1000 concurrent users?

**A:** The current architecture is single-process. For scale, I'd: (1) make the LangGraph orchestrator stateless by moving session state to Redis, (2) horizontally scale the FastAPI server behind a load balancer, (3) use a proper task queue (Celery + Redis) for the LLM/TTS pipeline since those are I/O-bound, and (4) replace Chroma with a production vector database like Qdrant or Pinecone. The plugin architecture and config system would remain unchanged — they're already decoupled from the execution model.

---

## AI Engineering

### Q: How do you ensure LLM response quality?

**A:** We take three approaches: (1) structural — clear system prompt with persona, behavior rules, and examples; (2) retrieval — RAG with hybrid search provides relevant context to ground responses; and (3) testing — our test suite validates that LLM nodes handle edge cases (empty input, tool calls, errors) correctly via mocked responses. For production, I'd add an evaluation harness with semantic similarity scoring and human feedback collection.

### Q: How does the memory system work?

**A:** It's a wiki-architecture inspired by Karpathy's approach. Conversation data is stored as Markdown files — human-readable and editable. From those files, we build two derived indexes: Chroma for vector similarity search and SQLite FTS5 for BM25 keyword search. Retrieval is a weighted fusion: 70% vector + 30% keyword. We also extract structured facts (MemoryEntry objects) with version chains, so changing preferences are tracked over time. See [ADR-005](../docs/adrs/ADR-005-wiki-memory.md).

### Q: How do you handle LLM failures or timeouts?

**A:** Each service has a mock fallback. If the real provider fails (network error, rate limit, invalid response), the service factory catches the exception and logs a warning, then returns a mock implementation that provides sensible default responses. The LangGraph node is wrapped in a try-catch and returns an error state rather than crashing. Additionally, per-session interrupt handling via `asyncio.Event` allows clean cancellation mid-stream.

---

## Testing & Quality

### Q: How do you test components that depend on external AI services?

**A:** All external services are behind interfaces (`LLMInterface`, `TTSInterface`, etc.). Our `conftest.py` provides mock fixtures for every service — `mock_llm`, `mock_tts`, `mock_asr`, `mock_vad`. These are AsyncMock objects that return predictable responses. Each LangGraph node has a test suite that injects these mocks via the `_config` mechanism. This lets us test the complete orchestration logic without any real API calls or network dependencies.

### Q: What's your testing pyramid look like?

**A:** 81 tests total. The pyramid is: (1) **unit tests** for individual graph nodes with mocked services (~30 tests), (2) **integration tests** for the orchestrator flow and memory system (~40 tests), and (3) **API tests** for the stats endpoints (~11 tests). We use pytest with asyncio_mode=auto, and every PR runs the full suite via GitHub Actions plus ruff linting and mypy type checking.

---

## Operations

### Q: How would you debug a production issue with slow responses?

**A:** The StatsCallbackHandler records per-node latency for every conversation trace. I'd open the dashboard, check the latency breakdown to identify which node is slow (e.g., LLM generation taking 5s vs the usual 1s), then drill into specific traces. If it's an LLM issue, I'd check token counts and provider status. If it's a memory issue, I'd check retrieval latency. The architecture is designed for this kind of observability — every graph node execution is timed and recorded.

### Q: How do you deploy the application?

**A:** Docker multi-stage build → docker-compose for local → Fly.io for production deployment. The Dockerfile is ~150MB with python:3.13-slim. The Fly.io config supports auto-scaling to zero on the free tier and auto-starts on the first request. Deployment is `flyctl deploy`. All secrets are passed via environment variables or `.env` file.

---

## Open-Ended

### Q: What would you improve if you had more time?

**A:** Three things: (1) **LLM evaluation harness** — automated semantic similarity tests to catch regressions when changing prompts or models; (2) **Streaming TTS** — begin audio playback before the full response is generated, reducing perceived latency; (3) **Multi-session conversation management** — proper conversation history UI with search, export, and the ability to resume past conversations.

### Q: What was the hardest technical challenge?

**A:** The migration from EventBus to LangGraph. The EventBus architecture had organically grown to handle streaming via side channels and tool calling via event nesting. Migrating to a state graph required rethinking how data flows through the system — but it was worth it. The graph is now the single source of truth for the pipeline, every state transition is explicit, and new features (like the interrupt handler) naturally fit into the node model.
