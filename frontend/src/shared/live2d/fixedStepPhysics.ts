interface PhysicsParameters {
  getParameterCount(): number
  getParameterIndex(id: string): number
  getParameterValueByIndex(index: number): number
  setParameterValueByIndex(index: number, value: number): void
}

interface Physics<Model> {
  evaluate(model: Model, deltaSeconds: number): void
  _physicsRig: {
    inputs: readonly { source: { id: string } }[]
    outputs: readonly { destination: { id: string } }[]
  }
}

const STEP_SECONDS = 1 / 60
const MAX_FRAME_SECONDS = 0.25
const TIME_EPSILON = 1e-10

/** Replace the installed SDK's single physics stage; parameter ownership comes from its rig. */
export function createFixedStepPhysics<Model extends PhysicsParameters>(
  physics: Physics<Model>,
  model: Model,
): Physics<Model>['evaluate'] {
  const indices = (ids: readonly string[]): number[] =>
    [...new Set(ids)].map((id) => {
      const index = model.getParameterIndex(id)
      if (index < 0 || index >= model.getParameterCount()) {
        throw new Error(`Physics parameter is missing: ${id}`)
      }
      return index
    })
  const inputIndices = indices(physics._physicsRig.inputs.map(({ source }) => source.id))
  const outputIndices = indices(
    physics._physicsRig.outputs.map(({ destination }) => destination.id),
  )
  if (inputIndices.some((index) => outputIndices.includes(index))) {
    throw new Error('Fixed-step physics requires separate input and output parameters')
  }
  const evaluateSdk = physics.evaluate.bind(physics)
  const read = (indices: readonly number[]): number[] =>
    indices.map((index) => model.getParameterValueByIndex(index))
  const write = (indices: readonly number[], values: readonly number[]): void => {
    indices.forEach((index, at) => model.setParameterValueByIndex(index, values[at]))
  }
  let previousInputs: number[] | undefined
  let previousOutputs = read(outputIndices)
  let currentOutputs = previousOutputs
  let accumulator = 0

  return (_model, deltaSeconds) => {
    if (!Number.isFinite(deltaSeconds) || deltaSeconds < 0) return
    const inputs = read(inputIndices)
    if (!previousInputs) {
      previousInputs = inputs
      return
    }
    // Resume suspended tabs without replaying an unbounded number of hidden frames.
    const elapsed = Math.min(deltaSeconds, MAX_FRAME_SECONDS)
    let tickWithinFrame = STEP_SECONDS - accumulator
    accumulator += elapsed
    while (accumulator + TIME_EPSILON >= STEP_SECONDS) {
      // A new action belongs to this render boundary, never to an earlier physics tick.
      write(inputIndices, tickWithinFrame + TIME_EPSILON >= elapsed ? inputs : previousInputs)
      previousOutputs = currentOutputs
      // Rendering interpolates outputs; that display value must not feed back into simulation.
      write(outputIndices, currentOutputs)
      evaluateSdk(model, STEP_SECONDS)
      currentOutputs = read(outputIndices)
      accumulator = Math.max(0, accumulator - STEP_SECONDS)
      tickWithinFrame += STEP_SECONDS
    }
    write(inputIndices, inputs)
    const fraction = accumulator / STEP_SECONDS
    write(
      outputIndices,
      previousOutputs.map((value, at) => value + (currentOutputs[at] - value) * fraction),
    )
    previousInputs = inputs
  }
}
