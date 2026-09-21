# 地球探索：接口与验证报告

日期：2026-09-22。状态：最终源码验证与正式文字探索通过，语音讲解有实际播放证据；最新检索修正已部署并复验。语音输入受外部凭据限制，视觉分析未授权。

本报告与 [实施计划](earth-exploration-plan.md) 配套。原型性能基线、静态边界、接口清单分别记录；正式 Dashboard、真实对话、语音、视觉及改造后性能必须有各自证据后才能标记完成。

## 1. 已落地的模块边界

`tooling/quality/architecture_boundaries.py` 复用现有审计入口和强连通分量算法，增加以下检查。主任务另已修改 `tooling/quality.yml` 中的 Docker 资源输入与功能开关指纹；质量目录仍以该文件为唯一真相源。

| 规则 | 拦截对象 | 允许的边界 |
| --- | --- | --- |
| `EARTH_SDK_OUTSIDE_ADAPTER` | 地球功能中 adapters 以外导入 Cesium、Socket 客户端、PIXI/Live2D SDK | 各适配器持有供应商 SDK；公共角色渲染器使用自己的 SDK |
| `EARTH_CORE_OUTWARD_IMPORT` | contracts/controller/core/domain 导入 Vue、Pinia、地图/传输 SDK、界面、装配或适配实现 | 核心通过显式参数消费普通契约 |
| `EARTH_DOMAIN_OUTWARD_IMPORT` | 后端 earth domain 导入编排、工具、其他业务服务、Provider、网络/模型 SDK | 领域值、earth contracts 与基础库 |
| `FRONTEND_SHARED_UPWARD_IMPORT` | 公共角色等 shared 模块导入 review、features 或其他上层模块 | shared 内部依赖与第三方基础 SDK |
| `FRONTEND_CROSS_FEATURE_DEEP_IMPORT` | 别名或相对路径导入另一个功能内部 | 功能公共入口，包括根 index |
| `EARTH_DEPENDENCY_CYCLE` | 前后端 earth 内部文件依赖环 | 有向无环依赖；复用现有检测器 |

Python `from package import module` 也解析实际导入目标，避免根包别名绕过检查。前端多行动态 import 纳入扫描；地球内部循环不再因顶层都归类为同一个功能而漏报。

限制：这是静态导入检查，不能识别任意运行时拼接模块名、全局对象访问或供应商条款违规；不替代模块行为测试和运行时资源检查。

## 2. 当前接口清单与验收责任

以下是实施中源码可见的接口，不表示真实链路已验证。字段的最终真相源是源码契约和 `config/socket-events.json`，本文不作为另一份协议 schema。

| 接口 | 输入/输出与责任 |
| --- | --- |
| `EarthMap` | `move(target, signal, progress)` 返回 `MapResult`；另外提供 `readView`、`pick`、`mark`、`capture`、`cancel`、`dispose`。不暴露 Cesium 对象 |
| `MapStatus` | accepted / arrived / ready / degraded / failed / cancelled；区分接收、到达与图层就绪 |
| `EarthView` | WGS84 经纬度、米制高度、相机姿态、视图版本、供应商、分析许可、质量及视口/DPR |
| `EarthTransport` | request/context/result 与 subscribe；Socket 事件转换在适配器内，控制器不导入 Socket SDK |
| `createEarthController` | 显式接收 conversationId、map、transport、narration、changed；拥有动作取消与 UI 状态投影 |
| `EarthSnapshot` | 包含 `selected`（可空的已选候选）、候选、会话与控制版本、transcript、能力和反馈截止时间；`reading` 表示文字阅读/讲解阶段，`feedback` 表示讲解结束后的反馈窗口，不合并为同一倒计时 |
| `Narration` | play/cancel/unlock；实际播放开始回调由适配器连接播放器，结束与取消回调带任务标识关联 |
| `GeographySearch` | `search(query)` 返回有来源的候选；供应商 HTTP 响应不跨出边界 |
| 后端领域契约 | Point/View/Candidate 与 Control/Context/Result；地理值、会话版本及动作状态在入口校验 |
| 共享角色渲染器 | `createLive2DRenderer` 接收 `canvas`、`resizeTo`、可选 `layout`、`onState`、口型回调；返回 ready/setMouth/applyAction、表演生命周期及 dispose。调用者分别拥有实例，review 包装负责原有 DOM/Socket 兼容 |

