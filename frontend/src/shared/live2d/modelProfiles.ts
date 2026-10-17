import { MAO_PERFORMANCE_PROFILE } from './maoPerformanceProfile'
import type { Live2DModelProfile } from './modelProfile'

const MAO_MODEL_PROFILE: Live2DModelProfile = {
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

const WHALE_MAID_MODEL_PROFILE: Live2DModelProfile = {
  id: 'whale-maid-v1',
  automaticBreathing: false,
  fixedStepPhysics: true,
  modelUrl: '/live2d/whale-maid-v1/whale-maid-v1.model3.json',
  mouthParameters: ['ParamMouthOpenY'],
  framing: { scale: 0.9, x: 0.5, y: 0.46 },
  performance: {
    resolve(plan) {
      if (plan.base === 'calm') return []
      const offset = plan.base === 'annoyed' ? -0.25 : 0.35
      return ['ParamBrowLY', 'ParamBrowRY'].map((name) => ({ name, offset, min: -1, max: 1 }))
    },
  },
  semanticMotions: {
    planning: { group: 'Nod', index: 0 },
    observing: { group: 'Nod', index: 0 },
    committed: { group: 'Nod', index: 0 },
    acting: { group: 'Nod', index: 0 },
    checking: { group: 'Nod', index: 0 },
    recovering: { group: 'Shake', index: 0 },
    finished: { group: 'Nod', index: 0 },
  },
  expressions: {
    standard: { label: '标准表情', mouthRest: 0 },
    goofy: { label: '傻笑', mouthRest: 0.82 },
  },
  emotionExpressions: {
    neutral: 'standard',
    happy: 'goofy',
    joy: 'goofy',
    excited: 'goofy',
    amused: 'goofy',
    relieved: 'goofy',
    sad: 'standard',
    angry: 'standard',
    surprised: 'standard',
    thinking: 'standard',
    confident: 'standard',
    focused: 'standard',
    alert: 'standard',
    calm: 'standard',
  },
}

export const DEFAULT_LIVE2D_MODEL_PROFILE = WHALE_MAID_MODEL_PROFILE

export function resolveLive2DModelProfile(id: string | null): Live2DModelProfile {
  return id === MAO_MODEL_PROFILE.id ? MAO_MODEL_PROFILE : DEFAULT_LIVE2D_MODEL_PROFILE
}
