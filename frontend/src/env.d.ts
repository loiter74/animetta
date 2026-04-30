/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

declare module 'pixi-live2d-display' {
  export const Live2DModel: any
}

// Global functions exposed by components for cross-component communication
interface Window {
  __setAppBg: (url: string) => void
  __live2dResetView: () => void
}
