<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useMemoryStore, type WikiPageEntry } from '@/stores/memory'
import type { MemoryNode } from '@/types/memoryGraph'
import MemoryGraph from './MemoryGraph.vue'

const emit = defineEmits<{
  'send-to-sandbox': [content: string]
}>()

const store = useMemoryStore()
const view = ref<'list' | 'graph'>('graph')
const selected = ref<WikiPageEntry | null>(null)
const correctionDraft = ref('')
const confirmForgetId = ref('')
const sourceDetail = ref<WikiPageEntry | null>(null)
const sourceLoading = ref(false)

const types = [
  { id: '', label: '全部类型' },
  { id: 'fact', label: '原子事实' },
  { id: 'entity', label: '实体' },
  { id: 'concept', label: '概念' },
  { id: 'synthesis', label: '合成' },
  { id: 'source', label: '来源' },
  { id: 'meme', label: '梗' },
] as const

const scopes = [
  { id: '', label: '全部作用域' },
  { id: 'character', label: '角色' },
  { id: 'community', label: '社群' },
  { id: 'viewer', label: '观众' },
  { id: 'stream', label: '本场' },
  { id: 'world', label: '世界' },
] as const

const organizing = computed(() => ['accepted', 'running'].includes(store.job?.status ?? ''))
const hasFacts = computed(() => store.wikiPages.some((page) => page.knowledge?.kind === 'fact'))
const relatedFacts = computed(() =>
  store.wikiPages.filter(
    (page) =>
      page.knowledge?.kind === 'fact' &&
      (page.knowledge.subject_id === selected.value?.id ||
        page.knowledge.object_id === selected.value?.id),
  ),
)

async function refresh(append = false): Promise<void> {
  try {
    await store.fetchMemories({
      scope: store.filterScope,
      cursor: append ? store.nextCursor : null,
      append,
      all: true,
    })
  } catch {
    // The store exposes the structured error below.
  }
}

function selectScope(value: string): void {
  store.setScope(value || null)
  void refresh()
}

function selectType(value: string): void {
  store.setFilter(value || null)
  selected.value = null
}

function selectPage(page: WikiPageEntry): void {
  selected.value = page
  correctionDraft.value = page.summary ?? page.content
  confirmForgetId.value = ''
  sourceDetail.value = null
}

function selectGraphNode(node: MemoryNode): void {
  const page = store.wikiPages.find((item) => item.id === node.id || item.path === node.id)
  if (page) selectPage(page)
}

function selectGraphFact(id: string): void {
  const page = store.wikiPages.find((item) => item.id === id)
  if (page) selectPage(page)
}

async function showSource(id: string): Promise<void> {
  const selectedId = selected.value?.id
  sourceLoading.value = true
  try {
    const page = store.wikiPages.find((item) => item.id === id) ?? (await store.getMemory(id))
    if (selected.value?.id === selectedId) sourceDetail.value = page
  } catch {
    // The store exposes the error and leaves the current fact selected.
  } finally {
    sourceLoading.value = false
  }
}

async function organize(): Promise<void> {
  try {
    await store.organizeMemory()
  } catch {
    // The store exposes the structured error below.
  }
}

async function togglePin(page: WikiPageEntry): Promise<void> {
  try {
    selected.value = await store.pinMemory(page.id, page.retention_policy !== 'pinned')
  } catch {
    // The store exposes the structured error below.
  }
}

async function forget(page: WikiPageEntry): Promise<void> {
  if (confirmForgetId.value !== page.id) {
    confirmForgetId.value = page.id
    return
  }
  try {
    await store.forgetMemory(page.id)
    confirmForgetId.value = ''
    selected.value = null
    await refresh()
  } catch {
    // The store exposes the structured error below.
  }
}

async function saveCorrection(): Promise<void> {
  if (!selected.value || !correctionDraft.value.trim()) return
  try {
    selected.value = await store.changeMemory(selected.value.id, correctionDraft.value.trim())
  } catch {
    // The store exposes the structured error below.
  }
}

