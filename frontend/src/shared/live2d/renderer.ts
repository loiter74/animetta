import * as PIXI from 'pixi.js'
import { Live2DModel, type Cubism4InternalModel } from 'pixi-live2d-display/cubism4'
import { resolveMouthParameterIndex } from './mouthParameter'
import { createFixedStepPhysics } from './fixedStepPhysics'
import {
  createLive2DPerformanceController,
  type Live2DPerformanceController,
} from './performanceController'
import { createCubismParameterAdapter, type CubismParameterModel } from './performanceProfile'
import type { Live2DPerformancePlanV1 } from './performanceContract'
import type { Live2DIdleVitalityParameter, Live2DModelProfile } from './modelProfile'
import {
  LIVE2D_UHD_SIZE,
  responsiveRenderResolution,
  type Live2DRenderOutput,
} from './renderResolution'

export interface Live2DLayoutInput {
  screenWidth: number
  screenHeight: number
  baseWidth: number
  baseHeight: number
}
export interface Live2DRendererOptions {
  canvas: HTMLCanvasElement
  resizeTo: Window | HTMLElement
  profile: Live2DModelProfile
  /** Fixed UHD pixels with a center-cropped CSS preview, or a responsive high-DPI canvas. */
  output?: Live2DRenderOutput
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
  setZoom(value: number): void
  setMouth(value: number, taskId?: string): void
  applyAction(action: Live2DRendererAction): void
  armPerformance(plan: Live2DPerformancePlanV1, taskId: string): void
  startPerformance(taskId: string): void
  finishPerformance(taskId: string): void
  cancelPerformance(): void
  dispose(): void
}

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

