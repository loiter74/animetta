## Context

Anima 的記憶系統 (`memory/`) 採用 Wiki 架構，底層為 SQLite FTS5 + Chroma 向量儲存，上層為 ShortTermMemory (FIFO deque) + WikiManager (raw/wiki 雙層目錄)。記憶以 sliding-window chunk 為單位（400 token/chunk, 80 token overlap），搜尋為混合向量 70% + BM25 30%。

LangGraph orchestration (`orchestration/graph/`) 中，記憶透過 llm_node 內的顯式 tool call (`memory_search` / `memory_get`) 觸發，無自動注入機制。output_node 負責在回應後儲存對話。

目前主要限制：
1. 記憶粒度是 chunk 級文字，無法表達原子事實
2. 更新事實時舊值直接被覆蓋，無版本追溯
3. Agent 必須主動呼叫 tool 才能查記憶，非自動注入
4. 無用戶畫像（profile）概念
5. 記憶之間無關聯關係

## Goals / Non-Goals

**Goals:**
- 引入 MemoryEntry 模型：原子事實級記憶單元，帶版本鏈（version + isLatest + parentMemoryId + rootMemoryId）
- 實現記憶關係：updates / extends / derives 三種關係類型的儲存與查詢
- 實現記憶中間件：LangGraph 節點中自動檢索相關記憶並注入 system prompt
- 實現 User Profile：static（長期事實）+ dynamic（當前上下文）雙軌
- 實現 Per-turn 快取：同輪 tool call 重複檢索去重
- 所有新功能向下相容：現有 chunk-based 記憶繼續可用

**Non-Goals:**
- 不替換現有 chunk 儲存機制，新版 MemoryEntry 為並行新增
- 不做記憶圖視覺化 UI（supermemory memory-graph 整合屬於後續階段）
- 不做 MCP 協議暴露（現有 MCP bridge 已足夠）
- 不做跨 session profile 持久化（static profile 由 wiki/entities 自動提煉）

## Decisions

### 1. 儲存層：SQLite 新增表，不改 Chroma

**決策**: 新增 `memory_entries` 和 `memory_relations` 兩張 SQLite 表，Chroma 保持不變。

**理由**: SQLite 對結構化關聯資料（版本鏈、關係圖）的查詢效率遠高於向量資料庫。Chroma 仍負責 chunk 級語意搜尋。兩者分工清晰：Chroma 找「相關內容」，SQLite memory_entries 找「精確事實」。

**替代方案**: 全部放 Chroma（需自建 filtering 邏輯，版本查詢複雜）→ 放棄。全部放 SQLite FTS5（無法做語意搜尋）→ 放棄。

### 2. 事實抽取：LLM 驅動的結構化解析

**決策**: 在 ingest 流程中加入 LLM 呼叫，從對話中提取結構化事實（subject-predicate-object + 關係判斷）。

**理由**: 原子事實提取需要語意理解，規則引擎無法處理。LLM 呼叫成本可控（每個對話輪次 1 次小型 LLM call），且現有 `WikiIngestor` 已經有 LLM 整合。

**替代方案**: 規則式提取（正則 + NER）→ 準確率不足，放棄。專門 fine-tune 模型 → 維護成本高，放棄。

### 3. 中間件注入：LangGraph ConfigStore 模式

**決策**: 中間件透過現有 ConfigStore 模式存取（session_id → MemorySystem），在 llm_node 中 `_retrieve_memory_context()` 步驟前增加自動檢索 + system prompt 注入。

**理由**: 現有架構已使用 ConfigStore 傳遞 service_context、socketio 等依賴。中間件作為 llm_node 內的步驟而非獨立節點，減少 Graph 複雜度。

**替代方案**: 獨立 graph node（增加 routing 複雜度）→ 放棄。外部 middleware 裝飾器（與 LangGraph 非同步模型不匹配）→ 放棄。

### 4. User Profile：WikiManager 擴展而非獨立服務

**決策**: static profile 從 wiki/entities + wiki/concepts 自動提煉，dynamic profile 從 ShortTermMemory 最近 N 輪建構。

**理由**: 不引入新儲存層，完全復用現有 Wiki 架構。static = 長期不變事實，dynamic = 當前 session 上下文，兩者生命週期不同。

### 5. Per-turn Cache：MemorySystem 內建而非獨立元件

**決策**: 在 MemorySystem 上加 `_turn_cache: Dict[str, str]`，key = `session_id:sha256(user_input)`，每次 `next_turn()` 訊號或新 user_input 時清空。

**理由**: 實現極簡單（~30 行），放在 MemorySystem 內部避免外部呼叫者需感知快取邏輯。

## Risks / Trade-offs

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| LLM 事實提取品質不穩定 | MemoryEntry 內容不準確 | 加入 confidence score 欄位；低置信度結果標記為 `is_static=0` 短期暫存 |
| 版本鏈查詢效能 | 大量記憶時查詢變慢 | 以 `is_latest=1` 索引加速；限制單一版本鏈深度（max 10 版後歸檔） |
| 中間件注入增加 LLM context 長度 | token 消耗上升 | 注入內容限 2000 tokens；支援 dynamic truncation |
| 與現有 chunk 記憶的重複檢索 | 搜尋結果重複 | retrieve_context() 中對 MemoryEntry 和 chunk 結果做 id dedup |
| 關係標註的 LLM 成本 | 每次 ingest 多一次 LLM call | 設定採樣率（預設 50% 輪次做關係分析）；支援 batch 處理 |
