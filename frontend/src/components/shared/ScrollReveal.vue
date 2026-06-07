<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

interface Props {
  /** Animation delay in seconds (default: 0) */
  delay?: number
  /** Animation duration in seconds (default: 0.6) */
  duration?: number
  /** Y offset in px (default: 30) */
  y?: number
  /** Scale start value (default: 1) */
  scale?: number
}

const props = withDefaults(defineProps<Props>(), {
  delay: 0,
  duration: 0.6,
  y: 30,
  scale: 1
})

const elementRef = ref<HTMLElement | null>(null)

onMounted(() => {
  if (!elementRef.value) return

  // Check prefers-reduced-motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (prefersReducedMotion) return

  gsap.from(elementRef.value, {
    opacity: 0,
    y: props.y,
    scale: props.scale,
    duration: props.duration,
    delay: props.delay,
    ease: 'power2.out',
    scrollTrigger: {
      trigger: elementRef.value,
      start: 'top 85%',
      toggleActions: 'play none none reverse'
    }
  })
})
</script>

<template>
  <div ref="elementRef">
    <slot />
  </div>
</template>
