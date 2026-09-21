import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMicrophone } from './microphone'

afterEach(() => vi.unstubAllGlobals())

describe('private Earth microphone lifecycle', () => {
  it('stops a late microphone grant after disposal without sending audio', async () => {
    let grant!: (stream: MediaStream) => void
    const stop = vi.fn()
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: () =>
          new Promise<MediaStream>((resolve) => {
            grant = resolve
          }),
      },
    })
    const callbacks = { started: vi.fn(), captured: vi.fn(), changed: vi.fn(), failed: vi.fn() }
    const microphone = createMicrophone(callbacks)
    const start = microphone.start()
    expect(callbacks.started).toHaveBeenCalledTimes(1)
    microphone.dispose()
    grant({ getTracks: () => [{ stop }] } as unknown as MediaStream)
    await start
    expect(stop).toHaveBeenCalledTimes(1)
    expect(callbacks.captured).not.toHaveBeenCalled()
    expect(callbacks.failed).not.toHaveBeenCalled()
  })
  it('cancels permission-pending recording and rejects duplicate starts', async () => {
    let grant!: (stream: MediaStream) => void
    const getUserMedia = vi.fn(
      () =>
        new Promise<MediaStream>((resolve) => {
          grant = resolve
        }),
    )
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } })
    const callbacks = { started: vi.fn(), captured: vi.fn(), changed: vi.fn(), failed: vi.fn() }
    const microphone = createMicrophone(callbacks)
    const first = microphone.start()
    await microphone.start()
    expect(getUserMedia).toHaveBeenCalledTimes(1)
    microphone.stop()
    const stop = vi.fn()
    grant({ getTracks: () => [{ stop }] } as unknown as MediaStream)
    await first
    expect(stop).toHaveBeenCalledTimes(1)
    expect(callbacks.changed).toHaveBeenLastCalledWith(false)
  })
})
