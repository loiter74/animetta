import { Events } from '@/shared/contracts/socket-events'
import type { Live2DAction } from '@/types/live2d'
import type { LiveSocket } from '@/shared/transport/liveSocket'
import type { PublicLive2DCue } from '@/shared/broadcast/publicActivity'
import type { Live2DPerformancePlanV1 } from '@/shared/contracts/socket-events'
import { DEFAULT_LIVE2D_PERFORMANCE_PLAN } from '@/shared/live2d/performanceController'
import { createLive2DRenderer } from '@/shared/live2d/renderer'
import type { Live2DModelProfile } from '@/shared/live2d/modelProfile'
import { DEFAULT_LIVE2D_MODEL_PROFILE } from '@/shared/live2d/modelProfiles'
import { createLive2DExpressionController } from '@/shared/live2d/expressionController'
import { bindLive2DEmotionSocket } from '@/shared/live2d/emotionSocket'
import type { Live2DRenderOutput } from '@/shared/live2d/renderResolution'
import { createReviewVolumeTimelineLipSync } from './review-lip-sync'

const PUBLIC_CUE_EMOTIONS = {
  planning: 'thinking',
  observing: 'thinking',
  committed: 'confident',
  acting: 'focused',
  checking: 'thinking',
  recovering: 'alert',
  finished: 'relieved',
} as const

export interface Live2DStage {
  ready: Promise<void>
  setZoom(value: number): void
  setMouth(value: number, taskId?: string): void
  setEmotion(emotion: string): void
  setExpression(name: string | null): void
  playReviewAudio(
    notification: HTMLElement,
    volumes: readonly number[],
    performance?: Live2DPerformancePlanV1,
  ): void
  cancelReviewAudio(): void
  applyPublicCue(cue: PublicLive2DCue): void
  dispose(): void
}

export interface Live2DStageOptions {
  readonly output?: Live2DRenderOutput
  readonly profile?: Live2DModelProfile
  readonly resizeTo?: Window | HTMLElement
  readonly idleVitality?: boolean
}

