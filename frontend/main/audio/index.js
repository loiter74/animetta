/**
 * Audio Module - 主进程音频处理
 * - AudioCapture: 录音
 * - VadBridge: VAD 检测 + 发送音频给后端
 * - LipSyncReceiver: 接收口型值 → 转发给 live2d 窗口
 */

const { ipcMain, BrowserWindow } = require('electron');

// === AudioCapture ===
class AudioCapture {
  constructor() {
    this.recording = false;
    this.audioChunks = [];
  }

  async start() {
    if (this.recording) return;
    this.recording = true;
    this.audioChunks = [];
    console.log('[AudioCapture] Started');
  }

  stop() {
    this.recording = false;
    console.log('[AudioCapture] Stopped');
    return this.audioChunks;
  }

  addChunk(chunk) {
    if (this.recording) {
      this.audioChunks.push(chunk);
    }
  }

  getChunks() {
    return this.audioChunks;
  }

  isRecording() {
    return this.recording;
  }
}

// === VadBridge ===
class VadBridge {
  constructor(socketBridge) {
    this.socketBridge = socketBridge;
    this.isRecording = false;
  }

  async startRecording() {
    this.isRecording = true;
    console.log('[VadBridge] Recording started');
  }

  async stopRecording() {
    this.isRecording = false;
    console.log('[VadBridge] Recording stopped');
  }

  async sendAudioChunk(chunk) {
    if (!this.socketBridge?.isConnected()) {
      console.warn('[VadBridge] Socket not connected');
      return;
    }

    this.socketBridge.send('audio_data', {
      audio: chunk,
      sample_rate: 16000
    });
  }

  isConnected() {
    return this.socketBridge?.isConnected() || false;
  }
}

// === LipSyncReceiver ===
class LipSyncReceiver {
  constructor(windowManager) {
    this.windowManager = windowManager;
  }

  sendLipSyncValue(value) {
    const live2dWindow = this.windowManager.getWindow('live2d');
    if (live2dWindow && !live2dWindow.isDestroyed()) {
      live2dWindow.webContents.send('audio:stream', { volume: value });
    }
  }

  sendExpression(expression) {
    const live2dWindow = this.windowManager.getWindow('live2d');
    if (live2dWindow && !live2dWindow.isDestroyed()) {
      live2dWindow.webContents.send('live2d:action', {
        type: 'expression',
        name: expression
      });
    }
  }
}

module.exports = { AudioCapture, VadBridge, LipSyncReceiver };
