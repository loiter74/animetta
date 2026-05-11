## Context

AnimaBot 已有完整的 Minecraft 工具集（mc_goto, mc_mine, mc_build 等 9 个工具）和 Mineflayer 桥接，但目前是被动触发模式——只能等 LLM 调用工具。玩家希望 AI 能自主决策、持续活动，形成"收集材料→建造→聊天"的闭环体验。

当前状态：
- Bridge 层支持发送 action 指令到 Node.js Mineflayer bot
- 9 个工具覆盖移动、挖掘、建造、战斗、聊天、状态查询
- 安全性配置已有（no_griefing, auto_heal, max_distance）
- 无自主决策循环、无行为规则系统、无持续目标管理

## Goals / Non-Goals

**Goals:**
- AI 在无玩家指令时能自主决策下一个行为
- 实现"感知→评估→决策→执行"的自主循环
- 支持收集材料→建造目标的简单管线
- 基于 rules.md 配置文件控制行为偏好和边界
- AI 能根据环境和状态主动触发聊天

**Non-Goals:**
- 复杂建筑蓝图系统（仅限简单结构：小屋、围墙、瞭望塔）
- 多机器人协作
- 完整的任务/队列系统（当前只做单步决策）
- 与 LLM 实时流式决策（固定规则优先，LLM 增强可选）

## Decisions

### Decision 1: 决策引擎位置 — Python 侧 vs Node.js 侧
**选择**: Python 侧自治循环 + Node.js 侧 idle handler

**理由**:
- Python 可以直接读取 rules.md、调用工具、记录日志
- Node.js 侧适合做实时响应（聊天事件、受伤反应）
- 分工清晰：Python = 战略决策，Node.js = 战术执行 + 紧急反应

### Decision 2: 决策模式 — Rule-based vs LLM-based
**选择**: 双层架构：Rule-based 主循环 + LLM 增强可选

**理由**:
- Rule-based 反应快、可预测、无 API 成本
- LLM 增强用于复杂决策（"建什么风格？""怎么回应某玩家？"）
- 默认只用 Rule-based，LLM 增强作为可选项

### Decision 3: 目标管理 — 单一目标 vs 目标队列
**选择**: 单一活跃目标 + 优先级驱动切换

**理由**:
- 简单可靠，不易出现目标堆积
- 优先级来自 rules.md（如：生存 > 建造 > 社交）
- 当前目标完成后自动评估下一个最高优先级目标

### Decision 4: 自主循环触发频率
**选择**: 5-10 秒间隔，每次重新评估

**理由**:
- Minecraft 操作耗时（走路、挖掘）本身需要秒级时间
- 5-10 秒避免过度决策，也足够响应环境变化
- 执行耗时操作时跳过评估（busy 状态）

## Architecture

```
┌─────────────────────────────────────────────┐
│              AutonomousLoop (Python)          │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │ RulesEngine │→│ StateEval │→│ Decision   │  │
│  │ (rules.md) │  │ (status)  │  │ (action)   │  │
│  └───────────┘  └──────────┘  └──────┬───┘  │
│                                      │       │
└──────────────────────────────────────┼───────┘
                                       │
              ┌────────────────────────┼────────┐
              │       Action Executor   │        │
              │  ┌──────┐ ┌────┐ ┌────┐│        │
              │  │goto  │ │mine│ │build││        │
              │  └──┬───┘ └──┬─┘ └──┬──┘        │
              │     │        │      │            │
              │  ┌──┴────────┴──────┴──┐         │
              │  │  MinecraftBridge     │         │
              │  │  (JSON over stdin)   │         │
              │  └──────────┬───────────┘         │
              │             │                     │
              │  ┌──────────┴───────────┐         │
              │  │  Mineflayer Bot (JS)  │         │
              │  │  (index.js, idle.goal)│         │
              │  └──────────────────────┘         │
              └──────────────────────────────────┘
```

### 自主循环流程

```
[Every 5-10s when idle]
  │
  1. mc_status() → 获取完整状态
     ├─ position, health, food, dimension
     ├─ inventory (可用材料)
     ├─ nearby_entities (附近玩家/生物)
     ├─ time (昼夜), weather
     └─ current_goal (当前目标状态)
  │
  2. RulesEngine.evaluate(state, rules)
     ├─ 检查紧急情况（受伤、夜晚、怪物威胁）
     ├─ 评估当前目标进度
     ├─ 按优先级选择下一个行为
     └─ 生成 Action + 参数
  │
  3. Execute Action
     ├─ 聊天触发（概率 + 条件）
     ├─ 收集材料（目标材料不足时）
     ├─ 建造（有材料且目标未完成）
     ├─ 探索（无更优先事项）
     └─ 返回安全位置（夜晚/受伤时）
  │
  4. 等待 → 回到步骤 1
```

### rules.md 设计

```yaml
# AI 自主行为规则
character_name: "AnimaBot"
personality: "友好、勤劳的建造者"

priorities:
  - survival          # 生存永远第一
  - maintenance       # 维护已有建筑
  - building          # 建造新建筑
  - gathering         # 收集材料
  - social            # 社交/聊天
  - exploration       # 探索

building:
  target: "small_house"
  blueprint: "5x5 木石混合小屋，带门和窗户"
  required_materials:
    oak_log: 16
    cobblestone: 32
    glass: 4
  build_plan:
    - {action: "foundation", block: "cobblestone", area: "5x5"}
    - {action: "walls", block: "oak_planks", height: 3}
    - {action: "roof", block: "oak_stairs"}
    - {action: "windows", block: "glass"}
    - {action: "door", block: "oak_door"}

safety:
  return_to_base_at_night: true
  auto_heal_threshold: 10
  avoid_ravines: true
  max_build_height: 50

chat:
  proactive_chance: 0.25       # 每次评估时 25% 概率主动说话
  topics:
    - trigger: "player_nearby"
      messages: 
        - "你好！我在建房子呢"
        - "能帮我收集些木头吗？"
    - trigger: "night_time"
      messages:
        - "天黑了，注意安全"
        - "我该回基地了"
    - trigger: "building_progress"
      messages:
        - "地基打好了！"
        - "房子快建完了！"
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 自主循环与 LLM 指令冲突 | LLM 指令优先级 > 自主决策；LLM 调用时暂停自主循环 |
| Bot 卡在某个位置/动作 | 超时机制：每个动作 30s 超时，超时后重置并评估 |
| 无限循环同一行为 | 行为冷却：每个行为执行后有 N 秒冷却期 |
| rules.md 配置不合理导致奇怪行为 | 安全边界硬编码（no_griefing、max_distance）覆盖 rules.md |
| 资源耗尽（库存满） | 自动检查库存，满时触发存储或丢弃 |