确定性测试覆盖重复动作、旧版本丢弃、操作者/控制版本、断线暂停、订阅释放、角色双实例、音频完成后等待、功能关闭与拒绝截图分析。真实浏览器覆盖范围见第 5 节；未以单测替代多浏览器长期压力或 WebGL 显存测量。

## 3. 改造前性能基线

### 冻结条件

- 原始提交：`bcbc67277a24782b6be943037ca46a5223fd7d2d`。
- 原始工作区在并行改造中，因此通过 `git archive` 导出已提交前端到隔离目录，复用安装好的 node_modules，独立 Vite 监听 `127.0.0.1:3012`。没有回退主工作区文件。
- 原请求入口为 `http://127.0.0.1:3011/earth-prototype.html`；正式有效采样入口为获授权的 `http://127.0.0.1:3012/earth-prototype.html`，仅用于原型基线，不证明正式 Dashboard。
- Chrome `153.0.8010.52`，headless，1600×1000，DPR 1；CPU i5-14600KF，WebGL 报告 NVIDIA GeForce RTX 5090 D v2 / ANGLE D3D11。
- 使用真实 Cesium、Esri 影像及 Mao Live2D。每轮等待角色 live 状态，再执行上海 → 区域 → 青浦 → 淀山湖 → 湖岸五段路线。每段等待解释阶段后暂停，避免自动推进影响采样。
- 30 FPS 与取消 p95 ≤100ms 的预测在 `2026-09-20T16:55:01.826Z` 冻结；不是实施后推定的验收结果。
- 第一批完成第 1–3 轮；随后一次第 4 轮启动阶段等待 globe.tilesLoaded 超时。保留这次失败，重新打开浏览器只补采第 4–5 轮，没有重跑已成功路线。

### 实测结果

| 成功轮次 | 启动等待 ms | RAF 样本数 | 间隔 p95 ms | 最大间隔 ms | 缓存条件 |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 3849 | 4118 | 6.2 | 145.4 | 新浏览器上下文；系统/网络缓存未清空 |
| 2 | 962 | 4100 | 6.2 | 24.3 | 同浏览器上下文 |
| 3 | 1205 | 4110 | 6.2 | 18.3 | 同浏览器上下文 |
| 4 | 2878 | 4113 | 6.2 | 139.4 | 超时后新建浏览器上下文 |
| 5 | 851 | 4094 | 6.2 | 30.4 | 同补采浏览器上下文 |

累计 20,535 个 RAF 间隔，中位数 6.1ms、p95 6.2ms、最大 145.4ms；99.9805% 的间隔不超过 33.33ms。各段从提交导航到解释阶段的耗时保留在原始文件 `steps[].elapsedMs`。

每轮路线后再次发起导航，经过两次 RAF，在页面内部调用暂停，分别记录同步调用耗时和下一帧看到暂停状态的耗时。五次同步耗时 p95 为 0.2ms；下一帧观察 p95 为 7.0ms，样本分别为 5.8 / 6.2 / 6.0 / 7.0 / 5.2ms。取消后再观察十帧，五轮位置与俯仰保持不变；首轮 heading 从 2π 规范化到 0，按模 2π 视作同一方向，原始值未修改。

### 解读限制

- RAF 是浏览器回调调度间隔，不是 GPU 实际提交/呈现帧；不能把其倒数称为已证明的地图渲染 FPS。
- 取消时间测量从页面函数调用开始，未包含真人输入硬件延迟或 Playwright 到浏览器的网络往返。
- 五次取消的最近秩 p95 等于该批最大值，样本量不足以估计稳定的生产尾延迟。
- 本批有一次进入路线前的底图就绪超时。返回的影像响应为 200、页面错误数组为空，具体阻塞原因未进一步证实；不能从成功路线推断加载可靠性为 100%。
- 第一轮及补采首轮只保证新浏览器上下文，不是真正的系统冷缓存；不同缓存组不能直接混称冷/热启动对比。
- 后续补采仅比较原型的共享角色替换，见下一节；仍不声明达到正式产品的 30 FPS 或 100ms 验收要求。

### 原始数据位置

统一位于本机可视化目录，不写入仓库运行时 `artifacts/` 或 `evidence/`：

`C:/Users/30262/.codex/visualizations/2026/09/20/01a0bf82-74ed-71b1-bbda-d90278e9d1bc/earth-build/`

