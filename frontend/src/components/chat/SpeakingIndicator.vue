<template>
  <div class="absolute top-14 right-4 flex gap-1 px-3 py-2 bg-$c-panel/90 rounded-full backdrop-blur-md animate-fade-in z-20">
    <span v-for="i in 4" :key="i"
      class="w-1 bg-$c-accent rounded-full"
      :style="{
        height: '16px',
        animation: `wave 1s ease-in-out infinite ${i * 0.15}s`
      }"
    />
  </div>
</template>
