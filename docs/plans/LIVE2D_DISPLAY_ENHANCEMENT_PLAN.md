# Live2D 全身展示与界面调整 - 实现计划

**优先级**: P1 (高)
**版本**: 1.0
**创建日期**: 2026-03-14

---

## 1. 项目概述

### 1.1 目标
为B站直播和日常使用提供完整的Live2D全身展示解决方案，支持多种背景模式、灵活的窗口控制和OBS集成。

### 1.2 核心功能
- 全身模型适配与缩放策略
- 多种背景模式（透明/纯色/图片/视频）
- 快捷键系统
- 窗口置顶与OBS集成

### 1.3 当前状态
```
frontend/renderer/live2d/
├── core/
│   ├── PixiApp.js          # PIXI应用初始化 (透明背景)
│   ├── ModelLoader.js      # 模型加载 (基础自动缩放)
│   └── LibLoader.js        # 库加载
├── animation/
│   ├── LipSync.js          # 口型同步
│   ├── ExpressionController.js
│   └── ActionExecutor.js
├── audio/
│   └── AudioWithExpression.js
├── ipc/
│   └── Live2DIpcListeners.js
├── Live2DRenderer.js       # 主控制器
├── live2d.html
└── live2d.css              # 样式 (仅透明背景)
```

---

## 2. 架构设计

### 2.1 新增模块结构

```
frontend/renderer/live2d/
├── core/
│   ├── PixiApp.js              # [修改] 支持背景模式
│   ├── ModelLoader.js          # [修改] 缩放策略
│   ├── LibLoader.js
│   └── SceneManager.js         # [新增] 场景管理
├── display/
│   ├── ScaleManager.js         # [新增] 缩放策略管理
│   ├── BackgroundManager.js    # [新增] 背景系统
│   └── ModelBoundsAnalyzer.js  # [新增] 模型边界分析
├── control/
│   ├── HotkeyManager.js        # [新增] 快捷键系统
│   └── WindowController.js     # [新增] 窗口控制
├── config/
│   ├── DisplayConfig.js        # [新增] 显示配置
│   └── default-display.json    # [新增] 默认配置
├── ipc/
│   ├── Live2DIpcListeners.js   # [修改] 新增IPC命令
│   └── DisplayIpcHandlers.js   # [新增] 显示相关IPC
├── ui/
│   ├── ControlOverlay.js       # [新增] 控制面板UI
│   └── SettingsPanel.js        # [新增] 设置面板
├── Live2DRenderer.js           # [修改] 集成新模块
├── live2d.html
└── live2d.css                  # [修改] 新增样式
```

### 2.2 主进程新增

```
frontend/main/
├── windows/
│   ├── Live2DWindow.js         # [修改] 窗口控制增强
│   └── WindowManager.js        # [修改] 窗口状态持久化
├── ipc/
│   └── handlers/
│       └── display.js          # [新增] 显示相关IPC处理
└── config/
    └── WindowStateStore.js     # [新增] 窗口状态存储
```

---

## 3. 详细实现

### 3.1 缩放策略系统

**文件**: `frontend/renderer/live2d/display/ScaleManager.js`

