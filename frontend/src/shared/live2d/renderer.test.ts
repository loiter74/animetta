import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fixtures = vi.hoisted(() => {
  const models: ReturnType<typeof createModel>[] = []
  const apps: {
    destroy: ReturnType<typeof vi.fn>
    listeners: Set<() => void>
    options: Record<string, unknown>
    screen: { width: number; height: number }
    renderer: { resolution: number; resize: ReturnType<typeof vi.fn> }
  }[] = []
  const limits = { renderbuffer: 8192, viewport: [8192, 8192] }
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
        breath: { setParameters: vi.fn() },
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
  return { models, apps, limits, createModel, from }
})

vi.mock('pixi-live2d-display/cubism4', () => ({ Live2DModel: { from: fixtures.from } }))
vi.mock('pixi.js', () => ({
  Application: class {
    screen = { width: 300, height: 400 }
    options: Record<string, unknown>
    listeners = new Set<() => void>()
    renderer = {
      resolution: 1,
      gl: {
        MAX_RENDERBUFFER_SIZE: 1,
        MAX_VIEWPORT_DIMS: 2,
        getParameter: (parameter: number) =>
          parameter === 1 ? fixtures.limits.renderbuffer : fixtures.limits.viewport,
      },
      resize: vi.fn(),
      on: (_event: string, listener: () => void) => this.listeners.add(listener),
      off: (_event: string, listener: () => void) => this.listeners.delete(listener),
    }
    stage = { addChild: vi.fn() }
    stop = vi.fn()
    destroy = vi.fn()
    constructor(options: Record<string, unknown>) {
      this.options = options
      this.renderer.resolution = Number(options.resolution ?? 1)
      if (typeof options.width === 'number') this.screen.width = options.width
      if (typeof options.height === 'number') this.screen.height = options.height
      const canvas = options.view as HTMLCanvasElement
      canvas.width = this.screen.width * this.renderer.resolution
      canvas.height = this.screen.height * this.renderer.resolution
      fixtures.apps.push(this)
    }
  },
}))

import { createLive2DRenderer } from './renderer'
import type { Live2DModelProfile } from './modelProfile'
import { DEFAULT_LIVE2D_MODEL_PROFILE, resolveLive2DModelProfile } from './modelProfiles'
import { DEFAULT_LIVE2D_PERFORMANCE_PLAN } from './performanceContract'
import { LIVE2D_UHD_SIZE, responsiveRenderResolution } from './renderResolution'
import { createFixedStepPhysics } from './fixedStepPhysics'

// The SDK fixture uses Mao's mouth parameter and does not include authored physics.
const mao = resolveLive2DModelProfile('mao')

const elements = () => ({
  canvas: document.createElement('canvas'),
  resizeTo: document.createElement('div'),
  profile: mao,
})

