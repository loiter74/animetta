# Animetta 项目能力简报

日期：2026-10-10。分析基线：`a36fcf8a08687f096a43911d454ae03b1d480a02`，结合当前工作区源码、架构文档和测试定义。

本次进行静态分析，没有启动应用、连接直播间或游戏服务器，也没有运行产品测试。下文的“已实现”表示存在对应代码及接入路径；测试文件证明有验证设计，不表示本次测试通过。工作区中尚未提交的训练数据审核工具不纳入正式能力结论。

## 一页摘要

**Animetta 是面向 AI 伙伴与虚拟主播的角色运行框架，覆盖对话、声音、Live2D 表演、记忆、直播互动和外部行动，并提供运营后台。** 用户侧通过直播舞台接收角色表现，操作者通过 Dashboard 管理现场、节目、记忆和验证；两者复用后端模型与业务能力。

从源码看，项目形成了三条能力主线：

- **角色交互**：文字／语音输入，角色化回复，长期记忆召回，情绪与表演控制，语音输出。
- **直播运营**：Bilibili 弹幕接入、回复排队、主动话题、场景分析、节目脚本、唱歌制作与梗库治理。
- **外部行动**：通过工具控制 Minecraft，通过私密地球探索工作区检索地点、移动地图并讲解。

**分析判断：项目的工程特点是将这些能力纳入可配置、可观察、可审批和可恢复的执行体系。** 它适合描述为“有运营后台的多场景 AI 角色系统”。本次证据不足以判断长期无人值守稳定性、真实主播表现、模型质量或规模化服务能力。

## 产品形态

| 入口 | 使用者与能力 | 源码依据 |
| --- | --- | --- |
| `/live.html` | 面向观众的直播舞台，接收角色、声音与直播输出；公开连接的业务控制事件受到只读限制 | [直播控制器](../../frontend/src/live/controller.ts)、[服务端注册与访问控制](../../src/animetta/orchestration/server/routes.py) |
| `/dashboard` | 面向操作者，提供“现场、节目、记忆、验证、探索”工作区；探索可由构建开关关闭 | [Dashboard 页面](../../frontend/src/views/DashboardPage.vue) |
| `/account` | 支持账号及会话管理，作为后台的辅助页面 | [账号页面](../../frontend/src/views/AccountPage.vue)、[路由](../../frontend/src/router/index.ts) |

Web 前端使用 Vue 3，仓库也保留 Electron 桌面壳与打包脚本。当前产品重心从页面组织上表现为直播舞台与运营后台；桌面打包定义不等于本次已验证安装包。[前端项目配置](../../frontend/package.json)

## 主要能力与边界

