## Why

当前 benchmark 流程是手动的：启动服务 → 发消息 → 查面板 → 看报告。每次调代码后想确认性能变化都要重复这套操作，容易忘记、容易漏。

自动化后一个命令就能：启动 mock 服务 → 跑测试 prompt → 收集 OTel spans → 生成对比报告 → 检测 regression。开发者只需要 `python scripts/benchmark.py auto`，5 秒看到结果。

## What Changes

- 新增 `scripts/benchmark.py auto` 模式：一键完成 mock 服务启动 + 基准测试 + 报告生成 + 清理
- 新增 `scripts/benchmark.py diff` 模式：对比两次 benchmark 结果，显示性能变化
- 在 `scripts/benchmark-context/` 下保存历史和基线数据（JSON）
- 报告增加火焰图数据 + baseline diff + 自动告警（当 P95 上升 > 20%）
- 增强 benchmark.py 的 mock 模式，使其产生的 OTel spans 能被 StatsStore 正确记录

## Capabilities

### New Capabilities

- `auto-benchmark`: 一键自动化性能基准测试，含 mock 服务启动、测试执行、报告生成、基线对比

## Impact

- 新增文件：`docs/benchmarks/runs/` 目录存放历史运行数据
- 修改文件：`scripts/benchmark.py` 增加 auto/diff 模式
- 无破坏性变更，不影响现有功能
