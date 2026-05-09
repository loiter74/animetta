## Context

Anima's Live2D canvas area has no text overlay today — the AI's response text only appears in the right-side ChatPanel. For live streaming, viewers need to see what the AI is saying on-screen without looking away from the model. The existing rendering pipeline (AppLayout.vue with z-index layers) makes it straightforward to add an overlay layer between the Live2D canvas and the InteractivePanel.

The `sentence` Socket.IO event already carries the AI's response text from backend to frontend. The system uses an anime-themed design system (dark purple `#1a1028`, pink accent `#e879a8`, blue `#7c8cf5`) with glassmorphism patterns (`backdrop-blur`, `rounded-2xl`, semi-transparent backgrounds).

## Goals / Non-Goals

**Goals:**
- Display AI response text as a subtitle overlay at the bottom of the Live2D canvas area
- Support bilingual display (original + LLM-translated text) with configurable target language
- Provide settings to toggle subtitle on/off and switch between display modes (original only / translation only / bilingual)
- Animate subtitle entrance/exit with a 二次元 "萌系泡泡" style (pop-in spring animation, glassmorphism panel)
- Persist subtitle preferences via localStorage
- Keep the subtitle overlay functional whether Live2D is embedded or "popped out" (full-width chat)

**Non-Goals:**
- Not adding separate Electron windows or OBS browser source support (can be added later)
- Not translating danmaku (audience bullet comments) — only AI assistant response text
- Not storing subtitle display history or logs
- Not changing existing chat message rendering in ChatPanel
- Not adding real-time streaming word-by-word subtitle (text appears once response is complete)

## Decisions

### Decision 1: Translation approach — Dedicated LLM call in output_node.py
**Choice**: After the LLM generates a response, make a second LLM call specifically for translation in `output_node.py`, before emitting socket events.

**Rationale**:
- Most reliable translation quality — dedicated prompt controls output format precisely
- No impact on the primary LLM response quality or persona consistency
- Translation runs asynchronously: the `sentence` event emits the original text first (`seq: 0`), then the translation arrives in a subsequent event (`seq: 1`) or as a field in the final event
- Can be toggled on/off via service-level config without changing the LLM provider

**Alternative considered**: Modifying the system prompt to output bilingual content natively. Rejected because it interferes with persona tone and produces inconsistent formatting.

**Alternative considered**: Frontend-side translation API call. Rejected because it adds network latency on the client side and requires a separate API key management flow.

### Decision 2: Subtitle overlay position — Inside Live2DRenderer.vue
**Choice**: Add `<SubtitleOverlay>` as a child of the Live2DRenderer container `<div>`, positioned with `absolute bottom-0 left-0 right-0` above the canvas.

**Rationale**:
- Follows the existing pattern of overlay elements already in Live2DRenderer.vue (reset button, HUD, loading states)
- When Live2D is "popped out" (hidden in AppLayout), the subtitle goes with the model — correct behavior since there's no model to subtitle
- Uses the existing `pointer-events-none` pattern for non-interactive overlays

### Decision 3: Subtitle data source — Direct socket event listener in useSubtitle.ts
**Choice**: Create a new composed `useSubtitle.ts` that listens for `sentence` events directly, rather than reading from `useChatStore`.

**Rationale**:
- The `sentence` event payload will carry both `text` and optional `translation` — this is the canonical source
- ChatStore's `currentResponse` accumulates buffered chunks and may not cleanly separate original from translation
- A dedicated composable keeps subtitle concerns isolated from chat message logic
- The composable emits reactivity via Vue refs that SubtitleOverlay.vue consumes

### Decision 4: Subtitle animation — CSS @keyframes with spring easing
**Choice**: Entrance via `transform: translateY(20px) → translateY(0)` with `cubic-bezier(0.34, 1.56, 0.64, 1)` (overshoot spring), exit via fade-out.

**Rationale**:
- Spring easing gives the "萌系泡泡" (cute bubble) feel — slightly bouncy, playful
- CSS-only, no JS animation library dependency needed
- Vue `<Transition>` component handles enter/leave cleanly
- Uses existing animation tokens from `animations.css`

### Decision 5: Subtitle config — Pinia store + localStorage
**Choice**: New `stores/subtitle.ts` Pinia store using `localStorage` for persistence.

**Rationale**:
- Follows existing store pattern (`stores/chat.ts`, `stores/danmaku.ts`)
- `localStorage` matches the existing background image persistence pattern in `App.vue`
- Reactive — SettingsPanel and SubtitleOverlay both read from the same store
- No backend config changes needed for frontend UI preferences

### Decision 6: Translation config — Backend service-level setting
**Choice**: Add a `translation` section to `config/services.yaml` or `config/config.yaml`:
```yaml
translation:
  enabled: true
  target_language: "English"
  source_language: "Chinese"
  provider: "agent"  # reuse the current LLM provider
```

**Rationale**:
- Backend controls which LLM/provider does translation (reuses existing agent config)
- Frontend controls only display preferences (on/off, bilingual mode)
- Clean separation: backend = content, frontend = presentation

### Decision 7: Frontend display modes
**Choice**: Three modes for subtitle display:
1. **original** — Show only the original language text
2. **translated** — Show only the translated text
3. **bilingual** — Show both (original larger on top, translation smaller below)

**Rationale**: Covers all common streaming scenarios. Bilingual is the default for maximum accessibility.

## Risks / Trade-offs

- **[Latency] Translation adds response time**: A second LLM call adds ~1-3s to the response pipeline. Mitigation: Translation runs in parallel with TTS synthesis, and the original text is emitted immediately. The translation arrives in a follow-up event.
- **[Quality] LLM translation may be inconsistent**: Different LLM providers produce varying translation quality. Mitigation: The translation prompt is configurable, and the `target_language` can be changed. Users can switch providers.
- **[UX] Subtitle may overlap with Live2D model**: If the model is positioned low on the canvas. Mitigation: Subtitle panel has configurable position offset, and the glassmorphism background ensures readability against any background.
- **[Config] Frontend/backend config split may confuse users**: Translation target is set in backend config, display toggle in frontend. Mitigation: Add a "翻译目标语言" selector in the frontend SettingsPanel that emits a `translation.configure` socket event to update the backend setting at runtime.
