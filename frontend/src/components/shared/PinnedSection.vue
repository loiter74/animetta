<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface Props {
  /** Pin position: 'left' for left-pinned title, 'top' for top-pinned header */
  pinPosition?: 'left' | 'top'
  /** Section title */
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  pinPosition: 'left',
  title: ''
})

const sectionRef = ref<HTMLElement | null>(null)
const titleRef = ref<HTMLElement | null>(null)
const contentRef = ref<HTMLElement | null>(null)

onMounted(() => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (prefersReducedMotion) return

  if (props.pinPosition === 'left' && titleRef.value && contentRef.value) {
    // Left-pinned title, content scrolls on right
    ScrollTrigger.create({
      trigger: sectionRef.value,
      start: 'top top',
      end: 'bottom bottom',
      pin: titleRef.value,
      pinSpacing: false
    })
  } else if (props.pinPosition === 'top' && titleRef.value) {
    // Top-pinned header
    ScrollTrigger.create({
      trigger: sectionRef.value,
      start: 'top top',
      end: 'bottom bottom',
      pin: titleRef.value,
      pinSpacing: false
    })
  }
})

onUnmounted(() => {
  ScrollTrigger.getAll().forEach(t => t.kill())
})
</script>

<template>
  <section
    ref="sectionRef"
    class="relative py-24 md:py-36"
    :class="pinPosition === 'left' ? 'flex gap-12' : ''"
  >
    <!-- Pinned Title -->
    <div
      ref="titleRef"
      class="shrink-0"
      :class="pinPosition === 'left' ? 'w-1/3' : 'mb-8 text-center'"
    >
      <h2
        v-if="title"
        class="text-3xl md:text-4xl font-bold text-c-text tracking-tight"
      >
        {{ title }}
      </h2>
      <slot name="title" />
    </div>

    <!-- Scrollable Content -->
    <div
      ref="contentRef"
      :class="pinPosition === 'left' ? 'flex-1 space-y-12' : 'space-y-12'"
    >
      <slot />
    </div>
  </section>
</template>
