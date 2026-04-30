<script setup lang="ts">
import { ref } from 'vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import SettingsPanel from '@/components/settings/SettingsPanel.vue'
import PopOutButton from '@/components/live2d/PopOutButton.vue'

const props = defineProps<{
  live2dPopout: boolean
}>()

const emit = defineEmits<{
  popout: []
  popoutClosed: []
}>()

const isCollapsed = ref(false)
const activeTab = ref<'chat' | 'settings'>('chat')
</script>

<template>
  <div class="absolute inset-y-0 right-0 z-20 flex pointer-events-none">
    <!-- Collapse trigger (visible when collapsed) -->
    <button
      v-if="isCollapsed"
      class="pointer-events-auto w-12 flex flex-col items-center pt-4 gap-3
             bg-c-surface/60 backdrop-blur-xl border-l border-c-border rounded-l-2xl
             text-c-text-dim hover:text-c-accent transition-colors"
      @click="isCollapsed = false"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M5 12h14M12 5l7 7-7 7" />
      </svg>
      <span class="text-10px writing-mode-vertical">聊天</span>
    </button>

    <!-- Main panel -->
    <Transition name="slide">
      <div
        v-if="!isCollapsed"
        class="pointer-events-auto flex flex-col glass-strong m-3 ml-0 w-[380px] min-w-[320px] max-w-[420px]"
        :class="live2dPopout ? '!w-full !max-w-none !m-0 rounded-none' : ''"
      >
        <!-- Header: Tabs + Collapse -->
        <div class="flex items-center border-b border-c-border px-3 py-2 shrink-0">
          <!-- Tab buttons -->
          <div class="flex gap-1 flex-1">
            <button
              class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
              :class="activeTab === 'chat'
                ? 'bg-c-accent/20 text-c-accent'
                : 'text-c-text-dim hover:text-c-text hover:bg-c-panel/50'"
              @click="activeTab = 'chat'"
            >
              💬 聊天
            </button>
            <button
              class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
              :class="activeTab === 'settings'
                ? 'bg-c-accent/20 text-c-accent'
                : 'text-c-text-dim hover:text-c-text hover:bg-c-panel/50'"
              @click="activeTab = 'settings'"
            >
              ⚙️ 设置
            </button>
          </div>

          <!-- PopOut button (when Live2D is embedded) -->
          <PopOutButton
            v-if="!live2dPopout"
            class="mr-1"
            @popout="emit('popout')"
          />

          <!-- Collapse button -->
          <button
            class="w-7 h-7 flex items-center justify-center rounded-lg
                   text-c-text-dim hover:text-c-text hover:bg-c-panel/50 transition-colors"
            @click="isCollapsed = true"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
        </div>

        <!-- Tab content -->
        <div class="flex-1 overflow-hidden relative">
          <Transition name="fade" mode="out-in">
            <ChatPanel v-if="activeTab === 'chat'" key="chat" />
            <SettingsPanel v-else key="settings" />
          </Transition>
        </div>
      </div>
    </Transition>

    <!-- Popout closed indicator -->
    <div
      v-if="live2dPopout && isCollapsed"
      class="pointer-events-auto absolute top-4 left-3"
    >
      <button
        class="btn-ghost text-xs flex items-center gap-1 px-3 py-2 glass"
        @click="emit('popoutClosed')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        收回 Live2D
      </button>
    </div>
  </div>
</template>

<style scoped>
.slide-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-leave-active {
  transition: all 0.25s ease-in;
}
.slide-enter-from {
  transform: translateX(100%);
  opacity: 0;
}
.slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.writing-mode-vertical {
  writing-mode: vertical-rl;
}
</style>
