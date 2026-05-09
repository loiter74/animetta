## 1. Fix gain application in AudioAnalyzer

- [ ] 1.1 Move gain logic out of `if normalize` block in `src/anima/avatar/analyzers/audio.py`
- [ ] 1.2 Verify with LSP diagnostics that the change is clean

## 2. Verify

- [ ] 2.1 Review the diff and confirm normalize=True path unchanged
- [ ] 2.2 Run Python syntax check on changed file
