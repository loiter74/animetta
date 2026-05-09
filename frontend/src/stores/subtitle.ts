import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type SubtitleDisplayMode = 'original' | 'translated' | 'bilingual'
export type SubtitleFontSize = 'small' | 'medium' | 'large'

const STORAGE_KEY = 'anima_subtitle_config'

interface SubtitleConfig {
  enabled: boolean
  displayMode: SubtitleDisplayMode
  fontSize: SubtitleFontSize
  targetLanguage: string
  posX: number | null  // dragged X (px from left), null = default center
  posY: number | null  // dragged Y (px from bottom), null = default bottom
}

function migrateConfig(raw: any): SubtitleConfig {
  return {
    enabled: raw.enabled ?? true,
    displayMode: raw.displayMode ?? 'bilingual',
    fontSize: raw.fontSize ?? 'large',
    targetLanguage: raw.targetLanguage ?? 'English',
    posX: raw.posX ?? null,
    posY: raw.posY ?? null,
  }
}

function loadConfig(): SubtitleConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return migrateConfig(parsed)
    }
  } catch { /* ignore */ }
  return migrateConfig({})
}

function saveConfig(config: SubtitleConfig): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
}

export const useSubtitleStore = defineStore('subtitle', () => {
  const saved = loadConfig()

  const enabled = ref(saved.enabled)
  const displayMode = ref<SubtitleDisplayMode>(saved.displayMode)
  const fontSize = ref<SubtitleFontSize>(saved.fontSize)
  const targetLanguage = ref(saved.targetLanguage)
  const posX = ref<number | null>(saved.posX)
  const posY = ref<number | null>(saved.posY)

  // Persist on any change
  watch([enabled, displayMode, fontSize, targetLanguage, posX, posY], () => {
    saveConfig({
      enabled: enabled.value,
      displayMode: displayMode.value,
      fontSize: fontSize.value,
      targetLanguage: targetLanguage.value,
      posX: posX.value,
      posY: posY.value,
    })
  }, { deep: true })

  function toggle(): void {
    enabled.value = !enabled.value
  }

  function setDisplayMode(mode: SubtitleDisplayMode): void {
    displayMode.value = mode
  }

  function setFontSize(size: SubtitleFontSize): void {
    fontSize.value = size
  }

  function setTargetLanguage(lang: string): void {
    targetLanguage.value = lang
  }

  function setPosition(x: number, y: number): void {
    posX.value = x
    posY.value = y
  }

  function resetPosition(): void {
    posX.value = null
    posY.value = null
  }

  return {
    enabled,
    displayMode,
    fontSize,
    targetLanguage,
    posX,
    posY,
    toggle,
    setDisplayMode,
    setFontSize,
    setTargetLanguage,
    setPosition,
    resetPosition,
  }
})
