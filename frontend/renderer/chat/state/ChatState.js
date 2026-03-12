/**
 * Chat State Management
 * Centralized state for chat window
 */

export class ChatState {
  constructor() {
    // Messages
    this.messages = [];

    // Streaming response state
    this.currentResponse = '';
    this.currentResponseSeq = 0;
    this.responseBuffer = new Map();

    // UI state
    this.isRecording = false;
    this.isSpeaking = false;
    this.isConnected = false;
    this.styleTransferEnabled = false;

    // Fallback timeout for missing chunks
    this._flushTimeout = null;
  }

  /**
   * Reset streaming response state for new response
   * @param {number} startSeq - Optional starting sequence number
   */
  resetResponse(startSeq = null) {
    this.currentResponse = '';
    this.currentResponseSeq = startSeq !== null ? startSeq : 0;
    this.responseBuffer.clear();

    // Clear any pending flush
    if (this._flushTimeout) {
      clearTimeout(this._flushTimeout);
      this._flushTimeout = null;
    }
  }

  /**
   * Add chunk to buffer
   */
  bufferChunk(seq, text) {
    this.responseBuffer.set(seq, text);
  }

  /**
   * Process buffered chunks in order
   * @param {boolean} flushAll - If true, process all chunks even if out of order
   */
  processBufferedChunks(flushAll = false) {
    // Normal ordered processing
    while (this.responseBuffer.has(this.currentResponseSeq)) {
      const chunk = this.responseBuffer.get(this.currentResponseSeq);
      this.currentResponse += chunk;
      this.responseBuffer.delete(this.currentResponseSeq);
      this.currentResponseSeq++;
    }

    // Fallback: if flushAll and we have buffered chunks, process them in order
    if (flushAll && this.responseBuffer.size > 0) {
      const sortedSeqs = Array.from(this.responseBuffer.keys()).sort((a, b) => a - b);
      for (const seq of sortedSeqs) {
        const chunk = this.responseBuffer.get(seq);
        this.currentResponse += chunk;
        this.responseBuffer.delete(seq);
      }
      console.log('[ChatState] Flushed out-of-order chunks');
    }
  }

  /**
   * Schedule a flush to handle missing chunks
   * @param {Function} callback - Called when flush happens
   */
  scheduleFlush(callback, delay = 500) {
    if (this._flushTimeout) {
      clearTimeout(this._flushTimeout);
    }
    this._flushTimeout = setTimeout(() => {
      if (this.responseBuffer.size > 0) {
        this.processBufferedChunks(true);
        callback();
      }
    }, delay);
  }

  /**
   * Add message to list
   */
  addMessage(message) {
    if (!message.id) {
      message.id = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    this.messages.push(message);
    return message;
  }

  /**
   * Get last message
   */
  getLastMessage() {
    return this.messages[this.messages.length - 1];
  }
}
