## Context

`anime-ui-redesign` 成功重构了布局、主题和动画系统，但遗漏了一个关键验证：pixi.js 和 pixi-live2d-display 在 Vite ESM 环境下是否真正能加载。

当前代码继承自老前端（vanilla JS + Electron），使用了两种 Vite 不支持的加载方式：
1. `index.html` 的 `<script src="/node_modules/...">`——Vite dev server 不保证 serve `node_modules` 文件，生产构建完全不包含 `node_modules`
2. `useLive2D.ts` 的 `require('pixi.js')`——浏览器没有 `require()`

这两个问题导致：Vue 组件初始化时 `ReferenceError: require is not defined` → 整个 app 崩溃 → 白屏/Live2D 黑屏/CSS 不渲染。

好消息：`pixi-live2d-display@0.4.0` 自带 ESM 构建产物 (`dist/cubism4.es.js`)，内部已用 `import from '@pixi/*'` 引用 pixi 子包。唯一硬性要求是 `window.PIXI.Ticker` 存在（供模型逐帧动画驱动）。

## Goals / Non-Goals

**Goals:**
- 让 Live2D 在 `pnpm dev` 和 `pnpm build` 下都能正常渲染
- 使用 Vite 原生的 ES module import，不引入额外插件或 shim
- 保持 pixi.js v6.5.10 和 pixi-live2d-display v0.4.0 版本不变
- 最小化改动范围（只改 `index.html` + `useLive2D.ts`）

**Non-Goals:**
- 不升级 pixi.js 到 v7/v8（v7+ 的 tree-shaking 模式与 v0.4.0 不兼容）
- 不替换 pixi-live2d-display 为其他 Live2D 库
- 不修改 vite.config.ts / electron.vite.config.ts
- 不改变 Vue 组件结构或 Live2D 交互逻辑

## Decisions

### D1: ES module import + window.PIXI 桥接

**选择**: `import * as PIXI from 'pixi.js'` + `import { Live2DModel } from 'pixi-live2d-display/cubism4'` + `window.PIXI = PIXI`

**依据**:
- `pixi-live2d-display@0.4.0` 的 `package.json` exports 字段已声明 ESM 入口 (`./cubism4` → `dist/cubism4.es.js`)
- `cubism4.es.js` 内部通过 `import from '@pixi/utils'` 等方式引用 pixi 子包，与 `import * as PIXI from 'pixi.js'` 无冲突
- `cubism4.es.js` 第 4854 行：`tickerRef = window.PIXI?.Ticker`——需显式设 `window.PIXI` 供 Ticker 驱动

**替代方案**: `<script>` 标签加载 `cubism4.min.js` + `window.PIXI` 引用
- 缺点：生产构建 `node_modules` 不在产物中，需额外插件复制文件到 `public/`

### D2: 保留 Cubism Core 的 `<script>` 加载

**选择**: `index.html` 保留 `<script src="/live2d/live2dcubismcore.min.js">`

**依据**: `live2dcubismcore.min.js` 是 Live2D 官方原生库（C++ 编译到 WASM/JS），不提供 npm 包，必须以全局 `<script>` 加载。文件位于 `public/live2d/`，Vite 自动作为静态资源 serve。

### D3: 不在 vite.config.ts 中做特殊配置

**选择**: 不添加 `optimizeDeps`、`resolve.alias`、`commonjs` 插件

**依据**: Vite 的预构建（esbuild）自动处理 CJS → ESM 转换，`pixi.js` 和 `@pixi/*` 子包均可自动转换。无需手动干预。

## Risks / Trade-offs

- **[兼容性] `pixi-live2d-display@0.4.0` 锁定 pixi.js v6** → 不能升级 pixi.js，但 v6 足够稳定，非阻塞
- **[Nuance] `window.PIXI = PIXI` 污染全局命名空间** → 仅在 `useLive2D.ts` 的 `init()` 中调一次，影响可控；pixi-live2d-display 官方 README 推荐此做法
- **[验证] pnpm 的符号链接可能影响 `@pixi/*` 子包解析** → Vite 的 `optimizeDeps` 在 dev 模式下自动处理，构建时 rollup 正确解析；如有问题，加 `optimizeDeps.include: ['pixi.js', 'pixi-live2d-display']` 即可
