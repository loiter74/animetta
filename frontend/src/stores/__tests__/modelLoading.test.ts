import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useModelLoadingStore } from '@/stores/modelLoading'

describe('useModelLoadingStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('starts with empty models', () => {
      const store = useModelLoadingStore()
      expect(store.models.size).toBe(0)
      expect(store.modelNames).toEqual([])
    })

    it('isLoading is false when no models', () => {
      const store = useModelLoadingStore()
      expect(store.isLoading).toBe(false)
    })

    it('progress is 1 when no models', () => {
      const store = useModelLoadingStore()
      expect(store.progress).toBe(1)
    })

    it('summary is empty when no models', () => {
      const store = useModelLoadingStore()
      expect(store.summary).toBe('')
    })
  })

  describe('updateModelStatus', () => {
    it('tracks a loading model', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loading' })
      expect(store.models.size).toBe(1)
      expect(store.isLoading).toBe(true)
      expect(store.progress).toBe(0)
      expect(store.modelNames).toEqual(['deepseek'])
    })

    it('tracks multiple models', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loading' })
      store.updateModelStatus({ service: 'tts', name: 'edge-tts', status: 'loading' })
      expect(store.models.size).toBe(2)
      expect(store.isLoading).toBe(true)
    })

    it('updates existing model status', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loading' })
      expect(store.isLoading).toBe(true)
      expect(store.progress).toBe(0)

      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loaded' })
      expect(store.isLoading).toBe(false)
      expect(store.progress).toBe(1)
    })

    it('handles error status', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'asr', name: 'whisper', status: 'loading' })
      store.updateModelStatus({ service: 'asr', name: 'whisper', status: 'error', error: 'OOM' })
      expect(store.isLoading).toBe(false)
      expect(store.progress).toBe(1)
    })

    it('summary shows loading service names', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loading' })
      expect(store.summary).toContain('llm')
      expect(store.summary).toContain('正在加载')
    })

    it('summary is empty when all models loaded', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loading' })
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loaded' })
      expect(store.summary).toBe('')
    })
  })

  describe('clear', () => {
    it('clears all models', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loading' })
      store.clear()
      expect(store.models.size).toBe(0)
      expect(store.isLoading).toBe(false)
    })
  })

  describe('progress computation', () => {
    it('progress is 0.5 when half of models are loaded', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loading' })
      store.updateModelStatus({ service: 'tts', name: 'edge-tts', status: 'loaded' })
      expect(store.progress).toBe(0.5)
    })

    it('progress is 0.33 when one of three models is loaded', () => {
      const store = useModelLoadingStore()
      store.updateModelStatus({ service: 'llm', name: 'deepseek', status: 'loaded' })
      store.updateModelStatus({ service: 'tts', name: 'edge-tts', status: 'loading' })
      store.updateModelStatus({ service: 'asr', name: 'whisper', status: 'loading' })
      expect(store.progress).toBeCloseTo(0.333, 2)
    })
  })
})
