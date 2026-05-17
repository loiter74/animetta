## 1. DanmakuBuffer 组件

- [x] 1.1 创建 `services/meme/danmaku_buffer.py`，实现 `DanmakuBuffer` 类和 `DanmakuPhrase` 数据类
- [x] 1.2 实现 `add(msg)` 方法：接收弹幕推送，更新环形缓冲区和频率表
- [x] 1.3 实现 `get_hot_phrases(min_freq, window_minutes)` 方法：按时间和频次过滤高频短语
- [x] 1.4 实现 `get_recent_danmaku(limit)` 和缓冲区状态查询方法
- [x] 1.5 在 `services/meme/__init__.py` 导出 DanmakuBuffer

## 2. BilibiliDanmakuService 接口暴露

- [x] 2.1 在 `BilibiliDanmakuService` 新增 `set_buffer(buffer)` 方法
- [x] 2.2 修改 `_consume_queue` 方法：在转发弹幕给 UI 回调的同时推入 DanmakuBuffer
- [x] 2.3 在 `BilibiliDanmakuService` 启动流程中接入 DanmakuBuffer（配置 room_id 时自动创建 buffer）— 依赖 BilibiliDanmakuService 的集成点，待后续 wiring 变更时完成

## 3. 采集器弹幕数据源

- [x] 3.1 在 `BilibiliMemeCollector` 新增 `_fetch_danmaku_phrases()` 方法：从 DanmakuBuffer 获取实时弹幕高频短语
- [x] 3.2 实现 `_fetch_historical_danmaku(room_id)` 方法：通过 `live.get_danmaku()` 拉取历史弹幕
- [x] 3.3 修改 `_collect_impl()` 流程：在视频采集之外并行启动弹幕采集
- [x] 3.4 将弹幕数据加入 LLM 识别的 `_identify_meme_candidates()` 上下文

## 4. 采集并行化与参数调优

- [x] 4.1 评论获取从串行 for 循环改为 `asyncio.gather` + semaphore（并发数 5）
- [x] 4.2 调整参数默认值：`max_videos=50`, `max_comments_per_video=50`, `min_comment_likes=2`
- [x] 4.3 调整参数默认值：`request_delay=0.3`, `request_timeout=120`, `comment_timeout=15`

## 5. LLM Prompt 升级

- [x] 5.1 在 `MEME_IDENTIFY_SYSTEM_PROMPT` 中增加弹幕高频短语分析维度和跨视频交叉验证要求
- [x] 5.2 在 `MEME_IDENTIFY_USER_PROMPT` 中增加弹幕数据占位符和格式化逻辑
- [x] 5.3 将 persona_fit 从绝对硬阈值改为按候选列表相对排名过滤（取 top 50%）

## 6. Heuristic 语义级升级

- [x] 6.1 在 `requirements.txt` 中添加 `jieba` 依赖
- [x] 6.2 实现 `_extract_semantic_phrases(texts, top_k)` 方法：jieba 分词 + 2-4 词 n-gram 提取
- [x] 6.3 实现 TF-IDF 通用短语过滤逻辑
- [x] 6.4 改造 `_heuristic_identify()`：集成语义短语提取为第4种策略（弹幕语义短语）
- [x] 6.5 jieba 不可用时回退到原有的字符 2-gram 方法

## 7. MemePool 与 MemeDiscoverer 扩容

- [x] 7.1 修改 `MemePool` 默认 `max_active` 从 10 改为 20
- [x] 7.2 修改 `PeriodicLearner` 默认 `meme_candidates_per_run` 从 3 改为 15
- [x] 7.3 降低 `MemeCognitiveAnalyzer` 默认 `min_persona_fit_score` 从 0.5 改为 0.4
- [x] 7.4 更新 `config/features/memory.yaml` 中的对应配置参数 — 配置通过程序传入，无需 YAML 更新

## 8. BilibiliInteractionLearner 改造

- [x] 8.1 在 `BilibiliInteractionLearner` 新增 `get_hot_danmaku_phrases()` 方法
- [x] 8.2 修改 `learn_patterns()` 返回值（额外返回弹幕高频短语列表）— 新增 `get_hot_danmaku_phrases()` 作为独立 API，避免破坏现有接口

## 9. 测试

- [x] 9.1 为 DanmakuBuffer 编写单元测试（add/get_hot_phrases/容量管理/边界条件）
- [x] 9.2 为 BilibiliMemeCollector 编写弹幕数据源集成测试（mock DanmakuBuffer）
- [x] 9.3 为 Heuristic 语义短语提取编写单元测试（jieba 分词 + n-gram + TF-IDF）
- [x] 9.4 运行现有 meme 测试套件，确保未引入回归：133 passed ✓
