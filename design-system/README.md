# Animetta Design System

A design system extracted from **[loiter74/Anima-LLM-Vtuber](https://github.com/loiter74/Anima-LLM-Vtuber)** — a Vue 3 + Electron desktop AI companion with a Live2D character, chat UI, and voice I/O.

**Aesthetic:** 日系二次元 — anime-night palette, sakura-pink accent, glassmorphism panels, deliberately small typography.

## Where to start

| File | What's in it |
|---|---|
| **[brand.html](brand.html)** | Pillars, voice & tone, wordmark + app-icon lockups |
| **[colors.html](colors.html)** | Surface scale, accent, semantic, alpha tokens |
| **[typography.html](typography.html)** | CJK-safe OS font stack, nine-step type scale |
| **[spacing.html](spacing.html)** | 4-px base, radii, shadows, easings, layout grid |
| **[iconography.html](iconography.html)** | Section icons + atmosphere backgrounds |
| **[components.html](components.html)** | Glass, buttons, bubbles, input, indicators, sliders |
| **[ui-kit.html](ui-kit.html)** | Full in-app composition |

## Tokens

All tokens live as CSS variables in **[`colors_and_type.css`](colors_and_type.css)**. Every page imports them; nothing is hard-coded.

## Assets

- `assets/favicon.svg` — app icon
- `assets/avatar.png` — character key art
- `assets/icons/*.png` — 11 section icons (64×64, white-on-transparent)
- `assets/backgrounds/*.png` — 7 atmosphere scenes (1792×1008)
- `assets/backgrounds/default.svg` — vector fallback

## Source

Tokens are lifted directly from `frontend/uno.config.ts` in the upstream repo so the system stays in sync with the codebase.

## Applying this to your local Animetta

See **[USAGE.md](USAGE.md)** — it explains how the tokens map to the UnoCSS theme keys you already have, how to add a new section icon, how to add a new background scene, and where to extend the system without forking it.
