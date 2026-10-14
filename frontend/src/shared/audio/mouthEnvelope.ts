const NOISE_GATE = 0.008
const GAIN = 12
const MAX_OPENING = 0.65
const VISIBILITY_EXPONENT = 0.65
const FRAME_MS = 20
const ATTACK_MS = 50
const RELEASE_MS = 120

export interface MouthEnvelope {
  next(amplitude: number): number
  reset(): number
}

export function createMouthEnvelope(gain = GAIN): MouthEnvelope {
  let value = 0

  return {
    next(amplitude: number): number {
      const gated = Math.max(0, amplitude - NOISE_GATE)
      const amplified = Math.min(1, gated * gain)
      const target = Math.min(MAX_OPENING, Math.pow(amplified, VISIBILITY_EXPONENT))
      const timeConstant = target > value ? ATTACK_MS : RELEASE_MS
      const factor = 1 - Math.exp(-FRAME_MS / timeConstant)
      value += (target - value) * factor
      return value
    },
    reset(): number {
      value = 0
      return value
    },
  }
}
