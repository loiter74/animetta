## ADDED Requirements

### Requirement: 記憶關係資料模型

系統 SHALL 支援三種記憶關係類型：

- `updates`: 新記憶取代了舊記憶（版本鏈的語意化表達）
- `extends`: 新記憶擴展/補充了舊記憶（非取代，是補充）
- `derives`: 記憶衍生自某個來源（如對話、文件）

系統 SHALL 在 SQLite 中新增 `memory_relations` 表：

```sql
CREATE TABLE memory_relations (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation  TEXT NOT NULL CHECK(relation IN ('updates', 'extends', 'derives')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (source_id, target_id, relation)
);
```

`memory_relations` 表 SHALL 包含索引 `idx_target` 以加速反向查詢（查詢被誰關聯）。

#### Scenario: 標記關係

- **WHEN** ingest 流程判斷新 MemoryEntry 與已有記憶存在關係
- **THEN** 系統在 `memory_relations` 表中插入一條對應關係記錄

#### Scenario: 反向查詢關聯記憶

- **WHEN** `retrieve_context()` 找到一個相關 MemoryEntry
- **THEN** 系統可選地查詢 `memory_relations` 找到關聯記憶，做關聯擴展

### Requirement: LLM 驅動的關係判斷

系統在 ingest 流程中 SHALL 可選地呼叫 LLM，判斷新事實與已有事實的關係。

判斷結果 SHALL 為以下之一：`updates` / `extends` / `derives` / `none`。

#### Scenario: 自動判斷關係

- **WHEN** ingest 新 MemoryEntry 且系統啟用關係分析
- **THEN** 系統查詢最相似的現有 MemoryEntry
- **THEN** 系統呼叫 LLM 判斷兩者關係（帶具體 prompt + 記憶上下文）
- **THEN** 若關係非 `none`，在 `memory_relations` 插入對應記錄

#### Scenario: 關係分析可配置開關

- **WHEN** 配置關閉關係分析
- **THEN** 系統跳過 LLM 關係判斷步驟，僅儲存 MemoryEntry
