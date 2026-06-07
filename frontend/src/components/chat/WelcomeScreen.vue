<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { gsap } from 'gsap'
import SceneEffects from '@/components/shared/SceneEffects.vue'

const emit = defineEmits<{
  dismiss: []
}>()

const heroRef = ref<HTMLElement | null>(null)
const bgRef = ref<HTMLElement | null>(null)
const titleRef = ref<HTMLElement | null>(null)
const subtitleRef = ref<HTMLElement | null>(null)
const ctaRef = ref<HTMLElement | null>(null)
const ctx = ref<gsap.Context>()

onMounted(() => {
  // Check prefers-reduced-motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (prefersReducedMotion) return

  // GSAP entrance timeline
  ctx.value = gsap.context(() => {
    const tl = gsap.timeline({ defaults: { ease: 'power2.out' } })

    // Title entrance
    tl.from(titleRef.value, {
      opacity: 0,
      y: 40,
      duration: 0.8
    })

    // Subtitle entrance
    tl.from(subtitleRef.value, {
      opacity: 0,
      y: 20,
      duration: 0.6
    }, '-=0.4')

    // CTA buttons stagger
    tl.from(ctaRef.value?.children || [], {
      opacity: 0,
      y: 20,
      duration: 0.5,
      stagger: 0.15
    }, '-=0.3')
  })

  // Parallax scroll effect
  const handleScroll = () => {
    if (!bgRef.value) return
    const scrollY = window.scrollY
    gsap.set(bgRef.value, { y: scrollY * 0.5 })
  }

  window.addEventListener('scroll', handleScroll, { passive: true })
  onUnmounted(() => {
    window.removeEventListener('scroll', handleScroll)
    ctx.value?.revert()
  })
})

function handleStartChat() {
  emit('dismiss')
}
</script>

<template>
  <div ref="heroRef" class="relative h-screen overflow-hidden">
    <!-- Layer 0: Background with parallax -->
    <div
      ref="bgRef"
      class="absolute inset-0 bg-cover bg-center will-change-transform"
      style="background-image: url('https://picsum.photos/seed/anime-night/1920/1080')"
    />

    <!-- Layer 1: Radial gradient wash -->
    <div class="absolute inset-0 bg-gradient-radial from-transparent via-black/30 to-black/70" />

    <!-- Layer 2: Scene Effects (particles) -->
    <SceneEffects class="z-10" />

    <!-- Layer 3: Content -->
    <div class="relative z-20 flex flex-col items-center justify-center h-full px-6 text-center select-none">
      <!-- Title -->
      <h1
        ref="titleRef"
        class="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 tracking-tight"
        style="text-shadow: 0 4px 20px rgba(232, 121, 168, 0.3)"
      >
        Animetta<span class="text-c-accent">.</span>
      </h1>

      <!-- Subtitle -->
      <p
        ref="subtitleRef"
        class="text-lg md:text-xl text-white/80 max-w-md mb-10 leading-relaxed"
      >
        和我一起聊会儿天吧
      </p>

      <!-- CTA Buttons -->
      <div ref="ctaRef" class="flex flex-col sm:flex-row gap-4">
        <button
          class="btn-accent text-base px-8 py-3 rounded-xl shadow-lg shadow-c-accent/30 hover:shadow-c-accent/50 transition-shadow"
          @click="handleStartChat"
        >
          开始对话
        </button>
        <button
          class="btn-ghost text-base px-8 py-3 rounded-xl border border-white/20 text-white/80 hover:text-white hover:border-white/40 transition-all"
        >
          了解更多
        </button>
      </div>

      <!-- Scroll hint -->
      <div class="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
        <svg class="w-6 h-6 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bg-gradient-radial {
  background: radial-gradient(ellipse at center, var(--tw-gradient-from), var(--tw-gradient-via), var(--tw-gradient-to));
}
</style>
