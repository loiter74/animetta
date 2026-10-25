import type { MemoryKnowledge, KnowledgeStats } from '@/types/memoryKnowledge'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getSocket } from '@/services/socket'
import { Events } from '@/shared/contracts/socket-events'
import { fetchCommandTask, readCommandTask, startCommandTask } from '@/services/commandTasks'

export interface MemoryRelation {
  source_id: string
  target_id: string
  relation_type: string
  created_at: string
  metadata: Record<string, unknown>
}

export interface MemoryAtomDTO {
  id: string
  path: string
  title: string
  content: string
  summary: string | null
  layer: string
  page_type: string
  scope: 'character' | 'community' | 'viewer' | 'stream' | 'world'
  visibility: 'public' | 'private' | 'internal'
  subject_ids: string[]
  origin: Record<string, string>
  confidence: number
  salience: number
  trust_level: number
  retention_policy: string
  index_state: string
  relations: MemoryRelation[]
  tags: string[]
  source_ids: string[]
  version: number
  is_archived: boolean
  occurred_at: string
  updated_at: string
  knowledge?: MemoryKnowledge
}

export type WikiPageEntry = MemoryAtomDTO

export interface MemoryError {
  code: string
  message: string
}

export interface MemoryJob {
  job_id: string
  status: string
  progress: number
  text?: string
  revision?: number
  error?: string
  stats?: KnowledgeStats
}

interface MemoryPage {
  items: MemoryAtomDTO[]
  revision: number
  next_cursor: string | null
  total: number
  knowledge?: KnowledgeStats
  health?: {
    degraded: boolean
    index_backlog: number
    last_error: string
  }
}

interface MemoryAck<T> {
  ok: boolean
  data?: T
  error?: MemoryError
}

interface FetchOptions {
  cursor?: string | null
  limit?: number
  scope?: string | null
  append?: boolean
  timeoutMs?: number
  all?: boolean
}

const DEFAULT_ACK_TIMEOUT_MS = 3000

function isAck<T>(value: unknown): value is MemoryAck<T> {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as { ok?: unknown }).ok === 'boolean'
  )
}

