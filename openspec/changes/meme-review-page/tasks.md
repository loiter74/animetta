## 1. 数据模型扩展

- [x] 1.1 在 Meme 模型中增加 `review_status: str = "pending"` 字段（pending/good/bad）
- [x] 1.2 更新 Meme.to_dict() 和 MemeStore 持久化支持 review_status
- [x] 1.3 在 CognitiveAnalysis 中增加 `roast: str = ""` 字段用于存储吐槽

## 2. 后端 API

- [x] 2.1 在 `routes.py` 中新增 MemeReview 事件处理器（meme:list, meme:review, meme:dataset）
- [x] 2.2 实现 `meme:list` — 从 MemePool 获取 pending 状态的梗列表
- [x] 2.3 实现 `meme:review` — 记录筛选结果，更新评分和状态
- [x] 2.4 烂梗/好梗标记时集成 AI 反馈生成（LLM + 降级模板）
- [x] 2.5 实现 `meme:dataset` — 导出 good 状态梗的 JSON 数据集
- [x] 2.6 在 `register_routes()` 中注册 meme review 事件

## 3. AI 反馈（赞赏+吐槽）

- [x] 3.1 设计 LLM prompt：好梗赞赏（15-30字）和烂梗吐槽（20-40字），均符合 AI VTuber 人设
- [x] 3.2 实现反馈生成函数 `_generate_meme_feedback()` → 尝试LLM，降级模板
- [x] 3.3 实现降级模板：好梗 5 条 + 烂梗 5 条，随机选择
- [x] 3.4 反馈结果存入 Meme.cognitive_analysis.roast，Wiki 持久化

## 4. 前端页面

- [x] 4.1 创建 `frontend/src/views/MemeReview.vue` — 主页面组件
- [x] 4.2 创建 `frontend/src/components/meme/MemeCard.vue` — 梗卡片组件
- [x] 4.3 创建 `frontend/src/stores/memeReview.ts` — Pinia store（梗列表、当前索引、投票状态）
- [x] 4.4 在 `frontend/src/router/index.ts` 注册 `/meme-review` 路由
- [x] 4.5 实现卡片逐个展示逻辑（前进/后退、进度条）
- [x] 4.6 实现「好」/「烂」按钮交互（调用 API、动画过渡）
- [x] 4.7 实现 AI 反馈展示（气泡、2.5 秒自动消失）
- [x] 4.8 实现空状态提示和导出数据集按钮
- [x] 4.9 添加导航入口（TitleBar 侧边栏链接到筛选页）

## 5. 测试

- [x] 5.1 为 meme review 数据模型和 API 逻辑编写单元测试（10 tests）
- [x] 5.2 为反馈生成降级模板编写测试
- [x] 5.3 运行测试套件确认无回归（53 passed）
