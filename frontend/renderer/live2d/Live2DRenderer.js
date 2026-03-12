/**
 * Live2DRenderer - Main controller for Live2D rendering
 * Coordinates PIXI app, model loading, animation, and IPC
 */

import { PixiApp } from './core/PixiApp.js';
import { ModelLoader } from './core/ModelLoader.js';
import { LipSync } from './animation/LipSync.js';
import { ExpressionController } from './animation/ExpressionController.js';
import { ActionExecutor } from './animation/ActionExecutor.js';
import { Live2DIpcListeners } from './ipc/Live2DIpcListeners.js';

export class Live2DRenderer {
  constructor() {
    // DOM elements
    this.canvas = document.getElementById('live2d-canvas');
    this.container = document.getElementById('live2d-container');

    // State
    this.isLoaded = false;

    // Components (initialized in _init)
    this.pixiApp = null;
    this.app = null;
    this.modelLoader = null;
    this.lipSync = null;
    this.expressionController = null;
    this.actionExecutor = null;
    this.ipc = null;

    // Resize handler bound
    this._handleResize = this._handleResize.bind(this);
  }

  /**
   * Initialize the renderer
   */
  async init() {
    try {
      console.log('[Live2DRenderer] Initializing...');

      // Create PIXI application
      this.pixiApp = new PixiApp(this.canvas, this.container);
      this.app = await this.pixiApp.create();

      // Create model loader
      this.modelLoader = new ModelLoader(this.app, this.container);

      // Create lip sync (uses PIXI ticker, not rAF)
      this.lipSync = new LipSync(this.app.ticker);

      // Create expression controller
      this.expressionController = new ExpressionController();

      // Create action executor
      this.actionExecutor = new ActionExecutor(this.expressionController);

      // Setup IPC listeners
      this.ipc = new Live2DIpcListeners({
        onAction: (action) => this.actionExecutor.execute(action),
        onAudioStream: (data) => this._handleAudioStream(data),
      });
      this.ipc.setup();

      // Handle window resize
      window.addEventListener('resize', this._handleResize);

      // Expose globally for IPC calls
      window.live2dRenderer = this;

      console.log('[Live2DRenderer] Initialized successfully');

      // Load default model
      await this._loadDefaultModel();
    } catch (error) {
      console.error('[Live2DRenderer] Initialization failed:', error);
      this._showError(`Failed to initialize: ${error.message}`);
    }
  }

  /**
   * Load default model from config or fallback
   */
  async _loadDefaultModel() {
    const fallbackPath = '../../public/live2d/haru/haru_greeter_t03.model3.json';

    try {
      let modelPath = null;

      // Try to get from config
      if (window.electronAPI?.getConfig) {
        modelPath = await window.electronAPI.getConfig('model.defaultPath');
      }

      if (modelPath) {
        console.log('[Live2DRenderer] Default model path from config:', modelPath);
        await this.loadModel(modelPath);
      } else {
        console.log('[Live2DRenderer] Using fallback model path:', fallbackPath);
        await this.loadModel(fallbackPath);
      }
    } catch (error) {
      console.error('[Live2DRenderer] Failed to load default model, trying fallback:', error);
      try {
        await this.loadModel(fallbackPath);
      } catch (fallbackError) {
        console.error('[Live2DRenderer] Fallback model also failed:', fallbackError);
      }
    }
  }

  /**
   * Load Live2D model
   * @param {string} modelPath - Path to model file
   */
  async loadModel(modelPath) {
    try {
      const model = await this.modelLoader.load(modelPath);

      // Connect model to components
      this.lipSync.setModel(model);
      this.expressionController.setModel(model);
      this.expressionController.enableTapInteraction();

      this.isLoaded = true;
    } catch (error) {
      console.error('[Live2DRenderer] Failed to load model:', error);
      throw error;
    }
  }

  /**
   * Handle audio stream for lip sync
   * @param {Object} data - Audio data with volume
   */
  _handleAudioStream(data) {
    if (data.volume !== undefined) {
      this.lipSync.setTarget(data.volume);
    }
  }

  /**
   * Handle window resize
   */
  _handleResize() {
    this.pixiApp.handleResize();
    this.modelLoader.handleResize();
  }

  /**
   * Set expression (public API)
   * @param {string} expressionName
   */
  setExpression(expressionName) {
    this.expressionController.setExpression(expressionName);
  }

  /**
   * Play motion (public API)
   * @param {string} group
   * @param {number} index
   */
  playMotion(group, index) {
    this.expressionController.playMotion(group, index);
  }

  /**
   * Set mouth openness (public API)
   * @param {number} value
   */
  setMouthOpen(value) {
    this.lipSync.setTarget(value);
  }

  /**
   * Execute action (public API)
   * @param {Object} action
   */
  executeAction(action) {
    this.actionExecutor.execute(action);
  }

  /**
   * Get model bounds (public API)
   */
  getBounds() {
    return this.modelLoader.getBounds();
  }

  /**
   * Show error message
   * @param {string} message
   */
  _showError(message) {
    const existing = this.container.querySelector('.error');
    if (existing) existing.remove();

    const error = document.createElement('div');
    error.className = 'error';
    error.textContent = message;
    this.container.appendChild(error);
  }

  /**
   * Destroy renderer and cleanup
   */
  destroy() {
    // Cleanup IPC listeners
    if (this.ipc) {
      this.ipc.cleanup();
    }

    // Cleanup lip sync
    if (this.lipSync) {
      this.lipSync.destroy();
    }

    // Remove resize listener
    window.removeEventListener('resize', this._handleResize);

    // Cleanup model
    if (this.modelLoader) {
      this.modelLoader.unload();
    }

    // Cleanup PIXI
    if (this.pixiApp) {
      this.pixiApp.destroy();
    }

    // Remove global reference
    if (window.live2dRenderer === this) {
      delete window.live2dRenderer;
    }

    console.log('[Live2DRenderer] Destroyed');
  }
}
