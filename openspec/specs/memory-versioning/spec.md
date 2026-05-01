# memory-versioning Specification

## Purpose
TBD - created by archiving change supermemory-memory-enhancement. Update Purpose after archive.
## Requirements
### Requirement: MemoryEntry 資料模型

系統 SHALL 引入 MemoryEntry 資料模型，表示一個原子事實級記憶單元。

MemoryEntry SHALL 包含以下欄位：
- `id`: UUID 主鍵
- `memory`: 事實文本（如"使用者喜歡 TypeScript"）
- `space_id`: 容器 ID（對應 containerTag / session scope）
- `version`: 版本號，預設 1，每次更新 +1
- `is_latest`: 是否為最新版本，預設 1
- `is_static`: 是否為長期記憶（vs 短期），預設 0
- `is_forgotten`: 是否軟刪除，預設 0
- `forget_after`: 自動過期時間（ISO datetime），nullable
- `parent_memory_id`: 被此版本取代的舊版 ID，nullable
- `root_memory_id`: 版本鏈根 ID，首版為自身 ID
- `confidence`: 置信度（0.0 ~ 1.0），預設 1.0
- `created_at`: 建立時間
- `updated_at`: 更新時間

#### Scenario: 建立新記憶

- **WHEN** ingest 流程從對話中提取一個新事實
- **THEN** 系統建立一個 MemoryEntry，`version=1`，`is_latest=1`，`root_memory_id=self.id`

#### Scenario: 更新現有事實（建立新版）

- **WHEN** ingest 發現與現有 MemoryEntry 衝突或互補的新事實
- **THEN** 系統將舊版 `is_latest` 設為 0，建立新版 `is_latest=1`，新版的 `parent_memory_id` 指向舊版 ID，`root_memory_id` 與舊版相同

#### Scenario: 查詢時只傳回最新版本

- **WHEN** `retrieve_context()` 或 `search()` 查詢記憶
- **THEN** 系統預設只傳回 `is_latest=1` 的 MemoryEntry

#### Scenario: 軟刪除記憶

- **WHEN** 系統判定某事實已過期或使用者要求遺忘
- **THEN** 系統將 `is_forgotten` 設為 1，該記憶在一般查詢中不再出現

#### Scenario: 自動過期

- **WHEN** 目前時間超過 `forget_after`
- **THEN** 系統自動將 `is_forgotten` 設為 1

### Requirement: MemoryEntry SQLite 儲存

系統 SHALL 在 SQLite 中新增 `memory_entries` 表，儲存 MemoryEntry。

`memory_entries` 表 SHALL 包含以下索引：
- `idx_latest`: `(space_id, is_latest)` — 快速查詢某 space 的最新記憶
- `idx_root`: `(root_memory_id)` — 快速查詢版本鏈
- `idx_forgotten`: `(is_forgotten, forget_after)` — 過期清理

系統 SHALL 提供 `MemoryEntryStore` 類別封裝所有 `memory_entries` 表操作，包括 CRUD、版本鏈查詢、過期清理。

#### Scenario: 新增 MemoryEntry

- **WHEN** 新事實建立
- **THEN** `MemoryEntryStore.create(entry)` 寫入 `memory_entries` 表

#### Scenario: 版本鏈查詢

- **WHEN** 需要查詢某個事實的完整版本演變歷史
- **THEN** `MemoryEntryStore.get_version_chain(root_memory_id)` 傳回按 version ASC 排序的所有版本

#### Scenario: 過期清理

- **WHEN** 系統啟動或定時任務執行
- **THEN** `MemoryEntryStore.expire_old()` 將所有 `forget_after < now()` 且 `is_forgotten=0` 的記錄設為 `is_forgotten=1`

