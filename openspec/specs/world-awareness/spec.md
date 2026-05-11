# world-awareness Specification

## Purpose
TBD - created by archiving change minecraft-ai-autonomous-builder. Update Purpose after archive.
## Requirements
### Requirement: Full state query
系统 SHALL 在自主循环每次评估时获取 Bot 完整状态。

#### Scenario: State includes all decision factors
- **WHEN** 自主循环触发状态查询
- **THEN** 返回数据 SHALL 包含：位置(x,y,z)、血量、食物、维度、游戏模式、天气、时间、生态群系、库存物品列表、附近实体列表

### Requirement: Environmental awareness
系统 SHALL 感知并解读环境信息用于决策。

#### Scenario: Night detection
- **WHEN** 状态中 time 为 night
- **THEN** 系统 SHALL 标记为高风险外部活动时段

#### Scenario: Weather impact on decisions
- **WHEN** 天气为 rain 或 thunder
- **THEN** 系统可降低户外活动（如探索）的优先级

### Requirement: Entity awareness
系统 SHALL 感知附近实体并用于决策。

#### Scenario: Hostile mob detection
- **WHEN** nearby_entities 包含 hostile 类型实体
- **THEN** 系统 SHALL 评估威胁级别
- **AND** 威胁高时优先战斗或逃跑

#### Scenario: Player detection
- **WHEN** nearby_entities 包含玩家
- **THEN** 系统 SHALL 知道附近有玩家可用于触发社交行为

