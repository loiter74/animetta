import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveLive2DModelProfile } from '@/shared/live2d/modelProfiles'
import { bindAvatarPreview } from './avatar-preview'
import type { AvatarPreviewCommand } from '@/shared/live2d/previewContract'

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.replaceChildren()
})

function fixture() {
  document.body.innerHTML =
    '<p id="modelStatus" data-state="live" data-emotion="neutral" data-expression="standard" data-expression-mode="auto"></p>'
  const parent = window.open('', 'avatar-dashboard')!
  const post = vi.spyOn(parent, 'postMessage').mockImplementation(() => {})
  vi.spyOn(window, 'parent', 'get').mockReturnValue(parent)
  const stage = { setExpression: vi.fn(), setEmotion: vi.fn(), setMouth: vi.fn(), setZoom: vi.fn() }
  const search = new URLSearchParams('review=1&media=muted&avatarDebug=1')
  const send = (
    command: AvatarPreviewCommand,
    origin = window.location.origin,
    source: Window = parent,
  ) => {
    window.dispatchEvent(
      new MessageEvent('message', {
        origin,
        source,
        data: { type: 'animetta:avatar-preview-command', command },
      }),
    )
  }
  return { stage, search, send, post }
}

describe('avatar debug bridge', () => {
  it('keeps controls off live and refuses debug commands outside an embedded opt-in preview', () => {
    const { stage, search, send } = fixture()
    const profile = resolveLive2DModelProfile('whale-maid-v1')
    expect(
      bindAvatarPreview(document, new URLSearchParams('review=1'), profile, stage),
    ).toBeUndefined()
    send({ type: 'expression', name: 'goofy' })
    expect(stage.setExpression).not.toHaveBeenCalled()
    vi.spyOn(window, 'parent', 'get').mockReturnValue(window)
    expect(bindAvatarPreview(document, search, profile, stage)).toBeUndefined()
    expect(document.querySelector('[aria-label="立绘预览"]')).toBeNull()
  })

  it('accepts only same-origin parent commands and returns observed state', () => {
    const { stage, search, send, post } = fixture()
    const dispose = bindAvatarPreview(
      document,
      search,
      resolveLive2DModelProfile('whale-maid-v1'),
      stage,
    )!
    expect(post).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'animetta:avatar-preview-state',
        state: expect.objectContaining({
          loaded: true,
          emotion: 'neutral',
          expression: 'standard',
        }),
      }),
      window.location.origin,
    )
    send({ type: 'expression', name: 'goofy' }, 'https://untrusted.example')
    send({ type: 'expression', name: 'goofy' }, window.location.origin, window)
    send({ type: 'expression', name: 'missing' })
    expect(stage.setExpression).not.toHaveBeenCalled()
    send({ type: 'expression', name: 'goofy' })
    expect(stage.setExpression).toHaveBeenLastCalledWith('goofy')
    send({ type: 'emotion', emotion: 'happy' })
    expect(stage.setExpression).toHaveBeenLastCalledWith(null)
    expect(stage.setEmotion).toHaveBeenLastCalledWith('happy')
    send({ type: 'emotion', emotion: 'invalid' })
    expect(stage.setEmotion).toHaveBeenCalledOnce()
    send({ type: 'zoom', value: 10 })
    expect(stage.setZoom).toHaveBeenLastCalledWith(3)
    send({ type: 'zoom', value: Number.NaN })
    expect(stage.setZoom).toHaveBeenCalledOnce()
    dispose()
    stage.setExpression.mockClear()
    send({ type: 'expression', name: 'goofy' })
    expect(stage.setExpression).not.toHaveBeenCalled()
  })

  it('bounds the local mouth demo and releases timers on disposal', () => {
    vi.useFakeTimers()
    const { stage, search, send } = fixture()
    const dispose = bindAvatarPreview(
      document,
      search,
      resolveLive2DModelProfile('whale-maid-v1'),
      stage,
    )!
    send({ type: 'mouth-demo' })
    vi.advanceTimersByTime(200)
    expect(stage.setMouth).toHaveBeenLastCalledWith(expect.any(Number), 'avatar-preview')
    vi.advanceTimersByTime(20000)
    expect(stage.setMouth).toHaveBeenLastCalledWith(0)
    expect(vi.getTimerCount()).toBe(0)
    send({ type: 'mouth-demo' })
    send({ type: 'reset' })
    expect(stage.setZoom).toHaveBeenLastCalledWith(1)
    expect(stage.setEmotion).toHaveBeenLastCalledWith('neutral')
    send({ type: 'mouth-demo' })
    dispose()
    expect(vi.getTimerCount()).toBe(0)
    expect(stage.setMouth).toHaveBeenLastCalledWith(0)
  })
})
