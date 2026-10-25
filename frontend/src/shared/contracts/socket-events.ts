import events from '../../../../config/socket-events.json'

// 从 JSON 推断类型
type EventConfig = {
  name: string
  payload: Record<string, unknown>
  ack?: Record<string, unknown>
}

type ModuleEvents = Record<string, EventConfig>

type SocketEventsConfig = Record<string, ModuleEvents>

// 类型断言
const socketEvents = events as SocketEventsConfig

export const PublicLiveEvents = {
  ACTIVITY_PROJECTION: socketEvents.minecraft.activity_projection.name,
  NARRATION_STATE: socketEvents.livestream.narration_state.name,
} as const

export const ChatEmotionEvents = {
  CONTROL: socketEvents.chat.control.name,
  SENTENCE: socketEvents.chat.sentence.name,
  EXPRESSION: socketEvents.chat.expression.name,
  AUDIO_STREAM_START: socketEvents.chat.audio_stream_start.name,
  STOP_AUDIO: socketEvents.chat.stop_audio.name,
} as const

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error'

export type CommandTaskStatus =
  'accepted' | 'processing' | 'succeeded' | 'failed' | 'cancelled' | 'interrupted'

export interface CommandTaskSnapshot {
  kind: string
  task_id: string
  status: CommandTaskStatus
  progress: Record<string, unknown> | null
  result: Record<string, unknown> | null
  error: { code: string; message: string } | null
  reused: boolean
  created_at: number
  updated_at: number
}

export interface ChatIdentity {
  message_id: string
  conversation_id: string
  task_id: string
  turn_id: string
}

export interface ChatCommandPayload extends ChatIdentity {
  text: string
  source: 'text'
  is_inspection: false
  is_acceptance: boolean
  user_id?: string
  from_name?: string
}

/**
 * Payload for the `sentence` socket event (LLM streaming response).
 * Extended with optional translation fields for bilingual subtitle support.
 */
export interface SentenceEvent extends ChatIdentity {
  text: string
  seq: number
  is_complete?: boolean
  /** Original language code (e.g. "zh", "en") */
  lang?: string
  /** Translated text in the target language */
  translation?: string
  /** Target language code (e.g. "en", "ja") */
  target_lang?: string
  /** Optional workflow/effect metadata for expression effects. */
  metadata?: Record<string, unknown>
}

/** Payload for `chat:subtitle_translation` server-to-client event */
export interface SubtitleTranslationEvent extends ChatIdentity {
  translation: string
  target_lang?: string
}

export interface ChatControlEvent extends ChatIdentity {
  signal?: 'conversation-start' | 'conversation-end'
  type?: string
  text?: string
  status?: 'degraded'
}

export interface ParameterTimelineParameter {
  name: string
  value: number
  duration: number
}

export interface ParameterTimelineFrame {
  timestamp: number
  parameters: ParameterTimelineParameter[]
}

export interface ParameterTimeline {
  frames: ParameterTimelineFrame[]
  total_duration?: number
}

export type {
  Live2DPerformanceAccent,
  Live2DPerformanceBase,
  Live2DPerformancePlanV1,
} from '@/shared/live2d/performanceContract'
import type { Live2DPerformancePlanV1 } from '@/shared/live2d/performanceContract'

export interface AudioWithExpressionEvent extends ChatIdentity {
  audio_data: string
  format: string
  volumes?: number[]
  use_parameter_mapping?: boolean
  expressions?: ParameterTimeline
  return_to_idle?: boolean
  performance?: Live2DPerformancePlanV1
}

export const CHAT_EMOTIONS = ['neutral', 'happy', 'sad', 'angry', 'surprised', 'thinking'] as const
export type ChatEmotion = (typeof CHAT_EMOTIONS)[number]

export interface AudioStreamStartEvent extends ChatIdentity {
  stream_id: string
  format: 'pcm_s16le'
  sample_rate: 24000
  channels: 1
  emotion: ChatEmotion
  performance?: Live2DPerformancePlanV1
}

export interface AudioStreamChunkEvent extends ChatIdentity {
  stream_id: string
  sequence: number
  audio_data: string
}

