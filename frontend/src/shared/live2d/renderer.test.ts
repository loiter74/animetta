import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixtures = vi.hoisted(() => {
  const models: ReturnType<typeof createModel>[] = []
  const apps: { destroy: ReturnType<typeof vi.fn>; listeners: Set<() => void> }[] = []
  function createModel() {
    const listeners = new Set<() => void>()
    const coreModel = {
      getParameterCount: () => 1,
      getParameterIndex: (name: string) => (name === 'ParamMouthOpenY' ? 0 : -1),
      getParameterValueByIndex: () => 0,
      setParameterValueByIndex: vi.fn(),
    }
    return {
      width: 400,
      height: 800,
      scale: { x: 1, y: 1, set: vi.fn() },
      position: { set: vi.fn() },
      anchor: { set: vi.fn() },
      internalModel: {
        coreModel,
        motionManager: {
          groups: { idle: 'Idle' },
          definitions: { Idle: [{}] },
          loadMotion: vi.fn().mockResolvedValue(null),
        },
        on: (_event: string, listener: () => void) => listeners.add(listener),
        off: (_event: string, listener: () => void) => listeners.delete(listener),
      },
      listeners,
      expression: vi.fn(),
      motion: vi.fn(),
      destroy: vi.fn(),
    }
  }
  const from = vi.fn(async () => {
    const model = createModel()
    models.push(model)
    return model
  })
  return { models, apps, createModel, from }
})

vi.mock('pixi-live2d-display/cubism4', () => ({ Live2DModel: { from: fixtures.from } }))
vi.mock('pixi.js', () => ({
  Application: class {
    screen = { width: 300, height: 400 }
    listeners = new Set<() => void>()
    renderer = {
      on: (_event: string, listener: () => void) => this.listeners.add(listener),
      off: (_event: string, listener: () => void) => this.listeners.delete(listener),
    }
    stage = { addChild: vi.fn() }
    stop = vi.fn()
    destroy = vi.fn()
    constructor() {
      fixtures.apps.push(this)
    }
  },
}))

import { createLive2DRenderer } from './renderer'

const elements = () => ({
  canvas: document.createElement('canvas'),
  resizeTo: document.createElement('div'),
})

describe('instance Live2D renderer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fixtures.models.length = 0
    fixtures.apps.length = 0
  })

  it('isolates mouth, callbacks, actions and disposal across two instances without global DOM IDs', async () => {
    const firstApplied = vi.fn()
    const secondApplied = vi.fn()
    const first = createLive2DRenderer({ ...elements(), onMouthApplied: firstApplied })
    const second = createLive2DRenderer({ ...elements(), onMouthApplied: secondApplied })
    await Promise.all([first.ready, second.ready])
    first.setMouth(0.3, 'first')
    second.setMouth(0.8, 'second')
    fixtures.models.forEach((model) => model.listeners.forEach((listener) => listener()))
    expect(firstApplied).toHaveBeenLastCalledWith(0.3, 'first')
    expect(secondApplied).toHaveBeenLastCalledWith(0.8, 'second')
    first.dispose()
    first.dispose()
    expect(fixtures.models[0].destroy).toHaveBeenCalledOnce()
    expect(fixtures.apps[0].destroy).toHaveBeenCalledOnce()
    expect(fixtures.models[0].listeners.size).toBe(0)
    expect(fixtures.apps[0].listeners.size).toBe(0)
    expect(fixtures.models[1].destroy).not.toHaveBeenCalled()
    second.applyAction({ type: 'motion', group: 'TapBody', index: 2 })
    first.applyAction({ type: 'expression', name: 'smile' })
    expect(fixtures.models[0].expression).not.toHaveBeenCalled()
    expect(fixtures.models[1].motion).toHaveBeenCalledWith('TapBody', 2)
    second.setMouth(0.6, 'still-active')
    fixtures.models[1].listeners.forEach((listener) => listener())
    expect(secondApplied).toHaveBeenLastCalledWith(0.6, 'still-active')
    second.dispose()
    expect(fixtures.models[1].listeners.size).toBe(0)
    expect(fixtures.apps[1].listeners.size).toBe(0)
  })

  it('destroys a late model after disposal without status callbacks or listeners', async () => {
    const model = fixtures.createModel()
    let resolve!: (value: typeof model) => void
    fixtures.from.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const onState = vi.fn()
    const renderer = createLive2DRenderer({ ...elements(), onState })
    renderer.dispose()
    resolve(model)
    await renderer.ready
    expect(model.destroy).toHaveBeenCalledOnce()
    expect(onState).not.toHaveBeenCalled()
    expect(model.listeners.size).toBe(0)
    expect(fixtures.apps[0].destroy).toHaveBeenCalledOnce()
  })

  it('handles disposal during asynchronous motion loading', async () => {
    const model = fixtures.createModel()
    let finish!: () => void
    model.internalModel.motionManager.loadMotion.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = () => resolve(null)
        }),
    )
    fixtures.from.mockResolvedValueOnce(model)
    const onState = vi.fn()
    const renderer = createLive2DRenderer({ ...elements(), onState })
    await Promise.resolve()
    renderer.dispose()
    finish()
    await renderer.ready
    expect(model.destroy).toHaveBeenCalledOnce()
    expect(onState).not.toHaveBeenCalled()
    expect(model.listeners.size).toBe(0)
  })

  it('releases failed initialization and reports an error without leaking an application', async () => {
    fixtures.from.mockRejectedValueOnce(new Error('model unavailable'))
    const onState = vi.fn()
    const renderer = createLive2DRenderer({ ...elements(), onState })
    await renderer.ready
    expect(onState).toHaveBeenCalledWith('error', expect.any(Error))
    expect(fixtures.apps[0].destroy).toHaveBeenCalledOnce()
    renderer.dispose()
    expect(fixtures.apps[0].destroy).toHaveBeenCalledOnce()
  })
})
