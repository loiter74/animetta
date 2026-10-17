import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const liveStyles = readFileSync(resolve(process.cwd(), 'src/live/styles.css'), 'utf8')

describe('standalone live panel styles', () => {
  it('keeps desktop chat compact at the outer edge of the stage', () => {
    expect(liveStyles).toMatch(/\.danmaku-panel\s*\{[^}]*width:\s*min\(380px,\s*28vw\)/s)
    expect(liveStyles).toMatch(/\.danmaku-panel\s*\{[^}]*right:\s*var\(--live-gutter\)/s)
  })

  it('caps the danmaku list above the Live2D model', () => {
    expect(liveStyles).toMatch(/\.danmaku-list\s*\{[^}]*max-height:\s*min\(360px,\s*32dvh\)/s)
  })

  it('composites the Live2D model in front of the danmaku panel', () => {
    expect(liveStyles).toMatch(/\.live2d-stage\s*\{[^}]*z-index:\s*1/s)
    expect(liveStyles).toMatch(/\.danmaku-panel\s*\{[^}]*z-index:\s*0/s)
  })

  it('hides the danmaku scrollbar while preserving scrolling', () => {
    expect(liveStyles).toMatch(
      /\.danmaku-list\s*\{[^}]*overflow:\s*auto[^}]*scrollbar-width:\s*none/s,
    )
    expect(liveStyles).toMatch(/\.danmaku-list::-(?:webkit-)?scrollbar\s*\{[^}]*display:\s*none/s)
  })

  it('uses existing theme tokens for gift and super-chat labels', () => {
    expect(liveStyles).toMatch(/\.danmaku-kind--gift\s*\{[^}]*@apply[^;]*text-c-success/s)
    expect(liveStyles).toMatch(/\.danmaku-kind--super-chat\s*\{[^}]*@apply[^;]*text-c-accent/s)
  })

  it('keeps the public subtitle above the model using theme tokens', () => {
    expect(liveStyles).toMatch(/\.subtitle-overlay\s*\{[^}]*z-index:\s*20/s)
    expect(liveStyles).toMatch(/\.subtitle-overlay\s*\{[^}]*@apply[^;]*bg-c-panel\/95/s)
    expect(liveStyles).toMatch(
      /\.subtitle-overlay p\s*\{[^}]*font-size:\s*clamp\(24px,\s*2\.2vw,\s*36px\)/s,
    )
    expect(liveStyles).toMatch(/\.subtitle-overlay p\s*\{[^}]*font-weight:\s*500/s)
  })

  it('stacks portrait chat, subtitles and controls below the clear stage area', () => {
    expect(liveStyles).toMatch(/\.live-shell\s*\{[^}]*height:\s*100dvh/s)
    const portraitStyles = liveStyles.split('@media (max-width: 760px), (max-aspect-ratio: 4/3)')[1]
    expect(portraitStyles).toMatch(
      /\.live-shell\s*\{[^}]*grid-template-rows:\s*minmax\(0,\s*1fr\) auto auto auto/s,
    )
    expect(portraitStyles).toMatch(
      /\.danmaku-panel\s*\{[^}]*grid-row:\s*2[^}]*max-height:\s*22dvh/s,
    )
    expect(portraitStyles).toMatch(/\.subtitle-overlay\s*\{[^}]*grid-row:\s*3/s)
    expect(portraitStyles).toMatch(/\.live-controls\s*\{[^}]*grid-row:\s*4/s)
    expect(liveStyles).toMatch(
      /\.subtitle-overlay\s*\{[^}]*max-height:\s*32dvh[^}]*overflow-y:\s*auto/s,
    )
  })

  it('reserves one shared safe area for subtitles and playback controls', () => {
    expect(liveStyles).toContain('--live-safe-bottom: max(16px, env(safe-area-inset-bottom))')
    expect(liveStyles).toContain(
      '--live-subtitle-bottom: calc(var(--live-safe-bottom) + var(--live-controls-height) + 12px)',
    )
    expect(liveStyles).toMatch(/\.live-controls\s*\{[^}]*bottom:\s*var\(--live-safe-bottom\)/s)
    expect(liveStyles).toMatch(
      /\.subtitle-overlay\s*\{[^}]*bottom:\s*var\(--live-subtitle-bottom\)/s,
    )
  })

  it('caps side panels on short desktop viewports without overriding portrait stacking', () => {
    expect(liveStyles).toContain(
      '@media (min-width: 761px) and (max-height: 600px) and (min-aspect-ratio: 4/3)',
    )
    expect(liveStyles).toMatch(
      /max-height: 600px[\s\S]*\.danmaku-panel\s*\{[^}]*max-height:\s*42dvh/s,
    )
  })
})
