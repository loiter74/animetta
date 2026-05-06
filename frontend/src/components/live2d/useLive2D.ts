import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import type { Live2DAction, AudioWithExpression } from '@/types/live2d'
import { getSocket } from '@/composables/useSocket'

// ===== Model Configuration (edit these to change model) =====
export const MODEL_PATH = 'live2d/hiyori/Hiyori.model3.json'
// Position is computed as a fraction of canvas dimensions at load time,
// so the model appears at the same relative position on any screen size.
const POS_X_RATIO = 0.35   // 0.0 = left edge, 1.0 = right edge
const POS_Y_RATIO = 1.2    // >1.0 = below canvas bottom edge
const INITIAL_SCALE = 2.59

// Mouth parameter candidates (Cubism 3/4)
const MOUTH_PARAMS = ['ParamMouthOpenY', 'ParamMouthOpen', 'PARAM_MOUTH_OPEN']

interface ScaleStrategy {
  anchor: [number, number]
  yRatio: number
}

const STRATEGIES: Record<string, ScaleStrategy> = {
  fit: { anchor: [0.5, 0.5], yRatio: 0.5 },
  contain: { anchor: [0.5, 1.0], yRatio: 1.0 },
  cover: { anchor: [0.5, 0.5], yRatio: 0.5 }
}

