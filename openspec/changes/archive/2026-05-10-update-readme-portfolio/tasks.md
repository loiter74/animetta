## 1. Hero Section (L1)

- [x] 1.1 Add demo GIF element referencing `assets/demo/anima-chat-preview.gif` with placeholder comment for user to replace
- [x] 1.2 Write one-line project hook in CN/EN: "AI Virtual Companion with Live2D + Real-time Voice + LangGraph Orchestration"
- [x] 1.3 Add badge row: Test status, Docker, Python 3.12|3.13, License, Tests passing, 30K+ lines

## 2. User Experience Section (L2)

- [x] 2.1 Create 3 visual highlight cards (Living Avatar, Natural Conversation, Swap Models) with emoji headers and CN/EN descriptions
- [x] 2.2 Preserve Quick Start section with pip install → cp .env → python scripts/start.py (no changes)
- [x] 2.3 Create compact capability matrix table listing all LLM, ASR, TTS, VAD providers

## 3. Architecture Section (L3)

- [x] 3.1 Copy mermaid C4 Level 1 diagram from ARCHITECTURE.md to README
- [x] 3.2 Preserve and lightly format existing ASCII data flow diagram
- [x] 3.3 Add LangGraph state machine description with 7 nodes + conditional edges (text + simple ASCII)
- [x] 3.4 Add plugin architecture description: interface.py ABC → implementations → @ProviderRegistry → factory → __init__.py
- [x] 3.5 Add memory architecture description: Hybrid Search (70/30) → Wiki Memory (Markdown truth) → Periodic Learner

## 4. Engineering Section (L4)

- [x] 4.1 Create ADR summary table (ADR-001 through ADR-005 with decision titles and links)
- [x] 4.2 Add engineering metrics summary: 81 tests, CI (Python 3.12/3.13 matrix), mypy strict, ruff, OpenTelemetry, 202 files / 30K lines
- [x] 4.3 Preserve existing test commands (pytest, coverage, mypy, ruff)

## 5. Action Section (L5)

- [x] 5.1 Preserve Docker deployment commands (docker-compose up -d)
- [x] 5.2 Preserve documentation navigation links (ARCHITECTURE.md, TESTING.md, CONTRIBUTING.md, docs/adrs/)
- [x] 5.3 Preserve project structure tree as appendix
- [x] 5.4 Preserve license section

## 6. Cleanup & Verification

- [x] 6.1 Remove standalone "为什么选择 Anima" section (content absorbed into L2 highlight cards)
- [x] 6.2 Remove standalone 30-line subtitle feature section (condensed to one row in L2)
- [x] 6.3 Verify all existing links (ARCHITECTURE.md, TESTING.md, CONTRIBUTING.md, docs/) still resolve
- [x] 6.4 Verify all command blocks are copy-pasteable
- [x] 6.5 Verify bilingual CN/EN text is present for all section headers and key content
- [x] 6.6 Final line count check: 272 lines (bilingual, effective ~136/language; below original 294; mermaid + ASCII diagrams account for ~35 structural lines)