```javascript
/**
 * ScaleManager - 模型缩放策略管理
 *
 * 策略模式:
 * - fit:    完整显示，保持比例，可能有留白
 * - contain: 填满容器，保持比例，可能裁切
 * - cover:  填满容器，可能变形 (不推荐)
 */

export class ScaleManager {
  constructor(app, modelLoader) {
    this.app = app;
    this.modelLoader = modelLoader;
    this.strategy = 'fit';  // fit | contain | cover
    this.scale = 1.0;
    this.minScale = 0.1;
    this.maxScale = 3.0;
    this.scaleStep = 0.1;
  }

  /**
   * 设置缩放策略
   * @param {'fit'|'contain'|'cover'} strategy
   */
  setStrategy(strategy) {
    this.strategy = strategy;
    this.applyScale();
  }

  /**
   * 缩放模型
   * @param {number} delta - 缩放增量 (-1, 1)
   */
  zoom(delta) {
    this.scale = Math.max(
      this.minScale,
      Math.min(this.maxScale, this.scale + delta * this.scaleStep)
    );
    this.applyScale();
  }

  /**
   * 重置缩放
   */
  reset() {
    this.scale = 1.0;
    this.applyScale();
  }

  /**
   * 应用缩放
   */
  applyScale() {
    const model = this.modelLoader.model;
    if (!model) return;

    const canvas = this.app.screen;
    const bounds = model.getBounds();

    let baseScale;
    switch (this.strategy) {
      case 'fit':
        // 完整显示，保持比例
        baseScale = Math.min(
          canvas.width / bounds.width,
          canvas.height / bounds.height
        );
        break;

      case 'contain':
        // 填满高度，保持比例 (适合全身模型)
        baseScale = canvas.height / bounds.height;
        break;

      case 'cover':
        // 填满容器，可能裁切
        baseScale = Math.max(
          canvas.width / bounds.width,
          canvas.height / bounds.height
        );
        break;
    }

    model.scale.set(baseScale * this.scale);
    this._centerModel();
  }

  _centerModel() {
    const model = this.modelLoader.model;
    if (!model) return;

    // 根据策略调整锚点位置
    if (this.strategy === 'contain') {
      // 全身模型：底部居中
      model.anchor.set(0.5, 1.0);
      model.x = this.app.screen.width / 2;
      model.y = this.app.screen.height;
    } else {
      // 其他策略：中心对齐
      model.anchor.set(0.5, 0.5);
      model.x = this.app.screen.width / 2;
      model.y = this.app.screen.height / 2;
    }
  }

  /**
   * 获取当前状态
   */
  getState() {
    return {
      strategy: this.strategy,
      scale: this.scale,
      minScale: this.minScale,
      maxScale: this.maxScale,
    };
  }
}
```

### 3.2 背景系统

**文件**: `frontend/renderer/live2d/display/BackgroundManager.js`

```javascript
/**
 * BackgroundManager - 背景管理
 *
 * 支持模式:
 * - transparent: 透明背景 (默认，OBS绿幕)
 * - color:       纯色背景
 * - image:       图片背景
 * - video:       视频背景
 */

export class BackgroundManager {
  constructor(app, container) {
    this.app = app;
    this.container = container;
    this.mode = 'transparent';
    this.background = null;
    this.config = {
      color: '#00ff00',      // 绿幕色
      image: null,           // 图片路径
      video: null,           // 视频路径
      opacity: 1.0,          // 背景透明度
    };
  }

  /**
   * 设置背景模式
   * @param {'transparent'|'color'|'image'|'video'} mode
   * @param {Object} options
   */
  async setMode(mode, options = {}) {
    this.mode = mode;
    Object.assign(this.config, options);

    // 清除现有背景
    this._clearBackground();

    switch (mode) {
      case 'transparent':
        this._setTransparent();
        break;
      case 'color':
        this._setColor(this.config.color);
        break;
      case 'image':
        await this._setImage(this.config.image);
        break;
      case 'video':
        await this._setVideo(this.config.video);
        break;
    }

    this._saveConfig();
  }

  _setTransparent() {
    this.app.renderer.backgroundAlpha = 0;
    this.container.style.background = 'transparent';
  }

  _setColor(color) {
    this.app.renderer.backgroundAlpha = this.config.opacity;
    // 转换hex为number
    const colorNum = parseInt(color.replace('#', ''), 16);
    this.app.renderer.backgroundColor = colorNum;
  }

  async _setImage(imagePath) {
    if (!imagePath) return;

    const texture = await PIXI.Texture.from(imagePath);
    this.background = new PIXI.TilingSprite(texture, this.app.screen.width, this.app.screen.height);
    this.background.alpha = this.config.opacity;
    this.app.stage.addChildAt(this.background, 0);
  }

  async _setVideo(videoPath) {
    if (!videoPath) return;

    const video = document.createElement('video');
    video.src = videoPath;
    video.loop = true;
    video.muted = true;
    video.autoplay = true;

    await video.play();

    const texture = PIXI.Texture.from(video);
    this.background = new PIXI.Sprite(texture);
    this.background.alpha = this.config.opacity;
    this.background.width = this.app.screen.width;
    this.background.height = this.app.screen.height;
    this.app.stage.addChildAt(this.background, 0);

    // 视频循环更新
    this._videoUpdateTicker = () => {
      texture.update();
    };
    this.app.ticker.add(this._videoUpdateTicker);
  }

  _clearBackground() {
    if (this.background) {
      this.app.stage.removeChild(this.background);
      this.background.destroy();
      this.background = null;
    }
    if (this._videoUpdateTicker) {
      this.app.ticker.remove(this._videoUpdateTicker);
      this._videoUpdateTicker = null;
    }
  }

  /**
   * 设置透明度
   * @param {number} opacity - 0.0 ~ 1.0
   */
  setOpacity(opacity) {
    this.config.opacity = opacity;
    if (this.background) {
      this.background.alpha = opacity;
    }
    if (this.mode === 'color') {
      this.app.renderer.backgroundAlpha = opacity;
    }
  }

  /**
   * 处理窗口缩放
   */
  handleResize() {
    if (this.background && this.background instanceof PIXI.TilingSprite) {
      this.background.width = this.app.screen.width;
      this.background.height = this.app.screen.height;
    }
    if (this.background && this.background instanceof PIXI.Sprite) {
      this.background.width = this.app.screen.width;
      this.background.height = this.app.screen.height;
    }
  }

  async _saveConfig() {
    // 通过IPC保存配置
    if (window.electronAPI?.saveDisplayConfig) {
      await window.electronAPI.saveDisplayConfig({
        background: {
          mode: this.mode,
          ...this.config,
        },
      });
    }
  }

  getState() {
    return {
      mode: this.mode,
      ...this.config,
    };
  }
}
```

