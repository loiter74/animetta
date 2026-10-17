import { describe, expect, it } from 'vitest'

import { applyLiveReviewLayout } from '../layout'

describe('livestream review layout', () => {
  it('anchors the danmaku panel near the upper-right corner', () => {
    applyLiveReviewLayout(document.documentElement)

    expect(document.documentElement.style.getPropertyValue('--live-danmaku-panel-top')).toBe('28px')
    expect(document.documentElement.style.getPropertyValue('--live-danmaku-panel-bottom')).toBe('')
  })
})
