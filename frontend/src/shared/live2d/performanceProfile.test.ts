import { describe, expect, it, vi } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { DEFAULT_LIVE2D_MODEL_PROFILE, resolveLive2DModelProfile } from './modelProfiles'
import { createCubismParameterAdapter } from './performanceProfile'

describe('Live2D performance model adapter', () => {
  it('reads and writes known Cubism parameters with model bounds', () => {
    const set = vi.fn()
    const coreModel = {
      getParameterIndex: (name: string) => (name === 'ParamBrowLY' ? 2 : -1),
      getParameterValueByIndex: () => 0.25,
      setParameterValueByIndex: set,
      getParameterMinimumValue: () => -0.5,
      getParameterMaximumValue: () => 0.5,
    }
    const adapter = createCubismParameterAdapter(coreModel)

    expect(adapter.read('ParamBrowLY')).toBe(0.25)
    expect(adapter.read('missing')).toBe(0)
    adapter.write('ParamBrowLY', 2)
    adapter.write('missing', 1)

    expect(set).toHaveBeenCalledOnce()
    expect(set).toHaveBeenCalledWith(2, 0.5)
  })
})

describe('versioned Live2D model assets', () => {
  it('falls back to the default model for undeclared IDs', () => {
    expect(resolveLive2DModelProfile(null)).toBe(DEFAULT_LIVE2D_MODEL_PROFILE)
    expect(resolveLive2DModelProfile('unknown')).toBe(DEFAULT_LIVE2D_MODEL_PROFILE)
    expect(resolveLive2DModelProfile('/arbitrary.model3.json')).toBe(DEFAULT_LIVE2D_MODEL_PROFILE)
  })

  it('keeps whale maid idle breathing without independent head rotation', () => {
    const profile = resolveLive2DModelProfile('whale-maid-v1')
    expect(profile.automaticBreathing).toBe(false)
    const modelPath = resolve('public', profile.modelUrl.slice(1))
    const model = JSON.parse(readFileSync(modelPath, 'utf8'))
    const idle = JSON.parse(
      readFileSync(resolve(dirname(modelPath), model.FileReferences.Motions.Idle[0].File), 'utf8'),
    )
    const parameters = idle.Curves.map((curve: { Id: string }) => curve.Id)
    expect(parameters).toEqual(
      expect.arrayContaining(['ParamBreath', 'ParamEyeLOpen', 'ParamEyeROpen', 'ParamTailAngle']),
    )
    expect(parameters.some((id: string) => /^Param(?:Body)?Angle[XYZ]$/.test(id))).toBe(false)
  })

  it('maps each model only to its own packaged motion groups and mouth parameters', () => {
    for (const profile of [
      DEFAULT_LIVE2D_MODEL_PROFILE,
      resolveLive2DModelProfile('whale-maid-v1'),
    ]) {
      const path = resolve('public', profile.modelUrl.slice(1))
      const model = JSON.parse(readFileSync(path, 'utf8'))
      const refs = model.FileReferences
      const files = [refs.Moc, ...refs.Textures, refs.Physics, refs.DisplayInfo]
      for (const file of files) expect(existsSync(resolve(dirname(path), file)), file).toBe(true)
      const display = JSON.parse(
        readFileSync(resolve(dirname(path), model.FileReferences.DisplayInfo), 'utf8'),
      )
      const parameters = new Set(
        display.Parameters.map((parameter: { Id: string }) => parameter.Id),
      )
      expect(profile.mouthParameters.every((parameter) => parameters.has(parameter))).toBe(true)
      for (const motion of Object.values(profile.semanticMotions)) {
        expect(model.FileReferences.Motions[motion.group]?.[motion.index ?? 0]).toBeDefined()
      }
      for (const [name, { mouthRest }] of Object.entries(profile.expressions ?? {})) {
        const expression = refs.Expressions.find((entry: { Name: string }) => entry.Name === name)
        expect(expression, name).toBeDefined()
        expect(existsSync(resolve(dirname(path), expression.File)), name).toBe(true)
        expect(Number.isFinite(mouthRest), name).toBe(true)
        expect(mouthRest, name).toBeGreaterThanOrEqual(0)
        expect(mouthRest, name).toBeLessThanOrEqual(1)
      }
    }
  })
})
