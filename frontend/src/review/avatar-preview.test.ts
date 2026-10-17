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
    const stage = { setExpression: vi.fn(), setMouth: vi.fn(), setZoom: vi.fn() }
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
    const stage = { setExpression: vi.fn(), setMouth: vi.fn(), setZoom: vi.fn() }
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

  it('enlarges the actual model and restores full-body framing without changing expressions', () => {
    document.body.innerHTML = '<main class="live-shell"></main>'
    const stage = { setExpression: vi.fn(), setMouth: vi.fn(), setZoom: vi.fn() }
    const dispose = mountAvatarPreview(
      document,
      new URLSearchParams('review=1'),
      resolveLive2DModelProfile('whale-maid-v1'),
      stage,
    )!
    const button = (label: string) =>
      [...document.querySelectorAll('button')].find((item) => item.textContent === label)!
    const larger = button('放大')
    larger.click()
    larger.click()
    expect(stage.setZoom).toHaveBeenLastCalledWith(1.5)
    expect(document.querySelector('[aria-label="立绘缩放"]')?.textContent).toBe('150%')
    button('缩小').click()
    expect(stage.setZoom).toHaveBeenLastCalledWith(1.25)
    button('全身').click()
    expect(stage.setZoom).toHaveBeenLastCalledWith(1)
    button('缩小').click()
    expect(stage.setZoom).toHaveBeenLastCalledWith(1)
    expect(stage.setExpression).toHaveBeenCalledOnce()
    dispose()
    stage.setZoom.mockClear()
    larger.click()
    expect(stage.setZoom).not.toHaveBeenCalled()
  })
})
