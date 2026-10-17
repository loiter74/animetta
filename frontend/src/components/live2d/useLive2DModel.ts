import type { Cubism4InternalModel, Live2DModel } from 'pixi-live2d-display/cubism4'
import { getApp } from './usePixiApp'
import { isLoaded, isLoading, loadError, updateModelInfo } from './useInteraction'
import { DEFAULT_LIVE2D_MODEL_PROFILE } from '@/shared/live2d/modelProfiles'

// ===== Default avatar selected at the application boundary =====

export const MODEL_PATH = DEFAULT_LIVE2D_MODEL_PROFILE.modelUrl
// The Vue surface keeps its existing composition independently of model defaults.
const INITIAL_POSITION = { x: 800, y: 1300 }
const INITIAL_SCALE = 2.59

export { INITIAL_SCALE }

export interface ScaleStrategy {
  anchor: [number, number]
  yRatio: number
}

export const STRATEGIES: Record<string, ScaleStrategy> = {
  fit: { anchor: [0.5, 0.5], yRatio: 0.5 },
  contain: { anchor: [0.5, 1.0], yRatio: 1.0 },
  cover: { anchor: [0.5, 0.5], yRatio: 0.5 },
}

// ===== Model State =====

let model: Live2DModel<Cubism4InternalModel> | null = null
let baseBounds: { width: number; height: number } | null = null
let userScale = 1.5
let strategy = 'fit'

export function getModel(): Live2DModel<Cubism4InternalModel> | null {
  return model
}
export function getUserScale(): number {
  return userScale
}
export function getStrategy(): string {
  return strategy
}
export function setUserScale(s: number): void {
  userScale = s
}
export function setStrategy(s: string): void {
  if (STRATEGIES[s]) strategy = s
}

// ===== Model Loading =====

export function unloadModel(): void {
  const app = getApp()
  if (model) {
    app?.stage.removeChild(model)
    model.destroy()
    model = null
    isLoaded.value = false
  }
}

export async function loadModel(modelPath: string): Promise<void> {
  const app = getApp()
  if (!app) {
    loadError.value = 'PixiJS 未初始化，请刷新页面重试'
    isLoading.value = false
    return
  }
  isLoading.value = true
  loadError.value = ''

  // 30-second timeout for the entire loading process
  const LOAD_TIMEOUT_MS = 30_000

  try {
    unloadModel()

    // Dynamic import: Live2D is optional, app works without it
    const { Live2DModel } = await import('pixi-live2d-display/cubism4')

    // Wrap model creation with timeout
    model = (await Promise.race([
      Live2DModel.from(modelPath),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('模型加载超时（30秒）')), LOAD_TIMEOUT_MS),
      ),
    ])) as Live2DModel<Cubism4InternalModel>

    // Reset scheduler state left by a previously loaded model.
    try {
      model.internalModel?.motionManager?.stopAllMotions()
    } catch {}
    model.anchor.set(0.5, 0.5)
    // Will be overridden after applyScale below to user's preferred position
    model.interactive = true

    app.stage.addChild(model)
    const loadedModel = model

    // Wait for bounds to be available (with timeout to prevent infinite loop)
    await Promise.race([
      new Promise<void>((resolve) => {
        const check = () => {
          const b = loadedModel.getBounds()
          if (b?.width > 0) return resolve()
          requestAnimationFrame(check)
        }
        check()
      }),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('模型边界计算超时')), 10_000),
      ),
    ])

    // Cache initial bounds (before any scaling) as the stable reference
    const initialBounds = loadedModel.getBounds()
    baseBounds = { width: initialBounds.width, height: initialBounds.height }

    userScale = INITIAL_SCALE
    applyScale()
    centerModel()
    isLoaded.value = true
    isLoading.value = false
  } catch (err: unknown) {
    loadError.value = err instanceof Error ? err.message : '模型加载失败'
    isLoading.value = false
  }
}

// ===== Scale =====

/**
 * Apply current scale (strategy × userScale) using cached baseBounds.
 * NEVER use real-time getBounds() here — creates a feedback loop.
 */
export function applyScale(): void {
  const app = getApp()
  if (!model || !app || !baseBounds) return
  const canvas = { width: app.screen.width, height: app.screen.height }
  // Use cached initial bounds as stable reference — NEVER real-time getBounds()
  // because getBounds() changes as scale changes, creating a feedback loop.
  const b = baseBounds

  const scales: Record<string, number> = {
    fit: Math.min(canvas.width / b.width, canvas.height / b.height),
    contain: canvas.height / b.height,
    cover: Math.max(canvas.width / b.width, canvas.height / b.height),
  }

  model.scale.set((scales[strategy] || scales.fit) * userScale)
  // NOTE: Do NOT reset model.x/model.y/anchor here — position is
  // managed by drag interaction. Only centerModel() changes position.
}

// ===== Positioning =====

/** Center model in the current canvas. Preserves userScale. */
export function centerModel(): void {
  const app = getApp()
  if (!model || !app) return
  model.x = INITIAL_POSITION.x
  model.y = INITIAL_POSITION.y
  updateModelInfo()
}

// ===== Expression & Motion =====

export function setExpression(name: string): void {
  if (!model) return
  const manager = model.internalModel.motionManager as typeof model.internalModel.motionManager & {
    expressionNames?: string[]
  }
  if (!manager.expressionNames) return
  const idx = manager.expressionNames.indexOf(name)
  if (idx >= 0) model.expression(idx)
}

export function playMotion(group: string, index: number): void {
  model?.motion?.(group, index)
}

export function setClampedParameter(name: string, value: number): void {
  const coreModel = model?.internalModel?.coreModel
  if (!coreModel) return
  const index = coreModel.getParameterIndex(name)
  if (index < 0) return
  const bounded = coreModel as typeof coreModel & {
    getParameterMinimumValue?: (parameterIndex: number) => number
    getParameterMaximumValue?: (parameterIndex: number) => number
  }
  const minimum = bounded.getParameterMinimumValue?.(index) ?? -1
  const maximum = bounded.getParameterMaximumValue?.(index) ?? 1
  coreModel.setParameterValueByIndex(index, Math.max(minimum, Math.min(maximum, value)))
}

export function getParameterValue(name: string): number {
  const coreModel = model?.internalModel?.coreModel
  if (!coreModel) return 0
  const index = coreModel.getParameterIndex(name)
  return index < 0 ? 0 : coreModel.getParameterValueByIndex(index)
}

// ===== Retry =====

/** Retry loading the default model after a failure */
export async function retryLoad(): Promise<void> {
  loadError.value = ''
  isLoaded.value = false
  await loadModel(MODEL_PATH)
}
