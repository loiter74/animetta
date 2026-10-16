<script setup lang="ts">
/**
 * MemoryGraphControls — toolbar at top of the knowledge graph.
 *
 * Left: zoom in/out/reset. Center: search input. Right: category filter.
 * Stacks vertically on mobile (sm breakpoint).
 */
defineProps<{
  searchQuery: string
  selectedCategory: string | null
  categories: string[]
}>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  'update:selectedCategory': [value: string | null]
  zoomIn: []
  zoomOut: []
  zoomReset: []
}>()
const categoryLabels: Record<string, string> = {
  person: '人物',
  place: '地点',
  organization: '组织',
  concept: '概念',
  value: '数值 / 日期',
  fact: '事实',
  interest: '兴趣',
  skill: '能力',
  relation: '关系',
  knowledge: '知识',
  other: '其他',
}
</script>

<template>
  <div class="graph-controls">
    <!-- Left: zoom controls -->
    <div class="graph-controls-left flex items-center gap-1 shrink-0">
      <button class="btn-icon" type="button" aria-label="放大" title="放大" @click="emit('zoomIn')">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
          <path d="M8 11h6M11 8v6" />
        </svg>
      </button>
      <button
        class="btn-icon"
        type="button"
        aria-label="缩小"
        title="缩小"
        @click="emit('zoomOut')"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
          <path d="M8 11h6" />
        </svg>
      </button>
      <button
        class="btn-icon"
        type="button"
        aria-label="重置视图"
        title="重置视图"
        @click="emit('zoomReset')"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
          <path d="M3 3v5h5" />
        </svg>
      </button>
    </div>

    <!-- Center: search -->
    <div class="graph-controls-center flex-1 min-w-0 relative">
      <input
        :value="searchQuery"
        type="text"
        placeholder="搜索实体…"
        aria-label="搜索图谱实体"
        class="control-field w-full pl-9 pr-3"
        @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
      />
      <svg
        class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-c-text-muted"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="11" cy="11" r="8" />
        <path d="M21 21l-4.35-4.35" />
      </svg>
    </div>

    <!-- Right: category filter -->
    <div class="graph-controls-right shrink-0">
      <select
        :value="selectedCategory ?? ''"
        class="control-field"
        aria-label="图谱实体类型"
        @change="
          emit('update:selectedCategory', ($event.target as HTMLSelectElement).value || null)
        "
      >
        <option value="">全部实体类型</option>
        <option v-for="cat in categories" :key="cat" :value="cat">
          {{ categoryLabels[cat] ?? cat }}
        </option>
      </select>
    </div>
  </div>
</template>