export interface AudioStreamEndEvent extends ChatIdentity {
  stream_id: string
  final_sequence: number
  status: 'completed' | 'failed' | 'cancelled'
  reason?: 'timeout' | 'provider_error' | 'cancelled'
}

export type MinecraftPublicActivityOutcome =
  'active' | 'succeeded' | 'failed' | 'cancelled' | 'blocked'

export type MinecraftPublicActivityPhase =
  'planning' | 'observing' | 'committed' | 'acting' | 'checking' | 'recovering' | 'finished'

export type MinecraftPublicActivityIntent =
  | 'acquire'
  | 'craft'
  | 'build'
  | 'travel'
  | 'combat'
  | 'survive'
  | 'learn'
  | 'discover'
  | 'interact'

export type MinecraftPublicActivityFocusKind =
  'item' | 'entity' | 'place' | 'structure' | 'condition'

export type MinecraftPublicActivityProgressUnit = 'objectives' | 'items' | 'blocks' | 'actions'

export interface MinecraftPublicActivityFocus {
  kind: MinecraftPublicActivityFocusKind
  label: string
}

export interface MinecraftPublicActivityProgress {
  current: number
  total: number
  unit: MinecraftPublicActivityProgressUnit
}

export interface MinecraftPublicActivityPayload {
  phase: MinecraftPublicActivityPhase
  intent?: MinecraftPublicActivityIntent
  focus?: MinecraftPublicActivityFocus
  progress?: MinecraftPublicActivityProgress
  outcome: MinecraftPublicActivityOutcome
}

export interface MinecraftActivityProjectionEvent {
  schema_version: '1'
  event: 'minecraft.activity.projection'
  event_id: string
  projection_kind: 'activity'
  projection_version: number
  occurred_at_ms: number
  mission_id?: string
  entity_id: 'minecraft'
  payload: MinecraftPublicActivityPayload
}

export type LivestreamNarrationSpeechState =
  'none' | 'queued' | 'speaking' | 'completed' | 'cancelled'

export type LivestreamNarrationEmotion = 'thinking' | 'confident' | 'focused' | 'alert' | 'relieved'

export interface LivestreamNarrationStateEvent {
  schema_version: '1'
  cue_id: string
  source_event_id: string
  task_id?: string
  phase: MinecraftPublicActivityPhase
  visual_text: string
  emotion: LivestreamNarrationEmotion
  speech_state: LivestreamNarrationSpeechState
  occurred_at_ms: number
}

export interface ChatErrorEvent extends ChatIdentity {
  type: 'validation_error' | 'processing_error' | 'timeout' | 'interrupted' | 'internal_error'
  message: string
  component: string
  phase: string
  retryable: boolean
  terminal: boolean
}

export interface SandboxHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SandboxRequestEvent extends ChatIdentity {
  text: string
  history: SandboxHistoryMessage[]
}

export interface SandboxChunkEvent extends ChatIdentity {
  text: string
  seq: number
  provider: string
  model?: string | null
  is_complete?: boolean
  error_code?: string | null
}

/**
 * 事件常量 - 用于 socket.emit() 和 socket.on()。
 *
 * socket.emit(Events.CHAT.TEXT, { text: 'hello' })
 */
