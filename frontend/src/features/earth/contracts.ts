/** Engine-neutral values. Coordinates are WGS84 degrees; heights are metres. */
export interface GeoPoint {
  longitude: number
  latitude: number
}

export interface CameraTarget extends GeoPoint {
  height: number
  heading?: number
  pitch?: number
}

export type MapStatus = 'accepted' | 'arrived' | 'ready' | 'degraded' | 'failed' | 'cancelled'

export interface EarthView extends CameraTarget {
  view_revision: number
  provider: string
  analysis_allowed: boolean
  quality: 'ready' | 'loading' | 'degraded'
  viewport: { width: number; height: number; pixel_ratio: number }
}

export interface MapResult {
  status: MapStatus
  view: EarthView
  error?: string
}

export interface EarthMap {
  move(
    target: CameraTarget,
    signal: AbortSignal,
    progress: (status: MapStatus) => void,
  ): Promise<MapResult>
  readView(): EarthView
  pick(x: number, y: number): GeoPoint | null
  mark(point: GeoPoint, label: string): void
  capture(): Promise<string>
  cancel(): void
  dispose(): void
}

export interface EarthSocket {
  readonly connected: boolean
  on(event: string, listener: (payload: unknown) => void): unknown
  off(event: string, listener: (payload: unknown) => void): unknown
  emit(event: string, payload: unknown, ack?: (reply: unknown) => void): unknown
}

export interface NarrationAudio {
  audio_data?: string
  audio_url?: string
  format?: string
  volumes?: number[]
}

export interface Narration {
  play(
    taskId: string,
    audio: NarrationAudio,
    completed: (status: 'ended' | 'cancelled') => void,
  ): void
  cancel(): void
  unlock(): void
}
