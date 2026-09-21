import { describe, expect, it, vi } from 'vitest'
import {
  createEarthController,
  type EarthCommand,
  type EarthSnapshot,
  type EarthTransport,
} from './controller'
import type { EarthMap, MapResult } from './contracts'

function fixture() {
  let handlers!: Parameters<EarthTransport['subscribe']>[0]
  const pending: Array<(result: MapResult) => void> = []
  let finish!: (result: MapResult) => void
  let view = {
    longitude: 115,
    latitude: 29,
    height: 19000000,
    view_revision: 1,
    provider: 'test',
    analysis_allowed: false,
    quality: 'ready' as const,
    viewport: { width: 1600, height: 1000, pixel_ratio: 1 },
  }
  const map: EarthMap = {
    readView: () => view,
    move: vi.fn((target, _signal, progress) => {
      progress('accepted')
      view = { ...view, ...target, view_revision: view.view_revision + 1 }
      return new Promise<MapResult>((resolve) => {
        finish = resolve
        pending.push(resolve)
      })
    }),
    cancel: vi.fn(),
    dispose: vi.fn(),
    capture: vi.fn(),
    mark: vi.fn(),
    pick: () => ({ longitude: 120.9, latitude: 31.1 }),
  }
  const snapshot: EarthSnapshot = {
    conversation_id: 'private',
    control_revision: 1,
    phase: 'waiting_input',
    candidates: [],
    transcript: [],
    capabilities: { search: true, voice: true, vision: false, auto_search: false },
  }
  const unsubscribe = vi.fn()
  const transport: EarthTransport = {
    request: vi.fn(async () => ({ ok: true, state: snapshot })),
    result: vi.fn(),
    context: vi.fn(),
    subscribe(callbacks) {
      handlers = callbacks
      return unsubscribe
    },
  }
  const narration = { play: vi.fn(), cancel: vi.fn(), unlock: vi.fn() }
  const changed = vi.fn()
  const controller = createEarthController({
    map,
    transport,
    narration,
    changed,
    conversationId: 'private',
  })
  const command: EarthCommand = {
    conversation_id: 'private',
    control_revision: 1,
    action_id: 'one',
    kind: 'navigate',
    target: { longitude: 121.4, latitude: 31.2, height: 100000 },
  }
  return {
    pending,
    controller,
    map,
    transport,
    narration,
    changed,
    snapshot,
    command,
    unsubscribe,
    get handlers() {
      return handlers
    },
    finish: () => finish({ status: 'ready', view }),
  }
}

describe('Earth execution controller', () => {
  it('executes a structured command and reports readiness separately from acceptance', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.command(f.command)
    expect(f.transport.result).toHaveBeenCalledWith(expect.objectContaining({ status: 'accepted' }))
    expect(f.transport.result).not.toHaveBeenCalledWith(
      expect.objectContaining({ status: 'ready' }),
    )
    f.finish()
    await Promise.resolve()
    expect(f.transport.result).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'ready', action_id: 'one' }),
    )
    f.handlers.command(f.command)
    expect(f.map.move).toHaveBeenCalledTimes(1)
  })
  it('cancels locally before server acknowledgment and discards the late ready result', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.command(f.command)
    f.controller.pause()
    expect(f.map.cancel).toHaveBeenCalled()
    expect(f.narration.cancel).toHaveBeenCalled()
    f.finish()
    await Promise.resolve()
    expect(f.transport.result).not.toHaveBeenCalledWith(
      expect.objectContaining({ status: 'ready' }),
    )
    f.handlers.command({ ...f.command, action_id: 'late' })
    expect(f.map.move).toHaveBeenCalledTimes(1)
  })
  it('never executes another conversation or stale control generation', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.command({ ...f.command, conversation_id: 'other' })
    f.handlers.command({ ...f.command, control_revision: 0 })
    expect(f.map.move).not.toHaveBeenCalled()
  })
  it('sends point identity with the actual view, independently of avatar and audio', async () => {
    const f = fixture()
    await f.controller.open()
    expect(f.controller.select(0.4, 0.6)).toEqual({ longitude: 120.9, latitude: 31.1 })
    expect(f.transport.context).toHaveBeenLastCalledWith(
      expect.objectContaining({
        selected_point: { longitude: 120.9, latitude: 31.1 },
        view_revision: 1,
      }),
    )
    expect(f.narration.play).not.toHaveBeenCalled()
  })
  it('unsubscribes and disposes once; disconnect never resumes automatically', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.disconnected()
    f.handlers.state({ ...f.snapshot, phase: 'moving' })
    expect(f.changed).toHaveBeenLastCalledWith(expect.objectContaining({ phase: 'paused' }))
    f.controller.dispose()
    f.controller.dispose()
    expect(f.unsubscribe).toHaveBeenCalledTimes(1)
    expect(f.map.dispose).toHaveBeenCalledTimes(1)
  })
  it('does not acknowledge narration end on receipt and drops cancelled playback callbacks', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.narration({
      conversation_id: 'private',
      control_revision: 1,
      task_id: 'speech',
      text: '湖泊',
      status: 'ready',
      audio: { data: 'audio', format: 'wav' },
    })
    expect(f.narration.play).toHaveBeenCalledTimes(1)
    expect(f.transport.request).not.toHaveBeenCalledWith(
      expect.objectContaining({ operation: 'playback_ended' }),
    )
    const complete = f.narration.play.mock.calls[0][2] as (status: 'ended') => void
    f.controller.pause()
    complete('ended')
    await Promise.resolve()
    expect(f.transport.request).not.toHaveBeenCalledWith(
      expect.objectContaining({ operation: 'playback_ended' }),
    )
  })
})

