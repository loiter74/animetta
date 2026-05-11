## Context

AnimaBot 当前架构：
- **Python 侧**: `autonomous.py` 的规则驱动循环 → `bridge.py` → JSON/stdin 协议
- **Node.js 侧**: `index.js` 接收 JSON 指令，调度 mineflayer 动作
- **问题**: 固定规则，无 LLM 规划，无状态机，动作阻塞时无法中断

目标架构（双脑模式）：
```
LLM目标? ──YES──► Planner(LLM) ──► StateMachine ──► Mineflayer
   │                                      ▲
   NO                                     │
   └──► RuleLoop(旧autonomous) ──────────►│ (后备)
```

## Goals / Non-Goals

**Goals:**
- LLM 能将"在我旁边建房子"分解为可执行的子任务序列
- 状态机替代当前规则循环，支持任意状态间条件切换
- Node.js 侧集成 `mineflayer-statemachine`，直接执行状态机
- LLM 规划失败时自动降级到规则模式
- 新增 3 个智能动作：smart_goto（长距离）、smart_build（多步）、auto_eat（生存）

**Non-Goals:**
- 不做 Voyager 级别的技能库（那是下一步）
- 不做 Mindcraft 的完整 RAG 系统（用 Anima 已有 Wiki 记忆即可）
- 不改变 bridge.py 的 JSON 协议格式
- 不重写 index.js 全部逻辑（增量改造）

## Decisions

### Decision 1: 状态机位置 — Node.js 侧 vs Python 侧

**选择**: Node.js 侧运行 mineflayer-statemachine，Python 侧只发"模式切换"指令

**理由**:
- `mineflayer-statemachine` 是 JS 库，绑定 Mineflayer 对象
- Python 侧只需发送 `set_mode` 命令切换模式
- 状态转换在 Node.js 侧实时响应（毫秒级），无需跨 JSON 协议来回

**备选**: Python 侧自己做状态机 → 每步都要跨协议发 goto/mine → 延迟高、协议重

### Decision 2: LLM 规划器 — 独立模块 vs 嵌入 autonomous.py

**选择**: 新建 `planner.py` 独立模块，复用 Anima 已有 LLM 服务

**理由**:
- 规划逻辑独立，便于测试和升级
- 复用 `anima.services.intelligence.llm` 的已有 provider
- autonomous.py 简化为后备模式，职责单一

### Decision 3: LLM 调用频率 — 每步 vs 批量规划

**选择**: 批量规划 + 状态机执行 + 失败时重规划

**理由**:
- 规划一次生成完整步骤序列 → 状态机逐步执行
- 执行中某步失败 → 只重新规划剩余步骤
- 避免每步都调 LLM（成本、延迟）

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Python 侧                             │
│                                                         │
│  ┌──────────┐    ┌───────────────┐    ┌─────────────┐  │
│  │ 用户指令  │───▶│ Planner(LLM)  │───▶│ 模式选择器   │  │
│  │ "建房子"  │    │ 分解→子任务   │    │ LLM vs Rule │  │
│  └──────────┘    └───────┬───────┘    └──────┬──────┘  │
│                          │                    │         │
│                    ┌─────▼──────┐    ┌───────▼──────┐  │
│                    │ 子任务队列  │    │ RuleLoop     │  │
│                    │ [收集,铺地] │    │ (后备)       │  │
│                    └─────┬──────┘    └───────┬──────┘  │
│                          │                    │         │
├──────────────────────────┼────────────────────┼─────────┤
│               Bridge (set_mode / run_plan)    │         │
├─────────────────────────────────────────────────────────┤
│                    Node.js 侧                            │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              StateMachine                        │   │
│  │                                                  │   │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐        │   │
│  │  │收集  │  │ 建造 │  │ 战斗 │  │ 闲置 │  ...   │   │
│  │  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘        │   │
│  │     └─────────┴─────────┴─────────┘              │   │
│  │           (任意状态可切换)                         │   │
│  │                                                  │   │
│  │  新增: smart_goto / smart_build / auto_eat       │   │
│  └──────────────────────┬──────────────────────────┘   │
│                         │                               │
│  ┌──────────────────────▼──────────────────────────┐   │
│  │  Mineflayer (pathfinder + pvp + collectblock)    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 协议扩展

当前协议: `{"id": 1, "action": "goto", "params": {"x": 10, "y": 64, "z": 20}}`

新增模式:
```json
// 启用 LLM 规划模式
{"id": 1, "action": "set_mode", "params": {"mode": "planner", "plan": [
  {"action": "smart_goto", "params": {"target": "oak_tree"}},
  {"action": "smart_collect", "params": {"block": "oak_log", "count": 16}},
  {"action": "smart_build", "params": {"blueprint": "small_house"}}
]}}

// 启用规则后备模式
{"id": 2, "action": "set_mode", "params": {"mode": "rule"}}

// 单步状态查询
{"id": 3, "action": "plan_status"}
// → {"id": 3, "status": "success", "result": {"step": 2, "total": 5, "current": "building"}}
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| LLM 规划质量不稳定 | 规划结果验证（子任务必须映射到现有工具），失败降级到 rule 模式 |
| 状态机复杂度增加 | 每个状态 50 行以内，新增行为只需注册新状态 |
| mineflayer-statemachine 与现有 index.js 冲突 | 增量改造：保留现有 JSON 协议处理器，状态机作为 dispatch 层 |
| LLM 调用延迟（数秒） | 批量规划 + 异步执行，不阻塞游戏循环 |
