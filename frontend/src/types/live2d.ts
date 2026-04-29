export interface Live2DConfig {
  modelUrl: string
  scale: number
  x: number
  y: number
}

export type ExpressionType = string

export interface Live2DAction {
  type: 'expression' | 'motion' | 'param' | 'sequence' | 'wait'
  name?: string
  group?: string
  index?: number
  value?: number
  duration?: number
}

export interface AudioWithExpression {
  audio_path: string
  text: string
  emotions: string[]
  volumes: number[]
}
