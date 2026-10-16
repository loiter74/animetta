import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { sendCanonicalChatText } from '@/composables/chatTransport'

const getRandomValues = crypto.getRandomValues.bind(crypto)
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe('browser crypto on LAN HTTP', () => {
  beforeEach(() => {
    vi.resetModules()
    localStorage.clear()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('preserves the native UUID generator when available', async () => {
    const native = vi.fn()
    vi.stubGlobal('crypto', { getRandomValues, randomUUID: native })
    await import('../browserCrypto')
    expect(crypto.randomUUID).toBe(native)
  })

  it('generates distinct v4 IDs and keeps chat identity without native randomUUID', async () => {
    vi.stubGlobal('crypto', { getRandomValues })
    expect(() => sendCanonicalChatText({ emit: vi.fn() }, 'LAN chat')).toThrow(TypeError)
    await import('../browserCrypto')

    const ids = Array.from({ length: 64 }, () => crypto.randomUUID())
    expect(new Set(ids).size).toBe(ids.length)
    ids.forEach((id) => expect(id).toMatch(UUID_V4))

    const socket = { emit: vi.fn() }
    const first = sendCanonicalChatText(socket, 'first LAN message')
    const second = sendCanonicalChatText(socket, 'second LAN message')
    expect(second.conversation_id).toBe(first.conversation_id)
    expect(second.message_id).not.toBe(first.message_id)
    expect(second.task_id).not.toBe(first.task_id)
    expect(second.turn_id).toBe(second.task_id)
    expect(socket.emit).toHaveBeenCalledTimes(2)
  })

  it('propagates random source failures', async () => {
    vi.stubGlobal('crypto', {
      getRandomValues: () => {
        throw new Error('random source unavailable')
      },
    })
    await import('../browserCrypto')
    expect(() => crypto.randomUUID()).toThrow('random source unavailable')
  })
})
