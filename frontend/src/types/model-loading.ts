/** Model loading status from backend ModelLoadingManager */
export type ModelLoadStatus = 'loading' | 'loaded' | 'error'

export interface ModelStatusPayload {
  service: string
  name: string
  status: ModelLoadStatus
  error?: string
}

export interface ModelLoadingState {
  service: string
  name: string
  status: ModelLoadStatus
  error?: string
}
