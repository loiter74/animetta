import { MAO_PERFORMANCE_PROFILE } from './maoPerformanceProfile'
import type { Live2DModelProfile } from './modelProfile'

export const DEFAULT_LIVE2D_MODEL_PROFILE: Live2DModelProfile = {
  id: 'mao',
  modelUrl: '/live2d/mao/Mao.model3.json',
  mouthParameters: ['ParamA'],
  performance: MAO_PERFORMANCE_PROFILE,
  framing: { scale: 1.8, x: 0.5, y: 0.8 },
  semanticMotions: {
    planning: { group: 'TapBody', index: 0 },
    observing: { group: 'TapBody', index: 1 },
    committed: { group: 'TapBody', index: 2 },
    acting: { group: 'TapBody', index: 3 },
    checking: { group: 'TapBody', index: 1 },
    recovering: { group: 'TapBody', index: 4 },
    finished: { group: 'TapBody', index: 5 },
  },
  idleVitality: [
    { name: 'ParamAngleX', factor: 2.3 },
    { name: 'ParamAngleY', factor: 2.3 },
    { name: 'ParamAngleZ', factor: 2.3 },
    { name: 'ParamBodyAngleX', factor: 2.6 },
    { name: 'ParamBodyAngleY', factor: 2.6 },
    { name: 'ParamBodyAngleZ', factor: 2.6 },
    { name: 'ParamBreath', factor: 2.4 },
  ],
}
