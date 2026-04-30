import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import unocss from 'unocss/vite'

export default defineConfig({
  root: resolve(__dirname),
  build: {
    rollupOptions: {
      input: resolve(__dirname, 'index.html')
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  optimizeDeps: {
    include: ['pixi.js', 'pixi-live2d-display', '@pixi/utils', '@pixi/math', '@pixi/core', '@pixi/display']
  },
  plugins: [
    vue(),
    unocss()
  ]
})
