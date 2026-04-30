## 1. Favicon

- [ ] 1.1 Create SVG favicon with dark/light mode support in `frontend/public/favicon.svg`
- [ ] 1.2 Add `<link rel="icon">` to `frontend/index.html`

## 2. Backend: get_config socket event

- [ ] 2.1 Add `on_get_config` handler in `routes.py` that reads config and returns safe (no API keys) config_data
- [ ] 2.2 Register `get_config` event in `register_routes()`

## 3. Settings Panel: Display real config

- [ ] 3.1 Update `SettingsPanel.vue` — emit `get_config` on mount, listen for `config_data`, display service names/types
- [ ] 3.2 Display persona name and Live2D model path from config_data

## 4. Background Image Support

- [ ] 4.1 Create `frontend/public/backgrounds/` with 3-5 preset dark-themed background images
- [ ] 4.2 Create `BackgroundSettings.vue` component (preset grid + URL input + file upload)
- [ ] 4.3 Integrate background into `App.vue` via CSS variable + localStorage persistence
- [ ] 4.4 Add background settings UI to InteractivePanel/settings area

## 5. Memory Organize Status Display

- [ ] 5.1 Enhance memory organize progress display in ChatPanel.vue with stage text and completion message

## 6. Live2D View Reset Button

- [ ] 6.1 Add "重置视图" button in settings panel, wired to `live2d.resetView()`

## 7. Verification

- [x] 7.1 Run `pnpm typecheck` — zero errors
- [ ] 7.2 Verify favicon loads in browser
- [ ] 7.3 Verify settings panel shows real config
- [ ] 7.4 Verify background image (preset/URL/upload) works