- `perf-prediction.json`：先于有效采样冻结的预测。
- `perf-baseline-isolated-raw.json`：第 1–3 轮、逐帧间隔、阶段耗时、影像响应及后续启动超时。
- `perf-baseline-resume-raw.json`：仅补采第 4–5 轮。
- `perf-baseline-summary.json`：最近秩统计、各轮缓存说明、取消原始视图与稳定性判断。
- `perf-baseline.mjs`、`summarize-baseline.mjs`：采样与汇总脚本。
- `baseline-bcbc6727/source-hashes.json`、`asset-hashes.json`、`server-process.json`：源文件、原始归档、引擎/角色资源哈希及独立进程信息。
- `perf-baseline-raw.json`：最初 3011 混合版本的失败尝试；`perf-baseline-startup-failed.json`：服务尚未就绪时的连接失败；两者均不纳入基线统计。

完整本机文件不随 Git 自动分发。按用户明确要求，另在 [earth-evidence](earth-evidence/README.md) 保存四个精简原始时序文件和 manifest：保留逐帧间隔、阶段及取消时间、公开路线视图、哈希与失败，移除重复瓦片响应及本机绝对路径。复现者应保留同一提交与依赖版本、使用相同脚本，并将新批次另存，不能覆盖本批预测或原始证据。

## 4. 共享角色替换后的局部对比

入口保持 `http://127.0.0.1:3011/earth-prototype.html`，相同浏览器版本、1600×1000、DPR 1、公开五段路线和采样代码；文字模式、真实地图与角色。改造后等待 `[data-testid="earth-companion"] [data-state="live"]`，取代已移除的全局状态 ID。

第 1–2 轮完成后，Vite 资源脚本变更触发服务热重启，第三轮被开发 HMR 卸载打断。日志与失败原始数据保留。仅在测试浏览器隔离 Vite 热更新 WebSocket 后，补采第 3–5 轮，不改产品源码。两批分别保存为 `perf-post-renderer-raw.json` 与 `perf-post-renderer-resume-raw.json`。

| 成功轮次 | 启动等待 ms | RAF 样本数 | 间隔 p95 ms | 最大间隔 ms | 取消后下一帧 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4149 | 3188 | 8.2 | 193.4 | 8.0 |
| 2 | 1015 | 3196 | 8.2 | 39.1 | 6.7 |
| 3 | 4100 | 3174 | 8.2 | 178.5 | 6.9 |
| 4 | 1007 | 3212 | 8.2 | 31.5 | 7.0 |
| 5 | 977 | 3210 | 8.1 | 30.0 | 7.0 |

累计 15,980 个 RAF 间隔；中位数 7.8ms、p95 8.2ms、最大 193.4ms；99.9687% 的间隔不超过 33.33ms。取消同步耗时 p95 0.2ms，下一帧观察 p95 8.0ms。五轮取消后视图稳定。

本次观测的 RAF p95 从 6.2ms 增至 8.2ms，取消下一帧 p95 从 7.0ms 增至 8.0ms，**没有证明性能提升**。由于系统负载、缓存及开发活动未完全隔离，不把该差异归因于共享渲染器。预测没有据此修改。该对比不覆盖新 `features/earth` 地图适配器、正式 Dashboard、真实模型或语音。

`post-source-before.json` 与 `post-source-after.json` 证实原型、Companion、共享 renderer 与 Cesium 引擎哈希前后一致。被同时记录的 shared audio 播放器发生变化，但新角色渲染器和文字模式原型不导入它；这一变化照实保留在便携 manifest 中。原型快照不是整个正在开发的工作区冻结。

改造后操作截图为 `post-earth.png`、`post-shanghai.png`、`post-qingpu.png`、`post-lake.png`、`post-shore.png`、`post-picked.png`。采集记录 `post-demo.json` 没有页面错误，指认完成；1600×1000 下角色容器 bottom=1000，讲解框与角色无交叠。这是原型截图证据，非正式页面验收。

## 5. 验证进度与未完成项