### 3.3 快捷键系统

**文件**: `frontend/renderer/live2d/control/HotkeyManager.js`

```javascript
/**
 * HotkeyManager - 快捷键管理
 */

const DEFAULT_HOTKEYS = {
  // 位置移动
  moveUp: { key: 'ArrowUp', modifiers: [], description: '向上移动' },
  moveDown: { key: 'ArrowDown', modifiers: [], description: '向下移动' },
  moveLeft: { key: 'ArrowLeft', modifiers: [], description: '向左移动' },
  moveRight: { key: 'ArrowRight', modifiers: [], description: '向右移动' },

  // WASD备选
  moveUpAlt: { key: 'w', modifiers: [], description: '向上移动 (WASD)' },
  moveDownAlt: { key: 's', modifiers: [], description: '向下移动 (WASD)' },
  moveLeftAlt: { key: 'a', modifiers: [], description: '向左移动 (WASD)' },
  moveRightAlt: { key: 'd', modifiers: [], description: '向右移动 (WASD)' },

  // 缩放
  zoomIn: { key: '=', modifiers: ['ctrl'], description: '放大 (Ctrl + =)' },
  zoomOut: { key: '-', modifiers: ['ctrl'], description: '缩小 (Ctrl + -)' },

  // 重置
  reset: { key: 'r', modifiers: ['ctrl'], description: '重置位置和缩放 (Ctrl + R)' },

  // 背景切换
  nextBackground: { key: 'b', modifiers: [], description: '切换背景模式 (B)' },

  // 窗口控制
  toggleAlwaysOnTop: { key: 't', modifiers: ['ctrl'], description: '切换置顶 (Ctrl + T)' },
  toggleClickThrough: { key: 'c', modifiers: ['ctrl', 'alt'], description: '切换点击穿透 (Ctrl + Alt + C)' },
};

export class HotkeyManager {
  constructor(options) {
    this.scaleManager = options.scaleManager;
    this.backgroundManager = options.backgroundManager;
    this.windowController = options.windowController;
    this.modelLoader = options.modelLoader;

    this.hotkeys = { ...DEFAULT_HOTKEYS };
    this.enabled = true;
    this.moveStep = 10; // 移动步长 (像素)

    this._handleKeyDown = this._handleKeyDown.bind(this);
    this._handleWheel = this._handleWheel.bind(this);
  }

  start() {
    document.addEventListener('keydown', this._handleKeyDown);
    document.addEventListener('wheel', this._handleWheel, { passive: false });
    console.log('[HotkeyManager] Started');
  }

  stop() {
    document.removeEventListener('keydown', this._handleKeyDown);
    document.removeEventListener('wheel', this._handleWheel);
    console.log('[HotkeyManager] Stopped');
  }

  _handleKeyDown(e) {
    if (!this.enabled) return;

    const hotkey = this._findHotkey(e);
    if (!hotkey) return;

    e.preventDefault();

    switch (hotkey) {
      // 移动
      case 'moveUp':
      case 'moveUpAlt':
        this._moveModel(0, -this.moveStep);
        break;
      case 'moveDown':
      case 'moveDownAlt':
        this._moveModel(0, this.moveStep);
        break;
      case 'moveLeft':
      case 'moveLeftAlt':
        this._moveModel(-this.moveStep, 0);
        break;
      case 'moveRight':
      case 'moveRightAlt':
        this._moveModel(this.moveStep, 0);
        break;

      // 缩放
      case 'zoomIn':
        this.scaleManager.zoom(1);
        break;
      case 'zoomOut':
        this.scaleManager.zoom(-1);
        break;

      // 重置
      case 'reset':
        this._resetAll();
        break;

      // 背景
      case 'nextBackground':
        this._cycleBackground();
        break;

      // 窗口
      case 'toggleAlwaysOnTop':
        this.windowController?.toggleAlwaysOnTop();
        break;
      case 'toggleClickThrough':
        this.windowController?.toggleClickThrough();
        break;
    }
  }

  _handleWheel(e) {
    if (!this.enabled) return;
    if (!e.ctrlKey) return;

    e.preventDefault();
    const delta = e.deltaY > 0 ? -1 : 1;
    this.scaleManager.zoom(delta);
  }

  _findHotkey(e) {
    for (const [name, config] of Object.entries(this.hotkeys)) {
      if (e.key.toLowerCase() === config.key.toLowerCase()) {
        const hasCtrl = config.modifiers.includes('ctrl');
        const hasAlt = config.modifiers.includes('alt');
        const hasShift = config.modifiers.includes('shift');

        if (e.ctrlKey === hasCtrl && e.altKey === hasAlt && e.shiftKey === hasShift) {
          return name;
        }
      }
    }
    return null;
  }

  _moveModel(dx, dy) {
    const model = this.modelLoader.model;
    if (!model) return;

    model.x += dx;
    model.y += dy;
  }

  _resetAll() {
    this.scaleManager.reset();
    this.modelLoader._center();
  }

  _cycleBackground() {
    const modes = ['transparent', 'color', 'image', 'video'];
    const currentIndex = modes.indexOf(this.backgroundManager.mode);
    const nextIndex = (currentIndex + 1) % modes.length;
    this.backgroundManager.setMode(modes[nextIndex]);
  }

  /**
   * 自定义快捷键
   */
  setHotkey(action, key, modifiers = []) {
    if (this.hotkeys[action]) {
      this.hotkeys[action] = { ...this.hotkeys[action], key, modifiers };
    }
  }

  /**
   * 获取所有快捷键配置
   */
  getHotkeys() {
    return { ...this.hotkeys };
  }
}
```

