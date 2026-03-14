const { ipcMain } = require('electron');

/**
 * Register Chat IPC handlers
 * @param {IpcBridge} ipcBridge - IPC bridge instance
 */
function registerChatHandlers(ipcBridge) {
  /**
   * Send chat message to backend
   */
  ipcMain.handle('chat:sendMessage', async (event, message) => {
    try {
      // Forward to backend via Socket.IO
      ipcBridge.sendToBackend('text_input', {
        text: message.text,
        timestamp: message.timestamp || Date.now()
      });

      console.log('[ChatHandler] Message sent to backend:', message.text);
      return { ok: true };
    } catch (error) {
      console.error('[ChatHandler] Failed to send message:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Send audio data for ASR processing
   */
  ipcMain.handle('chat:sendAudio', async (event, audioData) => {
    try {
      ipcBridge.sendToBackend('audio_input', audioData);
      return { ok: true };
    } catch (error) {
      console.error('[ChatHandler] Failed to send audio:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Start voice input
   */
  ipcMain.handle('chat:startVoiceInput', async (event) => {
    try {
      ipcBridge.sendToBackend('voice_start', {});
      return { ok: true };
    } catch (error) {
      console.error('[ChatHandler] Failed to start voice input:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Stop voice input
   */
  ipcMain.handle('chat:stopVoiceInput', async (event) => {
    try {
      ipcBridge.sendToBackend('voice_stop', {});
      return { ok: true };
    } catch (error) {
      console.error('[ChatHandler] Failed to stop voice input:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Get chat history
   */
  ipcMain.handle('chat:getHistory', async (event, limit = 50) => {
    try {
      ipcBridge.sendToBackend('chat_history', { limit });
      return { ok: true, data: [] };
    } catch (error) {
      console.error('[ChatHandler] Failed to get history:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Clear chat history
   */
  ipcMain.handle('chat:clearHistory', async (event) => {
    try {
      ipcBridge.sendToBackend('chat_clear', {});
      console.log('[ChatHandler] Chat history cleared');
      return { ok: true };
    } catch (error) {
      console.error('[ChatHandler] Failed to clear history:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Set speaking state (when TTS is playing)
   */
  ipcMain.handle('chat:setSpeaking', async (event, isSpeaking) => {
    try {
      // Notify Live2D window
      ipcBridge.sendToWindow('live2d', 'chat:speaking', { isSpeaking });

      // Notify backend
      ipcBridge.sendToBackend('chat_speaking', { isSpeaking });

      return { ok: true };
    } catch (error) {
      console.error('[ChatHandler] Failed to set speaking state:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Send typing indicator
   */
  ipcMain.handle('chat:setTyping', async (event, isTyping) => {
    try {
      ipcBridge.sendToBackend('chat_typing', { isTyping });
      return { ok: true };
    } catch (error) {
      console.error('[ChatHandler] Failed to set typing state:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Send audio chunk for VAD processing (high-frequency, use send not invoke)
   */
  let audioChunkCount = 0;
  ipcMain.on('chat:sendAudioChunk', (event, audioData) => {
    audioChunkCount++;
    // Log every 50 chunks (~1.5 seconds at 30ms/chunk) to avoid console spam
    if (audioChunkCount % 50 === 0) {
      console.log(`[ChatHandler] Audio chunks sent: ${audioChunkCount}, samples: ${audioData?.length || 0}`);
    }
    ipcBridge.sendToBackend('raw_audio_data', { audio: audioData });
  });

  /**
   * Set style transfer (Local LLM style migration toggle)
   */
  ipcMain.handle('chat:setStyleTransfer', async (event, enabled) => {
    try {
      console.log('[ChatHandler] Style transfer:', enabled ? 'enabled' : 'disabled');

      // Notify backend via IPC bridge
      ipcBridge.sendToBackend('style_transfer_toggle', { enabled });

      // Also broadcast to all windows for state sync
      ipcBridge.sendToAllWindows('chat:styleTransfer', { enabled });

      return { ok: true };
    } catch (error) {
      console.error('[ChatHandler] Failed to set style transfer:', error);
      return { ok: false, error: error.message };
    }
  });

  console.log('[ChatHandler] Handlers registered');
}

module.exports = { registerChatHandlers };