| 项目 | 状态 | 证据或下一步 |
| --- | --- | --- |
| 架构违规/允许样例 | 已通过 | 本支持任务的 37 个定向 pytest 用例通过（3.30s），ruff check/format 通过；不代表主任务全部门禁通过 |
| 仓库静态边界 | 已通过 | 定向审计无违规；主任务最终 affected 的全部非 full 组已通过 |
| 原型性能基线 | 完成，有加载失败记录 | 五轮路线，两批原始数据，源文件哈希前后一致 |
| 地图契约、控制器与后端定向测试 | 已收到通过结果 | 主任务回传的精确范围见下表；不能外推为完整正式链路通过 |
| 正式 Dashboard E2E | 文字主流程通过 | 最终批次通过上海、青浦行政区、淀山湖与完整杭州西湖输入；点选、角色开关、三次重入另有证据，ASR 失败单列 |
| 现有 live/review 真实浏览器回归 | 已通过受影响范围 | live 实际字幕、播放与口型通过；8 个固定场景 browser 诊断通过，未做 OBS 稳定轮次 |
| 真实模型、宿主语音、视觉授权 | 模型与讲解通过，ASR/视觉受外部条件限制 | DeepSeek 与 Qwen 实际运行；MiMo ASR 返回 401 invalid_key，文字回退可用；未授权视觉分析保持关闭 |
| 改造后性能对比 | 原型对比与正式接管小样本完成 | 正式硬件 5 次接管，输入至取消 p95 0.7ms、下一帧 15.1ms；两种口径分开，不声明性能提升或 GPU FPS |
| 最终操作演示 PPT | 已生成并检查正式验收版 | 10 页、3 张原生可编辑表格，替换为真实 Dashboard 截图，明确 ASR 与视觉限制 |
| 最终 affected 验证 | `071aeb3aef04` 已通过 | 新检索规则在内的 5659 个后端、638 个前端测试及全部检查通过；`57c4d0b7b758` 为中断批次，不计成功 |
| 提交与推送 | 交付收尾 | 完成证据与文档检查后按任务精确文件提交；不包含 train/songs 的无关改动 |

### 主任务回传的定向验证

以下结果由主任务回传，本支持任务未重复执行；保留原有验证范围，不把局部或确定性测试写成正式运行时验收。

| 范围 | 已知结果 |
| --- | --- |
| Controller + Cesium | 26 passed |
| Deployment | 23 passed |
| ASR 有界处理与归一化 | 三种格式经实际 ffmpeg 验证；未提供用例数量或耗时，不补填 |
| Earth + MiMo / handlers / tools | 36 passed |
| 最终音频定向测试 | 8 passed；不等同于正式入口宿主语音全链路验收 |
| 跨入口 Earth 私密隔离 | 1 passed，8.81s |
| 确定性对话连续性 Skill | passed，31.714s |

### 最新门禁与部署进度

2026-09-21 用户从独立环境恢复 Docker 后，Docker Engine 29.8.0/Linux 正常响应，宿主 Qwen 与 RVC 均 running/ready 且身份匹配。构建诊断确认 Windows buildx 的镜像认证请求需要沿用现有本机代理；仅在生命周期进程环境设置代理，未修改全局设置。

生产 run `anima-up-earth-45e485d6ca77` 随后暴露实际构建上下文遗漏：`.dockerignore` 排除了 Dockerfile 要复制的 `frontend/scripts/earth-assets.ts`。现仅放行该文件。真实仓库上下文的隔离 Docker COPY 探针 exit 0（约 6.4s），导出文件与源文件前后 SHA256 均为 `5855a2ad9fb24547100d9713926e695b7bd8f322f64584ccce45a4e00ca2affe`；未创建产品标签或启动容器。

修复后的冻结计划 `3d3072a7b8c49e382ea95c9b1deae367576e0c5f6c7320da66e1f532f6fb8214` 已完整通过。26 个 backend-full 分片合计 5659 passed、分片耗时合计 617.04s；前端 95 个测试文件、638 项测试通过，覆盖率及全部其余组通过。证据目录为 `artifacts/test-impact/3d3072a7b8c49e382ea95c9b1deae367576e0c5f6c7320da66e1f532f6fb8214/results/`。随后完成下述规范部署与浏览器验收。

后续生产 run `anima-up-earth-6704ae5bf8e6` 已于 2026-09-22 00:06:14 完成，exit 0；容器启动、HTTP health、鉴权 ready、前端就绪与日志检查全部通过。当前 LLM 为 DeepSeek `deepseek-v4-flash`；ASR 配置为 MiMo `mimo-v2.5-asr`；TTS 主通道 billing 降级，实际回退到宿主 Qwen `Qwen3-TTS-1.7B-Base` / `tosaka-rin-cn`。构造就绪不等于外部接口凭据可用，ASR 的实际 401 另见下文。

