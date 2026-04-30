## ADDED Requirements

### Requirement: Memory organization status is shown in detail
The frontend SHALL display the current stage and progress of memory organization when it is running, using data from the `memory.organize.progress` socket event.

#### Scenario: Show organizing progress
- **WHEN** memory organization is in progress
- **THEN** the UI SHALL display the current stage text (e.g., "正在分析对话...", "正在合并相似内容...")
- **AND** a progress bar SHALL show completion percentage

#### Scenario: Show organizing complete
- **WHEN** memory organization finishes
- **THEN** the progress display SHALL disappear
- **AND** a brief completion message MAY be shown
