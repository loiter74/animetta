import type { Live2DPerformanceProfile } from './performanceProfile'

export interface Live2DIdleVitalityParameter {
  readonly name: string
  readonly factor: number
}

export interface Live2DModelProfile {
  readonly id: string
  readonly modelUrl: string
  readonly mouthParameters: readonly string[]
  readonly performance: Live2DPerformanceProfile
  readonly framing: {
    readonly scale: number
    readonly x: number
    readonly y: number
  }
  readonly semanticMotions: Readonly<Record<string, { group: string; index?: number }>>
  readonly idleVitality?: readonly Live2DIdleVitalityParameter[]
}
