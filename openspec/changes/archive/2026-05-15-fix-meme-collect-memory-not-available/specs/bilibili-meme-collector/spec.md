# bilibili-meme-collector Delta Specification

## MODIFIED Requirements

### Requirement: 手动触发采集的可用性

用户通过前端「采集热梗」按钮手动触发 `meme:collect` 事件时，系统 SHALL 在任何页面状态下（包括连接后未发送过聊天消息）都能正常响应并执行采集。

#### Scenario: 首连后立即触发手动采集
- **WHEN** 客户端刚建立 WebSocket 连接（未发送任何聊天消息）
- **AND** 用户在前端点击「采集热梗」按钮
- **AND** 前端发送 `meme:collect` 事件
- **THEN** 系统 SHALL 自动初始化 session 上下文和 MemorySystem
- **AND** 调用 `PeriodicLearner.collect_bilibili_memes()` 执行 B 站热梗采集
- **AND** 返回采集结果 `{"ok": True, "count": ..., "ingested": ...}`

#### Scenario: 定时采集不受影响
- **WHEN** PeriodicLearner 通过 Scheduler 触发定期采集
- **THEN** 采集流程与修改前完全一致，不受懒创建逻辑影响