describe('instance Live2D renderer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fixtures.models.length = 0
    fixtures.apps.length = 0
    fixtures.limits.renderbuffer = 8192
    fixtures.limits.viewport = [8192, 8192]
  })
  afterEach(() => vi.unstubAllGlobals())

  it('renders a fixed 3840×2160 backing canvas independently of the embedded preview size', async () => {
    vi.stubGlobal('devicePixelRatio', 2)
    const options = elements()
    options.canvas.style.objectFit = 'contain'
    const renderer = createLive2DRenderer({ ...options, output: '4k' })
    await renderer.ready
    expect(options.canvas.width).toBe(3840)
    expect(options.canvas.height).toBe(2160)
    expect(fixtures.apps[0].screen).toEqual(LIVE2D_UHD_SIZE)
    expect(fixtures.apps[0].options.resizeTo).toBeUndefined()
    expect(fixtures.apps[0].renderer.resolution).toBe(1)
    expect(options.canvas.style.objectFit).toBe('cover')
    expect(options.canvas.dataset.renderState).toBe('live')
    expect(options.canvas.dataset.renderOutput).toBe('4k')
    renderer.setZoom(2)
    expect(options.canvas.width).toBe(3840)
    expect(options.canvas.height).toBe(2160)
    renderer.dispose()
    expect(options.canvas.style.objectFit).toBe('contain')
    expect(options.canvas.dataset.renderState).toBe('disposed')
  })

  it('reports unsupported UHD graphics limits without silently falling back to a lower resolution', async () => {
    fixtures.limits.renderbuffer = 2048
    const onState = vi.fn()
    const options = elements()
    const renderer = createLive2DRenderer({ ...options, output: '4k', onState })
    await renderer.ready
    expect(onState).toHaveBeenCalledExactlyOnceWith(
      'error',
      expect.objectContaining({ message: expect.stringContaining('3840×2160') }),
    )
    expect(fixtures.from).not.toHaveBeenCalled()
    expect(fixtures.apps[0].destroy).toHaveBeenCalledOnce()
    expect(options.canvas.dataset.renderState).toBe('error')
    renderer.dispose()
  })

  it('uses high DPI for responsive previews while bounding the backing surface to UHD', async () => {
    vi.stubGlobal('devicePixelRatio', 2)
    const options = elements()
    const renderer = createLive2DRenderer(options)
    await renderer.ready
    expect(fixtures.apps[0].options).toMatchObject({
      resizeTo: options.resizeTo,
      autoDensity: true,
      resolution: 2,
    })
    expect(responsiveRenderResolution(1920, 1080, 3)).toBe(2)
    expect(responsiveRenderResolution(3840, 2160, 2)).toBe(1)
    expect(responsiveRenderResolution(7680, 4320, 2)).toBe(0.5)
    expect(responsiveRenderResolution(800, 600, Number.NaN)).toBe(1)
    expect(responsiveRenderResolution(800, 600, Number.MIN_VALUE)).toBe(1)
    for (const [width, height] of [
      [0, 0],
      [-100, Number.NEGATIVE_INFINITY],
      [Number.NaN, Number.POSITIVE_INFINITY],
      [Number.MAX_VALUE, Number.MAX_VALUE],
    ]) {
      const resolution = responsiveRenderResolution(width, height, 2)
      expect(Number.isFinite(resolution)).toBe(true)
      expect(resolution).toBeGreaterThan(0)
      expect(resolution).toBeLessThanOrEqual(2)
    }
    renderer.dispose()
  })

  it('disables SDK head oscillation only for models with authored breathing', async () => {
    const authored = createLive2DRenderer({
      ...elements(),
      profile: { ...mao, automaticBreathing: false },
    })
    const defaults = createLive2DRenderer(elements())
    await Promise.all([authored.ready, defaults.ready])
    expect(fixtures.models[0].internalModel.breath.setParameters).toHaveBeenCalledWith([])
    expect(fixtures.models[1].internalModel.breath.setParameters).not.toHaveBeenCalled()
    authored.dispose()
    defaults.dispose()
  })

  it('replaces only the opted-in model physics stage and preserves other instances', async () => {
    const firstModel = fixtures.createModel(['ParamInput', 'ParamOutput'])
    const secondModel = fixtures.createModel(['ParamInput', 'ParamOutput'])
    const makePhysics = () => ({
      _physicsRig: {
        inputs: [{ source: { id: 'ParamInput' } }],
        outputs: [{ destination: { id: 'ParamOutput' } }],
      },
      evaluate: vi.fn(),
    })
    const firstPhysics = makePhysics()
    const secondPhysics = makePhysics()
    const originalFirst = firstPhysics.evaluate
    const originalSecond = secondPhysics.evaluate
    Object.assign(firstModel.internalModel, { physics: firstPhysics })
    Object.assign(secondModel.internalModel, { physics: secondPhysics })
    fixtures.from.mockResolvedValueOnce(firstModel).mockResolvedValueOnce(secondModel)
    const first = createLive2DRenderer({
      ...elements(),
      profile: { ...mao, fixedStepPhysics: true },
    })
    const second = createLive2DRenderer(elements())
    await Promise.all([first.ready, second.ready])
    expect(firstPhysics.evaluate).not.toBe(originalFirst)
    expect(secondPhysics.evaluate).toBe(originalSecond)
    expect(originalFirst).not.toHaveBeenCalled()
    expect(firstModel.listeners.size).toBe(1)
    first.dispose()
    second.dispose()
  })

  it('fails when the default whale model is missing its required authored physics', async () => {
    const onState = vi.fn()
    const options = { ...elements(), profile: DEFAULT_LIVE2D_MODEL_PROFILE, onState }
    const renderer = createLive2DRenderer(options)
    await renderer.ready
    expect(fixtures.from).toHaveBeenCalledWith(DEFAULT_LIVE2D_MODEL_PROFILE.modelUrl, {
      autoInteract: false,
    })
    expect(onState).toHaveBeenCalledExactlyOnceWith(
      'error',
      expect.objectContaining({ message: 'Authored Live2D physics could not be loaded' }),
    )
    expect(options.canvas.dataset.renderState).toBe('error')
    expect(fixtures.models[0].destroy).toHaveBeenCalledOnce()
    renderer.dispose()
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
        ...mao,
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
      ...mao,
      id: 'first',
      modelUrl: '/first.model3.json',
      mouthParameters: ['firstMouth'],
      performance: { resolve: firstResolve },
    }
    const secondProfile: Live2DModelProfile = {
      ...mao,
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

  it('zooms with cached dimensions while keeping the head visible and restores the fitted full body', async () => {
    const renderer = createLive2DRenderer({ ...elements() })
    renderer.setZoom(2)
    await renderer.ready
    const model = fixtures.models[0]
    expect(model.scale.set).toHaveBeenLastCalledWith(1.476)
    expect(model.position.set.mock.lastCall?.[1]).toBeCloseTo(615.2)
    renderer.setZoom(2)
    expect(model.scale.set).toHaveBeenLastCalledWith(1.476)
    renderer.setZoom(20)
    expect(model.scale.set.mock.lastCall?.[0]).toBeCloseTo(2.214)
    renderer.setZoom(1)
    expect(model.scale.set).toHaveBeenLastCalledWith(0.738)
    expect(model.position.set).toHaveBeenLastCalledWith(150, 320)
    renderer.dispose()
    model.scale.set.mockClear()
    renderer.setZoom(2)
    expect(model.scale.set).not.toHaveBeenCalled()
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

describe('fixed-step authored physics', () => {
  function fixture() {
    const ids = ['input', 'output', 'unrelated']
    const values = [0, 0, 0.7]
    const model = {
      getParameterCount: () => ids.length,
      getParameterIndex: (id: string) => ids.indexOf(id),
      getParameterValueByIndex: (index: number) => values[index],
      setParameterValueByIndex: (index: number, value: number) => {
        values[index] = value
      },
    }
    const physics = {
      _physicsRig: {
        inputs: [{ source: { id: 'input' } }, { source: { id: 'input' } }],
        outputs: [{ destination: { id: 'output' } }],
      },
      evaluate: vi.fn((_model: typeof model, delta: number) => {
        values[1] += values[0] * delta
      }),
    }
    return { model, physics, values }
  }

  it('keeps 30/60/120 Hz physics aligned without advancing a step input before its frame', () => {
    const run = (fps: number) => {
      const { model, physics, values } = fixture()
      const evaluate = createFixedStepPhysics(physics, model)
      const samples: number[] = []
      evaluate(model, 0)
      for (let frame = 1; frame <= fps * 2; frame++) {
        values[0] = frame / fps >= 1 ? 1 : 0
        evaluate(model, 1 / fps)
        expect(values[0]).toBe(frame / fps >= 1 ? 1 : 0)
        expect(values[2]).toBe(0.7)
        if (frame % (fps / 30) === 0) samples.push(values[1])
      }
      expect(physics.evaluate).toHaveBeenCalledTimes(120)
      expect(samples[28]).toBe(0)
      expect(samples[29]).toBe(0)
      expect(samples.at(-1)).toBeCloseTo(1)
      return samples
    }
    const reference = run(60)
    for (const fps of [30, 120]) {
      run(fps).forEach((value, at) => expect(value).toBeCloseTo(reference[at], 12))
    }
  })

  it('bounds resume work and rejects conflicting or missing rig parameters', () => {
    const { model, physics, values } = fixture()
    const evaluate = createFixedStepPhysics(physics, model)
    evaluate(model, 0)
    values[0] = 1
    evaluate(model, 60)
    expect(physics.evaluate).toHaveBeenCalledTimes(15)
    expect(values[0]).toBe(1)
    for (const delta of [Number.NaN, Number.POSITIVE_INFINITY, -1]) evaluate(model, delta)
    expect(physics.evaluate).toHaveBeenCalledTimes(15)
    physics._physicsRig.outputs[0].destination.id = 'input'
    expect(() => createFixedStepPhysics(physics, model)).toThrow('separate input and output')
    physics._physicsRig.outputs[0].destination.id = 'missing'
    expect(() => createFixedStepPhysics(physics, model)).toThrow('missing')
  })
})