### 3.4 窗口控制器 (IPC桥接)

**文件**: `frontend/renderer/live2d/control/WindowController.js`

```javascript
/**
 * WindowController - 窗口控制 (通过IPC与主进程通信)
 */

export class WindowController {
  constructor() {
    this.alwaysOnTop = true;
    this.clickThrough = true;
  }

  /**
   * 切换窗口置顶
   */
  async toggleAlwaysOnTop() {
    this.alwaysOnTop = !this.alwaysOnTop;
    await window.electronAPI?.setAlwaysOnTop?.(this.alwaysOnTop);
    console.log('[WindowController] Always on top:', this.alwaysOnTop);
  }

  /**
   * 设置窗口置顶
   */
  async setAlwaysOnTop(value) {
    this.alwaysOnTop = value;
    await window.electronAPI?.setAlwaysOnTop?.(value);
  }

  /**
   * 切换点击穿透
   */
  async toggleClickThrough() {
    this.clickThrough = !this.clickThrough;
    await window.electronAPI?.setClickThrough?.(this.clickThrough);
    console.log('[WindowController] Click through:', this.clickThrough);
  }

  /**
   * 设置点击穿透
   */
  async setClickThrough(value) {
    this.clickThrough = value;
    await window.electronAPI?.setClickThrough?.(value);
  }

  /**
   * 移动窗口
   */
  async moveWindow(x, y) {
    await window.electronAPI?.moveWindow?.(x, y);
  }

  /**
   * 调整窗口大小
   */
  async resizeWindow(width, height) {
    await window.electronAPI?.resizeWindow?.(width, height);
  }

  /**
   * 获取窗口位置
   */
  async getWindowPosition() {
    return await window.electronAPI?.getWindowPosition?.() || { x: 0, y: 0 };
  }

  getState() {
    return {
      alwaysOnTop: this.alwaysOnTop,
      clickThrough: this.clickThrough,
    };
  }
}
```

