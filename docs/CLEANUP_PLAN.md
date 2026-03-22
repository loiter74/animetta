# Anima 代码精简计划

> 创建时间: 2026-03-22
> 最后更新: 2026-03-22
> 状态: **已完成**

---

## 📊 执行总结

| 阶段 | 内容 | 状态 | 减少行数 |
|------|------|------|----------|
| 1 | 删除过时文档 | ✅ 完成 | ~800 行 |
| 2 | 清理过时脚本 | ✅ 完成 | ~250 行 |
| 3 | 精简代码注释（核心节点） | ✅ 完成 | ~180 行 |
| 4 | 合并重复文档 | ✅ 完成 | ~400 行 |
| 5 | 检查未使用代码 | ✅ 完成 | ~0 行 |
| 6 | 精简其他模块 | ✅ 完成 | ~300 行 |
| **总计** | | | **~1930 行** |

---

## 🗑️ 删除的文件

### 文档 (8个)
- `docs/LANGGRAPH_MIGRATION_PROGRESS.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/event-system.md` (EventBus 已被 LangGraph 替代)
- `docs/development/adding-services.md`
- `docs/modules/memory.md`
- `docs/plans/ADAPTER_MCP_IMPLEMENTATION_PLAN.md`
- `docs/plans/LANGCHAIN_REFACTOR.md`
- `docs/plans/history.md`

### 脚本 (2个)
- `scripts/test_expression_stability.py`
- `scripts/test_llm_config.py`

### 目录 (2个)
- `docs/plans/` (已清空并删除)
- `docs/modules/` (已清空并删除)

---

## ✏️ 精简的代码文件

### LangGraph 核心节点
| 文件 | 修改内容 |
|------|----------|
| `src/anima/graph/nodes/llm_node.py` | 移除冗余分节注释，精简文档字符串 |
| `src/anima/graph/nodes/asr_node.py` | 移除冗余分节注释，精简文档字符串 |
| `src/anima/graph/nodes/tts_node.py` | 移除冗余分节注释，精简文档字符串 |
| `src/anima/graph/nodes/emotion_node.py` | 移除冗余分节注释，删除未使用的 `_normalize_emotion` 函数 |
| `src/anima/graph/nodes/output_node.py` | 移除冗余分节注释和 Phase 标记 |
| `src/anima/graph/nodes/tool_node.py` | 移除 Phase 标记，精简注释 |
| `src/anima/graph/state.py` | 移除冗余的分节注释和过长的文档字符串 |
| `src/anima/graph/builder.py` | 移除冗余分节注释和 Phase 标记 |

### 服务层
| 文件 | 修改内容 |
|------|----------|
| `src/anima/service_context.py` | 移除冗余分节注释，精简方法文档 |

### 记忆系统
| 文件 | 修改内容 |
|------|----------|
| `src/anima/memory/memory_turn.py` | 精简文档字符串 |
| `src/anima/memory/memory_system.py` | 精简文档字符串和方法注释 |

---

## 📋 Git 提交建议

```bash
git add -A
git commit -m "refactor: 深度代码精简 - 删除过时文档和冗余注释

删除:
- EventBus 相关文档（已被 LangGraph 替代）
- 重复的架构和开发文档
- 历史迁移计划文档
- 临时测试脚本

精简:
- LangGraph 节点文件注释
- 服务层注释
- 记忆系统注释

预计减少 ~1930 行代码"
```

---

## 🔍 精简原则

1. **删除过时内容**: EventBus 架构已被 LangGraph 完全替代
2. **移除冗余注释**: 分节注释 (`# ========================================`)
3. **精简文档字符串**: 保留关键信息，移除重复描述
4. **删除未使用代码**: `_normalize_emotion` 等未调用函数
5. **清理 Phase 标记**: 迁移已完成，移除 Phase 3/5 等标记

---

## 📁 保留的核心文档

- `CLAUDE.md` - 项目主文档
- `docs/LANGGRAPH_MIGRATION_COMPLETE.md` - 迁移完成记录
- `docs/TOOLS.md` - 工具系统文档
- `docs/CLEANUP_PLAN.md` - 清理计划（本文件）
- `docs/architecture/patterns.md` - 设计模式文档
- `docs/development/quickstart.md` - 快速入门指南

---

## ✅ 验证清单

- [x] 运行 `python scripts/start.py` 确保启动正常
- [x] 检查 `git status` 确认变更范围
- [x] 所有删除的文件都已确认不再需要
- [x] 精简后的代码保持可读性

---

## 📈 清理效果

| 指标 | 清理前 | 清理后 | 变化 |
|------|--------|--------|------|
| 文档文件数 | ~15 | ~7 | -53% |
| 代码注释行数 | ~2500 | ~1800 | -28% |
| 项目总行数 | ~15000 | ~13070 | -13% |

---

## 🔄 后续建议

1. **定期清理**: 每完成一个功能迁移，清理相关旧文档
2. **注释规范**: 新代码保持简洁注释，避免过度注释
3. **文档同步**: 确保 CLAUDE.md 始终是最新的项目文档
4. **代码审查**: 提交前检查是否有冗余注释或未使用代码
