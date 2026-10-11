# 阶段 0 运行基线记录

唯一执行方。本轮只做原实现 `b422c70a835564a244e9bd3bd2058b699f14d948`；不安装依赖、不编辑产品源码、锁、配置、测试或训练文件，不提交、不推送。

## 冻结输入

2026-10-11 02:41:47 UTC 已完成 `git archive`，2092 个跟踪文件，不包含未提交训练内容。归档 SHA-256：`aa04b84df75465565c68d7152f8161a01e78e81846184093da7e82108efaa721`。

冻结副本：`C:/Users/30262/AppData/Local/Temp/anima-deployment-core-20261011-b422c70a-3x_hbvvp/source`。完整逐文件哈希：副本父目录 `frozen-input.json`。环境值在同一控制子进程从原 `.env` 安全导入，仅保存文件摘要，不落盘密钥。`docker compose config --quiet` 通过。

固定 production profile、Compose 项目 `anima`、真实 HTTP `http://localhost`、端口 80/12394、独立镜像标签 `animetta:deployment-core-baseline-b422c70a`。保留现有命名卷与 Docker 缓存；不手工修改运行数据。构建输入与测量驱动来自冻结副本。

## 已完成

- 读取 root、operate-anima-runtime 及 commands/recovery 引用，Python 3.13.14 断言通过。
- Docker Desktop 4.92.0 / Engine 29.8.0 可访问，原应用静态入口正常、动态 health/ready 502；该现有容器不计入启动样本。
- 宿主 Qwen/RVC 均未运行；GPU RTX 5090 D v2，总显存 24455 MiB，初始使用 3376 MiB、空闲 20660 MiB。GPU PID 与完整命令行保存在 runtime-baseline.json。
- 未发现其他运行生命周期、训练或批量推理进程；应用和 Minecraft 是既有进程，未由本任务直接停止。
- 已检查 benchmark_startup.py、benchmark_host_tts.py、baseline_golden_path.py；复用冻结的 benchmark_startup worker。安装基准由主 Agent 负责，本执行方不重复。

## 当前 run 与续接

`base-qwen-cold-20261011-01`：通过冻结 benchmark worker 调用 runtime_lifecycle.py 的 `host-tts-up`。测量 JSON 和外层日志：副本父目录 `measurements/base-qwen-cold-20261011-01.{json,log}`。自动生命周期证据：项目 `artifacts/iteration-plans/base-qwen-cold-20261011-01/`。

先检查原 worker 是否仍运行与 JSON/生命周期结果。正在执行时不再启动另一个生命周期命令；若终态失败只按 recovery 分支诊断，不重跑终态动作。Qwen 准备成功后才开始原应用启动样本，将构建、模型冷准备、HTTP 就绪、浏览器就绪、首轮真实对话和实际播放分开记录。未测项保持 null/缺测。

启动 `anima-down`，run ID `b-dc0-down01`；冻结 production 默认链保持不变，云密钥均存在。

启动 `anima-up`，run ID `b-dc0-app01`；冻结 production 默认链保持不变，云密钥均存在。

Qwen 冷准备 run 通过：总 97.7777092 s；host-tts-start 97.3275172 s，preflight 0.4092232 s。实际 HTTP ready 与声线身份匹配。注意该准备与初始镜像构建阶段曾和主 Agent 安装测量重叠，独立报告，不用来计算干净运行性能收益。主 Agent 随后报告冷暖安装各 3 完成；后续应用样本需确认无安装进程。

主 Agent 的 source-baseline.zip 与本运行归档 SHA-256 完全一致；本 run 继续复用原临时副本。production 保持 dashscope-local-failover、long_term_memory_mode=off、mimo-asr/mimo-vad；所需云密钥存在。

续接检查点：exec session `10601`，冻结 benchmark worker PID `32808`，BuildKit 包装进程 PID `3576`，当前 run `b-dc0-app01`。以实际创建时间/完整命令行与自动租约核对，不能仅凭 PID 续接或清理。镜像系统包解包持续进展，前端构建已完成；不因构建耗时较长启动第二个构建。

为遵守用户要求的采样隔离，2026-10-11T03:02:05.782986+00:00 暂停唯一测量驱动 PID 32808（先核对完整命令行/创建时间；不是服务或 BuildKit 进程）。原 BuildKit 子进程与租约继续运行；不从主工作区启动，不创建新 run。等待主 Agent 明确通知 core-install exec session 82889 完成后，核对保存的精确 worker_identity 再恢复同一驱动。等待耗时单列，从应用启动计时中排除。

