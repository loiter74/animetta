## 1. Panel Container — MemeReview.vue

- [ ] 1.1 Replace `bg-c-bg border-l border-c-border` with `glass-strong m-3 rounded-2xl`, remove the left border, adjust layout to account for margin
- [ ] 1.2 Replace custom `panel-enter-active`/`panel-leave-to` CSS with standard `animate-slide-in-right` / `animate-slide-out-right` using Vue `<Transition>` with enter/leave classes
- [ ] 1.3 Add gradient divider line below header: `bg-gradient-to-r from-transparent via-c-accent/20 to-transparent h-px`
- [ ] 1.4 Replace progress bar background with `gradient-accent` gradient fill

## 2. Card Component — MemeCard.vue

- [ ] 2.1 Upgrade card background from `bg-c-surface border border-c-border` to `bg-c-card/50 rounded-xl border border-c-border hover:bg-c-card/60 transition-all`
- [ ] 2.2 Conditionally apply `border-c-success/30` with `shadow-[0_0_8px_rgba(74,222,128,0.3)]` on good vote, and `border-c-error/30` with `shadow-[0_0_8px_rgba(248,113,113,0.3)]` on bad vote
- [ ] 2.3 Replace persona_fit_score percentage text with a small SVG ring progress indicator

## 3. Vote Buttons — MemeReview.vue

- [ ] 3.1 Style 好梗 button: `bg-c-success/15 text-c-success border border-c-success/20 hover:bg-c-success/25 hover:shadow-[0_0_8px_rgba(74,222,128,0.3)] active:scale-95 transition-all`
- [ ] 3.2 Style 烂梗 button: `bg-c-error/15 text-c-error border border-c-error/20 hover:bg-c-error/25 hover:shadow-[0_0_8px_rgba(248,113,113,0.3)] active:scale-95 transition-all`
- [ ] 3.3 Style skip/prev navigation buttons using `btn-ghost` pattern: `bg-c-card/50 text-c-text-dim hover:bg-c-card border border-transparent`

## 4. Micro-interactions & Polish

- [ ] 4.1 Add card switch transition: wrap card area in Vue `<Transition>` with `animate-slide-out-right` on leave and `animate-slide-in-right` on enter, keyed by `store.currentIndex`
- [ ] 4.2 Add good/bad count number pop animation on update (brief scale-up tween when goodCount/badCount changes)
- [ ] 4.3 Style 采集热梗 button with `gradient-accent` gradient and hover glow effect: `shadow-[0_0_12px_rgba(232,121,168,0.3)]` on hover

## 5. Verification

- [ ] 5.1 Run `pnpm dev` in frontend and verify the panel opens/closes with smooth animations
- [ ] 5.2 Verify all states render correctly: loading, empty, card, done
- [ ] 5.3 Verify vote buttons trigger correct socket events and card transitions work
- [ ] 5.4 Verify all styles use existing UnoCSS tokens (no new CSS variables or colors introduced)
