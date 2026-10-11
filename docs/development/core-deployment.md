# 核心安装与可选能力

默认 production 保留角色文字对话、Live2D、记忆 v2 和现有 Qwen 语音输出。基础设施仍为应用、Redis 和已经准备好的 Windows Qwen 服务；LLM 使用所选远端 Provider。Python 3.13 是主应用要求，主环境不安装本地推理或训练依赖。

## 日常启动：一个入口

已经配置好的本机直接双击根目录 `start-anima.cmd`，或运行：

```powershell
py -3.13 scripts/bootstrap.py --open
```

入口自动在 `.venv/launcher` 准备轻量控制工具，复用健康的宿主 Qwen，通过原有 `runtime_lifecycle.py anima-up --wait` 构建或复用镜像，完成真实就绪、前端资源和日志检查，随后初始化首次登录账号并打开 `/live.html`。重复运行复用控制环境、匹配源码的镜像和健康容器；不重新安装完整后端，不在宿主安装 Node/pnpm，不启动关闭的可选服务。应用和 Redis 仍在 Docker 中，Qwen 模型与声线独立保留。

新机器的前置条件是 Python 3.13、Docker Desktop 的 Linux 引擎，以及已经准备好的 Windows Qwen 服务。第一次用同一入口准备配置：

```powershell
py -3.13 scripts/bootstrap.py --prepare-only
# 在生成的 .env 填写所选远端 LLM 和现有 Qwen 服务密钥。
py -3.13 scripts/bootstrap.py --open
```

入口只生成缺失的机器访问 token 和 Redis 密码；管理员首次密码固定为 `123456`。不生成 API 密钥，也不替换已有机器或宿主凭据。Provider、角色和功能开关仍来自 `config/animetta.yaml`。默认不需要 ASR/VAD 密钥。第一次源码构建可能下载镜像和依赖；一个命令不等于免下载或免准备模型。

控制环境使用官方 PyPI 和核心版本约束，隔离用户级 pip 索引设置，避免旧镜像源或额外包配置影响默认准备；已有系统代理继续由网络客户端使用。应用镜像的依赖安装仍遵循 Docker 中的既有设置。

## 首次登录与改密

默认用户名 `admin`，首次登录密码 `123456`。登录 Dashboard 后自动进入账号页，必须设置新密码才能访问产品 API 和控制功能。新密码继续要求 8–1024 个 UTF-8 字节；六位初始密码只用于首次登录。其他账号的创建与密码策略保持原有规则。

密码保存在持久化账号数据库中。入口的 `ensure-admin-bootstrap` 只迁移尚未更换过初始密码的管理员，重复运行不增加凭据版本、不撤销已有会话。浏览器设置的新密码和本地恢复工具设置的临时密码均保留，不会因重启恢复为 `123456`。被禁用账号和普通账号不会自动启用或升级。`.env` 的初始哈希仅用于空库初始化，不承担长期密码同步；旧密码文件配置会被移除，入口不再读取私人文件。

忘记密码时仍使用隐藏输入的原恢复工具：

```powershell
py -3.13 scripts/manage_users.py reset-admin-password --username admin
```

恢复后登录仍须设置新密码。`ANIMETTA_ACCESS_TOKEN` 继续仅用于机器客户端。

## 安装规格

`pyproject.toml` 与 `uv.lock` 是唯一依赖来源。`py -3.13 scripts/check_python_lock.py --write` 生成以下完整规格，不能手改 requirements：

| 文件 | 用途 |
| --- | --- |
| `requirements.txt` | 默认核心运行环境 |
| `requirements-bilibili.txt` | 核心及 Bilibili extra |
| `requirements-search.txt` | 核心及社区网页搜索 extra |
| `requirements-memory-semantic.txt` | 核心及显式语义检索 extra；不包含 GPU 推理包 |
| `requirements-dev.txt` | 开发、测试及所有应用 extras；Windows/Linux 的 Torch 使用 CPU 构建，不含 CUDA 推理环境 |

隔离检查核心安装：

```powershell
$corePython = py -3.13 -c "import sys; print(sys.executable)"
uv venv --python $corePython .venv-core
uv pip sync --python .venv-core/Scripts/python.exe requirements.txt
```

`sync` 使环境精确匹配所选规格，会移除未列出的包，不要对正在使用的开发或模型环境执行。同时需要 Bilibili 和搜索时，可以在自己的应用环境中以 `uv pip install` 安装两个 feature 规格；已有功能不会因第二次 `sync` 被清掉。

Docker 默认只安装 `requirements.txt`。按需选择镜像依赖：

```powershell
py -3.13 scripts/bootstrap.py --extra bilibili search
py -3.13 scripts/bootstrap.py --extra memory-semantic
# 空集合恢复仅核心；不传 --extra 则保留上次选择。
py -3.13 scripts/bootstrap.py --extra
```

`--extra` 声明完整集合，多个规格取并集，不逐次累加。选择保存在 `.env` 的 `ANIMETTA_PYTHON_EXTRAS`；Docker 从锁文件导出的完整规格安装，并将选择纳入镜像身份，避免误用之前的核心镜像。依赖安装不会开启功能；仍需在所选 profile 修改能力或记忆检索模式。关闭开关也不自动卸载已选依赖，恢复核心时同时清空该集合。上述安装没有 GPU 推理包。

## Web 与开发工具

前端共享一个锁文件，安装范围由 workspace 包明确选择。默认构建不复制 Cesium，关闭地图时不会加载地图实现。Electron 和浏览器评审工具各有独立安装包。

