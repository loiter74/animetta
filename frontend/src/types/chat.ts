export type MessageRole = 'user' | 'assistant' | 'system'
export type MessageStatus = 'streaming' | 'complete'

export interface ChatMessage {
  id: string
  role: MessageRole
  text: string
  timestamp: number
  status: MessageStatus
  source?: 'text' | 'voice'
}

export interface LlmChunk {
  text: string
  seq: number
  is_complete: boolean
}

export interface Transcript {
  text: string
  is_final: boolean
}
