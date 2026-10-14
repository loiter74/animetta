export const SUBTITLE_CONFIG_STORAGE_KEY = 'animetta_subtitle_config'

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
