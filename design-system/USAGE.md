# Using this design system in Animetta

The design system is a **1-to-1 mirror** of `frontend/uno.config.ts` in the
[loiter74/Anima-LLM-Vtuber](https://github.com/loiter74/Anima-LLM-Vtuber) repo.
Every token in `colors_and_type.css` corresponds to a key in the UnoCSS
`theme.colors` table — so you don't need to "apply" anything new. You just need
to recognize what's already wired and follow the patterns when you build new UI.

---

## 1 · The tokens are already in your codebase

| Token in this DS | What it is in Animetta | Example UnoCSS class |
|---|---|---|
| `--c-bg` | `c-bg` | `bg-c-bg` |
| `--c-surface` | `c-surface` | `bg-c-surface` |
| `--c-accent` | `c-accent` | `bg-c-accent` · `text-c-accent` |
| `--c-text` | `c-text` | `text-c-text` |
| `--c-ai-bubble` | `c-ai-bubble` | `bg-c-ai-bubble` |
| `--r-2xl` | (Tailwind built-in) | `rounded-2xl` |
| `--shadow-glow-accent` | (custom) | drop on inline style |

If you ever add a new color to `colors_and_type.css`, add the same key to
`uno.config.ts → theme.colors` and you can use it as a Tailwind class everywhere
in the Vue codebase.

---

## 2 · Building a new component? Match a card in `components.html`.

The shortcut table from `uno.config.ts` already covers the system:

```ts
// uno.config.ts → shortcuts
'glass':       'bg-c-surface/70 backdrop-blur-xl border border-c-border rounded-2xl',
'glass-strong':'bg-c-surface/85 backdrop-blur-2xl border border-c-border rounded-2xl',
'btn-accent':  'bg-c-accent hover:bg-c-accent-hover text-white rounded-xl px-4 py-2 transition-all duration-200 active:scale-95',
'btn-ghost':   'bg-transparent hover:bg-c-accent-soft text-c-text-dim hover:text-c-accent rounded-xl px-3 py-2 transition-all duration-200',
```

So a primary button is just:

```vue
<button class="btn-accent">Send</button>
```

…and a glass panel is just:

```vue
<GlassPanel class="p-5">
  <h3 class="text-c-text font-semibold">Persona</h3>
  …
</GlassPanel>
```

When you're not sure how something should look, open the matching card in
`components.html` — it lists the exact tokens, padding, radius and motion.

---

## 3 · Adding a new section icon

1. Draw your icon as a 64 × 64 PNG, white-on-transparent.
2. Save it at `frontend/public/icons/<key>/<key>.png` (the existing folder pattern).
3. Reference it where you'd reference the others, e.g. in a Settings tab:

```vue
<img src="/icons/yourkey/yourkey.png" class="w-5 h-5 opacity-65" />
<span class="text-xs">Your section</span>
```

The icon will pick up its color from the surrounding container's drop-shadow
and ring — no need to bake a color into the PNG.

---

## 4 · Adding a new background scene

1. Render the scene at 1920 × 1080 (or close — the frontend covers anyway).
2. Save it as a `.png` or `.jpg` under `frontend/public/backgrounds/`.
3. Register the filename in `src/components/settings/BackgroundSettings.vue` —
   it's a single array near the top.
4. It will appear in **Settings → Background** automatically and persist to
    `localStorage` under `animetta_background`.

Composition rules live in `iconography.html § Composition rules`:
center-clear, dim enough for glass, one light source, no text on canvas.

---

## 5 · Treating new copy

Anima speaks in two voices — see `brand.html § Voice & tone`. The fastest way
to keep them apart in code:

| Surface | Voice | Examples in code |
|---|---|---|
| `<MessageBubble>` content | **Character** — first-person, warm | `「嗯！我也想出去走走～」` |
| Status pills, badges, toasts | **System** — terse, technical | `"Connected · 14 ms"` |
| Persona descriptions in `<PersonalityPanel>` | **Character** | written in-world |
| Error states in `<SettingsPanel>` | **System** | `"Cannot reach provider."` |

---

## 6 · Where to look when you want to extend the system

- **A new color?** Add to both `colors_and_type.css` and `uno.config.ts → theme.colors`. Document the role in `colors.html § Where each color goes`.
- **A new component?** Build it, then add a card to `components.html` so the next person can find it.
- **A new motion?** It should compose `--d-base` × `--ease-out-expo` first. If you really need a new easing, add it to the motion section of `spacing.html`.

---

## TL;DR

The design system isn't a separate thing to integrate — it's a readable form of
what already lives in `uno.config.ts`. Treat each page in `brand.html`, `colors.html`,
`typography.html`, `spacing.html`, `iconography.html`, `components.html` as a
**spec sheet** for the matching directory in `frontend/src/`. The
`ui-kit.html` file is a reference assembly to compare against when you change
the app shell.
