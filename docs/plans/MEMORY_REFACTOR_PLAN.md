# 记忆系统重构执行计划

> 目标：按照工程级架构重构记忆系统，解决幻觉问题，提升记忆质量和检索效率

## 执行进度

### 阶段 1: 基础重构 ✅ 已完成
- [x] 创建 `MemoryScorer` 评分器 → `src/anima/memory/scorer.py`
- [x] 创建 `ShortTermMemory` 类 → `src/anima/memory/stores/short_term.py`
- [x] 创建 `LongTermMemory` 类 → `src/anima/memory/stores/long_term.py`
- [x] 重构 `MemorySystem` 使用新组件 → `src/anima/memory/memory_system.py`

### 阶段 2: Prompt 优化 ✅ 已完成
- [x] 创建 `MemoryPromptBuilder` → `src/anima/memory/prompt_builder.py`
- [x] 更新 `orchestrator.py` 使用新 Prompt 构建

### 阶段 3: 内部优化 (待执行)
- [ ] 重构 `MemoryManager` 读写分离
- [ ] 优化 `load_session_context` 语义检索
- [ ] 添加写入缓冲机制

### 阶段 4: 测试验证 (待执行)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 手动测试脚本
