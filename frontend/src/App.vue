<script setup lang="ts">
import TitleBar from '@/components/layout/TitleBar.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useSocket } from '@/composables/useSocket'

// Initialize socket connection listener
useSocket()
</script>

<template>
  <div class="flex flex-col h-screen w-screen overflow-hidden bg-$c-bg text-$c-text">
    <TitleBar />
    <AppLayout />
  </div>
</template>
