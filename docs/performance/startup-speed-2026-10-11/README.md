# 默认核心启动速度优化（2026-10-11）

成功启动的同条件中位数从 **22.59 秒降到 15.52 秒**，减少 **7.07 秒 / 31.3%**。角色对话、Live2D、记忆和宿主机 Qwen 语音保持原实现。此次只调整镜像中的分词器数据交付和 Redis 启动期健康检查，没有继续裁剪业务能力或新增服务。

## 测量口径

主指标使用规范生命周期 `animetta-start` 实际结果的 `started_at`，至 `animetta-ready` 实际结果的 `feedback_at`；完整 `/ready` 是完成条件，不能以 `/health` 替代。另列整个 CLI 和应用容器 `StartedAt` 至完整就绪的耗时。构建及一次预热均在样本外完成。

基线源码是 `59fca67ca0931ed75999aec08acf545b953835ac`。两组均使用 production、`http://localhost` / 80、后端 12394、相同私密凭据及三个原命名卷；每个样本通过 `py -3.13 scripts/runtime_lifecycle.py` 的 down → up 创建新的应用和 Redis 容器，保留镜像、操作系统及模型缓存。Qwen 的原 PID、模型与声线保持，RVC 及其他可选能力关闭。测量期间不并行构建、安装、质量门禁或浏览器检查。

原计划每组三个成功样本。基线两次出现 LLM 探测超时：保留失败容器及原始结果，单次只读真实请求确认上游恢复后，仅进行了一轮有证据的恢复采样。再次失败后停止继续凑样本，改为每组两个成功样本。这项修订和优化目标在实现前写入并冻结了 [预测文件](evidence/optimization-prediction.json)，原 [测量契约](evidence/contract.json) 保留。

## 实测结果

| 样本 | 应用启动 → 完整就绪 | 应用容器启动 → 就绪 | 整个 CLI |
| --- | ---: | ---: | ---: |
| `ss-base01` | 22.497 s | 10.344 s | 29.628 s |
| `ss-base03` | 22.674 s | 10.696 s | 28.871 s |
| 基线中位数 | **22.586 s** | **10.520 s** | **29.250 s** |
| `ss-opt01` | 15.640 s | 7.613 s | 22.127 s |
| `ss-opt02` | 15.396 s | 7.493 s | 21.890 s |
| 优化中位数 | **15.518 s** | **7.553 s** | **22.009 s** |

成功样本的主指标范围：基线 22.497–22.674 秒，跨度 0.177 秒；优化 15.396–15.640 秒，跨度 0.245 秒。两个样本不足以估计 p95 或长期可靠性。

| 实际生命周期阶段，中位数 | 基线 | 优化 | 减少 |
| --- | ---: | ---: | ---: |
| `animetta-start` / Compose 创建与等待 | 12.970 s | 8.858 s | 4.112 s |
| `animetta-health` / HTTP 可用 | 3.888 s | 3.794 s | 0.094 s |
| `animetta-ready` / 完整就绪 | 5.711 s | 2.850 s | 2.861 s |

步骤间调度也包含在主指标中，因此表中阶段耗时之和与主指标略有差异。两个优化一起测量，未单独进行两因素消融；不能把阶段变化全部归于某一个改动。

## 瓶颈与实现

