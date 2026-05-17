import { type Ref } from 'vue'

// ===== PIXI Application State =====

let app: any = null
let container: HTMLElement | null = null
let lastCanvasW = 0
let lastCanvasH = 0

export function getApp(): any { return app }
export function getContainer(): HTMLElement | null { return container }
export function getLastCanvasW(): number { return lastCanvasW }
export function getLastCanvasH(): number { return lastCanvasH }

// ===== PIXI Application Initialization =====

export async function initPixiApp(
  canvasRef: Ref<HTMLCanvasElement | null>
): Promise<void> {
  if (!canvasRef.value) return
  container = canvasRef.value.parentElement

  const PIXI = await import('pixi.js')

  // Required: pixi-live2d-display references window.PIXI.Ticker internally
  ;(window as any).PIXI = PIXI

  app = new PIXI.Application({
    view: canvasRef.value,
    width: container?.clientWidth || 400,
    height: container?.clientHeight || 600,
    transparent: true,
    autoDensity: true,
    resolution: window.devicePixelRatio || 1,
    antialias: true,
    backgroundAlpha: 0,
    preserveDrawingBuffer: true
  })

  lastCanvasW = app.screen.width
  lastCanvasH = app.screen.height
}

// ===== Resize =====

/**
 * Resize the PIXI renderer to match the current container size.
 * Returns the old dimensions so the caller can adjust model position proportionally.
 */
export function handlePixiResize(): { oldW: number; oldH: number } | null {
  if (!app || !container) return null
  const oldW = lastCanvasW || app.screen.width
  const oldH = lastCanvasH || app.screen.height
  app.renderer.resize(container.clientWidth, container.clientHeight)
  lastCanvasW = app.screen.width
  lastCanvasH = app.screen.height
  return { oldW, oldH }
}

// ===== Cleanup =====

export function destroyPixiApp(): void {
  if (app) {
    app.destroy(true)
    app = null
  }
  container = null
}
