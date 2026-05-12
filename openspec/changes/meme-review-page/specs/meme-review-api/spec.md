# meme-review-api Specification

## Purpose
后端梗筛选 REST API，提供梗列表获取、筛选结果记录、数据集导出功能。

## ADDED Requirements

### Requirement: 待筛选梗列表 API
系统 SHALL 提供 `GET /api/memes/list` 接口返回待筛选梗列表。

#### Scenario: 获取待筛选梗
- **WHEN** 前端请求 `GET /api/memes/list?source_platform=bilibili&limit=50`
- **THEN** 系统 SHALL 从 MemeStore 获取 `review_status == "pending"` 的活跃梗
- **AND** 返回 JSON 数组，每项包含 id、text、tags、context_hint、cognitive_analysis、source_platform、source_url

#### Scenario: 无待筛选梗
- **WHEN** MemeStore 中没有 pending 状态的梗
- **THEN** 系统 SHALL 返回空数组 `[]`
- **AND** HTTP 状态码 200

### Requirement: 梗筛选提交 API
系统 SHALL 提供 `POST /api/memes/review` 接口记录筛选结果。

#### Scenario: 提交「好」评价
- **WHEN** 前端发送 `{"meme_id": "xxx", "status": "good"}`
- **THEN** 系统 SHALL 更新该梗的 `review_status` 为 `"good"`
- **AND** 提升 `base_score` +0.2（确保好梗留在活跃池）
- **AND** 返回 `{"ok": true}`

#### Scenario: 提交「烂」评价
- **WHEN** 前端发送 `{"meme_id": "xxx", "status": "bad"}`
- **THEN** 系统 SHALL 更新 `review_status` 为 `"bad"`
- **AND** 设置 `is_active = False`（从活跃池移除）
- **AND** 调用 LLM 生成吐槽
- **AND** 返回 `{"ok": true, "roast": "吐槽文本"}`

#### Scenario: 无效请求
- **WHEN** 请求缺少必填字段或 meme_id 不存在
- **THEN** 系统 SHALL 返回 HTTP 400
- **AND** 返回 `{"error": "描述"}`

### Requirement: 数据集导出 API
系统 SHALL 提供 `GET /api/memes/dataset` 接口导出高质量梗数据集。

#### Scenario: 导出数据集
- **WHEN** 前端请求 `GET /api/memes/dataset?source_platform=bilibili`
- **THEN** 系统 SHALL 返回所有 `review_status == "good"` 的梗
- **AND** 每项包含完整信息（text、tags、cognitive_analysis、source_url）
- **AND** HTTP Content-Disposition 头设置为 `attachment; filename=meme_dataset.json`

### Requirement: Meme 数据模型扩展
系统 SHALL 在 Meme 模型中增加 `review_status` 字段。

#### Scenario: review_status 默认值
- **WHEN** 新梗被创建
- **THEN** `review_status` SHALL 默认为 `"pending"`

#### Scenario: review_status 持久化
- **WHEN** MemeStore 保存或更新 Meme
- **THEN** `review_status` SHALL 通过 Wiki metadata 持久化
