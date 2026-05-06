## Context

The server startup and session creation flow has multiple independent bugs that were introduced during the LangGraph migration and service pool refactoring. The bugs range from a missing `await` keyword (critical — blocks all conversation processing) to missing imports (silent degradation). All are simple one-liner fixes except the `from_config` refactoring.

Three of the six bugs are directly linked: the missing `await` on `load_cache()` causes `self.config` and `self.llm_engine` to remain `None`, which triggers crashes in both the orchestrator's `_get_persona_dict()` and the tool manager's `_create_chat_model()`. Fixing the `await` resolves all three.

## Goals / Non-Goals

**Goals:**
- Fix all 6 identified bugs with minimal, surgical changes
- Ensure conversation processing works end-to-end
- Ensure emotion analyzer initializes on startup
- Ensure faster_whisper ASR provider is discoverable

**Non-Goals:**
- No architectural refactoring
- No test additions (existing tests should still pass)
- No config changes or new defaults
- No changes to the service pool pattern itself

## Decisions

### 1. Fix `await` on `load_cache` (CRITICAL)
- **What**: Change `ctx.load_cache(...)` to `await ctx.load_cache(...)` in `session.py:69`
- **Rationale**: The `load_cache` method is an `async def` that sets `self.config` and copies pooled engine instances. Without `await`, none of this runs. This is a textbook async bug.
- **Alternative considered**: Making `load_cache` synchronous. Rejected because it calls `init_emotion_analyzer` at the end which is also async. Adding `await` is the correct fix.

### 2. Fix `KeywordAnalyzer.__init__` missing `valid_emotions` (HIGH)
- **What**: Add `valid_emotions: Optional[List[str]] = None` parameter to `KeywordAnalyzer.__init__`
- **Rationale**: The factory does `analyzer_class(**config)` and the config always contains `valid_emotions`. The `StandaloneLLMTagAnalyzer` already accepts this param. Making `KeywordAnalyzer` consistent is the simplest fix. If provided, the param can be used to filter which emotions the analyzer tracks.
- **Alternative considered**: Filter kwargs in factory by inspecting constructor signature. Rejected — adds complexity, fragility, and breaks the explicit contract between factory and implementation.

### 3. Fix ASR `__init__.py` missing import (MEDIUM)
- **What**: Add `from .faster_whisper_asr import FasterWhisperASR` to `src/anima/services/speech/asr/__init__.py`
- **Rationale**: The `@ProviderRegistry.register_service` decorator on `FasterWhisperASR` must execute at import time. Since the module is never imported, the service never registers. All other ASR providers are imported in `__init__.py`.
- **Alternative considered**: Import lazily in the factory. Rejected — the existing pattern for all other providers is eager import via `__init__.py`.

### 4. Fix orchestrator None guards (LOW)
- **What**: Add `and self.service_context.config` checks in `_get_persona_dict()` and `_get_system_prompt()`
- **Rationale**: Defense-in-depth. Even after fixing the `await`, having runtime None guards prevents future regressions and isolates failures.
- **Alternative considered**: Leaving as-is (rely on fix #1). Rejected — the orchestrator should be resilient to partial initialization.

### 5. Fix `FasterWhisperASR.from_config()` dict access (LOW)
- **What**: Replace `config.get("model")` with `config.model` (attribute access)
- **Rationale**: `config` is a Pydantic model, not a dict. `.get()` doesn't exist on Pydantic models. This currently doesn't crash because fix #3 isn't done yet (service never registered, so `from_config` never called), but it will crash immediately after fix #3.
- **Alternative considered**: Converting config to dict first with `config.model_dump()`. Rejected — attribute access is simpler and type-safe.

## Risks / Trade-offs

- **[Risk] Fix #3 (import) exposes fix #6 (dict access)**: Adding the `FasterWhisperASR` import will immediately cause `from_config` to crash on first ASR call. **Mitigation**: Apply fixes #3 and #6 together; don't deploy one without the other.
- **[Risk] KeywordAnalyzer still doesn't USE `valid_emotions`**: The fix adds the parameter but doesn't change behavior. The analyzer will accept and ignore `valid_emotions`. This is intentional — fixing behavior (filtering keyword groups) is a separate enhancement, not a bug fix.
- **[Risk] Missing `await` fix changes timing**: Adding `await` means service context initialization becomes sequential again during session creation. This is fine — it was always intended to be async-initialized; the missing `await` was the bug.
