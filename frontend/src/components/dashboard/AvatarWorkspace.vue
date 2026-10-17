<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  AVATAR_PREVIEW_EMOTIONS,
  type AvatarPreviewCommand,
  type AvatarPreviewState,
} from '@/shared/live2d/previewContract'
import { resolveLive2DModelProfile } from '@/shared/live2d/modelProfiles'

const preview = ref<HTMLIFrameElement | null>(null)
const state = ref<AvatarPreviewState | null>(null)
const selectedEmotion = ref('neutral')
const waiting = ref(false)
const profile = resolveLive2DModelProfile('whale-maid-v1')
const expressions = Object.entries(profile.expressions ?? {})
const ready = computed(() => state.value?.loaded === true)
const expressionLabel = computed(
  () => profile.expressions?.[state.value?.expression ?? '']?.label ?? '等待预览',
)
const emotionLabels: Readonly<Record<string, string>> = {
  neutral: '平静',
  happy: '开心',
  sad: '难过',
  angry: '生气',
  surprised: '惊讶',
  thinking: '思考',
}

function isPreviewState(value: unknown): value is AvatarPreviewState {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  return (
    candidate.modelId === profile.id &&
    typeof candidate.loaded === 'boolean' &&
    typeof candidate.expression === 'string' &&
    typeof candidate.emotion === 'string' &&
    (candidate.mode === 'auto' || candidate.mode === 'manual') &&
    typeof candidate.zoom === 'number' &&
    Number.isFinite(candidate.zoom) &&
    typeof candidate.mouthDemo === 'boolean' &&
    typeof candidate.socketState === 'string' &&
    typeof candidate.livestreamState === 'string'
  )
}

function onPreviewMessage(event: MessageEvent): void {
  const frameWindow = preview.value?.contentWindow
  if (!frameWindow || event.origin !== location.origin || event.source !== frameWindow) return
  const message: unknown = event.data
  if (!message || typeof message !== 'object') return
  const envelope = message as Record<string, unknown>
  if (envelope.type !== 'animetta:avatar-preview-state' || !isPreviewState(envelope.state)) return
  state.value = envelope.state
  selectedEmotion.value = envelope.state.emotion
  waiting.value = false
}

function send(command: AvatarPreviewCommand): void {
  if (!ready.value || !preview.value?.contentWindow) return
  waiting.value = true
  preview.value.contentWindow.postMessage(
    { type: 'animetta:avatar-preview-command', command },
    location.origin,
  )
}

function onPreviewLoad(): void {
  state.value = null
  waiting.value = false
  preview.value?.contentWindow?.postMessage(
    { type: 'animetta:avatar-preview-command', command: { type: 'reset' } },
    location.origin,
  )
}

function simulateEmotion(): void {
  send({ type: 'emotion', emotion: selectedEmotion.value })
}

function changeZoom(delta: number): void {
  send({ type: 'zoom', value: Math.max(1, Math.min(3, (state.value?.zoom ?? 1) + delta)) })
}

onMounted(() => window.addEventListener('message', onPreviewMessage))
onUnmounted(() => window.removeEventListener('message', onPreviewMessage))
</script>

