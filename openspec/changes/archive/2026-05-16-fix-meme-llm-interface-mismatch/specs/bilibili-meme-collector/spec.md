# bilibili-meme-collector Delta Specification

## MODIFIED Requirements

### Requirement: 梗候选识别

系统 SHALL 从采集到的视频标题和评论中识别潜在的梗候选。LLM 调用 SHALL 使用 `LLMInterface.chat_messages()` 方法。

#### Scenario: 梗候选识别
- **WHEN** 完成视频和评论采集
- **THEN** 系统 SHALL 使用 LLM 分析标题和高频评论内容
- **AND** LLM 调用 SHALL 通过 `self._llm.chat_messages(messages=[...], response_format={"type": "json_object"})` 发起
- **AND** 识别重复出现的特定短语、句式或概念
- **AND** 每个候选附带出现频次和来源视频链接

#### Scenario: LLM 识别失败降级到启发式识别
- **WHEN** `chat_messages()` 调用抛出异常
- **THEN** 系统 SHALL 降级到 `_heuristic_identify()` 方法
- **AND** 基于标题/评论中的高频词和重复短语识别梗候选
- **AND** 记录 warning 日志

#### Scenario: 无新梗可识别
- **WHEN** LLM 分析后未发现新兴梗模式
- **THEN** 系统 SHALL 返回空列表
- **AND** 记录 info 日志 "No new meme candidates found"
