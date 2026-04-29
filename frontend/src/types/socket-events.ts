export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error'

export interface ConnectionStatusPayload {
  status: ConnectionStatus
  message?: string
}
