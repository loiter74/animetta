<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useDashboardStore } from '../stores/dashboardStore'
import BentoGrid from '../components/shared/BentoGrid.vue'
import BentoCard from '../components/shared/BentoCard.vue'
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
  <div class="flex-1 overflow-y-auto p-6">
    <div class="flex items-center justify-between mb-6">
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

    <BentoGrid>
      <!-- KPI Cards - full width -->
      <BentoCard :col-span="2" :row-span="1" type="stat">
        <StatsKpiCards />
      </BentoCard>

      <!-- Latency Chart -->
      <BentoCard type="chart">
        <LatencyBreakdown />
      </BentoCard>

      <!-- Token Usage -->
      <BentoCard type="chart">
        <TokenUsageChart />
      </BentoCard>

      <!-- Error Rate -->
      <BentoCard type="stat">
        <ErrorRateCard />
      </BentoCard>

      <!-- Session Timeline - spans 2 columns -->
      <BentoCard :col-span="2" type="chart">
        <SessionTimeline />
      </BentoCard>
    </BentoGrid>
  </div>
</template>