### 3.5 显示配置

**文件**: `frontend/renderer/live2d/config/DisplayConfig.js`

```javascript
/**
 * DisplayConfig - 显示配置管理
 */

const DEFAULT_CONFIG = {
  scale: {
    strategy: 'contain',  // fit | contain | cover
    value: 1.0,
    minScale: 0.1,
    maxScale: 3.0,
  },
  background: {
    mode: 'transparent',
    color: '#00ff00',
    image: null,
    video: null,
    opacity: 1.0,
  },
  window: {
    alwaysOnTop: true,
    clickThrough: true,
    width: 400,
    height: 600,
    x: null,
    y: null,
  },
  hotkeys: null, // null = 使用默认
};

export class DisplayConfig {
  constructor() {
    this.config = { ...DEFAULT_CONFIG };
    this.loaded = false;
  }

  /**
   * 加载配置
   */
  async load() {
    try {
      const saved = await window.electronAPI?.getDisplayConfig?.();
      if (saved) {
        this.config = this._mergeDeep(DEFAULT_CONFIG, saved);
      }
      this.loaded = true;
      console.log('[DisplayConfig] Loaded:', this.config);
    } catch (error) {
      console.warn('[DisplayConfig] Load failed, using defaults:', error);
    }
    return this.config;
  }

  /**
   * 保存配置
   */
  async save() {
    try {
      await window.electronAPI?.saveDisplayConfig?.(this.config);
      console.log('[DisplayConfig] Saved');
    } catch (error) {
      console.error('[DisplayConfig] Save failed:', error);
    }
  }

  /**
   * 更新部分配置
   */
  async update(path, value) {
    this._setByPath(this.config, path, value);
    await this.save();
  }

  get(path = null) {
    if (!path) return this.config;
    return this._getByPath(this.config, path);
  }

  _getByPath(obj, path) {
    return path.split('.').reduce((o, k) => o?.[k], obj);
  }

  _setByPath(obj, path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((o, k) => o[k], obj);
    target[lastKey] = value;
  }

  _mergeDeep(target, source) {
    const output = { ...target };
    for (const key in source) {
      if (source[key] instanceof Object && key in target) {
        output[key] = this._mergeDeep(target[key], source[key]);
      } else {
        output[key] = source[key];
      }
    }
    return output;
  }
}
```

### 3.6 主进程 IPC 处理

**文件**: `frontend/main/ipc/handlers/display.js`

```javascript
/**
 * Display IPC Handlers - 显示相关IPC处理
 */

const { ipcMain, BrowserWindow } = require('electron');
const Store = require('electron-store');

const displayStore = new Store({ name: 'display-config' });

function registerDisplayHandlers() {
  // 获取显示配置
  ipcMain.handle('display:getConfig', () => {
    return displayStore.store;
  });

  // 保存显示配置
  ipcMain.handle('display:saveConfig', (event, config) => {
    displayStore.store = config;
    return true;
  });

  // 设置窗口置顶
  ipcMain.handle('display:setAlwaysOnTop', (event, value) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) {
      win.setAlwaysOnTop(value);
    }
    return true;
  });

  // 设置点击穿透
  ipcMain.handle('display:setClickThrough', (event, value) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) {
      win.setIgnoreMouseEvents(value, { forward: true });
    }
    return true;
  });

  // 移动窗口
  ipcMain.handle('display:moveWindow', (event, x, y) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) {
      win.setPosition(x, y);
    }
    return true;
  });

  // 调整窗口大小
  ipcMain.handle('display:resizeWindow', (event, width, height) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) {
      win.setSize(width, height);
    }
    return true;
  });

  // 获取窗口位置
  ipcMain.handle('display:getWindowPosition', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) {
      const [x, y] = win.getPosition();
      return { x, y };
    }
    return { x: 0, y: 0 };
  });

  console.log('[Display IPC] Handlers registered');
}

module.exports = { registerDisplayHandlers };
```

### 3.7 Preload 脚本更新

**文件**: `frontend/preload/index.js` (添加以下内容)

