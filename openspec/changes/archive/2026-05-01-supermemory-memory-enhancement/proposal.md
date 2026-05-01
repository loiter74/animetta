## Why

Anima 的記憶系統已有堅實的存儲基礎設施（SQLite + Chroma + Wiki），但相比 supermemoryai/supermemory 等現代記憶方案，在**事實粒度、版本追溯、自動注入和用戶畫像**方面存在明顯差距。當前記憶以 chunk 為單位存儲整段文本，Agent 必須顯式呼叫 `memory_search` tool 才能檢索，且無法追蹤事實的演變過程。這限制了 AI 角色對用戶的「理解深度」和個性化能力。

## What Changes

- **MemoryEntry 版本化記憶** — 引入原子事實級記憶單元，帶版本鏈、關係標註和過期機制，替換純 chunk 級存儲
- **記憶中間件（MemoryMiddleware）** — 在 LangGraph orchestration 層增加自動注入層，每次 LLM 調用前自動檢索相關記憶 + 用戶畫像並注入 system prompt
- **User Profile** — 提取 static（長期穩定事實）+ dynamic（當前上下文）用戶畫像，隨記憶檢索一併返回
- **記憶關係標註** — 支援 updates / extends / derives 三種關係，LLM ingest 時自動判斷新事實與已有事實的關係
- **Per-turn 緩存** — 同輪 Agent tool call 循環中記憶檢索只做一次，避免重複查詢

## Capabilities

### New Capabilities
- `memory-versioning`: 引入 MemoryEntry 模型 + 版本鏈 + isLatest/isForgotten/forgetAfter，支援事實級原子記憶及其生命週期管理
- `memory-middleware`: 在 LangGraph orchestration 中增加自動記憶注入中間件，before_llm_call 檢索 + 注入，after_llm_call 儲存
- `user-profile`: 從 WikiManager entities/concepts 提取 static profile + 從 ShortTermMemory 最近輪次構建 dynamic profile
- `memory-relations`: 新增 memory_relations 表，支援 updates / extends / derives 三種關係類型，搜索時做關聯擴展
- `turn-cache`: 在 MemorySystem 上加 TurnCache，按 session_id + user_input hash 去重，每輪 clear

### Modified Capabilities
- （無現有 spec 需要修改）

## Impact

- **記憶存儲層**: SQLite 新增 `memory_entries` 和 `memory_relations` 兩張表；Chroma 不變；現有 file-based chunking 保持向下相容
- **Orchestration 層**: LangGraph 節點流程需調整——llm_node 前增加記憶檢索步驟，output_node 後增加記憶存儲步驟
- **ServiceContext**: 可能需注入 MemorySystem 實例到 LangGraph config
- **依賴**: 無新外部依賴，全部基於現有 SQLite + Chroma + LangGraph 架構
