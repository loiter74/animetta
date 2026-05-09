<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler,
} from 'chart.js'
import { useDashboardStore } from '../../stores/dashboardStore'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const store = useDashboardStore()

const chartData = computed(() => ({
  labels: store.traces.slice(0, 20).reverse().map(t =>
    t.created_at ? new Date(t.created_at).toLocaleTimeString() : ''
  ),
  datasets: [
    {
      label: 'Latency (ms)',
      data: store.traces.slice(0, 20).reverse().map(t => t.total_duration_ms),
      borderColor: 'rgb(52, 211, 153)',
      backgroundColor: 'rgba(52, 211, 153, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 3,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  plugins: {
    legend: { display: false },
  },
  scales: {
    x: {
      grid: { color: 'rgba(255,255,255,0.05)' },
      ticks: { color: '#9ca3af', maxTicksLimit: 10 },
    },
    y: {
      grid: { color: 'rgba(255,255,255,0.05)' },
      ticks: { color: '#9ca3af' },
      beginAtZero: true,
    },
  },
}
</script>

<template>
  <div class="bg-white/5 rounded-2xl p-4 border border-white/10">
    <h3 class="text-sm font-medium text-gray-300 mb-4">Latency Trend</h3>
    <Line v-if="store.traces.length" :data="chartData" :options="chartOptions" />
    <div v-else class="text-gray-500 text-center py-12 text-sm">No data yet</div>
  </div>
</template>
