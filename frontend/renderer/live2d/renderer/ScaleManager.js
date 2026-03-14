/**
 * ScaleManager - 缩放管理 (含 bounds 分析)
 */

const STRATEGIES = {
  fit: { anchor: [0.5, 0.5], yRatio: 0.5 },
  contain: { anchor: [0.5, 1.0], yRatio: 1.0 },
  cover: { anchor: [0.5, 0.5], yRatio: 0.5 }
};

export class ScaleManager {
  constructor(app, modelLoader) {
    this.app = app;
    this.modelLoader = modelLoader;
    this.strategy = 'contain';
    this.userScale = 1.0;
    this.minScale = 0.1;
    this.maxScale = 3.0;
    this.scaleStep = 0.1;
    this.onScaleChange = null;
  }

  setStrategy(s) {
    if (!STRATEGIES[s]) return;
    this.strategy = s;
    this.apply();
  }

  getStrategy() { return this.strategy; }

  zoom(delta) {
    this.setUserScale(this.userScale + delta * this.scaleStep);
  }

  setUserScale(scale) {
    this.userScale = Math.max(this.minScale, Math.min(this.maxScale, scale));
    this.apply();
  }

  reset() {
    this.userScale = 1.0;
    this.apply();
  }

  apply() {
    const model = this.modelLoader?.model;
    if (!model) return;

    const canvas = { width: this.app.screen.width, height: this.app.screen.height };
    const bounds = model.getBounds();
    if (!bounds?.width) return;

    const scales = {
      fit: Math.min(canvas.width / bounds.width, canvas.height / bounds.height),
      contain: canvas.height / bounds.height,
      cover: Math.max(canvas.width / bounds.width, canvas.height / bounds.height)
    };

    const scale = (scales[this.strategy] || scales.fit) * this.userScale;
    model.scale.set(scale);

    const cfg = STRATEGIES[this.strategy];
    model.anchor.set(cfg.anchor[0], cfg.anchor[1]);
    model.x = canvas.width / 2;
    model.y = cfg.yRatio === 1.0 ? canvas.height : canvas.height / 2;

    this.onScaleChange?.(this.getState());
  }

  handleResize() { this.apply(); }

  async onModelLoaded(model) {
    if (!model) return;
    await new Promise(resolve => {
      const check = () => {
        const b = model.getBounds();
        if (b?.width > 0) return resolve();
        requestAnimationFrame(check);
      };
      check();
    });
    this.apply();
  }

  moveModel(dx, dy) {
    const model = this.modelLoader?.model;
    if (!model) return;
    model.x += dx;
    model.y += dy;
    this.onScaleChange?.(this.getState());
  }

  resetModelPosition() { this.apply(); }

  getState() {
    return { strategy: this.strategy, userScale: this.userScale };
  }

  getModelInfo() {
    const model = this.modelLoader?.model;
    if (!model) return null;
    return {
      strategy: this.strategy,
      userScale: this.userScale.toFixed(2),
      position: `(${model.x.toFixed(0)}, ${model.y.toFixed(0)})`,
      canvas: `${this.app.screen.width}x${this.app.screen.height}`
    };
  }
}
