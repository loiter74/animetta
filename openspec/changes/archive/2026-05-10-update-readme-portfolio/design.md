## Context

The current README is a flat, text-heavy document (~294 lines) that lists features as tables without narrative progression. For a portfolio project targeting interviewers and GitHub passersby, it fails to:
- Hook readers in the first 5 seconds (no visible demo)
- Show engineering depth (ADR, plugin architecture, LangGraph state machine are invisible)
- Guide readers from "what" → "how" → "why trust it"

The project has strong technical foundations (5 ADRs, LangGraph orchestration, decorator-based plugin system, hybrid search memory, OpenTelemetry tracing, 81 tests) that the current README doesn't surface.

## Goals / Non-Goals

**Goals:**
- Restructure README into 5 progressive layers: Hero → UX → Architecture → Engineering → Action
- Surface engineering signals: ADR table, LangGraph state machine, plugin architecture diagram, hybrid search
- Add mermaid C4 architecture diagram (reuse from ARCHITECTURE.md)
- Condense bloated sections (subtitle feature 30 lines → 1 row, flat feature tables → capability matrix)
- Add demo GIF placeholder (user provides video)
- Maintain bilingual CN/EN throughout
- Maintain all existing quick start, deploy, and test commands

**Non-Goals:**
- Not rewriting ARCHITECTURE.md, TESTING.md, or CONTRIBUTING.md
- Not adding new features or changing project capabilities
- Not removing any existing content that's still relevant (just reorganizing/condensing)
- Not creating new diagrams — reuse existing mermaid from ARCHITECTURE.md

## Decisions

### Decision 1: 5-Layer Progressive Structure

5 layers ordered from shallowest (anyone can understand) to deepest (engineering interview):
1. **Hero** — demo GIF + one-line hook + badges (3 seconds to impress)
2. **User Experience** — 3 visual highlights + quick start + capability matrix (what can it do?)
3. **Architecture** — C4 diagram + LangGraph state machine + plugin system + memory (how is it built?)
4. **Engineering** — ADR table + test/CI/observability + code scale (why trust it?)
5. **Action** — Docker deploy + docs navigation + project structure appendix (want to try?)

Rationale: Matches how interviewers scan — first impression → capability check → deep dive → credibility signals.

### Decision 2: Bilingual Format

Keep existing bilingual pattern but tighten: use `**CN:** ... **EN:** ...` on one line where possible, separate lines for longer content. Rationale: shows internationalization capability without doubling line count.

### Decision 3: Demo GIF Placement

Center-top, full-width in Hero section. Currently references `assets/demo/anima-chat-preview.gif` — keep same path, user provides file. Rationale: visual first impression is non-negotiable for portfolio README.

### Decision 4: Architecture Diagrams — Reuse vs New

Reuse existing mermaid C4 diagrams from ARCHITECTURE.md rather than creating new ones. Rationale: single source of truth, avoids divergence.

### Decision 5: Provider Support — Table → Compact List

Replace the current 3 separate feature tables (Smart Dialogue, Lively Character, Flexible Config) with:
- 3 visual highlight cards at top (Living Avatar, Natural Conversation, Swap Models)
- A compact capability matrix: `| LLM | DeepSeek, GLM, OpenAI, Ollama, Local |`
- Subtitle feature condensed to one row in the Character table

Rationale: current layout buries provider diversity in a grid of feature names.

## Risks / Trade-offs

- [Risk] Removing standalone subtitle section may upset users who rely on that documentation → Mitigation: subtitle feature is well-documented in the UI settings panel itself; condensed table row is sufficient
- [Risk] Bilingual text increases line count → Mitigation: use compact formatting (one-liners where possible), target ~200 lines vs current 294
- [Risk] Demo GIF placeholder may look broken if user hasn't recorded yet → Mitigation: add HTML comment `<!-- Replace with your demo GIF: record 15s of chat + Live2D interaction -->`
