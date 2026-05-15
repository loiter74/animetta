## 1. admin_handlers.py — on_meme_collect 懒创建上下文

- [x] 1.1 在 `on_meme_collect` (line 872) 的 `ctx = self.session_manager.get_context(sid)` 之后，增加 `if not ctx: await self._get_or_create_orchestrator(sid); ctx = self.session_manager.get_context(sid)` 逻辑，确保首次连接后无聊天交互时也能创建上下文
- [x] 1.2 验证 `on_meme_collect` 返回的 `{"ok": False, "error": "Memory system not available"}` 仅在 `init_memory()` 真正失败时触发（config 禁用或初始化异常），而非「上下文未创建」时误触发

## 2. admin_handlers.py — on_meme_list 补全空值守卫

- [x] 2.1 在 `on_meme_list` (line 679-683) 的守卫条件中追加 `or not ctx.memory_system.meme_pool`，使其与 `on_meme_add` (line 583) 等其他 5 个 handler 完全一致
- [x] 2.2 添加后的守卫条件为: `if (not ctx or not ctx.memory_system or not hasattr(ctx.memory_system, "meme_pool") or not ctx.memory_system.meme_pool)`

## 3. service_context.py — init_memory 配置透传

- [x] 3.1 在 `init_memory()` (line 293-301) 构建 config dict 时，增加 `"meme_pool": mem_cfg.get('meme_pool', {})`、`"learner": mem_cfg.get('learner', {})`、`"scheduler": mem_cfg.get('scheduler', {})`、`"llm_client": self.llm_engine` 四个字段
- [x] 3.2 验证 `memory.yaml` 中 `meme_pool`/`learner`/`scheduler` sections 被正确读取并透传（可通过日志 `[MemorySystem] MemePool initialized` / `PeriodicLearner initialized` 确认）

## 4. 验证

- [x] 4.1 运行 `PYTHONPATH=src python -m pytest tests/ -v -k "meme or memory"` — 718 passed, 3 failed（全部预存问题，与本改动无关）
- [x] 4.2 mypy 未安装；改动极小（无新类型、无新 import），不引入类型风险
- [ ] 4.3 手动测试：重启后端 → 连接前端 → 不发送消息直接进入梗筛选页 → 点击「采集热梗」→ 确认不再出现 "Memory system not available"（此任务需运行中的后端+前端，无法在本 session 自动化）
