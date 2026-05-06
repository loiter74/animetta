import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface StatsOverview {
  total_traces: number
  total_spans: number
  total_errors: number
  avg_latency_ms: number
  total_input_tokens: number
  total_output_tokens: number
  unique_sessions: number
}

export interface NodeStats {
  node_name: string
  call_count: number
  avg_duration_ms: number
  error_count: number
  error_rate: number
}

export interface Trace {
  trace_id: string
  session_id: string
  input_type: string
  input_summary: string
  total_duration_ms: number
  status: string
  started_at: string
}

export const useDashboardStore = defineStore('dashboard', () => {
  const overview = ref<StatsOverview | null>(null)
  const nodeStats = ref<NodeStats[]>([])
  const traces = ref<Trace[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const avgLatency = computed(() => overview.value?.avg_latency_ms ?? 0)
  const totalSessions = computed(() => overview.value?.total_traces ?? 0)
  const errorRate = computed(() => {
    if (!overview.value || overview.value.total_spans === 0) return 0
    return (overview.value.total_errors / overview.value.total_spans) * 100
  })

  function getTokenSummary() {
    const inp = overview.value?.total_input_tokens ?? 0
    const out = overview.value?.total_output_tokens ?? 0
    return { input: inp, output: out, total: inp + out }
  }

  async function fetchOverview() {
    try {
      const res = await fetch('/api/stats/overview')
      overview.value = await res.json()
    } catch (e) {
      error.value = String(e)
    }
  }

  async function fetchNodeStats() {
    try {
      const res = await fetch('/api/stats/nodes')
      nodeStats.value = await res.json()
    } catch (e) {
      error.value = String(e)
    }
  }

  async function fetchTraces(limit = 50, offset = 0) {
    try {
      const res = await fetch(`/api/stats/traces?limit=${limit}&offset=${offset}`)
      traces.value = await res.json()
    } catch (e) {
      error.value = String(e)
    }
  }

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      await Promise.all([fetchOverview(), fetchNodeStats(), fetchTraces()])
    } finally {
      loading.value = false
    }
  }

  return {
    overview, nodeStats, traces, loading, error,
    avgLatency, totalSessions, errorRate, getTokenSummary,
    fetchAll, fetchOverview, fetchNodeStats, fetchTraces,
  }
})
