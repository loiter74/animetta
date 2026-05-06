## 1. Fix Missing `await` on `load_cache` (CRITICAL — Fixes 3 errors)

- [x] 1.1 Add `await` before `ctx.load_cache(config=config, **pool)` in `src/anima/orchestration/server/session.py:69`

## 2. Fix Orchestrator None Guards (LOW — Defense-in-depth)

- [x] 2.1 Add `and self.service_context.config is not None` guard in `_get_persona_dict()` at `src/anima/orchestration/graph/orchestrator.py:267`
- [x] 2.2 Add `and self.service_context.config is not None` guard in `_get_system_prompt()` at `src/anima/orchestration/graph/orchestrator.py:282`

## 3. Fix `KeywordAnalyzer.__init__` Missing `valid_emotions` (HIGH)

- [x] 3.1 Add `valid_emotions: Optional[List[str]] = None` parameter to `KeywordAnalyzer.__init__` in `src/anima/avatar/analyzers/keyword.py:105`

## 4. Fix `FasterWhisperASR` Not Imported in `__init__.py` (MEDIUM)

- [x] 4.1 Add `from .faster_whisper_asr import FasterWhisperASR` to `src/anima/services/speech/asr/__init__.py`

## 5. Fix `FasterWhisperASR.from_config()` Dict Access (LOW — Blocked by Task 4)

- [x] 5.1-5.8 All `config.get()` calls replaced with `getattr()` in `faster_whisper_asr.py`

## 6. Final Verification

- [x] 6.1 Python syntax check on all 5 changed files — all pass
- [x] 6.2 Run `python -m pytest tests/ -v` — **159/159 passed**
- [x] 6.3 Code changes ready for server restart
