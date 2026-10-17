<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { mountEarth } from './mount'
import type { createEarthController, EarthSnapshot } from './controller'
import { createMicrophone } from './adapters/microphone'

const EarthAvatar = defineAsyncComponent(() => import('@/shared/live2d/Companion.vue'))
const container = ref<HTMLElement>()
const avatar = ref<{ setMouth(value: number): void }>()
const enabledAvatar = ref(true)
const enabledVoice = ref(false)
const input = ref('')
const selecting = ref(false)
const error = ref('')
const ready = ref(false)
const now = ref(Date.now())
const snapshot = shallowRef<EarthSnapshot>()
const playback = ref({ taskId: '', status: '', count: 0, at: 0 })
const life = new AbortController()
let controller: ReturnType<typeof createEarthController> | undefined
let tick: ReturnType<typeof setInterval> | undefined
const recording = ref(false)
const microphone = createMicrophone({
  started: () => controller?.pause(),
  captured: (data, format) => {
    void controller?.audio(data, format)
  },
  changed: (value) => {
    recording.value = value
  },
  failed: (message) => {
    error.value = message
  },
})
const phases: Record<string, string> = {
  connecting: '连接中',
  idle: '等待线索',
  waiting_input: '等待线索',
  deciding: '思考中',
  moving: '移动中',
  observing: '观察中',
  explaining: '解释中',
  waiting_feedback: '等待反馈',
  waiting_selection: '等待你选择',
  reading: '解释中',
  feedback: '等待反馈',
  awaiting_playback: '准备讲解',
  playing: '讲解中',
  waiting_identification: '等待你辨认',
  paused: '已暂停',
  closed: '已结束',
}
const phase = computed(() => phases[snapshot.value?.phase ?? 'connecting'] ?? '等待你辨认')
const remaining = computed(() =>
  Math.max(0, Math.ceil((snapshot.value?.feedback_deadline ?? 0) - now.value / 1000)),
)
const messages = computed(() => snapshot.value?.transcript ?? [])
const explanation = computed(
  () =>
    [...messages.value].reverse().find((message) => message.role === 'assistant')?.text ??
    '我们先从一个大范围开始。你记得在哪座城市，或者附近有什么？',
)
const title = computed(() => snapshot.value?.selected?.name ?? '一起寻找熟悉的地方')

function pause() {
  controller?.pause()
}
function toggleSelection() {
  pause()
  selecting.value = !selecting.value
}
function submit() {
  const text = input.value.trim()
  if (!text || !controller) return
  input.value = ''
  selecting.value = false
  void controller.submit(text)
}
function select(event: MouseEvent) {
  if (!selecting.value || !container.value) return
  const bounds = container.value.getBoundingClientRect()
  const point = controller?.select(
    (event.clientX - bounds.x) / bounds.width,
    (event.clientY - bounds.y) / bounds.height,
  )
  if (point) selecting.value = false
}
function visibility() {
  if (document.hidden) pause()
}

onMounted(async () => {
  document.addEventListener('visibilitychange', visibility)
  tick = setInterval(() => {
    now.value = Date.now()
  }, 250)
  try {
    if (!container.value) return
    const next = await mountEarth({
      container: container.value,
      signal: life.signal,
      changed: (value) => {
        snapshot.value = value
      },
      mouth: (value) => avatar.value?.setMouth(value),
      playback: (taskId, status) => {
        playback.value = {
          taskId,
          status,
          count: playback.value.count + (status === 'started' ? 1 : 0),
          at: Date.now(),
        }
      },
    })
    if (life.signal.aborted) {
      next.dispose()
      return
    }
    controller = next
    ready.value = true
  } catch (reason) {
    if (!life.signal.aborted)
      error.value = reason instanceof Error ? reason.message : '地图加载失败'
  }
})
onBeforeUnmount(() => {
  microphone.dispose()
  document.removeEventListener('visibilitychange', visibility)
  clearInterval(tick)
  controller?.dispose()
  life.abort()
})
</script>

