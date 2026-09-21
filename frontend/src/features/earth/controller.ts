import type { CameraTarget, EarthMap, GeoPoint, Narration } from './contracts'

export interface EarthSnapshot {
  conversation_id: string
  control_revision: number
  phase: string
  selected?: (CameraTarget & { id: string; name: string }) | null
  candidates: Array<
    CameraTarget & {
      id: string
      name: string
      source: { name: string; url: string; attribution: string }
    }
  >
  transcript: Array<{ role: 'user' | 'assistant'; text: string }>
  capabilities: {
    search: boolean
    voice: boolean
    vision: boolean
    auto_search: boolean
    asr?: boolean
  }
  feedback_deadline?: number
  task_id?: string
  error?: { code: string; message: string }
}

export interface EarthCommand {
  conversation_id: string
  control_revision: number
  action_id: string
  kind: 'navigate' | 'cancel'
  target?: CameraTarget
}

export interface EarthNarration {
  conversation_id: string
  control_revision: number
  task_id: string
  text: string
  audio?: { data: string; format: string; volumes?: number[] }
  status: 'ready' | 'text_only'
}

export interface EarthTransport {
  request(
    payload: Record<string, unknown>,
  ): Promise<{ ok: boolean; state?: EarthSnapshot; error?: { code: string; message: string } }>
  context(payload: Record<string, unknown>): void
  result(payload: Record<string, unknown>): void
  subscribe(handlers: {
    state(snapshot: EarthSnapshot): void
    command(command: EarthCommand): void
    narration(narration: EarthNarration): void
    disconnected(): void
  }): () => void
}

