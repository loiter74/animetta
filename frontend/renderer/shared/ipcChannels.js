/**
 * IPC Channels - 所有 IPC 频道名常量
 */

export const IPC_CHANNELS = {
  // Live2D
  LIVE2D_LOAD_MODEL: 'live2d:loadModel',
  LIVE2D_SET_EXPRESSION: 'live2d:setExpression',
  LIVE2D_PLAY_MOTION: 'live2d:playMotion',
  LIVE2D_SET_PARAM: 'live2d:setParam',
  LIVE2D_SET_MOUTH: 'live2d:setMouthOpen',
  LIVE2D_EXECUTE_ACTION: 'live2d:executeAction',
  LIVE2D_ACTION: 'live2d:action',

  // Audio
  AUDIO_STREAM: 'audio:stream',
  AUDIO_WITH_EXPRESSION: 'audio:with-expression',

  // Display
  DISPLAY_SET_STRATEGY: 'display:setScaleStrategy',
  DISPLAY_ZOOM: 'display:zoom',
  DISPLAY_SET_SCALE: 'display:setUserScale',
  DISPLAY_RESET_SCALE: 'display:resetScale',
  DISPLAY_MOVE_MODEL: 'display:moveModel',
  DISPLAY_RESET_POS: 'display:resetModelPosition',
  DISPLAY_SET_BG: 'display:setBackgroundMode',
  DISPLAY_CYCLE_BG: 'display:cycleBackgroundMode',
  DISPLAY_SET_TOP: 'display:setAlwaysOnTop',
  DISPLAY_SET_CLICK_THROUGH: 'display:setClickThrough',
  DISPLAY_GET_CONFIG: 'display:getConfig',
  DISPLAY_SAVE_CONFIG: 'display:saveConfig',

  // Chat
  CHAT_SEND: 'chat:sendMessage',
  CHAT_SEND_AUDIO: 'chat:sendAudio',
  CHAT_START_VOICE: 'chat:startVoiceInput',
  CHAT_STOP_VOICE: 'chat:stopVoiceInput',
  CHAT_SET_SPEAKING: 'chat:setSpeaking',
  CHAT_LLM_CHUNK: 'llm:chunk',
  CHAT_MESSAGE: 'chat:message',

  // Window
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_CLOSE: 'window:close',

  // App
  APP_GET_VERSION: 'app:getVersion',
  APP_GET_CONFIG: 'app:getConfig',
};