export function useLive2D(canvasRef: Ref<HTMLCanvasElement | null>) {
  const isLoaded = ref(false)
  const isLoading = ref(false)
  const loadError = ref<string>('')
  const modelInfo = ref<Record<string, string> | null>(null)
  const isDragging = ref(false)

  let app: any = null // PIXI.Application
  let model: any = null // Live2DModel
  let container: HTMLElement | null = null

  // LipSync state
  let mouthValue = 0
  let targetMouth = 0
  let mouthParam: string | null = null
  let lipSyncCancel: (() => void) | null = null
  let _lipSyncRafActive = false  // when true, PIXI ticker lip sync is disabled

  // Scale state
  let strategy = 'fit'
  let userScale = 1.5
  let baseBounds: { width: number; height: number } | null = null

  // Drag state
  let dragStartX = 0
  let dragStartY = 0
  let modelStartX = 0
  let modelStartY = 0

  // Track canvas size ratio for proportional resize
  let lastCanvasW = 0
  let lastCanvasH = 0

  // Audio
  let currentAudio: HTMLAudioElement | null = null
  let currentBlobUrl: string | null = null

  // Timeline
  let timelinePlaying = false
  let timelineFrames: any[] = []
  let timelineDuration = 0
  let timelineStart = 0
  let timelineFrameIdx = 0
  let timelineRaf: number | null = null
  let currentParams = new Map<string, { currentValue: number; targetValue: number; startTime: number; duration: number; startValue: number }>()

  async function init(): Promise<void> {
    if (!canvasRef.value) return
    container = canvasRef.value.parentElement

    try {
      // Dynamic import: pixi.js is optional for the app
      const PIXI = await import('pixi.js')

      // Required: pixi-live2d-display references window.PIXI.Ticker internally
      ;(window as any).PIXI = PIXI

      app = new PIXI.Application({
        view: canvasRef.value,
        width: container?.clientWidth || 400,
        height: container?.clientHeight || 600,
        transparent: true,
        autoDensity: true,
        resolution: window.devicePixelRatio || 1,
        antialias: true,
        backgroundAlpha: 0,
        preserveDrawingBuffer: true
      })

      // LipSync ticker
      app.ticker.add(tickLipSync)
      setupSocketListeners()
      lastCanvasW = app.screen.width
      lastCanvasH = app.screen.height
    } catch (e) {
      loadError.value = 'pixi.js 初始化失败: ' + (e as Error).message
      isLoading.value = false
    }
  }

  function setupSocketListeners(): void {
    const socket = getSocket()
    if (!socket) return

    socket.on('live2d.action', (data: unknown) => {
      executeAction(data as Live2DAction)
    })

    socket.on('audio_with_expression', (data: unknown) => {
      const d = data as any
      if (d.use_parameter_mapping && d.expressions?.frames) {
        playParameterTimeline(d)
      } else {
        playAudio(d)
      }
    })

    socket.on('stop_audio', () => {
      stopAudio()
    })
  }

  function teardownSocketListeners(): void {
    const socket = getSocket()
    if (!socket) return
    socket.off('live2d.action')
    socket.off('audio_with_expression')
    socket.off('stop_audio')
  }

  // ===== Model =====

  async function loadModel(modelPath: string): Promise<void> {
    isLoading.value = true
    loadError.value = ''

    try {
      unloadModel()

      // Dynamic import: Live2D is optional, app works without it
      const { Live2DModel } = await import('pixi-live2d-display/cubism4')

      model = await Live2DModel.from(modelPath)
      // Disable idle group to prevent random idle motion cycling,
      // then play motion[0] (Hiyori_m01: gentle head sway with ParamAngleX)
      // on loop for a natural subtle swaying effect.
      try {
        model.internalModel?.motionManager?.stopAllMotions()
        if (model.internalModel?.motionManager?.groups) {
          model.internalModel.motionManager.groups.idle = '_none'
        }
      } catch {}
      // Play the gentlest motion on loop (m01 has natural head sway + breathing)
      try { model.motion("Idle", 0) } catch {}
      model.anchor.set(0.5, 0.5)
      // Will be overridden after applyScale below to user's preferred position
      model.interactive = true

      app.stage.addChild(model)

      // Wait for bounds to be available
      await new Promise<void>((resolve) => {
        const check = () => {
          const b = model.getBounds()
          if (b?.width > 0) return resolve()
          requestAnimationFrame(check)
        }
        check()
      })

      // Cache initial bounds (before any scaling) as the stable reference
      const initialBounds = model.getBounds()
      baseBounds = { width: initialBounds.width, height: initialBounds.height }

      applyScale()
      // Position model relative to canvas size
      model.x = app.screen.width * POS_X_RATIO
      model.y = app.screen.height * POS_Y_RATIO
      userScale = INITIAL_SCALE
      applyScale()
      isLoaded.value = true
      isLoading.value = false
      updateModelInfo()
    } catch (err: any) {
      loadError.value = err.message
      isLoading.value = false
    }
  }

  function unloadModel(): void {
    if (model) {
      app?.stage.removeChild(model)
      model.destroy()
      model = null
      mouthParam = null
      isLoaded.value = false
    }
  }

  // ===== Scale =====

  // ===== Scale =====

  function applyScale(): void {
    if (!model || !app || !baseBounds) return
    const canvas = { width: app.screen.width, height: app.screen.height }
    // Use cached initial bounds as stable reference — NEVER real-time getBounds()
    // because getBounds() changes as scale changes, creating a feedback loop.
    const b = baseBounds

    const scales: Record<string, number> = {
      fit: Math.min(canvas.width / b.width, canvas.height / b.height),
      contain: canvas.height / b.height,
      cover: Math.max(canvas.width / b.width, canvas.height / b.height)
    }

    model.scale.set((scales[strategy] || scales.fit) * userScale)
    console.log(`[Live2D] scale=${userScale.toFixed(2)}x pos=(${model.x.toFixed(0)},${model.y.toFixed(0)})`)
    // NOTE: Do NOT reset model.x/model.y/anchor here — position is
    // managed by drag interaction. Only centerModel() changes position.
  }

  /**
   * Handle container resize (e.g. DevTools open/close).
   * Resizes renderer and adjusts model position proportionally.
   * Does NOT re-center — preserves user's drag offset.
   * Does NOT change scale.
   */
  function handleResize(): void {
    if (!app || !container) return
    const oldW = lastCanvasW || app.screen.width
    const oldH = lastCanvasH || app.screen.height
    app.renderer.resize(container.clientWidth, container.clientHeight)
    if (model) {
      model.x *= app.screen.width / oldW
      model.y *= app.screen.height / oldH
    }
    lastCanvasW = app.screen.width
    lastCanvasH = app.screen.height
  }

  /** Center model in the current canvas. Preserves userScale. */
  function centerModel(): void {
    if (!model || !app) return
    const cfg = STRATEGIES[strategy]
    model.x = app.screen.width / 2
    model.y = cfg.yRatio === 1.0 ? app.screen.height : app.screen.height / 2
    updateModelInfo()
  }

  // ===== Drag =====

  function startDrag(clientX: number, clientY: number): void {
    if (!model) return
    isDragging.value = true
    dragStartX = clientX
    dragStartY = clientY
    modelStartX = model.x
    modelStartY = model.y
  }

  function onDrag(clientX: number, clientY: number): void {
    if (!isDragging.value || !model) return
    const dx = clientX - dragStartX
    const dy = clientY - dragStartY
    model.x = modelStartX + dx
    model.y = modelStartY + dy
    updateModelInfo()
  }

  function stopDrag(): void {
    if (!isDragging.value) return
    isDragging.value = false
  }

  // ===== Expression =====

  function setExpression(name: string): void {
    if (!model?.internalModel?.motionManager?.expressionNames) return
    const idx = model.internalModel.motionManager.expressionNames.indexOf(name)
    if (idx >= 0) model.expression(idx)
  }

  function playMotion(group: string, index: number): void {
    model?.motion?.(group, index)
  }

  // ===== LipSync =====

  function setMouthTarget(value: number): void {
    targetMouth = Math.max(0, Math.min(1, value))
  }

  function tickLipSync(): void {
    // RAF-based lip sync takes priority over PIXI ticker
    if (_lipSyncRafActive) return
    if (!model) return

    const delta = Math.abs(targetMouth - mouthValue)
    const factor = 0.5 + 0.4 * Math.min(delta / 0.3, 1.0)
    mouthValue += (targetMouth - mouthValue) * factor

    if (!mouthParam) {
      for (const name of MOUTH_PARAMS) {
        const idx = model.internalModel?.coreModel?.getParameterIndex(name)
        if (idx >= 0) { mouthParam = name; break }
      }
    }

    if (mouthParam) {
      const idx = model.internalModel.coreModel.getParameterIndex(mouthParam)
      if (idx >= 0) model.internalModel.coreModel.setParameterValueByIndex(idx, mouthValue)
    }
  }

  function startLipSync(audio: HTMLAudioElement, volumes: number[]): void {
    stopLipSync()
    _lipSyncRafActive = true

    // Stop idle motion that may override mouth parameters via motionManager
    try {
      model?.internalModel?.motionManager?.stopAllMotions()
    } catch {}
    const intervalMs = 20
    let lastIndex = -1
    let hasStarted = false
    let preRollCount = 0
    let preRollTarget = 3
    let lipSyncMouth = 0
    let lipSyncTarget = 0

    // Direct parameter setter — runs every RAF frame, NOT through the PIXI
    // ticker, so it wins over any motion-driven mouth keyframes.
    function setLipSyncParam(value: number) {
      lipSyncTarget = Math.max(0, Math.min(1, value))
      // Smooth interpolation
      const delta = Math.abs(lipSyncTarget - lipSyncMouth)
      const factor = 0.5 + 0.4 * Math.min(delta / 0.3, 1.0)
      lipSyncMouth += (lipSyncTarget - lipSyncMouth) * factor
      if (!mouthParam) {
        for (const name of MOUTH_PARAMS) {
          const idx = model?.internalModel?.coreModel?.getParameterIndex(name)
          if (idx !== undefined && idx >= 0) { mouthParam = name; break }
        }
      }
      if (mouthParam && model?.internalModel?.coreModel) {
        const idx = model.internalModel.coreModel.getParameterIndex(mouthParam)
        if (idx >= 0) model.internalModel.coreModel.setParameterValueByIndex(idx, lipSyncMouth)
      }
    }

    const tick = () => {
      if (audio.ended || (hasStarted && audio.paused)) {
        setLipSyncParam(0)
        return
      }

      if (!hasStarted) {
        if (audio.paused) {
          if (preRollCount < preRollTarget && preRollCount < volumes.length) {
            setLipSyncParam(volumes[preRollCount])
            preRollCount++
          }
          requestAnimationFrame(tick)
          return
        }
        hasStarted = true
      }

      const rawIndex = Math.floor((audio.currentTime * 1000) / intervalMs)
      const index = rawIndex + preRollCount
      if (index !== lastIndex) {
        setLipSyncParam(index < volumes.length ? volumes[index] : 0)
        lastIndex = index
      } else {
        // Keep smoothing toward current target even on same index
        setLipSyncParam(lipSyncTarget)
      }
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)

    lipSyncCancel = () => { _lipSyncRafActive = false; setLipSyncParam(0) }
  }

  function stopLipSync(): void {
    lipSyncCancel?.()
    lipSyncCancel = null
    _lipSyncRafActive = false
    setMouthTarget(0)
    // Restart idle motion for head sway now that lip sync is done
    try { model?.motion?.("Idle", 0) } catch {}
  }

  // ===== Audio =====

  function playAudio(data: { audio_data?: string; format?: string; volumes?: number[]; expressions?: any; return_to_idle?: boolean }): void {
    if (!data?.audio_data) return
    cleanupAudio()

    const binary = atob(data.audio_data)
    const buffer = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) buffer[i] = binary.charCodeAt(i)

    const blob = new Blob([buffer], { type: `audio/${data.format || 'mp3'}` })
    const url = URL.createObjectURL(blob)
    currentBlobUrl = url
    const audio = new Audio(url)
    currentAudio = audio

    if (data.volumes?.length) startLipSync(audio, data.volumes)

    audio.onended = () => {
      stopLipSync()
      if (data.return_to_idle) setExpression('idle')
      cleanupAudio()
    }

    audio.play().catch(() => cleanupAudio())
  }

  function stopAudio(): void {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio.currentTime = 0
    }
    stopLipSync()
    cleanupAudio()
  }

  function cleanupAudio(): void {
    if (currentAudio) { currentAudio.onended = null; currentAudio = null }
    if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null }
  }

  // ===== Timeline =====

  function playParameterTimeline(data: { audio_data?: string; format?: string; volumes?: number[]; expressions: any; return_to_idle?: boolean }): void {
    playAudio(data)
    if (data.expressions?.frames) {
      setTimeout(() => {
        timelineFrames = data.expressions.frames
        timelineDuration = data.expressions.total_duration || 0
        timelineStart = performance.now() / 1000
        timelineFrameIdx = 0
        timelinePlaying = true
        currentParams.clear()
        tickTimeline()
      }, 100)
    }
  }

  function tickTimeline(): void {
    if (!timelinePlaying) return
    const currentTime = performance.now() / 1000 - timelineStart

    if (currentTime >= timelineDuration) {
      timelinePlaying = false
      return
    }

    // Process frames
    while (timelineFrameIdx < timelineFrames.length && timelineFrames[timelineFrameIdx].timestamp <= currentTime) {
      const frame = timelineFrames[timelineFrameIdx]
      for (const param of frame.parameters) {
        currentParams.set(param.name, {
          targetValue: param.value,
          startTime: currentTime,
          duration: param.duration,
          startValue: currentParams.get(param.name)?.currentValue ?? param.value,
          currentValue: currentParams.get(param.name)?.currentValue ?? param.value
        })
      }
      timelineFrameIdx++
    }

    // Interpolate and apply
    for (const [name, state] of currentParams) {
      const progress = Math.min((currentTime - state.startTime) / state.duration, 1.0)
      const eased = progress < 0.5 ? 4 * progress ** 3 : 1 - ((-2 * progress + 2) ** 3) / 2
      state.currentValue = state.startValue + (state.targetValue - state.startValue) * eased
      setParam(name, state.currentValue)
      if (progress >= 1.0) currentParams.delete(name)
    }

    timelineRaf = requestAnimationFrame(tickTimeline)
  }

  function setParam(name: string, value: number): void {
    if (!model?.internalModel?.coreModel) return
    const idx = model.internalModel.coreModel.getParameterIndex(name)
    if (idx >= 0) model.internalModel.coreModel.setParameterValueByIndex(idx, value)
  }

  // ===== Actions =====

  function executeAction(action: Live2DAction): void {
    switch (action.type) {
      case 'expression': setExpression(action.name!); break
      case 'motion': playMotion(action.group!, action.index!); break
      case 'param': setParam(action.name!, action.value!); break
      case 'sequence':
        let delay = 0
        for (const sub of (action as any).actions ?? []) {
          if (sub.type === 'wait') { delay += sub.ms || 0 }
          else { setTimeout(() => executeAction(sub), delay) }
        }
        break
    }
  }

  function updateModelInfo(): void {
    if (!model || !app) { modelInfo.value = null; return }
    modelInfo.value = {
      strategy,
      userScale: userScale.toFixed(2),
      position: `(${model.x.toFixed(0)}, ${model.y.toFixed(0)})`,
      canvas: `${app.screen.width}x${app.screen.height}`
    }
  }

  function destroy(): void {
    stopAudio()
    timelinePlaying = false
    teardownSocketListeners()
    if (timelineRaf) cancelAnimationFrame(timelineRaf)
    if (app) { app.ticker.remove(tickLipSync); unloadModel(); app.destroy(true); app = null }
    window.removeEventListener('resize', handleResize)
  }

  // Auto-cleanup
  onMounted(() => {
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    destroy()
  })

  return {
    isLoaded,
    isLoading,
    loadError,
    modelInfo,
    isDragging,
    init,
    loadModel,
    handleResize,
    setExpression,
    playMotion,
    setMouthTarget,
    executeAction,
    stopAudio,
    startDrag,
    onDrag,
    stopDrag,
    /** Scroll-wheel zoom. Positive delta = zoom in, negative = zoom out. Range 0.05x – 10x. */
    zoom(delta: number) {
      userScale = Math.max(0.05, Math.min(10.0, userScale * Math.exp(delta)))
      applyScale()
      updateModelInfo()
    },
    /** Reset to user's preferred initial position and scale */
    resetView() {
      userScale = INITIAL_SCALE
      applyScale()
      if (model && app) {
        model.x = app.screen.width * POS_X_RATIO
        model.y = app.screen.height * POS_Y_RATIO
      }
      updateModelInfo()
    },
    setScaleStrategy(s: string) { if (STRATEGIES[s]) { strategy = s; applyScale(); updateModelInfo() } },
    // Mouse focus (eye/head tracking)
    focus(x: number, y: number) {
      if (!model) return
      model.focus(x, y)
    },
    destroy
  }
}
