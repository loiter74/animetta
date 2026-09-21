import * as PIXI from 'pixi.js'
import { Live2DModel, type Cubism4InternalModel } from 'pixi-live2d-display/cubism4'
import { resolveMouthParameterIndex } from './mouthParameter'
import {
  createLive2DPerformanceController,
  type Live2DPerformanceController,
} from './performanceController'
import { createCubismParameterAdapter, type CubismParameterModel } from './performanceProfile'
import type { Live2DPerformancePlanV1 } from './performanceContract'

export interface Live2DLayoutInput {
  screenWidth: number
  screenHeight: number
  baseWidth: number
  baseHeight: number
}
export interface Live2DRendererOptions {
  canvas: HTMLCanvasElement
  resizeTo: Window | HTMLElement
  idleVitality?: boolean
  layout?(input: Live2DLayoutInput): { scale: number; x: number; y: number }
  onState?(status: 'live' | 'error', error?: unknown): void
  onMouthApplied?(value: number, taskId: string): void
  beforeMouthApply?(): void
}
export type Live2DRendererAction =
  { type: 'expression'; name: string } | { type: 'motion'; group: string; index?: number }
export interface Live2DRenderer {
  ready: Promise<void>
  setMouth(value: number, taskId?: string): void
  applyAction(action: Live2DRendererAction): void
  armPerformance(plan: Live2DPerformancePlanV1, taskId: string): void
  startPerformance(taskId: string): void
  finishPerformance(taskId: string): void
  cancelPerformance(): void
  dispose(): void
}

const IDLE_VITALITY_PARAMETERS = [
  { name: 'ParamAngleX', factor: 2.3 },
  { name: 'ParamAngleY', factor: 2.3 },
  { name: 'ParamAngleZ', factor: 2.3 },
  { name: 'ParamBodyAngleX', factor: 2.6 },
  { name: 'ParamBodyAngleY', factor: 2.6 },
  { name: 'ParamBodyAngleZ', factor: 2.6 },
  { name: 'ParamBreath', factor: 2.4 },
] as const

const PARAMETER_LIMIT_KNEE_RATIO = 0.8

function softlyLimitParameter(
  value: number,
  defaultValue: number,
  minimum: number,
  maximum: number,
): number {
  const offset = value - defaultValue
  const limit = offset < 0 ? defaultValue - minimum : maximum - defaultValue
  if (!Number.isFinite(limit)) return value
  if (limit <= 0) return defaultValue

  const magnitude = Math.abs(offset)
  const knee = limit * PARAMETER_LIMIT_KNEE_RATIO
  if (magnitude <= knee) return value

  const remaining = limit - knee
  const softened = knee + remaining * (1 - Math.exp(-(magnitude - knee) / remaining))
  return defaultValue + Math.sign(offset) * softened
}

function amplifyIdleMotion(internalModel: Cubism4InternalModel): void {
  if (internalModel.motionManager.state.currentGroup !== 'Idle') return

  for (const { name, factor } of IDLE_VITALITY_PARAMETERS) {
    const index = internalModel.coreModel.getParameterIndex(name)
    if (index < 0) continue
    const current = internalModel.coreModel.getParameterValueByIndex(index)
    const defaultValue = internalModel.coreModel.getParameterDefaultValue?.(index) ?? 0
    const minimum =
      internalModel.coreModel.getParameterMinimumValue?.(index) ?? Number.NEGATIVE_INFINITY
    const maximum =
      internalModel.coreModel.getParameterMaximumValue?.(index) ?? Number.POSITIVE_INFINITY
    internalModel.coreModel.setParameterValueByIndex(
      index,
      softlyLimitParameter(
        defaultValue + (current - defaultValue) * factor,
        defaultValue,
        minimum,
        maximum,
      ),
    )
  }
}

async function configureIdleLoopMotions(internalModel: Cubism4InternalModel): Promise<void> {
  const { motionManager } = internalModel
  const idleGroup = motionManager.groups.idle
  const idleDefinitions = motionManager.definitions[idleGroup] ?? []
  await Promise.all(
    idleDefinitions.map(async (_definition, index) => {
      const motion = await motionManager.loadMotion(idleGroup, index)
      if (!motion) return
      motion.setIsLoop(true)
      motion.setIsLoopFadeIn(false)
    }),
  )
}