export function createLive2DStage(
  socket: LiveSocket,
  options: Live2DStageOptions = {},
): Live2DStage {
  const canvas = document.getElementById('live2dCanvas')
  const state = document.getElementById('modelStatus')
  const audioStatus = document.getElementById('audioStatus')
  if (!(canvas instanceof HTMLCanvasElement) || !state) {
    return {
      ready: Promise.resolve(),
      setZoom() {},
      setMouth() {},
      setEmotion() {},
      setExpression() {},
      playReviewAudio() {},
      cancelReviewAudio() {},
      applyPublicCue() {},
      dispose() {},
    }
  }
  let disposed = false
  let loaded = false
  let pendingCue: PublicLive2DCue | null = null
  let lastCue = ''
  let lipSync: ReturnType<typeof createReviewVolumeTimelineLipSync> | null = null
  let notification: HTMLElement | null = null
  let releaseAudio: (() => void) | null = null
  let playbackVersion = 0
  const profile = options.profile ?? DEFAULT_LIVE2D_MODEL_PROFILE
  const expression = createLive2DExpressionController(
    profile,
    (name) => {
      if (loaded) renderer.applyAction({ type: 'expression', name })
    },
    (snapshot) => {
      state.dataset.emotion = snapshot.emotion
      state.dataset.expression = snapshot.expression
      state.dataset.expressionMode = snapshot.mode
    },
  )
  const renderer = createLive2DRenderer({
    canvas,
    resizeTo: options.resizeTo ?? window,
    idleVitality: options.idleVitality,
    profile,
    output: options.output,
    beforeMouthApply: () => lipSync?.sample(),
    onMouthApplied(value, taskId) {
      if (notification) notification.dataset.lipSync = 'observed'
      if (!audioStatus) return
      audioStatus.dataset.lipSyncState = 'observed'
      audioStatus.dataset.lipSyncAppliedCount = String(
        Number(audioStatus.dataset.lipSyncAppliedCount ?? 0) + 1,
      )
      audioStatus.dataset.lipSyncPeak = String(
        Math.max(Number(audioStatus.dataset.lipSyncPeak ?? 0), value),
      )
      audioStatus.dataset.lastLipSyncTaskId = taskId
      audioStatus.dataset.lastLipSyncAppliedAt = String(Date.now())
    },
    onState(status, error) {
      state.textContent = status === 'live' ? 'Live2D 已加载' : 'Live2D 加载失败'
      state.dataset.state = status
      if (error) console.error('[Live] Live2D initialization failed', error)
    },
  })
  const applyPublicCue = (cue: PublicLive2DCue): void => {
    if (disposed) return
    if (!loaded) {
      pendingCue = cue
      return
    }
    if (cue.sourceEventId === lastCue) return
    const action = profile.semanticMotions[cue.phase]
    if (!action || cue.emotion !== PUBLIC_CUE_EMOTIONS[cue.phase]) return
    lastCue = cue.sourceEventId
    expression.setEmotion(cue.emotion)
    renderer.applyAction({ type: 'motion', group: action.group, index: action.index })
  }
  const onAction = (value: unknown): void => {
    if (disposed) return
    const action = value as Live2DAction
    // Semantic emotion events own expressions on mapped models; legacy asset
    // commands remain available for models without a semantic mapping.
    if (action?.type === 'expression' && action.name && !profile.emotionExpressions) {
      renderer.applyAction(action)
    }
    if (action?.type === 'motion' && action.group) renderer.applyAction(action)
  }
  socket.on(Events.CHAT.LIVE2D_ACTION, onAction)
  const unbindEmotion = bindLive2DEmotionSocket(socket, {
    setEmotion: expression.setEmotion,
    resetEmotion: () => expression.setEmotion('neutral'),
  })
  const ready = renderer.ready.then(() => {
    if (disposed || state.dataset.state !== 'live') return
    loaded = true
    if (expression.snapshot.expression) {
      renderer.applyAction({ type: 'expression', name: expression.snapshot.expression })
    }
    if (pendingCue) {
      applyPublicCue(pendingCue)
      pendingCue = null
    }
  })
  const cancelReviewAudio = (): void => {
    playbackVersion++
    releaseAudio?.()
    releaseAudio = null
    lipSync?.stop()
    lipSync = null
    notification = null
    renderer.setMouth(0)
    renderer.cancelPerformance()
  }
  return {
    ready,
    setZoom: renderer.setZoom,
    setMouth: renderer.setMouth,
    setEmotion: expression.setEmotion,
    setExpression: expression.setManual,
    applyPublicCue,
    cancelReviewAudio,
    playReviewAudio(element, volumes, performance = DEFAULT_LIVE2D_PERFORMANCE_PLAN) {
      if (disposed) return
      const audio = element.querySelector<HTMLAudioElement>('#reviewAudio')
      if (!audio) throw new Error('TTS review audio is unavailable')
      cancelReviewAudio()
      const version = playbackVersion
      const taskId = `${performance.base}:${performance.accent}:${audio.currentSrc || audio.src}`
      notification = element
      renderer.armPerformance(performance, taskId)
      element.dataset.performanceBase = performance.base
      element.dataset.performanceAccent = performance.accent
      lipSync = createReviewVolumeTimelineLipSync({
        audio,
        volumes,
        setMouth: (value) => renderer.setMouth(value, taskId),
        manualSampling: true,
      })
      const stop = (): void => {
        if (version !== playbackVersion) return
        lipSync?.stop()
        renderer.finishPerformance(taskId)
        releaseAudio?.()
        releaseAudio = null
      }
      audio.addEventListener('ended', stop, { once: true })
      audio.addEventListener('error', stop, { once: true })
      releaseAudio = () => {
        audio.removeEventListener('ended', stop)
        audio.removeEventListener('error', stop)
      }
      lipSync.start()
      void audio
        .play()
        .then(() => {
          if (!disposed && version === playbackVersion) renderer.startPerformance(taskId)
        })
        .catch(() => {
          if (disposed || version !== playbackVersion) return
          audio.dataset.complete = 'blocked'
          renderer.cancelPerformance()
          stop()
        })
    },
    dispose() {
      if (disposed) return
      disposed = true
      socket.off(Events.CHAT.LIVE2D_ACTION, onAction)
      unbindEmotion()
      expression.dispose()
      cancelReviewAudio()
      renderer.dispose()
    },
  }
}
