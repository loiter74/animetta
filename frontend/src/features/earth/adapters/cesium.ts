import type * as Cesium from 'cesium'
import type { CameraTarget, EarthMap, EarthView, MapResult, MapStatus } from '../contracts'

let loading: Promise<typeof Cesium> | undefined

function loadCesium(): Promise<typeof Cesium> {
  if (loading) return loading
  loading = new Promise((resolve, reject) => {
    const root = window as unknown as { Cesium?: typeof Cesium; CESIUM_BASE_URL?: string }
    if (root.Cesium) return resolve(root.Cesium)
    root.CESIUM_BASE_URL = '/earth/cesium/'
    const css = document.createElement('link')
    css.rel = 'stylesheet'
    css.href = '/earth/cesium/Widgets/widgets.css'
    document.head.append(css)
    const script = document.createElement('script')
    script.src = '/earth/cesium/Cesium.js'
    script.onload = () => {
      if (root.Cesium) resolve(root.Cesium)
      else {
        script.remove()
        css.remove()
        loading = undefined
        reject(new Error('地图引擎未初始化'))
      }
    }
    script.onerror = () => {
      script.remove()
      css.remove()
      loading = undefined
      reject(new Error('地图资源加载失败，请重新进入探索'))
    }
    document.head.append(script)
  })
  return loading
}

export async function createCesiumMap(
  container: HTMLElement,
  signal: AbortSignal,
  load: () => Promise<typeof Cesium> = loadCesium,
): Promise<EarthMap> {
  signal.throwIfAborted()
  const C = await load()
  signal.throwIfAborted()
  const viewer = new C.Viewer(container, {
    baseLayer: false,
    baseLayerPicker: false,
    geocoder: false,
    timeline: false,
    animation: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    fullscreenButton: false,
    selectionIndicator: false,
    infoBox: false,
    contextOptions: { webgl: { preserveDrawingBuffer: false } },
  })
  let disposed = false
  let revision = 1
  let failedTiles = false
  let stop: (() => void) | undefined
  const releases: Array<() => void> = []
  const destroy = () => {
    if (disposed) return
    stop?.()
    disposed = true
    signal.removeEventListener('abort', destroy)
    for (const release of releases.splice(0)) release()
    viewer.destroy()
  }
  signal.addEventListener('abort', destroy, { once: true })
  try {
    const imagery = await C.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
      { enablePickFeatures: false },
    )
    signal.throwIfAborted()
    viewer.imageryLayers.addImageryProvider(imagery)
    releases.push(
      imagery.errorEvent.addEventListener(() => {
        failedTiles = true
      }),
    )
    releases.push(
      viewer.camera.moveEnd.addEventListener(() => {
        revision++
      }),
    )
    viewer.camera.setView({ destination: C.Cartesian3.fromDegrees(115, 29, 19000000) })
    let lastView: EarthView
    const readView = (): EarthView => {
      if (disposed) return lastView
      const camera = viewer.camera
      lastView = {
        longitude: C.Math.toDegrees(camera.positionCartographic.longitude),
        latitude: C.Math.toDegrees(camera.positionCartographic.latitude),
        height: camera.positionCartographic.height,
        heading: camera.heading,
        pitch: camera.pitch,
        view_revision: revision,
        provider: 'Esri World Imagery',
        analysis_allowed: false,
        quality: failedTiles ? 'degraded' : viewer.scene.globe.tilesLoaded ? 'ready' : 'loading',
        viewport: {
          width: container.clientWidth,
          height: container.clientHeight,
          pixel_ratio: window.devicePixelRatio,
        },
      }
      return lastView
    }
    readView()
    const map: EarthMap = {
      readView,
      move(
        target: CameraTarget,
        moveSignal: AbortSignal,
        progress: (status: MapStatus) => void,
      ): Promise<MapResult> {
        stop?.()
        return new Promise((resolve) => {
          let done = false
          let removeRender: (() => void) | undefined
          let timer: ReturnType<typeof setTimeout> | undefined
          const finish = (status: MapStatus, error?: string) => {
            if (done) return
            done = true
            clearTimeout(timer)
            removeRender?.()
            moveSignal.removeEventListener('abort', cancel)
            stop = undefined
            resolve({ status, view: readView(), error })
          }
          const cancel = () => {
            if (!done) {
              viewer.camera.cancelFlight()
              finish('cancelled')
            }
          }
          stop = cancel
          if (moveSignal.aborted || disposed) return finish('cancelled')
          moveSignal.addEventListener('abort', cancel, { once: true })
          failedTiles = false
          progress('accepted')
          if (done) return
          const distance = Math.hypot(
            target.longitude - readView().longitude,
            target.latitude - readView().latitude,
          )
          try {
            viewer.camera.flyTo({
              destination: C.Cartesian3.fromDegrees(
                target.longitude,
                target.latitude,
                target.height,
              ),
              orientation: {
                heading: target.heading ?? 0,
                pitch: target.pitch ?? -Math.PI / 2,
                roll: 0,
              },
              duration: distance > 10 ? 7 : 4,
              cancel: () => finish('cancelled'),
              complete: () => {
                if (done) return
                progress('arrived')
                if (done) return
                const check = () => {
                  if (viewer.scene.globe.tilesLoaded) finish(failedTiles ? 'degraded' : 'ready')
                }
                removeRender = viewer.scene.postRender.addEventListener(check)
                timer = setTimeout(() => finish('degraded', '影像未就绪，已暂停自动探索'), 20000)
                check()
              },
            })
          } catch (error) {
            finish('failed', error instanceof Error ? error.message : '地图移动失败')
          }
        })
      },
      pick(x, y) {
        if (
          disposed ||
          !Number.isFinite(x) ||
          !Number.isFinite(y) ||
          x < 0 ||
          x > 1 ||
          y < 0 ||
          y > 1
        )
          return null
        const position = new C.Cartesian2(x * container.clientWidth, y * container.clientHeight)
        const point = viewer.camera.pickEllipsoid(position, viewer.scene.globe.ellipsoid)
        if (!point) return null
        const geo = C.Cartographic.fromCartesian(point)
        return {
          longitude: C.Math.toDegrees(geo.longitude),
          latitude: C.Math.toDegrees(geo.latitude),
        }
      },
      mark(point, label) {
        if (disposed) return
        viewer.entities.removeById('earth-user-point')
        const accent = C.Color.fromCssColorString(
          getComputedStyle(container).getPropertyValue('--c-accent').trim(),
        )
        viewer.entities.add({
          id: 'earth-user-point',
          position: C.Cartesian3.fromDegrees(point.longitude, point.latitude),
          point: {
            pixelSize: 12,
            color: accent,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
          label: {
            text: label,
            font: '16px sans-serif',
            showBackground: true,
            pixelOffset: new C.Cartesian2(0, -26),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
        })
      },
      async capture() {
        throw new Error('当前影像源未获图像分析授权')
      },
      cancel() {
        if (!disposed) {
          stop?.()
          viewer.camera.cancelFlight()
        }
      },
      dispose() {
        destroy()
      },
    }
    return map
  } catch (error) {
    signal.removeEventListener('abort', destroy)
    destroy()
    throw error
  }
}
