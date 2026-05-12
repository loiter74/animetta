<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMemeReviewStore } from '@/stores/memeReview'
import MemeCard from '@/components/meme/MemeCard.vue'

const store = useMemeReviewStore()
const router = useRouter()
const visible = ref(false)
const collecting = ref(false)
const collectResult = ref('')

onMounted(() => { visible.value = true; store.fetchMemes() })
function close() { router.push('/') }

function triggerCollect() {
  if (!store.socket) return
  collecting.value = true
  collectResult.value = ''
  store.socket.emit('meme:collect', {})
  store.socket.once('meme:collect', (data: { ok: boolean; count?: number; error?: string }) => {
    collecting.value = false
    if (data.ok) {
      collectResult.value = `采集完成，新增 ${data.count ?? 0} 个梗候选`
      setTimeout(() => { collectResult.value = ''; store.fetchMemes() }, 2000)
    } else {
      collectResult.value = data.error || '采集失败'
    }
  })
  setTimeout(() => { if (collecting.value) { collecting.value = false; collectResult.value = '采集超时，请重试' } }, 30000)
}

</script>

<template>
  <Transition name="panel">
    <div v-if="visible" class="fixed inset-0 z-50 flex justify-end">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close" />
      <div class="relative w-full max-w-[440px] h-full bg-c-bg border-l border-c-border flex flex-col shadow-2xl overflow-hidden">
        <!-- Header -->
        <div class="flex items-center justify-between px-5 py-4 border-b border-c-border shrink-0">
          <div class="flex items-center gap-2">
            <span class="text-lg">🔍</span>
            <h2 class="text-base font-semibold text-c-text">梗筛选器</h2>
          </div>
          <div class="flex items-center gap-2">
            <button
              class="px-3 py-1.5 text-xs rounded-lg transition-colors"
              :class="collecting ? 'bg-c-primary/20 text-c-primary animate-pulse' : collectResult ? 'bg-green-500/10 text-green-400' : 'bg-c-primary/10 text-c-primary hover:bg-c-primary/20'"
              :disabled="collecting"
              @click="triggerCollect"
            >
              {{ collecting ? '⏳ 采集中…' : collectResult ? '✓ ' + collectResult.split('，')[0] : '🔥 采集热梗' }}
            </button>
            <button
              class="w-8 h-8 flex items-center justify-center rounded-lg text-c-text-secondary hover:text-c-text hover:bg-c-surface transition-colors text-lg"
              @click="close"
            >
              ✕
            </button>
          </div>
        </div>

        <!-- Stats bar -->
        <div v-if="store.total > 0 && !store.isDone" class="px-5 py-2 border-b border-c-border/50 shrink-0">
          <div class="flex justify-between text-xs text-c-text-secondary mb-1">
            <span>{{ store.progress }}</span>
            <span>👍 {{ store.goodCount }} <span class="mx-1">|</span> 👎 {{ store.badCount }}</span>
          </div>
          <div class="h-1 rounded-full bg-c-border overflow-hidden">
            <div class="h-full rounded-full bg-c-primary transition-all duration-300" :style="{ width: `${((store.currentIndex + 1) / store.total) * 100}%` }" />
          </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto px-5 py-4">
          <!-- Loading -->
          <div v-if="store.loading" class="flex flex-col items-center justify-center h-full text-c-text-secondary gap-2">
            <span class="text-3xl animate-bounce">🔍</span>
            <p class="text-sm">正在加载梗列表…</p>
          </div>
          <!-- Empty -->
          <div v-else-if="store.total === 0" class="flex flex-col items-center justify-center h-full text-c-text-secondary gap-2">
            <span class="text-4xl">📭</span>
            <p class="text-sm">暂无待筛选梗</p>
            <p class="text-xs opacity-50">点击「🔥 采集热梗」或等待自动采集</p>
            <button class="mt-3 px-4 py-1.5 text-xs rounded-lg bg-c-primary/10 text-c-primary hover:bg-c-primary/20 transition-colors" @click="store.fetchMemes()">刷新列表</button>
          </div>
          <!-- Done -->
          <div v-else-if="store.isDone" class="flex flex-col items-center justify-center h-full text-c-text-secondary gap-2">
            <span class="text-4xl">🎉</span>
            <p class="text-sm">全部筛选完成！</p>
            <p class="text-xs opacity-50">👍 {{ store.goodCount }} 个好梗 | 👎 {{ store.badCount }} 个烂梗</p>
            <div class="flex gap-2 mt-3">
              <button class="px-3 py-1.5 text-xs rounded-lg bg-c-primary/10 text-c-primary hover:bg-c-primary/20 transition-colors" @click="store.exportDataset()">📦 导出数据集</button>
              <button class="px-3 py-1.5 text-xs rounded-lg border border-c-border text-c-text-secondary hover:text-c-text transition-colors" @click="store.fetchMemes()">重新加载</button>
            </div>
          </div>
          <!-- Cards -->
          <template v-else>
            <MemeCard :meme="store.currentMeme!" :feedback="store.feedback" :feedback-visible="store.feedbackVisible" />
            <div class="flex gap-3 mt-4">
              <button class="flex-1 py-3 rounded-xl text-sm font-medium transition-all duration-200 bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500/20 hover:scale-[1.02] active:scale-[0.98]" @click="store.voteGood()">👍 好梗</button>
              <button class="flex-1 py-3 rounded-xl text-sm font-medium transition-all duration-200 bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 hover:scale-[1.02] active:scale-[0.98]" @click="store.voteBad()">👎 烂梗</button>
            </div>
            <div class="flex gap-2 mt-2 justify-center">
              <button class="px-2 py-1 text-xs rounded-lg border border-c-border text-c-text-secondary hover:text-c-text disabled:opacity-30" :disabled="store.currentIndex === 0" @click="store.prevMeme()">← 上一条</button>
              <button class="px-2 py-1 text-xs rounded-lg border border-c-border text-c-text-secondary hover:text-c-text disabled:opacity-30" :disabled="store.currentIndex >= store.total - 1" @click="store.nextMeme()">跳过 →</button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.panel-enter-active { transition: all 0.3s ease-out; }
.panel-leave-active { transition: all 0.25s ease-in; }
.panel-enter-from { opacity: 0; }
.panel-enter-from > :last-child { transform: translateX(100%); }
.panel-leave-to { opacity: 0; }
.panel-leave-to > :last-child { transform: translateX(100%); }
</style>