1. **Redis 已接受连接，应用仍等待启动期健康检查。** 原检查间隔 5 秒。现在设置 `start_period: 20s`、`start_interval: 1s`；稳定运行仍为 5 秒，原 PING、`FT.CREATE`、`JSON.SET` 判定保持。首次成功检查即可解除依赖等待。[Docker 官方配置说明](https://docs.docker.com/reference/compose-file/services/#healthcheck)。基线成功容器的首次健康检查记录没有及时保存，不能将日志中的“接受连接”当作首次健康时间；这里以实际 Compose 阶段改善为主要证据。
2. **每次新容器在线下载分词器数据。** 原缓存位于临时目录，随容器删除。基线从 ServicePool 初始化至分词器加载完成分别为 2.771、3.645 秒；优化后为 0.336、0.260 秒。这段区间也包含之前少量服务初始化，不能解释为纯分词器 CPU 时间。Docker 构建现在调用同一个原生 `cl100k_base` 编码加载器，把经过原生哈希验证的数据随 `/opt/venv` 复制到运行镜像；构建命令有 60 秒上限，运行阶段无需这次下载。
3. **保留真实 LLM 验证。** 成功基线的真实探测为 2477、2031 ms，优化为 2259、2194 ms；没有移除配置模型别名验证、改用 mock 或放宽 readiness。

只读导入探针显示，配置模块总进程时间约 0.524 秒，Socket.IO 服务导入约 2.912 秒。相对上述等待，其收益空间较小，因此本轮没有扩大到 Provider 注册或编排重构。

## 失败与限制

基线共四个计时启动尝试，其中两个成功、两个失败；优化的两个计时启动均成功。失败样本 `ss-base02`、`ss-base04` 都出现分词器下载 TLS 错误和 LLM 五秒探测预算超时；前者已被捕获返回，后者使失败状态保留，完整 `/ready` 持续 503，最终触发约 240 秒的生命周期步骤截止时间。不能确定原 LLM 的哪一个子请求超时。

失败不计入“成功启动耗时”中位数，但没有删除或改写为成功。原失败结果与日志随证据归档；分词器随镜像交付消除了该项启动下载，不能据两次成功就声称外部 LLM 网络故障已被解决。

冻结目标为中位数不超过 18 秒且改善至少 20%，实测达到目标。约 4 秒 Redis 等待和约 3 秒分词器等待的预测仅为事前估计；首次健康时间的基线缺测以及两个因素共同修改，限制了独立归因。

镜像本地逻辑大小从 614,348,777 增至 616,822,142 字节，增加 2,473,365 字节（约 2.36 MiB / 0.40%）。其中原生分词器数据为 1,681,126 字节；这次用很小的镜像增量换取更快启动及该项数据的离线可用，未测量压缩后的网络传输量。

## 验证与证据

源配置冻结后执行一次影响感知验证，全部通过：

```powershell
py -3.13 -m tooling.quality verify --tier affected --paths Dockerfile docker-compose.yml --cache read-write
```

计划 `69d1c4c1d24e`：`backend-route-smoke`、`docker-compose-contract`、`operational-source-contract`、`runtime-lifecycle-unit`。未再运行 full 或重复宽泛测试。

优化运行实例的最终验收：

- [离线分词器](evidence/acceptance/offline-tokenizer.stdout.json)：独立 Python 进程禁止网络，实际网络尝试为零；tiktoken 仍为 0.12.0，数据 SHA-256 与原生预期哈希一致，多语言编码／解码通过。核心安装仍为 88 个包，Torch、Transformers、ChromaDB、Demucs 等可选重依赖及 FFmpeg、Cesium 资源不存在。
- [严格就绪与 Redis](evidence/acceptance/ready-identity-redis.json)：80 与 12394 的真实 `/ready` 均 200，官方 Redis checkpointer 初始化正常。模块命令检查保持 `FT.CREATE` / `JSON.SET`；没有把命令存在宣称为额外直接写入测试。
- [本轮角色与实际播放](evidence/acceptance/ss-opt-role01.json)：任务 `4ded87f7-27dc-44d8-81e4-26e89896d7a3`，首段回复 4.716 秒，实际非零 WAV/blob 的 HTMLMediaElement 开始播放 8.209 秒并原生播放完成；页面持久播放计数递增，本轮 audio task ID 一致，Live2D 已加载并实际应用口型 282 次，浏览器错误为空。这里证明浏览器播放，未验证物理扬声器。
- 同一 Socket 和逻辑会话下两轮普通对话，回忆问题未包含答案，实际回复正确回忆前一轮食物；两轮均真实播放完成。记忆运行时 ready，既有长期记忆模式未改；此场景只证明短期会话连续性。使用记录化 Socket.IO 写入口；没有账户登录凭据，未验收 Dashboard 输入框。
- [最终身份与资源](evidence/acceptance/final-identity-resources.json)：仍是原 Qwen PID、模型、声线及私密凭据，当前正式入口资源和实际容器镜像指纹已核对。页面通过项目 review CLI 解析并用可见内置浏览器打开 `http://localhost/live.html`，显示“服务已连接”和“Live2D 已加载”，保留页面供查看；真实 Bilibili 直播未启动。

原始样本、实际步骤结果、stdout / stderr、源码输入清单、冻结预测及最后验收统一列在 [证据索引](evidence/evidence-index.json)。索引保存源位置、归档位置、字节数和 SHA-256；JSON 中原绝对路径是采集位置，跨机器阅读请使用索引中的归档相对路径。
