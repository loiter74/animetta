/**
 * ChatWindow - Main controller for chat window
 * Coordinates UI components, IPC, and state
 */

import { ChatState } from './state/ChatState.js';
import { MessageList } from './ui/MessageList.js';
import { InputBar } from './ui/InputBar.js';
import { VoiceButton } from './ui/VoiceButton.js';
import { TypingIndicator } from './ui/TypingIndicator.js';
import { IpcListeners } from './ipc/IpcListeners.js';
import { AudioCapture } from './audio/AudioCapture.js';

export class ChatWindow {
  constructor() {
    // Initialize state
    this.state = new ChatState();

    // Get DOM elements
    this.elements = {
      messageList: document.getElementById('message-list'),
      messageInput: document.getElementById('message-input'),
      sendBtn: document.getElementById('send-btn'),
      voiceBtn: document.getElementById('voice-btn'),
      volumeIndicator: document.getElementById('volume-indicator'),
      connectionStatus: document.getElementById('connection-status'),
      speakingIndicator: document.getElementById('speaking-indicator'),
      styleTransferSwitch: document.getElementById('style-transfer-switch'),
      styleTransferStatus: document.getElementById('style-transfer-status'),
    };

    // Initialize UI components
    this.ui = {
      messageList: new MessageList(this.elements.messageList),
      typingIndicator: new TypingIndicator(this.elements.messageList),
    };

    // Initialize input bar with callback
    this.ui.inputBar = new InputBar(
      this.elements.messageInput,
      this.elements.sendBtn,
      (text) => this._handleSendText(text)
    );

    // Initialize voice button with callbacks
    this.ui.voiceButton = new VoiceButton(
      this.elements.voiceBtn,
      () => this._startVoiceInput(),
      () => this._stopVoiceInput()
    );

    // Initialize IPC listeners
    this.ipc = new IpcListeners({
      onLlmChunk: (data) => this._handleLlmChunk(data),
      onMessage: (data) => this._handleMessage(data),
      onSpeaking: (isSpeaking) => this._setSpeaking(isSpeaking),
      onStyleTransfer: (enabled) => this._setStyleTransfer(enabled),
      onTranscript: (data) => this._handleTranscript(data),
    });

    // Initialize audio capture
    this.audioCapture = new AudioCapture({
      sampleRate: 16000,
      chunkSize: 480, // 30ms at 16kHz
    });

    // Setup audio capture callbacks
    this.audioCapture.onAudioChunk = (audioData) => {
      this._sendAudioChunk(audioData);
    };
    this.audioCapture.onError = (error) => {
      console.error('[ChatWindow] Audio capture error:', error);
      this._showError(`麦克风错误: ${error.message}`);
      this.ui.voiceButton.isRecording = false;
      this.elements.voiceBtn.classList.remove('recording');
    };
    this.audioCapture.onPermissionGranted = () => {
      console.log('[ChatWindow] Microphone permission granted');
    };
    this.audioCapture.onVolumeUpdate = (volume) => {
      this._updateVolumeIndicator(volume);
    };

    // Setup event listeners
    this._setupEventListeners();

    // Setup IPC
    this.ipc.setup();

    // Check connection
    this._checkConnection();

    // Focus input
    this.ui.inputBar.focus();

    console.log('[ChatWindow] Initialized');
  }

