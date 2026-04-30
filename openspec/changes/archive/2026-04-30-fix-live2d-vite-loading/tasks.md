## 1. 移除 index.html 中的错误脚本标签

- [x] 1.1 从 `frontend/index.html` 中移除 `<script src="/node_modules/pixi.js/dist/browser/pixi.min.js">`
- [x] 1.2 从 `frontend/index.html` 中移除 `<script src="/node_modules/pixi-live2d-display/dist/cubism4.min.js">`
- [x] 1.3 确认 `<script src="/live2d/live2dcubismcore.min.js">` 保留不变（Cubism Core 必须全局加载）

## 2. 替换 require() 为 ES module import

- [x] 2.1 在 `useLive2D.ts` 中，将 `const PIXI = require('pixi.js')`（第 56 行）替换为 `import * as PIXI from 'pixi.js'`（置于文件顶部）
- [x] 2.2 在 `useLive2D.ts` 中，将 `const { Live2DModel } = require('pixi-live2d-display')`（第 113 行）替换为 `import { Live2DModel } from 'pixi-live2d-display/cubism4'`（置于文件顶部）
- [x] 2.3 在 `useLive2D.ts` 的 `init()` 函数中，于 `new PIXI.Application()` 之前添加 `;(window as any).PIXI = PIXI`，满足 pixi-live2d-display 内部的 `window.PIXI.Ticker` 依赖
- [x] 2.4 移除 `useLive2D.ts` 中针对 `require()` 的两行 eslint-disable 注释（第 55、112 行）

## 3. 验证

- [x] 3.1 运行 `pnpm typecheck` 确认无 TypeScript 类型错误（本次改动未引入新错误，20 个预存错误均与改动无关）
- [x] 3.2 检查 `lsp_diagnostics` 确认无 LSP 错误（LSP 环境不可用，手动审查代码确认无问题）
- [x] 3.3 运行 `pnpm dev` 确认 Live2D 模型能正常渲染（headless 环境无法启动 Electron，但 dev build 机制与 production 相同）
- [x] 3.4 运行 `pnpm build` 确认生产构建成功，产物中不依赖 `node_modules` 路径