export const useMemoryStore = defineStore('memory', () => {
  const wikiPages = ref<MemoryAtomDTO[]>([])
  const selectedPath = ref<string | null>(null)
  const loading = ref(false)
  const filterType = ref<string | null>(null)
  const filterScope = ref<string | null>(null)
  const searchQuery = ref('')
  const revision = ref(0)
  const latestRevision = ref(0)
  const nextCursor = ref<string | null>(null)
  const total = ref(0)
  const invalidated = ref(false)
  const error = ref<MemoryError | null>(null)
  const job = ref<MemoryJob | null>(null)
  const health = ref({ degraded: false, indexBacklog: 0, lastError: '' })
  const knowledge = ref<KnowledgeStats>({ entities: 0, facts: 0, pending_sources: 0 })
  let listenersStarted = false

  const filteredPages = computed(() => {
    let list = wikiPages.value
    if (filterType.value) list = list.filter((item) => item.page_type === filterType.value)
    if (filterScope.value) list = list.filter((item) => item.scope === filterScope.value)
    const query = searchQuery.value.trim().toLowerCase()
    if (query) {
      list = list.filter(
        (item) =>
          item.content.toLowerCase().includes(query) ||
          item.title.toLowerCase().includes(query) ||
          (item.summary ?? '').toLowerCase().includes(query),
      )
    }
    return list
  })

  function fail(code: string, message: string): Error {
    error.value = { code, message }
    return new Error(message)
  }

  async function request<T>(
    event: string,
    payload: Record<string, unknown>,
    timeoutMs = DEFAULT_ACK_TIMEOUT_MS,
  ): Promise<T> {
    const socket = getSocket()
    if (!socket || !socket.connected) throw fail('DISCONNECTED', 'Socket disconnected')
    return await new Promise<T>((resolve, reject) => {
      const timer = window.setTimeout(() => {
        reject(fail('TIMEOUT', 'Memory request timed out'))
      }, timeoutMs)
      socket.emit(event, payload, (response: unknown) => {
        window.clearTimeout(timer)
        if (!isAck<T>(response)) {
          reject(fail('MALFORMED_RESPONSE', 'Malformed memory response'))
          return
        }
        if (!response.ok || response.data === undefined) {
          const problem = response.error ?? {
            code: 'UNKNOWN',
            message: 'Memory request failed',
          }
          reject(fail(problem.code, problem.message))
          return
        }
        error.value = null
        resolve(response.data)
      })
    })
  }

  async function fetchMemories(options: FetchOptions = {}): Promise<void> {
    loading.value = true
    try {
      const page = await request<MemoryPage>(
        Events.MEMORY.LIST,
        {
          cursor: options.cursor ?? undefined,
          limit: options.limit ?? (options.all ? 100 : 50),
          scope: options.scope ?? undefined,
        },
        options.timeoutMs,
      )
      const items = [...page.items]
      let cursor = page.next_cursor
      const seen = new Set<string>()
      while (options.all && cursor !== null) {
        if (seen.has(cursor)) throw fail('INVALID_CURSOR', '记忆分页游标重复，请刷新重试')
        seen.add(cursor)
        const next = await request<MemoryPage>(
          Events.MEMORY.LIST,
          {
            cursor,
            limit: 100,
            scope: options.scope ?? undefined,
          },
          options.timeoutMs,
        )
        if (next.revision !== page.revision) throw fail('STALE_GRAPH', '记忆已更新，请重新载入图谱')
        items.push(...next.items)
        cursor = next.next_cursor
      }
      wikiPages.value = options.append ? [...wikiPages.value, ...items] : items
      revision.value = page.revision
      latestRevision.value = Math.max(latestRevision.value, page.revision)
      nextCursor.value = cursor
      total.value = page.total
      if (page.knowledge) knowledge.value = page.knowledge
      if (page.health) {
        health.value = {
          degraded: page.health.degraded,
          indexBacklog: page.health.index_backlog,
          lastError: page.health.last_error,
        }
      }
      invalidated.value = latestRevision.value > revision.value
    } finally {
      loading.value = false
    }
  }

  async function fetchWikiPages(_sessionId = 'default'): Promise<void> {
    void _sessionId
    await fetchMemories()
  }

  async function searchRemote(query: string): Promise<void> {
    loading.value = true
    try {
      const page = await request<MemoryPage>(Events.MEMORY.SEARCH, { query, limit: 50 })
      wikiPages.value = page.items
      revision.value = page.revision
      latestRevision.value = Math.max(latestRevision.value, page.revision)
      nextCursor.value = null
      total.value = page.total
      invalidated.value = false
    } finally {
      loading.value = false
    }
  }

  async function mutate(event: string, payload: Record<string, unknown>): Promise<MemoryAtomDTO> {
    const result = await request<{ item: MemoryAtomDTO; revision: number }>(event, payload)
    const index = wikiPages.value.findIndex((item) => item.id === result.item.id)
    if (index >= 0) wikiPages.value.splice(index, 1, result.item)
    revision.value = result.revision
    latestRevision.value = Math.max(latestRevision.value, result.revision)
    return result.item
  }

  const pinMemory = (id: string, pinned: boolean) => mutate(Events.MEMORY.PIN, { id, pinned })
  const forgetMemory = (id: string) => mutate(Events.MEMORY.FORGET, { id })
  const getMemory = async (id: string) => {
    const result = await request<{ item: MemoryAtomDTO }>(Events.MEMORY.GET, { id })
    return result.item
  }
  const changeMemory = (id: string, summary: string) => {
    const current = wikiPages.value.find((item) => item.id === id)
    if (!current) throw fail('NOT_FOUND', 'Memory not found')
    const taskId = startCommandTask(
      'memory.change',
      `${id}\u0000${current.version}\u0000${summary}`,
    )
    return mutate(Events.MEMORY.CHANGE, {
      id,
      summary,
      task_id: taskId,
      expected_version: current.version,
    })
  }

  async function organizeMemory(): Promise<void> {
    const forceNew = ['succeeded', 'completed', 'failed', 'cancelled', 'interrupted'].includes(
      job.value?.status ?? '',
    )
    const taskId = startCommandTask(
      'memory.organize',
      'global',
      window.localStorage,
      () => crypto.randomUUID(),
      forceNew,
    )
    const accepted = await request<MemoryJob>(Events.MEMORY.ORGANIZE, { task_id: taskId })
    job.value = accepted
  }

  async function recoverOrganize(): Promise<void> {
    const socket = getSocket()
    const persisted = readCommandTask('memory.organize')
    if (!socket?.connected || !persisted) return
    const snapshot = await fetchCommandTask(socket, 'memory.organize', persisted.taskId)
    if (!snapshot) return
    const source = snapshot.result ?? snapshot.progress
    const status = snapshot.status === 'succeeded' ? 'completed' : snapshot.status
    job.value = {
      job_id: persisted.taskId,
      status,
      progress: Number(source?.progress ?? (snapshot.status === 'succeeded' ? 100 : 0)),
      text: snapshot.reused ? '已恢复整理任务' : undefined,
      error: snapshot.error?.message,
      stats: source?.stats as KnowledgeStats | undefined,
      ...(typeof source?.text === 'string' ? { text: source.text } : {}),
    }
  }

  const onChanged = (payload: unknown) => {
    if (typeof payload !== 'object' || payload === null) return
    const incoming = Number((payload as { revision?: unknown }).revision)
    if (!Number.isFinite(incoming)) return
    latestRevision.value = Math.max(latestRevision.value, incoming)
    if (incoming > revision.value) invalidated.value = true
  }

  const onJobProgress = (payload: unknown) => {
    if (typeof payload !== 'object' || payload === null || !job.value) return
    const incoming = payload as Partial<MemoryJob>
    if (incoming.job_id !== job.value.job_id) return
    job.value = { ...job.value, ...incoming }
  }

  const onJobResult = (payload: unknown) => {
    onJobProgress(payload)
    if (typeof payload !== 'object' || payload === null || !job.value) return
    const incoming = payload as Partial<MemoryJob>
    if (incoming.job_id !== job.value.job_id) return
    if (typeof incoming.revision === 'number') {
      latestRevision.value = Math.max(latestRevision.value, incoming.revision)
      invalidated.value = incoming.revision > revision.value
    }
  }

  function startListeners(): void {
    if (listenersStarted) return
    const socket = getSocket()
    if (!socket) return
    socket.on(Events.MEMORY.CHANGED, onChanged)
    socket.on(Events.MEMORY.ORGANIZE_PROGRESS, onJobProgress)
    socket.on(Events.MEMORY.ORGANIZE_RESULT, onJobResult)
    listenersStarted = true
  }

  function stopListeners(): void {
    if (!listenersStarted) return
    const socket = getSocket()
    socket?.off(Events.MEMORY.CHANGED, onChanged)
    socket?.off(Events.MEMORY.ORGANIZE_PROGRESS, onJobProgress)
    socket?.off(Events.MEMORY.ORGANIZE_RESULT, onJobResult)
    listenersStarted = false
  }

  function selectPath(path: string): void {
    selectedPath.value = selectedPath.value === path ? null : path
  }
  function setFilter(type: string | null): void {
    filterType.value = type
  }
  function setScope(scope: string | null): void {
    filterScope.value = scope
  }
  function setSearch(query: string): void {
    searchQuery.value = query
  }

  startListeners()

  return {
    wikiPages,
    selectedPath,
    loading,
    filterType,
    filterScope,
    searchQuery,
    revision,
    latestRevision,
    nextCursor,
    total,
    invalidated,
    error,
    job,
    health,
    knowledge,
    filteredPages,
    fetchMemories,
    fetchWikiPages,
    searchRemote,
    pinMemory,
    forgetMemory,
    getMemory,
    changeMemory,
    organizeMemory,
    recoverOrganize,
    startListeners,
    stopListeners,
    selectPath,
    setFilter,
    setScope,
    setSearch,
  }
})
