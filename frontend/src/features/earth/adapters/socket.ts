import { Events } from '@/constants/socket-events'
import type { EarthSocket } from '../contracts'
import type { EarthCommand, EarthNarration, EarthSnapshot, EarthTransport } from '../controller'

export function createEarthTransport(socket: EarthSocket | null): EarthTransport {
  const pending = new Map<ReturnType<typeof setTimeout>, (error: Error) => void>()
  const clearPending = () => {
    for (const [timer, reject] of pending) {
      clearTimeout(timer)
      reject(new Error('探索连接已关闭'))
    }
    pending.clear()
  }
  return {
    request(payload) {
      return new Promise((resolve, reject) => {
        if (!socket?.connected) {
          reject(new Error('服务尚未连接；仍可手动查看地图'))
          return
        }
        if (payload.operation === 'close') {
          socket.emit(Events.EARTH.CONTROL, payload)
          resolve({ ok: true })
          return
        }
        const timer = setTimeout(() => {
          pending.delete(timer)
          reject(new Error('探索响应超时，自动操作已暂停'))
        }, 60000)
        pending.set(timer, reject)
        socket.emit(Events.EARTH.CONTROL, payload, (reply) => {
          if (!pending.delete(timer)) return
          clearTimeout(timer)
          if (!reply || typeof reply !== 'object' || !('ok' in reply)) {
            reject(new Error('探索响应格式无效'))
            return
          }
          resolve(reply as Awaited<ReturnType<EarthTransport['request']>>)
        })
      })
    },
    context(payload) {
      socket?.emit(Events.EARTH.CONTEXT, payload)
    },
    result(payload) {
      socket?.emit(Events.EARTH.RESULT, payload)
    },
    subscribe(handlers) {
      if (!socket) return clearPending
      const entries: Array<[string, (value: unknown) => void]> = [
        [Events.EARTH.STATE, (value) => handlers.state(value as EarthSnapshot)],
        [Events.EARTH.COMMAND, (value) => handlers.command(value as EarthCommand)],
        [Events.EARTH.NARRATION, (value) => handlers.narration(value as EarthNarration)],
        [
          'disconnect',
          () => {
            clearPending()
            handlers.disconnected()
          },
        ],
      ]
      for (const [event, handler] of entries) socket.on(event, handler)
      return () => {
        for (const [event, handler] of entries) socket.off(event, handler)
        clearPending()
      }
    },
  }
}
