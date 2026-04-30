<template>
  <div class="flex gap-1 px-3 py-1.5 animate-fade-in shrink-0">
    <span v-for="i in 4" :key="i"
      class="w-1 bg-c-accent rounded-full"
      :style="{
        height: '12px',
        animation: `wave 1s ease-in-out infinite ${i * 0.15}s`
      }"
    />
    <span class="text-10px text-c-text-muted ml-1 self-center">语音中</span>
  </div>
</template>
