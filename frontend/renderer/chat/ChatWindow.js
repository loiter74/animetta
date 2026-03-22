import { ChatState } from './state/ChatState.js';
import { MessageList } from './ui/MessageList.js';
import { InputBar } from './ui/InputBar.js';
import { VoiceButton } from './ui/VoiceButton.js';
import { TypingIndicator } from './ui/TypingIndicator.js';
import { IpcListeners } from './ipc/IpcListeners.js';
import { AudioCapture } from './audio/AudioCapture.js';

export class ChatWindow {
  constructor() {
    this.state = new ChatState();

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

    this.ui = {
      messageList: new MessageList(this.elements.messageList),
      typingIndicator: new TypingIndicator(this.elements.messageList),
    };

    this.ui.inputBar = new InputBar(
      this.elements.messageInput,
      this.elements.sendBtn,
      (text) => this._handleSendText(text)
    );

    this.ui.voiceButton = new VoiceButton(
      this.elements.voiceBtn,
      () => this._startVoiceInput(),
      () => this._stopVoiceInput()
    );

    this.ipc = new IpcListeners({
      onLlmChunk: (data) => this._handleLlmChunk(data),
      onMessage: (data) => this._handleMessage(data),
      onSpeaking: (isSpeaking) => this._setSpeaking(isSpeaking),
      onStyleTransfer: (enabled) => this._setStyleTransfer(enabled),
      onTranscript: (data) => this._handleTranscript(data),
    });

    this.audioCapture = new AudioCapture({
      sampleRate: 16000,
      chunkSize: 480,
    });

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

    this._setupEventListeners();
    this.ipc.setup();
    this._checkConnection();
    this.ui.inputBar.focus();

    console.log('[ChatWindow] Initialized');
  }

  _setupEventListeners() {
    if (this.elements.styleTransferSwitch) {
      this.elements.styleTransferSwitch.addEventListener('change', () => {
        this._toggleStyleTransfer();
      });
    }

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

  async _handleSendText(text) {
    this._addMessage({
      role: 'user',
      text: text,
      timestamp: Date.now(),
    });

    try {
      if (!window.electronAPI || !window.electronAPI.chat) {
        this._showError('Electron API not available');
        return;
      }

      await window.electronAPI.chat.sendMessage({
        text: text,
        timestamp: Date.now(),
      });

      this.ui.typingIndicator.show();
    } catch (error) {
      console.error('[ChatWindow] Failed to send message:', error);
      this._showError('Failed to send message');
    }
  }

  _handleLlmChunk(data) {
    this.ui.typingIndicator.hide();

    const text = data.text || '';
    const seq = data.seq ?? 0;
    const isComplete = data.is_complete || text === '';

    if (isComplete) {
      console.log('[ChatWindow] Stream complete');
      this._finalizeResponse();
      return;
    }

    if (seq === 0 || this.state.currentResponseSeq === 0) {
      const startSeq = this.state.currentResponseSeq === 0 ? seq : 0;
      this.state.resetResponse(startSeq);
    }

    this.state.bufferChunk(seq, text);
    this.state.processBufferedChunks();

    if (!this.state.currentResponse) {
      this.state.scheduleFlush(() => this._updateUIWithCurrentResponse());
      return;
    }

    this._updateUIWithCurrentResponse();
  }

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

  _finalizeResponse() {
    this.state.processBufferedChunks();

    const lastMessage = this.state.getLastMessage();
    if (lastMessage && lastMessage.streaming) {
      lastMessage.streaming = false;
      this._updateMessage(lastMessage);
    }

    this.state.resetResponse();
  }

  _handleMessage(data) {
    console.log('[ChatWindow] Complete message:', data);
    this._finalizeResponse();
  }

  _handleTranscript(data) {
    const text = data.text || '';
    if (!text.trim()) return;

    console.log('[ChatWindow] 🎤 User transcript:', text);

    this._addMessage({
      role: 'user',
      text: text,
      timestamp: Date.now(),
      source: 'voice',
    });

    this.ui.typingIndicator.show();
  }

  _addMessage(message) {
    this.state.addMessage(message);

    const emptyState = this.ui.messageList.querySelector('.empty-state');
    if (emptyState) {
      emptyState.remove();
    }

    const messageEl = this.ui.messageList.createMessageElement(message);
    this.ui.messageList.appendChild(messageEl);
    this.ui.messageList.scrollToBottom();
  }

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

  async _startVoiceInput() {
    if (!window.electronAPI || !window.electronAPI.chat) {
      console.error('[ChatWindow] Electron API not available');
      return;
    }

    try {
      await window.electronAPI.chat.startVoiceInput();
      await this.audioCapture.start();

      console.log('[ChatWindow] Voice input started');
    } catch (error) {
      console.error('[ChatWindow] Failed to start voice input:', error);
      this._showError(`无法启动录音: ${error.message}`);
      this.ui.voiceButton.isRecording = false;
      this.elements.voiceBtn.classList.remove('recording');
    }
  }

  async _stopVoiceInput() {
    if (!window.electronAPI || !window.electronAPI.chat) return;

    try {
      this.audioCapture.stop();
      await window.electronAPI.chat.stopVoiceInput();

      console.log('[ChatWindow] Voice input stopped');
    } catch (error) {
      console.error('[ChatWindow] Failed to stop voice input:', error);
    }
  }

  _sendAudioChunk(audioData) {
    if (!window.electronAPI || !window.electronAPI.chat) return;

    const audioArray = Array.from(audioData);
    window.electronAPI.chat.sendAudioChunk(audioArray);

    if (!this._audioChunkCount) this._audioChunkCount = 0;
    this._audioChunkCount++;
    if (this._audioChunkCount % 30 === 0) {
      console.log(`[ChatWindow] 📤 Sent ${this._audioChunkCount} audio chunks to backend`);
    }
  }

  _updateVolumeIndicator(volume) {
    if (this.elements.volumeIndicator) {
      const amplified = Math.min(1, volume * 5);
      const percentage = Math.round(amplified * 100);
      this.elements.volumeIndicator.style.setProperty('--volume', `${percentage}%`);
      this.elements.volumeIndicator.classList.toggle('active', amplified > 0.05);
    }
  }

  _setSpeaking(isSpeaking) {
    this.state.isSpeaking = isSpeaking;
    this.elements.speakingIndicator.classList.toggle('hidden', !isSpeaking);

    if (window.electronAPI && window.electronAPI.chat) {
      window.electronAPI.chat.setSpeaking(isSpeaking);
    }
  }

  _setStyleTransfer(enabled) {
    this.state.styleTransferEnabled = enabled;
    if (this.elements.styleTransferSwitch) {
      this.elements.styleTransferSwitch.checked = enabled;
    }
    if (this.elements.styleTransferStatus) {
      this.elements.styleTransferStatus.textContent = enabled ? 'ON' : 'OFF';
    }
  }

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

  async _checkConnection() {
    try {
      await window.electronAPI.getVersion();
      this._setConnectionStatus('connected');
    } catch (error) {
      this._setConnectionStatus('disconnected');
    }
  }

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

  _showError(message) {
    const el = document.createElement('div');
    el.className = 'message assistant error';

    const content = document.createElement('div');
    content.className = 'message-content';
    content.style.background = '#f87171';
    content.textContent = message;

    el.appendChild(content);
    this.ui.messageList.appendChild(el);
    this.ui.messageList.scrollToBottom();

    setTimeout(() => el.remove(), 3000);
  }

  destroy() {
    if (this.audioCapture) {
      this.audioCapture.stop();
    }
    this.ipc.cleanup();
    console.log('[ChatWindow] Destroyed');
  }
}
