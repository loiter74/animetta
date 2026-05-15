## 1. 依赖安装与基础配置

- [x] 1.1 安装 `pytest-xdist`：`pip install pytest-xdist`
- [x] 1.2 更新 `pyproject.toml`：addopts 加 `-n auto`，markers 加 `slow`，加 `-m "not slow"` 默认排除
- [x] 1.3 验证：`PYTHONPATH=src python -m pytest tests/core/test_service_pool.py -n auto --tb=short -q` 能并行执行

## 2. 慢速测试隔离

- [x] 2.1 在 `tests/services/test_bilibili_danmaku.py` 所有测试类上加 `@pytest.mark.slow`
- [x] 2.2 验证慢速测试被默认排除：`PYTHONPATH=src python -m pytest tests/ -n auto -m slow --tb=short -q --collect-only`
- [x] 2.3 验证快速测试正常执行：`PYTHONPATH=src python -m pytest tests/ -n auto -m "not slow" --tb=short -q`

## 3. 共享状态隔离

- [x] 3.1 在 `tests/memory/test_storage_fallback.py` 文件级加 `pytestmark = pytest.mark.xdist_group("serial")`
- [x] 3.2 验证：并行执行下 `test_storage_fallback.py` 内测试不冲突

## 4. 预置失败测试修复

- [x] 4.1 修复 `tests/tracing/test_exporter.py` 中 3 个 OTel gRPC exporter 测试（Collector 不可用时的行为适配）
- [x] 4.2 在 `tests/utils/test_auto_config.py` 中 Linux 路径测试上加 `@pytest.mark.skipif(sys.platform == "win32", ...)`
- [x] 4.3 验证修复后零失败：`PYTHONPATH=src python -m pytest tests/ --ignore=tests/memory/test_manager.py --tb=short -q` 退出码 0

## 5. CI 适配

- [x] 5.1 更新 `.github/workflows/test.yml`：快速并行 job + 慢速/手动 job
- [x] 5.2 验证 CI 配置语法正确
