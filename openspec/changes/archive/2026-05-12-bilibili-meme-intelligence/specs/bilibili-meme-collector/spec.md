# bilibili-meme-collector Specification

## Purpose
从 B 站定期采集热门视频和评论，识别新兴梗并提取关键上下文，为 MemePool 提供外部数据源。

## ADDED Requirements

### Requirement: 热门视频采集
系统 SHALL 定期从 B 站热门分区采集视频信息，包括标题、标签（tags）、播放量、视频描述。

#### Scenario: 每日定时采集
- **WHEN** PeriodicLearner 触发 `collect_bilibili_memes()` 调度任务
- **THEN** 系统使用 `bilibili-api-python` 的搜索接口获取热门视频列表
- **AND** 每个视频提取标题（title）、标签（tags）、播放量（view_count）、简介（description）

#### Scenario: API 请求限流保护
- **WHEN** 发起 B 站 API 请求
- **THEN** 系统 SHALL 在请求间插入至少 1 秒延迟
- **AND** 单次采集不超过 50 个视频

#### Scenario: API 调用失败降级
- **WHEN** B 站 API 返回错误或超时
- **THEN** 系统 SHALL 记录 warning 日志
- **AND** 返回已成功采集的部分数据（而非整体失败）

### Requirement: 高赞评论抓取
系统 SHALL 对采集到的热门视频抓取其高赞评论（按点赞数排序前 20 条）。

#### Scenario: 评论抓取
- **WHEN** 获取到热门视频列表
- **THEN** 对每个视频抓取前 20 条高赞评论
- **AND** 每条评论包含：内容、点赞数、回复数、发布时间

#### Scenario: 评论为空的视频
- **WHEN** 视频无评论或评论 API 返回空
- **THEN** 系统 SHALL 跳过该视频的评论分析
- **AND** 仍保留视频标题和标签用于梗识别

### Requirement: 梗候选识别
系统 SHALL 从采集到的视频标题和评论中识别潜在的梗候选。

#### Scenario: 梗候选识别
- **WHEN** 完成视频和评论采集
- **THEN** 系统 SHALL 使用 LLM 分析标题和高频评论内容
- **AND** 识别重复出现的特定短语、句式或概念
- **AND** 每个候选附带出现频次和来源视频链接

#### Scenario: 无新梗可识别
- **WHEN** LLM 分析后未发现新兴梗模式
- **THEN** 系统 SHALL 返回空列表
- **AND** 记录 info 日志 "No new meme candidates found"
