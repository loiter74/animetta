import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { startLipSync, stopLipSync, tickLipSync } from './lipSync'

describe('audio-clock lip sync', () => {
  let frames: Map<number, FrameRequestCallback>
  let sequence: number

  function frame(): void {
    const callbacks = [...frames.values()]
    frames.clear()
    callbacks.forEach((callback) => callback(0))
  }

  beforeEach(() => {
    frames = new Map()
    sequence = 0
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      frames.set(++sequence, callback)
      return sequence
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => frames.delete(id))
  })

  afterEach(() => {
    stopLipSync()
    vi.unstubAllGlobals()
  })

  it('does not amplify the same audio sample again between animation frames', () => {
    const audio = { paused: false, ended: false, currentTime: 0 }
    const target = vi.fn()
    startLipSync(audio as HTMLAudioElement, [0.03], target)
    frame()
    const opening = target.mock.lastCall![0]
    for (let index = 0; index < 8; index++) frame()
    expect(target.mock.lastCall![0]).toBe(opening)
    expect(opening).toBeLessThan(0.1)
  })

  it('uses the selected mouth mapping and refreshes it even when the model stays the same', () => {
    const write = vi.fn()
    const model = {
      internalModel: {
        coreModel: {
          getParameterCount: () => 3,
          getParameterIndex: (name: string) =>
            ['ParamMouthOpenY', 'ParamA', 'CustomMouth'].indexOf(name),
          getParameterValueByIndex: () => 0,
          setParameterValueByIndex: write,
        },
      },
    }
    tickLipSync(model, ['CustomMouth'])
    expect(write).toHaveBeenLastCalledWith(2, expect.any(Number))
    tickLipSync(model, ['ParamA'])
    expect(write).toHaveBeenLastCalledWith(1, expect.any(Number))
    tickLipSync(model)
    expect(write).toHaveBeenLastCalledWith(0, expect.any(Number))
  })

  it('waits for actual playback without advancing the mouth timeline', () => {
    const audio = { paused: true, ended: false, currentTime: 0 }
    const target = vi.fn()
    startLipSync(audio as HTMLAudioElement, [0.5, 0.5, 0.5, 0, 0], target)
    for (let index = 0; index < 3; index++) frame()
    expect(target.mock.calls.every(([value]) => value === 0)).toBe(true)
    audio.paused = false
    frame()
    expect(target.mock.lastCall![0]).toBeGreaterThan(0)
  })

  it('keeps loud speech below full opening and releases through a silent gap', () => {
    const audio = { paused: false, ended: false, currentTime: 0 }
    const target = vi.fn()
    startLipSync(audio as HTMLAudioElement, [...Array(10).fill(1), ...Array(30).fill(0)], target)
    for (let index = 0; index < 40; index++) {
      audio.currentTime = index * 0.0201
      frame()
    }
    expect(Math.max(...target.mock.calls.map(([value]) => value))).toBeLessThanOrEqual(0.65)
    expect(target.mock.lastCall![0]).toBeLessThan(0.01)
  })

  it('cancels the old animation loop on replacement and closes on pause', () => {
    const audio = { paused: false, ended: false, currentTime: 0 }
    const oldTarget = vi.fn()
    const newTarget = vi.fn()
    startLipSync(audio as HTMLAudioElement, [0.5], oldTarget)
    frame()
    startLipSync(audio as HTMLAudioElement, [0.2], newTarget)
    oldTarget.mockClear()
    frame()
    expect(oldTarget).not.toHaveBeenCalled()
    audio.paused = true
    frame()
    expect(newTarget.mock.lastCall![0]).toBe(0)
    expect(frames.size).toBe(0)
  })
})
