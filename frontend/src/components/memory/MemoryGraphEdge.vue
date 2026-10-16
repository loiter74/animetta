<script setup lang="ts">
import { computed } from 'vue'
import type { MemoryEdge } from '@/types/memoryGraph'

const props = defineProps<{
  edge: MemoryEdge
  x1: number
  y1: number
  x2: number
  y2: number
  dimmed?: boolean
}>()
const emit = defineEmits<{ select: [id: string] }>()
const relationClasses: Record<string, string> = {
  DERIVES: 'text-c-mint',
  EXTENDS: 'text-c-blue',
  CONTRADICTS: 'text-c-error',
  UPDATES: 'text-c-accent',
  EVOKES: 'text-c-gold',
}
const color = computed(() => relationClasses[props.edge.type] ?? 'text-c-text-muted')

const geometry = computed(() => {
  const { x1, y1, x2, y2 } = props
  const distance = Math.hypot(x2 - x1, y2 - y1)
  if (distance < 1) {
    return {
      path: `M${x1 + 20},${y1 - 15} C${x1 + 80},${y1 - 100} ${x1 - 80},${y1 - 100} ${x1 - 20},${y1 - 15}`,
      end: { x: x1 - 20, y: y1 - 15 },
      control: { x: x1 - 80, y: y1 - 100 },
      label: { x: x1, y: y1 - 80 },
    }
  }
  const ux = (x2 - x1) / distance,
    uy = (y2 - y1) / distance
  const offset = props.edge.offset ?? 0
  const start = { x: x1 + ux * 30, y: y1 + uy * 30 }
  const end = { x: x2 - ux * 30, y: y2 - uy * 30 }
  const control = { x: (x1 + x2) / 2 - uy * offset, y: (y1 + y2) / 2 + ux * offset }
  return {
    path: `M${start.x},${start.y} Q${control.x},${control.y} ${end.x},${end.y}`,
    end,
    control,
    label: { x: (x1 + x2) / 2 - (uy * offset) / 2, y: (y1 + y2) / 2 + (ux * offset) / 2 - 7 },
  }
})
const arrow = computed(() => {
  const { end, control } = geometry.value
  const angle = Math.atan2(end.y - control.y, end.x - control.x)
  return `${end.x},${end.y} ${end.x - 10 * Math.cos(angle - 0.45)},${end.y - 10 * Math.sin(angle - 0.45)} ${end.x - 10 * Math.cos(angle + 0.45)},${end.y - 10 * Math.sin(angle + 0.45)}`
})
function select() {
  if (props.edge.factId) emit('select', props.edge.factId)
}
</script>

<template>
  <g
    :class="[color, { 'opacity-15': dimmed, 'cursor-pointer': edge.factId }]"
    :role="edge.factId ? 'button' : undefined"
    :tabindex="edge.factId ? 0 : undefined"
    :aria-label="edge.factId ? `查看事实：${edge.label}` : undefined"
    @mousedown.stop
    @click.stop="select"
    @keydown.enter.prevent="select"
    @keydown.space.prevent="select"
  >
    <path
      :d="geometry.path"
      stroke="currentColor"
      fill="none"
      :stroke-width="1 + edge.weight * 3"
      opacity="0.65"
    />
    <path :d="geometry.path" stroke="transparent" fill="none" stroke-width="16" />
    <polygon :points="arrow" fill="currentColor" />
    <text
      :x="geometry.label.x"
      :y="geometry.label.y"
      text-anchor="middle"
      class="fill-current text-xs"
      >{{ edge.label }}</text
    >
    <title>{{ edge.label }}</title>
  </g>
</template>
