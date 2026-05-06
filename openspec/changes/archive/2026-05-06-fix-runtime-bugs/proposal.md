## Why

The server has multiple runtime bugs that block basic functionality: text input processing crashes with `'NoneType' object has no attribute 'get_persona'`, emotion analyzer initialization always fails, and the faster_whisper ASR provider is silently ignored. These bugs all occur on every startup, making the system unusable for anyone using the default config.

## What Changes

- Fix missing `await` on `ctx.load_cache()` — the root cause of the runtime crash cascade
- Add `valid_emotions` parameter to `KeywordAnalyzer.__init__` — fix emotion analyzer initialization
- Import `FasterWhisperASR` in ASR `__init__.py` — fix ASR provider registration
- Add None guards on `self.service_context.config` in orchestrator — defense-in-depth
- Fix `FasterWhisperASR.from_config()` to use Pydantic attribute access instead of dict `.get()`

## Capabilities

### New Capabilities
- `runtime-error-recovery`: Graceful handling of service context initialization failures — system logs warning instead of crashing
- `emotion-analyzer-init`: Robust emotion analyzer factory that handles constructor parameter mismatches between analyzer implementations

### Modified Capabilities
<!-- No existing specs require changes — these are all bug fixes, not new features -->

## Impact

- `src/anima/orchestration/server/session.py`: 1-line fix (add `await`)
- `src/anima/orchestration/graph/orchestrator.py`: 2-line fix (add None guards)
- `src/anima/avatar/analyzers/keyword.py`: 1-line addition (add `valid_emotions` parameter)
- `src/anima/services/speech/asr/__init__.py`: 1-line addition (add import)
- `src/anima/services/speech/asr/faster_whisper_asr.py`: Rewrite `from_config` (attribute access)
- No API changes, no new dependencies, no breaking changes
