const DANMAKU_PANEL_TOP_PX = 28

export function applyLiveReviewLayout(root: HTMLElement): void {
  root.style.removeProperty('--live-danmaku-panel-bottom')
  root.style.setProperty('--live-danmaku-panel-top', `${DANMAKU_PANEL_TOP_PX}px`)
}
