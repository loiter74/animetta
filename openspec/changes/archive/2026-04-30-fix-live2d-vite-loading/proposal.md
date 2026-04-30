## Why

`anime-ui-redesign` 完成后，前端 Live2D 渲染完全不工作——窗口白屏、Live2D 黑屏、样式异常。根因是 pixi.js 和 pixi-live2d-display 的加载方式在 Vue 3 + Vite 的 ESM 环境下失效：`index.html` 用 `<script>` 从 `/node_modules/` 加载（生产构建 404），`useLive2D.ts` 用 `require()` 引用（浏览器无 require）。这两个问题导致 Vue 组件初始化崩溃，连锁引发白屏、布局失效、CSS 不渲染。

## What Changes

- 从 `index.html` 移除 pixi.js 和 pixi-live2d-display 的 `<script>` 标签（保留 Cubism Core）
- `useLive2D.ts` 中 `require('pixi.js')` → `import * as PIXI from 'pixi.js'`
- `useLive2D.ts` 中 `require('pixi-live2d-display')` → `import { Live2DModel } from 'pixi-live2d-display/cubism4'`
- `useLive2D.ts` 新增 `window.PIXI = PIXI`（pixi-live2d-display 内部依赖 `window.PIXI.Ticker`）
- 无需修改 vite.config.ts 或 electron.vite.config.ts

## Capabilities

### New Capabilities
<!-- No new capabilities - this is a bugfix -->

### Modified Capabilities
- `live2d-vue-component`: 澄清 pixi.js 和 pixi-live2d-display 的加载方式必须使用 ES module import（而非 `<script>` 全局加载或 `require()`），并明确 `window.PIXI = PIXI` 是 pixi-live2d-display 内部 Tick 驱动的必要前提

## Impact

- **前端文件变更**: `index.html`（删 2 行）、`useLive2D.ts`（改 3 行）
- **无后端影响**: 纯前端修复
- **无新依赖**: pixi.js v6.5.10 和 pixi-live2d-display v0.4.0 已在 package.json 中，v0.4.0 内置 ESM 版本 (`cubism4.es.js`)
- **Vite 配置无需变更**: Vite 原生支持 `import * from 'pixi.js'` 和 `import from 'pixi-live2d-display/cubism4'`
