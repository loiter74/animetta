## Why

MemePool 采集了大量 B 站热梗候选，但 LLM 自动判断的梗质量不稳定——有些是真正的好梗，有些是噪音（重复标签、无意义短语）。需要一个人工筛选界面来标注好梗/烂梗，构建高质量梗数据集。同时，标注烂梗时让 AI 吐槽可以提升交互趣味性，也帮助理解"为什么这个梗不行"。

## What Changes

- **新增梗筛选前端页面**：Vue 3 组件，卡片式逐个展示梗内容、来源信息、标签，左滑/右滑或按钮选择「好」/「烂」
- **新增梗筛选后端 API**：`POST /api/memes/review` 记录筛选结果到 MemeStore（更新 `is_active` 和评分）
- **新增烂梗 AI 吐槽 + 好梗 AI 赞赏**：标记为烂梗时 AI 吐槽问题所在，标记为好梗时 AI 点评亮点，均符合 AI VTuber 人设
- **新增梗数据集导出**：`GET /api/memes/dataset` 导出已筛选的高质量梗 JSON

## Capabilities

### New Capabilities
- `meme-review-ui`: Vue 3 梗筛选卡片页面，支持逐个展示、好/坏投票、来源信息、AI 吐槽动画
- `meme-review-api`: 后端筛选 API（投票记录、评分更新、数据集导出）
- `meme-roast`: 烂梗 AI 吐槽生成（LLM 调用，个性化解构烂梗的问题）

### Modified Capabilities
<!-- No existing specs have requirement-level changes -->

## Impact

- **新增文件**: `frontend/src/views/MemeReview.vue`, `frontend/src/components/meme/MemeCard.vue`, `src/anima/orchestration/server/meme_routes.py`
- **修改文件**: `src/anima/memory/meme/store.py`（增加筛选评分方法）, `src/anima/memory/meme/models.py`（增加 `review_status` 字段）
- **新增 API**: `POST /api/memes/review`, `GET /api/memes/list`, `GET /api/memes/dataset`
- **LLM 成本**: 吐槽每次约 0.5K tokens，仅在标记烂梗时触发
