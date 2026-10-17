import type { Live2DModelProfile } from '@/shared/live2d/modelProfile'
import type { Live2DStage } from './live2d-stage'
import {
  AVATAR_PREVIEW_EMOTIONS,
  type AvatarPreviewCommand,
  type AvatarPreviewState,
} from '@/shared/live2d/previewContract'

/** Only an explicitly embedded Dashboard preview accepts local debug commands. */
export function bindAvatarPreview(
  document: Document,
  search: URLSearchParams,
  profile: Live2DModelProfile,
  stage: Pick<Live2DStage, 'setMouth' | 'setExpression' | 'setEmotion' | 'setZoom'>,
): (() => void) | undefined {
  const host = document.defaultView
  if (
    !host ||
    host.parent === host ||
    search.get('review') !== '1' ||
    search.get('media') !== 'muted' ||
    search.get('avatarDebug') !== '1'
  )
    return
  const model = document.getElementById('modelStatus')
  const socket = document.getElementById('socketStatus')
  const livestream = document.getElementById('livestreamStatus')
  let disposed = false
  let zoom = 1
  let frame: ReturnType<typeof setInterval> | undefined
  let timeout: ReturnType<typeof setTimeout> | undefined
  const publish = (): void => {
    if (disposed) return
    const state: AvatarPreviewState = {
      modelId: profile.id,
      loaded: model?.dataset.state === 'live',
      expression: model?.dataset.expression ?? '',
      emotion: model?.dataset.emotion ?? 'neutral',
      mode: model?.dataset.expressionMode === 'manual' ? 'manual' : 'auto',
      zoom,
      mouthDemo: frame !== undefined,
      socketState: socket?.dataset.state ?? 'connecting',
      livestreamState: livestream?.textContent ?? '',
    }
    host.parent.postMessage({ type: 'animetta:avatar-preview-state', state }, host.location.origin)
  }
  const stopDemo = (): void => {
    clearInterval(frame)
    clearTimeout(timeout)
    frame = undefined
    timeout = undefined
    stage.setMouth(0)
  }
  const onMessage = (event: MessageEvent): void => {
    if (disposed || event.origin !== host.location.origin || event.source !== host.parent) return
    const envelope = event.data
    if (!envelope || envelope.type !== 'animetta:avatar-preview-command') return
    const command = envelope.command as Partial<AvatarPreviewCommand> | undefined
    if (!command || typeof command !== 'object') return
    switch (command.type) {
      case 'expression':
        if (
          command.name !== null &&
          (typeof command.name !== 'string' ||
            !Object.hasOwn(profile.expressions ?? {}, command.name))
        )
          return
        stopDemo()
        stage.setExpression(command.name)
        break
      case 'emotion':
        if (
          typeof command.emotion !== 'string' ||
          !AVATAR_PREVIEW_EMOTIONS.some((emotion) => emotion === command.emotion)
        )
          return
        stopDemo()
        stage.setExpression(null)
        stage.setEmotion(command.emotion)
        break
      case 'zoom':
        if (typeof command.value !== 'number' || !Number.isFinite(command.value)) return
        zoom = Math.max(1, Math.min(3, command.value))
        stage.setZoom(zoom)
        break
      case 'mouth-demo':
        if (frame !== undefined) {
          stopDemo()
          break
        }
        {
          let phase = 0
          stage.setMouth(0.5, 'avatar-preview')
          frame = setInterval(() => {
            phase += 0.45
            stage.setMouth((1 + Math.sin(phase)) / 2, 'avatar-preview')
          }, 80)
          timeout = setTimeout(() => {
            stopDemo()
            publish()
          }, 20000)
        }
        break
      case 'reset':
        stopDemo()
        stage.setExpression(null)
        stage.setEmotion('neutral')
        zoom = 1
        stage.setZoom(zoom)
        break
      default:
        return
    }
    publish()
  }
  const observer = new MutationObserver(publish)
  for (const element of [model, socket, livestream]) {
    if (element) observer.observe(element, { attributes: true, childList: true, subtree: true })
  }
  host.addEventListener('message', onMessage)
  publish()
  return () => {
    disposed = true
    observer.disconnect()
    host.removeEventListener('message', onMessage)
    stopDemo()
  }
}
