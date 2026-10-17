// @unocss-include
import type { Live2DModelProfile } from '@/shared/live2d/modelProfile'
import type { Live2DStage } from './live2d-stage'

export function mountAvatarPreview(
  document: Document,
  search: URLSearchParams,
  profile: Live2DModelProfile,
  stage: Pick<Live2DStage, 'setMouth' | 'setExpression'>,
): (() => void) | undefined {
  const expressions = Object.entries(profile.expressions ?? {})
  const shell = document.querySelector('.live-shell')
  if (search.get('review') !== '1' || !expressions.length || !shell) return

  const life = new AbortController()
  const panel = document.createElement('aside')
  panel.setAttribute('aria-label', '立绘预览')
  panel.className =
    'absolute bottom-22 left-4 z-30 flex flex-wrap gap-2 rounded-xl bg-c-panel/95 p-3 text-c-text'
  panel.dataset.avatar = profile.id
  const demo = document.createElement('button')
  demo.type = 'button'
  demo.className = 'btn-secondary min-h-11'
  demo.textContent = '口型演示'
  demo.setAttribute('aria-pressed', 'false')
  let frame: ReturnType<typeof setInterval> | undefined
  let timeout: ReturnType<typeof setTimeout> | undefined
  const stopDemo = (): void => {
    clearInterval(frame)
    clearTimeout(timeout)
    frame = undefined
    timeout = undefined
    stage.setMouth(0)
    demo.setAttribute('aria-pressed', 'false')
  }
  const buttons = new Map<string, HTMLButtonElement>()
  const select = (name: string): void => {
    stopDemo()
    stage.setExpression(name)
    panel.dataset.expression = name
    for (const [id, button] of buttons) button.setAttribute('aria-pressed', String(id === name))
  }
  for (const [name, expression] of expressions) {
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'btn-secondary min-h-11'
    button.textContent = expression.label
    button.addEventListener('click', () => select(name), { signal: life.signal })
    buttons.set(name, button)
    panel.append(button)
  }
  demo.addEventListener(
    'click',
    () => {
      if (frame !== undefined) {
        stopDemo()
        return
      }
      let phase = 0
      stage.setMouth(0.5, 'avatar-preview')
      frame = setInterval(() => {
        phase += 0.45
        stage.setMouth((1 + Math.sin(phase)) / 2, 'avatar-preview')
      }, 80)
      timeout = setTimeout(stopDemo, 20000)
      demo.setAttribute('aria-pressed', 'true')
    },
    { signal: life.signal },
  )
  panel.append(demo)
  shell.append(panel)
  const requested = search.get('expression') ?? ''
  select(buttons.has(requested) ? requested : expressions[0][0])
  return () => {
    life.abort()
    stopDemo()
    panel.remove()
  }
}
