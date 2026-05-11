## ADDED Requirements

### Requirement: Smart long-distance navigation
系统 SHALL 支持长距离智能导航，能绕过水域、峡谷等障碍。

#### Scenario: Navigate across terrain
- **WHEN** 目标距离 > 50 格
- **THEN** Bot SHALL 使用 layered pathfinding（先粗后细）减少计算量
- **AND** 自动绕过大片水域和深谷

### Requirement: Multi-step building
系统 SHALL 支持多步骤建造序列，按蓝图逐步放置方块。

#### Scenario: Build a wall
- **WHEN** 执行 smart_build(wall, position, dimensions)
- **THEN** Bot SHALL 按行/列顺序放置方块，不遗漏

### Requirement: Auto survival behaviors
系统 SHALL 自动执行生存行为：饥饿时进食、低血量时后退。

#### Scenario: Auto eat when hungry
- **WHEN** 食物值 < 6
- **THEN** Bot SHALL 自动切换到手上食物并食用
