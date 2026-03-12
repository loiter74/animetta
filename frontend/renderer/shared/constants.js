/**
 * Shared Constants
 * Common constants used across the application
 */

// IPC Channels
const IPC_CHANNELS = {
  // Live2D
  LIVE2D_LOAD_MODEL: 'live2d:loadModel',
  LIVE2D_SET_EXPRESSION: 'live2d:setExpression',
  LIVE2D_PLAY_MOTION: 'live2d:playMotion',
  LIVE2D_SET_PARAM: 'live2d:setParam',
  LIVE2D_SET_MOUTH_OPEN: 'live2d:setMouthOpen',
  LIVE2D_EXECUTE_ACTION: 'live2d:executeAction',
  LIVE2D_GET_MODEL_INFO: 'live2d:getModelInfo',

  // Chat
  CHAT_SEND_MESSAGE: 'chat:sendMessage',
  CHAT_SEND_AUDIO: 'chat:sendAudio',
  CHAT_START_VOICE: 'chat:startVoiceInput',
  CHAT_STOP_VOICE: 'chat:stopVoiceInput',
  CHAT_GET_HISTORY: 'chat:getHistory',
  CHAT_CLEAR_HISTORY: 'chat:clearHistory',
  CHAT_SET_SPEAKING: 'chat:setSpeaking',
  CHAT_SET_TYPING: 'chat:setTyping',

  // App
  APP_GET_CONFIG: 'app:getConfig',
  APP_GET_VERSION: 'app:getVersion'
};

// Events from backend
const BACKEND_EVENTS = {
  LLM_CHUNK: 'llm:chunk',
  LIVE2D_ACTION: 'live2d:action',
  AUDIO_STREAM: 'audio:stream',
  CHAT_MESSAGE: 'chat:message',
  CHAT_SPEAKING: 'chat:speaking'
};

// Message roles
const MESSAGE_ROLES = {
  USER: 'user',
  ASSISTANT: 'assistant',
  SYSTEM: 'system'
};

// Action types
const ACTION_TYPES = {
  EXPRESSION: 'expression',
  MOTION: 'motion',
  PARAM: 'param',
  SEQUENCE: 'sequence',
  WAIT: 'wait'
};

// Connection status
const CONNECTION_STATUS = {
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting'
};

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    IPC_CHANNELS,
    BACKEND_EVENTS,
    MESSAGE_ROLES,
    ACTION_TYPES,
    CONNECTION_STATUS
  };
}
