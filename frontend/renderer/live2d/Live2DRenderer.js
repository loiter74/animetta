import { PixiApp } from './core/PixiApp.js';
import { ModelLoader } from './core/ModelLoader.js';
import { ScaleManager } from './renderer/ScaleManager.js';
import { BackgroundManager } from './renderer/BackgroundManager.js';
import { ExpressionController } from './renderer/ExpressionController.js';
import { IpcBridge } from './bridge/IpcBridge.js';
import { DisplayConfig } from './config/index.js';

class SimpleAudioPlayer {
  constructor(opts) {
    this.opts = opts;
    this.ctx = null;
    this.source = null;
    this._currentAudio = null;
    this._currentBlobUrl = null;
    this._onEndedHandler = null;
  }

  async play(data) {
    console.log('[AudioPlayer] play() called, audio_data:', !!data?.audio_data, 'volumes:', data?.volumes?.length);
    const { audio_data, format, volumes, expressions, return_to_idle } = data || {};
    if (!audio_data) return;

    this._cleanupCurrentAudio();

    if (volumes && volumes.length > 0) {
      console.log('[AudioPlayer] volumes first:', volumes[0].toFixed(3), 'last:', volumes[volumes.length - 1].toFixed(3));
    }

    try {
      const binary = atob(audio_data);
      const buffer = new Uint8Array(binary.length);
      for (let o = 0; o < binary.length; o++) buffer[o] = binary.charCodeAt(o);
      const blob = new Blob([buffer], { type: `audio/${format || 'mp3'}` });
      const url = URL.createObjectURL(blob);
      this._currentBlobUrl = url;
      const audio = new Audio(url);

      this._currentAudio = audio;

      if (volumes && Array.isArray(volumes) && volumes.length > 0) {
        this.opts.onPlaybackStart?.(audio, volumes);
      }

      this._onEndedHandler = () => {
        console.log('[AudioPlayer] audio.onended triggered, return_to_idle:', return_to_idle);
        this.opts.onPlaybackEnd?.();

        if (return_to_idle) {
          console.log('[AudioPlayer] Playback ended, restoring idle expression');
          this.opts.onReturnToIdle?.();
        }

        this._cleanupCurrentAudio();
      };
      audio.onended = this._onEndedHandler;

      await audio.play();

    } catch (e) {
      console.error('[AudioPlayer] ❌ Playback failed:', e.name, e.message);
      this._cleanupCurrentAudio();
    }
  }

  stop() {
    console.log('[AudioPlayer] stop() called');
    if (this._currentAudio) {
      this._currentAudio.pause();
      this._currentAudio.currentTime = 0;
    }
    this._cleanupCurrentAudio();
    this.opts.onPlaybackEnd?.();
  }

  _cleanupCurrentAudio() {
    if (this._currentAudio) {
      this._currentAudio.onended = null;
      this._currentAudio = null;
    }
    if (this._currentBlobUrl) {
      URL.revokeObjectURL(this._currentBlobUrl);
      this._currentBlobUrl = null;
    }
    this._onEndedHandler = null;
  }

