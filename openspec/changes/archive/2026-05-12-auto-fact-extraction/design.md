## Context

当前 PeriodicLearner 做模式提取但不做结构化事实提取。需要一次 LLM 调用，从对话日志中提取用户偏好、身份信息等。

## Decisions

- **触发时机**：定时触发（PeriodicLearner 调度），不在实时对话中运行
- **提取格式**：Pydantic schema（fact_type, confidence, source_turn_ids, content）
- **存储位置**：Wiki Markdown，`memory/wiki/auto_extracted/` 目录，与人工编写的知识隔离
- **去重策略**：按 fact_type + content MD5 去重；同类型新事实更新旧条目
