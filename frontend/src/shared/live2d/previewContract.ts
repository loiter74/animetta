import { CHAT_EMOTIONS } from '@/shared/contracts/socket-events'

export const AVATAR_PREVIEW_EMOTIONS = CHAT_EMOTIONS

export type AvatarPreviewCommand =
  | { type: 'expression'; name: string | null }
  | { type: 'emotion'; emotion: string }
  | { type: 'mouth-demo' }
  | { type: 'zoom'; value: number }
  | { type: 'reset' }

export interface AvatarPreviewState {
  modelId: string
  loaded: boolean
  expression: string
  emotion: string
  mode: 'auto' | 'manual'
  zoom: number
  mouthDemo: boolean
  socketState: string
  livestreamState: string
}
