/**
 * Live2D Renderer
 * Handles Live2D model loading, rendering, and interaction
 */

// Wait for all scripts to load
function waitForLibs() {
  return new Promise((resolve, reject) => {
    const check = () => {
      if (typeof PIXI !== 'undefined' && PIXI.live2d && PIXI.live2d.Live2DModel) {
        resolve();
      } else {
        setTimeout(check, 100);
      }
    };
    check();

    // Timeout after 10 seconds
    setTimeout(() => {
      if (typeof PIXI === 'undefined') {
        reject(new Error('PIXI.js failed to load'));
      } else if (!PIXI.live2d) {
        reject(new Error('pixi-live2d-display failed to load'));
      } else {
        reject(new Error('Unknown library loading error'));
      }
    }, 10000);
  });
}

class Live2DRenderer {
  constructor() {
    this.app = null;
    this.model = null;
    this.modelPath = null;
    this.canvas = document.getElementById('live2d-canvas');
    this.container = document.getElementById('live2d-container');
    this.isLoaded = false;

    // Lip sync state
    this.mouthOpenValue = 0;
    this.targetMouthOpen = 0;

    // Bind methods
    this._init = this._init.bind(this);
    this._animate = this._animate.bind(this);

    // Wait for libraries then initialize
    waitForLibs()
      .then(() => {
        console.log('[Live2DRenderer] Libraries loaded');
        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', this._init);
        } else {
          this._init();
        }
      })
      .catch((error) => {
        console.error('[Live2DRenderer] Failed to load libraries:', error);
        this._showError(`Failed to load libraries: ${error.message}`);
      });
  }

  /**
   * Initialize PIXI application
   * @private
   */
  async _init() {
    try {
      console.log('[Live2DRenderer] Initializing...');

      // Check canvas and container exist
      if (!this.canvas) {
        throw new Error('Canvas element not found');
      }
      if (!this.container) {
        throw new Error('Container element not found');
      }

      // Log PIXI version
      console.log('[Live2DRenderer] PIXI version:', PIXI.VERSION);

      // Check if pixi-live2d-display is available
      if (!PIXI.live2d) {
        throw new Error('pixi-live2d-display not loaded');
      }
      console.log('[Live2DRenderer] pixi-live2d-display loaded');

      // Create PIXI application
      this.app = new PIXI.Application({
        view: this.canvas,
        width: this.container.clientWidth || 400,
        height: this.container.clientHeight || 600,
        transparent: true,
        autoDensity: true,
        resolution: window.devicePixelRatio || 1,
        antialias: true,
        backgroundAlpha: 0,
        preserveDrawingBuffer: true // For transparency
      });

      console.log('[Live2DRenderer] PIXI.Application created');
      console.log('[Live2DRenderer] Canvas size:', this.app.screen.width, 'x', this.app.screen.height);

      // Handle resize
      window.addEventListener('resize', () => this._onResize());

      // Setup IPC listeners for backend messages
      this._setupIpcListeners();

      // Start animation loop
      this._animate();

      // Expose globally for IPC calls
      window.live2dRenderer = this;

      console.log('[Live2DRenderer] Initialized successfully');

      // Load default model if configured
      this._loadDefaultModel();
    } catch (error) {
      console.error('[Live2DRenderer] Initialization failed:', error);
      this._showError(`Failed to initialize: ${error.message}`);
    }
  }

  /**
   * Setup IPC listeners
   * @private
   */
  _setupIpcListeners() {
    if (window.electronAPI && window.electronAPI.live2d) {
      // Listen for actions from backend
      window.electronAPI.live2d.onAction((action) => {
        this._executeAction(action);
      });

      // Listen for audio stream (lip sync)
      window.electronAPI.live2d.onAudioStream((data) => {
        this._handleAudioStream(data);
      });

      console.log('[Live2DRenderer] IPC listeners setup');
    }
  }

  /**
   * Load default model
   * @private
   */
  async _loadDefaultModel() {
    // Fallback model path if config is not available
    const fallbackPath = '../../public/live2d/haru/haru_greeter_t03.model3.json';

    try {
      let modelPath = null;

      // Try to get from config
      if (window.electronAPI && window.electronAPI.getConfig) {
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
   * @param {string} modelPath - Path to Live2D model (.json)
   */
  async loadModel(modelPath) {
    try {
      console.log('[Live2DRenderer] Loading model:', modelPath);

      // Remove existing model
      if (this.model) {
        this.app.stage.removeChild(this.model);
        this.model.destroy();
        this.model = null;
      }

      // Show loading
      this._showLoading();

      // Resolve path for Electron file:// protocol
      // If it's a relative path, it will be resolved from the HTML file's directory
      let resolvedPath = modelPath;

      // Check if path is a URL or absolute path (Windows: C:\, Unix: /)
      const isAbsoluteOrUrl =
        modelPath.startsWith('file://') ||
        modelPath.startsWith('http://') ||
        modelPath.startsWith('https://') ||
        /^[A-Za-z]:/.test(modelPath) ||
        modelPath.startsWith('/');

      if (!isAbsoluteOrUrl) {
        // In Electron renderer, relative paths are resolved from the HTML location
        // The HTML is at renderer/live2d/live2d.html
        console.log('[Live2DRenderer] Using relative path from HTML location');
      }

      console.log('[Live2DRenderer] Resolved model path:', resolvedPath);

      // Load new model
      this.model = await PIXI.live2d.Live2DModel.from(resolvedPath);
      this.modelPath = modelPath;

      // Auto scale to fit
      this._autoScaleModel();

      // Center model
      this.model.x = this.app.screen.width / 2;
      this.model.y = this.app.screen.height / 2;

      // Add to stage
      this.app.stage.addChild(this.model);

      // Enable interaction
      this.model.interactive = true;
      this.model.on('pointertap', () => {
        console.log('[Live2DRenderer] Model tapped');
        this.playMotion('Tap', 0);
      });

      this.isLoaded = true;
      console.log('[Live2DRenderer] Model loaded successfully');

      // Hide loading indicator
      this._hideLoading();
    } catch (error) {
      console.error('[Live2DRenderer] Failed to load model:', error);
      this._showError(`Failed to load model: ${error.message}`);
    }
  }

  /**
   * Auto scale model to fit canvas
   * @private
   */
  _autoScaleModel() {
    if (!this.model) return;

    const canvasBounds = {
      width: this.app.screen.width,
      height: this.app.screen.height
    };

    const modelBounds = this.model.getBounds();
    const scaleX = canvasBounds.width / modelBounds.width;
    const scaleY = canvasBounds.height / modelBounds.height;
    const scale = Math.min(scaleX, scaleY, 1); // Don't upscale beyond 1

    this.model.scale.set(scale);
  }

  /**
   * Set expression by name
   * @param {string} expressionName - Expression name
   */
  setExpression(expressionName) {
    if (!this.model) return;

    const expressionIndex = this.model.internalModel.motionManager.expressionNames.indexOf(
      expressionName
    );

    if (expressionIndex >= 0) {
      this.model.expression(expressionIndex);
      console.log('[Live2DRenderer] Expression:', expressionName);
    } else {
      console.warn('[Live2DRenderer] Expression not found:', expressionName);
    }
  }

  /**
   * Play motion
   * @param {string} group - Motion group name
   * @param {number} index - Motion index within group
   */
  playMotion(group, index) {
    if (!this.model) return;

    this.model.motion(group, index);
    console.log('[Live2DRenderer] Motion:', group, index);
  }

  /**
   * Set model parameter
   * @param {string} paramName - Parameter name
   * @param {number} value - Parameter value
   */
  setParam(paramName, value) {
    if (!this.model) return;

    const paramIndex = this.model.internalModel.coreModel.getParameterIndex(paramName);
    if (paramIndex >= 0) {
      this.model.internalModel.coreModel.setParameterValueByIndex(paramIndex, value);
    }
  }

  /**
   * Set mouth openness for lip sync
   * @param {number} value - Mouth openness (0-1)
   */
  setMouthOpen(value) {
    this.targetMouthOpen = Math.max(0, Math.min(1, value));
  }

  /**
   * Execute action from preset
   * @param {Object} action - Action object
   * @private
   */
  _executeAction(action) {
    console.log('[Live2DRenderer] Executing action:', action);

    switch (action.type) {
      case 'expression':
        if (action.name) {
          this.setExpression(action.name);
        }
        break;

      case 'motion':
        if (action.group && action.index !== undefined) {
          this.playMotion(action.group, action.index);
        }
        break;

      case 'param':
        if (action.name && action.value !== undefined) {
          this.setParam(action.name, action.value);
        }
        break;

      case 'sequence':
        if (Array.isArray(action.actions)) {
          this._executeSequence(action.actions);
        }
        break;

      default:
        console.warn('[Live2DRenderer] Unknown action type:', action.type);
    }
  }

  /**
   * Execute sequence of actions
   * @param {Array} actions - Array of action objects
   * @private
   */
  _executeSequence(actions) {
    let delay = 0;

    actions.forEach((action) => {
      if (action.type === 'wait') {
        delay += action.ms || 0;
      } else {
        setTimeout(() => {
          this._executeAction(action);
        }, delay);
        delay += 250; // Default delay between actions
      }
    });
  }

  /**
   * Handle audio stream for lip sync
   * @param {Object} data - Audio data
   * @private
   */
  _handleAudioStream(data) {
    // TODO: Implement viseme-based lip sync
    // For now, simple RMS-based
    if (data.volume !== undefined) {
      this.setMouthOpen(data.volume);
    }
  }

  /**
   * Animation loop
   * @private
   */
  _animate() {
    requestAnimationFrame(this._animate);

    // Smooth mouth transition
    if (this.model) {
      const smoothing = 0.3;
      this.mouthOpenValue +=
        (this.targetMouthOpen - this.mouthOpenValue) * smoothing;

      // Update mouth parameters - try multiple common Live2D mouth param names
      // Different models use different parameter names
      const mouthParams = ['ParamMouthOpenY', 'ParamMouthOpen', 'PARAM_MOUTH_OPEN'];
      for (const paramName of mouthParams) {
        this.setParam(paramName, this.mouthOpenValue);
      }
      // Also try mouth form for shape
      this.setParam('ParamMouthForm', this.mouthOpenValue * 0.5);
    }

    // Update PIXI
    if (this.app) {
      // Delta time is handled by PIXI ticker
    }
  }

  /**
   * Handle window resize
   * @private
   */
  _onResize() {
    if (!this.app) return;

    this.app.renderer.resize(
      this.container.clientWidth,
      this.container.clientHeight
    );

    if (this.model) {
      this.model.x = this.app.screen.width / 2;
      this.model.y = this.app.screen.height / 2;
      this._autoScaleModel();
    }
  }

  /**
   * Get model bounds
   * @returns {Object|null} Model bounds
   */
  getBounds() {
    if (!this.model) return null;
    return this.model.getBounds();
  }

  /**
   * Show loading indicator
   * @private
   */
  _showLoading() {
    this._hideLoading(); // Remove existing
    const loading = document.createElement('div');
    loading.className = 'loading';
    loading.textContent = 'Loading Live2D model...';
    loading.id = 'loading-indicator';
    this.container.appendChild(loading);
  }

  /**
   * Hide loading indicator
   * @private
   */
  _hideLoading() {
    const loading = document.getElementById('loading-indicator');
    if (loading) {
      loading.remove();
    }
  }

  /**
   * Show error message
   * @param {string} message - Error message
   * @private
   */
  _showError(message) {
    const existing = document.querySelector('.error');
    if (existing) existing.remove();

    const error = document.createElement('div');
    error.className = 'error';
    error.textContent = message;
    this.container.appendChild(error);
  }
}

// Initialize renderer
const renderer = new Live2DRenderer();

console.log('[Live2D] Renderer loaded');