### 正式入口分批验收（2026-09-22）

- `formal-1790006948413`：7 个步骤通过，包含未进入探索时不加载 Earth 资源、真实地图与角色、上海/青浦/淀山湖导航到 ready、暂停与用户点选、角色单独开关。随后“我想看看杭州西湖”未返回匹配候选，批次整体记为失败；没有覆盖或重跑已成功步骤。
- `formal-1790007562763`：从未完成步骤续作，“西湖”并明确选取杭州市候选完成导航。Qwen 讲解任务 `dbe0266b-b0b7-4fbb-9f38-1159c057b846` 播放计数 1，收到实际开始和结束回执，服务端随后进入 feedback。ASR 使用宿主真实合成的公开测试句，经浏览器 MediaRecorder 编码并提交；MiMo 返回失败，页面保持地图与文字可用。该批整体也保留失败状态，不能把部分成功计为完整 E2E 成功。
- `asr-provider-probe.json`：同配置、同公开 WAV 的独立 MiMo 调用确认 HTTP 401 / `invalid_key`。未使用物理麦克风，未改动凭据，未以 mock 替代验收。
- `formal-1790007988513`：独立完成三次退出/重入，退出后地图和角色 DOM 移除、发送私密 close，重入各只有一个地图实例和一个角色并正常就绪。此结果证明 DOM 与协议生命周期，不声称测得 WebGL 显存长期无泄漏。
- `formal-live-1790008084050`：正式 `/live.html` 公开回复任务 `332ce16c-9ba0-4158-8b3f-05af59c676ca` 字幕出现、播放计数 0→1、最终 completed、task id 匹配、口型应用 368 次，无页面或播放错误。
- `artifacts/live-review/2026-09-21T16-29-02Z-9c5b0c66/summary.json`：8 个原有固定场景均通过，耗时 57.485s。feature=`live`、profile=`browser`、workflow fingerprint=`ab01edf5281f07ebbc015d264edeefc31ee3e44ebef342031f6a199f34b820bf`。未做 OBS 稳定轮次；本轮未建立相同 fingerprint 的历史耗时比较。

正式前端指纹为 `app-T4ZBtzwl.js` / SHA256 `e187150f5e0ab5f6ea59fbb1c3613b5e1a0e35d3e124fee49d47b00ddc4e4386`。首批上海截图经目视确认角色贴底、位于地图右下，讲解框无角色遮挡。

复合地名根因探针确认模型曾输出连续的“杭州西湖”，而 Photon 对“杭州 西湖”和连续名称有不同匹配。已在现有意图提示中要求层级地名用空格分隔，明确切换城市时放弃不兼容旧地区。`earth-query-segmentation-probe.json` 以真实 DeepSeek 和 Photon 验证“上海 青浦区”包含行政区候选、“杭州 西湖”包含杭州市西湖；未加入特定城市硬编码。最终冻结验证 `071aeb3aef04ceedc66cff966064d65cae13429951ba2f3d135cbf520f531a7e` 全部通过，正式后端按该结果更新。

首批青浦步骤选择的是青浦区内的国家会展中心，不能当作青浦行政区全景证据，最终批次已明确选择“青浦区，上海市，中国”。早期启动截图早于地球瓦片完成，画面为星空；`formal-1790009481362` 的真实相机探针证实默认俯仰为 -π/2、中心射线与地球相交、停稳截图显示完整地球，没有修改相机源码。因误判启动截图而中断的 `57c4d0b7b758` 保留为未完成批次。最终采集等待图层就绪后再截图。

### 最终部署与补验

最终 production run `anima-up-earth-3d5458b78104` 全部通过、exit 0。镜像 `sha256:c4e708a46764aae7c5db59da5d5c30b926626a45f0d6f841d01bb2d270d145b3`，源码指纹 `ad61ca8de73e086d487f03933b0be5bf772b26a50a69e31bee1c6906ab184f23`，容器内检索服务源码与冻结文件哈希一致。上一 run `anima-up-earth-be230afe1e05` 因构建助手创建时间捕获失败终止；遗留构建随后自然完成并退出，没有强杀或掩盖该失败。

`formal-1790010777784` 的六个步骤全部通过：延迟加载、真实地图与角色、上海、青浦行政区、淀山湖、完整“我想看看杭州西湖”输入。实际收到 446 个成功影像瓦片响应，页面错误 0。1280×800、1600×1000、1920×1080 三种视口的角色容器 bottom 与地图 bottom 差值均小于 1px，讲解框不与角色容器重叠，无水平溢出。初始地球停稳截图与四次导航截图保存于同一批次。

