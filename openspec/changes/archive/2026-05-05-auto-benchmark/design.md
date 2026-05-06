## Context

现有的 `scripts/benchmark.py` 有 live 模式（连接已有服务），但需要手动启动服务器、手动总结。我们刚部署了 OTel tracing 框架，service 调用产生 span，需要一个自动化工具来：启动一个独立实例 → 发真实请求 → 收集 OTel spans → 生成对比报告 → 检测 regression。

## Goals / Non-Goals

**Goals:**
- `python scripts/benchmark.py auto` = 一键完成所有步骤
- 用真实 API 服务（读 .env + config.yaml），不用 mock
- 测试文本 + 语音混合场景
- 历史运行结果持久化，支持 baseline diff
- 自动检测 regression（P95 上升 > 阈值时告警）

**Non-Goals:**
- 不在 CI 中运行（只限本地开发）
- 不做 UI 截图测试
- 不生成火焰图图片（只输出结构化数据）

## Decisions

### D1: auto 模式执行流程

```
python scripts/benchmark.py auto

  1. 校验环境：检查 .env 是否有 API key
  2. 选择端口：默认 12395（避开用户可能已在跑的 12394）
  3. 在后台启动真实服务进程：
     uvicorn anima.socketio_server:get_asgi_app --port 12395
  
  4. 等待 /health 返回 200（最多 30s）
  
  5. 发送测试：
     ┌─ 文本 prompt（3-5 条）
     │   "你好，请介绍一下你自己"
     │   "今天天气怎么样？"
     │   "讲个笑话"
     │   "1+1等于几？"
     │   "再见"
     │
     └─ 语音输入（1-2 条）
         "你好"（预录的 test_audio.wav）
  
  6. 等待每个响应完成，记录端到端延迟
  
  7. 停止服务进程
  
  8. 读取 StatsStore（data/stats.db）：
     - traces 表 → 总耗时
     - spans 表 → 节点 + 子步骤耗时
     - OTel spans → service 方法级耗时
  
  9. 生成报告（Markdown）：
     - 本次结果：每条 prompt 耗时、P50/P95/P99 per node
     - OTel 子步骤明细（llm.api_call, tts.synthesize 等）
     - 与前一次 baseline 对比（delta）
     - 回归告警（P95 升 > 20% → ⚠️）
  
  10. 保存结果到 docs/benchmarks/runs/<timestamp>/
  
  11. 清理
```

### D2: 音频测试数据

使用一个预录的短音频文件 `scripts/benchmark_data/test_audio.wav`（~3秒，16kHz mono，说话内容"你好"）。通过 Socket.IO 的 `raw_audio_data` 事件发送，模拟真实语音输入。

生成方式：benchmark 首次运行时自动创建（生成简单正弦波测试音），或用户自行录制。

### D3: Baseline 对比

```
基准线：docs/benchmarks/runs/latest.json（自动更新）
历史：   docs/benchmarks/runs/<YYYYMMDD_HHMMSS>.json

对比逻辑：
  新运行结束后，自动读取 latest.json 计算 delta
  每个指标标记：↑ faster / ↓ slower / - same
  阈值：P95 上升超过 20% → 告警标志 ⚠️
```

### D4: StatsStore 读取

新增 `BenchmarkData` 类封装 StatsStore 读取：
- `load_traces(since)` → 过滤时间窗口后的所有 trace
- `load_spans(since)` → 按 node_name 聚合的统计
- `load_otel_spans(since)` → service 级子步骤明细（llm.api_call 等）

## Architecture

```
scripts/benchmark.py auto
  │
  ├── 1. EnvCheck()
  │       └── 检查 .env API key + config.yaml
  │
  ├── 2. RealServer()
  │       ├── choose_port() → 12395+
  │       ├── start()       → subprocess.Popen(uvicorn)
  │       ├── wait_ready()  → poll /health (30s timeout)
  │       └── stop()        → terminate() + wait
  │
  ├── 3. BenchmarkClient()
  │       ├── connect()     → socketio
  │       ├── send_text()   → text_input event（N 条）
  │       ├── send_audio()  → raw_audio_data + mic_audio_end
  │       └── close()
  │
  ├── 4. StatsCollector()
  │       ├── read_traces()
  │       ├── read_spans()
  │       └── read_otel()
  │
  ├── 5. ReportGenerator()
  │       ├── generate()
  │       ├── diff_baseline()
  │       └── check_regression()
  │
  └── 6. PersistRun()
        └── save + update latest
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 真实 LLM 调用慢（3-10s/条） | 正常现象，报告里显示真实延迟 |
| API key 没配 | 启动前校验 .env，没有则报错退出 |
| 子进程启动失败 | wait_ready 超时 30s 后报错退出 |
| 端口被占用 | 从 12395 开始 auto-increment |
| 子进程退出后没清理干净 | atexit 注册清理 + signal handler |
| 音频 ASR 识别不准 | 音频内容尽量清晰简短 |
