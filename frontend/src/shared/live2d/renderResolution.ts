/** UHD is an output pixel size, independent of the embedded preview's CSS size. */
export const LIVE2D_UHD_SIZE = { width: 3840, height: 2160 } as const

export type Live2DRenderOutput = 'responsive' | '4k'

export function responsiveRenderResolution(
  width: number,
  height: number,
  devicePixelRatio: number,
): number {
  const density = Number.isFinite(devicePixelRatio) ? Math.max(1, devicePixelRatio) : 1
  const viewportWidth = Number.isFinite(width) ? Math.max(1, width) : 1
  const viewportHeight = Number.isFinite(height) ? Math.max(1, height) : 1
  // A responsive companion can use high DPI without allocating a second 8K surface
  // on a 4K display. The explicit UHD output always keeps its full pixel dimensions.
  return Math.min(
    density,
    2,
    LIVE2D_UHD_SIZE.width / viewportWidth,
    LIVE2D_UHD_SIZE.height / viewportHeight,
  )
}