export const Events = {
  EARTH: {
    CONTROL: socketEvents.earth.control.name,
    CONTEXT: socketEvents.earth.context.name,
    RESULT: socketEvents.earth.result.name,
    STATE: socketEvents.earth.state.name,
    COMMAND: socketEvents.earth.command.name,
    NARRATION: socketEvents.earth.narration.name,
  },
  TOOL: {
    APPROVAL_REQUIRED: socketEvents.tool.approval_required.name,
    APPROVAL_LIST: socketEvents.tool.approval_list.name,
    APPROVAL_DECIDE: socketEvents.tool.approval_decide.name,
    APPROVAL_RESOLVED: socketEvents.tool.approval_resolved.name,
  },
  TASK: {
    STATUS: socketEvents.task.status.name,
    SNAPSHOT: socketEvents.task.snapshot.name,
  },
  CHAT: {
    TEXT: socketEvents.chat.text.name,
    DEVELOPER_TEXT: socketEvents.chat.developer_text.name,
    SANDBOX_REQUEST: socketEvents.chat.sandbox_request.name,
    SANDBOX_CANCEL: socketEvents.chat.sandbox_cancel.name,
    SANDBOX_CHUNK: socketEvents.chat.sandbox_chunk.name,
    AUDIO: socketEvents.chat.audio.name,
    AUDIO_END: socketEvents.chat.audio_end.name,
    INTERRUPT: socketEvents.chat.interrupt.name,
    SENTENCE: socketEvents.chat.sentence.name,
    CONTROL: socketEvents.chat.control.name,
    TRANSCRIPT: socketEvents.chat.transcript.name,
    STOP_AUDIO: socketEvents.chat.stop_audio.name,
    AUDIO_WITH_EXPRESSION: socketEvents.chat.audio_with_expression.name,
    AUDIO_STREAM_START: socketEvents.chat.audio_stream_start.name,
    AUDIO_STREAM_CHUNK: socketEvents.chat.audio_stream_chunk.name,
    AUDIO_STREAM_END: socketEvents.chat.audio_stream_end.name,
    SUBTITLE_TRANSLATION: socketEvents.chat.subtitle_translation.name,
    LIVE2D_ACTION: socketEvents.chat.live2d_action.name,
    EXPRESSION: socketEvents.chat.expression.name,
  },
  HISTORY: {
    LIST: socketEvents.history.list.name,
    FETCH: socketEvents.history.fetch.name,
    CLEAR: socketEvents.history.clear.name,
    CREATE: socketEvents.history.create.name,
  },
  CONFIG: {
    SWITCH: socketEvents.config.switch.name,
    LOG_LEVEL: socketEvents.config.log_level.name,
    GET: socketEvents.config.get.name,
    SWITCHED: socketEvents.config.switched.name,
    LOG_LEVEL_CHANGED: socketEvents.config.log_level_changed.name,
    DATA: socketEvents.config.data.name,
    HEARTBEAT_ACK: socketEvents.config.heartbeat_ack.name,
  },
  SYSTEM: {
    HEARTBEAT: socketEvents.system.heartbeat.name,
    CONNECTION_ESTABLISHED: socketEvents.system.connection_established.name,
    MODEL_STATUS: socketEvents.system.model_status.name,
    ERROR: socketEvents.system.error.name,
  },
  DESKTOP: {
    REGISTER: socketEvents.desktop.register.name,
    LIVE2D_ACTION: socketEvents.desktop.live2d_action.name,
    CHAT_MESSAGE: socketEvents.desktop.chat_message.name,
    VOICE_START: socketEvents.desktop.voice_start.name,
    VOICE_STOP: socketEvents.desktop.voice_stop.name,
    REGISTERED: socketEvents.desktop.registered.name,
    ACTION_QUEUED: socketEvents.desktop.action_queued.name,
    VOICE_STARTED: socketEvents.desktop.voice_started.name,
    VOICE_STOPPED: socketEvents.desktop.voice_stopped.name,
  },
  BILIBILI: {
    CONNECT: socketEvents.bilibili.connect.name,
    DISCONNECT: socketEvents.bilibili.disconnect.name,
    UPDATE_ROOM: socketEvents.bilibili.update_room.name,
    DANMAKU: socketEvents.bilibili.danmaku.name,
    DANMAKU_STATUS: socketEvents.bilibili.danmaku_status.name,
    LIVE_EVENT: socketEvents.bilibili.live_event.name,
    DANMAKU_AI_REPLY: socketEvents.bilibili.danmaku_ai_reply.name,
  },
  MINECRAFT: {
    CONNECT: socketEvents.minecraft.connect.name,
    STATUS: socketEvents.minecraft.status.name,
    DISCONNECT: socketEvents.minecraft.disconnect.name,
    SHUTDOWN: socketEvents.minecraft.shutdown.name,
    REATTACH_VIEWER: socketEvents.minecraft.reattach_viewer.name,
    VIEWER_STATUS: socketEvents.minecraft.viewer_status.name,
    COMMAND_TRANSITION: socketEvents.minecraft.command_transition.name,
    SKILL_TRUST: socketEvents.minecraft.skill_trust.name,
    MISSION_PROJECTION: socketEvents.minecraft.mission_projection.name,
    OBJECTIVE_PROJECTION: socketEvents.minecraft.objective_projection.name,
    PROPOSAL_PROJECTION: socketEvents.minecraft.proposal_projection.name,
    DISCOVERY_PROJECTION: socketEvents.minecraft.discovery_projection.name,
    SKILL_VALIDATION: socketEvents.minecraft.skill_validation.name,
    ADVANCEMENT_PROJECTION: socketEvents.minecraft.advancement_projection.name,
    STAGE_PROJECTION: socketEvents.minecraft.stage_projection.name,
    ACTIVITY_PROJECTION: socketEvents.minecraft.activity_projection.name,
    BOT_STATE: socketEvents.minecraft.bot_state.name,
  },
  LIVESTREAM: {
    NARRATION_STATE: socketEvents.livestream.narration_state.name,
  },
  TRANSLATION: {
    CONFIGURE: socketEvents.translation.configure.name,
    STATUS: socketEvents.translation.status.name,
  },
  PERSONA: {
    LIST: socketEvents.persona.list.name,
    SET: socketEvents.persona.set.name,
    SET_MODE: socketEvents.persona.set_mode.name,
    UPDATED: socketEvents.persona.updated.name,
    PERSONALITY_UPDATED: socketEvents.persona.personality_updated.name,
  },
  MEMORY: {
    LIST: socketEvents.memory.list.name,
    GET: socketEvents.memory.get.name,
    SEARCH: socketEvents.memory.search.name,
    PIN: socketEvents.memory.pin.name,
    FORGET: socketEvents.memory.forget.name,
    CHANGE: socketEvents.memory.change.name,
    JOB: socketEvents.memory.job.name,
    CHANGED: socketEvents.memory.changed.name,
    ORGANIZE: socketEvents.memory.organize.name,
    LIST_PAGES: socketEvents.memory.list_pages.name,
    ORGANIZE_PROGRESS: socketEvents.memory.organize_progress.name,
    ORGANIZE_RESULT: socketEvents.memory.organize_result.name,
  },
  SING: {
    PROCESS: socketEvents.sing.process.name,
    CONFIRM_LYRICS: socketEvents.sing.confirm_lyrics.name,
    CANCEL: socketEvents.sing.cancel.name,
    SUBTITLE_SYNC: socketEvents.sing.subtitle_sync.name,
    PROGRESS: socketEvents.sing.progress.name,
    COMPLETE: socketEvents.sing.complete.name,
    ERROR: socketEvents.sing.error.name,
    LYRICS_READY: socketEvents.sing.lyrics_ready.name,
    SUBTITLE_LINE: socketEvents.sing.subtitle_line.name,
  },
  MEME: {
    ADD: socketEvents.meme.add.name,
    LIST: socketEvents.meme.list.name,
    REVIEW: socketEvents.meme.review.name,
    DATASET: socketEvents.meme.dataset.name,
    COLLECT: socketEvents.meme.collect.name,
  },
} as const

export interface SingCompletePayload {
  task_id: string
  audio_url: string
  subtitle_url?: string
  tts_audio_url?: string
  vocals_url?: string
  original_url?: string
  video_title?: string
  duration: number
  voice_conversion_applied: boolean
  voice_provider: string
  voice_model: string
  voice_revision: string
  voice_name: string
  lyrics?: Array<{ text: string; translation: string; start_ms: number; end_ms: number }>
  volumes?: number[]
}

export type LivestreamState =
  'stopped' | 'connecting' | 'prelive' | 'live' | 'reconnecting' | 'stopping' | 'error'

export interface BilibiliCommandAck {
  accepted: boolean
  state: LivestreamState
  error_code: string | null
  message: string
}

export interface BilibiliStatusPayload {
  state: LivestreamState
  connected: boolean
  room_id: number | null
  desired_room_id: number | null
  retry_count: number
  error_code: string | null
  generation_id: number
  message: string
  updated_at: number
}

// 导出原始 JSON 配置（用于验证脚本）
export { socketEvents }
