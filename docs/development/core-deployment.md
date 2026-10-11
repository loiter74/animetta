# 核心安装与可选能力

默认 production 保留角色文字对话、Live2D、记忆 v2 和现有 Qwen 语音输出。基础设施仍为应用、Redis 和已经准备好的 Windows Qwen 服务；LLM 使用所选远端 Provider。Python 3.13 是主应用要求，主环境不安装本地推理或训练依赖。

## 安装规格

`pyproject.toml` 与 `uv.lock` 是唯一依赖来源。`py -3.13 scripts/check_python_lock.py --write` 生成以下完整规格，不能手改 requirements：

| 文件 | 用途 |
| --- | --- |
| `requirements.txt` | 默认核心运行环境 |
| `requirements-bilibili.txt` | 核心及 Bilibili extra |
| `requirements-search.txt` | 核心及社区网页搜索 extra |
| `requirements-dev.txt` | 开发、测试及所有应用 extras；不含 GPU 推理环境 |

隔离检查核心安装：

```powershell
uv venv --python 3.13 .venv-core
uv pip sync --python .venv-core/Scripts/python.exe requirements.txt
```

`sync` 使环境精确匹配所选规格，会移除未列出的包，不要对正在使用的开发或模型环境执行。同时需要 Bilibili 和搜索时，可以在自己的应用环境中以 `uv pip install` 安装两个 feature 规格；已有功能不会因第二次 `sync` 被清掉。

Docker 默认仍读取 `requirements.txt`。要部署可选能力，应在自己的镜像构建中选择对应完整规格；单独修改能力开关不会替镜像安装缺失依赖。地图与 Electron 的构建资源精简属于后续阶段，当前前端构建仍保留这些依赖。

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
| `earth` | 原有探索配置与前端地图资源 |
| `enable_tools` | 原有工具配置；使用社区搜索回退时安装 search extra |

关闭的麦克风不会解析 ASR/VAD 密钥、创建相关引擎或影响 `/ready`。默认 Qwen 仍是必需能力：不可用或身份不匹配时就绪检查失败。关闭的功能事件返回 `CAPABILITY_DISABLED`，不加载相应重型实现。显式启用后的真实 Provider 失败仍按现有严格策略报错，不用 Mock 掩盖缺失。

## 启动边界

```powershell
py -3.13 scripts/runtime_lifecycle.py anima-up
```

生命周期从同一份配置读取宿主需求：所选 TTS 包含 Qwen 时准备并复用健康的 Qwen；启用唱歌时才准备 RVC。默认不探测或启动 RVC、mc-mcp，也不要求 ASR/VAD 密钥。`anima-down` 继续保留两个宿主服务；显式 `host-tts-*`、`host-rvc-*` 操作保留原有权限和行为。

记忆 v2 的共享运行时、SQLite/FTS 存储及隔离规则保留。已有 `long_term_memory_mode` 仍控制原有长期记忆策略，本轮没有改写数据或引入新的检索实现。Qwen 模型、声线合同与参考音频没有修改。

阶段测量见 [实施记录](../performance/deployment-core-2026-10-11/results.md)。
