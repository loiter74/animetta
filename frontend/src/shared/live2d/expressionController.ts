import type { Live2DModelProfile } from './modelProfile'

export interface Live2DExpressionState {
  readonly emotion: string
  readonly expression: string
  readonly mode: 'auto' | 'manual'
}

/** Selects declared model expressions independently of the rendering surface. */
export function createLive2DExpressionController(
  profile: Live2DModelProfile,
  apply: (name: string) => void,
  onChange?: (state: Live2DExpressionState) => void,
) {
  const available = new Set(Object.keys(profile.expressions ?? {}))
  const mappings = profile.emotionExpressions ?? {}
  const neutral = available.has(mappings.neutral)
    ? mappings.neutral
    : available.has('standard')
      ? 'standard'
      : (available.values().next().value ?? '')
  let disposed = false
  let state: Live2DExpressionState = Object.freeze({
    emotion: 'neutral',
    expression: neutral,
    mode: 'auto',
  })
  if (neutral) apply(neutral)
  onChange?.(state)

  function expressionFor(emotion: string): string {
    return available.has(mappings[emotion]) ? mappings[emotion] : neutral
  }

  function update(next: Live2DExpressionState): void {
    if (
      disposed ||
      (next.emotion === state.emotion &&
        next.expression === state.expression &&
        next.mode === state.mode)
    )
      return
    const previousExpression = state.expression
    state = Object.freeze(next)
    if (state.expression && state.expression !== previousExpression) apply(state.expression)
    onChange?.(state)
  }

  return {
    get snapshot(): Live2DExpressionState {
      return state
    },
    setEmotion(emotion: string): void {
      const candidate = emotion.trim().toLowerCase()
      const supported = Object.hasOwn(mappings, candidate) && available.has(mappings[candidate])
      const nextEmotion = supported ? candidate : 'neutral'
      update({
        emotion: nextEmotion,
        expression: state.mode === 'manual' ? state.expression : expressionFor(nextEmotion),
        mode: state.mode,
      })
    },
    setManual(name: string | null): void {
      if (name !== null && !available.has(name)) return
      update({
        emotion: state.emotion,
        expression: name ?? expressionFor(state.emotion),
        mode: name === null ? 'auto' : 'manual',
      })
    },
    reset(): void {
      update({ emotion: 'neutral', expression: neutral, mode: 'auto' })
    },
    dispose(): void {
      disposed = true
    },
  }
}
