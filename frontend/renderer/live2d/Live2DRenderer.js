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
    const { audio_data, format, volumes, expressions, return_to_idle } = data || {};
    if (!audio_data) return;

    // 打印 volumes 数组的首尾值用于调试
    if (volumes && volumes.length > 0) {
      console.log('[AudioPlayer] volumes 首值:', volumes[0].toFixed(3), '尾值:', volumes[volumes.length - 1].toFixed(3));
    }

    // 播放音频
    try {
      const binary = atob(audio_data);
      const buffer = new Uint8Array(binary.length);
      for (let o = 0; o < binary.length; o++) buffer[o] = binary.charCodeAt(o);
      const blob = new Blob([buffer], { type: `audio/${format || 'mp3'}` });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      // 启动口型同步（如果提供了 volumes），传递 audio 对象用于时间同步
      // 必须在 play() 之前设置监听器，否则会错过 playing 事件
      if (volumes && Array.isArray(volumes) && volumes.length > 0) {
        this.opts.onPlaybackStart?.(audio, volumes);
      }

      // 处理音频播放结束时的 idle 恢复
      const onEnded = () => {
        console.log('[AudioPlayer] audio.onended 触发, return_to_idle:', return_to_idle);
        this.opts.onPlaybackEnd?.();

        // 如果标记了 return_to_idle，在音频播放结束后恢复 idle 表情
        if (return_to_idle) {
          console.log('[AudioPlayer] 音频播放结束，恢复 idle 表情');
          this.opts.onReturnToIdle?.();
        }

        URL.revokeObjectURL(url);
      };

      audio.onended = onEnded;
      await audio.play();

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
      onPlaybackStart: (audio, volumes) => this._startLipSync(audio, volumes),
      onPlaybackEnd: () => {
        this._stopLipSync();
        this.expressionController.setMouthTarget(0);
      },
      onReturnToIdle: () => {
        // 音频播放结束后恢复 idle 表情
        this.expressionController.setExpression('idle');
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
      // 处理新的参数映射模式
      if (data.use_parameter_mapping && data.expressions?.frames) {
        console.log('[Renderer] 使用参数映射模式, frames:', data.expressions.frames.length);
        this._playParameterTimeline(data);
      } else {
        // 传统模式：只播放音频和口型同步
        console.log('[Renderer] 使用传统模式');
        this.audioPlayer.play(data);
      }
    });

    this.ipcBridge.on('audio:stream', (data) => {
      if (data.volume !== undefined) {
        this.expressionController.setMouthTarget(data.volume);
      }
    });
  }

  /**
   * 播放参数时间轴（参数映射模式）
   * @param {Object} data - { audio_data, format, volumes, expressions, use_parameter_mapping, return_to_idle }
   */
  async _playParameterTimeline(data) {
    const { audio_data, format, volumes, expressions, return_to_idle } = data;

    // 1. 启动音频播放和口型同步
    this.audioPlayer.play({
      audio_data,
      format,
      volumes,
      expressions,
      return_to_idle  // 传递 return_to_idle 标志
    });

    // 2. 启动表情时间轴播放
    if (expressions?.frames) {
      // 等待音频开始播放
      await new Promise(resolve => setTimeout(resolve, 100));

      // 启动参数时间轴
      this.expressionController.playParameterTimeline(expressions);
    }
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
  _startLipSync(audio, volumes) {
    // volumes 是 50Hz 采样的音量包络数组，每 20ms 一个采样点
    if (!Array.isArray(volumes) || volumes.length === 0) {
      console.warn('[Live2DRenderer] 无效的 volumes 数据');
      return;
    }

    console.log('[Live2DRenderer] 启动口型同步，采样点数:', volumes.length, '音频时长:', audio.duration.toFixed(2) + 's');

    const intervalMs = 20; // 原始采样间隔
    let animFrameId = null;
    let lastIndex = -1;
    let hasStarted = false;

    // 清除之前的同步
    this._stopLipSync();

    const tick = () => {
      // 检查音频是否已结束
      if (audio.ended) {
        console.log('[Live2DRenderer] 音频已结束，停止同步');
        if (animFrameId) cancelAnimationFrame(animFrameId);
        this.expressionController.setMouthTarget(0);
        return;
      }

      // 检查音频是否暂停
      if (audio.paused) {
        // 如果还没开始播放，继续等待
        if (!hasStarted) {
          animFrameId = requestAnimationFrame(tick);
          return;
        }
        // 如果已经开始了但现在暂停，停止同步
        console.log('[Live2DRenderer] 音频已暂停，停止同步');
        if (animFrameId) cancelAnimationFrame(animFrameId);
        this.expressionController.setMouthTarget(0);
        return;
      }

      // 音频正在播放，标记为已开始
      if (!hasStarted) {
        hasStarted = true;
        console.log('[Live2DRenderer] 音频开始播放，duration:', audio.duration.toFixed(2) + 's');
      }

      const currentMs = audio.currentTime * 1000;
      const index = Math.floor(currentMs / intervalMs);

      // 更新口型：如果在 volumes 范围内，使用对应的值；否则归零
      if (index !== lastIndex) {
        if (index < volumes.length) {
          const volume = volumes[index];
          this.expressionController.setMouthTarget(volume);
          lastIndex = index;
        } else {
          // 超出 volumes 范围，归零
          if (lastIndex < volumes.length) {
            console.log('[Live2DRenderer] 播放完所有 volume 数据 (index:', index, '>= volumes.length:', volumes.length + ')，归零口型');
          }
          this.expressionController.setMouthTarget(0);
          lastIndex = index;
        }
      }

      animFrameId = requestAnimationFrame(tick);
    };

    // 立即启动 tick 循环
    animFrameId = requestAnimationFrame(tick);

    // 保存 cancel 函数供 _stopLipSync 调用
    this._lipSyncCancel = () => {
      if (animFrameId) cancelAnimationFrame(animFrameId);
    };
  }

  _stopLipSync() {
    if (this._lipSyncCancel) {
      this._lipSyncCancel();
      this._lipSyncCancel = null;
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
