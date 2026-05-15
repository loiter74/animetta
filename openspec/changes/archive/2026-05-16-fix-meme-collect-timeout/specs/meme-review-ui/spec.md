# meme-review-ui Delta Specification

## MODIFIED Requirements

### Requirement: 梗采集超时时间

前端 `MemeReview.vue` 的采集超时 SHALL 从 30 秒延长到 120 秒，匹配后端实际采集耗时。

#### Scenario: 正常采集不超时
- **WHEN** 用户点击「采集热梗」且后端在 120 秒内完成
- **THEN** 前端 SHALL 显示采集结果
- **AND** 不会显示"采集超时，请重试"

#### Scenario: 后端超时前端感知
- **WHEN** 用户点击「采集热梗」且后端超过 120 秒无响应
- **THEN** 前端 SHALL 显示"采集超时，请重试"
- **AND** `collecting` 状态重置为 false