<template>
  <section
    class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto bg-c-bg p-4 text-c-text lg:grid lg:grid-cols-[minmax(0,1fr)_22rem] lg:overflow-hidden lg:p-6"
    data-testid="earth-workspace"
    :data-playback-task="playback.taskId"
    :data-playback-state="playback.status"
    :data-playback-count="playback.count"
    :data-playback-at="playback.at"
  >
    <div
      class="flex min-h-112 min-w-0 shrink-0 flex-col overflow-hidden rounded-xl border border-c-border bg-c-surface lg:min-h-0"
      aria-label="三维地球"
    >
      <div class="relative min-h-72 flex-1 lg:min-h-0">
        <div
          ref="container"
          class="absolute inset-0"
          @pointerdown="pause"
          @wheel.passive="pause"
          @keydown="pause"
          @click="select"
        />
        <EarthAvatar
          v-if="enabledAvatar"
          ref="avatar"
          data-testid="earth-companion"
          class="pointer-events-none absolute bottom-0 right-[3%] h-[68%] max-h-140 w-[38%] max-w-104"
        />
        <div
          class="absolute left-4 top-4 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-c-border bg-c-panel/95 px-3 py-2 text-xs backdrop-blur-md"
        >
          <span class="font-semibold text-c-accent">◎ 私密探索</span>
          <span class="text-c-text-dim">拖动即暂停</span>
        </div>
      </div>
      <div
        class="max-h-52 shrink-0 overflow-y-auto border-t border-c-border bg-c-panel p-4 sm:p-5"
        aria-live="polite"
      >
        <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
          <span class="text-xs font-semibold text-c-accent">Animetta</span
          ><span class="text-xs text-c-text-dim" data-testid="earth-phase"
            >{{ phase }}<template v-if="remaining"> · {{ remaining }} 秒</template></span
          >
        </div>
        <p class="m-0 text-sm leading-6">{{ explanation }}</p>
      </div>
    </div>
    <aside
      class="flex min-h-0 min-w-0 shrink-0 flex-col gap-5 overflow-y-auto rounded-xl border border-c-border bg-c-surface p-4 sm:p-5"
      aria-label="探索对话"
    >
      <header class="shrink-0 border-b border-c-border pb-4">
        <p class="m-0 text-xs text-c-text-muted">我们正在看</p>
        <h1 class="mb-0 mt-2 text-xl font-semibold leading-7 tracking-tight">{{ title }}</h1>
        <p class="mb-0 mt-2 text-xs leading-5 text-c-text-dim">
          从模糊的记忆开始，慢慢认出你熟悉的地方。
        </p>
      </header>
      <div
        class="min-h-24 max-h-64 flex-1 space-y-3 overflow-y-auto lg:max-h-none"
        role="log"
        aria-label="探索记录"
      >
        <p
          v-if="!messages.length"
          class="m-0 rounded-xl bg-c-panel p-4 text-xs leading-6 text-c-text-dim"
        >
          告诉我一座城市、一个地标，或在地图上指出你熟悉的位置。
        </p>
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="break-words rounded-xl p-3 text-sm leading-6"
          :class="message.role === 'user' ? 'bg-c-user-bubble' : 'bg-c-panel'"
        >
          <span class="block text-xs text-c-text-muted mb-1">{{
            message.role === 'user' ? '你' : 'Animetta'
          }}</span
          >{{ message.text }}
        </div>
      </div>
      <div v-if="snapshot?.candidates.length" class="shrink-0 space-y-2" aria-label="地点候选">
        <button
          v-for="candidate in snapshot.candidates"
          :key="candidate.id"
          class="btn-secondary w-full flex-col items-start whitespace-normal text-left"
          @click="controller?.choose(candidate.id)"
        >
          {{ candidate.name }} ↗<span class="block text-xs text-c-text-muted">{{
            candidate.source.attribution
          }}</span>
        </button>
      </div>
      <form class="flex shrink-0 gap-2" @submit.prevent="submit">
        <input
          v-model="input"
          aria-label="告诉 Animetta 你的线索"
          placeholder="好像是在上海…"
          class="control-field min-w-0 flex-1"
          @input="pause"
          @focus="pause"
        />
        <button class="btn-accent" :disabled="!ready || !input.trim()">发送</button>
      </form>
      <div class="grid shrink-0 grid-cols-2 gap-2">
        <button class="btn-secondary" :disabled="!ready" @click="pause">暂停</button>
        <button class="btn-secondary" :disabled="!ready" @click="controller?.resume()">
          继续观察
        </button>
        <button class="btn-secondary" :disabled="!ready" @click="toggleSelection">
          {{ selecting ? '请点击地图…' : '指认这里' }}
        </button>
        <button class="btn-secondary" :disabled="!ready" @click="controller?.back()">
          返回观察点
        </button>
      </div>
      <div
        class="flex shrink-0 flex-wrap items-center gap-4 border-t border-c-border pt-4 text-xs text-c-text-dim"
      >
        <label class="flex items-center gap-2"
          ><input v-model="enabledAvatar" type="checkbox" /> 角色</label
        >
        <label class="flex items-center gap-2"
          ><input
            v-model="enabledVoice"
            type="checkbox"
            :disabled="!snapshot?.capabilities.voice"
            @change="controller?.voice(enabledVoice)"
          />
          语音讲解</label
        >
      </div>
      <button
        v-if="snapshot?.capabilities.asr"
        class="btn-secondary shrink-0"
        @click="recording ? microphone.stop() : microphone.start()"
      >
        {{ recording ? '结束录音并发送' : '说一条线索' }}
      </button>
      <p
        v-if="error || snapshot?.error"
        role="alert"
        class="m-0 shrink-0 rounded-xl border border-c-warning/30 bg-c-warning/8 p-3 text-xs leading-5 text-c-warning"
      >
        {{ error || snapshot?.error?.message }}
      </p>
      <p class="m-0 shrink-0 text-xs leading-5 text-c-text-muted">
        线索与指认仅用于本次私密探索。当前使用卫星影像展示与地名资料；视觉分析尚未开放。
      </p>
    </aside>
  </section>
</template>
