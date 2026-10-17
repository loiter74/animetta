import { describe, expect, it, vi } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { DEFAULT_LIVE2D_MODEL_PROFILE, resolveLive2DModelProfile } from './modelProfiles'
import { createCubismParameterAdapter } from './performanceProfile'
import { createLive2DExpressionController } from './expressionController'

describe('Live2D emotion expressions', () => {
  const whale = resolveLive2DModelProfile('whale-maid-v1')

  it('applies the neutral expression initially and follows supported emotions without restarting it', () => {
    const apply = vi.fn()
    const onChange = vi.fn()
    const controller = createLive2DExpressionController(whale, apply, onChange)

    expect(controller.snapshot).toEqual({
      emotion: 'neutral',
      expression: 'standard',
      mode: 'auto',
    })
    controller.setEmotion(' HAPPY ')
    controller.setEmotion('happy')
    controller.setEmotion('amused')
    expect(controller.snapshot).toEqual({ emotion: 'amused', expression: 'goofy', mode: 'auto' })
    expect(apply.mock.calls).toEqual([['standard'], ['goofy']])
    expect(onChange).toHaveBeenCalledTimes(3)
    controller.setEmotion('sad')
    expect(apply).toHaveBeenLastCalledWith('standard')
  })

  it('remembers emotion during a manual override and resumes the latest emotion immediately', () => {
    const apply = vi.fn()
    const controller = createLive2DExpressionController(whale, apply)
    controller.setManual('standard')
    controller.setEmotion('excited')
    expect(controller.snapshot).toEqual({
      emotion: 'excited',
      expression: 'standard',
      mode: 'manual',
    })
    expect(apply).toHaveBeenCalledOnce()
    controller.setManual(null)
    expect(controller.snapshot).toEqual({ emotion: 'excited', expression: 'goofy', mode: 'auto' })
    expect(apply).toHaveBeenLastCalledWith('goofy')
  })

  it('ignores unknown manual expressions and safely returns unknown emotions to neutral', () => {
    const apply = vi.fn()
    const controller = createLive2DExpressionController(whale, apply)
    controller.setEmotion('joy')
    controller.setManual('missing-expression')
    expect(controller.snapshot.mode).toBe('auto')
    controller.setEmotion('missing-emotion')
    expect(controller.snapshot).toEqual({
      emotion: 'neutral',
      expression: 'standard',
      mode: 'auto',
    })
    controller.setEmotion('none')
    expect(apply.mock.calls).toEqual([['standard'], ['goofy'], ['standard']])
  })

  it('resets both the manual selection and remembered emotion', () => {
    const controller = createLive2DExpressionController(whale, vi.fn())
    controller.setEmotion('happy')
    controller.setManual('goofy')
    controller.reset()
    expect(controller.snapshot).toEqual({
      emotion: 'neutral',
      expression: 'standard',
      mode: 'auto',
    })
    expect(Object.isFrozen(controller.snapshot)).toBe(true)
  })

  it('stops state notifications and model writes after disposal', () => {
    const apply = vi.fn()
    const onChange = vi.fn()
    const controller = createLive2DExpressionController(whale, apply, onChange)
    const initial = controller.snapshot
    controller.dispose()
    controller.setEmotion('happy')
    controller.setManual('goofy')
    controller.setManual(null)
    controller.reset()
    expect(controller.snapshot).toBe(initial)
    expect(apply).toHaveBeenCalledOnce()
    expect(onChange).toHaveBeenCalledOnce()
  })

  it('does not invent expression assets for a model without expression declarations', () => {
    const apply = vi.fn()
    const controller = createLive2DExpressionController(DEFAULT_LIVE2D_MODEL_PROFILE, apply)
    controller.setEmotion('happy')
    controller.setManual('goofy')
    controller.setManual(null)
    expect(controller.snapshot).toEqual({ emotion: 'neutral', expression: '', mode: 'auto' })
    expect(apply).not.toHaveBeenCalled()
  })

  it('never applies an expression missing from the profile even when a mapping is invalid', () => {
    const apply = vi.fn()
    const controller = createLive2DExpressionController(
      {
        ...whale,
        emotionExpressions: { neutral: 'missing', happy: 'also-missing' },
      },
      apply,
    )
    controller.setEmotion('happy')
    controller.setManual(null)
    expect(controller.snapshot).toEqual({
      emotion: 'neutral',
      expression: 'standard',
      mode: 'auto',
    })
    expect(apply.mock.calls).toEqual([['standard']])
  })
})

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

  it('assigns local parts to idle or physics without head rotation or duplicate writers', () => {
    const profile = resolveLive2DModelProfile('whale-maid-v1')
    expect(profile.automaticBreathing).toBe(false)
    expect(profile.fixedStepPhysics).toBe(true)
    const modelPath = resolve('public', profile.modelUrl.slice(1))
    const model = JSON.parse(readFileSync(modelPath, 'utf8'))
    const idle = JSON.parse(
      readFileSync(resolve(dirname(modelPath), model.FileReferences.Motions.Idle[0].File), 'utf8'),
    )
    const parameters = idle.Curves.map((curve: { Id: string }) => curve.Id)
    expect(parameters).toEqual(
      expect.arrayContaining([
        'ParamBreath',
        'ParamEyeLOpen',
        'ParamEyeROpen',
        'ParamTailAngle',
        'ParamFinR',
        'ParamFinL',
        'ParamArmR',
        'ParamArmL',
      ]),
    )
    expect(parameters).toHaveLength(8)
    expect(new Set(parameters).size).toBe(parameters.length)
    expect(idle.Meta.CurveCount).toBe(parameters.length)
    expect(parameters.some((id: string) => /^Param(?:Body)?Angle[XYZ]$/.test(id))).toBe(false)
    const display = JSON.parse(
      readFileSync(resolve(dirname(modelPath), model.FileReferences.DisplayInfo), 'utf8'),
    )
    const declaredParameters = new Set(
      display.Parameters.map((parameter: { Id: string }) => parameter.Id),
    )
    expect(parameters.every((id: string) => declaredParameters.has(id))).toBe(true)
    const physics = JSON.parse(
      readFileSync(resolve(dirname(modelPath), model.FileReferences.Physics), 'utf8'),
    )
    const physicsOutputs: string[] = []
    for (const setting of physics.PhysicsSettings) {
      for (const output of setting.Output) {
        physicsOutputs.push(output.Destination.Id)
        expect(parameters).not.toContain(output.Destination.Id)
        expect(declaredParameters.has(output.Destination.Id)).toBe(true)
      }
    }
    expect(physicsOutputs).toEqual([
      'ParamHairBack',
      'ParamHairFringeR',
      'ParamHairFringeC',
      'ParamHairFringeL',
      'ParamSkirtSway',
    ])
    for (const setting of physics.PhysicsSettings) {
      for (const input of setting.Input) {
        expect(declaredParameters.has(input.Source.Id)).toBe(true)
        expect(physicsOutputs).not.toContain(input.Source.Id)
      }
    }
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
      for (const name of Object.values(profile.emotionExpressions ?? {})) {
        expect(profile.expressions?.[name], name).toBeDefined()
      }
    }
  })
})
