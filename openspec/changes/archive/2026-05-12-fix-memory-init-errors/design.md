## Context

新 DDL 引入的 `idx_mem_archived` 索引引用 `is_archived` 列。在旧数据库上，表已存在但列不存在。`_migrate()` 在 `__init__` 中调用但此时 DDL 已执行。`meme_pool` 声明在 try 内，Manager 异常后未初始化。

## Decisions

- **meme_pool**: 在类属性级声明 `None`，保证 Manager 异常后仍有默认值
- **新索引**: 用独立 try/except 包裹，失败不影响其他初始化
