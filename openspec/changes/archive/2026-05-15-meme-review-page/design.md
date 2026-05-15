## Context

Anima 已有 MemePool 系统和 B站采集管道。采集到的梗候选存储在 `wiki/memes/` 下，但目前没有人工审核界面。前端是 Vue 3 + Electron + UnoCSS + Pinia，使用 Vue Router（memory history），现有 Chat 和 Dashboard 两个页面。

## Goals / Non-Goals

**Goals:**
- 在 Anima 前端中新增梗筛选页面，路由 `/meme-review`
- 逐个展示梗（文本、来源、标签、认知分析），按钮选择好/坏
- 标记烂梗时触发 AI 吐槽，展示在卡片下方
- 筛选结果持久化到 MemeStore（更新评分和状态）
- 支持导出已筛选的高质量梗 JSON 数据集

**Non-Goals:**
- 不做滑动手势（v1 用按钮即可，v2 再加手势）
- 不做批量操作（v1 单条筛选，v2 加批量）
- 不做梗的编辑/修改功能
- 不在独立 Electron 窗口运行（集成在现有前端）

## Decisions

### Decision 1: 前端作为新路由页面集成

- **选择**：在现有 Anima 前端中新增 `/meme-review` 路由，使用 Pinia store 管理状态，UnoCSS 样式
- **备选**：独立 SPA 页面（增加构建复杂度，需要额外通信）
- **理由**：复用现有 Socket.IO 连接、Pinia store、UnoCSS 样式体系，零额外依赖

### Decision 2: 后端使用 REST API + Socket.IO 混合

- **选择**：`GET /api/memes/list`（获取待筛选梗列表）、`POST /api/memes/review`（提交筛选结果）、`GET /api/memes/dataset`（导出数据集）使用 REST；AI 吐槽使用 Socket.IO `meme_roast` 事件推送
- **备选**：纯 Socket.IO（路由管理复杂）、纯 REST（吐槽需要轮询）
- **理由**：REST 适合 CRUD 操作，Socket.IO 适合实时推送吐槽结果

### Decision 3: AI 反馈根据用户选择双向生成

- **选择**：标记好梗时 LLM 生成赞赏（15-30 字，指出梗的优点），标记烂梗时生成吐槽（20-40 字，指出问题）。非流式返回。
- **备选**：只吐槽不赞赏（单向，交互感弱）；流式（复杂度高，短文本不需要）
- **理由**：双向反馈让筛选过程更有互动感，用户能即时看到 AI 对自己判断的回应

### Decision 4: 数据模型增加 review_status 字段

- **选择**：在 Meme 模型增加 `review_status: str = "pending"`（pending/good/bad），通过 MemeStore 的 Wiki 持久化
- **理由**：最小改动，不需要新数据库表；标记为 bad 的梗自动 `is_active = False`

## Data Flow

```
Frontend                          Backend
────────                          ───────
MemeReview.vue
  │ onMounted
  ├─ GET /api/memes/list ────────→ meme_routes.list_memes()
  │                                 └→ MemeStore.get_active()
  │    ← [{id, text, tags, source_url, ...}]
  │
  │ 用户点击「好」
  ├─ POST /api/memes/review ─────→ meme_routes.review_meme()
  │  {id, status: "good"}           └→ Meme.update_score(+0.2)
  │                                     MemeStore.update()
  │
  │ 用户点击「烂」
  ├─ POST /api/memes/review ─────→ meme_routes.review_meme()
  │  {id, status: "bad"}            └→ Meme.is_active = False
  │                                     LLM.generate_roast(text)
  │    ← {roast: "这梗...", ...}    ←─ Socket.IO emit("meme_roast")
  │
  │ 用户点击「导出」
  ├─ GET /api/memes/dataset ─────→ 返回 JSON [{text, tags, ...}]
```

## Risks / Trade-offs

- **[Risk] 梗列表为空时页面空白** → 展示空状态提示 "暂无待筛选梗，去采集一些吧"
- **[Risk] LLM 吐槽调用失败** → 降级为预设吐槽模板（"这梗太冷了，连 AI 都懒得吐槽"）
- **[Risk] 前端路由在 Electron 中可能刷新丢失状态** → 使用 Pinia store + localStorage 持久化当前进度
