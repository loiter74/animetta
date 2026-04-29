import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import type { Live2DAction, AudioWithExpression } from '@/types/live2d'

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

  let app: any = null // PIXI.Application
  let model: any = null // Live2DModel
  let container: HTMLElement | null = null

  // LipSync state
  let mouthValue = 0
  let targetMouth = 0
  let mouthParam: string | null = null
  let lipSyncCancel: (() => void) | null = null

  // Scale state
  let strategy = 'contain'
  let userScale = 1.0

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

  function init(): void {
    if (!canvasRef.value) return
    container = canvasRef.value.parentElement

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const PIXI = require('pixi.js')

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
    setupIpcListeners()
  }

  function setupIpcListeners(): void {
    if (!window.electronAPI) return

    window.electronAPI.live2d?.onAction?.((data) => {
      executeAction(data as Live2DAction)
    })

    window.electronAPI.live2d?.onAudioWithExpression?.((data) => {
      const d = data as any
      if (d.use_parameter_mapping && d.expressions?.frames) {
        playParameterTimeline(d)
      } else {
        playAudio(d)
      }
    })

    window.electronAPI.live2d?.onAudioStream?.((data) => {
      const d = data as any
      if (d.volume !== undefined) {
        setMouthTarget(d.volume)
      }
    })

    window.electronAPI.live2d?.onStopAudio?.(() => {
      stopAudio()
    })
  }

  // ===== Model =====

  async function loadModel(modelPath: string): Promise<void> {
    isLoading.value = true
    loadError.value = ''

    try {
      unloadModel()

      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { Live2DModel } = require('pixi-live2d-display')

      model = await Live2DModel.from(modelPath)
      model.anchor.set(0.5, 0.5)
      model.x = app.screen.width / 2
      model.y = app.screen.height / 2
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

  function applyScale(): void {
    if (!model || !app) return
    const canvas = { width: app.screen.width, height: app.screen.height }
    const bounds = model.getBounds()
    if (!bounds?.width) return

    const scales: Record<string, number> = {
      fit: Math.min(canvas.width / bounds.width, canvas.height / bounds.height),
      contain: canvas.height / bounds.height,
      cover: Math.max(canvas.width / bounds.width, canvas.height / bounds.height)
    }

    const scale = (scales[strategy] || scales.fit) * userScale
    model.scale.set(scale)

    const cfg = STRATEGIES[strategy]
    model.anchor.set(cfg.anchor[0], cfg.anchor[1])
    model.x = canvas.width / 2
    model.y = cfg.yRatio === 1.0 ? canvas.height : canvas.height / 2
  }

  function handleResize(): void {
    if (!app || !container) return
    app.renderer.resize(container.clientWidth, container.clientHeight)
    applyScale()
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
    const intervalMs = 20
    let lastIndex = -1
    let hasStarted = false

    const tick = () => {
      if (audio.ended || (hasStarted && audio.paused)) {
        setMouthTarget(0)
        return
      }
      if (!hasStarted) {
        if (audio.paused) { requestAnimationFrame(tick); return }
        hasStarted = true
      }

      const index = Math.floor((audio.currentTime * 1000) / intervalMs)
      if (index !== lastIndex) {
        setMouthTarget(index < volumes.length ? volumes[index] : 0)
        lastIndex = index
      }
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)

    lipSyncCancel = () => setMouthTarget(0)
  }

  function stopLipSync(): void {
    lipSyncCancel?.()
    lipSyncCancel = null
    setMouthTarget(0)
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
    init,
    loadModel,
    handleResize,
    setExpression,
    playMotion,
    setMouthTarget,
    executeAction,
    stopAudio,
    zoom(delta: number) { userScale = Math.max(0.1, Math.min(3.0, userScale + delta * 0.1)); applyScale() },
    resetScale() { userScale = 1.0; applyScale() },
    setScaleStrategy(s: string) { if (STRATEGIES[s]) { strategy = s; applyScale() } },
    destroy
  }
}
