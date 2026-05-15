## MODIFIED Requirements

### Requirement: 梗筛选页面路由
系统 SHALL 在 Anima 前端新增 `/meme-review` 路由，加载 `MemeReview.vue` 视图组件。

#### Scenario: 路由访问
- **WHEN** 用户导航到 `/meme-review`
- **THEN** 系统 SHALL 显示梗筛选页面
- **AND** 自动从后端获取待筛选梗列表

### Requirement: 梗卡片展示
系统 SHALL 以卡片形式逐个展示待筛选的梗。

#### Scenario: 卡片内容展示
- **WHEN** 页面加载梗列表
- **THEN** 每张卡片 SHALL 显示：梗文本（text）、来源平台（source_platform）、标签（tags）、认知分析（humor_mechanism、emotional_tone）
- **AND** 如果有 source_url，SHALL 显示可点击的 B 站视频链接
- **AND** 卡片 SHALL 使用玻璃态样式（`bg-c-card/50 rounded-xl`）呈现
- **AND** 卡片 SHALL 在悬停时有渐变色反馈

#### Scenario: 逐个展示
- **WHEN** 页面有多个待筛选梗
- **THEN** 系统 SHALL 一次只展示一个梗
- **AND** 用户做出选择后以动画过渡到下一个
- **AND** 切换动画 SHALL 使用 slideInRight / slideOutRight 动效

#### Scenario: 空列表状态
- **WHEN** 后端返回空梗列表
- **THEN** 页面 SHALL 显示 "暂无待筛选梗，去采集一些吧" 提示
- **AND** 提示区域 SHALL 使用玻璃态样式，与面板风格一致

### Requirement: 好/坏投票
系统 SHALL 提供「好」和「烂」两个按钮用于梗质量投票。

#### Scenario: 标记为「好」
- **WHEN** 用户点击「好」按钮
- **THEN** 系统 SHALL 调用 `POST /api/memes/review` 提交 `status: "good"`
- **AND** 按钮 SHALL 显示绿色主题样式（`bg-c-success/15 text-c-success`）并在 hover 时有发光效果
- **AND** 卡片 SHALL 以绿色动画过渡到下一个梗
- **AND** 更新进度计数（已筛选 N/M）
- **AND** 好梗计数 SHALL 以数字飘动画效更新

#### Scenario: 标记为「烂」
- **WHEN** 用户点击「烂」按钮
- **THEN** 系统 SHALL 调用 `POST /api/memes/review` 提交 `status: "bad"`
- **AND** 按钮 SHALL 显示红色主题样式（`bg-c-error/15 text-c-error`）并在 hover 时有发光效果
- **AND** 卡片 SHALL 以红色动画过渡
- **AND** 如果后端返回 AI 吐槽内容，SHALL 在过渡前展示吐槽

### Requirement: AI 吐槽展示
系统 SHALL 在标记烂梗后展示 AI 生成的吐槽。

#### Scenario: 吐槽展示
- **WHEN** 后端返回 AI 吐槽内容
- **THEN** 页面 SHALL 在卡片下方以 VTuber 对话气泡形式展示吐槽文本
- **AND** 气泡 SHALL 使用 `chat-msg-enter-active` 动画入场
- **AND** 吐槽展示 2 秒后自动消失并切换到下一个梗

### Requirement: 进度追踪
系统 SHALL 展示当前筛选进度。

#### Scenario: 进度显示
- **WHEN** 页面展示梗列表
- **THEN** 系统 SHALL 显示 "第 N 个 / 共 M 个" 的进度指示器
- **AND** 好/坏计数分别以绿/红色标签显示
- **AND** 进度条 SHALL 使用 `gradient-accent` 渐变填充

### Requirement: 数据集导出
系统 SHALL 提供导出已筛选高质量梗的功能。

#### Scenario: 导出按钮
- **WHEN** 用户点击「导出数据集」按钮
- **THEN** 系统 SHALL 调用 `GET /api/memes/dataset`
- **AND** 下载包含高质量梗的 JSON 文件
- **AND** 按钮 SHALL 在导出完成后显示成功状态
