import { onMounted, onUnmounted, type Ref } from 'vue'
import type { Live2DAction } from '@/types/live2d'
import { getSocket } from '@/composables/useSocket'

// ===== Public exports for backward compatibility =====
export { MODEL_PATH } from './useLive2DModel'
export type { ScaleStrategy } from './useLive2DModel'

// ===== Import sub-composable internals =====
import { getApp, initPixiApp, handlePixiResize, destroyPixiApp } from './usePixiApp'
import { loadModel, unloadModel, setExpression, playMotion, getModel } from './useLive2DModel'
import { tickLipSync, setMouthTarget } from './useLipSync'
import { playAudio, stopAudio } from './useAudioPlayback'
import { playParameterTimeline, setParam, cancelTimeline } from './useParameterTimeline'
import {
  isLoaded, isLoading, loadError, modelInfo, isDragging,
  startDrag, onDrag, stopDrag, focus as focusFn,
  zoom as zoomFn, resetView as resetViewFn, setScaleStrategy as setScaleStrategyFn
} from './useInteraction'

// ===== Main Composable =====

/**
 * Unified composable entry point — wires all sub-composables together
 * while maintaining the identical public API surface.
 */
export function useLive2D(canvasRef: Ref<HTMLCanvasElement | null>) {
  // ===== Init =====

  async function init(): Promise<void> {
    if (!canvasRef.value) return

    try {
      await initPixiApp(canvasRef)

      const app = getApp()
      if (app) {
        // NOTE: pixi.js internally uses synchronous gl.readPixels() which
        // triggers "GPU stall due to ReadPixels" warnings in some GPU drivers.
        // This is a known limitation of the pixi-live2d-display rendering
        // pipeline. Mitigation: reduce ticker FPS if warnings are excessive:
        //   app.ticker.maxFPS = 30
        // See: .gstack/qa-reports/qa-report-localhost-3000-2026-06-02.md (ISSUE-008)
        app.ticker.add(tickLipSync)
        setupSocketListeners()
      }
    } catch (e) {
      loadError.value = 'pixi.js 初始化失败: ' + (e as Error).message
      isLoading.value = false
    }
  }

  // ===== Resize =====

  /**
   * Handle container resize (e.g. DevTools open/close).
   * Resizes renderer and adjusts model position proportionally.
   * Does NOT re-center — preserves user's drag offset.
   * Does NOT change scale.
   */
  function handleResize(): void {
    const result = handlePixiResize()
    if (!result) return

    const model = getModel()
    const app = getApp()
    if (model && app) {
      model.x *= app.screen.width / result.oldW
      model.y *= app.screen.height / result.oldH
    }
  }

  // ===== Execute Action =====

  function executeAction(action: Live2DAction): void {
    switch (action.type) {
      case 'expression': setExpression(action.name!); break
      case 'motion': playMotion(action.group!, action.index!); break
      case 'param': setParam(action.name!, action.value!); break
      case 'sequence':
        let delay = 0
        for (const sub of (action as any).actions ?? []) {
          if (sub.type === 'wait') { delay += sub.ms || 0 }
          else { setTimeout(() => executeAction(sub), delay) }
        }
        break
    }
  }

  // ===== Socket Listeners =====

  function setupSocketListeners(): void {
    const socket = getSocket()
    if (!socket) return

    socket.on('live2d.action', (data: unknown) => {
      executeAction(data as Live2DAction)
    })

    socket.on('audio_with_expression', (data: unknown) => {
      const d = data as any
      if (d.use_parameter_mapping && d.expressions?.frames) {
        playParameterTimeline(d)
      } else {
        playAudio(d)
      }
    })

    socket.on('stop_audio', () => {
      stopAudio()
    })
  }

  function teardownSocketListeners(): void {
    const socket = getSocket()
    if (!socket) return
    socket.off('live2d.action')
    socket.off('audio_with_expression')
    socket.off('stop_audio')
  }

  // ===== Destroy =====

  function destroy(): void {
    stopAudio()
    cancelTimeline()
    teardownSocketListeners()

    const app = getApp()
    if (app) {
      app.ticker.remove(tickLipSync)
      unloadModel()
    }
    destroyPixiApp()

    window.removeEventListener('resize', handleResize)
  }

  // ===== Lifecycle =====

  onMounted(() => {
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    destroy()
  })

  // ===== Public API (identical to original) =====

  return {
    isLoaded,
    isLoading,
    loadError,
    modelInfo,
    isDragging,
    init,
    loadModel,
    handleResize,
    setExpression,
    playMotion,
    setMouthTarget,
    executeAction,
    stopAudio,
    startDrag,
    onDrag,
    stopDrag,
    /** Scroll-wheel zoom. Positive delta = zoom in, negative = zoom out. Range 0.05x – 10x. */
    zoom(delta: number) {
      zoomFn(delta)
    },
    /** Reset to user's preferred initial position and scale */
    resetView() {
      resetViewFn()
    },
    setScaleStrategy(s: string) {
      setScaleStrategyFn(s)
    },
    /** Mouse focus (eye/head tracking) */
    focus(x: number, y: number) {
      focusFn(x, y)
    },
    destroy
  }
}
