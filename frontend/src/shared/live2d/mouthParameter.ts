const MOUTH_PARAMETERS = ['ParamMouthOpenY', 'ParamMouthOpen', 'PARAM_MOUTH_OPEN', 'ParamA']

export interface MouthParameterLookup {
  getParameterCount(): number
  getParameterIndex(name: string): number
}

export function resolveMouthParameterIndex(
  model: MouthParameterLookup,
  candidates: readonly string[] = MOUTH_PARAMETERS,
): number {
  const parameterCount = model.getParameterCount()
  for (const name of candidates) {
    const index = model.getParameterIndex(name)
    if (index >= 0 && index < parameterCount) return index
  }
  return -1
}
