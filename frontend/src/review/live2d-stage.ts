import { Events } from '@/constants/socket-events'
import type { Live2DAction } from '@/types/live2d'
import type { LiveSocket } from '@/shared/transport/liveSocket'
import type { PublicLive2DCue } from '@/shared/broadcast/publicActivity'
import type { Live2DPerformancePlanV1 } from '@/types/socket-events'
import { DEFAULT_LIVE2D_PERFORMANCE_PLAN } from '@/shared/live2d/performanceController'
import { createLive2DRenderer } from '@/shared/live2d/renderer'
import { computeLive2DLayout } from './layout'
import { createReviewVolumeTimelineLipSync } from './review-lip-sync'

const PUBLIC_CUE_ACTIONS = {
  planning: { emotion: 'thinking', group: 'TapBody', index: 0 },
  observing: { emotion: 'thinking', group: 'TapBody', index: 1 },
  committed: { emotion: 'confident', group: 'TapBody', index: 2 },
  acting: { emotion: 'focused', group: 'TapBody', index: 3 },
  checking: { emotion: 'thinking', group: 'TapBody', index: 1 },
  recovering: { emotion: 'alert', group: 'TapBody', index: 4 },
  finished: { emotion: 'relieved', group: 'TapBody', index: 5 },
} as const

export interface Live2DStage {
  ready: Promise<void>
  setMouth(value: number, taskId?: string): void
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
      setMouth() {},
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
  const renderer = createLive2DRenderer({
    canvas,
    resizeTo: options.resizeTo ?? window,
    idleVitality: options.idleVitality,
    layout: computeLive2DLayout,
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
    const action = PUBLIC_CUE_ACTIONS[cue.phase]
    if (cue.emotion !== action.emotion) return
    lastCue = cue.sourceEventId
    renderer.applyAction({ type: 'motion', group: action.group, index: action.index })
  }
  const onAction = (value: unknown): void => {
    if (disposed) return
    const action = value as Live2DAction
    if (action?.type === 'expression' && action.name) renderer.applyAction(action)
    if (action?.type === 'motion' && action.group) renderer.applyAction(action)
  }
  const ready = renderer.ready.then(() => {
    if (disposed || state.dataset.state !== 'live') return
    loaded = true
    socket.on(Events.CHAT.LIVE2D_ACTION, onAction)
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
    setMouth: renderer.setMouth,
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
      if (loaded) socket.off(Events.CHAT.LIVE2D_ACTION, onAction)
      cancelReviewAudio()
      renderer.dispose()
    },
  }
}