function formatTime(value: string): string {
  if (!value) return '未知'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(() => {
  void store.recoverOrganize()
  void refresh()
})
watch(
  () => store.job?.status,
  (status, previous) => {
    if (status === 'completed' && ['accepted', 'running'].includes(previous ?? '')) void refresh()
  },
)
</script>

<template>
  <main class="workspace-body" data-testid="memory-workspace">
    <header class="flex shrink-0 flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="workspace-title">原子知识图谱</h1>
        <p class="workspace-copy">将对话拆成独立事实，连接实体，并保留每条关系的原文证据</p>
      </div>
      <button class="btn-accent" type="button" :disabled="organizing" @click="organize">
        {{ organizing ? '整理中' : '整理记忆' }}
      </button>
    </header>

    <div
      class="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-c-text-dim"
      aria-label="知识统计"
    >
      <span
        ><strong class="mr-1 font-semibold tabular-nums text-c-text">{{
          store.knowledge.entities
        }}</strong>
        个实体</span
      >
      <span
        ><strong class="mr-1 font-semibold tabular-nums text-c-text">{{
          store.knowledge.facts
        }}</strong>
        条原子事实</span
      >
      <span
        ><strong class="mr-1 font-semibold tabular-nums text-c-text">{{
          store.knowledge.pending_sources
        }}</strong>
        条对话待整理</span
      >
    </div>

    <section v-if="store.job" class="glass shrink-0 px-4 py-3" aria-live="polite">
      <div class="flex items-center justify-between gap-3 text-xs">
        <span class="text-c-text-secondary">{{ store.job.text || '记忆整理任务' }}</span>
        <span class="font-mono uppercase text-c-text-muted"
          >{{ store.job.status }} · {{ store.job.progress }}%</span
        >
      </div>
      <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-c-panel">
        <div
          class="h-full rounded-full bg-c-accent transition-all duration-300"
          :style="{ width: `${store.job.progress}%` }"
        />
      </div>
      <p v-if="store.job.error" class="mt-2 text-xs text-c-error">{{ store.job.error }}</p>
    </section>

    <section class="glass flex min-h-0 flex-1 flex-col overflow-hidden">
      <div class="flex shrink-0 flex-wrap items-center gap-2 border-b border-c-border p-3">
        <input
          v-if="view === 'list'"
          :value="store.searchQuery"
          class="control-field min-w-44 flex-1"
          placeholder="搜索标题、摘要或正文"
          @input="store.setSearch(($event.target as HTMLInputElement).value)"
        />
        <select
          v-if="view === 'list'"
          :value="store.filterType ?? ''"
          class="control-field"
          aria-label="记忆类型"
          @change="selectType(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="item in types" :key="item.id" :value="item.id">{{ item.label }}</option>
        </select>
        <select
          :value="store.filterScope ?? ''"
          class="control-field"
          aria-label="记忆作用域"
          @change="selectScope(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="item in scopes" :key="item.id" :value="item.id">{{ item.label }}</option>
        </select>
        <div class="segmented-control ml-auto" role="group" aria-label="记忆视图">
          <button
            class="segment-option"
            type="button"
            :aria-pressed="view === 'list'"
            @click="view = 'list'"
          >
            列表
          </button>
          <button
            class="segment-option"
            type="button"
            :aria-pressed="view === 'graph'"
            @click="view = 'graph'"
          >
            关系图
          </button>
        </div>
        <button v-if="store.invalidated" class="btn-ghost" type="button" @click="refresh()">
          载入新版本
        </button>
      </div>

      <p
        v-if="store.error"
        class="m-3 rounded-xl border border-c-error/40 bg-c-error/10 px-3 py-2 text-xs text-c-error"
        role="alert"
      >
        {{ store.error.message }}
        <button class="ml-2 underline" type="button" @click="refresh()">重试</button>
      </p>

      <div class="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,3fr)_minmax(320px,2fr)]">
        <div class="min-h-0 overflow-hidden border-b border-c-border lg:border-b-0 lg:border-r">
          <div
            v-if="store.loading"
            class="grid h-full min-h-80 place-items-center text-sm text-c-text-muted"
          >
            正在读取记忆
          </div>
          <div
            v-else-if="view === 'graph' ? !hasFacts : !store.filteredPages.length"
            class="grid h-full min-h-80 place-items-center px-6 text-center"
          >
            <div>
              <p class="text-sm text-c-text-secondary">
                {{ view === 'graph' ? '还没有可展示的原子知识' : '没有符合条件的记忆' }}
              </p>
              <p class="mt-1 text-xs text-c-text-muted">
                {{
                  view === 'graph'
                    ? '点击“整理记忆”，从已有对话抽取实体和事实；没有可确认的事实时会保留原始记录。'
                    : '调整搜索、类型或作用域后重试'
                }}
              </p>
            </div>
          </div>
          <div v-else-if="view === 'list'" class="h-full overflow-y-auto">
            <button
              v-for="page in store.filteredPages"
              :key="page.id"
              type="button"
              class="block w-full border-b border-c-border px-5 py-4 text-left transition-colors duration-200"
              :class="selected?.id === page.id ? 'bg-c-panel/55' : 'hover:bg-c-panel/30'"
              @click="selectPage(page)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium">{{ page.title }}</p>
                  <p class="mt-1 line-clamp-2 text-xs leading-relaxed text-c-text-secondary">
                    {{ page.summary || page.content }}
                  </p>
                </div>
                <span
                  v-if="page.retention_policy === 'pinned'"
                  class="rounded-lg bg-c-accent-soft px-2 py-1 text-10px text-c-accent"
                  >已固定</span
                >
              </div>
              <div class="mt-3 flex flex-wrap gap-2 text-10px text-c-text-muted">
                <span>{{ page.page_type }}</span
                ><span>{{ page.scope }}</span
                ><span>v{{ page.version }}</span
                ><span>{{ formatTime(page.updated_at) }}</span>
              </div>
            </button>
            <div v-if="store.nextCursor" class="p-4 text-center">
              <button class="btn-ghost" type="button" @click="refresh(true)">加载更多</button>
            </div>
          </div>
          <MemoryGraph
            v-else
            class="h-full min-h-112"
            :pages="store.wikiPages"
            knowledge-only
            :selected-id="selected?.id"
            @node-click="selectGraphNode"
            @fact-click="selectGraphFact"
          />
        </div>

        <aside class="min-h-0 overflow-y-auto bg-c-panel/45 p-5 sm:p-6">
          <div v-if="!selected" class="grid min-h-72 place-items-center text-center">
            <div>
              <p class="text-sm text-c-text-secondary">点击实体或关系查看知识</p>
              <p class="mt-1 text-xs text-c-text-muted">
                箭头表示关系方向，每条事实都可追溯到原始对话
              </p>
            </div>
          </div>
          <template v-else>
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <h2 class="break-words text-sm font-semibold">{{ selected.title }}</h2>
                <p
                  v-if="!selected.knowledge?.kind"
                  class="mt-1 font-mono text-10px text-c-text-muted"
                >
                  {{ selected.id }}
                </p>
              </div>
              <button class="btn-secondary" type="button" @click="togglePin(selected)">
                {{ selected.retention_policy === 'pinned' ? '取消固定' : '固定' }}
              </button>
            </div>

            <p class="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-c-text-secondary">
              {{ selected.content }}
            </p>

            <section v-if="relatedFacts.length" class="mt-5" aria-label="关联事实">
              <h3 class="text-xs font-medium">关联事实</h3>
              <button
                v-for="fact in relatedFacts"
                :key="fact.id"
                type="button"
                class="mt-2 block w-full rounded-xl bg-c-panel/45 px-3 py-2 text-left text-xs hover:bg-c-panel"
                @click="selectPage(fact)"
              >
                {{ fact.title }}
              </button>
            </section>

            <section v-if="selected.knowledge?.evidence?.length" class="mt-5" aria-label="原文证据">
              <h3 class="text-xs font-medium">原文证据</h3>
              <figure
                v-for="(evidence, index) in selected.knowledge.evidence"
                :key="index"
                class="mx-0 mt-3 rounded-xl border border-c-border bg-c-surface p-4"
              >
                <blockquote class="whitespace-pre-wrap text-xs leading-relaxed">
                  {{ evidence.quote }}
                </blockquote>
                <figcaption
                  class="mt-2 flex flex-wrap items-center gap-2 text-10px text-c-text-muted"
                >
                  <span>{{ evidence.role === 'user' ? '用户陈述' : '助手陈述' }}</span>
                  <span>{{ formatTime(evidence.occurred_at) }}</span>
                  <button
                    type="button"
                    class="border-none bg-transparent p-0 text-c-accent underline"
                    @click="showSource(evidence.source_id)"
                  >
                    查看原始对话
                  </button>
                </figcaption>
              </figure>
            </section>
            <p v-if="sourceLoading" class="mt-3 text-xs text-c-text-muted" role="status">
              正在读取来源…
            </p>
            <section
              v-if="sourceDetail"
              class="mt-3 rounded-xl border border-c-border p-3"
              aria-label="原始对话"
            >
              <h3 class="text-xs font-medium">原始对话</h3>
              <p class="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-c-text-secondary">
                {{ sourceDetail.content }}
              </p>
            </section>

            <div v-if="!selected.knowledge?.kind" class="mt-5">
              <h3 class="text-xs font-medium">关系</h3>
              <ul
                v-if="selected.relations.length"
                class="mt-2 space-y-2 text-xs text-c-text-secondary"
              >
                <li
                  v-for="relation in selected.relations"
                  :key="`${relation.source_id}:${relation.target_id}:${relation.relation_type}`"
                  class="rounded-xl bg-c-panel/45 px-3 py-2"
                >
                  {{ relation.relation_type }} · {{ relation.target_id }}
                </li>
              </ul>
              <p v-else class="mt-2 text-xs text-c-text-muted">暂无已建立关系</p>
            </div>

            <dl class="mt-5 grid grid-cols-2 gap-2 text-xs">
              <div class="rounded-xl bg-c-panel/45 p-3">
                <dt class="text-c-text-muted">可信度</dt>
                <dd class="mt-1 font-mono">{{ selected.confidence }}</dd>
              </div>
              <div v-if="!selected.knowledge?.kind" class="rounded-xl bg-c-panel/45 p-3">
                <dt class="text-c-text-muted">信任等级</dt>
                <dd class="mt-1 font-mono">{{ selected.trust_level }}</dd>
              </div>
              <div v-if="!selected.knowledge?.kind" class="rounded-xl bg-c-panel/45 p-3">
                <dt class="text-c-text-muted">索引状态</dt>
                <dd class="mt-1 font-mono">{{ selected.index_state }}</dd>
              </div>
              <div class="rounded-xl bg-c-panel/45 p-3">
                <dt class="text-c-text-muted">可见性</dt>
                <dd class="mt-1">
                  {{ { public: '公开', private: '仅本人', internal: '内部' }[selected.visibility] }}
                </dd>
              </div>
            </dl>
            <details v-if="selected.knowledge?.kind" class="mt-4 text-xs text-c-text-muted">
              <summary class="cursor-pointer">审计信息</summary>
              <p class="mt-2 break-all font-mono">{{ selected.id }} · v{{ selected.version }}</p>
              <p class="mt-1">
                记录于 {{ formatTime(selected.occurred_at) }} ·
                {{ selected.source_ids.length }} 条来源
              </p>
            </details>

            <p
              v-if="selected.knowledge?.kind"
              class="mt-5 text-xs leading-relaxed text-c-text-muted"
            >
              如需更正知识，可先遗忘旧事实，再在现场对话中提供新的陈述。
            </p>
            <label v-else class="mt-5 block text-xs font-medium">
              内容修正
              <textarea
                v-model="correctionDraft"
                rows="4"
                class="mt-2 w-full resize-none rounded-xl border border-c-border bg-c-panel/55 px-3 py-2 text-sm font-normal outline-none focus:border-c-border-accent"
              />
            </label>
            <div class="mt-3 flex flex-wrap gap-2">
              <button
                v-if="!selected.knowledge?.kind"
                class="btn-accent"
                type="button"
                :disabled="!correctionDraft.trim()"
                @click="saveCorrection"
              >
                保存修正
              </button>
              <button
                class="btn-secondary"
                type="button"
                @click="emit('send-to-sandbox', selected.content)"
              >
                发送到对话沙盒
              </button>
              <button class="btn-danger" type="button" @click="forget(selected)">
                {{ confirmForgetId === selected.id ? '确认遗忘' : '遗忘' }}
              </button>
            </div>
          </template>
        </aside>
      </div>
    </section>
  </main>
</template>
