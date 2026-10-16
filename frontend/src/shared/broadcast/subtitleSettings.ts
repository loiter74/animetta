export const SUBTITLE_CONFIG_STORAGE_KEY = 'animetta_subtitle_config'

export function writeSubtitleEnabled(enabled: boolean): void {
  let config: Record<string, unknown> = {}
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(SUBTITLE_CONFIG_STORAGE_KEY) ?? 'null')
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed))
      config = parsed as Record<string, unknown>
  } catch {
    /* Replace invalid settings with the chosen visibility. */
  }
  localStorage.setItem(SUBTITLE_CONFIG_STORAGE_KEY, JSON.stringify({ ...config, enabled }))
}

export function readSubtitleEnabled(raw?: string | null): boolean {
  try {
    const config = JSON.parse(
      raw === undefined
        ? (localStorage.getItem(SUBTITLE_CONFIG_STORAGE_KEY) ?? 'null')
        : (raw ?? 'null'),
    )
    return typeof config?.enabled === 'boolean' ? config.enabled : true
  } catch {
    return true
  }
}
