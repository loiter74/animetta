## Why

当前 AnimaBot 只能被动等待 LLM 指令，缺乏自主行为能力和持续的游戏内活动。玩家希望 AI 角色能像真人一样：会说话互动、自主收集资源、建造建筑，并根据简单的行为规则自主决策做什么，让 Minecraft 世界更有活力。

## What Changes

- **AI 自主决策循环**: 新增 AutonomousBehaviorLoop，让 AI 在没有玩家指令时自主决定行为（聊天、探索、收集、建造）
- **收集→建造管线 collect-buid pipeline**: 实现"感知资源需求→寻找/收集→建造目标→评估结果"的闭环
- **行为规则系统**: 新增 `rules.md` 文件，定义 AI 的行为偏好、优先级、安全边界和 personality
- **聊天互动升级**: 基于附近玩家和游戏事件触发主动聊天（打招呼、报告进度、表达情绪）
- **状态感知**: AI 能感知周围环境（时间、天气、附近实体、库存），并据此决策

## Capabilities

### New Capabilities
- `autonomous-loop`: 自主决策循环，无指令时 idle 状态下按规则运行
- `collect-build-pipeline`: 收集材料→建造的闭环流程，含目标选择、路径规划和进度追踪
- `behavior-rules`: 行为规则系统，定义 AI 什么该做什么不该做
- `proactive-chat`: 主动聊天，基于环境和事件触发对话
- `world-awareness`: 环境感知，为决策提供上下文

### Modified Capabilities
<!-- No existing specs are being modified -->

## Impact

- **新增文件**: `src/anima/tools/minecraft/rules.md`（行为规则配置）、`src/anima/tools/minecraft/autonomous.py`（自主循环逻辑）
- **修改文件**: `src/anima/tools/minecraft/tools.py`（可能新增决策工具）、`src/anima/tools/minecraft/bridge.py`（增强状态上报）
- **配置更新**: `config/tools.yaml` 新增自主行为配置项
- **新依赖**: 无（完全基于现有 Mineflayer 工具和桥接）
