import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface StatsOverview {
  total_requests: number
  success_rate: number
  avg_duration_ms: number
  p95_duration_ms: number
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
  user_text: string
  total_duration_ms: number
  status: string
  created_at: string
}

export const useDashboardStore = defineStore('dashboard', () => {
  const overview = ref<StatsOverview | null>(null)
  const nodeStats = ref<NodeStats[]>([])
  const traces = ref<Trace[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const avgLatency = computed(() => overview.value?.avg_duration_ms ?? 0)
  const totalSessions = computed(() => overview.value?.total_requests ?? 0)
  const errorRate = computed(() => {
    if (!overview.value || !overview.value.success_rate) return 0
    return Math.round((100 - overview.value.success_rate) * 10) / 10
  })

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
    avgLatency, totalSessions, errorRate,
    fetchAll, fetchOverview, fetchNodeStats, fetchTraces,
  }
})
