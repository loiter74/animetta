import type { LiveSocket } from '@/shared/transport/liveSocket'
import {
  CHAT_EMOTIONS,
  ChatEmotionEvents,
  type ChatEmotion,
} from '@/shared/contracts/socket-events'

const EMOTIONS = new Set<ChatEmotion>(CHAT_EMOTIONS)

interface EmotionTarget {
  setEmotion(emotion: string): void
  resetEmotion(): void
}

function correlatedFrame(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const frame = value as Record<string, unknown>
  if (
    !['message_id', 'conversation_id', 'task_id', 'turn_id'].every(
      (key) => typeof frame[key] === 'string' && frame[key] !== '',
    ) ||
    frame.task_id !== frame.turn_id
  ) {
    return null
  }
  return frame
}

/** Keep public emotion updates attached to the current conversation turn. */
export function bindLive2DEmotionSocket(socket: LiveSocket, target: EmotionTarget): () => void {
  let activeTask: string | null = null
  let canBootstrap = true
  let disposed = false
  const retiredTasks = new Set<string>()

  const activate = (taskId: string): void => {
    if (retiredTasks.has(taskId) || taskId === activeTask) return
    if (activeTask) retiredTasks.add(activeTask)
    activeTask = taskId
    canBootstrap = false
    target.resetEmotion()
  }
  const reset = (): void => {
    if (activeTask) retiredTasks.add(activeTask)
    activeTask = null
    canBootstrap = false
    target.resetEmotion()
  }
  const onControl = (value: unknown): void => {
    if (disposed) return
    const frame = correlatedFrame(value)
    if (frame?.signal === 'conversation-start') activate(frame.task_id as string)
  }
  const onSentence = (value: unknown): void => {
    if (disposed) return
    const frame = correlatedFrame(value)
    if (frame?.seq === 0) activate(frame.task_id as string)
  }
  const onEmotion = (value: unknown): void => {
    if (disposed) return
    const frame = correlatedFrame(value)
    if (!frame || !EMOTIONS.has(frame.emotion as ChatEmotion)) return
    const taskId = frame.task_id as string
    if (retiredTasks.has(taskId)) return
    // A page opened mid-turn may miss its start, but later unknown turns must start explicitly.
    if (canBootstrap) activate(taskId)
    if (taskId === activeTask) target.setEmotion(frame.emotion as ChatEmotion)
  }
  const onStop = (value: unknown): void => {
    if (disposed) return
    const frame = correlatedFrame(value)
    if (frame && frame.task_id === activeTask) reset()
  }
  const onDisconnect = (): void => {
    if (!disposed) reset()
  }
  const handlers: ReadonlyArray<readonly [string, (...args: unknown[]) => void]> = [
    [ChatEmotionEvents.CONTROL, onControl],
    [ChatEmotionEvents.SENTENCE, onSentence],
    [ChatEmotionEvents.EXPRESSION, onEmotion],
    [ChatEmotionEvents.AUDIO_STREAM_START, onEmotion],
    [ChatEmotionEvents.STOP_AUDIO, onStop],
    ['disconnect', onDisconnect],
  ]
  for (const [event, handler] of handlers) socket.on(event, handler)
  return () => {
    if (disposed) return
    disposed = true
    for (const [event, handler] of handlers) socket.off(event, handler)
    retiredTasks.clear()
  }
}