describe('Earth revision races', () => {
  it.each(['paused', 'closed', 'error'])(
    'stops execution immediately on a server %s snapshot without cancel command',
    async (phase) => {
      const f = fixture()
      await f.controller.open()
      f.handlers.command(f.command)
      const signal = vi.mocked(f.map.move).mock.calls[0][1]
      const cancels = vi.mocked(f.narration.cancel).mock.calls.length
      f.handlers.state({ ...f.snapshot, phase })
      expect(signal.aborted).toBe(true)
      expect(f.narration.cancel).toHaveBeenCalledTimes(cancels + 1)
      f.finish()
      await Promise.resolve()
      expect(f.transport.result).not.toHaveBeenCalledWith(
        expect.objectContaining({ status: 'ready' }),
      )
      f.handlers.command({ ...f.command, action_id: 'late' })
      expect(f.map.move).toHaveBeenCalledOnce()
      f.controller.dispose()
    },
  )
  it('normalizes an incomplete failure snapshot into safe UI collections', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.state({
      conversation_id: 'private',
      control_revision: 1,
      phase: 'paused',
      error: { code: 'FAIL', message: 'failed' },
    } as EarthSnapshot)
    expect(f.changed).toHaveBeenLastCalledWith(
      expect.objectContaining({
        candidates: [],
        transcript: [],
        capabilities: expect.objectContaining({ search: true }),
        phase: 'paused',
      }),
    )
    f.controller.dispose()
  })
  it('opens a disconnected session paused before explicit continuation', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.disconnected()
    const count = vi.mocked(f.transport.request).mock.calls.length
    f.handlers.state({ ...f.snapshot, phase: 'paused' })
    expect(f.transport.request).toHaveBeenCalledTimes(count)
    vi.mocked(f.transport.request).mockResolvedValueOnce({
      ok: true,
      state: { ...f.snapshot, control_revision: 2, phase: 'paused' },
    })
    await f.controller.resume()
    const requests = vi
      .mocked(f.transport.request)
      .mock.calls.slice(count)
      .map(([value]) => value)
    expect(requests).toEqual([
      expect.objectContaining({ operation: 'open' }),
      expect.objectContaining({ operation: 'continue', control_revision: 2 }),
    ])
    f.handlers.command({ ...f.command, control_revision: 2 })
    expect(f.map.move).toHaveBeenCalledOnce()
    f.controller.dispose()
  })
  it('does not continue if a reconnect open fails or a newer pause supersedes it', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.disconnected()
    vi.mocked(f.transport.request).mockResolvedValueOnce({
      ok: false,
      error: { code: 'EARTH_DISCONNECTED', message: 'offline' },
    })
    await f.controller.resume()
    expect(f.transport.request).not.toHaveBeenCalledWith(
      expect.objectContaining({ operation: 'continue' }),
    )
    let resolve!: (value: Awaited<ReturnType<EarthTransport['request']>>) => void
    vi.mocked(f.transport.request).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const resumed = f.controller.resume()
    f.controller.pause()
    resolve({ ok: true, state: { ...f.snapshot, phase: 'paused' } })
    await resumed
    expect(f.transport.request).not.toHaveBeenCalledWith(
      expect.objectContaining({ operation: 'continue' }),
    )
    f.controller.dispose()
  })
  it('still retries pause when a delayed replacement cancel arrives before its stale ack', async () => {
    const f = fixture()
    await f.controller.open()
    let resolve!: (value: Awaited<ReturnType<EarthTransport['request']>>) => void
    vi.mocked(f.transport.request).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    f.controller.pause()
    f.handlers.command({ ...f.command, kind: 'cancel', control_revision: 2 })
    resolve({
      ok: false,
      error: { code: 'STALE_CONTROL', message: 'stale' },
      state: { ...f.snapshot, control_revision: 2 },
    })
    await Promise.resolve()
    expect(f.transport.request).toHaveBeenLastCalledWith(
      expect.objectContaining({ operation: 'pause', control_revision: 2 }),
    )
    f.controller.dispose()
  })
  it('ignores a superseded request failure without pausing the newer intent', async () => {
    const f = fixture()
    await f.controller.open()
    let reject!: (reason: Error) => void
    vi.mocked(f.transport.request).mockImplementationOnce(
      () =>
        new Promise((_done, fail) => {
          reject = fail
        }),
    )
    const old = f.controller.submit('old')
    await f.controller.submit('new')
    reject(new Error('late failure'))
    await old
    f.handlers.command(f.command)
    expect(f.map.move).toHaveBeenCalledOnce()
    expect(f.changed).not.toHaveBeenCalledWith(
      expect.objectContaining({ error: expect.anything() }),
    )
    f.controller.dispose()
  })
  it('sends pause immediately during a pending text request and ignores its late state', async () => {
    const f = fixture()
    await f.controller.open()
    let resolve!: (value: { ok: boolean; state: EarthSnapshot }) => void
    vi.mocked(f.transport.request).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const text = f.controller.submit('Shanghai')
    f.controller.pause()
    expect(f.transport.request).toHaveBeenLastCalledWith(
      expect.objectContaining({ operation: 'pause' }),
    )
    resolve({
      ok: true,
      state: {
        ...f.snapshot,
        control_revision: 99,
        transcript: [{ role: 'assistant', text: 'stale' }],
      },
    })
    await text
    expect(f.changed).not.toHaveBeenCalledWith(expect.objectContaining({ control_revision: 99 }))
    f.controller.dispose()
  })
  it('retries stale pause once with latest revision, but never retries after a newer intent', async () => {
    const f = fixture()
    await f.controller.open()
    vi.mocked(f.transport.request).mockResolvedValueOnce({
      ok: false,
      error: { code: 'STALE_CONTROL', message: 'stale' },
      state: { ...f.snapshot, control_revision: 2 },
    })
    f.controller.pause()
    await Promise.resolve()
    expect(f.transport.request).toHaveBeenLastCalledWith(
      expect.objectContaining({ operation: 'pause', control_revision: 2 }),
    )
    await f.controller.resume()
    let resolve!: (value: Awaited<ReturnType<EarthTransport['request']>>) => void
    vi.mocked(f.transport.request).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    f.controller.pause()
    const next = f.controller.submit('Qingpu')
    const count = vi.mocked(f.transport.request).mock.calls.length
    resolve({
      ok: false,
      error: { code: 'STALE_CONTROL', message: 'stale' },
      state: { ...f.snapshot, control_revision: 3 },
    })
    await next
    await Promise.resolve()
    expect(f.transport.request).toHaveBeenCalledTimes(count)
    f.controller.dispose()
  })
  it('accepts replacement cancel before navigation and isolates old progress and completion', async () => {
    const f = fixture()
    await f.controller.open()
    f.handlers.command(f.command)
    let resolve!: (value: { ok: boolean }) => void
    vi.mocked(f.transport.request).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const next = f.controller.submit('Qingpu')
    const cancel = { ...f.command, kind: 'cancel' as const, control_revision: 2 }
    f.handlers.command(cancel)
    const second = { ...f.command, action_id: 'two', control_revision: 2 }
    f.handlers.command(second)
    f.handlers.command(cancel)
    f.handlers.command(second)
    expect(f.map.move).toHaveBeenCalledTimes(2)
    const count = vi.mocked(f.transport.result).mock.calls.length
    vi.mocked(f.map.move).mock.calls[0][2]('arrived')
    f.pending[0]({ status: 'ready', view: f.map.readView() })
    await Promise.resolve()
    expect(f.transport.result).toHaveBeenCalledTimes(count)
    f.pending[1]({ status: 'ready', view: f.map.readView() })
    await Promise.resolve()
    expect(f.transport.result).toHaveBeenLastCalledWith(
      expect.objectContaining({ action_id: 'two', control_revision: 2, status: 'ready' }),
    )
    resolve({ ok: true })
    await next
    f.controller.dispose()
  })
  it('does not replay duplicate narration', async () => {
    const f = fixture()
    await f.controller.open()
    const message = {
      conversation_id: 'private',
      control_revision: 1,
      task_id: 'speech',
      text: 'lake',
      status: 'ready' as const,
      audio: { data: 'audio', format: 'wav' },
    }
    f.handlers.narration(message)
    f.handlers.narration(message)
    expect(f.narration.play).toHaveBeenCalledOnce()
    f.controller.dispose()
  })
})
