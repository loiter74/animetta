/**
 * AudioCapture - 麦克风录音模块
 *
 * 功能：
 * - 获取麦克风权限
 * - 捕获音频流并重采样到 16kHz
 * - 通过回调函数输出音频数据块
 */

export class AudioCapture {
  constructor(options = {}) {
    // 配置
    this.targetSampleRate = options.sampleRate || 16000;
    this.sourceSampleRate = options.sourceSampleRate || 48000;
    this.chunkSize = options.chunkSize || 480; // 30ms at 16kHz

    // 状态
    this.isRecording = false;
    this.stream = null;
    this.audioContext = null;
    this.sourceNode = null;
    this.scriptProcessor = null;

    // 回调
    this.onAudioChunk = null;  // (Float32Array) => void
    this.onError = null;       // (Error) => void
    this.onPermissionGranted = null;  // () => void
    this.onVolumeUpdate = null;  // (number) => void - RMS volume 0-1

    // 音量监控
    this._chunkCount = 0;
    this._lastVolumeLog = 0;

    // 重采样缓冲区
    this._resampleBuffer = [];
    this._resampleRatio = this.sourceSampleRate / this.targetSampleRate;
  }

  /**
   * 检查麦克风权限状态
   */
  async checkPermission() {
    try {
      const result = await navigator.permissions.query({ name: 'microphone' });
      return result.state; // 'granted', 'denied', 'prompt'
    } catch (e) {
      // 某些浏览器不支持 permissions API
      return 'unknown';
    }
  }

  /**
   * 开始录音
   */
  async start() {
    if (this.isRecording) {
      console.warn('[AudioCapture] Already recording');
      return;
    }

    try {
      // 1. 请求麦克风权限
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.sourceSampleRate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });

      if (this.onPermissionGranted) {
        this.onPermissionGranted();
      }

      // 2. 获取实际采样率（可能和请求的不同）
      const track = this.stream.getAudioTracks()[0];
      const settings = track.getSettings();
      this.sourceSampleRate = settings.sampleRate || this.sourceSampleRate;
      this._resampleRatio = this.sourceSampleRate / this.targetSampleRate;

      console.log(`[AudioCapture] 麦克风已启动: ${this.sourceSampleRate}Hz → ${this.targetSampleRate}Hz`);

      // 3. 创建 AudioContext
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.sourceSampleRate
      });

      // 4. 创建音频源
      this.sourceNode = this.audioContext.createMediaStreamSource(this.stream);

      // 5. 创建 ScriptProcessor (虽然已弃用，但兼容性更好)
      // bufferSize 4096 在 48kHz 下约 85ms
      const bufferSize = 4096;
      this.scriptProcessor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

      // 6. 处理音频数据
      this.scriptProcessor.onaudioprocess = (event) => {
        if (!this.isRecording) return;

        const inputData = event.inputBuffer.getChannelData(0);
        this._processAudioChunk(inputData);
      };

      this.gainNode = this.audioContext.createGain();
      this.gainNode.gain.value = 3.0;

      // 7. 连接节点 ← 只改这里
      this.sourceNode.connect(this.gainNode);      // source → gain
      this.gainNode.connect(this.scriptProcessor); // gain → processor
      this.scriptProcessor.connect(this.audioContext.destination);

      this.isRecording = true;
      console.log('[AudioCapture] 录音已开始');

    } catch (error) {
      console.error('[AudioCapture] 启动失败:', error);
      if (this.onError) {
        this.onError(error);
      }
      throw error;
    }
  }

  /**
   * 停止录音
   */
  stop() {
    if (!this.isRecording) {
      return;
    }

    this.isRecording = false;

    // 断开音频节点
    if (this.gainNode) {
      this.gainNode.disconnect();
      this.gainNode = null;
    }

    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor.onaudioprocess = null;
      this.scriptProcessor = null;
    }

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    // 关闭 AudioContext
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    // 停止麦克风流
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    // 清空缓冲区
    this._resampleBuffer = [];

    console.log('[AudioCapture] 录音已停止');
  }

  /**
   * 处理音频块 - 重采样并发送
   */
  _processAudioChunk(inputData) {
    // 线性插值重采样: 48kHz → 16kHz
    const resampled = this._resample(inputData);

    // 计算音量 (RMS)
    const volume = this._calculateVolume(inputData);

    // 累积到缓冲区
    this._resampleBuffer.push(...resampled);

    // 当缓冲区足够大时，发送数据块
    while (this._resampleBuffer.length >= this.chunkSize) {
      const chunk = this._resampleBuffer.splice(0, this.chunkSize);

      this._chunkCount++;

      // 每 30 个块 (~900ms) 打印一次音量日志
      const now = Date.now();
      if (this._chunkCount % 30 === 0 || now - this._lastVolumeLog > 1000) {
        const volumeBar = this._volumeToBar(volume);
        console.log(`[AudioCapture] 🎤 音量: ${volumeBar} ${(volume * 100).toFixed(1)}% | 块: ${this._chunkCount}`);
        this._lastVolumeLog = now;
      }

      if (this.onAudioChunk) {
        this.onAudioChunk(new Float32Array(chunk));
      }

      if (this.onVolumeUpdate) {
        this.onVolumeUpdate(volume);
      }
    }
  }

  /**
   * 计算 RMS 音量
   */
  _calculateVolume(samples) {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    return Math.sqrt(sum / samples.length);
  }

  /**
   * 音量转可视化条
   */
  _volumeToBar(volume) {
    const bars = Math.round(volume * 20);
    return '█'.repeat(bars) + '░'.repeat(20 - bars);
  }

  /**
   * 线性插值重采样
   */
  _resample(inputData) {
    const inputLength = inputData.length;
    const outputLength = Math.floor(inputLength / this._resampleRatio);
    const output = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * this._resampleRatio;
      const srcIndexFloor = Math.floor(srcIndex);
      const srcIndexCeil = Math.min(srcIndexFloor + 1, inputLength - 1);
      const fraction = srcIndex - srcIndexFloor;

      // 线性插值
      output[i] = inputData[srcIndexFloor] * (1 - fraction) +
                  inputData[srcIndexCeil] * fraction;
    }

    return output;
  }

  /**
   * 获取录音状态
   */
  getRecordingState() {
    return {
      isRecording: this.isRecording,
      sourceSampleRate: this.sourceSampleRate,
      targetSampleRate: this.targetSampleRate,
    };
  }
}