最终交互时段 01:12:50–01:15:56 的服务端日志 ERROR/Traceback 共 0 条；Anima/Redis healthy，Qwen/RVC 保留运行。此结论不解决已知 ASR 401 或上游 TTS billing。当前 TTS 的可用证据来自实际 Qwen fallback 播放。

阶段结论：M1–M3 的首版模块与文字闭环完成；M0 确认本版展示/检索组合与视觉禁用结论，尚未开通商业供应商或几何数据服务；M4 的讲解与可选失败回退完成，ASR 成功识别、授权视觉仍受外部条件限制；M5 已交付当前可用范围的源码、正式入口、原入口回归、性能与 PPT 证据，不把未测能力记作通过。

### 正式页面接管时序的测量边界

`formal-1790008453841` 使用 Playwright 自带无界面 Chrome 148，五次约一秒运镜后的点按接管均保持下一帧相机位置稳定。65 个 RAF 间隔 p95 为 350ms；输入到取消 p95 36.3ms，取消调用本身 p95 0.2ms，输入到下一帧观察 p95 149ms。独立渲染诊断确认该浏览器使用 SwiftShader 软件渲染；这组数据不可用于声称日常硬件渲染流畅，也不能与原型完整路线的基线直接比较。

硬件浏览器确认 Chrome 153 + RTX 5090 D v2。首次硬件采样 `formal-1790008768574` 因测试未等待新候选、快速命令触发控制限流而未完成，失败保留，不拼凑为五次成功。后续采样须等待当前请求的候选返回并遵守既有控制限流，不放宽产品限制。原始预测保持不变。

最终硬件批次 `formal-1790010833744` 使用 Chrome 153、NVIDIA RTX 5090 D v2 / D3D11、1600×1000、DPR 1，五次约一秒运镜后实际点按地图接管全部通过。663 个 RAF 间隔 p95 8.3ms、最大 136.3ms；输入事件到取消 p95 0.7ms、取消调用本身 0.2ms、下一帧确认停止 15.1ms，五次相机位置稳定、页面错误 0。原始样本见 `formal-map-timing.json`。这不是原型完整路线，也不包含输入硬件延迟；未测 GPU 呈现 FPS、长期尾延迟或同条件因果性能收益。未修改原预测。

本机诊断证据：`earth-build/earth-assets-context-probe.json`、`frontend-probe-proxy-result.json`、`production-runtime-attempt.json`。下列旧门禁与 IPC 故障记录保留为历史，不代表当前 Docker 状态。

### 历史门禁与运行时故障

以下为 2026-09-21 当时的故障交接记录，状态用语仅指当时，不代表目前运行情况。当前结果以前述 2026-09-22 验收为准。

最新结论由主任务回传：重启计划 `1b0933c37c82f332f7f34a9f4fcdd94ae6fe69add2b19add92385f3645186c55`（执行会话 `53645`）最终 affected **通过**。26 个 backend-full 分片合计 **5659 passed**，coverage 及所有其他组均通过；前端 **95 个测试文件、638 项测试通过**。配置风险对应的 backend-full 属于本次 affected 的合理必需范围。此结论完成源码验证，不代表 M5 整体完成或正式运行时可用。

门禁证据目录：`artifacts/test-impact/1b0933c37c82f332f7f34a9f4fcdd94ae6fe69add2b19add92385f3645186c55/results/`。这是主任务质量工具生成的既有结果，本支持任务只读引用，未修改该目录；与本报告第 3–4 节的原型性能证据分开。

保留失败与修复历史，避免用重试成功掩盖资源泄漏：

- 旧计划 `370b5e492702a215b7011a0b112666b0d591d5098c6b92640010b5f371701ab4` 的非 full 组和 backend-full 分片 1–10 通过；分片 11 打印 `218 passed in 20.04s`，进程却未正常结束，记录耗时 239.29s、终端状态 `in_progress`、退出码 `null`，分片 12–26 因此 blocked。该旧计划仍记录为失败。
- 已确认根因为与地球功能无关的预存路由测试资源泄漏：`tests/orchestration/server/test_routes.py` 中默认 `CommandInbox` 的 SQLite 资源未关闭。后端工作任务改为由异步 fixture 持有资源，在 `finally` 中关闭。
- 修复后同组 `218 passed in 20.59s`，进程自然退出码 0，无残留线程；随后最终 affected 重启计划通过。这里区分测试正文成功与进程正常退出，不改写旧批次记录。

