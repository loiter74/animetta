## Why

当前测试套件 2605 个测试全串行执行，单次运行约 2-10 分钟以上。20 核 CPU 只用了 1 核。安装 pytest-xdist 实现 `-n auto` 并行执行，可将 CI 测试时间缩短至 ~10-15 秒，大幅提升开发反馈速度。

## What Changes

- 安装 `pytest-xdist` 依赖
- 在 `pyproject.toml` 中配置 `addopts = "-n auto"` 默认开启并行
- 将 `test_bilibili_danmaku.py` 标记为 `@pytest.mark.slow` 并加入默认排除列表（该测试有挂起问题）
- 隔离共享状态文件 `test_storage_fallback.py`（SQLiteStore 写入冲突），标记 `@pytest.mark.xdist_group`
- 修复 9 个预置失败测试（tracing + utils 平台相关）以确保持续集成零失败
- 更新 CI workflow 配置，区分快速并行测试和慢速测试

## Capabilities

### New Capabilities
- `parallel-test-runner`: pytest-xdist 集成配置，支持 `-n auto` 多核并行执行
- `slow-test-isolation`: 将易超时/挂起的测试标记为 `slow`，默认排除但可手动触发
- `test-gating`: 并行测试 + 慢速测试分离的 CI pipeline 配置

### Modified Capabilities
<!-- No existing specs are being modified — this is a new infrastructure change -->

## Impact

- **新增依赖**: `pytest-xdist`（dev dependency）
- **修改文件**: `pyproject.toml`（addopts + markers）、`.github/workflows/test.yml`（并行配置）
- **修改测试文件**: 标记 slow/xdist_group 的测试
- **不影响**: 现有测试逻辑、应用代码、API 接口
