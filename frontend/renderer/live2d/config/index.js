/**
 * Config Module - 显示配置管理
 */

const DEFAULT_CONFIG = {
  scale: { strategy: 'contain', userScale: 1.0 },
  background: { mode: 'transparent' },
  window: { alwaysOnTop: true, clickThrough: false }
};

export class DisplayConfig {
  constructor() {
    this.config = this._deepClone(DEFAULT_CONFIG);
    this.loaded = false;
    this._listeners = [];
  }

  async load() {
    try {
      const saved = await this._loadFromStore();
      if (saved) {
        this.config = this._deepMerge(DEFAULT_CONFIG, saved);
        this.loaded = true;
      }
    } catch (e) { console.warn('[DisplayConfig] Load failed, using defaults'); }
    return this.config;
  }

  async save() {
    await this._saveToStore(this.config);
    localStorage.setItem('displayConfig', JSON.stringify(this.config));
    this._notify('save', this.config);
  }

  get(path) { return this._getByPath(this.config, path); }
  async set(path, value) {
    this._setByPath(this.config, path, value);
    await this.save();
    this._notify(path, value);
  }

  async updateMany(updates) {
    for (const [path, value] of Object.entries(updates)) {
      this._setByPath(this.config, path, value);
    }
    await this.save();
  }

  async reset() {
    this.config = this._deepClone(DEFAULT_CONFIG);
    await this.save();
  }

  getScaleConfig() { return { ...this.config.scale }; }
  getBackgroundConfig() { return { ...this.config.background }; }
  getWindowConfig() { return { ...this.config.window }; }

  onChange(callback) {
    this._listeners.push(callback);
    return () => {
      const idx = this._listeners.indexOf(callback);
      if (idx > -1) this._listeners.splice(idx, 1);
    };
  }

  _notify(path, value) {
    for (const listener of this._listeners) {
      try { listener(path, value); } catch {}
    }
  }

  async _loadFromStore() {
    if (window.electronAPI?.display?.getConfig) {
      return await window.electronAPI.display.getConfig();
    }
    try {
      const saved = localStorage.getItem('displayConfig');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  }

  async _saveToStore(config) {
    if (window.electronAPI?.display?.saveConfig) {
      await window.electronAPI.display.saveConfig(config);
    }
  }

  _deepClone(obj) { return JSON.parse(JSON.stringify(obj)); }
  _deepMerge(target, source) {
    const output = { ...target };
    for (const key in source) {
      if (source[key] instanceof Object && key in target) {
        output[key] = this._deepMerge(target[key], source[key]);
      } else {
        output[key] = source[key];
      }
    }
    return output;
  }
  _getByPath(obj, path) { return path?.split('.').reduce((o, k) => o?.[k], obj); }
  _setByPath(obj, path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((o, k) => { if (!(k in o)) o[k] = {}; return o[k]; }, obj);
    target[lastKey] = value;
  }
}
