/**
 * Live2D Module Entry Point
 */

import { Live2DRenderer } from './Live2DRenderer.js';

// Export all components
export { Live2DRenderer };
export { PixiApp } from './core/PixiApp.js';
export { ModelLoader } from './core/ModelLoader.js';
export { ExpressionController } from './renderer/ExpressionController.js';
export { ScaleManager } from './renderer/ScaleManager.js';
export { BackgroundManager } from './renderer/BackgroundManager.js';
export { IpcBridge } from './bridge/IpcBridge.js';
export { DisplayConfig } from './config/index.js';

// Initialize on load
let renderer;

async function init() {
  try {
    console.log('[Live2D] Initializing...');

    // 库已通过 HTML script 标签加载，直接初始化
    renderer = new Live2DRenderer();
    await renderer.init();
    console.log('[Live2D] Ready');
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