  destroy() {
    this._cleanupCurrentAudio();
    this.opts = null;
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

    this.pixiApp = new PixiApp(this.canvas, this.container);
    this.app = await this.pixiApp.create();

    this.modelLoader = new ModelLoader(this.app, this.container);

    this.scaleManager = new ScaleManager(this.app, this.modelLoader);
    this.backgroundManager = new BackgroundManager(this.app, this.container);
    this.expressionController = new ExpressionController(this.app.ticker, this.modelLoader);

    this.audioPlayer = new SimpleAudioPlayer({
      onPlaybackStart: (audio, volumes) => this._startLipSync(audio, volumes),
      onPlaybackEnd: () => {
        this._stopLipSync();
        this.expressionController.setMouthTarget(0);
      },
      onReturnToIdle: () => {
        this.expressionController.setExpression('idle');
      },
    });

    this.displayConfig = new DisplayConfig();
    await this._loadConfig();

    this.ipcBridge = new IpcBridge();
    this._setupIpcListeners();

    window.addEventListener('resize', this._handleResize);

    window.live2dRenderer = this;

    console.log('[Live2DRenderer] Initialized');

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
      console.log('[Renderer] Received audio:with-expression');
      this.expressionController.execute(data);
    });

    this.ipcBridge.on('audio:with-expression', (data) => {
      if (data.use_parameter_mapping && data.expressions?.frames) {
        console.log('[Renderer] Using parameter mapping mode, frames:', data.expressions.frames.length);
        this._playParameterTimeline(data);
      } else {
        console.log('[Renderer] Using legacy mode');
        this.audioPlayer.play(data);
      }
    });

    this.ipcBridge.on('audio:stream', (data) => {
      if (data.volume !== undefined) {
        this.expressionController.setMouthTarget(data.volume);
      }
    });

    this.ipcBridge.on('audio:stop', () => {
      console.log('[Renderer] Received stop_audio event');
      this.stopAudio();
    });
  }

  async _playParameterTimeline(data) {
    const { audio_data, format, volumes, expressions, return_to_idle } = data;

    this.audioPlayer.play({
      audio_data,
      format,
      volumes,
      expressions,
      return_to_idle
    });

    if (expressions?.frames) {
      await new Promise(resolve => setTimeout(resolve, 100));
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

  _startLipSync(audio, volumes) {
    if (!Array.isArray(volumes) || volumes.length === 0) {
      console.warn('[Live2DRenderer] Invalid volumes data');
      return;
    }

    console.log('[Live2DRenderer] Starting lip sync, samples:', volumes.length, 'duration:', audio.duration.toFixed(2) + 's');

    const intervalMs = 20;
    let animFrameId = null;
    let lastIndex = -1;
    let hasStarted = false;

    this._stopLipSync();

    const tick = () => {
      if (audio.ended) {
        console.log('[Live2DRenderer] Audio ended, stopping sync');
        if (animFrameId) cancelAnimationFrame(animFrameId);
        this.expressionController.setMouthTarget(0);
        return;
      }

      if (audio.paused) {
        if (!hasStarted) {
          animFrameId = requestAnimationFrame(tick);
          return;
        }
        console.log('[Live2DRenderer] Audio paused, stopping sync');
        if (animFrameId) cancelAnimationFrame(animFrameId);
        this.expressionController.setMouthTarget(0);
        return;
      }

      if (!hasStarted) {
        hasStarted = true;
        console.log('[Live2DRenderer] Audio started, duration:', audio.duration.toFixed(2) + 's');
      }

      const currentMs = audio.currentTime * 1000;
      const index = Math.floor(currentMs / intervalMs);

      if (index !== lastIndex) {
        if (index < volumes.length) {
          const volume = volumes[index];
          this.expressionController.setMouthTarget(volume);
          lastIndex = index;
        } else {
          if (lastIndex < volumes.length) {
            console.log('[Live2DRenderer] Played all volume data (index:', index, '>= volumes.length:', volumes.length + ')');
          }
          this.expressionController.setMouthTarget(0);
          lastIndex = index;
        }
      }

      animFrameId = requestAnimationFrame(tick);
    };

    animFrameId = requestAnimationFrame(tick);

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

  setExpression(name) { this.expressionController.setExpression(name); }
  playMotion(group, index) { this.expressionController.playMotion(group, index); }
  setMouthOpen(value) { this.expressionController.setMouthTarget(value); }
  executeAction(action) { this.expressionController.execute(action); }

  stopAudio() {
    console.log('[Live2DRenderer] stopAudio() called');
    this.audioPlayer?.stop();
    this._stopLipSync();
    this.expressionController.setMouthTarget(0);
  }

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
    this.ipcBridge?.destroy();
    this.ipcBridge = null;
    this.audioPlayer?.destroy();
    this.audioPlayer = null;
    this.modelLoader?.unload();
    this.pixiApp?.destroy();
    delete window.live2dRenderer;
    console.log('[Live2DRenderer] Destroyed');
  }
}
