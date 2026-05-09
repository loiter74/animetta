<script setup lang="ts">
import { computed } from 'vue'
import { useDashboardStore } from '../../stores/dashboardStore'

const store = useDashboardStore()

const kpis = computed(() => [
  { label: 'Sessions', value: store.totalSessions, icon: '💬' },
  { label: 'Avg Latency', value: `${store.avgLatency.toFixed(0)}ms`, icon: '⚡' },
  { label: 'Total Requests', value: store.overview?.total_requests ?? 0, icon: '📊' },
  { label: 'Error Rate', value: `${store.errorRate.toFixed(1)}%`, icon: '❌' },
])
</script>

<template>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    <div
      v-for="kpi in kpis"
      :key="kpi.label"
      class="bg-white/5 rounded-2xl p-4 border border-white/10"
    >
      <div class="text-2xl mb-2">{{ kpi.icon }}</div>
      <div class="text-xl font-bold text-white">{{ kpi.value }}</div>
      <div class="text-xs text-gray-400 mt-1">{{ kpi.label }}</div>
    </div>
  </div>
</template>