正式运行时仍受 Docker Desktop IPC 阻塞。2026-09-21 晚续作确认旧进程已退出，正常启动依次遇到 `dockerInference` 与 `docker-secrets-engine/engine.sock` 无法访问错误。仅对经检查只含 IPC 的目录实施可逆改名，原对象均保留；没有删除、覆盖或修改 Docker 设置和数据盘。FileID 反查揭示 Codex 的 AppData 虚拟覆盖路径，真实 Secrets 旧目录随后已移动并保留到明确的应用缓存路径，但 19:59 的正常启动再次停在 Inference manager。

当前停止进一步隔离与重复启动。下一步是在本轮 Docker 残留进程清理完成后，从 Windows 开始菜单独立启动 Docker Desktop，以排除当前调用环境的影响；该步骤尚无成功证据。日志曾出现恢复出厂设置记录，但触发来源未知，用户明确表示没有操作 Docker，本任务没有执行该操作。尚未执行 `anima-up`，没有本次生命周期 run ID。正式 Dashboard、实际语音播放链路，以及现有 live/review 的真实浏览器回归保持阻塞、未完成；不作运行成功声明。

续作证据保存在前述本机 `earth-build/` 目录：`docker-recovery-resume.json`、`docker-second-ipc-identity-detail.json`、`docker-real-ipc-isolation.json`、`docker-ipc-accepted-backup.json` 和 `docker-after-real-isolation-errors.log`。隔离对象的实际位置及回滚映射以该备份记录为准，不能仅凭逻辑路径判断移动成功。正式验收脚本仅补齐同源 Socket.IO token 鉴权并通过语法检查，未执行浏览器验收，也未改动产品源码。

20:02:27 收尾核验：Docker 进程为 0，无本轮启动/停止 CLI 残留，`com.docker.service` 为 Stopped/PID 0，三处隔离备份全部保留。正常 stop 失败后，仅清理了 PID、创建时间和完整命令行均匹配的本轮进程。交接证据为 `docker-final-handoff.json`、`docker-final-cleanup-identities.json`；现等待从 Windows 开始菜单独立启动 Docker Desktop 的结果。

本轮只更新已知结果，不新增采样、不重做演示稿、不作整体验收或正式运行成功声明。

效率修正：首次采样受共享工作区变更影响，因此后续采样固定为已提交版本的隔离源，并在发起浏览器采样前确认独立端口实际就绪。延续已成功批次，不因后续启动失败重跑成功路线。

## 6. 演示稿交付

文件：[Animetta-地球探索-正式验收-20260922.pptx](C:/Users/30262/.codex/visualizations/2026/09/20/01a0bf82-74ed-71b1-bbda-d90278e9d1bc/earth-output/Animetta-地球探索-正式验收-20260922.pptx)。SHA256：`b9fdb227fda710b618e15655206891093984d21e6c9709073d52c7101bf6c6f5`，9,371,136 字节。

10 页包含正式操作截图、模块边界、原型局部性能对比与能力限制，保留 3 张原生可编辑表格。包结构、版式、字体策略、原生表格与 Artifact Tool 回读检查通过，最终文件逐页渲染目视检查完成。未在 PowerPoint 原生程序中验证。检查回执 `earth-build/delivery-deck-validation.json`，预览 `delivery-deck-final-rendered/`。

先前原型稿和带提前启动截图的中间稿仅作历史文件保留，本节链接才是最终交付。原始版本 Vite PID 30156 及子进程已停止，3012 不再监听；隔离源与原始证据保留。正式生产实例继续运行供用户使用。

## 7. 效率复盘

浪费路径：提前截取启动帧后误判相机朝向，导致一次门禁中断；采样选择器含糊又选中行政区内的机构。根因是验收驱动缺少“瓦片停稳”和“精确行政候选”的断言。改进已固化到本次外部验收脚本：先核对真实 SDK 相机/中心射线并等待图层，再匹配完整行政候选、等待本轮响应，性能采样先确认硬件渲染并遵守既有限流。未给产品增加症状补丁，也未改变限流或质量映射。下次先完成这些驱动检查，再冻结一次源代码门禁和运行验收。