| 能力 | 当前实现 | 实际使用边界 |
| --- | --- | --- |
| 文字与语音对话 | 文字／音频分流、ASR、人格注入、LLM 回复、工具循环、语音合成、对话历史与中断接口；模型接口支持流式输出 | 需要对应模型、网络或本地服务；语音识别、回复质量、延迟和实际播放均需现场验证。[状态图](../../src/animetta/orchestration/graph/builder.py)、[LLM 接口](../../src/animetta/services/llm/interface.py) |
| 人格与表达 | 人格切换、人格模式、幽默改写与校验；状态图还提供“推理—表达—响应校验”的两阶段分支 | 分支能否启用取决于运行配置；人格一致性和幽默效果属于模型行为，不由节点存在性保证。[状态图](../../src/animetta/orchestration/graph/builder.py)、[人格路由](../../src/animetta/orchestration/server/routes.py) |
| Live2D 表演 | 将结构化表演标记映射为角色状态、强度与表情点缀，配合共享渲染、口型与音频控制 | 实际效果依赖模型资源、参数映射和浏览器渲染；不能据此认定所有 Live2D 模型均兼容。[表演契约](../../src/animetta/avatar/performance.py)、[共享渲染器](../../frontend/src/shared/live2d/renderer.ts) |
| 长期记忆 | `LivingMemorySystem` 管理记忆原子、版本、来源、作用域、召回、再巩固与代谢；后台支持检索、固定、修正和遗忘 | 记忆写入模式和索引可用性受配置与依赖影响；情绪重排是实现机制，不能作为“类人记忆效果”的证明。[记忆系统](../../src/animetta/memory/v2/system.py)、[存储与检索](../../src/animetta/memory/v2/store.py) |
| Bilibili 直播互动 | 真实弹幕传输适配与回放适配，消息／事件处理、回复准入与队列、回复长度约束、主动话题及场景分析 | 真实接入依赖平台连接条件；场景分析提供 off／shadow／active 模式，当前实例是否启用未核验。[弹幕网关](../../src/animetta/services/bilibili/gateway.py)、[直播会话](../../src/animetta/services/bilibili/livestream_session.py)、[场景运行时](../../src/animetta/services/scene_analysis/runtime.py) |
| 节目与梗库 | 编辑、校验和发布结构化节目脚本，按节拍推进并记录结果；后台包含唱歌制作、梗候选采集与审核入口 | 节目运行器是受控的线性脚本执行器；梗的采集、审核与使用分属不同环节。[节目工作区](../../frontend/src/components/program/ProgramWorkspace.vue)、[脚本运行器](../../src/animetta/services/program_script/runtime.py) |
| 唱歌制作 | 音源处理、人声／伴奏分离、歌词转写或导入与确认、声线转换、混音、字幕和口型音量数据；结果携带声线身份及转换状态 | 存在分离及转换降级路径。必须核对 `voice_conversion_applied`、真实模型身份和播放证据；产出音频文件不能单独证明真实变声。[唱歌流程](../../src/animetta/services/singing/svc_pipeline.py)、[RVC 桥接](../../src/animetta/services/singing/rvc_bridge.py) |
| Minecraft 行动 | Python 控制平面通过独立 Node.js／Mineflayer MCP 服务执行行动；包含目标策略、预算、日志、取消、恢复对账和目标验证 | 需要游戏服务器与 mc-mcp 服务；结果应以世界观测和目标验证为准。任意复杂任务的成功率及长时间自主生存效果，本次未测。[控制平面](../../src/animetta/tools/minecraft/voyager/control_plane.py)、[目标验证器](../../src/animetta/tools/minecraft/voyager/goal_verifier.py)、[mc-mcp 说明](../../services/mc-mcp/README.md) |
| 地球探索 | 正式 Dashboard 接入地点检索、候选选择、地图移动、文字／语音输入与讲解、暂停和指认；使用独立领域契约与地图适配器 | 源码明确声明 `vision: false`、`auto_search: false`。不能宣传为卫星图视觉理解或自主定位住址；地图与检索需要外部服务。[探索服务](../../src/animetta/services/earth/exploration.py)、[工作区](../../frontend/src/features/earth/EarthWorkspace.vue) |
| 私密演练与验证 | Dashboard 对话沙盒使用显式上下文，提供弹幕回放及独立评估代码；可将记忆内容送入沙盒演练 | 沙盒要求 Provider 支持不污染共享历史的消息接口；离线回放与真实直播各自需要验证。[沙盒](../../src/animetta/services/dialogue/sandbox.py)、[验证工作区](../../frontend/src/components/dashboard/ValidationWorkspace.vue)、[直播评估](../../evaluations/livestream/runner.py) |

## 能力如何组合

以一条观众弹幕为例，直播接入层先处理房间、消息与身份，回复准入和队列决定进入对话的时机；LangGraph 组织人格、模型、工具与回复节点；记忆和场景服务提供上下文；回复通过声音与 Live2D 表演呈现。操作者在后台观察执行链路，并调整节目或治理记忆。

Minecraft 行动复用角色对话入口，但世界操作交由独立控制平面和 mc-mcp 服务执行；动作回执与观测进入目标验证，游戏活动也可形成直播讲述素材。地球探索则拥有专门的探索状态图与私密会话，复用 ASR／LLM／TTS 服务，并让前端回报地图动作及图层就绪状态。

这种组合使“角色说什么”“角色如何表现”“角色在外部做什么”“操作者如何管理”具有各自的实现边界。[模块所有权与依赖方向](module-map.md)

## 技术架构与工程机制

| 层次 | 职责与已存在机制 |
| --- | --- |
| 产品界面 | Vue 3／Vite／UnoCSS；Dashboard 与独立直播页面；共享音频、传输和 Live2D 基础设施 |
| 服务端接入 | Python 3.13、Starlette、Socket.IO ASGI；认证、限流、会话和业务路由 |
| 编排 | LangGraph 状态图；文字／音频分支、工具循环、检查点注入与中断处理 |
| 业务与模型 | 对话、直播、节目、记忆、唱歌、探索等领域服务；通过 `ProviderRegistry` 注册模型配置和实现 |
| 外部运行时 | Windows 宿主 Qwen TTS、RVC 推理与独立 mc-mcp 服务；按各自生命周期管理 |
| 数据与观测 | SQLite 记忆与命令状态、Chroma／FTS5 检索、Redis 检查点，以及观察账本、OpenTelemetry 和 Prometheus 接口 |

依据：[后端依赖](../../pyproject.toml)、[前端依赖](../../frontend/package.json)、[Provider 注册器](../../src/animetta/config/core/registry.py)、[模块地图](module-map.md)、[运行规则](../../AGENTS.md)、[观察层](../../src/animetta/observability/ports.py)。

