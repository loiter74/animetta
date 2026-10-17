import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_LIVE2D_MODEL_PROFILE,
  resolveLive2DModelProfile,
} from '@/shared/live2d/modelProfiles'
import { bindLive2DEmotionSocket } from '@/shared/live2d/emotionSocket'
import { Events } from '@/constants/socket-events'
import type { LiveSocket } from '@/shared/transport/liveSocket'

const fixtures = vi.hoisted(() => {
  let beforeModelUpdate: (() => void) | null = null
  let applicationOptions: Record<string, unknown> | null = null
  const screen = { width: 1080, height: 1920 }
  let resizeListener: (() => void) | null = null
  const renderer = {
    resolution: 1,
    resize: vi.fn((width: number, height: number) => {
      screen.width = width
      screen.height = height
      resizeListener?.()
    }),
    on: vi.fn((_event: string, listener: () => void) => {
      resizeListener = listener
    }),
    off: vi.fn(() => {
      resizeListener = null
    }),
  }
  const setParameterValueByIndex = vi.fn()
  const parameterNames = [
    'ParamA',
    'ParamAngleX',
    'ParamAngleY',
    'ParamAngleZ',
    'ParamBodyAngleX',
    'ParamBodyAngleY',
    'ParamBodyAngleZ',
    'ParamBreath',
  ]
  const parameterValues = Array.from({ length: parameterNames.length }, () => 0)
  const motionState: { currentGroup?: string } = { currentGroup: 'Idle' }
  const idleMotions = [
    { setIsLoop: vi.fn(), setIsLoopFadeIn: vi.fn() },
    { setIsLoop: vi.fn(), setIsLoopFadeIn: vi.fn() },
  ]
  setParameterValueByIndex.mockImplementation((index: number, value: number) => {
    parameterValues[index] = value
  })
  const model = {
    width: 400,
    height: 800,
    scale: { x: 1, y: 1, set: vi.fn() },
    anchor: { set: vi.fn() },
    position: { set: vi.fn() },
    internalModel: {
      breath: { setParameters: vi.fn() },
      physics: { _physicsRig: { inputs: [], outputs: [] }, evaluate: vi.fn() },
      coreModel: {
        getParameterCount: vi.fn().mockReturnValue(parameterNames.length),
        getParameterIndex: vi.fn((name: string) => parameterNames.indexOf(name)),
        getParameterValueByIndex: vi.fn((index: number) => parameterValues[index]),
        getParameterDefaultValue: vi.fn((index: number) => (index === 1 ? 2 : 0)),
        getParameterMinimumValue: vi.fn((index: number) =>
          index === 7 ? 0 : parameterNames[index].startsWith('ParamBodyAngle') ? -10 : -30,
        ),
        getParameterMaximumValue: vi.fn((index: number) =>
          index === 7 ? 1 : parameterNames[index].startsWith('ParamBodyAngle') ? 10 : 30,
        ),
        setParameterValueByIndex,
      },
      motionManager: {
        state: motionState,
        groups: { idle: 'Idle' },
        definitions: { Idle: [{}, {}] },
        loadMotion: vi.fn((_group: string, index: number) => Promise.resolve(idleMotions[index])),
        stopAllMotions: vi.fn(),
      },
      on: vi.fn((_event: string, listener: () => void) => {
        beforeModelUpdate = listener
      }),
      off: vi.fn(),
    },
    expression: vi.fn(),
    motion: vi.fn().mockResolvedValue(undefined),
    destroy: vi.fn(),
  }
  return {
    screen,
    renderer,
    emitRendererResize: (width: number, height: number) => {
      screen.width = width
      screen.height = height
      resizeListener?.()
    },
    model,
    idleMotions,
    setParameterValueByIndex,
    setApplicationOptions: (options: Record<string, unknown>) => {
      applicationOptions = options
      renderer.resolution = Number(options.resolution ?? 1)
    },
    resetModelState: () => {
      screen.width = 1080
      screen.height = 1920
      resizeListener = null
      renderer.resolution = 1
      parameterValues.fill(0)
      motionState.currentGroup = 'Idle'
    },
    setParameterValue: (name: string, value: number) => {
      parameterValues[parameterNames.indexOf(name)] = value
    },
    getParameterValue: (name: string) => parameterValues[parameterNames.indexOf(name)],
    setMotionGroup: (group: string) => {
      motionState.currentGroup = group
    },
    getApplicationOptions: () => applicationOptions,
    emitBeforeModelUpdate: () => beforeModelUpdate?.(),
  }
})

