## Why

当前 AnimaBot 的自主行为是基于固定优先级规则表的简单循环，缺乏真正的"理解能力"和"规划能力"。它能按规则收集→建造，但无法理解"在我旁边建个瞭望塔"这种自然语言目标，也无法应对"材料不够时切收集、天黑时避难、再回来继续建"这种多步骤动态规划。现在已有 9 个基础工具和 LLM 服务体系，升级到 LLM 规划 + 状态机执行的时机已到。

## What Changes

- **LLM 规划层**: 新增 Planner 模块，LLM 接收自然语言目标 → 拆解为子任务序列 → 动态调整计划 → 驱动状态机执行
- **状态机执行层**: 用 `mineflayer-statemachine` 替换当前 `autonomous.py` 中的自主循环，每个行为成为独立状态节点，支持任意节点间的条件切换
- **行为升级**: 新增"目标驱动"模式——LLM 有目标时用 LLM 规划，无目标时自动降级为规则驱动（复用已有 autonomous-loop）
- **Node.js 侧增强**: 在 `index.js` 中集成状态机，新增 `smart_goto`（长距离导航）、`smart_build`（多步骤建造）、`auto_eat`（自动进食）等高级行为
- **记忆增强**: 利用 Anima 已有的 Wiki 记忆系统，记录 bot 探索过的区域、学到的技能、失败的任务，供 LLM 参考

## Capabilities

### New Capabilities
- `llm-planner`: LLM 将自然语言目标分解为可执行的子任务序列，支持运行时动态重规划
- `behavior-state-machine`: 基于 mineflayer-statemachine 的行为状态机，替代当前规则循环
- `smart-actions`: 高级动作：长距离智能导航、多步骤建造序列、自动进食、工具自动切换

### Modified Capabilities
- `autonomous-loop`: 从"唯一行为模式"降级为"无 LLM 目标时的后备模式"
- `collect-build-pipeline`: 从硬编码规则迁移到 LLM 可调度的子任务

## Impact

- **新增文件**: `src/anima/tools/minecraft/planner.py`（LLM 规划器）、`src/anima/tools/minecraft/state_machine.py`（Python 侧状态机包装）
- **修改文件**: `src/anima/tools/minecraft/bot/index.js`（集成状态机 + 新动作）、`src/anima/tools/minecraft/autonomous.py`（降级为后备）、`src/anima/tools/minecraft/bridge.py`（支持 smart 动作）
- **新依赖**: `mineflayer-statemachine`（npm）、`mineflayer-auto-eat`（npm）
- **原有依赖不变**: mineflayer-pathfinder、mineflayer-pvp、mineflayer-collectblock
