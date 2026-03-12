/**
 * Live2D Module Entry Point
 */

import { waitForLibs } from './core/LibLoader.js';
import { Live2DRenderer } from './Live2DRenderer.js';

// Export all components
export { Live2DRenderer };
export { PixiApp } from './core/PixiApp.js';
export { ModelLoader } from './core/ModelLoader.js';
export { waitForLibs } from './core/LibLoader.js';
export { LipSync } from './animation/LipSync.js';
export { ExpressionController } from './animation/ExpressionController.js';
export { ActionExecutor } from './animation/ActionExecutor.js';
export { Live2DIpcListeners } from './ipc/Live2DIpcListeners.js';

// Initialize on load
let renderer;

async function init() {
  try {
    console.log('[Live2D] Waiting for libraries...');
    await waitForLibs(10000);
    console.log('[Live2D] Libraries loaded');

    renderer = new Live2DRenderer();
    await renderer.init();
  } catch (error) {
    console.error('[Live2D] Initialization failed:', error);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

console.log('[Live2D] Module loaded');
