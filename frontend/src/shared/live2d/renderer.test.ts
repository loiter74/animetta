import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixtures = vi.hoisted(() => {
  const models: ReturnType<typeof createModel>[] = []
  const apps: { destroy: ReturnType<typeof vi.fn>; listeners: Set<() => void> }[] = []
  function createModel(parameterIds = ['ParamA']) {
    const listeners = new Set<() => void>()
    const values = new Map<number, number>()
    const coreModel = {
      getParameterCount: () => parameterIds.length,
      getParameterIndex: (name: string) => parameterIds.indexOf(name),
      getParameterValueByIndex: (index: number) => values.get(index) ?? 0,
      setParameterValueByIndex: vi.fn((index: number, value: number) => values.set(index, value)),
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
          state: { currentGroup: 'Idle' },
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
import type { Live2DModelProfile } from './modelProfile'
import { DEFAULT_LIVE2D_MODEL_PROFILE } from './modelProfiles'
import { DEFAULT_LIVE2D_PERFORMANCE_PLAN } from './performanceContract'

const elements = () => ({
  canvas: document.createElement('canvas'),
  resizeTo: document.createElement('div'),
  profile: DEFAULT_LIVE2D_MODEL_PROFILE,
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

  it('preserves a selected smile while applying speech opening and reports the applied value', async () => {
    const applied = vi.fn()
    const renderer = createLive2DRenderer({
      ...elements(),
      profile: {
        ...DEFAULT_LIVE2D_MODEL_PROFILE,
        expressions: {
          standard: { label: '标准', mouthRest: 0 },
          goofy: { label: '傻笑', mouthRest: 0.8 },
        },
      },
      onMouthApplied: applied,
    })
    await renderer.ready
    const model = fixtures.models[0]
    renderer.applyAction({ type: 'expression', name: 'goofy' })
    model.listeners.forEach((listener) => listener())
    expect(model.internalModel.coreModel.getParameterValueByIndex(0)).toBe(0.8)
    expect(applied).not.toHaveBeenCalled()
    renderer.applyAction({ type: 'expression', name: 'unsupported' })
    model.listeners.forEach((listener) => listener())
    expect(model.internalModel.coreModel.getParameterValueByIndex(0)).toBe(0.8)
    expect(model.expression).toHaveBeenCalledTimes(1)
    renderer.setMouth(0.5, 'speech')
    model.listeners.forEach((listener) => listener())
    expect(applied).toHaveBeenLastCalledWith(0.9, 'speech')
    renderer.applyAction({ type: 'expression', name: 'standard' })
    renderer.setMouth(0)
    model.listeners.forEach((listener) => listener())
    expect(model.internalModel.coreModel.getParameterValueByIndex(0)).toBe(0)
    renderer.dispose()
  })

  it('uses independent model URLs, declared mouth parameters and performance profiles', async () => {
    const firstModel = fixtures.createModel(['ParamMouthOpenY', 'firstMouth', 'firstEmotion'])
    const secondModel = fixtures.createModel(['ParamMouthOpenY', 'secondMouth', 'secondEmotion'])
    fixtures.from.mockResolvedValueOnce(firstModel).mockResolvedValueOnce(secondModel)
    const firstResolve = vi.fn((plan: typeof DEFAULT_LIVE2D_PERFORMANCE_PLAN) =>
      plan.base === 'surprised' ? [{ name: 'firstEmotion', offset: 0.4, min: 0, max: 1 }] : [],
    )
    const secondResolve = vi.fn((plan: typeof DEFAULT_LIVE2D_PERFORMANCE_PLAN) =>
      plan.base === 'annoyed' ? [{ name: 'secondEmotion', offset: 0.6, min: 0, max: 1 }] : [],
    )
    const firstProfile: Live2DModelProfile = {
      ...DEFAULT_LIVE2D_MODEL_PROFILE,
      id: 'first',
      modelUrl: '/first.model3.json',
      mouthParameters: ['firstMouth'],
      performance: { resolve: firstResolve },
    }
    const secondProfile: Live2DModelProfile = {
      ...DEFAULT_LIVE2D_MODEL_PROFILE,
      id: 'second',
      modelUrl: '/second.model3.json',
      mouthParameters: ['secondMouth'],
      performance: { resolve: secondResolve },
    }
    const first = createLive2DRenderer({ ...elements(), profile: firstProfile })
    const second = createLive2DRenderer({ ...elements(), profile: secondProfile })
    await Promise.all([first.ready, second.ready])
    expect(fixtures.from).toHaveBeenNthCalledWith(1, '/first.model3.json', { autoInteract: false })
    expect(fixtures.from).toHaveBeenNthCalledWith(2, '/second.model3.json', { autoInteract: false })
    first.setMouth(0.3)
    second.setMouth(0.8)
    first.armPerformance({ ...DEFAULT_LIVE2D_PERFORMANCE_PLAN, base: 'surprised' }, 'first')
    second.armPerformance({ ...DEFAULT_LIVE2D_PERFORMANCE_PLAN, base: 'annoyed' }, 'second')
    first.startPerformance('first')
    second.startPerformance('first')
    firstModel.listeners.forEach((listener) => listener())
    secondModel.listeners.forEach((listener) => listener())
    expect(firstModel.internalModel.coreModel.getParameterValueByIndex(1)).toBe(0.3)
    expect(firstModel.internalModel.coreModel.getParameterValueByIndex(2)).toBe(0.4)
    expect(secondModel.internalModel.coreModel.getParameterValueByIndex(1)).toBe(0.8)
    expect(secondModel.internalModel.coreModel.getParameterValueByIndex(2)).toBe(0)
    expect(secondResolve).not.toHaveBeenCalled()
    second.startPerformance('second')
    secondModel.listeners.forEach((listener) => listener())
    expect(secondModel.internalModel.coreModel.getParameterValueByIndex(2)).toBe(0.6)
    for (const model of [firstModel, secondModel]) {
      expect(model.internalModel.coreModel.setParameterValueByIndex).not.toHaveBeenCalledWith(
        0,
        expect.any(Number),
      )
    }
    first.dispose()
    secondModel.listeners.forEach((listener) => listener())
    expect(secondModel.internalModel.coreModel.getParameterValueByIndex(1)).toBe(0.8)
    expect(secondModel.destroy).not.toHaveBeenCalled()
    second.dispose()
  })

  it('keeps Mao framing and amplifies its configured idle parameters only in the idle group', async () => {
    const model = fixtures.createModel(['ParamA', 'ParamAngleX'])
    const { coreModel, motionManager } = model.internalModel
    motionManager.groups.idle = 'Rest'
    motionManager.state.currentGroup = 'Rest'
    coreModel.setParameterValueByIndex(1, 0.1)
    fixtures.from.mockResolvedValueOnce(model)
    const renderer = createLive2DRenderer({ ...elements(), idleVitality: true })
    await renderer.ready
    expect(fixtures.from).toHaveBeenCalledWith('/live2d/mao/Mao.model3.json', {
      autoInteract: false,
    })
    expect(model.scale.set).toHaveBeenCalledWith(0.738)
    expect(model.position.set).toHaveBeenCalledWith(150, 320)
    model.listeners.forEach((listener) => listener())
    expect(coreModel.getParameterValueByIndex(1)).toBeCloseTo(0.23)
    coreModel.setParameterValueByIndex(1, 0.1)
    motionManager.state.currentGroup = 'TapBody'
    model.listeners.forEach((listener) => listener())
    expect(coreModel.getParameterValueByIndex(1)).toBe(0.1)
    renderer.dispose()
  })

  it('can fit a different full-body model without applying Mao performance or idle parameters', async () => {
    const model = fixtures.createModel(['ParamMouthOpenY', 'ParamMouthDown', 'ParamAngleX'])
    fixtures.from.mockResolvedValueOnce(model)
    const renderer = createLive2DRenderer({
      ...elements(),
      profile: {
        id: 'full-body',
        modelUrl: '/live2d/custom/model.model3.json',
        mouthParameters: ['ParamMouthOpenY'],
        framing: { scale: 1, x: 0.5, y: 0.5 },
        semanticMotions: {},
        performance: { resolve: () => [] },
      },
      idleVitality: true,
    })
    await renderer.ready
    expect(fixtures.from).toHaveBeenCalledWith('/live2d/custom/model.model3.json', {
      autoInteract: false,
    })
    expect(model.scale.set).toHaveBeenCalledWith(0.41)
    expect(model.position.set).toHaveBeenCalledWith(150, 200)
    renderer.armPerformance({ ...DEFAULT_LIVE2D_PERFORMANCE_PLAN, base: 'annoyed' }, 'custom')
    renderer.startPerformance('custom')
    renderer.setMouth(0.4)
    model.listeners.forEach((listener) => listener())
    expect(model.internalModel.coreModel.setParameterValueByIndex).toHaveBeenCalledExactlyOnceWith(
      0,
      0.4,
    )
    renderer.dispose()
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
