/**
 * Chat Module Entry Point
 */

import { ChatWindow } from './ChatWindow.js';

// Export all components
export { ChatWindow };
export { ChatState } from './state/ChatState.js';
export { MessageList } from './ui/MessageList.js';
export { InputBar } from './ui/InputBar.js';
export { VoiceButton } from './ui/VoiceButton.js';
export { TypingIndicator } from './ui/TypingIndicator.js';
export { IpcListeners } from './ipc/IpcListeners.js';

// Initialize on load
let chatWindow;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    chatWindow = new ChatWindow();
  });
} else {
  chatWindow = new ChatWindow();
}

// console.log('[Chat] Chat window loaded');
