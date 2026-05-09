## Why

The Live2D model displays expressive animations but has no on-screen text overlay, making it hard for live viewers to read what the AI is saying. For streaming scenarios, viewers need subtitles at a glance — especially for multilingual audiences. Adding a configurable bilingual subtitle overlay closes this gap and makes streaming more accessible.

## What Changes

- **New `SubtitleOverlay.vue` component** — positioned at the bottom of the Live2D canvas area, showing the AI's response text with a 二次元 (anime) "萌系泡泡" visual style
- **New socket event field** — `sentence` event payload gains an optional `translation` field for bilingual display
- **New backend translation step** — in `output_node.py`, after LLM response, the same LLM translates the text to the target language
- **New subtitle config section** — in `SettingsPanel.vue`, toggle on/off, language mode (original/translation/bilingual), target language, font size
- **New `useSubtitle.ts` composable** — manages subtitle state (current text, translation, visibility, animation)
- **New `subtitleStore` Pinia store** — persistent subtitle configuration (localStorage)
- **README update** — document the subtitle feature with usage instructions

## Capabilities

### New Capabilities
- `subtitle-overlay`: Frontend subtitle overlay component rendering at the bottom of the Live2D canvas, with 二次元 "萌系泡泡" styling, entrance/exit animations, and bilingual text layout
- `subtitle-config`: Configuration panel section for toggling subtitle visibility, selecting display mode (original/translation/bilingual), target language, and font size
- `subtitle-translation`: Backend LLM-based translation step in the output pipeline — after generating a response, the LLM translates it to the target language, and the result is sent alongside the original text in the `sentence` socket event

### Modified Capabilities
- *(empty — no existing spec-level behavior changes)*

## Impact

- **Frontend** (`frontend/src/`):
  - New: `components/live2d/SubtitleOverlay.vue`
  - New: `composables/useSubtitle.ts`
  - New: `stores/subtitle.ts`
  - Modify: `components/live2d/Live2DRenderer.vue` — add SubtitleOverlay inside the container
  - Modify: `components/settings/SettingsPanel.vue` — add subtitle config section
  - Modify: `types/socket-events.ts` — add translation field to sentence event types

- **Backend** (`src/anima/`):
  - Modify: `orchestration/graph/output_node.py` — add LLM translation step before emitting events
  - Modify: `orchestration/server/routes.py` — pass translation through danmaku.ai_reply if applicable

- **Docs**:
  - Update: `README.md` — add subtitle feature description and usage