vi.mock('pixi.js', () => ({
  Application: class {
    screen = fixtures.screen
    renderer = fixtures.renderer
    stage = { addChild: vi.fn() }
    stop = vi.fn()
    destroy = vi.fn()
    constructor(options: Record<string, unknown>) {
      fixtures.setApplicationOptions(options)
    }
  },
}))
vi.mock('pixi-live2d-display/cubism4', () => ({
  Live2DModel: { from: vi.fn().mockResolvedValue(fixtures.model) },
}))

describe('createLive2DStage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fixtures.resetModelState()
    document.body.innerHTML = `
      <canvas id="live2dCanvas"></canvas>
      <p id="modelStatus"></p>
      <span id="audioStatus" data-lip-sync-applied-count="0" data-lip-sync-peak="0"></span>
    `
  })

  it('fits the model after the renderer changes size and removes the resize listener on disposal', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const stage = createLive2DStage({ on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() })
    await stage.ready
    expect(document.getElementById('modelStatus')?.dataset.state).toBe('live')
    fixtures.emitRendererResize(300, 400)
    expect(fixtures.model.position.set).toHaveBeenLastCalledWith(150, 320)
    const appliedScale = fixtures.model.scale.set.mock.lastCall?.[0]
    expect(appliedScale).toBeCloseTo(0.738)
    fixtures.emitRendererResize(7680, 4320)
    expect(fixtures.renderer.resolution).toBe(0.5)
    expect(fixtures.renderer.resize).toHaveBeenLastCalledWith(7680, 4320)
    expect(fixtures.model.position.set).toHaveBeenLastCalledWith(3840, 3456)
    stage.dispose()
    const calls = fixtures.model.position.set.mock.calls.length
    fixtures.emitRendererResize(600, 800)
    expect(fixtures.model.position.set).toHaveBeenCalledTimes(calls)
  })

  it('retains emotion while loading and lets manual preview override automatic events until released', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const handlers = new Map<string, (...args: unknown[]) => void>()
    const socket = {
      on: vi.fn((event: string, handler: (...args: unknown[]) => void) => {
        handlers.set(event, handler)
        return socket
      }),
      off: vi.fn().mockReturnThis(),
    }
    const profile = { ...resolveLive2DModelProfile('whale-maid-v1'), mouthParameters: ['ParamA'] }
    const stage = createLive2DStage(socket, { profile })
    const frame = {
      message_id: 'm1',
      conversation_id: 'c1',
      task_id: 't1',
      turn_id: 't1',
      emotion: 'happy',
    }
    handlers.get(Events.CHAT.EXPRESSION)!(frame)
    await stage.ready
    expect(fixtures.model.expression).toHaveBeenLastCalledWith('goofy')
    fixtures.emitBeforeModelUpdate()
    expect(fixtures.getParameterValue('ParamA')).toBeCloseTo(0.82)
    stage.setExpression('standard')
    handlers.get(Events.CHAT.LIVE2D_ACTION)!({ type: 'expression', name: 'goofy' })
    handlers.get(Events.CHAT.EXPRESSION)!({ ...frame, emotion: 'sad' })
    expect(fixtures.model.expression).toHaveBeenLastCalledWith('standard')
    expect(document.getElementById('modelStatus')?.dataset.expressionMode).toBe('manual')
    handlers.get(Events.CHAT.EXPRESSION)!(frame)
    stage.setExpression(null)
    expect(fixtures.model.expression).toHaveBeenLastCalledWith('goofy')
    expect(document.getElementById('modelStatus')?.dataset.emotion).toBe('happy')
    handlers.get('disconnect')!()
    expect(fixtures.model.expression).toHaveBeenLastCalledWith('standard')
    stage.dispose()
  })

  it('owns the only review playback and samples mouth volume in the model frame', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const socket = { on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() }
    const stage = createLive2DStage(socket)
    await stage.ready
    const notification = document.createElement('aside')
    const audio = document.createElement('audio')
    audio.id = 'reviewAudio'
    Object.defineProperties(audio, {
      currentTime: { value: 0, writable: true },
      paused: { value: false },
      ended: { value: false },
    })
    const play = vi.spyOn(audio, 'play').mockResolvedValue()
    notification.append(audio)

    stage.playReviewAudio(
      notification,
      Array.from({ length: 10 }, () => 0.8),
    )
    fixtures.emitBeforeModelUpdate()

    expect(play).toHaveBeenCalledOnce()
    expect(fixtures.setParameterValueByIndex).toHaveBeenCalledWith(0, expect.any(Number))
    expect(notification.dataset.lipSync).toBe('observed')
    stage.dispose()
    stage.dispose()
  })

  it('applies production mouth targets inside the Live2D model frame', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const socket = { on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() }
    const stage = createLive2DStage(socket)
    await stage.ready

    stage.setMouth(0.8, 'task-1')
    fixtures.emitBeforeModelUpdate()

    expect(fixtures.setParameterValueByIndex).toHaveBeenLastCalledWith(0, 0.8)
    expect(document.getElementById('audioStatus')).toHaveProperty(
      'dataset.lastLipSyncTaskId',
      'task-1',
    )
    expect(document.getElementById('audioStatus')).toHaveProperty(
      'dataset.lipSyncAppliedCount',
      '1',
    )
    expect(Number(document.getElementById('audioStatus')?.dataset.lipSyncPeak)).toBe(0.8)
    stage.dispose()
  })

  it('unsubscribes its own socket handler and ignores actions after disposal', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const socket = { on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() }
    const stage = createLive2DStage(socket)
    await stage.ready
    const [event, handler] = socket.on.mock.calls[0]
    handler({ type: 'expression', name: 'smile' })
    expect(fixtures.model.expression).toHaveBeenCalledWith('smile')
    stage.dispose()
    expect(socket.off).toHaveBeenCalledWith(event, handler)
    handler({ type: 'expression', name: 'late' })
    expect(fixtures.model.expression).toHaveBeenCalledOnce()
  })

  it('detaches replaced audio callbacks and ignores a late playback rejection', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const stage = createLive2DStage({ on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() })
    await stage.ready
    const first = document.createElement('aside')
    const second = document.createElement('aside')
    const oldAudio = document.createElement('audio')
    const newAudio = document.createElement('audio')
    for (const audio of [oldAudio, newAudio]) {
      audio.id = 'reviewAudio'
      Object.defineProperties(audio, {
        currentTime: { value: 0 },
        paused: { value: false },
        ended: { value: false },
      })
    }
    let reject!: (reason: Error) => void
    vi.spyOn(oldAudio, 'play').mockReturnValue(
      new Promise((_resolve, fail) => {
        reject = fail
      }),
    )
    vi.spyOn(newAudio, 'play').mockResolvedValue()
    const removeOld = vi.spyOn(oldAudio, 'removeEventListener')
    const removeNew = vi.spyOn(newAudio, 'removeEventListener')
    first.append(oldAudio)
    second.append(newAudio)
    stage.playReviewAudio(first, Array(10).fill(0.4))
    stage.playReviewAudio(second, Array(10).fill(0.8))
    expect(removeOld).toHaveBeenCalledWith('ended', expect.any(Function))
    expect(removeOld).toHaveBeenCalledWith('error', expect.any(Function))
    reject(new Error('late rejection'))
    await Promise.resolve()
    await Promise.resolve()
    oldAudio.dispatchEvent(new Event('ended'))
    fixtures.emitBeforeModelUpdate()
    expect(second.dataset.lipSync).toBe('observed')
    expect(oldAudio.dataset.complete).toBeUndefined()
    stage.dispose()
    expect(removeNew).toHaveBeenCalledWith('ended', expect.any(Function))
    expect(removeNew).toHaveBeenCalledWith('error', expect.any(Function))
  })

  it('can size the shared stage to a bounded broadcast avatar container', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const socket = { on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() }
    const avatarContainer = document.createElement('section')

    const stage = createLive2DStage(socket, { resizeTo: avatarContainer })
    await stage.ready

    expect(fixtures.getApplicationOptions()?.resizeTo).toBe(avatarContainer)
    stage.dispose()
  })

  it('maps sanitized public cues only to existing Mao motion assets', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const socket = { on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() }
    const stage = createLive2DStage(socket, { profile: DEFAULT_LIVE2D_MODEL_PROFILE })

    stage.applyPublicCue({
      sourceEventId: 'activity:1',
      phase: 'planning',
      emotion: 'thinking',
    })
    await stage.ready
    stage.applyPublicCue({
      sourceEventId: 'activity:1',
      phase: 'planning',
      emotion: 'thinking',
    })
    stage.applyPublicCue({
      sourceEventId: 'activity:2',
      phase: 'recovering',
      emotion: 'thinking',
    })

    expect(fixtures.model.motion).toHaveBeenCalledOnce()
    expect(fixtures.model.motion).toHaveBeenCalledWith('TapBody', 0)
    stage.dispose()
  })

  it('keeps authored idle motion continuous when the same motion loops', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const socket = { on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() }

    const stage = createLive2DStage(socket)
    await stage.ready

    expect(fixtures.idleMotions[0].setIsLoop).toHaveBeenCalledWith(true)
    expect(fixtures.idleMotions[1].setIsLoop).toHaveBeenCalledWith(true)
    expect(fixtures.idleMotions[0].setIsLoopFadeIn).toHaveBeenCalledWith(false)
    expect(fixtures.idleMotions[1].setIsLoopFadeIn).toHaveBeenCalledWith(false)
    stage.dispose()
  })

  it('amplifies idle motion without hitting hard parameter limits', async () => {
    const { createLive2DStage } = await import('./live2d-stage')
    const socket = { on: vi.fn().mockReturnThis(), off: vi.fn().mockReturnThis() }
    const stage = createLive2DStage(socket, {
      idleVitality: true,
      profile: DEFAULT_LIVE2D_MODEL_PROFILE,
    })
    await stage.ready

    fixtures.setParameterValue('ParamAngleX', 8)
    fixtures.setParameterValue('ParamBodyAngleX', 4)
    fixtures.setParameterValue('ParamBreath', 0.9)
    fixtures.emitBeforeModelUpdate()

    expect(fixtures.getParameterValue('ParamAngleX')).toBeCloseTo(15.8)
    expect(fixtures.getParameterValue('ParamBodyAngleX')).toBeGreaterThan(9)
    expect(fixtures.getParameterValue('ParamBodyAngleX')).toBeLessThan(10)
    expect(fixtures.getParameterValue('ParamBreath')).toBeCloseTo(1, 3)

    fixtures.setMotionGroup('TapBody')
    fixtures.setParameterValue('ParamAngleX', 8)
    fixtures.emitBeforeModelUpdate()
    expect(fixtures.getParameterValue('ParamAngleX')).toBe(8)
    stage.dispose()
  })
})

