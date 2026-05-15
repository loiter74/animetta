# meme-review-api Delta Specification

## MODIFIED Requirements

### Requirement: MemePool 持久化与查询一致性

`MemePool.add_from_candidate()` 写入 memes 后，`store.list_active()` SHALL 能立即查询到新写入的 memes，且 `review_status` SHALL 为 `"pending"`。

#### Scenario: 采集后立即可查询
- **WHEN** `analyze_and_ingest()` 成功调用 `add_from_candidate()` 入库 3 条 memes
- **THEN** `store.list_active()` SHALL 返回至少包含这 3 条的 active memes
- **AND** 每条 `review_status` SHALL 为 `"pending"`

#### Scenario: 日志可诊断
- **WHEN** `add_from_candidate()` 成功保存 meme
- **THEN** 系统 SHALL 输出 INFO 日志包含 meme.id + review_status
- **WHEN** `get_active()` 查询 wiki
- **THEN** 系统 SHALL 输出 DEBUG 日志包含总页数 + active 数量
