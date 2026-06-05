<script setup lang="ts">
import { ref } from 'vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import LiveChatPanel from '@/components/chat/LiveChatPanel.vue'
import SettingsPanel from '@/components/settings/SettingsPanel.vue'
import MemoryPanel from '@/components/memory/MemoryPanel.vue'
import PersonalityPanel from '@/components/personality/PersonalityPanel.vue'
import MusicCard from '@/components/singing/MusicCard.vue'
import PopOutButton from '@/components/live2d/PopOutButton.vue'
import { useDanmaku } from '@/composables/useDanmaku'
import { useMobile } from '@/composables/useMobile'

const props = defineProps<{
  live2dPopout: boolean
}>()

const emit = defineEmits<{
  popout: []
  popoutClosed: []
}>()

const { isMobile } = useMobile()
const isCollapsed = ref(false)
const activeTab = ref<'chat' | 'live' | 'memory' | 'personality' | 'singing' | 'settings'>('chat')

// Mobile tab definitions (icon-only)
const mobileTabs = [
  { key: 'chat' as const, icon: '💬', label: '聊天' },
  { key: 'live' as const, icon: '📺', label: '直播' },
  { key: 'memory' as const, icon: '🧠', label: '记忆' },
  { key: 'personality' as const, icon: '🎭', label: '人格' },
  { key: 'singing' as const, icon: '🎵', label: '音乐' },
  { key: 'settings' as const, icon: '⚙️', label: '设置' },
]

// Desktop tab labels
const desktopTabLabels: Record<string, string> = {
  chat: '💬 聊天', live: '📺 直播', memory: '🧠 记忆',
  personality: '🎭 人格', singing: '🎵 音乐', settings: '⚙️ 设置',
}

// Initialize danmaku socket listeners (runs globally, not per-tab)
useDanmaku()
</script>

<template>
  <!-- ========== MOBILE LAYOUT ========== -->
  <div v-if="isMobile" class="flex flex-col h-full pointer-events-none">
    <!-- Mobile: panel content (fills space between Live2D and bottom nav) -->
    <div class="flex-1 overflow-hidden relative pointer-events-auto">
      <Transition name="fade" mode="out-in">
        <ChatPanel v-if="activeTab === 'chat'" key="chat" />
        <LiveChatPanel v-else-if="activeTab === 'live'" key="live" />
        <MemoryPanel v-else-if="activeTab === 'memory'" key="memory" />
        <PersonalityPanel v-else-if="activeTab === 'personality'" key="personality" />
        <MusicCard v-else-if="activeTab === 'singing'" key="singing" />
        <SettingsPanel v-else key="settings" />
      </Transition>
    </div>

    <!-- Mobile: fixed bottom navigation bar -->
    <nav class="shrink-0 pointer-events-auto flex items-center justify-around py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] bg-c-surface/90 backdrop-blur-xl border-t border-c-border">
      <button
        v-for="tab in mobileTabs"
        :key="tab.key"
        class="flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-all touch-manipulation"
        :class="activeTab === tab.key
          ? 'bg-c-accent/20 text-c-accent'
          : 'text-c-text-dim active:text-c-accent'"
        @click="activeTab = tab.key"
      >
        <span class="text-lg leading-none">{{ tab.icon }}</span>
        <span class="text-9px leading-tight">{{ tab.label }}</span>
      </button>
    </nav>
  </div>

  <!-- ========== DESKTOP LAYOUT (unchanged) ========== -->
  <div v-else class="absolute inset-y-0 right-0 z-20 flex pointer-events-none">
    <!-- Collapse trigger (visible when collapsed) -->
      <button
        v-if="isCollapsed"
        class="pointer-events-auto w-12 flex flex-col items-center pt-4 gap-3
               bg-c-bg/60 backdrop-blur-xl border border-c-border/30 rounded-l-2xl
               text-c-text-dim hover:text-c-accent hover:bg-c-bg/80 transition-colors"
        aria-label="展开侧边栏"
        @click="isCollapsed = false"
      >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M5 12h14M12 5l7 7-7 7" />
      </svg>
      <span class="text-10px writing-mode-vertical">{{ desktopTabLabels[activeTab] }}</span>
    </button>

    <!-- Main panel -->
    <Transition name="slide">
      <div
        v-if="!isCollapsed"
        class="pointer-events-auto flex flex-col glass-strong m-3 ml-0 w-[420px] min-w-[320px] max-w-[480px] interactive-panel"
        :class="live2dPopout ? '!w-full !max-w-none !m-0 rounded-none' : ''"
      >
        <!-- Header: Tabs + Collapse -->
        <div class="flex items-center border-b border-c-border px-4 py-3 shrink-0">
          <!-- Tab buttons -->
          <div class="flex gap-1.5 flex-1">
            <button
              v-for="tab in (['chat', 'live', 'memory', 'personality', 'singing', 'settings'] as const)"
              :key="tab"
              class="px-3.5 py-2 rounded-lg text-11px font-medium transition-all"
              :class="activeTab === tab
                ? 'bg-c-accent/20 text-c-accent'
                : 'bg-c-bg/40 text-c-text-dim hover:text-c-text hover:bg-c-panel/50'"
              @click="activeTab = tab"
            >
              {{ desktopTabLabels[tab] }}
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
                   bg-c-bg/40 text-c-text-dim hover:text-c-text hover:bg-c-bg/60 transition-colors"
            aria-label="收起侧边栏"
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
            <LiveChatPanel v-else-if="activeTab === 'live'" key="live" />
            <MemoryPanel v-else-if="activeTab === 'memory'" key="memory" />
            <PersonalityPanel v-else-if="activeTab === 'personality'" key="personality" />
            <MusicCard v-else-if="activeTab === 'singing'" key="singing" />
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

/* Mobile slide-up transition */
.slide-up-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-up-leave-active {
  transition: all 0.25s ease-in;
}
.slide-up-enter-from {
  transform: translateY(100%);
  opacity: 0;
}
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