主 Agent 通知 session 82889 exit0，核对系统无 uv.exe；2026-10-11T03:02:47.422960+00:00 按保存的 PID/创建时间/完整命令行恢复原驱动。隔离等待 41.639974 s 单列，不计入应用启动。继续原 b-dc0-app01，没有新建生命周期 run 或重启构建。

首次真实 Dashboard 对话 b-dc0-first-dialogue01 完成。状态 partial，首次回复 None s，浏览器原生非零音频完成 False；live 持久计数/任务关联 False。详见 runtime-baseline.json.first_real_dialogue；未冒充物理扬声器听感。

b-dc0-app02 通过；应用启动步骤至 HTTP ready 30.485048 s，容器 StartedAt 至 HTTP ready 18.386851 s，Qwen PID [14240, 16104]。原始测量和自动步骤证据已保存；源码/镜像输入不变。

串行测量控制器在 app02 成功后暂停于竞争检查：匹配的是主 Agent mypy/quality 的文件参数，而非执行 lifecycle。校正为核对实际执行脚本位置；保留原匹配完整命令行，不停止质量进程，继续未执行的 app03/re01–03，不重跑成功样本。主 Agent affected 与这些样本有 CPU 负载重叠，最终比较需注明。

b-dc0-app03 通过；应用启动步骤至 HTTP ready 30.105647 s，容器 StartedAt 至 HTTP ready 17.867574 s，Qwen PID [14240, 16104]。原始测量/自动证据保留。

b-dc0-re01 通过；应用启动步骤至 HTTP ready 28.410359 s，容器 StartedAt 至 HTTP ready 16.293785 s，Qwen PID [14240, 16104]。原始测量/自动证据保留。

b-dc0-re02 通过；应用启动步骤至 HTTP ready 28.280524 s，容器 StartedAt 至 HTTP ready 16.351735 s，Qwen PID [14240, 16104]。原始测量/自动证据保留。

b-dc0-re03 通过；应用启动步骤至 HTTP ready 27.829793 s，容器 StartedAt 至 HTTP ready 15.77038 s，Qwen PID [14240, 16104]。原始测量/自动证据保留。

修正公开角色探针 b-dc0-public-dialogue02 完成：blocked；发送前 Dashboard Socket.IO 握手 None，first reply None s，live 持久播放 None。原 first-dialogue01 失败不覆写。

正式 auth.token 分支角色探针 b-dc0-socket-role03：passed；task d80de6ab-a51b-4f04-859a-e1484d51f28a，首回复 2.892 s，live 持久播放 True。此证明正式 Socket→角色图→live 链，Dashboard 浏览器账号登录/可写Socket仍独立缺测。

本任务 RVC 收尾 b-dc0-rvc-stop：规范 host-rvc-stop passed；精确原 PID/创建时间/模块命令已核对，剩余 RVC []，8769 开放 False；Qwen [14240, 16104] 保留。

## 阶段0最终运行基线

运行输入已冻结且重新核验2092文件均未变；b422c70a源码、production、原env摘要、独立镜像和真实URL完整保存。主工作区变动未参与本基线运行。

规范命令模板（既有测量worker内部只调用 runtime_lifecycle.run_bounded_operation）：

```text
py -3.13 C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-b422c70a-3x_hbvvp\source\scripts\benchmark_startup.py worker --root C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-b422c70a-3x_hbvvp\source --operation <operation> --run-id <run-id> --phase before --artifacts-root C:\Users\30262\Project\Anima\artifacts\iteration-plans --output C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-b422c70a-3x_hbvvp\measurements\<run-id>.json
```

