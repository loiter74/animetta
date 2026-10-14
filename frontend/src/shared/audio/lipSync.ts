import {
  resolveMouthParameterIndex,
  type MouthParameterLookup,
} from '@/shared/live2d/mouthParameter'
import { createMouthEnvelope } from './mouthEnvelope'

// ===== LipSync State =====

let mouthValue = 0
let targetMouth = 0
let mouthModel: MouthParameterLookup | null = null
let mouthParameterIndex = -1
let lipSyncCancel: (() => void) | null = null

export type MouthTarget = (value: number) => void

// ===== Mouth Target =====

export function setMouthTarget(value: number): void {
  targetMouth = Math.max(0, Math.min(1, value))
}

// ===== PIXI Ticker LipSync =====

interface MouthModel {
  internalModel?: {
    coreModel?: MouthParameterLookup & {
      getParameterValueByIndex(index: number): number
      setParameterValueByIndex(index: number, value: number): void
    }
  }
}

export function tickLipSync(model: MouthModel | null | undefined): void {
  if (!model) return
  const coreModel = model.internalModel?.coreModel
  if (!coreModel) return

  const delta = Math.abs(targetMouth - mouthValue)
  const factor = 0.5 + 0.4 * Math.min(delta / 0.3, 1.0)
  mouthValue += (targetMouth - mouthValue) * factor

  if (coreModel !== mouthModel) {
    mouthModel = coreModel
    mouthParameterIndex = resolveMouthParameterIndex(coreModel)
  }

  if (mouthParameterIndex >= 0) {
    coreModel.setParameterValueByIndex(mouthParameterIndex, mouthValue)
  }
}

// ===== RAF-based LipSync (for audio playback) =====

export function startLipSync(
  audio: HTMLAudioElement,
  volumes: number[],
  setTarget: MouthTarget = setMouthTarget,
): void {
  stopLipSync()
  const intervalMs = 20
  let lastIndex = -1
  let hasStarted = false
  let cancelled = false
  let frame: number | null = null
  // Complete-audio timelines already contain gained peak amplitudes;
  // PCM streaming applies its separate RMS gain in pcmStreamPlayback.
  const mouthEnvelope = createMouthEnvelope(1)

  // RAF tracks the audio envelope only. The PIXI late-frame ticker owns the
  // actual parameter write so mouth opening is always applied after motion
  // and semantic expression overlays.
  function cancel(): void {
    if (cancelled) return
    cancelled = true
    if (frame !== null) cancelAnimationFrame(frame)
    setTarget(mouthEnvelope.reset())
  }

  const tick = () => {
    if (cancelled) return
    if (audio.ended || (hasStarted && audio.paused)) {
      cancel()
      return
    }

    if (audio.paused) {
      setTarget(0)
    } else {
      hasStarted = true
      const index = Math.floor((audio.currentTime * 1000) / intervalMs)
      if (index !== lastIndex) {
        setTarget(mouthEnvelope.next(volumes[index] ?? 0))
        lastIndex = index
      }
    }
    frame = requestAnimationFrame(tick)
  }
  frame = requestAnimationFrame(tick)
  lipSyncCancel = cancel
}

export function stopLipSync(): void {
  const cancel = lipSyncCancel
  lipSyncCancel = null
  if (cancel) cancel()
  else setMouthTarget(0)
}
