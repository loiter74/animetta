## 1. Modify start.py: Remove --mode, add --no-frontend

- [x] 1.1 Remove `--mode` argument from argparse; add deprecation handling if passed
- [x] 1.2 Rename `--no-app` to `--no-frontend`, keep `--no-app` as deprecated alias
- [x] 1.3 Remove `desktop`/`web` mode branching — always start backend + frontend + web config

## 2. Update services.py startup order

- [x] 2.1 Make `start_vite` always called (not just in web mode)
- [x] 2.2 Verify startup order: backend → web config → frontend (Vite slowest last)

## 3. Update browser.py auto-open URLs

- [x] 3.1 Always open health check (2s), web config (3s), frontend (4s)
- [x] 3.2 Respect `--no-frontend`: skip frontend URL if flag set
- [x] 3.3 Respect `--no-web-config`: skip config URL if flag set

## 4. Verify web config page

- [x] 4.1 Confirm `frontend/web/templates/config.html` exists and is accessible
- [x] 4.2 Verify 8080 port serves the config page correctly

## 5. Final verification

- [x] 5.1 Run `python scripts/start.py --help` — verify new arguments
- [x] 5.2 Run all tests — 94 passed
- [x] 5.3 Verify `--no-app` still works with deprecation warning