function amplifyIdleMotion(
  internalModel: Cubism4InternalModel,
  parameters: readonly Live2DIdleVitalityParameter[],
): void {
  const { motionManager } = internalModel
  if (motionManager.state.currentGroup !== motionManager.groups.idle) return

  for (const { name, factor } of parameters) {
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
  const { profile } = options
  const output = options.output ?? 'responsive'
  const previousObjectFit = options.canvas.style.objectFit
  options.canvas.dataset.renderOutput = output
  options.canvas.dataset.renderTarget =
    output === '4k' ? `${LIVE2D_UHD_SIZE.width}x${LIVE2D_UHD_SIZE.height}` : 'viewport'
  options.canvas.dataset.renderState = 'loading'
  let disposed = false
  let app: PIXI.Application | null = null
  let model: Live2DModel | null = null
  let performanceController: Live2DPerformanceController | null = null
  let mouth = 0
  let mouthRest = 0
  let mouthTaskId = ''
  let zoom = 1
  let applyLayout: (() => void) | undefined
  const cleanups: (() => void)[] = []
  const cleanup = (): void => {
    for (const release of cleanups.splice(0).reverse()) release()
    performanceController?.destroy()
    performanceController = null
    model?.destroy()
    model = null
    applyLayout = undefined
    app?.stop()
    app?.destroy(false, { children: false, texture: false, baseTexture: false })
    app = null
    options.canvas.style.objectFit = previousObjectFit
  }
  const ready = (async (): Promise<void> => {
    try {
      const viewport = options.resizeTo
      const width = 'innerWidth' in viewport ? viewport.innerWidth : viewport.clientWidth
      const height = 'innerHeight' in viewport ? viewport.innerHeight : viewport.clientHeight
      app = new PIXI.Application({
        view: options.canvas,
        ...(output === '4k'
          ? { ...LIVE2D_UHD_SIZE, resolution: 1 }
          : {
              resizeTo: options.resizeTo,
              resolution: responsiveRenderResolution(width, height, window.devicePixelRatio),
              autoDensity: true,
            }),
        backgroundAlpha: 0,
        autoStart: true,
      })
      if (output === '4k') {
        // Narrow embedded windows crop the sides of the preview, preserving the
        // avatar's height. A 16:9 output shows the complete 3840×2160 image.
        options.canvas.style.objectFit = 'cover'
        const gl = (app.renderer as PIXI.Renderer).gl
        const maximumSize = gl.getParameter(gl.MAX_RENDERBUFFER_SIZE) as number
        const viewportLimits = gl.getParameter(gl.MAX_VIEWPORT_DIMS) as Int32Array
        if (
          maximumSize < LIVE2D_UHD_SIZE.width ||
          viewportLimits[0] < LIVE2D_UHD_SIZE.width ||
          viewportLimits[1] < LIVE2D_UHD_SIZE.height ||
          options.canvas.width !== LIVE2D_UHD_SIZE.width ||
          options.canvas.height !== LIVE2D_UHD_SIZE.height
        ) {
          throw new Error('This graphics context cannot provide a 3840×2160 Live2D output')
        }
      }
      const loaded = await Live2DModel.from(profile.modelUrl, { autoInteract: false })
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
      if (profile.automaticBreathing === false) internal.breath.setParameters([])
      if (profile.fixedStepPhysics) {
        if (!internal.physics) throw new Error('Authored Live2D physics could not be loaded')
        internal.physics.evaluate = createFixedStepPhysics(internal.physics, internal.coreModel)
      }
      const core = internal.coreModel as CubismParameterModel
      const mouthIndex = resolveMouthParameterIndex(internal.coreModel, profile.mouthParameters)
      const baseWidth = loaded.width / loaded.scale.x
      const baseHeight = loaded.height / loaded.scale.y
      performanceController = createLive2DPerformanceController(
        createCubismParameterAdapter(core),
        {
          profile: profile.performance,
        },
      )
      const applyMouth = (): void => {
        if (disposed) return
        performanceController?.tick()
        if (options.idleVitality && profile.idleVitality) {
          amplifyIdleMotion(internal, profile.idleVitality)
        }
        options.beforeMouthApply?.()
        if (mouthIndex >= 0) {
          const opening = mouthRest + (1 - mouthRest) * mouth
          internal.coreModel.setParameterValueByIndex(mouthIndex, opening)
          if (mouth > 0.02) options.onMouthApplied?.(opening, mouthTaskId)
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
            ) * profile.framing.scale,
          x: input.screenWidth * profile.framing.x,
          y: input.screenHeight * profile.framing.y,
        }
        loaded.scale.set(position.scale * zoom)
        loaded.anchor.set(0.5, 0.5)
        // Keep the fitted top edge visible when zooming in to inspect the face.
        loaded.position.set(position.x, position.y + (baseHeight * position.scale * (zoom - 1)) / 2)
      }
      applyLayout = layout
      app.stage.addChild(loaded)
      layout()
      const renderer = app.renderer
      const resize = (): void => {
        if (output === 'responsive' && app) {
          const resolution = responsiveRenderResolution(
            app.screen.width,
            app.screen.height,
            window.devicePixelRatio,
          )
          if (renderer.resolution !== resolution) {
            renderer.resolution = resolution
            renderer.resize(app.screen.width, app.screen.height)
            return
          }
        }
        layout()
      }
      renderer.on('resize', resize)
      cleanups.push(() => renderer.off('resize', resize))
      if (output === 'responsive' && !('innerWidth' in viewport)) {
        // Pixi's resize plugin listens to the window, while embedded panels
        // can change size independently of it.
        const observer = new ResizeObserver(() => {
          if (!disposed) app?.resize()
        })
        observer.observe(viewport)
        cleanups.push(() => observer.disconnect())
      }
      options.canvas.dataset.renderState = 'live'
      options.onState?.('live')
    } catch (error) {
      cleanup()
      options.canvas.dataset.renderState = 'error'
      if (!disposed) options.onState?.('error', error)
    }
  })()
  return {
    ready,
    setZoom(value) {
      if (disposed) return
      zoom = Number.isFinite(value) ? Math.max(1, Math.min(3, value)) : 1
      applyLayout?.()
    },
    setMouth(value, taskId = '') {
      if (disposed) return
      mouth = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0
      if (taskId) mouthTaskId = taskId
    },
    applyAction(action) {
      if (disposed || !model) return
      if (action.type === 'expression') {
        if (profile.expressions && !Object.hasOwn(profile.expressions, action.name)) return
        mouthRest = Math.max(0, Math.min(1, profile.expressions?.[action.name]?.mouthRest ?? 0))
        void model.expression(action.name)
      } else void model.motion(action.group, action.index ?? 0)
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
      options.canvas.dataset.renderState = 'disposed'
    },
  }
}