  /**
   * Setup DOM event listeners
   */
  _setupEventListeners() {
    // Style transfer toggle
    if (this.elements.styleTransferSwitch) {
      this.elements.styleTransferSwitch.addEventListener('change', () => {
        this._toggleStyleTransfer();
      });
    }

    // Title bar controls
    document.querySelectorAll('.control-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const action = e.target.dataset.action;
        if (window.electronAPI && window.electronAPI.window) {
          if (action === 'close') {
            window.electronAPI.window.close();
          }
        }
      });
    });
  }

  /**
   * Handle send text
   */
  async _handleSendText(text) {
    // Add user message
    this._addMessage({
      role: 'user',
      text: text,
      timestamp: Date.now(),
    });

    // Send to backend
    try {
      if (!window.electronAPI || !window.electronAPI.chat) {
        this._showError('Electron API not available');
        return;
      }

      await window.electronAPI.chat.sendMessage({
        text: text,
        timestamp: Date.now(),
      });

      // Show typing indicator
      this.ui.typingIndicator.show();
    } catch (error) {
      console.error('[ChatWindow] Failed to send message:', error);
      this._showError('Failed to send message');
    }
  }

  /**
   * Handle LLM chunk (streaming response)
   */
  _handleLlmChunk(data) {
    // Hide typing indicator
    this.ui.typingIndicator.hide();

    const text = data.text || '';
    const seq = data.seq ?? 0;
    const isComplete = data.is_complete || text === '';

    // Handle completion marker
    if (isComplete) {
      console.log('[ChatWindow] Stream complete');
      this._finalizeResponse();
      return;
    }

    // First chunk of new response (seq === 0 or no current response)
    // Use the incoming seq as the starting point if we're starting fresh
    if (seq === 0 || this.state.currentResponseSeq === 0) {
      const startSeq = this.state.currentResponseSeq === 0 ? seq : 0;
      this.state.resetResponse(startSeq);
    }

    // Buffer chunk by seq
    this.state.bufferChunk(seq, text);

    // Process buffered chunks
    this.state.processBufferedChunks();

    // Skip if no content yet (waiting for missing chunks)
    if (!this.state.currentResponse) {
      // Schedule fallback flush for missing chunks
      this.state.scheduleFlush(() => this._updateUIWithCurrentResponse());
      return;
    }

    // Update UI
    this._updateUIWithCurrentResponse();
  }

  /**
   * Update UI with current response text
   */
  _updateUIWithCurrentResponse() {
    if (!this.state.currentResponse) return;
    const lastMessage = this.state.getLastMessage();
    if (lastMessage && lastMessage.role === 'assistant' && lastMessage.streaming) {
      lastMessage.text = this.state.currentResponse;
      this._updateMessage(lastMessage);
    } else {
      this._addMessage({
        role: 'assistant',
        text: this.state.currentResponse,
        timestamp: Date.now(),
        streaming: true,
      });
    }
  }

  /**
   * Finalize streaming response
   */
  _finalizeResponse() {
    this.state.processBufferedChunks();

    const lastMessage = this.state.getLastMessage();
    if (lastMessage && lastMessage.streaming) {
      lastMessage.streaming = false;
      this._updateMessage(lastMessage);
    }

    this.state.resetResponse();
  }

  /**
   * Handle complete message
   */
  _handleMessage(data) {
    console.log('[ChatWindow] Complete message:', data);
    this._finalizeResponse();
  }

  /**
   * Handle transcript (ASR result from voice input)
   * Display user's voice input in the chat box
   */
  _handleTranscript(data) {
    const text = data.text || '';
    if (!text.trim()) return;

    console.log('[ChatWindow] 🎤 User transcript:', text);

    // Add user message to chat (from voice input)
    this._addMessage({
      role: 'user',
      text: text,
      timestamp: Date.now(),
      source: 'voice',  // Mark as voice input
    });

    // Show typing indicator (waiting for AI response)
    this.ui.typingIndicator.show();
  }

  /**
   * Add message to UI
   */
  _addMessage(message) {
    this.state.addMessage(message);

    // Remove empty state
    const emptyState = this.ui.messageList.querySelector('.empty-state');
    if (emptyState) {
      emptyState.remove();
    }

    // Create and append message element
    const messageEl = this.ui.messageList.createMessageElement(message);
    this.ui.messageList.appendChild(messageEl);
    this.ui.messageList.scrollToBottom();
  }

  /**
   * Update existing message
   */
  _updateMessage(message) {
    const messageEl = this.ui.messageList.querySelector(`[data-id="${message.id}"]`);
    if (messageEl) {
      const contentEl = messageEl.querySelector('.message-content');
      if (contentEl) {
        contentEl.textContent = message.text;
        contentEl.classList.toggle('streaming', message.streaming);
      }
      this.ui.messageList.scrollToBottom();
    }
  }

  /**
   * Start voice input
   */
  async _startVoiceInput() {
    if (!window.electronAPI || !window.electronAPI.chat) {
      console.error('[ChatWindow] Electron API not available');
      return;
    }

    try {
      // 1. 通知后端开始语音输入
      await window.electronAPI.chat.startVoiceInput();

      // 2. 启动本地录音
      await this.audioCapture.start();

      console.log('[ChatWindow] Voice input started');
    } catch (error) {
      console.error('[ChatWindow] Failed to start voice input:', error);
      this._showError(`无法启动录音: ${error.message}`);
      // 重置按钮状态
      this.ui.voiceButton.isRecording = false;
      this.elements.voiceBtn.classList.remove('recording');
    }
  }

  /**
   * Stop voice input
   */
  async _stopVoiceInput() {
    if (!window.electronAPI || !window.electronAPI.chat) return;

    try {
      // 1. 停止本地录音
      this.audioCapture.stop();

      // 2. 通知后端停止语音输入
      await window.electronAPI.chat.stopVoiceInput();

      console.log('[ChatWindow] Voice input stopped');
    } catch (error) {
      console.error('[ChatWindow] Failed to stop voice input:', error);
    }
  }

  /**
   * Send audio chunk to backend
   * @param {Float32Array} audioData - Audio samples at 16kHz
   */
  _sendAudioChunk(audioData) {
    if (!window.electronAPI || !window.electronAPI.chat) return;

    // 转换为普通数组发送 (IPC 不能直接传输 TypedArray)
    const audioArray = Array.from(audioData);
    window.electronAPI.chat.sendAudioChunk(audioArray);

    // 每 30 块打印一次 (~900ms)
    if (!this._audioChunkCount) this._audioChunkCount = 0;
    this._audioChunkCount++;
    if (this._audioChunkCount % 30 === 0) {
      console.log(`[ChatWindow] 📤 已发送 ${this._audioChunkCount} 个音频块到后端`);
    }
  }

  /**
   * Update volume indicator
   * @param {number} volume - Volume level 0-1
   */
  _updateVolumeIndicator(volume) {
    if (this.elements.volumeIndicator) {
      // Amplify volume for better visibility (mic input can be quiet)
      const amplified = Math.min(1, volume * 5);
      const percentage = Math.round(amplified * 100);
      this.elements.volumeIndicator.style.setProperty('--volume', `${percentage}%`);
      this.elements.volumeIndicator.classList.toggle('active', amplified > 0.05);
    }
  }

  /**
   * Set speaking state
   */
  _setSpeaking(isSpeaking) {
    this.state.isSpeaking = isSpeaking;
    this.elements.speakingIndicator.classList.toggle('hidden', !isSpeaking);

    if (window.electronAPI && window.electronAPI.chat) {
      window.electronAPI.chat.setSpeaking(isSpeaking);
    }
  }

  /**
   * Set style transfer state
   */
  _setStyleTransfer(enabled) {
    this.state.styleTransferEnabled = enabled;
    if (this.elements.styleTransferSwitch) {
      this.elements.styleTransferSwitch.checked = enabled;
    }
    if (this.elements.styleTransferStatus) {
      this.elements.styleTransferStatus.textContent = enabled ? 'ON' : 'OFF';
    }
    // console.log('[ChatWindow] Style transfer:', enabled);
  }

  /**
   * Toggle style transfer
   */
  async _toggleStyleTransfer() {
    const enabled = this.elements.styleTransferSwitch.checked;
    this._setStyleTransfer(enabled);

    if (window.electronAPI && window.electronAPI.chat) {
      try {
        await window.electronAPI.chat.setStyleTransfer(enabled);
      } catch (error) {
        console.error('[ChatWindow] Failed to update style transfer:', error);
      }
    }
  }

  /**
   * Check connection status
   */
  async _checkConnection() {
    try {
      await window.electronAPI.getVersion();
      this._setConnectionStatus('connected');
    } catch (error) {
      this._setConnectionStatus('disconnected');
    }
  }

  /**
   * Set connection status
   */
  _setConnectionStatus(status) {
    this.elements.connectionStatus.className = `status ${status}`;
    this.state.isConnected = status === 'connected';

    const statusText = this.elements.connectionStatus.querySelector('.status-text');
    if (statusText) {
      const labels = {
        connected: 'Connected',
        disconnected: 'Disconnected',
        connecting: 'Connecting...',
      };
      statusText.textContent = labels[status] || status;
    }
  }

  /**
   * Show error message
   */
  _showError(message) {
    const el = document.createElement('div');
    el.className = 'message assistant error';

    const content = document.createElement('div');
    content.className = 'message-content';
    content.style.background = '#f87171';
    content.textContent = message; // Use textContent for security

    el.appendChild(content);
    this.ui.messageList.appendChild(el);
    this.ui.messageList.scrollToBottom();

    // Auto-remove after 3 seconds
    setTimeout(() => el.remove(), 3000);
  }

  /**
   * Destroy chat window (cleanup)
   */
  destroy() {
    // Stop audio capture
    if (this.audioCapture) {
      this.audioCapture.stop();
    }
    this.ipc.cleanup();
    console.log('[ChatWindow] Destroyed');
  }
}
