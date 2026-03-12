/**
 * Chat Window Controller
 * Handles chat UI, messaging, and voice input
 */

class ChatWindow {
  constructor() {
    // UI elements
    this.messageList = document.getElementById('message-list');
    this.messageInput = document.getElementById('message-input');
    this.sendBtn = document.getElementById('send-btn');
    this.voiceBtn = document.getElementById('voice-btn');
    this.connectionStatus = document.getElementById('connection-status');
    this.speakingIndicator = document.getElementById('speaking-indicator');
    this.styleTransferSwitch = document.getElementById('style-transfer-switch');
    this.styleTransferStatus = document.getElementById('style-transfer-status');

    // State
    this.messages = [];
    this.isRecording = false;
    this.isSpeaking = false;
    this.currentResponse = '';
    this.isConnected = false;
    this.styleTransferEnabled = false; // Default disabled

    // Initialize
    this._init();
  }

  /**
   * Initialize chat window
   * @private
   */
  _init() {
    // Setup event listeners
    this._setupEventListeners();

    // Setup IPC listeners
    this._setupIpcListeners();

    // Check connection
    this._checkConnection();

    // Focus input
    this.messageInput.focus();

    console.log('[ChatWindow] Initialized');
  }

  /**
   * Setup DOM event listeners
   * @private
   */
  _setupEventListeners() {
    // Send button
    this.sendBtn.addEventListener('click', () => this._sendMessage());

    // Enter to send, Shift+Enter for new line
    this.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._sendMessage();
      }
    });

    // Auto-resize textarea
    this.messageInput.addEventListener('input', () => {
      this._resizeTextarea();
    });

    // Voice button
    this.voiceBtn.addEventListener('click', () => {
      this._toggleVoiceInput();
    });

    // Title bar controls
    document.querySelectorAll('.control-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = e.target.dataset.action;
        if (window.electronAPI && window.electronAPI.window) {
          switch (action) {
            case 'minimize':
              // Minimize logic would go here
              break;
            case 'close':
              window.electronAPI.window.close();
              break;
          }
        }
      });
    });

    // Style transfer toggle
    if (this.styleTransferSwitch) {
      this.styleTransferSwitch.addEventListener('change', () => {
        this._toggleStyleTransfer();
      });
    }
  }

  /**
   * Setup IPC listeners
   * @private
   */
  _setupIpcListeners() {
    if (!window.electronAPI || !window.electronAPI.chat) {
      console.warn('[ChatWindow] Electron API not available');
      return;
    }

    // Listen for LLM chunks (streaming response)
    window.electronAPI.chat.onLlmChunk((data) => {
      this._handleLlmChunk(data);
    });

    // Listen for messages
    window.electronAPI.chat.onMessage((data) => {
      this._handleMessage(data);
    });

    // Listen for speaking state
    window.electronAPI.chat.onSpeaking((isSpeaking) => {
      this._setSpeaking(isSpeaking);
    });

    // Listen for style transfer state from backend
    if (window.electronAPI.chat.onStyleTransfer) {
      window.electronAPI.chat.onStyleTransfer((enabled) => {
        this.styleTransferEnabled = enabled;
        this.styleTransferSwitch.checked = enabled;
        this.styleTransferStatus.textContent = enabled ? 'ON' : 'OFF';
        console.log('[ChatWindow] Style transfer state synced:', enabled);
      });
    }

    console.log('[ChatWindow] IPC listeners setup');
  }

  /**
   * Send message to backend
   * @private
   */
  async _sendMessage() {
    const text = this.messageInput.value.trim();
    if (!text) return;

    // Add user message to UI
    this._addMessage({
      role: 'user',
      text: text,
      timestamp: Date.now()
    });

    // Clear input
    this.messageInput.value = '';
    this._resizeTextarea();

    // Send to backend
    try {
      if (!window.electronAPI || !window.electronAPI.chat) {
        console.error('[ChatWindow] Electron API not available');
        this._showError('Electron API not available');
        return;
      }

      await window.electronAPI.chat.sendMessage({
        text: text,
        timestamp: Date.now()
      });

      // Show typing indicator
      this._showTypingIndicator();
    } catch (error) {
      console.error('[ChatWindow] Failed to send message:', error);
      this._showError('Failed to send message');
    }
  }

  /**
   * Toggle voice input
   * @private
   */
  async _toggleVoiceInput() {
    if (this.isRecording) {
      await this._stopVoiceInput();
    } else {
      await this._startVoiceInput();
    }
  }

  /**
   * Start voice input
   * @private
   */
  async _startVoiceInput() {
    if (!window.electronAPI || !window.electronAPI.chat) {
      console.warn('[ChatWindow] Electron API not available');
      return;
    }
    try {
      await window.electronAPI.chat.startVoiceInput();
      this.isRecording = true;
      this.voiceBtn.classList.add('recording');
      console.log('[ChatWindow] Voice input started');
    } catch (error) {
      console.error('[ChatWindow] Failed to start voice input:', error);
    }
  }

  /**
   * Stop voice input
   * @private
   */
  async _stopVoiceInput() {
    if (!window.electronAPI || !window.electronAPI.chat) {
      console.warn('[ChatWindow] Electron API not available');
      return;
    }
    try {
      await window.electronAPI.chat.stopVoiceInput();
      this.isRecording = false;
      this.voiceBtn.classList.remove('recording');
      console.log('[ChatWindow] Voice input stopped');
    } catch (error) {
      console.error('[ChatWindow] Failed to stop voice input:', error);
    }
  }

  /**
   * Handle LLM chunk (streaming response)
   * @private
   */
  _handleLlmChunk(data) {
    // Remove typing indicator
    this._hideTypingIndicator();

    // Append to current response
    this.currentResponse += data.text || '';

    // Update or create streaming message
    const lastMessage = this.messages[this.messages.length - 1];
    if (lastMessage && lastMessage.role === 'assistant' && lastMessage.streaming) {
      lastMessage.text = this.currentResponse;
      this._updateMessage(lastMessage);
    } else {
      this._addMessage({
        role: 'assistant',
        text: this.currentResponse,
        timestamp: Date.now(),
        streaming: true
      });
    }
  }

  /**
   * Handle complete message
   * @private
   */
  _handleMessage(data) {
    // Finalize streaming message
    if (this.currentResponse) {
      const lastMessage = this.messages[this.messages.length - 1];
      if (lastMessage && lastMessage.streaming) {
        lastMessage.streaming = false;
        this.currentResponse = '';
        this._updateMessage(lastMessage);
      }
    }
  }

  /**
   * Add message to UI
   * @private
   */
  _addMessage(message) {
    this.messages.push(message);

    // Remove empty state
    const emptyState = this.messageList.querySelector('.empty-state');
    if (emptyState) {
      emptyState.remove();
    }

    // Create message element
    const messageEl = this._createMessageElement(message);
    this.messageList.appendChild(messageEl);

    // Scroll to bottom
    this._scrollToBottom();
  }

  /**
   * Update existing message
   * @private
   */
  _updateMessage(message) {
    const messageEl = document.querySelector(`[data-id="${message.id}"]`);
    if (messageEl) {
      const contentEl = messageEl.querySelector('.message-content');
      if (contentEl) {
        contentEl.textContent = message.text;
        if (message.streaming) {
          contentEl.classList.add('streaming');
        } else {
          contentEl.classList.remove('streaming');
        }
      }
      this._scrollToBottom();
    }
  }

  /**
   * Create message element
   * @private
   */
  _createMessageElement(message) {
    const el = document.createElement('div');
    el.className = `message ${message.role}`;
    el.dataset.id = message.id || `msg-${Date.now()}`;

    const content = document.createElement('div');
    content.className = 'message-content';
    if (message.streaming) {
      content.classList.add('streaming');
    }
    content.textContent = message.text;

    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = new Date(message.timestamp).toLocaleTimeString();

    el.appendChild(content);
    el.appendChild(meta);

    return el;
  }

  /**
   * Show typing indicator
   * @private
   */
  _showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'message assistant typing';
    indicator.id = 'typing-indicator';

    const content = document.createElement('div');
    content.className = 'message-content';

    const dots = document.createElement('div');
    dots.className = 'typing-indicator';
    dots.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

    content.appendChild(dots);
    indicator.appendChild(content);
    this.messageList.appendChild(indicator);

    this._scrollToBottom();
  }

  /**
   * Hide typing indicator
   * @private
   */
  _hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
      indicator.remove();
    }
  }

  /**
   * Set speaking state
   * @private
   */
  _setSpeaking(isSpeaking) {
    this.isSpeaking = isSpeaking;
    if (isSpeaking) {
      this.speakingIndicator.classList.remove('hidden');
    } else {
      this.speakingIndicator.classList.add('hidden');
    }

    // Notify backend
    if (window.electronAPI && window.electronAPI.chat) {
      window.electronAPI.chat.setSpeaking(isSpeaking);
    }
  }

  /**
   * Resize textarea to fit content
   * @private
   */
  _resizeTextarea() {
    this.messageInput.style.height = 'auto';
    this.messageInput.style.height = Math.min(
      this.messageInput.scrollHeight,
      120
    ) + 'px';
  }

  /**
   * Scroll message list to bottom
   * @private
   */
  _scrollToBottom() {
    this.messageList.scrollTop = this.messageList.scrollHeight;
  }

  /**
   * Check connection status
   * @private
   */
  async _checkConnection() {
    try {
      // Try to get config to test connection
      await window.electronAPI.getVersion();
      this._setConnectionStatus('connected');
    } catch (error) {
      this._setConnectionStatus('disconnected');
    }
  }

  /**
   * Set connection status
   * @private
   */
  _setConnectionStatus(status) {
    this.connectionStatus.className = `status ${status}`;

    const statusText = this.connectionStatus.querySelector('.status-text');
    switch (status) {
      case 'connected':
        statusText.textContent = 'Connected';
        this.isConnected = true;
        break;
      case 'disconnected':
        statusText.textContent = 'Disconnected';
        this.isConnected = false;
        break;
      case 'connecting':
        statusText.textContent = 'Connecting...';
        this.isConnected = false;
        break;
    }
  }

  /**
   * Show error message
   * @private
   */
  _showError(message) {
    const el = document.createElement('div');
    el.className = 'message assistant error';
    el.innerHTML = `
      <div class="message-content" style="background: #f87171;">
        ${message}
      </div>
    `;
    this.messageList.appendChild(el);
    this._scrollToBottom();

    // Auto-remove after 3 seconds
    setTimeout(() => el.remove(), 3000);
  }

  /**
   * Toggle style transfer
   * @private
   */
  async _toggleStyleTransfer() {
    if (!window.electronAPI || !window.electronAPI.chat) {
      console.warn('[ChatWindow] Electron API not available');
      return;
    }

    this.styleTransferEnabled = this.styleTransferSwitch.checked;

    // Update status text
    this.styleTransferStatus.textContent = this.styleTransferEnabled ? 'ON' : 'OFF';
    this.styleTransferStatus.className = `toggle-status ${this.styleTransferEnabled ? 'active' : 'inactive'}`;

    // Notify backend
    try {
      await window.electronAPI.chat.setStyleTransfer(this.styleTransferEnabled);
      console.log('[ChatWindow] Style transfer:', this.styleTransferEnabled ? 'enabled' : 'disabled');
    } catch (error) {
      console.error('[ChatWindow] Failed to update style transfer:', error);
    }
  }

  /**
   * Get style transfer state
   * @returns {boolean}
   */
  getStyleTransferEnabled() {
    return this.styleTransferEnabled;
  }
}

// Initialize on load
let chatWindow;
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    chatWindow = new ChatWindow();
  });
} else {
  chatWindow = new ChatWindow();
}

console.log('[Chat] Chat window loaded');
