import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveLive2DModelProfile } from '@/shared/live2d/modelProfiles'
import { mountAvatarPreview } from './avatar-preview'

afterEach(() => {
  vi.useRealTimers()
  document.body.replaceChildren()
})

describe('avatar preview on the live entrypoint', () => {
  it('keeps the controls out of the normal live surface', () => {
    document.body.innerHTML = '<main class="live-shell"></main>'
    const stage = { setExpression: vi.fn(), setMouth: vi.fn() }
    const dispose = mountAvatarPreview(
      document,
      new URLSearchParams(),
      resolveLive2DModelProfile('whale-maid-v1'),
      stage,
    )
    expect(dispose).toBeUndefined()
    expect(stage.setExpression).not.toHaveBeenCalled()
    expect(document.querySelector('[aria-label="立绘预览"]')).toBeNull()
  })

  it('switches both expressions and bounds mouth preview to twenty seconds with disposal', () => {
    vi.useFakeTimers()
    document.body.innerHTML = '<main class="live-shell"></main>'
    const stage = { setExpression: vi.fn(), setMouth: vi.fn() }
    const dispose = mountAvatarPreview(
      document,
      new URLSearchParams('review=1&expression=goofy'),
      resolveLive2DModelProfile('whale-maid-v1'),
      stage,
    )!
    const [standard, goofy, demo] = document.querySelectorAll('button')
    expect(stage.setExpression).toHaveBeenLastCalledWith('goofy')
    expect(goofy.getAttribute('aria-pressed')).toBe('true')
    standard.click()
    expect(stage.setExpression).toHaveBeenLastCalledWith('standard')
    demo.click()
    vi.advanceTimersByTime(200)
    expect(stage.setMouth).toHaveBeenLastCalledWith(expect.any(Number), 'avatar-preview')
    vi.advanceTimersByTime(20000)
    expect(stage.setMouth).toHaveBeenLastCalledWith(0)
    expect(vi.getTimerCount()).toBe(0)
    demo.click()
    dispose()
    expect(vi.getTimerCount()).toBe(0)
    expect(stage.setMouth).toHaveBeenLastCalledWith(0)
    expect(document.querySelector('[aria-label="立绘预览"]')).toBeNull()
  })
})
