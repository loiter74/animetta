/**
 * Live2DRenderer - 主入口
 * 整合所有模块，对外唯一接口
 */

import { PixiApp } from './core/PixiApp.js';
import { ModelLoader } from './core/ModelLoader.js';
import { ScaleManager } from './renderer/ScaleManager.js';
import { BackgroundManager } from './renderer/BackgroundManager.js';
import { ExpressionController } from './renderer/ExpressionController.js';
import { IpcBridge } from './bridge/IpcBridge.js';
import { DisplayConfig } from './config/index.js';

// 简化: 不依赖外部模块，内联实现
class SimpleAudioPlayer {
  constructor(opts) {
    this.opts = opts;
    this.ctx = null;
    this.source = null;
  }

  async play(data) {
    console.log('[AudioPlayer] play() 被调用, audio_data:', !!data?.audio_data, 'volumes:', data?.volumes?.length);
    const { audio_data, format, volumes, expressions } = data || {};
    if (!audio_data) return;

    // 播放音频
    try {
      const binary = atob(audio_data);
      const buffer = new Uint8Array(binary.length);
      for (let o = 0; o < binary.length; o++) buffer[o] = binary.charCodeAt(o);
      const blob = new Blob([buffer], { type: `audio/${format || 'mp3'}` });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      // 启动口型同步（如果提供了 volumes）
      if (volumes && Array.isArray(volumes) && volumes.length > 0) {
        this.opts.onPlaybackStart?.(volumes);
      }

      await audio.play();
      audio.onended = () => {
        this.opts.onPlaybackEnd?.();
        URL.revokeObjectURL(url);
      };
    } catch (e) {
      console.error('[AudioPlayer] ❌ 播放失败:', e.name, e.message);
    }
  }
}

export class Live2DRenderer {
  constructor() {
    this.canvas = document.getElementById('live2d-canvas');
    this.container = document.getElementById('live2d-container');
    this.isLoaded = false;
    this._handleResize = this._handleResize.bind(this);
  }

  async init() {
    console.log('[Live2DRenderer] Initializing...');

    // 创建 PIXI 应用
    this.pixiApp = new PixiApp(this.canvas, this.container);
    this.app = await this.pixiApp.create();

    // 创建模型加载器
    this.modelLoader = new ModelLoader(this.app, this.container);

    // 创建渲染器
    this.scaleManager = new ScaleManager(this.app, this.modelLoader);
    this.backgroundManager = new BackgroundManager(this.app, this.container);
    this.expressionController = new ExpressionController(this.app.ticker, this.modelLoader);

    // 创建音频播放器
    this.audioPlayer = new SimpleAudioPlayer({
      onPlaybackStart: (volumes) => this._startLipSync(volumes),
      onPlaybackEnd: () => {
        this._stopLipSync();
        this.expressionController.setMouthTarget(0);
      },
    });

    // 创建配置管理
    this.displayConfig = new DisplayConfig();
    await this._loadConfig();

    // 创建 IPC 桥接
    this.ipcBridge = new IpcBridge();
    this._setupIpcListeners();

    // 监听窗口大小变化
    window.addEventListener('resize', this._handleResize);

    // 暴露全局引用
    window.live2dRenderer = this;

    console.log('[Live2DRenderer] Initialized');

    // 加载默认模型
    await this._loadDefaultModel();
  }

  async _loadDefaultModel() {
    const fallbackPath = '../../public/live2d/haru/haru_greeter_t03.model3.json';
    try {
      const modelPath = await window.electronAPI?.getConfig?.('model.defaultPath') || fallbackPath;
      await this.loadModel(modelPath);
    } catch {
      await this.loadModel(fallbackPath);
    }
  }

  async _loadConfig() {
    const config = await this.displayConfig.load();
    if (config?.scale) {
      if (config.scale.strategy) this.scaleManager.setStrategy(config.scale.strategy);
      if (config.scale.userScale) this.scaleManager.setUserScale(config.scale.userScale);
    }
    if (config?.background) {
      await this.backgroundManager.setMode(config.background.mode, config.background);
    }
  }

  _setupIpcListeners() {
    this.ipcBridge.on('live2d:action', (data) => {
      console.log('[Renderer] 收到 audio:with-expression');
      this.expressionController.execute(data);
    });

    this.ipcBridge.on('audio:with-expression', (data) => {
      this.audioPlayer.play(data);
    });

    this.ipcBridge.on('audio:stream', (data) => {
      if (data.volume !== undefined) {
        this.expressionController.setMouthTarget(data.volume);
      }
    });
  }

  async loadModel(modelPath) {
    console.log('[Live2DRenderer] Loading model:', modelPath);
    const model = await this.modelLoader.load(modelPath);
    this.expressionController.setModel(model);
    await this.scaleManager.onModelLoaded(model);
    this.isLoaded = true;
    console.log('[Live2DRenderer] Model loaded');
  }

  _handleResize() {
    this.pixiApp.handleResize();
    this.scaleManager.handleResize();
    this.backgroundManager.handleResize();
  }

  // ====== 口型同步 ======
  _startLipSync(volumes) {
    // volumes 是 50Hz 采样的音量包络数组
    // 每 20ms 一个采样点
    if (!Array.isArray(volumes) || volumes.length === 0) {
      console.warn('[Live2DRenderer] 无效的 volumes 数据');
      return;
    }

    console.log('[Live2DRenderer] 启动口型同步，采样点数:', volumes.length);

    const sampleInterval = 1000 / 50; // 50Hz = 20ms 间隔
    let index = 0;

    // 清除之前的定时器
    this._stopLipSync();

    // 创建定时器队列
    this._lipSyncTimers = [];

    const scheduleNext = () => {
      if (index >= volumes.length) {
        console.log('[Live2DRenderer] 口型同步完成');
        return;
      }

      const value = volumes[index];
      this.expressionController.setMouthTarget(value);

      index++;
      if (index < volumes.length) {
        const timerId = setTimeout(scheduleNext, sampleInterval);
        this._lipSyncTimers.push(timerId);
      }
    };

    // 立即开始第一个
    scheduleNext();
  }

  _stopLipSync() {
    if (this._lipSyncTimers) {
      this._lipSyncTimers.forEach(timerId => clearTimeout(timerId));
      this._lipSyncTimers = [];
    }
  }

  // === 公共 API ===
  setExpression(name) { this.expressionController.setExpression(name); }
  playMotion(group, index) { this.expressionController.playMotion(group, index); }
  setMouthOpen(value) { this.expressionController.setMouthTarget(value); }
  executeAction(action) { this.expressionController.execute(action); }

  zoom(delta) { this.scaleManager.zoom(delta); }
  setScaleStrategy(strategy) { this.scaleManager.setStrategy(strategy); }
  resetScale() { this.scaleManager.reset(); }
  moveModel(dx, dy) { this.scaleManager.moveModel(dx, dy); }
  resetModelPosition() { this.scaleManager.resetModelPosition(); }

  async setBackgroundMode(mode, options) { await this.backgroundManager.setMode(mode, options); }

  getModelInfo() { return this.scaleManager.getModelInfo(); }
  getScaleState() { return this.scaleManager.getState(); }
  getBackgroundState() { return this.backgroundManager.getState(); }

  destroy() {
    window.removeEventListener('resize', this._handleResize);
    this._stopLipSync();
    this.expressionController?.destroy();
    this.backgroundManager?.destroy();
    this.ipcBridge = null;
    this.modelLoader?.unload();
    this.pixiApp?.destroy();
    delete window.live2dRenderer;
    console.log('[Live2DRenderer] Destroyed');
  }
}
