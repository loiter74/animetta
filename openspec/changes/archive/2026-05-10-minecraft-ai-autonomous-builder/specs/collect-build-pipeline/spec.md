## ADDED Requirements

### Requirement: Material inventory tracking
系统 SHALL 跟踪 Bot 当前库存，并与建筑目标所需材料进行对比。

#### Scenario: Check material sufficiency
- **WHEN** 自主循环评估建造行为
- **THEN** 系统 SHALL 对比库存与 rules.md 中 building.required_materials
- **AND** 如果材料不足，进入收集模式而非建造模式

#### Scenario: Inventory status report
- **WHEN** 收集行为完成或库存变化
- **THEN** Bot 可触发状态报告聊天消息

### Requirement: Target material gathering
系统 SHALL 自动寻找并收集建造所需的缺失材料。

#### Scenario: Gather missing materials
- **WHEN** 检测到某种材料数量 < 目标需求
- **THEN** Bot SHALL 使用 mc_collect 工具收集该材料
- **AND** 优先收集最近的可获取来源

#### Scenario: Gather until sufficient
- **WHEN** Bot 执行收集行为
- **THEN** 持续收集直到该材料数量 >= 目标需求，或无法找到更多来源

### Requirement: Build plan execution
系统 SHALL 按 rules.md 中定义的 build_plan 步骤依次建造。

#### Scenario: Execute build steps in order
- **WHEN** 所有必需材料已收集完毕
- **THEN** Bot SHALL 按 build_plan 顺序执行每个建造步骤
- **AND** 每个步骤完成后 SHALL 评估结果再进入下一步

#### Scenario: Build progress tracking
- **WHEN** 一个建造步骤完成
- **THEN** 系统 SHALL 记录已完成步骤索引
- **AND** 持久化进度以便重启后恢复

### Requirement: Building site management
系统 SHALL 管理建造场地位置，确保建筑在同一位置进行。

#### Scenario: Designate build site
- **WHEN** 首次启动建造
- **THEN** Bot SHALL 选择平坦区域作为建造场地
- **AND** 在 rules.md 或运行时记录该位置坐标
