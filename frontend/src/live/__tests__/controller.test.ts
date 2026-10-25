import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Events, type BilibiliStatusPayload } from '@/shared/contracts/socket-events'
import { createLiveController, type LiveSocket, type LiveView } from '../controller'

const controllers: ReturnType<typeof createLiveController>[] = []

function harness(search = '') {
  const handlers = new Map<string, (...args: unknown[]) => void>()
  const socket: LiveSocket & { emit: ReturnType<typeof vi.fn> } = {
    on: vi.fn((event, handler) => {
      handlers.set(event, handler)
      return socket
    }),
    off: vi.fn((event, handler) => {
      if (handlers.get(event) === handler) handlers.delete(event)
      return socket
    }),
    emit: vi.fn(),
  }
  const view = {
    renderMessages: vi.fn(),
    setSocketState: vi.fn(),
    setLivestreamStatus: vi.fn(),
    setBilibiliReplyEvidence: vi.fn(),
    setCollapsed: vi.fn(),
    setBackground: vi.fn(),
    setSubtitle: vi.fn(),
    setSubtitleEnabled: vi.fn(),
    bindSubtitleToggle: vi
      .fn<NonNullable<LiveView['bindSubtitleToggle']>>()
      .mockReturnValue(vi.fn()),
    bindToggle: vi.fn(),
  } satisfies LiveView & {
    setCollapsed: ReturnType<typeof vi.fn>
    bindToggle: ReturnType<typeof vi.fn>
  }
  const controller = createLiveController({
    socket,
    view,
    search: new URLSearchParams(search),
  })
  controllers.push(controller)
  return { controller, handlers, socket, view }
}

function status(state: BilibiliStatusPayload['state']): BilibiliStatusPayload {
  return {
    state,
    connected: state === 'prelive' || state === 'live',
    room_id: null,
    desired_room_id: 123,
    retry_count: 2,
    error_code: null,
    generation_id: 1,
    message: state,
    updated_at: 1,
  }
}

