import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type SubtitleDisplayMode = 'original' | 'translated' | 'bilingual'
export type SubtitleFontSize = 'small' | 'medium' | 'large'

const STORAGE_KEY = 'animetta_subtitle_config'

interface SubtitleConfig {
  _version: number                    // storage format version (2 = ratio-based)
  enabled: boolean
  displayMode: SubtitleDisplayMode
  fontSize: SubtitleFontSize
  targetLanguage: string
  posX: number | null  // ratio (0.0~1.0) relative to container width, null = default center
  posY: number | null  // ratio (0.0~1.0) relative to container height, null = default bottom
}

/** Approximate ratio conversion for legacy px data (v1 → v2).
 *  Uses window dimensions as fallback since original container size is unknown. */
function migrateConfig(raw: any): SubtitleConfig {
  const isV1 = raw._version == null || (typeof raw.posX === 'number' && raw._version === undefined)
  let posX: number | null = null
  let posY: number | null = null

  if (isV1 && typeof raw.posX === 'number' && typeof raw.posY === 'number') {
    // Legacy px values → approximate ratios using window dimensions
    const w = window.innerWidth || 1280
    const h = window.innerHeight || 720
    posX = Math.min(1, Math.max(0, raw.posX / w))
    posY = Math.min(1, Math.max(0, raw.posY / h))
  } else if (raw._version === 2 || raw._version === '2') {
    // v2: direct ratio values
    posX = raw.posX ?? null
    posY = raw.posY ?? null
  }

  return {
    _version: 2,
    enabled: raw.enabled ?? true,
    displayMode: raw.displayMode ?? 'bilingual',
    fontSize: raw.fontSize ?? 'large',
    targetLanguage: raw.targetLanguage ?? 'English',
    posX,
    posY,
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
      _version: 2,
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
    // x, y are ratios (0.0~1.0) relative to parent container dimensions
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
