## 1. 行为规则系统 (rules.md)

 - [x] 1.1 创建 rules.md
 - [x] 1.2 创建 RulesEngine 类
 - [x] 1.3 实现规则验证

## 2. 世界感知 (World Awareness)

 - [x] 2.1 创建 WorldState 数据类
 - [x] 2.2 实现状态分析器
 - [x] 2.3 实现实体感知

## 3. 自主决策循环 (Autonomous Loop)

- [x] 3.1 创建 AutonomousLoop 类
- [x] 3.2 实现评估→决策→执行的主循环（5-10 秒间隔）
- [x] 3.3 实现优先级决策：基于 rules.md 优先级 + 当前状态选择行为
- [x] 3.4 实现动作超时机制（30 秒超时 + 重置）
- [x] 3.5 实现 LLM 指令暂停/恢复自主循环的机制
- [x] 3.6 实现行为冷却系统（每种行为有独立冷却时间）

## 4. 收集→建造管线 (Collect-Build Pipeline)

- [x] 4.1 实现材料缺口检测：对比 inventory + 库存追踪与 required_materials
- [x] 4.2 实现智能收集：目标材料不足时自动调用 mc_collect 持续收集
- [x] 4.3 实现建造进度管理：按 build_plan 顺序执行步骤，记录已完成步骤
- [x] 4.4 实现建造场地选择：检测平坦区域，定位建筑位置
- [x] 4.5 集成管线到自主循环：建造优先级 < 生存优先级

## 5. 主动聊天 (Proactive Chat)

- [x] 5.1 实现聊天触发器：玩家靠近、时间变化、天气变化、建造进度
- [x] 5.2 实现聊天冷却（30 秒）和概率触发（proactive_chance）
- [x] 5.3 实现上下文消息选择：从 rules.md chat.topics 按场景随机选择消息

## 6. 集成与测试

- [x] 6.1 将 AutonomousLoop 集成到 MinecraftBridge 中（bridge.py）
- [x] 6.2 更新 config/tools.yaml 新增 autonomous 配置项
- [x] 6.3 编写自主循环集成测试（mock 状态输入验证决策输出）
- [x] 6.4 编写 rules.md 解析测试（合法配置/非法配置/边界情况）
- [x] 6.5 全链路手动测试：启动 Bot → 验证自主移动 → 验证收集→建造