describe('bindLive2DEmotionSocket', () => {
  function harness() {
    const handlers = new Map<string, Set<(...args: unknown[]) => void>>()
    const socket: LiveSocket = {
      on: vi.fn((event, handler) => {
        if (!handlers.has(event)) handlers.set(event, new Set())
        handlers.get(event)!.add(handler)
        return socket
      }),
      off: vi.fn((event, handler) => {
        handlers.get(event)?.delete(handler)
        return socket
      }),
    }
    const target = { setEmotion: vi.fn(), resetEmotion: vi.fn() }
    const dispose = bindLive2DEmotionSocket(socket, target)
    return {
      socket,
      target,
      dispose,
      emit: (event: string, value?: unknown) => {
        for (const handler of handlers.get(event) ?? []) handler(value)
      },
    }
  }

  const frame = (taskId: string, extra: Record<string, unknown> = {}) => ({
    message_id: `message-${taskId}`,
    conversation_id: 'conversation',
    task_id: taskId,
    turn_id: taskId,
    ...extra,
  })

  it('accepts current expression and stream emotions, including a page opened mid-turn', () => {
    const { emit, target, dispose } = harness()
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'happy' }))
    expect(target.setEmotion).toHaveBeenLastCalledWith('happy')
    emit(Events.CHAT.AUDIO_STREAM_START, frame('one', { emotion: 'thinking' }))
    expect(target.setEmotion).toHaveBeenLastCalledWith('thinking')
    emit(Events.CHAT.CONTROL, frame('one', { signal: 'conversation-end' }))
    expect(target.resetEmotion).toHaveBeenCalledOnce()
    dispose()
  })

  it('rejects malformed identities, unknown emotions and unstarted tasks', () => {
    const { emit, target, dispose } = harness()
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'happy', turn_id: 'two' }))
    emit(Events.CHAT.EXPRESSION, { task_id: 'one', turn_id: 'one', emotion: 'happy' })
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'unknown' }))
    expect(target.setEmotion).not.toHaveBeenCalled()
    emit(Events.CHAT.CONTROL, frame('one', { signal: 'conversation-start' }))
    emit(Events.CHAT.EXPRESSION, frame('two', { emotion: 'happy' }))
    expect(target.setEmotion).not.toHaveBeenCalled()
    dispose()
  })

  it('retires replaced tasks and cannot revive them with delayed start or emotion events', () => {
    const { emit, target, dispose } = harness()
    emit(Events.CHAT.CONTROL, frame('one', { signal: 'conversation-start' }))
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'happy' }))
    emit(Events.CHAT.SENTENCE, frame('two', { seq: 0 }))
    emit(Events.CHAT.EXPRESSION, frame('two', { emotion: 'sad' }))
    target.setEmotion.mockClear()
    const resets = target.resetEmotion.mock.calls.length
    emit(Events.CHAT.CONTROL, frame('one', { signal: 'conversation-start' }))
    emit(Events.CHAT.SENTENCE, frame('one', { seq: 0 }))
    emit(Events.CHAT.AUDIO_STREAM_START, frame('one', { emotion: 'happy' }))
    emit(Events.CHAT.STOP_AUDIO, frame('one'))
    expect(target.setEmotion).not.toHaveBeenCalled()
    expect(target.resetEmotion).toHaveBeenCalledTimes(resets)
    emit(Events.CHAT.EXPRESSION, frame('two', { emotion: 'thinking' }))
    expect(target.setEmotion).toHaveBeenLastCalledWith('thinking')
    dispose()
  })

  it('resets only the stopped active task and retires it until a new turn starts', () => {
    const { emit, target, dispose } = harness()
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'happy' }))
    emit(Events.CHAT.STOP_AUDIO, frame('one'))
    target.setEmotion.mockClear()
    target.resetEmotion.mockClear()
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'happy' }))
    emit(Events.CHAT.SENTENCE, frame('one', { seq: 0 }))
    emit(Events.CHAT.EXPRESSION, frame('two', { emotion: 'happy' }))
    expect(target.setEmotion).not.toHaveBeenCalled()
    expect(target.resetEmotion).not.toHaveBeenCalled()
    emit(Events.CHAT.CONTROL, frame('two', { signal: 'conversation-start' }))
    emit(Events.CHAT.EXPRESSION, frame('two', { emotion: 'neutral' }))
    expect(target.setEmotion).toHaveBeenLastCalledWith('neutral')
    dispose()
  })

  it('clears on disconnect and requires a new turn before accepting emotions again', () => {
    const { emit, target, dispose } = harness()
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'happy' }))
    target.resetEmotion.mockClear()
    emit('disconnect')
    expect(target.resetEmotion).toHaveBeenCalledOnce()
    target.setEmotion.mockClear()
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'happy' }))
    emit(Events.CHAT.EXPRESSION, frame('two', { emotion: 'sad' }))
    expect(target.setEmotion).not.toHaveBeenCalled()
    emit(Events.CHAT.SENTENCE, frame('two', { seq: 0 }))
    emit(Events.CHAT.EXPRESSION, frame('two', { emotion: 'sad' }))
    expect(target.setEmotion).toHaveBeenLastCalledWith('sad')
    dispose()
  })

  it('unsubscribes every own handler once and ignores retained callbacks after disposal', () => {
    const { socket, target, emit, dispose } = harness()
    const listeners = vi.mocked(socket.on).mock.calls
    dispose()
    dispose()
    expect(socket.off).toHaveBeenCalledTimes(listeners.length)
    for (const [event, handler] of listeners) {
      expect(socket.off).toHaveBeenCalledWith(event, handler)
      handler(frame('one', { signal: 'conversation-start', seq: 0, emotion: 'happy' }))
    }
    emit(Events.CHAT.EXPRESSION, frame('one', { emotion: 'happy' }))
    expect(target.setEmotion).not.toHaveBeenCalled()
    expect(target.resetEmotion).not.toHaveBeenCalled()
  })
})
