<script setup lang="ts">
import { useDashboardStore } from '../../stores/dashboardStore'

const store = useDashboardStore()

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function statusClass(status: string): string {
  return status === 'error' ? 'text-red-400' : 'text-green-400'
}
</script>

<template>
  <div class="bg-white/5 rounded-2xl p-4 border border-white/10">
    <h3 class="text-sm font-medium text-gray-300 mb-4">Recent Sessions</h3>
    <div class="space-y-1 max-h-80 overflow-y-auto scrollbar-thin">
      <div
        v-for="trace in store.traces.slice(0, 30)"
        :key="trace.trace_id"
        class="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors cursor-default"
      >
        <div class="flex items-center gap-3 min-w-0">
          <span class="text-lg shrink-0">{{ trace.input_type === 'audio' ? '🎤' : '💬' }}</span>
          <div class="min-w-0">
            <div class="text-sm text-gray-200 truncate max-w-48">{{ trace.user_text }}</div>
            <div class="text-xs text-gray-500">
              {{ trace.created_at ? new Date(trace.created_at).toLocaleString() : '' }}
            </div>
          </div>
        </div>
        <div class="text-right shrink-0 ml-3">
          <div class="text-sm text-gray-300">{{ formatDuration(trace.total_duration_ms) }}</div>
          <div :class="statusClass(trace.status)" class="text-xs">{{ trace.status }}</div>
        </div>
      </div>
      <div v-if="!store.traces.length" class="text-gray-500 text-center py-8 text-sm">
        No sessions yet
      </div>
    </div>
  </div>
</template>