```powershell
# 只准备 Web 核心；显式包名也适用于从仓库根目录运行
pnpm --dir frontend --filter animetta-desktop install --frozen-lockfile
pnpm --dir frontend build

# 开发者需要所有可选工具时
pnpm --dir frontend --filter '*' install --frozen-lockfile

# 只增加地图；保留核心包
pnpm --dir frontend --filter animetta-desktop --filter @animetta/earth install --frozen-lockfile
pnpm --dir frontend build:earth
```

桌面打包选择 `@animetta/desktop`，评审选择 `@animetta/review`，同时保留核心包 filter。全量类型检查和测试仍属于开发质量门禁。由于 `recursiveInstall: false`，不要用不带明确 filter 的递归命令代替全量安装。纯 Web 安装保留少量类型声明和构建工具，不安装 Electron、Playwright、OBS、Cesium 等可选运行包。

## 普通部署与回退

已准备 Docker、配置、凭证及独立 Qwen 服务的运行者，优先使用 CI 发布的不可变镜像。质量工作流在门禁通过后发布 GHCR 的提交标签与 digest，普通部署无需本地 Node、pnpm、编译器或训练工具。不要用浮动标签作为回退记录。

默认入口自动安装控制依赖。直接使用底层生命周期的运行者可以手动准备以下轻量依赖，版本由核心规格约束；应用的完整 Python 环境安装在镜像内：

```powershell
py -3.13 -m pip install -c requirements.txt pydantic pyyaml python-dotenv loguru
```

独立 Windows 3.13.14 探针验证该规格闭包为 10 包，可导入生命周期、反馈控制器和 Qwen 预检，解析 production 宿主需求与构建标志；没有 LangGraph、OpenAI、Chroma、Torch 或 Transformers。此项为控制脚本依赖验证，没有启停服务。开发和本地直接运行后端仍使用前述完整核心／开发规格。

```powershell
py -3.13 scripts/bootstrap.py --image ghcr.io/loiter74/animetta:sha-<完整提交SHA> --open
```

使用仓库实际发布的镜像地址；部署前保留上一成功版本的提交标签或 digest。回退走同一 `anima-deploy` 入口并指定上一不可变镜像，不清空 Redis、应用数据或记忆卷。第一次准备 Qwen 模型、日常部署、应用重启是三个独立步骤，应用重启复用已经健康的 Qwen。

`--image` 只拉取已有镜像，不能追加 `--extra`；镜像本身必须包含所需能力和 `ensure-admin-bootstrap` 命令。旧镜像不支持该命令时会明确失败；旧版本回退仍可用原始 `runtime_lifecycle.py anima-deploy`，并配对原发布配置。

源码构建走 `anima-up`。生命周期从同一 profile 的能力配置导出地图与媒体构建开关，默认镜像不安装系统 ffmpeg；启用语音输入、唱歌或地图时才加入相关媒体支持。自行直接构建 Docker 的开发者需要显式传入相应 build args，不能只修改浏览器环境变量。

## 按需启用

在 `config/animetta.yaml` 的所选 profile 下修改 `runtime.capabilities`，随后通过规范生命周期重新启动应用。能力切换需要重启，不能通过热重载改变引擎组成。

```yaml
runtime:
  capabilities:
    voice_input: false
    bilibili: false
    singing: false
    minecraft: false
    earth: false
  enable_tools: false
```

| 开关 | 启用前提 |
| --- | --- |
| `voice_input` | 配置中所选 ASR/VAD Provider 及其密钥；本地模型另需独立推理环境 |
| `bilibili` | Bilibili extra、房间和凭证 |
| `singing` | 现有宿主 RVC 服务及唱歌配置；生命周期加入 RVC 准备与预检 |
| `minecraft` | 现有独立 mc-mcp 环境及桥接配置；应用仅通过现有 MCP 契约连接 |
| `earth` | 原有探索配置、`@animetta/earth` 包与对应地图构建资源 |
| `enable_tools` | 原有工具配置；使用社区搜索回退时安装 search extra |

关闭的麦克风不会解析 ASR/VAD 密钥、创建相关引擎或影响 `/ready`。默认 Qwen 仍是必需能力：不可用或身份不匹配时就绪检查失败。关闭的功能事件返回 `CAPABILITY_DISABLED`，不加载相应重型实现。显式启用后的真实 Provider 失败仍按现有严格策略报错，不用 Mock 掩盖缺失。

## 启动边界

```powershell
py -3.13 scripts/runtime_lifecycle.py anima-up
```

生命周期从同一份配置读取宿主需求：所选 TTS 包含 Qwen 时准备并复用健康的 Qwen；启用唱歌时才准备 RVC。默认不探测或启动 RVC、mc-mcp，也不要求 ASR/VAD 密钥。`anima-down` 继续保留两个宿主服务；显式 `host-tts-*`、`host-rvc-*` 操作保留原有权限和行为。

记忆 v2 的共享运行时、SQLite/FTS 存储、原子版本、身份与作用域隔离继续保留。`runtime.memory_retrieval_mode` 默认 `fts`，无需 Chroma 或 embedding 模型。显式选 `semantic` 时必须安装相应 extra；后端初始化失败会明确报错，运行中的向量检索故障会标记降级。语义索引位于所选 SQLite 文件旁的 `chroma_v2`，不会另写全局固定目录。语义模式首次文本检索可能需要准备原有 embedding 模型，应单独预算。

FTS 对字面词项有效，同义表达与隐含含义的召回可能下降，两种模式没有质量等价承诺。已有 `long_term_memory_mode` 控制写入与治理策略，选择检索模式不会擅自打开长期写入。切换模式需要重启，保留 SQLite 原始记忆，语义索引可重建。Qwen 模型、声线合同与参考音频没有修改。

阶段测量见 [实施记录](../performance/deployment-core-2026-10-11/results.md)。
