import { Plugin } from 'vite'
import path from 'path'

/**
 * Vite plugin to handle pixi-live2d-display library loading.
 *
 * pixi-live2d-display expects PIXI to be available as a global,
 * and its cubism4 runtime needs Live2DCubismCore. This plugin
 * copies the necessary files and injects script tags.
 */
export function live2dPlugin(): Plugin {
  return {
    name: 'anima-live2d',
    configureIndexHtml(html) {
      // Inject Live2D Cubism Core as a script before the app entry
      return html.replace(
        '</head>',
        `  <script src="/live2d/live2dcubismcore.min.js"><\/script>
</head>`
      )
    }
  }
}
