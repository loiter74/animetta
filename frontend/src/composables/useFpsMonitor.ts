/**
 * FPS monitoring utility. Tracks frame rate and auto-degrades
 * animations when performance drops below threshold.
 */

interface FpsMonitorOptions {
  /** Report interval in ms (default: 2000) */
  interval?: number
  /** FPS threshold for auto-degrade (default: 45) */
  degradeThreshold?: number
  /** Callback when FPS drops below threshold */
  onDegrade?: (fps: number) => void
  /** Callback when FPS recovers */
  onRecover?: (fps: number) => void
}

export function useFpsMonitor(options: FpsMonitorOptions = {}) {
  const { interval = 2000, degradeThreshold = 45, onDegrade, onRecover } = options

  let frameCount = 0
  let lastTime = performance.now()
  let rafId = 0
  let intervalId: ReturnType<typeof setInterval> | null = null
  let isDegraded = false

  function tick() {
    frameCount++
    rafId = requestAnimationFrame(tick)
  }

  function reportFps() {
    const now = performance.now()
    const elapsed = now - lastTime
    const fps = Math.round((frameCount * 1000) / elapsed)

    if (fps < degradeThreshold && !isDegraded) {
      isDegraded = true
      onDegrade?.(fps)
    } else if (fps >= degradeThreshold && isDegraded) {
      isDegraded = false
      onRecover?.(fps)
    }

    frameCount = 0
    lastTime = now
  }

  function start() {
    frameCount = 0
    lastTime = performance.now()
    rafId = requestAnimationFrame(tick)
    intervalId = setInterval(reportFps, interval)
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId)
    if (intervalId) clearInterval(intervalId)
  }

  return { start, stop, isDegraded }
}