下面几项机制对系统实际运行尤其有意义：

- **模型可替换**：LLM、ASR、TTS 等实现采用配置／接口／工厂／注册器组织；已有云端和本地适配。某个适配器存在，仍需核对它是否被选中、依赖是否就绪。
- **共享资源有明确归属**：应用拥有模型池，会话拥有对话上下文和会话资源，降低多个产品入口各自创建模型的风险。[运行时边界](module-map.md)
- **命令可追踪与去重**：SQLite Command Inbox 定义执行、观察、回放、冲突和审批状态，面向单实例的用户命令幂等。[命令收件箱](../../src/animetta/services/command_inbox.py)
- **私密信息与控制权限有边界**：观众记忆按稳定身份过滤，公开直播连接限制业务写操作，工具存在审批入口。[记忆上下文](../../src/animetta/memory/v2/context.py)、[访问与审批路由](../../src/animetta/orchestration/server/routes.py)
- **工程验证有统一模型**：质量目录规划受影响检查，CI 消费检查计划；模型调用和产品执行具有观测接口。[质量契约](../development/project-health.md)、[CI](../../.github/workflows/quality.yml)

这些机制构成了工程基础，但不自动证明多实例高可用、所有操作“恰好一次”、完整安全审计或长期无人值守运行。

## 证据与实现程度

本次能够确认的是：主要能力已有实现与产品／协议接入，核心边界有相应的测试定义。代表性证据如下，**本次均未重新执行**。

| 范围 | 可核查的验证设计 |
| --- | --- |
| 对话连续性 | [连续性证据契约](../../tests/acceptance/test_conversation_continuity_contract.py)、[直播连续性测试](../../tests/acceptance/test_livestream_conversation_continuity.py) |
| 记忆身份与隐私 | [重连后同一观众召回、不同观众隔离、匿名召回及编译隔离](../../tests/memory_v2/test_scoped_recall.py) |
| 唱歌真实转换 | [RVC 必需模式失败与可选降级测试](../../tests/services/singing/test_svc_pipeline_rvc.py) |
| Minecraft 完成判定 | [库存、战斗、结构、发现与原版进度证据测试](../../tests/tools/minecraft/voyager/test_goal_verifier.py) |
| 节目发布与控制 | [脚本复制、编辑、校验、发布和重复控制测试](../../tests/orchestration/server/test_program_script_api.py) |
| 地球探索 | [检索、动作回执、中断、私密上下文与播放时序测试](../../tests/services/earth/test_exploration.py) |

仓库还保存了 2026-09-22 的地球探索验收报告，其中记录正式文字探索与语音讲解证据，同时列出语音输入和视觉分析限制。它属于**历史验收记录**，不能代表当前运行实例已经通过相同验收。[历史报告](../development/earth-exploration-verification.md)

据此可以判断：项目已经具备多个业务模块协作的实现结构，验证设计关注身份、重连、去重、取消、降级和执行证据。真实场景下的表现、稳定性及成功率，应另由当前运行验收确认。

## 阅读现有文档时需要注意

1. **记忆以当前 v2 调用链为准。** 概览中“向量 70% + 关键词 30%”的描述与当前实现不同。实际流程在 `AtomStore.hybrid_search` 中合并向量和关键词候选，随后 `LivingMemorySystem.recall` 进行可见性过滤、情绪及身份重排；不能仅引用评分辅助函数来描述整个召回链。[检索](../../src/animetta/memory/v2/store.py)、[召回](../../src/animetta/memory/v2/system.py)
2. **地球原型与正式探索应分别阅读。** `earth-prototype` 保留脚本演示；正式能力位于 `features/earth`、`services/earth` 和专门状态图。原型报告中“未接入模型”的边界不应直接套用到正式工作区。[正式探索状态图](../../src/animetta/orchestration/graph/earth_graph.py)
3. **工作区组织比旧功能列表更能反映当前产品。** Dashboard 已按现场、节目、记忆、验证、探索组织；阅读源码时先从这些工作区定位，再沿服务与编排追踪。

## 后续架构分析入口

此前生成的[文件索引](file-index.md)提供目录规模和完整路径清单；它是文件导航快照，不是代码行数、测试用例数或复杂度统计。

阅读顺序：先看本简报了解能力，再看[模块地图](module-map.md)明确所有权和依赖方向，最后通过[文件索引](file-index.md)与 CodeGraph 深入具体调用链。应重点区分“应用共享资源与会话资源”“角色回复与外部动作”“公开舞台与私密控制”“源码实现与现场证据”这四组边界。
