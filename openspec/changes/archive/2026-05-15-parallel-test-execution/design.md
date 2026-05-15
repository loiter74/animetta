## Context

Anima 测试套件现有 2605 个测试，全部串行执行。开发机上 20 核 CPU 利用率极低。`test_bilibili_danmaku.py` 涉及 Bilibili API 库导入时会触发事件循环清理，导致测试挂起超时。部分测试（`test_storage_fallback.py`）共享 SQLiteStore 文件状态，并行写入会冲突。

## Goals / Non-Goals

**Goals:**
- 安装 `pytest-xdist`，`-n auto` 默认并行执行
- 将超时测试（`test_bilibili_danmaku.py`）标记 `slow` 并默认排除
- 共享状态测试（`test_storage_fallback.py`）加 `xdist_group` 隔离
- CI workflow 拆分：快速并行测试 + 可选慢速测试
- 修复 9 个预置失败测试（tracing exporter + 平台路径检测）

**Non-Goals:**
- 不重写测试逻辑
- 不改动应用代码
- 不追求 100% 通过率（保留 eval 基准测试的波动空间）

## Decisions

### 1. pytest-xdist with -n auto (非固定 worker 数)

**选择**：`addopts = "-n auto"` 自动使用所有 CPU 核心（20 核），而非写死 `-n 4` 或 `-n 8`。

**理由**：本地开发和 CI 环境核心数不同，`auto` 自动适配。20 核机器上约分配 20 个 worker，每个 worker 跑 ~130 个测试。

### 2. Slow test isolation: @pytest.mark.slow + --deselect

**选择**：用 `@pytest.mark.slow` 标记 `test_bilibili_danmaku.py`，在 `pyproject.toml` 的 `addopts` 中加 `-m "not slow"` 默认排除。CI 中通过独立 job 手动触发慢速测试。

**理由**：`test_bilibili_danmaku.py` 的 Bilibili API 导入会启动事件循环，在多 worker 下不可预测地挂起。排除后其余测试可稳定并行运行。

### 3. Shared state: @pytest.mark.xdist_group("serial")

**选择**：用 `pytest.mark.xdist_group("serial")` 标记共享 SQLite 状态的测试文件，确保同一组内的测试不会并行执行。

**替代方案**：`--forked`（需要 `pytest-forked`）——更重，每个 worker 独立进程开销大。

**理由**：`xdist_group` 是 xdist 内置功能，零额外依赖，精确控制序列化范围。

### 4. CI pipeline: 双 job 策略

**选择**：GitHub Actions 用两个 job：（1）快速并行测试（~10-15s），（2）慢速测试（手动触发或定时）。

**理由**：并行后 2421 个有效测试预计 8-12 秒完成，PR CI 可以秒级反馈。慢速测试独立运行不影响 PR 合并速度。

### 5. 预置失败修复

**选择**：
- `tracing/test_exporter.py` × 3：修正 OTel 测试中 gRPC exporter 在 Collector 不可用时的行为断言
- `utils/test_auto_config.py` × 6：在 Windows 上跳过 Linux 路径测试，用 `pytest.mark.skipif` 做平台判断

**理由**：这些失败是平台相关而非逻辑错误。修复后 CI 可以零失败通过。

## Risks / Trade-offs

- **[风险] xdist + asyncio 兼容性** → 缓解：pytest-asyncio >= 0.21 支持 `--asyncio-mode=auto` 与 xdist。当前版本 1.3.0（pytest 9.0.3）经过社区验证兼容。
- **[风险] Bilibili 测试完全跳过** → 缓解：CI 中保留独立的 `cron` job 专门跑慢速测试，不会永久忽视。
- **[风险] xdist_group 可能遗漏共享状态文件** → 缓解：首次启用后观察 CI 随机失败，逐步补充标记。

## Migration Plan

1. `pip install pytest-xdist` 安装依赖
2. 修改 `pyproject.toml`：addopts 加 `-n auto` + markers 加 slow
3. 标记 `test_bilibili_danmaku.py` 为 `@pytest.mark.slow`
4. 标记 `test_storage_fallback.py` 为 `@pytest.mark.xdist_group("serial")`
5. 修复 9 个预置失败测试
6. 验证：`PYTHONPATH=src python -m pytest tests/ -n auto --tb=short -q`
7. 更新 CI workflow
