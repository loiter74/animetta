<script setup lang="ts">
import { defineAsyncComponent, ref } from 'vue'
import LiveOperationsWorkspace from '@/components/dashboard/LiveOperationsWorkspace.vue'
import ValidationWorkspace from '@/components/dashboard/ValidationWorkspace.vue'
import TitleBar from '@/components/layout/TitleBar.vue'
import MemoryWorkspace from '@/components/memory/MemoryWorkspace.vue'
import ProgramWorkspace from '@/components/program/ProgramWorkspace.vue'
import SectionTabs, { type SectionTab } from '@/components/shared/SectionTabs.vue'

const earthEnabled = import.meta.env.VITE_EARTH_ENABLED === 'true'
const EarthWorkspace = earthEnabled
  ? defineAsyncComponent(() => import('@/features/earth').then((module) => module.EarthWorkspace))
  : undefined

const tasks: readonly SectionTab[] = [
  { id: 'live', label: '现场', description: '监看直播健康、节目进度和执行链路' },
  { id: 'program', label: '节目', description: '编排脚本、制作唱歌内容和治理 Meme' },
  { id: 'memory', label: '记忆', description: '整理、检索和修正长期记忆' },
  { id: 'validation', label: '验证', description: '私密演练对话并重放弹幕事件' },
  ...(earthEnabled ? [{ id: 'earth', label: '探索', description: '一起寻找熟悉的地方' }] : []),
]

const activeTask = ref('live')
const programMode = ref('scripts')
const validationMode = ref('sandbox')
const sandboxDraft = ref('')

function sendMemoryToSandbox(content: string): void {
  sandboxDraft.value = content
  validationMode.value = 'sandbox'
  activeTask.value = 'validation'
}
</script>

<template>
  <div
    class="ops-shell flex h-full min-h-0 flex-col bg-c-bg/95 text-c-text"
    data-testid="dashboard-page"
  >
    <TitleBar />
    <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden lg:flex-row">
      <aside
        class="shrink-0 border-b border-c-border bg-c-surface/65 lg:flex lg:w-44 lg:flex-col lg:border-b-0 lg:border-r xl:w-48"
      >
        <div class="hidden px-6 pb-3 pt-6 lg:block">
          <p class="text-xs font-medium tracking-wide text-c-text-muted">工作区</p>
        </div>
        <SectionTabs
          v-model="activeTask"
          :tabs="tasks"
          label="后台任务"
          class="!border-b-0 !bg-transparent lg:flex-col lg:items-stretch lg:gap-2 lg:!px-3 lg:!py-0"
        />
      </aside>

      <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <LiveOperationsWorkspace
          v-if="activeTask === 'live'"
          id="后台任务-live-panel"
          role="tabpanel"
          aria-labelledby="后台任务-live-tab"
        />
        <ProgramWorkspace
          v-else-if="activeTask === 'program'"
          id="后台任务-program-panel"
          v-model="programMode"
          role="tabpanel"
          aria-labelledby="后台任务-program-tab"
        />
        <MemoryWorkspace
          v-else-if="activeTask === 'memory'"
          id="后台任务-memory-panel"
          role="tabpanel"
          aria-labelledby="后台任务-memory-tab"
          @send-to-sandbox="sendMemoryToSandbox"
        />
        <EarthWorkspace
          v-else-if="activeTask === 'earth'"
          id="后台任务-earth-panel"
          role="tabpanel"
          aria-labelledby="后台任务-earth-tab"
        />
        <ValidationWorkspace
          v-else
          id="后台任务-validation-panel"
          v-model="validationMode"
          role="tabpanel"
          aria-labelledby="后台任务-validation-tab"
          :draft="sandboxDraft"
        />
      </div>
    </div>
  </div>
</template>
