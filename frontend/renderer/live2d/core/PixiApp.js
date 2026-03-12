/**
 * PixiApp - PIXI.Application initialization and resize handling
 */

export class PixiApp {
  constructor(canvas, container) {
    this.canvas = canvas;
    this.container = container;
    this.app = null;
  }

  /**
   * Create PIXI application
   * @returns {Promise<PIXI.Application>}
   */
  async create() {
    if (!this.canvas) {
      throw new Error('Canvas element not found');
    }
    if (!this.container) {
      throw new Error('Container element not found');
    }

    console.log('[PixiApp] PIXI version:', PIXI.VERSION);

    if (!PIXI.live2d) {
      throw new Error('pixi-live2d-display not loaded');
    }

    this.app = new PIXI.Application({
      view: this.canvas,
      width: this.container.clientWidth || 400,
      height: this.container.clientHeight || 600,
      transparent: true,
      autoDensity: true,
      resolution: window.devicePixelRatio || 1,
      antialias: true,
      backgroundAlpha: 0,
      preserveDrawingBuffer: true,
    });

    console.log('[PixiApp] Canvas size:', this.app.screen.width, 'x', this.app.screen.height);
    return this.app;
  }

  /**
   * Handle window resize
   */
  handleResize() {
    if (!this.app) return;

    this.app.renderer.resize(
      this.container.clientWidth,
      this.container.clientHeight
    );
  }

  /**
   * Get screen dimensions
   */
  getScreenSize() {
    if (!this.app) return { width: 0, height: 0 };
    return {
      width: this.app.screen.width,
      height: this.app.screen.height,
    };
  }

  /**
   * Destroy application
   */
  destroy() {
    if (this.app) {
      this.app.destroy(true);
      this.app = null;
    }
  }
}