```javascript
// Display API
display: {
  getDisplayConfig: () => ipcRenderer.invoke('display:getConfig'),
  saveDisplayConfig: (config) => ipcRenderer.invoke('display:saveConfig', config),
  setAlwaysOnTop: (value) => ipcRenderer.invoke('display:setAlwaysOnTop', value),
  setClickThrough: (value) => ipcRenderer.invoke('display:setClickThrough', value),
  moveWindow: (x, y) => ipcRenderer.invoke('display:moveWindow', x, y),
  resizeWindow: (w, h) => ipcRenderer.invoke('display:resizeWindow', w, h),
  getWindowPosition: () => ipcRenderer.invoke('display:getWindowPosition'),
},
```

---

## 4. 集成修改

### 4.1 Live2DRenderer.js 修改

```javascript
// 新增导入
import { ScaleManager } from './display/ScaleManager.js';
import { BackgroundManager } from './display/BackgroundManager.js';
import { HotkeyManager } from './control/HotkeyManager.js';
import { WindowController } from './control/WindowController.js';
import { DisplayConfig } from './config/DisplayConfig.js';

export class Live2DRenderer {
  constructor() {
    // ... 现有代码 ...

    // 新增组件
    this.displayConfig = null;
    this.scaleManager = null;
    this.backgroundManager = null;
    this.hotkeyManager = null;
    this.windowController = null;
  }

  async init() {
    try {
      // 加载配置
      this.displayConfig = new DisplayConfig();
      await this.displayConfig.load();

      // ... 现有PIXI初始化代码 ...

      // 初始化新组件
      this.scaleManager = new ScaleManager(this.app, this.modelLoader);
      this.backgroundManager = new BackgroundManager(this.app, this.container);
      this.windowController = new WindowController();

      // 应用配置
      const config = this.displayConfig.get();
      this.scaleManager.setStrategy(config.scale.strategy);
      this.scaleManager.scale = config.scale.value;
      await this.backgroundManager.setMode(config.background.mode, config.background);

      // 初始化快捷键
      this.hotkeyManager = new HotkeyManager({
        scaleManager: this.scaleManager,
        backgroundManager: this.backgroundManager,
        windowController: this.windowController,
        modelLoader: this.modelLoader,
      });
      this.hotkeyManager.start();

      // ... 其他现有代码 ...
    } catch (error) {
      // ...
    }
  }

  // 修改 handleResize
  _handleResize() {
    this.pixiApp.handleResize();
    this.modelLoader.handleResize();
    this.scaleManager?.applyScale();
    this.backgroundManager?.handleResize();
  }

  // 新增公开API
  setScaleStrategy(strategy) {
    this.scaleManager.setStrategy(strategy);
  }

  zoom(delta) {
    this.scaleManager.zoom(delta);
  }

  setBackground(mode, options) {
    return this.backgroundManager.setMode(mode, options);
  }

  getDisplayState() {
    return {
      scale: this.scaleManager?.getState(),
      background: this.backgroundManager?.getState(),
      window: this.windowController?.getState(),
    };
  }
}
```

### 4.2 Live2DWindow.js 修改

```javascript
class Live2DWindow {
  createWindow() {
    // 从存储加载窗口状态
    const savedState = this._loadWindowState();

    const window = new BrowserWindow({
      width: savedState.width || this.config.width,
      height: savedState.height || this.config.height,
      x: savedState.x,
      y: savedState.y,
      // ... 其他配置 ...

      // 新增: 支持调整大小
      resizable: true,
      minWidth: 200,
      minHeight: 300,
    });

    // 保存窗口状态
    window.on('close', () => {
      this._saveWindowState(window);
    });

    window.on('resize', () => {
      this._saveWindowState(window);
    });

    window.on('move', () => {
      this._saveWindowState(window);
    });

    return window;
  }

  _loadWindowState() {
    // 从 electron-store 加载
    const Store = require('electron-store');
    const store = new Store({ name: 'window-state' });
    return store.get('live2d', {});
  }

  _saveWindowState(window) {
    const Store = require('electron-store');
    const store = new Store({ name: 'window-state' });
    const [x, y] = window.getPosition();
    const [width, height] = window.getSize();
    store.set('live2d', { x, y, width, height, alwaysOnTop: window.isAlwaysOnTop() });
  }
}
```

---

## 5. CSS 样式更新

**文件**: `frontend/renderer/live2d/live2d.css`

