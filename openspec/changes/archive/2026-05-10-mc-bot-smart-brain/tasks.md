## 1. Node.js 侧 — 状态机集成

- [x] 1.1 安装依赖：`mineflayer-statemachine`、`mineflayer-auto-eat`
- [x] 1.2 创建 `bot/behaviors/` 目录，每个行为一个状态模块
- [x] 1.3 实现状态：收集 (GatherState)、建造 (BuildState)、战斗 (CombatState)、闲置 (IdleState)
- [x] 1.4 实现状态转移条件：收集完成 → 建造、敌怪靠近 → 战斗、战斗结束 → 之前状态
- [x] 1.5 在 index.js 中集成状态机，替换现有 busy + idle loop
- [x] 1.6 实现 mode 切换：planner 模式（逐步骤执行）vs rule 模式（等待 Python 指令）

## 2. Node.js 侧 — 智能动作

- [x] 2.1 实现 smart_goto：长距离分层寻路，自动绕障碍
- [x] 2.2 实现 smart_build：多步骤建造序列（按蓝图逐步放方块）
- [x] 2.3 实现 auto_eat：饥饿自动进食（用 mineflayer-auto-eat）

## 3. Python 侧 — LLM 规划器

- [x] 3.1 创建 `planner.py`，调用 Anima 已有 LLM 服务
- [x] 3.2 实现 goal → 子任务分解：用 LLM 生成结构化的子任务 JSON
- [x] 3.3 实现规划验证：确保 LLM 输出的子任务都能映射到已有工具
- [x] 3.4 实现动态重规划：某步失败时重新规划剩余步骤
- [x] 3.5 实现模式选择器：有 LLM 目标 → planner 模式，无目标 → rule 模式

## 4. Python 侧 — 降级改造

- [x] 4.1 重构 autonomous.py：添加暂停/恢复接口，planner 激活时暂停
- [x] 4.2 在 bridge.py 中添加 set_mode 和 plan_status 协议命令

## 5. 集成与测试

- [x] 5.1 端到端测试："在我旁边建个房子" → LLM 规划 → 状态机执行
- [x] 5.2 降级测试：LLM 不可用时自动切换到 rule 模式
- [x] 5.3 中断测试：建造中僵尸出现 → 切战斗 → 战斗后继续建造
- [x] 5.4 更新 rules.md 添加 planner 模式的行为偏好