describe('standalone live controller', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => {
    controllers.splice(0).forEach((controller) => controller.dispose())
    vi.useRealTimers()
  })

  it('lets the live page restore a disabled caption without waiting for another reply', () => {
    localStorage.setItem(
      'animetta_subtitle_config',
      JSON.stringify({ enabled: false, fontSize: 20 }),
    )
    const { handlers, view } = harness()
    handlers.get(Events.CHAT.SENTENCE)!({
      task_id: 'phone-turn',
      turn_id: 'phone-turn',
      text: '手机字幕',
      seq: 0,
    })
    expect(view.setSubtitle).toHaveBeenLastCalledWith(null)
    expect(view.setSubtitleEnabled).toHaveBeenLastCalledWith(false)
    view.bindSubtitleToggle.mock.calls[0][0]()
    expect(view.setSubtitle).toHaveBeenLastCalledWith('手机字幕')
    expect(view.setSubtitleEnabled).toHaveBeenLastCalledWith(true)
    expect(JSON.parse(localStorage.getItem('animetta_subtitle_config')!)).toEqual({
      enabled: true,
      fontSize: 20,
    })
  })

  it('uses canonical events and never emits room lifecycle commands', () => {
    const { handlers, socket } = harness()

    expect(handlers.has(Events.BILIBILI.DANMAKU)).toBe(true)
    expect(handlers.has(Events.BILIBILI.DANMAKU_STATUS)).toBe(true)
    expect(handlers.has(Events.BILIBILI.DANMAKU_AI_REPLY)).toBe(true)
    expect(handlers.has('danmaku')).toBe(false)
    expect(socket.emit).not.toHaveBeenCalled()
  })

  it('keeps only the newest 500 messages', () => {
    vi.useFakeTimers()
    const { controller, handlers } = harness()
    const onDanmaku = handlers.get(Events.BILIBILI.DANMAKU)!

    for (let i = 0; i < 501; i++) {
      onDanmaku({ text: `m${i}`, user_name: 'u', user_id: i, timestamp: i })
    }
    vi.runAllTimers()

    expect(controller.messages).toHaveLength(500)
    expect(controller.messages[0].text).toBe('m1')
    expect(controller.messages[499].text).toBe('m500')
  })

  it('coalesces a danmaku burst into one render frame', () => {
    vi.useFakeTimers()
    const { handlers, view } = harness()
    const onDanmaku = handlers.get(Events.BILIBILI.DANMAKU)!

    for (let index = 0; index < 10; index++) {
      onDanmaku({ text: `m${index}`, user_name: 'u', user_id: index, timestamp: index })
    }

    expect(view.renderMessages).not.toHaveBeenCalled()
    vi.runAllTimers()
    expect(view.renderMessages).toHaveBeenCalledOnce()
    expect(view.renderMessages).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ text: 'm9' })]),
    )
  })

  it('renders reconnect state from the backend snapshot', () => {
    const { handlers, view } = harness()

    handlers.get(Events.BILIBILI.DANMAKU_STATUS)!(status('reconnecting'))

    expect(view.setLivestreamStatus).toHaveBeenCalledWith(status('reconnecting'))
  })

  it('retains the Bilibili source and reply identities for playback acceptance', () => {
    const { controller, handlers, socket, view } = harness()
    const reply = { source_message_id: 'source-1', reply_id: 'reply-1' }

    handlers.get(Events.BILIBILI.DANMAKU_AI_REPLY)!(reply)

    expect(view.setBilibiliReplyEvidence).toHaveBeenCalledWith(reply)
    controller.dispose()
    expect(socket.off).toHaveBeenCalledWith(Events.BILIBILI.DANMAKU_AI_REPLY, expect.any(Function))
  })

  it('applies background query parameters through the view boundary', () => {
    const { view } = harness('bg=%E6%A3%AE%E6%9E%97.png&bgOpacity=0.65&bgPosition=top')

    expect(view.setBackground).toHaveBeenCalledWith({
      file: '森林.png',
      opacity: 0.65,
      position: 'top',
    })
  })

  it('uses the warm studio background when no override is provided', () => {
    const { view } = harness()

    expect(view.setBackground).toHaveBeenCalledWith({
      file: '温馨直播室.png',
      opacity: 0.9,
      position: 'center',
    })
  })

  it('leaves review fixture injection to the selected socket runtime', () => {
    const normal = harness()
    const demo = harness('demo=1')

    expect(normal.controller.messages).toHaveLength(0)
    expect(demo.controller.messages).toHaveLength(0)
    expect(demo.view.setLivestreamStatus).not.toHaveBeenCalled()
  })

  it('does not bind the removed collapse interaction', () => {
    const { view } = harness()

    expect(view.bindToggle).not.toHaveBeenCalled()
    expect(view.setCollapsed).not.toHaveBeenCalled()
  })

  it('renders only the active public reply as a temporary subtitle', () => {
    vi.useFakeTimers()
    const { handlers, view } = harness()
    const identity = {
      message_id: 'message',
      conversation_id: 'conversation',
      task_id: 'task',
      turn_id: 'task',
    }

    handlers.get(Events.CHAT.SENTENCE)!({ ...identity, seq: 0, text: '开发者刚刚在后台提到测试。' })
    handlers.get(Events.CHAT.SENTENCE)!({ ...identity, seq: 1, text: '', is_complete: true })

    expect(view.setSubtitle).toHaveBeenLastCalledWith('开发者刚刚在后台提到测试。')
    handlers.get(Events.CHAT.CONTROL)!({ ...identity, signal: 'conversation-end' })
    vi.advanceTimersByTime(6000)
    expect(view.setSubtitle).toHaveBeenLastCalledWith(null)
  })

  it('keeps the completed text while TTS synthesis takes longer than six seconds', () => {
    vi.useFakeTimers()
    const { controller, handlers, view } = harness()
    const identity = { task_id: 'slow-tts', turn_id: 'slow-tts' }
    handlers.get(Events.CHAT.SENTENCE)!({ ...identity, seq: 0, text: '等声音合成完成再收起。' })
    handlers.get(Events.CHAT.SENTENCE)!({ ...identity, seq: 1, text: '', is_complete: true })
    vi.advanceTimersByTime(10000)
    expect(view.setSubtitle).toHaveBeenLastCalledWith('等声音合成完成再收起。')
    controller.setChatPlaybackState('slow-tts', 'pending')
    handlers.get(Events.CHAT.CONTROL)!({ ...identity, signal: 'conversation-end' })
    controller.setChatPlaybackState('slow-tts', 'playing')
    vi.advanceTimersByTime(10000)
    expect(view.setSubtitle).toHaveBeenLastCalledWith('等声音合成完成再收起。')
    controller.setChatPlaybackState('slow-tts', 'completed')
    vi.advanceTimersByTime(1500)
    expect(view.setSubtitle).toHaveBeenLastCalledWith(null)
  })

  it('keeps subtitles through pending and playing audio until actual completion', () => {
    vi.useFakeTimers()
    const { controller, handlers, view } = harness()
    const identity = { task_id: 'task', turn_id: 'task' }
    handlers.get(Events.CHAT.SENTENCE)!({ ...identity, seq: 0, text: '一句需要说完的话。' })
    controller.setChatPlaybackState('task', 'pending')
    handlers.get(Events.CHAT.SENTENCE)!({ ...identity, seq: 1, is_complete: true })
    handlers.get(Events.CHAT.CONTROL)!({ ...identity, signal: 'conversation-end' })
    vi.advanceTimersByTime(10000)
    expect(view.setSubtitle).toHaveBeenLastCalledWith('一句需要说完的话。')
    controller.setChatPlaybackState('task', 'playing')
    vi.advanceTimersByTime(20000)
    expect(view.setSubtitle).toHaveBeenLastCalledWith('一句需要说完的话。')
    controller.setChatPlaybackState('task', 'completed')
    vi.advanceTimersByTime(1499)
    expect(view.setSubtitle).toHaveBeenLastCalledWith('一句需要说完的话。')
    vi.advanceTimersByTime(1)
    expect(view.setSubtitle).toHaveBeenLastCalledWith(null)
  })

  it('ignores old playback completion and falls back when playback fails', () => {
    vi.useFakeTimers()
    const { controller, handlers, view } = harness()
    handlers.get(Events.CHAT.SENTENCE)!({ task_id: 'old', turn_id: 'old', seq: 0, text: '旧话' })
    controller.setChatPlaybackState('old', 'playing')
    handlers.get(Events.CHAT.SENTENCE)!({ task_id: 'new', turn_id: 'new', seq: 0, text: '新话' })
    controller.setChatPlaybackState('new', 'pending')
    controller.setChatPlaybackState('old', 'completed')
    vi.advanceTimersByTime(10000)
    expect(view.setSubtitle).toHaveBeenLastCalledWith('新话')
    controller.setChatPlaybackState('new', 'cancelled')
    vi.advanceTimersByTime(1500)
    expect(view.setSubtitle).toHaveBeenLastCalledWith(null)
  })

  it('restores saved visibility and updates it during playback without losing the caption', () => {
    const key = 'animetta_subtitle_config'
    localStorage.setItem(key, JSON.stringify({ enabled: false }))
    const { handlers, view } = harness()
    handlers.get(Events.CHAT.SENTENCE)!({
      task_id: 'task',
      turn_id: 'task',
      seq: 0,
      text: '正在说话',
    })
    expect(view.setSubtitle).toHaveBeenLastCalledWith(null)
    window.dispatchEvent(new StorageEvent('storage', { key, newValue: '{"enabled":true}' }))
    expect(view.setSubtitle).toHaveBeenLastCalledWith('正在说话')
    window.dispatchEvent(new StorageEvent('storage', { key, newValue: '{"enabled":false}' }))
    expect(view.setSubtitle).toHaveBeenLastCalledWith(null)
    window.dispatchEvent(new StorageEvent('storage', { key, newValue: 'invalid' }))
    expect(view.setSubtitle).toHaveBeenLastCalledWith('正在说话')
  })
})