export function createLive2DRenderer(options: Live2DRendererOptions): Live2DRenderer {
  let disposed = false
  let app: PIXI.Application | null = null
  let model: Live2DModel | null = null
  let performanceController: Live2DPerformanceController | null = null
  let mouth = 0
  let mouthTaskId = ''
  const cleanups: (() => void)[] = []
  const cleanup = (): void => {
    for (const release of cleanups.splice(0).reverse()) release()
    performanceController?.destroy()
    performanceController = null
    model?.destroy()
    model = null
    app?.stop()
    app?.destroy(false, { children: false, texture: false, baseTexture: false })
    app = null
  }
  const ready = (async (): Promise<void> => {
    try {
      app = new PIXI.Application({
        view: options.canvas,
        resizeTo: options.resizeTo,
        backgroundAlpha: 0,
        autoStart: true,
      })
      const loaded = await Live2DModel.from('/live2d/mao/Mao.model3.json', { autoInteract: false })
      if (disposed) {
        loaded.destroy()
        return
      }
      // Keep ownership local until asynchronous motion loading finishes.
      try {
        await configureIdleLoopMotions(loaded.internalModel as Cubism4InternalModel)
      } catch (error) {
        loaded.destroy()
        throw error
      }
      if (disposed || !app) {
        loaded.destroy()
        return
      }
      model = loaded
      const internal = loaded.internalModel as Cubism4InternalModel
      const core = internal.coreModel as CubismParameterModel
      const mouthIndex = resolveMouthParameterIndex(internal.coreModel)
      const baseWidth = loaded.width / loaded.scale.x
      const baseHeight = loaded.height / loaded.scale.y
      performanceController = createLive2DPerformanceController(createCubismParameterAdapter(core))
      const applyMouth = (): void => {
        if (disposed) return
        performanceController?.tick()
        if (options.idleVitality) amplifyIdleMotion(internal)
        options.beforeMouthApply?.()
        if (mouthIndex >= 0) {
          internal.coreModel.setParameterValueByIndex(mouthIndex, mouth)
          if (mouth > 0.02) options.onMouthApplied?.(mouth, mouthTaskId)
        }
      }
      internal.on('beforeModelUpdate', applyMouth)
      cleanups.push(() => {
        internal.off('beforeModelUpdate', applyMouth)
        if (mouthIndex >= 0) internal.coreModel.setParameterValueByIndex(mouthIndex, 0)
      })
      const layout = (): void => {
        if (!app || disposed) return
        const input = {
          screenWidth: app.screen.width,
          screenHeight: app.screen.height,
          baseWidth,
          baseHeight,
        }
        const position = options.layout?.(input) ?? {
          scale:
            Math.min(
              (input.screenWidth * 0.88) / baseWidth,
              (input.screenHeight * 0.82) / baseHeight,
            ) * 1.8,
          x: input.screenWidth * 0.5,
          y: input.screenHeight * 0.8,
        }
        loaded.scale.set(position.scale)
        loaded.anchor.set(0.5, 0.5)
        loaded.position.set(position.x, position.y)
      }
      app.stage.addChild(loaded)
      layout()
      const renderer = app.renderer
      renderer.on('resize', layout)
      cleanups.push(() => renderer.off('resize', layout))
      options.onState?.('live')
    } catch (error) {
      cleanup()
      if (!disposed) options.onState?.('error', error)
    }
  })()
  return {
    ready,
    setMouth(value, taskId = '') {
      if (disposed) return
      mouth = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0
      if (taskId) mouthTaskId = taskId
    },
    applyAction(action) {
      if (disposed || !model) return
      if (action.type === 'expression') void model.expression(action.name)
      else void model.motion(action.group, action.index ?? 0)
    },
    armPerformance: (plan, taskId) => {
      performanceController?.arm(plan, taskId)
    },
    startPerformance: (taskId) => {
      performanceController?.start(taskId)
    },
    finishPerformance: (taskId) => {
      performanceController?.finish(taskId)
    },
    cancelPerformance: () => {
      performanceController?.cancel()
    },
    dispose() {
      if (disposed) return
      disposed = true
      cleanup()
    },
  }
}