export function createEarthController(options: {
  conversationId: string
  map: EarthMap
  transport: EarthTransport
  narration: Narration
  changed(snapshot: EarthSnapshot): void
}) {
  const { map, transport, narration } = options
  let state: EarthSnapshot = {
    conversation_id: options.conversationId,
    control_revision: 0,
    phase: 'connecting',
    candidates: [],
    transcript: [],
    capabilities: { search: false, voice: false, vision: false, auto_search: false },
  }
  let disposed = false
  let blocked = true
  let needsOpen = false
  let activating: number | undefined
  let generation = 0
  let move: AbortController | undefined
  let execution = 0
  let lastCancelRevision = -1
  const spoken = new Set<string>()
  const completed = new Map<string, Record<string, unknown>>()
  const history: CameraTarget[] = []
  const identity = () => ({
    conversation_id: options.conversationId,
    control_revision: state.control_revision,
  })
  const publish = () => {
    if (!disposed) options.changed({ ...state })
  }
  const accept = (next: EarthSnapshot) => {
    if (
      disposed ||
      next.conversation_id !== options.conversationId ||
      next.control_revision < state.control_revision
    )
      return
    const stopped = ['paused', 'closed', 'error'].includes(next.phase) || Boolean(next.error)
    if (stopped) {
      blocked = true
      // Server state stops execution, not the user request that is receiving it.
      cancelExecution()
    }
    state = {
      ...state,
      ...next,
      candidates: next.candidates ?? state.candidates ?? [],
      transcript: next.transcript ?? state.transcript ?? [],
      capabilities: {
        search: next.capabilities?.search ?? state.capabilities.search,
        voice: next.capabilities?.voice ?? state.capabilities.voice,
        vision: next.capabilities?.vision ?? state.capabilities.vision,
        auto_search: next.capabilities?.auto_search ?? state.capabilities.auto_search,
        asr: next.capabilities?.asr ?? state.capabilities.asr,
      },
      error: next.error,
      phase: ['closed', 'error'].includes(next.phase)
        ? next.phase
        : blocked
          ? 'paused'
          : next.phase,
      feedback_deadline: blocked ? undefined : next.feedback_deadline,
    }
    publish()
  }
  const cancelExecution = () => {
    execution++
    move?.abort()
    move = undefined
    map.cancel()
    narration.cancel()
  }
  const cancelLocal = () => {
    generation++
    blocked = true
    cancelExecution()
    state = { ...state, phase: 'paused', feedback_deadline: undefined }
    publish()
  }
  const request = async (
    operation: string,
    extra: Record<string, unknown> = {},
    activate = false,
  ) => {
    if (disposed) return
    const token = generation
    if (activate) {
      blocked = false
      activating = token
    }
    try {
      let reply = await transport.request({ ...identity(), operation, ...extra })
      if (disposed || token !== generation) return
      // A pause can race the server's replacement revision; retry only this intent.
      if (
        operation === 'pause' &&
        reply.error?.code === 'STALE_CONTROL' &&
        reply.state?.conversation_id === options.conversationId
      ) {
        accept(reply.state)
        if (disposed || token !== generation) return
        reply = await transport.request({ ...identity(), operation, ...extra })
        if (disposed || token !== generation) return
      }
      if (reply.state) accept(reply.state)
      if (!reply.ok) {
        if (reply.error?.code === 'EARTH_NOT_OPEN') needsOpen = true
        cancelLocal()
        state.error = reply.error ?? {
          code: 'EARTH_REQUEST_FAILED',
          message: '探索请求未完成，请重试',
        }
        publish()
        return false
      }
      if (operation === 'open') needsOpen = false
      return true
    } catch (error: unknown) {
      if (disposed || token !== generation) return
      cancelLocal()
      state.error = {
        code: 'EARTH_DISCONNECTED',
        message: error instanceof Error ? error.message : '探索连接不可用',
      }
      publish()
    } finally {
      if (activate && activating === token) activating = undefined
    }
  }
  const sendContext = (point?: GeoPoint) => {
    if (disposed) return
    const view = map.readView()
    transport.context({
      ...identity(),
      view_revision: view.view_revision,
      view,
      selected_point: point,
    })
  }
  const unsubscribe = transport.subscribe({
    state: accept,
    disconnected() {
      if (disposed) return
      needsOpen = true
      cancelLocal()
    },
    command(command) {
      if (
        disposed ||
        command.conversation_id !== options.conversationId ||
        command.control_revision < state.control_revision
      )
        return
      if (command.kind === 'cancel') {
        if (command.control_revision <= lastCancelRevision) return
        lastCancelRevision = command.control_revision
        state.control_revision = command.control_revision
        // Server acknowledgements of cancellation must not supersede a pending local pause.
        if (blocked || activating === generation) cancelExecution()
        else cancelLocal()
        return
      }
      if (blocked || !command.target) return
      state.control_revision = command.control_revision
      const actionKey = `${command.control_revision}:${command.action_id}`
      const prior = completed.get(actionKey)
      if (prior) {
        transport.result(prior)
        return
      }
      if (move) return
      history.push(map.readView())
      if (history.length > 30) history.shift()
      const activeMove = new AbortController()
      move = activeMove
      const token = generation
      const epoch = execution
      const actionIdentity = {
        conversation_id: command.conversation_id,
        control_revision: command.control_revision,
      }
      const current = () =>
        !disposed &&
        token === generation &&
        epoch === execution &&
        command.control_revision === state.control_revision
      const report = (status: string, view = map.readView()) => {
        const result = {
          ...actionIdentity,
          action_id: command.action_id,
          status,
          view_revision: view.view_revision,
          view,
        }
        if (current()) transport.result(result)
        return result
      }
      void map
        .move(command.target, activeMove.signal, (status) => report(status))
        .then((result) => {
          if (move === activeMove) move = undefined
          if (!current()) return
          completed.set(actionKey, report(result.status, result.view))
          if (completed.size > 100) completed.delete(completed.keys().next().value!)
          if (result.status === 'degraded' || result.status === 'failed') {
            cancelLocal()
            state.error = {
              code: 'EARTH_MAP_UNREADY',
              message: result.error ?? '画面仍在加载，请稍后继续',
            }
            publish()
          }
        })
        .catch(() => {
          if (move === activeMove) move = undefined
          if (current()) {
            report('failed')
            cancelLocal()
          }
        })
    },
    narration(message) {
      if (
        disposed ||
        blocked ||
        message.conversation_id !== options.conversationId ||
        message.control_revision !== state.control_revision
      )
        return
      if (!message.audio || message.status === 'text_only') return
      const token = generation
      const epoch = execution
      const speechKey = `${message.control_revision}:${message.task_id}`
      if (spoken.has(speechKey)) return
      spoken.add(speechKey)
      if (spoken.size > 100) spoken.delete(spoken.values().next().value!)
      narration.play(
        message.task_id,
        {
          audio_data: message.audio.data,
          format: message.audio.format,
          volumes: message.audio.volumes,
        },
        (status) => {
          if (
            disposed ||
            token !== generation ||
            epoch !== execution ||
            message.control_revision !== state.control_revision
          )
            return
          void request(status === 'ended' ? 'playback_ended' : 'playback_failed', {
            task_id: message.task_id,
          })
        },
      )
    },
  })
  return {
    async open() {
      await request('open', {}, true)
      if (!disposed) sendContext()
    },
    submit(text: string) {
      narration.unlock()
      cancelLocal()
      return request('text', { text }, true)
    },
    audio(data: string, format: string) {
      cancelLocal()
      return request('audio', { audio_data: data, format }, true)
    },
    pause() {
      const wasBlocked = blocked
      cancelLocal()
      if (!wasBlocked) void request('pause')
    },
    async resume() {
      narration.unlock()
      cancelLocal()
      const token = generation
      if (needsOpen) {
        // A new socket must claim its private session before continuing. Opening
        // alone stays paused; only this explicit, still-current intent continues.
        if (!(await request('open'))) return
        if (disposed || token !== generation) return
      }
      sendContext()
      return request('continue', {}, true)
    },
    choose(candidateId: string) {
      narration.unlock()
      cancelLocal()
      return request('select', { candidate_id: candidateId }, true)
    },
    select(x: number, y: number) {
      cancelLocal()
      const point = map.pick(x, y)
      if (!point) return null
      map.mark(point, '你指认的位置')
      sendContext(point)
      void request('select', { point }, true)
      return point
    },
    async back() {
      const target = history.pop()
      if (!target) return
      cancelLocal()
      const token = generation
      await request('pause')
      if (disposed || token !== generation) return
      const activeMove = new AbortController()
      move = activeMove
      try {
        await map.move(target, activeMove.signal, () => {})
      } finally {
        if (move === activeMove) move = undefined
      }
      if (!disposed && token === generation) sendContext()
    },
    voice(enabled: boolean) {
      narration.unlock()
      cancelLocal()
      return request('pause', { voice_enabled: enabled })
    },
    playbackStarted(taskId: string) {
      return request('playback_started', { task_id: taskId })
    },
    dispose() {
      if (disposed) return
      cancelLocal()
      disposed = true
      unsubscribe()
      void transport.request({ ...identity(), operation: 'close' }).catch(() => {})
      map.dispose()
    },
  }
}
