# 历史实现计划

已实现和计划中的功能记录。

---

## 已实现

### Adapter Layer ✅

**内容**: 通道适配器层，支持多种输入通道。

- `ChannelAdapter` 基类
- `DesktopLive2DChatter` 实现
- 基于 EventBus 的输入/输出抽象

**状态**: 已完成

### Memory System Refactor ✅

**内容**: 按工程级架构重构记忆系统。

- `MemoryScorer` 评分器
- `ShortTermMemory` / `LongTermMemory` 分层
- `MemoryPromptBuilder` 优化
- 混合检索（向量 70% + 关键词 30%）

**状态**: 已完成

---

## 计划中

### MCP Layer

**内容**: 工具集成与权限管理。

- `ToolManager` 工具管理器
- `BaseTool` 工具基类
- 权限系统（AUTO/SESSION/ASK/DENY）
- 内置工具（时间、记忆搜索、计算器）

**状态**: 规划中

**参考**: [ADAPTER_MCP_IMPLEMENTATION_PLAN.md](./ADAPTER_MCP_IMPLEMENTATION_PLAN.md)

---

## 废弃计划

### Live2D Display Enhancement

**原因**: 前端文档已删除，项目专注于后端。

**原计划内容**:
- 全身模型适配与缩放策略
- 多种背景模式（透明/纯色/图片/视频）
- 快捷键系统
- 窗口置顶与 OBS 集成

---

## 执行中

### Memory System 内部优化

**待执行**:
- [ ] 重构 `MemoryManager` 读写分离
- [ ] 优化 `load_session_context` 语义检索
- [ ] 添加写入缓冲机制
- [ ] 单元测试和集成测试
