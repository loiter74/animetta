<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

const progressRef = ref<HTMLElement | null>(null)
const progress = ref(0)

onMounted(() => {
  ScrollTrigger.create({
    trigger: document.documentElement,
    start: 'top top',
    end: 'bottom bottom',
    onUpdate: (self) => {
      progress.value = self.progress
      if (progressRef.value) {
        gsap.set(progressRef.value, { scaleX: self.progress })
      }
    }
  })
})

onUnmounted(() => {
  ScrollTrigger.getAll().forEach(t => t.kill())
})
</script>

<template>
  <div class="fixed top-0 left-0 right-0 h-1 z-50 bg-c-border">
    <div
      ref="progressRef"
      class="h-full bg-c-accent origin-left will-change-transform"
      style="transform: scaleX(0)"
    />
  </div>
</template>
