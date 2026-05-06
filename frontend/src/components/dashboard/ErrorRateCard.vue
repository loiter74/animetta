<script setup lang="ts">
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { useDashboardStore } from '../../stores/dashboardStore'

ChartJS.register(ArcElement, Tooltip, Legend)

const store = useDashboardStore()

const chartData = {
  labels: ['Success', 'Error'],
  datasets: [{
    data: [1, 0],
    backgroundColor: ['rgba(52, 211, 153, 0.7)', 'rgba(239, 68, 68, 0.7)'],
    borderWidth: 0,
  }],
}

const chartOptions = {
  responsive: true,
  cutout: '70%',
  plugins: {
    legend: {
      position: 'bottom' as const,
      labels: { color: '#9ca3af', font: { size: 11 } },
    },
  },
}
</script>

<template>
  <div class="bg-white/5 rounded-2xl p-4 border border-white/10">
    <h3 class="text-sm font-medium text-gray-300 mb-2">Error Rate</h3>
    <Doughnut :data="chartData" :options="chartOptions" />
    <div class="text-center mt-2">
      <span :class="store.errorRate > 5 ? 'text-red-400' : 'text-green-400'" class="text-sm font-medium">
        {{ store.errorRate.toFixed(1) }}%
      </span>
    </div>
  </div>
</template>
