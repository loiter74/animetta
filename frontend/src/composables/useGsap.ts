import { ref, onMounted, onUnmounted } from 'vue'
import { gsap } from 'gsap'

/**
 * GSAP context composable with automatic lifecycle management.
 * Creates a GSAP context on mount and reverts on unmount.
 * Respects prefers-reduced-motion preference.
 */
export function useGsap(callback: (gsapInstance: typeof gsap) => void) {
  const ctx = ref<gsap.Context>()
  const prefersReducedMotion = ref(false)

  onMounted(() => {
    // Check prefers-reduced-motion
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = mediaQuery.matches

    // Only create GSAP context if user doesn't prefer reduced motion
    if (!prefersReducedMotion.value) {
      ctx.value = gsap.context(() => callback(gsap))
    }
  })

  onUnmounted(() => {
    ctx.value?.revert()
  })

  return { ctx, prefersReducedMotion }
}
