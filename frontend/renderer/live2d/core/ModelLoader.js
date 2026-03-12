/**
 * ModelLoader - Live2D model loading, unloading, and scaling
 */

export class ModelLoader {
  constructor(app, container) {
    this.app = app;
    this.container = container;
    this.model = null;
    this.modelPath = null;
  }

  /**
   * Load Live2D model
   * @param {string} modelPath - Path to model file
   * @returns {Promise<PIXI.live2d.Live2DModel>}
   */
  async load(modelPath) {
    console.log('[ModelLoader] Loading model:', modelPath);

    // Remove existing model
    this.unload();

    // Show loading indicator
    this._showLoading();

    try {
      // Load new model
      this.model = await PIXI.live2d.Live2DModel.from(modelPath);
      this.modelPath = modelPath;

      // Auto scale and center
      this._autoScale();
      this._center();

      // Add to stage
      this.app.stage.addChild(this.model);

      // Enable interaction
      this.model.interactive = true;

      this._hideLoading();
      console.log('[ModelLoader] Model loaded successfully');

      return this.model;
    } catch (error) {
      this._hideLoading();
      this._showError(`Failed to load model: ${error.message}`);
      throw error;
    }
  }

  /**
   * Unload current model
   */
  unload() {
    if (this.model) {
      this.app.stage.removeChild(this.model);
      this.model.destroy();
      this.model = null;
      this.modelPath = null;
    }
  }

  /**
   * Center model in canvas
   */
  _center() {
    if (!this.model) return;

    this.model.x = this.app.screen.width / 2;
    this.model.y = this.app.screen.height / 2;
  }

  /**
   * Auto scale model to fit canvas
   */
  _autoScale() {
    if (!this.model) return;

    const canvasBounds = {
      width: this.app.screen.width,
      height: this.app.screen.height,
    };

    const modelBounds = this.model.getBounds();
    const scaleX = canvasBounds.width / modelBounds.width;
    const scaleY = canvasBounds.height / modelBounds.height;
    const scale = Math.min(scaleX, scaleY, 1); // Don't upscale beyond 1

    this.model.scale.set(scale);
  }

  /**
   * Recenter and rescale after resize
   */
  handleResize() {
    if (this.model) {
      this._center();
      this._autoScale();
    }
  }

  /**
   * Get model bounds
   */
  getBounds() {
    if (!this.model) return null;
    return this.model.getBounds();
  }

  /**
   * Show loading indicator
   */
  _showLoading() {
    this._hideLoading();
    const loading = document.createElement('div');
    loading.className = 'loading';
    loading.textContent = 'Loading Live2D model...';
    loading.id = 'loading-indicator';
    this.container.appendChild(loading);
  }

  /**
   * Hide loading indicator
   */
  _hideLoading() {
    const loading = document.getElementById('loading-indicator');
    if (loading) {
      loading.remove();
    }
  }

  /**
   * Show error message
   */
  _showError(message) {
    const existing = this.container.querySelector('.error');
    if (existing) existing.remove();

    const error = document.createElement('div');
    error.className = 'error';
    error.textContent = message;
    this.container.appendChild(error);
  }
}
