# bilibili-meme-collector Delta Specification

## ADDED Requirements

### Requirement: API 调用超时保护

系统 SHALL 对 B 站 API 调用施加超时保护，避免网络异常时线程永久阻塞。

#### Scenario: 整体采集超时
- **WHEN** `collect()` 整体执行超过 60 秒
- **THEN** 系统 SHALL 抛出 `asyncio.TimeoutError`
- **AND** 捕获后返回已成功采集的部分数据

#### Scenario: 单次评论 API 超时
- **WHEN** 单个视频的评论 API 调用超过 10 秒
- **THEN** 系统 SHALL 跳过该视频的评论
- **AND** 继续处理下一个视频

#### Scenario: 超时参数可配置
- **WHEN** `memory.yaml` 中配置了 `bilibili_meme.collector.request_timeout` 或 `comment_timeout`
- **THEN** 系统 SHALL 使用配置值覆盖默认超时（60s / 10s）
- **AND** 未配置时使用默认值

### Requirement: 部分降级返回

系统 SHALL 在超时或部分失败时返回已成功采集的数据，而非全部丢弃。

#### Scenario: 视频采集成功但评论超时
- **WHEN** 视频列表获取成功但评论抓取超时
- **THEN** 系统 SHALL 仍将已获取的视频（含空评论集）传递给 LLM 识别阶段
- **AND** LLM 可基于视频标题/标签识别梗候选
