## ADDED Requirements

### Requirement: 記憶中間件（MemoryMiddleware）

系統 SHALL 提供 `MemoryMiddleware` 元件，在 LLM 呼叫前後自動處理記憶。

`MemoryMiddleware` SHALL 包含兩個核心方法：

- `before_llm_call(context, user_input)`:
  1. 從 `context` 取得 `MemorySystem` 實例
  2. 調用 `retrieve_context(query=user_input, ...)` 檢索相關記憶
  3. 調用 `get_profile()` 取得用戶畫像
  4. 將記憶 + 畫像組裝為 `## 相關記憶\n{memories}\n## 用戶畫像\n{profile}` 注入到 system prompt

- `after_llm_call(context, user_input, response)`:
  1. 從 `context` 取得 `MemorySystem` 實例
  2. 構建 `MemoryTurn(user_input=user_input, agent_response=response)`
  3. 調用 `store_turn(turn)` 儲存到記憶系統

#### Scenario: LLM 呼叫前自動注入記憶

- **WHEN** 使用者輸入對話文字，系統準備呼叫 LLM
- **THEN** `before_llm_call` 自動檢索相關記憶並注入 system prompt
- **THEN** Agent 無需顯式呼叫 `memory_search` tool 即可感知相關記憶

#### Scenario: LLM 回應後自動儲存

- **WHEN** LLM 回覆完成
- **THEN** `after_llm_call` 自動將這輪對話儲存到記憶系統

### Requirement: LangGraph 整合

中間件 SHALL 在 LangGraph 的 llm_node 中整合，透過以下方式：

- 在 llm_node 的 `_retrieve_memory_context()` 步驟前，自動執行 `before_llm_call`
- 在 llm_node 取得 LLM response 後、傳遞給下個節點前，自動執行 `after_llm_call`
- 中間件 SHALL 透過 ConfigStore 取得 MemorySystem 實例（遵循現有 ConfigStore 模式）

#### Scenario: 中間件不阻斷主流程

- **WHEN** `before_llm_call` 或 `after_llm_call` 拋出例外
- **THEN** 系統 catch 例外、記錄 warning、不阻斷 LLM 呼叫主流程
