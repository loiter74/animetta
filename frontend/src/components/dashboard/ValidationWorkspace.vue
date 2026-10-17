<script setup lang="ts">
import { ref, watch } from 'vue'
import ProgramReplayPanel from '@/components/program/ProgramReplayPanel.vue'
import SectionTabs, { type SectionTab } from '@/components/shared/SectionTabs.vue'
import ConversationSandbox from './ConversationSandbox.vue'
import AvatarWorkspace from './AvatarWorkspace.vue'

const props = defineProps<{
  modelValue: string
  draft?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const sandboxDraft = ref(props.draft ?? '')

watch(
  () => props.draft,
  (value) => {
    if (value !== undefined) sandboxDraft.value = value
  },
)

const modes: readonly SectionTab[] = [
  { id: 'sandbox', label: '对话沙盒', description: '使用当前模型私密演练并核对执行证据' },
  { id: 'replay', label: '弹幕重放', description: '用节目脚本或 JSONL 验证直播执行' },
  { id: 'avatar', label: '立绘调试', description: '检查情绪驱动表情、口型与立绘缩放' },
]
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col" data-testid="validation-workspace">
    <header class="shrink-0 border-b border-c-border bg-c-surface/35 px-4 py-4 sm:px-6">
      <div class="mb-4">
        <h1 class="workspace-title">验证</h1>
        <p class="workspace-copy">在演练中检查对话、弹幕与立绘的表现</p>
      </div>
      <SectionTabs
        :model-value="modelValue"
        :tabs="modes"
        label="验证工作区"
        class="!border-b-0 !bg-transparent !p-0"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </header>

    <main
      v-if="modelValue === 'sandbox'"
      id="验证工作区-sandbox-panel"
      role="tabpanel"
      aria-labelledby="验证工作区-sandbox-tab"
      class="min-h-0 min-w-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:overflow-hidden"
    >
      <ConversationSandbox v-model="sandboxDraft" />
    </main>
    <main
      v-else-if="modelValue === 'replay'"
      id="验证工作区-replay-panel"
      role="tabpanel"
      aria-labelledby="验证工作区-replay-tab"
      class="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain p-4 sm:p-6"
    >
      <ProgramReplayPanel />
    </main>
    <main
      v-else-if="modelValue === 'avatar'"
      id="验证工作区-avatar-panel"
      role="tabpanel"
      aria-labelledby="验证工作区-avatar-tab"
      class="min-h-0 min-w-0 flex-1 overflow-hidden p-4 sm:p-6"
    >
      <AvatarWorkspace />
    </main>
  </div>
</template>
