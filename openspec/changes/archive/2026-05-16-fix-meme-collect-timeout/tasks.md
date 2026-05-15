## 1. 后端 — bilibili_collector.py 超时保护

- [x] 1.1 `collect()` 整体包裹 `asyncio.wait_for(..., timeout=self._request_timeout)`，超时默认 60s（从 config 读取 `request_timeout`）
- [x] 1.2 `_fetch_comments()` 内部 API 调用包裹 `asyncio.wait_for(..., timeout=self._comment_timeout)`，默认 10s
- [x] 1.3 `__init__` 中增加 `self._request_timeout` 和 `self._comment_timeout` 配置读取，从 `config.get("request_timeout", 60)` 和 `config.get("comment_timeout", 10)` 取值
- [x] 1.4 `asyncio.TimeoutError` 被捕获后返回已采集的部分数据，记录 warning 日志

## 2. 前端 — MemeReview.vue 超时延长

- [x] 2.1 `triggerCollect()` 中超时从 `setTimeout(30000)` 改为 `setTimeout(120000)`

## 3. 验证

- [x] 3.1 `PYTHONPATH=src python -m pytest tests/services/meme/ -v` — 58 passed, 0 failed
- [x] 3.2 手动测试：点击采集热梗 → 确认 120s 内完成，不再显示"采集超时"（需运行中的后端+前端）
