## MODIFIED Requirements

### Requirement: Material inventory tracking
系统 SHALL 跟踪 Bot 当前库存，并与建筑目标所需材料进行对比。支持 LLM planner 动态注入新的材料需求。

#### Scenario: Check material sufficiency
- **WHEN** 自主循环或 planner 评估建造行为
- **THEN** 系统 SHALL 对比库存与 target.required_materials
- **AND** planner 可动态追加材料需求（如 LLM 判断需要玻璃做窗户）

#### Scenario: Inventory status report
- **WHEN** 收集行为完成或库存变化
- **THEN** Bot 可触发状态报告，LLM planner 可根据库存变化重新规划
