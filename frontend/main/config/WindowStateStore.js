/**
 * WindowStateStore - 窗口状态持久化存储
 *
 * 使用 electron-store 保存窗口状态，包括:
 * - 窗口位置和大小
 * - 置顶状态
 * - 点击穿透状态
 */

const Store = require('electron-store');

// 存储 schema
const schema = {
  live2dWindow: {
    type: 'object',
    properties: {
      x: { type: 'number' },
      y: { type: 'number' },
      width: { type: 'number', default: 400 },
      height: { type: 'number', default: 600 },
      alwaysOnTop: { type: 'boolean', default: true },
      clickThrough: { type: 'boolean', default: false },
    },
    default: {
      width: 400,
      height: 600,
      alwaysOnTop: true,
      clickThrough: false,
    },
  },
  displayConfig: {
    type: 'object',
    properties: {
      scale: {
        type: 'object',
        properties: {
          strategy: { type: 'string', default: 'contain' },
          userScale: { type: 'number', default: 1.0 },
          moveStep: { type: 'number', default: 15 },
        },
      },
      background: {
        type: 'object',
        properties: {
          mode: { type: 'string', default: 'transparent' },
          color: { type: 'string', default: '#00ff00' },
          colorOpacity: { type: 'number', default: 1.0 },
          imagePath: { type: ['string', 'null'] },
          videoPath: { type: ['string', 'null'] },
        },
      },
      hotkeys: { type: ['object', 'null'] },
      overlay: {
        type: 'object',
        properties: {
          autoHide: { type: 'boolean', default: true },
          autoHideDelay: { type: 'number', default: 3000 },
        },
      },
    },
    default: {},
  },
};

class WindowStateStore {
  constructor() {
    this.store = new Store({
      name: 'display-state',
      schema,
      // 每 1 秒自动保存一次 (防抖)
      debounce: 1000,
    });

    console.log('[WindowStateStore] Initialized, file:', this.store.path);
  }

  // ==================== 窗口状态 ====================

  /**
   * 获取 Live2D 窗口状态
   */
  getLive2DWindowState() {
    return this.store.get('live2dWindow');
  }

  /**
   * 保存 Live2D 窗口状态
   * @param {Object} state
   */
  saveLive2DWindowState(state) {
    const current = this.getLive2DWindowState();
    this.store.set('live2dWindow', { ...current, ...state });
  }

  /**
   * 更新窗口位置
   */
  updateWindowPosition(x, y) {
    this.store.set('live2dWindow.x', x);
    this.store.set('live2dWindow.y', y);
  }

  /**
   * 更新窗口大小
   */
  updateWindowSize(width, height) {
    this.store.set('live2dWindow.width', width);
    this.store.set('live2dWindow.height', height);
  }

  /**
   * 更新置顶状态
   */
  updateAlwaysOnTop(value) {
    this.store.set('live2dWindow.alwaysOnTop', value);
  }

  /**
   * 更新点击穿透状态
   */
  updateClickThrough(value) {
    this.store.set('live2dWindow.clickThrough', value);
  }

  // ==================== 显示配置 ====================

  /**
   * 获取显示配置
   */
  getDisplayConfig() {
    return this.store.get('displayConfig');
  }

  /**
   * 保存显示配置
   * @param {Object} config
   */
  saveDisplayConfig(config) {
    this.store.set('displayConfig', config);
  }

  /**
   * 获取缩放配置
   */
  getScaleConfig() {
    return this.store.get('displayConfig.scale');
  }

  /**
   * 保存缩放配置
   */
  saveScaleConfig(scaleConfig) {
    this.store.set('displayConfig.scale', scaleConfig);
  }

  /**
   * 获取背景配置
   */
  getBackgroundConfig() {
    return this.store.get('displayConfig.background');
  }

  /**
   * 保存背景配置
   */
  saveBackgroundConfig(backgroundConfig) {
    this.store.set('displayConfig.background', backgroundConfig);
  }

  /**
   * 获取快捷键配置
   */
  getHotkeyConfig() {
    return this.store.get('displayConfig.hotkeys');
  }

  /**
   * 保存快捷键配置
   */
  saveHotkeyConfig(hotkeyConfig) {
    this.store.set('displayConfig.hotkeys', hotkeyConfig);
  }

  // ==================== 通用方法 ====================

  /**
   * 获取所有数据
   */
  getAll() {
    return this.store.store;
  }

  /**
   * 清除所有数据
   */
  clear() {
    this.store.clear();
    console.log('[WindowStateStore] All data cleared');
  }

  /**
   * 重置为默认值
   */
  reset() {
    this.store.clear();
    console.log('[WindowStateStore] Reset to defaults');
  }

  /**
   * 获取存储路径
   */
  getPath() {
    return this.store.path;
  }

  /**
   * 导出配置 (JSON)
   */
  exportConfig() {
    return JSON.stringify(this.store.store, null, 2);
  }

  /**
   * 导入配置
   * @param {string} json
   */
  importConfig(json) {
    try {
      const data = JSON.parse(json);
      for (const [key, value] of Object.entries(data)) {
        this.store.set(key, value);
      }
      console.log('[WindowStateStore] Config imported');
      return { success: true };
    } catch (error) {
      console.error('[WindowStateStore] Import failed:', error);
      return { success: false, error: error.message };
    }
  }
}

// 单例
let instance = null;

/**
 * 获取 WindowStateStore 单例
 */
function getWindowStateStore() {
  if (!instance) {
    instance = new WindowStateStore();
  }
  return instance;
}

module.exports = {
  WindowStateStore,
  getWindowStateStore,
};
