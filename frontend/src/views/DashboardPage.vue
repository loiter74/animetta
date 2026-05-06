<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useDashboardStore } from '../stores/dashboardStore'
import StatsKpiCards from '../components/dashboard/StatsKpiCards.vue'
import LatencyBreakdown from '../components/dashboard/LatencyBreakdown.vue'
import TokenUsageChart from '../components/dashboard/TokenUsageChart.vue'
import ErrorRateCard from '../components/dashboard/ErrorRateCard.vue'
import SessionTimeline from '../components/dashboard/SessionTimeline.vue'

const store = useDashboardStore()

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  store.fetchAll()
  refreshTimer = setInterval(() => store.fetchAll(), 10000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="flex-1 overflow-y-auto p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-white">Dashboard</h1>
      <div class="flex items-center gap-2 text-xs text-gray-400">
        <span
          :class="store.loading ? 'bg-yellow-400' : 'bg-green-400'"
          class="w-1.5 h-1.5 rounded-full inline-block"
        />
        {{ store.loading ? 'Refreshing...' : 'Live' }}
        <button
          @click="store.fetchAll()"
          class="px-2 py-0.5 bg-white/10 rounded hover:bg-white/20 transition-colors"
        >
          Refresh
        </button>
      </div>
    </div>

    <StatsKpiCards />
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <LatencyBreakdown />
      <TokenUsageChart />
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <ErrorRateCard />
      <div class="lg:col-span-2">
        <SessionTimeline />
      </div>
    </div>
  </div>
</template>
