import { afterEach, describe, expect, it, vi } from 'vitest'
import type * as Cesium from 'cesium'
import { createCesiumMap } from './cesium'

function event() {
  const listeners = new Set<() => void>()
  return {
    listeners,
    addEventListener(listener: () => void) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    fire() {
      for (const listener of [...listeners]) listener()
    },
  }
}
function fixture() {
  const postRender = event(),
    moveEnd = event(),
    errorEvent = event()
  let flight: { complete(): void; cancel(): void } | undefined
  const camera = {
    positionCartographic: { longitude: 115, latitude: 29, height: 19000000 },
    heading: 0,
    pitch: -1,
    moveEnd,
    setView: vi.fn(),
    flyTo: vi.fn((options: { complete(): void; cancel(): void }) => {
      flight = options
    }),
    cancelFlight: vi.fn(() => {
      flight?.cancel()
    }),
    pickEllipsoid: vi.fn(() => ({ longitude: 120, latitude: 31 })),
  }
  const viewer = {
    camera,
    scene: { globe: { tilesLoaded: false, ellipsoid: {} }, postRender },
    imageryLayers: { addImageryProvider: vi.fn() },
    entities: { removeById: vi.fn(), add: vi.fn() },
    destroy: vi.fn(),
  }
  const sdk = {
    Viewer: class {
      constructor() {
        return viewer
      }
    },
    ArcGisMapServerImageryProvider: { fromUrl: vi.fn().mockResolvedValue({ errorEvent }) },
    Math: { toDegrees: (value: number) => value },
    Cartesian3: { fromDegrees: (...values: number[]) => values },
    Cartesian2: class {
      constructor(
        public x: number,
        public y: number,
      ) {}
    },
    Cartographic: { fromCartesian: (value: unknown) => value },
    Color: { fromCssColorString: () => ({}) },
  }
  const container = document.createElement('div')
  Object.defineProperties(container, { clientWidth: { value: 800 }, clientHeight: { value: 600 } })
  const life = new AbortController()
  const load = async () => sdk as unknown as typeof Cesium
  return {
    viewer,
    sdk,
    container,
    life,
    postRender,
    moveEnd,
    errorEvent,
    load,
    arrive() {
      moveEnd.fire()
      flight?.complete()
    },
    create: () => createCesiumMap(container, life.signal, load),
  }
}
const target = { longitude: 121, latitude: 31, height: 10000 }
afterEach(() => {
  vi.useRealTimers()
})

describe('Cesium adapter with SDK boundary fake', () => {
  it('does not start a flight when acceptance callback synchronously cancels', async () => {
    const f = fixture(),
      map = await f.create(),
      abort = new AbortController()
    const result = await map.move(target, abort.signal, () => abort.abort())
    expect(result.status).toBe('cancelled')
    expect(f.viewer.camera.flyTo).not.toHaveBeenCalled()
    map.dispose()
  })
  it('does not report errored tiles as ready', async () => {
    const f = fixture(),
      map = await f.create()
    const result = map.move(target, new AbortController().signal, vi.fn())
    f.errorEvent.fire()
    f.viewer.scene.globe.tilesLoaded = true
    f.arrive()
    expect((await result).status).toBe('degraded')
    map.dispose()
  })
  it('separates accepted, arrived and tiles ready, removing render hooks', async () => {
    const f = fixture(),
      map = await f.create(),
      progress = vi.fn()
    const result = map.move(target, new AbortController().signal, progress)
    expect(progress).toHaveBeenCalledWith('accepted')
    f.arrive()
    expect(progress).toHaveBeenLastCalledWith('arrived')
    expect(f.postRender.listeners.size).toBe(1)
    f.viewer.scene.globe.tilesLoaded = true
    f.postRender.fire()
    expect(await result).toMatchObject({ status: 'ready', view: { view_revision: 2 } })
    expect(f.postRender.listeners.size).toBe(0)
    map.dispose()
  })
  it('cancels previous flight without allowing its late completion to finish the replacement', async () => {
    const f = fixture(),
      map = await f.create()
    const first = map.move(target, new AbortController().signal, vi.fn())
    const old = f.viewer.camera.flyTo.mock.calls[0][0]
    const second = map.move(target, new AbortController().signal, vi.fn())
    expect((await first).status).toBe('cancelled')
    old.complete()
    expect(f.postRender.listeners.size).toBe(0)
    f.viewer.scene.globe.tilesLoaded = true
    f.arrive()
    expect((await second).status).toBe('ready')
    map.dispose()
  })
  it('cleans flight, listeners and timeout on lifecycle abort and repeated disposal', async () => {
    vi.useFakeTimers()
    const f = fixture(),
      map = await f.create()
    const result = map.move(target, new AbortController().signal, vi.fn())
    f.arrive()
    f.life.abort()
    expect((await result).status).toBe('cancelled')
    expect(
      f.postRender.listeners.size + f.moveEnd.listeners.size + f.errorEvent.listeners.size,
    ).toBe(0)
    expect(vi.getTimerCount()).toBe(0)
    map.dispose()
    map.dispose()
    map.cancel()
    expect(f.viewer.destroy).toHaveBeenCalledOnce()
    expect((await map.move(target, new AbortController().signal, vi.fn())).status).toBe('cancelled')
  })
  it('reports timed out imagery as degraded and never permits image analysis', async () => {
    vi.useFakeTimers()
    const f = fixture(),
      map = await f.create()
    const result = map.move(target, new AbortController().signal, vi.fn())
    f.arrive()
    await vi.advanceTimersByTimeAsync(20000)
    expect((await result).status).toBe('degraded')
    expect(f.postRender.listeners.size).toBe(0)
    await expect(map.capture()).rejects.toThrow('未获图像分析授权')
    map.dispose()
  })
  it('handles preaborted moves, synchronous flight errors and invalid pick coordinates', async () => {
    const f = fixture(),
      map = await f.create(),
      abort = new AbortController()
    abort.abort()
    expect((await map.move(target, abort.signal, vi.fn())).status).toBe('cancelled')
    expect(f.viewer.camera.flyTo).not.toHaveBeenCalled()
    f.viewer.camera.flyTo.mockImplementationOnce(() => {
      throw new Error('flight failed')
    })
    expect(await map.move(target, new AbortController().signal, vi.fn())).toMatchObject({
      status: 'failed',
      error: 'flight failed',
    })
    expect(map.pick(-1, 0)).toBeNull()
    expect(map.pick(0.5, 0.5)).toEqual({ longitude: 120, latitude: 31 })
    expect(f.viewer.camera.pickEllipsoid).toHaveBeenCalledWith(
      expect.objectContaining({ x: 400, y: 300 }),
      expect.anything(),
    )
    map.dispose()
  })
  it('destroys viewer if imagery initialization finishes after abort', async () => {
    const f = fixture()
    let resolve!: (value: unknown) => void
    f.sdk.ArcGisMapServerImageryProvider.fromUrl.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const pending = f.create()
    await Promise.resolve()
    f.life.abort()
    resolve({ errorEvent: f.errorEvent })
    await expect(pending).rejects.toThrow()
    expect(f.viewer.destroy).toHaveBeenCalledOnce()
    expect(f.viewer.imageryLayers.addImageryProvider).not.toHaveBeenCalled()
  })
})