<template>
  <section
    class="flex h-full min-h-0 flex-col gap-4 overflow-y-auto text-c-text lg:overflow-hidden"
    data-testid="avatar-workspace"
  >
    <header class="shrink-0">
      <h2 class="text-base font-semibold">立绘调试</h2>
      <p class="workspace-copy">模拟与手动操作只影响此预览，直播默认跟随公开情绪</p>
    </header>

    <div
      class="grid shrink-0 gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,20rem)] lg:overflow-hidden"
    >
      <div
        class="h-[50dvh] min-h-48 overflow-hidden rounded-xl border border-c-border bg-c-surface lg:h-full lg:min-h-0"
      >
        <iframe
          ref="preview"
          src="/live.html?review=1&scene=empty&avatar=whale-maid-v1&media=muted&avatarDebug=1"
          title="立绘调试预览"
          class="block h-full w-full border-0"
          @load="onPreviewLoad"
        />
      </div>

      <aside
        class="flex flex-col gap-4 rounded-xl border border-c-border bg-c-panel p-4 lg:min-h-0 lg:overflow-y-auto"
      >
        <div>
          <h2 class="text-sm font-semibold">当前状态</h2>
          <dl class="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
            <dt class="text-c-text-muted">模型</dt>
            <dd class="break-all">{{ state?.modelId ?? profile.id }}</dd>
            <dt class="text-c-text-muted">加载</dt>
            <dd>{{ state ? (state.loaded ? '已加载' : '加载中') : '等待预览返回状态' }}</dd>
            <dt class="text-c-text-muted">连接</dt>
            <dd>{{ state?.socketState ?? '等待预览' }}</dd>
            <dt class="text-c-text-muted">直播</dt>
            <dd>{{ state?.livestreamState || '等待预览' }}</dd>
            <dt class="text-c-text-muted">当前情绪</dt>
            <dd>{{ state ? (emotionLabels[state.emotion] ?? state.emotion) : '等待预览' }}</dd>
            <dt class="text-c-text-muted">当前表情</dt>
            <dd>{{ expressionLabel }}</dd>
            <dt class="text-c-text-muted">驱动</dt>
            <dd>
              {{ state ? (state.mode === 'auto' ? '自动跟随情绪' : '手动预览') : '等待预览' }}
            </dd>
          </dl>
        </div>

        <fieldset :disabled="!ready" class="flex flex-col gap-4 disabled:opacity-50">
          <div class="border-t border-c-border pt-4">
            <h2 class="mb-3 text-sm font-semibold">表情</h2>
            <div class="flex flex-wrap gap-2" role="group" aria-label="立绘表情">
              <button
                v-for="[name, expression] in expressions"
                :key="name"
                type="button"
                class="btn-secondary"
                :aria-pressed="state?.mode === 'manual' && state.expression === name"
                @click="send({ type: 'expression', name })"
              >
                {{ expression.label }}
              </button>
              <button
                type="button"
                class="btn-secondary"
                :aria-pressed="state?.mode === 'auto'"
                @click="send({ type: 'expression', name: null })"
              >
                自动跟随
              </button>
            </div>
          </div>

          <label class="flex flex-col gap-2 text-sm">
            <span class="font-semibold">情绪模拟</span>
            <select
              v-model="selectedEmotion"
              class="control-field w-full"
              aria-label="情绪模拟"
              @change="simulateEmotion"
            >
              <option v-for="emotion in AVATAR_PREVIEW_EMOTIONS" :key="emotion" :value="emotion">
                {{ emotionLabels[emotion] ?? emotion }}
              </option>
            </select>
          </label>

          <button
            type="button"
            class="btn-secondary"
            :aria-pressed="state?.mouthDemo ?? false"
            @click="send({ type: 'mouth-demo' })"
          >
            {{ state?.mouthDemo ? '停止口型演示' : '口型演示' }}
          </button>

          <div class="border-t border-c-border pt-4">
            <div class="mb-3 flex items-center justify-between gap-2 text-sm">
              <h2 class="font-semibold">取景</h2>
              <output aria-label="立绘缩放" class="text-c-text-dim tabular-nums">
                {{ Math.round((state?.zoom ?? 1) * 100) }}%
              </output>
            </div>
            <div class="flex flex-wrap gap-2" role="group" aria-label="立绘缩放控制">
              <button
                type="button"
                class="btn-secondary"
                :disabled="(state?.zoom ?? 1) <= 1"
                @click="changeZoom(-0.25)"
              >
                缩小
              </button>
              <button
                type="button"
                class="btn-secondary"
                :disabled="(state?.zoom ?? 1) >= 3"
                @click="changeZoom(0.25)"
              >
                放大
              </button>
              <button type="button" class="btn-secondary" @click="send({ type: 'zoom', value: 1 })">
                全身
              </button>
            </div>
          </div>
        </fieldset>
        <p v-if="waiting" role="status" class="text-xs text-c-text-muted">等待预览返回状态…</p>
      </aside>
    </div>
  </section>
</template>