```css
/* 新增: 控制面板样式 */

.control-overlay {
  position: absolute;
  bottom: 10px;
  left: 10px;
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

#live2d-container:hover .control-overlay {
  opacity: 1;
  pointer-events: auto;
}

.control-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: background 0.2s;
}

.control-btn:hover {
  background: rgba(0, 0, 0, 0.8);
}

/* 设置面板 */
.settings-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 200px;
  background: rgba(0, 0, 0, 0.8);
  border-radius: 8px;
  padding: 12px;
  color: white;
  font-family: sans-serif;
  font-size: 12px;
  display: none;
}

.settings-panel.visible {
  display: block;
}

.settings-panel h3 {
  margin: 0 0 10px 0;
  font-size: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding-bottom: 8px;
}

.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.settings-row label {
  color: rgba(255, 255, 255, 0.8);
}

.settings-row select,
.settings-row input[type="range"] {
  width: 100px;
}

.settings-row input[type="color"] {
  width: 40px;
  height: 24px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* 快捷键提示 */
.hotkey-hint {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: rgba(255, 255, 255, 0.7);
  padding: 6px 10px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 10px;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

#live2d-container:hover .hotkey-hint {
  opacity: 1;
}
```

---

## 6. 实施步骤

### Phase 1: 核心功能 (2天)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 缩放策略系统 | `display/ScaleManager.js` | P0 |
| 模型边界分析 | `display/ModelBoundsAnalyzer.js` | P0 |
| 集成到 Live2DRenderer | `Live2DRenderer.js` | P0 |

### Phase 2: 背景系统 (1天)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 背景管理器 | `display/BackgroundManager.js` | P0 |
| CSS样式更新 | `live2d.css` | P1 |

### Phase 3: 快捷键与窗口控制 (1天)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 快捷键管理器 | `control/HotkeyManager.js` | P0 |
| 窗口控制器 | `control/WindowController.js` | P0 |
| IPC处理 | `main/ipc/handlers/display.js` | P0 |
| Preload更新 | `preload/index.js` | P0 |

### Phase 4: 配置持久化 (0.5天)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 显示配置 | `config/DisplayConfig.js` | P1 |
| 窗口状态存储 | `main/config/WindowStateStore.js` | P1 |
| Live2DWindow状态保存 | `main/windows/Live2DWindow.js` | P1 |

### Phase 5: UI与优化 (1天)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 控制面板UI | `ui/ControlOverlay.js` | P2 |
| 设置面板 | `ui/SettingsPanel.js` | P2 |
| 测试与调试 | - | P0 |

---

## 7. 测试清单

### 7.1 缩放测试
- [ ] fit模式：模型完整显示
- [ ] contain模式：全身模型底部对齐
- [ ] cover模式：填满窗口
- [ ] Ctrl+滚轮缩放
- [ ] 缩放限制 (0.1x ~ 3x)

### 7.2 背景测试
- [ ] 透明背景 (OBS捕获)
- [ ] 绿幕色背景
- [ ] 图片背景加载
- [ ] 视频背景循环播放
- [ ] 背景透明度调节

### 7.3 快捷键测试
- [ ] 方向键移动模型
- [ ] WASD移动模型
- [ ] Ctrl+=/- 缩放
- [ ] Ctrl+R 重置
- [ ] B 切换背景
- [ ] Ctrl+T 切换置顶
- [ ] Ctrl+Alt+C 切换点击穿透

### 7.4 窗口测试
- [ ] 窗口置顶/取消
- [ ] 点击穿透/取消
- [ ] 窗口拖拽
- [ ] 窗口大小调整
- [ ] 状态持久化 (重启后恢复)

### 7.5 OBS集成测试
- [ ] 透明背景捕获
- [ ] 绿幕色键
- [ ] 场景切换

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 不同模型骨骼差异大 | 缩放计算不准确 | 增加模型边界分析，提供手动微调 |
| 视频背景内存占用 | 长时间运行内存增长 | 限制视频分辨率，提供内存监控 |
| 快捷键冲突 | 与其他软件冲突 | 提供快捷键自定义，支持禁用 |
| electron-store性能 | 频繁保存影响性能 | 使用防抖，只在必要时保存 |

---

## 9. 后续扩展

- **多模型支持**: 同时显示多个Live2D模型
- **场景预设**: 保存和加载完整的场景配置
- **动画时间轴**: 背景视频与模型动作同步
- **语音控制**: 通过语音命令控制显示
- **移动端支持**: 响应式布局适配