原始测量：冻结副本父目录 measurements/*.json 和 *.log；自动证据：原项目 artifacts/iteration-plans/<run-id>/，包含 plan、step checkpoint/window result、命令/HTTP日志、构建租约与收据。未手改自动证据。

| 场景 | run ID | 应用启动步骤至HTTP ready秒 | 容器StartedAt至HTTP ready秒 | 负载限制 |
|---|---|---:|---:|---|
| application_cold | b-dc0-app01 | 41.068663 | 17.476925 | quality CPU重叠，无安装进程重叠 |
| application_cold | b-dc0-app02 | 30.485048 | 18.386851 | quality CPU重叠，无安装进程重叠 |
| application_cold | b-dc0-app03 | 30.105647 | 17.867574 | quality CPU重叠，无安装进程重叠 |
| application_restart_qwen_reused | b-dc0-re01 | 28.410359 | 16.293785 | quality CPU重叠，无安装进程重叠 |
| application_restart_qwen_reused | b-dc0-re02 | 28.280524 | 16.351735 | quality CPU重叠，无安装进程重叠 |
| application_restart_qwen_reused | b-dc0-re03 | 27.829793 | 15.77038 | quality CPU重叠，无安装进程重叠 |

冷启动 n=3，中位30.485048 s，范围30.105647–41.068663；复用Qwen重启 n=3，中位28.280524 s，范围27.829793–28.410359。容器实际进程启动计时另列。应用冷是新容器/进程，保留磁盘/OS/Docker缓存及现有模型/数据卷；不是机器冷启动。所有高值保留，不宣称干净环境启动收益。

Qwen冷准备 base-qwen-cold-20261011-01 总97.7777092 s；原模型文件和OS缓存保留，且与安装负载重叠，仅独立记录。首个构建 b-dc0-app01：执行反馈收据1034.3201068 s，timed subprocess 1033.8639524 s；和安装重叠，不作构建收益归因。worker整段总时长1126.4299073 s包含构建/宿主准备/反馈续接/隔离等待/页面验收，不能当应用启动时间。

镜像 sha256:54fd13a265b9b01d177fa3332fb7ed7ecb84b6f6b0c80b9342e1825615b1d9b5，未压缩体积 1447480052 bytes；启动ready后端RSS六快照中位 205.2109375 MiB，真实对话后 209.8515625 MiB。GPU前后快照、PID与完整命令行保留；未连续测峰值，不能把总显存当空闲或N/A当零。

真实角色+播放：b-dc0-socket-role03，task d80de6ab-a51b-4f04-859a-e1484d51f28a；正式 auth.token→chat:developer_text→角色LangGraph→实际DeepSeek回复/宿主Qwen→真实live。首回复2.892 s，原生音频首次启动4.435 s；live持久count增加/任务吻合/completed，原生非零PCM在running AudioContext中自然ended，无浏览器错误。/api/stats/live同trace的真实回合success、工具0次，声线 tosaka-rin-cn/模型revision与原身份一致。未声称人耳听到物理扬声器。

UI限制：保留 first-dialogue01 原超时和 public-dialogue02 原UNAUTHORIZED。read-only dashboard-network04 实测输入框已mount、HTTP auth/session200、WS HTTP101，但无Authorization/Cookie，发送40后服务端返回44 UNAUTHORIZED。这是bearer-only浏览器探针缺少账号Cookie的认证限制；当前env无账号密码，不改用户账号/配置，不重跑终态探针。正式auth.token分支真实链已通过，但Dashboard账号登录与UI可写Socket仍缺测。DashScope主连接失败使用Qwen fallback，基线忠实保留。

RVC本任务从无实例启动，仅用于旧默认生命周期；host-rvc-stop run b-dc0-rvc-stop通过，核对原PID1824/7508创建时间和完整模块命令后停止，进程消失/8769不可用。Qwen14240/16104全样本、真实对话、RVC停止后创建时间/PID/声线保持；其他服务未停止。

## 已完成与下一步

基线应用3+3、真实角色回复与live实际播放、RSS/镜像/GPU快照、输入与资源指纹已完成。证据足够保留冻结流程/功能比较；CPU负载与TTS主链故障使干净性能因果比较不足。主Agent的corrected affected仍待最终通过，当前仍是旧基线镜像；持有Qwen，不部署核心，不重复成功步骤。下一步由用户/主Agent给最终gate及冻结输入安排后，唯一运行执行方再测core。

按simplify以样本摘要引用完整raw结果，字段区分应用/构建/模型/HTTP/浏览器/首回复/播放，没有删除原始高值或失败。效率反思：竞争守卫应认实际argv执行入口而非文件参数；浏览器探针先核对精确正式入口、Socket协议及认证，使用network帧和持久播放证据。此次仅写任务记录，未更改规则/产品/测试/锁或训练文件。

最终只读复核：JSON解析/播放任务关联/2092原始文件哈希/原env摘要通过；无活跃生命周期进程。RVC停后HTTP ready与memory_runtime仍true；live实际持久计数0→1、任务 d80de6ab-a51b-4f04-859a-e1484d51f28a、状态completed。两个获准文档git diff --check通过，均未提交/推送。

## Core输入冻结准备（尚未获准生命周期）

2026-10-11T03:35:24.357755+00:00：从原b422c70a归档解压独立副本，按task-paths.json的39个产品/测试/锁/前端/开发指南文件做字节原样overlay，未覆盖未提交train/songs或其他未列工作区文件。33个性能记录不进入源码overlay，保持在原记录目录。

Source：`C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-51v0a4ti\source`；archive：`C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-51v0a4ti\source-core.zip`；SHA256：`a65ba69cffac97734672d5511b5b3843672e1a9c8f9a25f7fc4d2d412e732521`；source tree SHA256：`5cd066a734c5ccf1dceaec926f315477f06441213a7510086adf5666dc1cc629`；逐文件清单：`C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-51v0a4ti\frozen-input.json`，2097文件。task-paths摘要：`efedcb166e3436519b6eda4b3eaef3da07200bf07f087464478e3d1757c3747c`。归档重新逐文件校验通过，复制前后任务输入字节一致。

固定project=anima，profile=production，HTTP/backend=80/12394，URL http://localhost/dashboard 与 http://localhost/live.html，独立image tag `animetta:deployment-core-core-5cd066a734c5`。原.env摘要与基线一致，仅在本专用子进程安全导入，未复制.env、未落盘密钥。只读 docker compose config --quiet exit0。

Qwen14240/16104的PID/创建时间/完整命令保持；本轮无生命周期动作，未构建/启停/部署。父gate Plan30b0164e525c session42117仍pending；必须收到允许core生命周期及终态pass证据，且复核当前overlay/task-path哈希与候选一致后才运行。输入若变化，先重新冻结，不执行过期副本。

### Core gate 纠正与测试 overlay 等待（2026-10-11T03:43:18.837414+00:00）

- 父侧更正第3轮 gate 实际 plan hash 为 `735306eccb10`；前18/26 backend-full 分片通过，第19分片两条旧 smoke 预期正由父侧调整。此信息是父侧报告，尚非 gate pass。
- 保留候选归档 `A65BA69CFFAC97734672D5511B5B3843672E1A9C8F9A25F7FC4D2D412E732521`，zip 和冻结 manifest SHA256 复核通过；原有39份 overlay 与当前工作区逐文件 SHA256 仍一致。
- 当前 task-paths 仍为72项（SHA256 `efedcb166e3436519b6eda4b3eaef3da07200bf07f087464478e3d1757c3747c`），新增路径 []、移除路径 []；尚未列入新增 smoke 测试。未提前复制未冻结输入。
- 本轮生命周期动作为空；旧基线成功样本不重跑，Qwen 未由本轮停止或重启。保留上次成功运行 `b-dc0-re03` 与真实对话/播放证据 `b-dc0-socket-role03`。
- 下一步：父侧最终清单纳入两份 smoke 测试后，另建测试 overlay 修订归档并复核产品文件保持 A65 候选字节不变；仍须等待明确“允许core生命周期”及门禁通过证据。

### Core 输入修订：仅两份 smoke 测试及质量映射（2026-10-11T03:46:33.991493+00:00）

- 父侧明确授权复制 `tests/smoke/test_health_check.py`、`tests/smoke/test_main_path.py`、`tooling/quality.yml`；3个目标测试通过为父侧报告，本执行方未重复验证。
- 从保留的 A65 原候选 zip 重建任务专属副本，只覆盖这3份文件。全部2097份文件与 zip 内容逐文件 SHA256 校验通过；差异恰为上述3份，其余2094份完全一致。产品输入字节未变。
- 新 source：`C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r2-dptpv3uv\source`；新 zip：`C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r2-dptpv3uv\source-core.zip`。zip SHA256 `105a031903386881735832b92e1913b92ab3605991a5974ad36de4bc170d9434`，source tree SHA256 `35f0f16239b61cd1740c7d71417d44d81a6bec37cdc878877e36c262e44a8192`。
- 逐文件 manifest：`C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r2-dptpv3uv\frozen-input.json`，SHA256 `902bfb666ea59e8d7138ab37e503a27cdd3629e344c6472f5af4c4cf8b14890f`。task-paths 74项，SHA256 `04d1e41d0b8bb9bfbb8e2154bc74845465b0b07bf7f95c290c96e66cee8cdf49`；overlay 累计41项。原 A65 zip 与 manifest 均未修改。
- 新独立镜像 tag 仅规划为 `animetta:deployment-core-core-35f0f16239b6`，未构建。原 .env 只复核 SHA256 一致，未复制或输出值；不含用户未提交训练、songs、未列入工作区文件。
- 最终 affected plan `fc9b27b46317` 已由父侧报告启动，当前 pending，未获“允许core生命周期”。本轮 Docker/生命周期命令为空，不停止或重启 Qwen。
- 下一步：交付必要的小型原始证据/逐文件清单；最终门禁通过并明确许可后再执行唯一 core 运行验收。

### 阶段0证据交付索引（2026-10-11T03:49:24.341131+00:00）

- 按额外文档授权新增 `runtime-evidence-index.json` 与 `runtime-evidence/`。仅复制已有原始 baseline、core-r2 冻结 manifest（包含逐文件 SHA256），复制后逐字节及 SHA256 核对一致；两份共 521734 bytes。
- 全部21份 measurement JSON 的原始值已嵌入 `runtime-baseline.json`；索引记录原始文件 SHA256、canonical JSON SHA256 和 JSON Pointer，未重复复制。原 A65 文件哈希清单可由 core-r2 manifest 对三项差异恢复，恢复 tree hash 校验通过。
- 不复制 .env、source zip、镜像、庞大日志或任何自动 artifacts；待交付 manifest 对原 .env 已有密钥值做仅内存扫描通过，未写入或输出密钥。已有真实对话、网络拒绝和持久播放证明仍保留在 baseline 内。
- 本轮生命周期/重测为空；core 输入已冻结，最终 affected `fc9b27b46317` 仍待父侧终态及明确授权。

### Core 验收证据要求补充，尚未执行（2026-10-11T03:50:50.026546+00:00）

- 核心生命周期仍未授权；以下是获准后的必需验收要求，不能计作已获运行证据。冻结输入及原A65/revision归档不变，本轮无生命周期或探针执行。
- 在真实 core 容器只读记录 image/container 身份、安装包 metadata 和模块 discoverability，证明无 bilibili-api-python、langchain-community、Torch、Transformers；不安装依赖、不导入GPU包。
- 原始 /ready 必须证明 ASR/VAD disabled 且 required=false，runtime memory_v2 ready；沿用正式 /dashboard、/live.html 并核对真实资源指纹。
- 用既有正式 auth.token 角色协议发起单轮真实请求，保留 LangGraph→原Qwen→live 的同任务证据、持久播放计数/任务ID、非零音频与自然ended；Qwen PID、创建时间、声线模型合同保持。
- Live2D模型运行时加载及口型证据单独记录，尽可能收集；HTTP/模型资源200不足以验收，不能获得则如实缺测。保留旧Dashboard登录限制，不改账号、不重跑终态失败探针。
- 默认RVC无启动、预检、探测步骤，8769不可用时仍启动为既定最终边界。阶段0成功样本不重测。

### 获准后同会话连续性验收补充（2026-10-11T03:54:57.093725+00:00）

- 当前仍未获 core 生命周期许可，本轮不执行对话或生命周期。冻结源码、raw副本及其行尾/原SHA256均不变。
- 性能首轮沿用 baseline 正式角色提示；其后尽可能复用同一 authenticated socket、逻辑graph会话、角色与persona，另做两轮：先告知本次唯一普通验收代号，再问刚才代号（追问不包含答案）。
- 保留真实请求/回复、会话与task/thread标识、代号比对和可得live持久播放证据；回复必须经真实LangGraph/Qwen链，失败或无法保持会话则如实记录。
- 保持 production long_term_memory_mode=off，不修改用户数据库、不手写data；此项仅证明短期上下文连续性，不宣称长期写入。

- Core run `c-dc2-down01` operation `anima-down` started 2026-10-11T04:05:42.904492+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc2-app01` operation `anima-up` started 2026-10-11T04:06:02.135260+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc2-app01` application_cold: passed; application start→HTTP ready 34.563128s; container start→ready 11.740551s; backend RSS 196.672MiB; image sha256:bff76b080fc6a12a2e9d520e0cc4913ac568e9c08df08b95b254825941b83206 (1274642946 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc2-app02-down` operation `anima-down` started 2026-10-11T04:09:54.649450+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc2-app02` operation `anima-up` started 2026-10-11T04:10:37.967639+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc2-app02` application_cold: passed; application start→HTTP ready 22.960424s; container start→ready 10.945618s; backend RSS 196.809MiB; image sha256:bff76b080fc6a12a2e9d520e0cc4913ac568e9c08df08b95b254825941b83206 (1274642946 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc2-app03-down` operation `anima-down` started 2026-10-11T04:11:15.761239+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc2-app03` operation `anima-up` started 2026-10-11T04:11:27.000438+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc2-app03` application_cold: passed; application start→HTTP ready 22.680730s; container start→ready 10.658332s; backend RSS 196.691MiB; image sha256:bff76b080fc6a12a2e9d520e0cc4913ac568e9c08df08b95b254825941b83206 (1274642946 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc2-re01-down` operation `anima-down` started 2026-10-11T04:12:05.691188+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc2-re01` operation `anima-up` started 2026-10-11T04:12:17.158936+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc2-re01` application_restart_qwen_reused: passed; application start→HTTP ready 24.364396s; container start→ready 12.262427s; backend RSS 197.020MiB; image sha256:bff76b080fc6a12a2e9d520e0cc4913ac568e9c08df08b95b254825941b83206 (1274642946 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc2-re02-down` operation `anima-down` started 2026-10-11T04:12:57.137529+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc2-re02` operation `anima-up` started 2026-10-11T04:13:08.660859+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc2-re02` application_restart_qwen_reused: passed; application start→HTTP ready 24.469992s; container start→ready 11.854578s; backend RSS 196.484MiB; image sha256:bff76b080fc6a12a2e9d520e0cc4913ac568e9c08df08b95b254825941b83206 (1274642946 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc2-re03-down` operation `anima-down` started 2026-10-11T04:13:49.733302+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc2-re03` operation `anima-up` started 2026-10-11T04:14:01.217330+00:00; canonical lifecycle worker on frozen r2, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc2-re03` application_restart_qwen_reused: passed; application start→HTTP ready 23.355731s; container start→ready 11.417481s; backend RSS 197.223MiB; image sha256:bff76b080fc6a12a2e9d520e0cc4913ac568e9c08df08b95b254825941b83206 (1274642946 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core real role probe `c-dc2-role01` finished 2026-10-11T04:15:49.371948+00:00: blocked; task `d1b12f4a-b302-425d-ba0b-0f6c2a62a8a0`, reply 3.24s/native audio Nones; persistent playback True, natural nonzero audio False; Live2D model runtime loaded True/same-task mouth True; continuity None; graph task outcomes True. Qwen same identity/PID, RVC8769 unavailable. Raw JSON `C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r2-dptpv3uv\measurements\c-dc2-role01.json` SHA256 `b9c6c9e356cfb887d02fca510e3f034d9fea784bb71906f5ecdf215e9f8c1966`; no mock, no account/data edits.

### Role01 blocked 根因确认（无产品/生命周期修改）

- 原role01/raw/sourcehash保持。实际音频事件是完整 chat:audio_with_expression，legacy play4次、buffer source0次；原探针只对PCM BufferSource采native start/RMS/ended，因此漏采HTMLAudio路径并跳过连续性。
- 冻结源码与真实容器class核对：RemoteTTS supports_streaming=false，FailoverTTS=true；tts_node234按该标记分支，direct synthesize完整音频→playback.ts new Audio/blob/play/onended→live持久count/completed；基线failover→PCM BufferSource流。
- 已保存诊断 core-role01-diagnosis JSON与调用链文件哈希。原始首回复3.24s、native-start缺测保持；不伪造WebAudio事件。无需产品修复或生命周期变化。
- 下一步只建立新更正探针c-dc2-role02，实际捕获HTMLMediaElement原生playing/ended/时间推进/时长及原Blob非零PCM，同task关联且无中止。原buffer断言仍保持。

- Core real role probe `c-dc2-role02` finished 2026-10-11T04:22:32.601679+00:00: passed; task `162f014d-d35a-4c80-bf95-bd7e74f817bc`, reply 3.453s/native audio 8.736s; persistent playback True, natural nonzero audio True; Live2D model runtime loaded True/same-task mouth True; continuity failed; graph task outcomes True. Qwen same identity/PID, RVC8769 unavailable. Raw JSON `C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r2-dptpv3uv\measurements\c-dc2-role02.json` SHA256 `1f0bed3c275dfa306e0d04e23e3ada24e8f2204a555b2da7cb6737a4858c6d90`; no mock, no account/data edits.

### role02连续性审计与单次普通事实更正

- 原role02及拒绝失败字节保留。实际thread/channel均vVwquNqnouN1WDNuAAAL，authoritative scope为livestream:8610d8b5-8b38-47d0-a91d-2db396beccc3；set窗口2→3，recall3→4。task UUID表示新turn，不重置此scope。普通用户chat与developer前端均保留稳定conversation，仅来源/公开隐私策略不同。
- 原基线相同prompt规则明确禁止公开验收标记，允许回答所需普通事实；原代号探针触发此保护，不能据此判记忆丢失。新增一次c-dc2-continuity03仅验证非敏感午饭事实，不改策略/账号/数据库/产品或生命周期。
- 附带发现工具边界矛盾：session.py167-191从tools.yaml获取true，仅golden覆盖；未采用production canonical runtime.enable_tools=false。真实graph创建日志tools enabled/node registered，实际本任务工具调用0。最小修复需父侧应用canonical开关于orchestrator创建并目标回归/重冻，执行方未改源码或重启。

- 独立continuity-only `c-dc2-continuity03`终态passed；实际thread/channel `-Sqh1Sfp9MFRsQJwAAAP`，window [4, 5]→[5, 6]，两轮真实task outcomes success=True。原样事实匹配=True，追问不含答案，两轮真实native自然ended；raw `C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r2-dptpv3uv\measurements\c-dc2-continuity03.json` SHA256 `dc8c2e348ea0cbfc9f303ed914d0e908a42da7b5cb570a6391e01e24ba9c8ba7`。保持role02拒绝/失败，不改变人格/记忆off/数据库/产品/镜像/Qwen。工具开关边界另待父侧处理。

### r2测量收尾：保留原样，等待父侧r3工具开关修复

- 应用启动3样本[34.563128, 22.960424, 22.68073]，中位22.960424s；复用Qwen重启3样本[24.364396, 24.469992, 23.355731]，中位24.364396s。原baseline quality CPU重叠，不能宣称干净启动提速。构建145.4406274s保留缓存且旧build与安装/质量重叠，无构建收益归因。
- 镜像1274642946bytes，RSS ready中位196.75MiB；GPU只有快照，无实测峰值。角色role02真实native WAV/Live2D通过；普通事实continuity03同thread两轮通过，原role01漏采blocked与role02验收标记拒绝失败均不覆盖。
- runtime-core记录r2真实tools激活矛盾与最小父侧修复需求；此候选不能计作最终阶段2完整发布通过。r3需新冻结/门禁/明确生命周期许可，不能继承r2样本作为新实测。
- 源2097文件/原env/归档逐字节哈希复核通过，当前实际image仍sha256:bff76b080fc6a12a2e9d520e0cc4913ac568e9c08df08b95b254825941b83206；Qwen14240/16104创建时间/完整命令行/voice合同相同，RVC8769不可用。没有本任务生命周期/浏览器探针残留。未修改产品/测试/配置/锁/账号/用户数据库，未提交推送。
- 交付raw与探针仅二进制复制；索引是r2checkpoint，最终index仍待r3记录完成，不含自引用SHA。下一步保持服务，等父侧新许可。

### r3独立候选输入冻结（尚无生命周期授权）

- 基于r2已冻结zip，仅覆盖`session.py`和`tests/orchestration/server/test_session.py`；与r2差异严格为这2项，其余2095份源码、40份原overlay逐字节SHA一致。overlay42项、taskpaths75项、source2097文件；不含未提交train/songs/未列入输入或.env。
- source `C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r3-t8urbyf1\source`，archive `C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r3-t8urbyf1\source-core.zip` SHA256 `e55459ef84e51dc3d71daa75b169daf2f02f176c1874ea052977333182abfbfe`，tree `e9a02ad56a75e5f0fba4b3b69dc62d17d97644b92ae475a4615335272567077d`；manifest `C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r3-t8urbyf1\frozen-input.json` SHA256 `111d0f30875020de9a54b9ae492ea49a6916b990df30a213568c71c916fc957d`。taskpaths SHA256 `2fac8aba630fc2f0ad676338192ff3c49128ebfe72d2f9a33a52468d86f11299`。
- 计划独立tag `animetta:deployment-core-core-r3-e9a02ad56a75`，未构建、未compose预检、未启动；同project/url/profile/端口，原.env仍仅专用子进程安全导入，原env哈希一致。r3必须新gate终态pass及明确许可，不能沿用r2 gate。
- 普通事实03已终态passed，未重复。r2不可变记录SHA4122c8efd519e7145928733c44bb201c717659e28ed7b177d9f3775ad4d32dd1、role01/02/03 raw及原始probe均保持；当前Qwen/镜像无生命周期变化。下一步等待父侧新许可。

- Core run `c-dc3-down01` operation `anima-down` started 2026-10-11T04:52:26.642798+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc3-app01` operation `anima-up` started 2026-10-11T04:53:23.755067+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc3-app01` application_cold: passed; application start→HTTP ready 25.256353s; container start→ready 12.017030s; backend RSS 197.289MiB; image sha256:2947e4318fff367438fe98ef98bb006825dc1772eaf7a1c60f05efddbd978d25 (1274643121 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc3-app02-down` operation `anima-down` started 2026-10-11T04:55:48.569112+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc3-app02` operation `anima-up` started 2026-10-11T04:56:00.021469+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc3-app02` application_cold: passed; application start→HTTP ready 22.853917s; container start→ready 10.706818s; backend RSS 196.781MiB; image sha256:2947e4318fff367438fe98ef98bb006825dc1772eaf7a1c60f05efddbd978d25 (1274643121 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc3-app03-down` operation `anima-down` started 2026-10-11T04:56:38.805139+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc3-app03` operation `anima-up` started 2026-10-11T04:56:50.217114+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc3-app03` application_cold: passed; application start→HTTP ready 22.902177s; container start→ready 10.819067s; backend RSS 196.973MiB; image sha256:2947e4318fff367438fe98ef98bb006825dc1772eaf7a1c60f05efddbd978d25 (1274643121 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc3-re01-down` operation `anima-down` started 2026-10-11T04:57:29.216079+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc3-re01` operation `anima-up` started 2026-10-11T04:57:40.722867+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc3-re01` application_restart_qwen_reused: passed; application start→HTTP ready 22.865988s; container start→ready 10.819020s; backend RSS 196.930MiB; image sha256:2947e4318fff367438fe98ef98bb006825dc1772eaf7a1c60f05efddbd978d25 (1274643121 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc3-re02-down` operation `anima-down` started 2026-10-11T04:58:19.311782+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc3-re02` operation `anima-up` started 2026-10-11T04:58:30.684402+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc3-re02` application_restart_qwen_reused: passed; application start→HTTP ready 22.902588s; container start→ready 10.816603s; backend RSS 196.945MiB; image sha256:2947e4318fff367438fe98ef98bb006825dc1772eaf7a1c60f05efddbd978d25 (1274643121 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core run `c-dc3-re03-down` operation `anima-down` started 2026-10-11T04:59:09.540125+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core run `c-dc3-re03` operation `anima-up` started 2026-10-11T04:59:21.104448+00:00; canonical lifecycle worker on frozen r3, Qwen ownership preserved, 8769 unavailable, no quality/install competitors.

- Core `c-dc3-re03` application_restart_qwen_reused: passed; application start→HTTP ready 23.360285s; container start→ready 11.104993s; backend RSS 197.070MiB; image sha256:2947e4318fff367438fe98ef98bb006825dc1772eaf7a1c60f05efddbd978d25 (1274643121 bytes). Same Qwen14240/16104/identity; no RVC step/probe,8769 unavailable; no quality/install overlap. Baseline CPU overlap prevents clean-start speedup attribution.

- Core real role probe `c-dc3-role01` finished 2026-10-11T05:01:21.977248+00:00: passed; task `3961693d-3b92-42b3-a45b-867a5a4a4b09`, reply 3.122s/native audio 8.518s; persistent playback True, natural nonzero audio True; Live2D model runtime loaded True/same-task mouth True; continuity passed; graph task outcomes True. Qwen same identity/PID, RVC8769 unavailable. Raw JSON `C:\Users\30262\AppData\Local\Temp\anima-deployment-core-20261011-core-r3-t8urbyf1\measurements\c-dc3-role01.json` SHA256 `64fe5b60be14a296368d58e3b9fb2761f7b047e8daf9563163675ae4ed474373`; no mock, no account/data edits.

### r3最终运行验收完成（2026-10-11T05:03:12.730947+00:00）

- 新r3启动3样本[25.256353, 22.853917, 22.902177]，中位22.902177s；原Qwen复用重启3样本[22.865988, 22.902588, 23.360285]，中位22.902588s。r2全部历史记录/失败不覆盖、不计入r3。
- 独立r3实际镜像sha256:2947e4318fff367438fe98ef98bb006825dc1772eaf7a1c60f05efddbd978d25、1274643121bytes；ready RSS中位196.958984375MiB；构建73.90007770000011s；reply3.122s、native WAV playing8.518s。保留所有raw，基线quality CPU/构建安装重叠，不能宣称干净启动或构建提速；无GPU峰值/硬件冷缓存测量。
- `c-dc3-role01`实际LangGraph tools=false/config_keys=[]，注册节点无tools，完整stdout+stderr观察区间无可选工具YAML loader/工具加载日志；实际容器guard源码SHA匹配冻结r3。角色回复真实Qwen→live非零PCM WAV原生playing/时间推进/自然ended/持久同task播放，Live2D model live与同task口型通过。
- 两轮普通午饭事实原样匹配，第二轮不含答案，实际同graph thread与历史窗口连续；memory_v2 ready，long_term_memory_mode off不变。不改人格/账号/用户数据，不冒充长期写入。Dashboard账号登录限制保留。
- 2097源文件/42overlay/75taskpaths/归档/manifest/.env原SHA与全部历史records复核通过；同URL实际资源指纹已记录。Qwen14240/16104创建时间/完整命令行/模型声线保持；8769不可用，各r3 plan/observations无RVC步骤或探测。无本任务生命周期/浏览器残留。
- 仅交付授权runtime记录、原字节raw/probe与索引；不复制.env/源zip/镜像/庞大日志/自动artifacts，secret内存扫描通过。最终index不含自引用SHA，SHA在最终工具/交付消息记录供父侧Git blob复核。当前r3应用和Qwen保持，不提交/推送。
