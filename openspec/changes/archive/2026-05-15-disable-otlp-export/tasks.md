## 1. Configuration Change

- [x] 1.1 Set `otlp.enabled: false` in `config/observability.yaml` and add inline comment explaining opt-in behavior

## 2. Verification

- [x] 2.1 Verify `config/observability.yaml` is valid YAML after change
- [x] 2.2 Verify `bootstrap.py` correctly handles `otlp.enabled: false` (code already handles this — confirmation step)
