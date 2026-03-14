/**
 * BackgroundManager - 背景管理
 */

export class BackgroundManager {
  constructor(app, container) {
    this.app = app;
    this.container = container;
    this.mode = 'transparent';
    this.config = {};
    this.graphics = null;
    this.onBackgroundChange = null;
  }

  async setMode(mode, options = {}) {
    this.mode = mode;
    this.config = options;

    switch (mode) {
      case 'transparent':
        this.container.style.background = 'transparent';
        if (this.graphics) { this.graphics.destroy(); this.graphics = null; }
        break;

      case 'color':
        this.container.style.background = options.color || '#000000';
        break;

      case 'image':
        await this._loadImage(options.imagePath);
        break;

      case 'video':
        await this._loadVideo(options.videoPath);
        break;
    }

    this.onBackgroundChange?.(this.getState());
  }

  async _loadImage(path) {
    // TODO: 实现图片背景
  }

  async _loadVideo(path) {
    // TODO: 实现视频背景
  }

  getMode() { return this.mode; }
  getState() { return { mode: this.mode, config: this.config }; }

  handleResize() {}

  destroy() {
    if (this.graphics) this.graphics.destroy();
  }
}
