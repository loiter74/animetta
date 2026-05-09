## 1. Frontend — Subtitle Store & Composable

- [x] 1.1 Create `stores/subtitle.ts` — Pinia store with `enabled`, `displayMode` ('original'|'translated'|'bilingual'), `fontSize` ('small'|'medium'|'large'), `targetLanguage`, persisted via localStorage
- [x] 1.2 Create `composables/useSubtitle.ts` — listen for `sentence` socket events, extract `text` and `translation` fields, manage subtitle visibility state (show/hide timing based on conversation signals)
- [x] 1.3 Update `types/socket-events.ts` — extend sentence event type with optional `translation?: string`, `lang?: string`, `target_lang?: string` fields

## 2. Frontend — SubtitleOverlay Component

- [x] 2.1 Create `components/live2d/SubtitleOverlay.vue` — positioned `absolute bottom-0` in Live2DRenderer container, glassmorphism background, rounded corners, max-width 80vw centered
- [x] 2.2 Implement entrance animation — CSS `@keyframes` with spring easing (`cubic-bezier(0.34, 1.56, 0.64, 1)`), translateY + opacity
- [x] 2.3 Implement bilingual layout — original text larger (1.2rem), translation smaller (0.95rem), vertical stack with accent decoration
- [x] 2.4 Implement display mode switching — read from subtitleStore, conditionally render original/translation/bilingual content
- [x] 2.5 Add `<SubtitleOverlay>` to `Live2DRenderer.vue` — import and insert inside the container div, respect `pointer-events-none`
- [x] 2.6 Add exit animation — fade-out on conversation-end with Vue `<Transition>`

## 3. Frontend — Settings Panel Integration

- [x] 3.1 Add "字幕" section to `components/settings/SettingsPanel.vue` — enable/disable toggle switch
- [x] 3.2 Add display mode selector — radio buttons or segmented control for "原文" / "翻译" / "双语"
- [x] 3.3 Add font size selector — small/medium/large options
- [x] 3.4 Add target language dropdown — common language list (English, 日本語, 한국어, etc.), emit `translation.configure` socket event on change

## 4. Backend — LLM Translation Pipeline

- [x] 4.1 Add runtime translation config — created `translation_state.py` (shared module-level state) with `enabled`, `target_language`, `source_language`; managed at runtime via socket events instead of static YAML
- [x] 4.2 Create translation function in output pipeline — inline LLM translation call in `output_node.py` using `service_context.llm_engine.chat()` with a dedicated translate prompt
- [x] 4.3 Modify `output_node.py` — after `response_text`, if `translation_state.enabled`, call LLM translation and include `translation` field in `sentence` socket event payload
- [x] 4.4 Add `translation.configure` socket event handler in `routes.py` — updates `translation_state.target_language` at runtime
- [x] 4.5 Add translation config state — `translation_state.TranslationState` class with properties for runtime config

## 5. Backend — Socket Event Extension

- [x] 5.1 Update `sentence` event emission in `output_node.py` — includes `lang`, `translation`, and `target_lang` fields when translation is available
- [x] 5.2 Update `routes.py` danmaku AI reply path — same translation logic applied to danmaku AI replies before broadcasting

## 6. Polish

- [x] 6.1 Update `README.md` — document subtitle feature with feature table and usage instructions in both CN/EN
