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
    class="flex flex-1 min-h-0 bg-c-bg text-c-text overflow-hidden"
    data-testid="earth-workspace"
    :data-playback-task="playback.taskId"
    :data-playback-state="playback.status"
    :data-playback-count="playback.count"
    :data-playback-at="playback.at"
  >
    <div class="relative flex-1 min-w-0" aria-label="三维地球">
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
        class="absolute right-[3%] bottom-0 w-[34%] max-w-104 h-[62%] max-h-140 pointer-events-none"
      />
      <div class="absolute top-5 left-5 bg-c-panel/95 rounded-xl px-4 py-3 text-sm">
        <span class="text-c-accent">◎ 私密探索</span
        ><span class="ml-3 text-c-text-muted">拖动即暂停</span>
      </div>
      <div
        class="absolute bottom-13 left-6 box-border w-[calc(63%_-_3rem)] max-w-182 bg-c-panel/95 backdrop-blur-xl rounded-xl p-5 shadow-xl"
        aria-live="polite"
      >
        <div class="flex justify-between gap-3 mb-3">
          <span class="text-c-accent font-semibold">Animetta</span
          ><span class="text-xs text-c-text-muted" data-testid="earth-phase"
            >{{ phase }}<template v-if="remaining"> · {{ remaining }} 秒</template></span
          >
        </div>
        <p class="m-0 text-base xl:text-lg leading-relaxed">{{ explanation }}</p>
      </div>
    </div>
    <aside
      class="w-72 xl:w-88 shrink-0 bg-c-surface p-5 flex flex-col gap-4 overflow-y-auto"
      aria-label="探索对话"
    >
      <div>
        <p class="text-xs text-c-text-muted tracking-widest">我们正在看</p>
        <h1 class="text-2xl m-0">{{ title }}</h1>
        <p class="text-sm text-c-text-dim leading-relaxed">
          从模糊的记忆开始，慢慢认出你熟悉的地方。
        </p>
      </div>
      <div class="flex-1 min-h-24 overflow-y-auto space-y-3" role="log" aria-label="探索记录">
        <p v-if="!messages.length" class="text-sm text-c-text-muted leading-relaxed">
          告诉我一座城市、一个地标，或在地图上指出你熟悉的位置。
        </p>
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="rounded-xl p-3 text-sm leading-relaxed"
          :class="message.role === 'user' ? 'bg-c-user-bubble' : 'bg-c-panel'"
        >
          <span class="block text-xs text-c-text-muted mb-1">{{
            message.role === 'user' ? '你' : 'Animetta'
          }}</span
          >{{ message.text }}
        </div>
      </div>
      <div v-if="snapshot?.candidates.length" class="space-y-2" aria-label="地点候选">
        <button
          v-for="candidate in snapshot.candidates"
          :key="candidate.id"
          class="btn-ghost bg-c-panel w-full text-left"
          @click="controller?.choose(candidate.id)"
        >
          {{ candidate.name }} ↗<span class="block text-xs text-c-text-muted">{{
            candidate.source.attribution
          }}</span>
        </button>
      </div>
      <form class="flex gap-2" @submit.prevent="submit">
        <input
          v-model="input"
          aria-label="告诉 Animetta 你的线索"
          placeholder="好像是在上海…"
          class="min-w-0 flex-1 bg-c-panel text-c-text border-none rounded-xl p-3"
          @input="pause"
          @focus="pause"
        />
        <button class="btn-accent" :disabled="!ready || !input.trim()">发送</button>
      </form>
      <div class="grid grid-cols-2 gap-2">
        <button class="btn-accent" :disabled="!ready" @click="pause">暂停</button>
        <button class="btn-ghost bg-c-panel" :disabled="!ready" @click="controller?.resume()">
          继续观察
        </button>
        <button class="btn-ghost bg-c-panel" :disabled="!ready" @click="toggleSelection">
          {{ selecting ? '请点击地图…' : '指认这里' }}
        </button>
        <button class="btn-ghost bg-c-panel" :disabled="!ready" @click="controller?.back()">
          返回观察点
        </button>
      </div>
      <div class="flex gap-4 text-sm text-c-text-dim">
        <label><input v-model="enabledAvatar" type="checkbox" /> 角色</label>
        <label
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
        class="btn-ghost bg-c-panel"
        @click="recording ? microphone.stop() : microphone.start()"
      >
        {{ recording ? '结束录音并发送' : '说一条线索' }}
      </button>
      <p
        v-if="error || snapshot?.error"
        role="alert"
        class="text-sm text-c-warning leading-relaxed"
      >
        {{ error || snapshot?.error?.message }}
      </p>
      <p class="text-xs text-c-text-muted leading-relaxed m-0">
        线索与指认仅用于本次私密探索。当前使用卫星影像展示与地名资料；视觉分析尚未开放。
      </p>
    </aside>
  </section>
</template>
