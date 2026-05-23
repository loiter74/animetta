<p align="center">
  <h1 align="center">🤖 Animetta — AI Virtual Companion / VTuber Framework</h1>
  <p align="center">
    可配置、可扩展的 AI 虚拟伴侣框架<br>
    插件化架构 · LangGraph 编排 · 混合记忆 · Live2D 驱动 · 多模态交互
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Vue_3-vite-green?logo=vue.js" alt="Vue 3">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <img src="https://img.shields.io/badge/LangGraph-orchestration-orange" alt="LangGraph">
    <img src="https://img.shields.io/badge/OpenTelemetry-tracing-purple" alt="OpenTelemetry">
  </p>
</p>

---

## ✨ 项目亮点

Animetta 不是又一个 "ChatGPT + TTS" 的简单拼接。它是一个**工程化的 AI 伴侣框架**，核心设计原则是**可配置、可观测、可扩展**：

- **LangGraph 状态图编排** — 不是线性 pipeline，而是基于 LangGraph 的有向图，支持条件路由、工具调用循环、中断恢复
- **插件化 Provider 架构** — 通过 `@ProviderRegistry` 装饰器注册新服务商，零侵入核心代码
- **混合记忆系统** — Chroma 向量搜索 (70%) + SQLite FTS5 关键词匹配 (30%) + Markdown Wiki 知识库
- **Live2D 情感驱动** — LLM 输出 → 情感分析 → Live2D 参数映射，表情随对话内容实时变化
- **全链路可观测** — OpenTelemetry 分布式追踪 + Prometheus 指标 + 内置 Stats Dashboard

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3 + Vite)                     │
│              Live2D Renderer · Chat UI · Stats Dashboard        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Socket.IO / REST
┌──────────────────────────▼──────────────────────────────────────┐
│                    WebSocket Server (FastAPI + Socket.IO)        │
│                Session Management · Desktop App · Live2D Events │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  LangGraph Orchestration Engine                  │
│                                                                  │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌────────────────┐   │
│  │ASR Node │→ │Persona  │→ │ LLM Node │→ │ Emotion Node   │   │
│  │         │  │  Node   │  │ + RAG    │  │ → Live2D Map   │   │
│  └─────────┘  └─────────┘  └────┬─────┘  └────────────────┘   │
│                                  │                               │
│                          ┌───────▼───────┐  ┌──────────────┐   │
│                          │  Tool Node    │  │ Output Node  │   │
│                          │ MC/MCP/Custom │  │ TTS + Memory │   │
│                          └───────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Services   │  │    Memory    │  │   Tracing    │
│ LLM/ASR/TTS  │  │ Chroma+SQLite│  │  OTel+Stats  │
│  Live2D/VAD  │  │  +Wiki+Meme  │  │ +Prometheus  │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 🔧 核心模块

### 🧠 LangGraph 编排引擎

请求不是走 `if/else` 分支，而是通过 **LangGraph 状态图** 流转。每个 Node 是纯状态变换函数，业务逻辑委托给 `services/` 层：

| Node | 职责 |
|------|------|
| `asr_node` | 语音识别 → 文本 |
| `personality_node` | 注入人设 prompt |
| `memory_middleware` | RAG 检索记忆上下文 |
| `llm_node` | LLM 推理 + 工具调用 |
| `tool_node` | 执行工具（Minecraft / MCP / 自定义） |
| `emotion_node` | 情感分析 → Live2D 表情 |
| `output_node` | TTS 合成 + 记忆存储 + 字幕翻译 |

### 🔌 Provider 插件系统

通过装饰器注册，完全解耦：

```python
# 1. 注册配置
@ProviderRegistry.register_config("llm", "my_llm")
class MyLLMConfig(LLMBaseConfig):
    type: Literal["my_llm"] = "my_llm"
    api_key: str

# 2. 注册服务
@ProviderRegistry.register_service("llm", "my_llm")
class MyLLMAgent(AgentInterface):
    @classmethod
    def from_config(cls, config, **kwargs):
        return cls(api_key=config.api_key)
```

**已支持的服务商：**

| 类型 | Provider |
|------|----------|
| **LLM** | OpenAI · GLM (智谱) · Ollama · Mock |
| **ASR** | OpenAI Whisper · GLM ASR · Mock |
| **TTS** | OpenAI TTS · GLM TTS · Edge TTS · Mock |
| **VAD** | Silero VAD |

### 🧩 混合记忆系统

三层存储 + 双路搜索：

```
memory/
├── storage/
│   ├── chroma.py        # 向量语义搜索 (70% 权重)
│   └── sqlite.py        # FTS5 关键词搜索 (30% 权重)
├── wiki/                # Markdown 知识库
│   ├── entities/        # 实体页 (人物、宠物、项目)
│   ├── concepts/        # 概念页 (偏好、兴趣、习惯)
│   ├── sources/         # 每日对话摘要
│   ├── synthesis/       # 跨时间线主题综合
│   └── memes/           # AI 生成的梗
└── learner/             # 周期性学习
    ├── pattern_extractor   # 行为模式提取
    ├── fact_extractor      # 事实知识提取
    └── meme_discovery      # 梗生成与评分
```

记忆系统自带 **LINT 健康检查**：断链检测、孤立页面发现、索引漂移告警。

### 🎭 Live2D 情感表达

LLM 输出 → 情感标签提取 → Live2D 参数映射，支持 6 种基础情感：

```
happy → 嘴角上扬 + 眉毛上挑 + 眼睛放大 + 身体前倾
sad   → 嘴角下垂 + 眉毛下压 + 半闭眼 + 低头
angry → 紧咬牙关 + 皱眉 + 身体后仰
...
```

架构采用策略模式：`IEmotionAnalyzer` → `ITimelineStrategy` → `IEmotionParamMapper`，可自定义情感分析器和参数映射。

### 🎤 唱歌 Pipeline

从一条 Bilibili 链接到 AI 翻唱，全自动：

```
Bilibili URL → yt-dlp 下载 → Demucs/UVR 人声分离
    → Whisper 歌词识别 (或 B站原生歌词)
    → GPT-SoVITS / RVC 声线转换
    → AudioMixer 混音 → 成品输出
```

支持实时进度回调、歌词确认中断、lip sync 音量包络计算。

### ⛏️ Minecraft 集成

通过 Node.js Mineflayer 子进程驱动，LLM 可以自主操控 Minecraft 角色：

```
LLM Tool Call → MinecraftBridge (JSON over stdin/stdout) → Mineflayer Bot
```

支持的操作：移动 (`mc_goto`)、挖矿 (`mc_mine`)、建造 (`mc_build`)、战斗 (`mc_attack`)、聊天 (`mc_chat`)。附带自主行为循环 (`AutonomousLoop`) 和规则引擎 (`RulesEngine`)。

### 📡 可观测性

```yaml
# config/observability.yaml
tracing:
  enabled: true
  service_name: animetta
otlp:
  enabled: true          # 双写：SQLite + OTel Collector
  endpoint: http://localhost:4317
```

- **OpenTelemetry Tracing** — 每个 Graph Node 自动 span，双写至 SQLite + OTLP Collector
- **Prometheus Metrics** — Node 耗时、LLM token 用量、RAG 检索质量、WebSocket 会话数
- **Stats Dashboard** — 内置 REST API (`/api/stats/`) + 前端面板
- **健康检查** — 7 组件并发探针 (`/health`)，返回 ok / degraded / error

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
cd frontend && npm install
```

### 2. 配置

```bash
cp config/config.default.yaml config/config.yaml
```

编辑 `config/config.yaml`：

```yaml
profile: "glm"            # mock / openai / glm / ollama
persona: "neuro-vtuber"   # default / neuro-vtuber
system:
  host: "localhost"
  port: 12394
```

设置 API Key：

```bash
export LLM_API_KEY="your-api-key"
```

### 3. 启动

```bash
# 后端
python -m animetta.core.socketio_server

# 前端 (另一个终端)
cd frontend && npm run dev
```

---

## 📁 项目结构

```
animetta/
├── config/
│   ├── config.yaml               # 主配置
│   ├── profiles/                  # 服务方案 (mock/openai/glm/ollama)
│   ├── personas/                  # 人设配置
│   └── observability.yaml         # 追踪 & 指标配置
├── src/animetta/
│   ├── core/                      # 入口 + 服务容器
│   ├── orchestration/
│   │   ├── graph/                 # LangGraph 状态图 + Nodes
│   │   └── server/                # WebSocket + REST API
│   ├── services/
│   │   ├── intelligence/llm/      # LLM 服务
│   │   ├── speech/asr/            # 语音识别
│   │   ├── speech/tts/            # 语音合成
│   │   ├── live2d/                # Live2D 动作队列
│   │   └── singing/               # 唱歌 Pipeline
│   ├── memory/                    # 混合记忆系统
│   ├── avatar/                    # 情感分析 → Live2D 映射
│   ├── tools/                     # 工具调用 (Minecraft/MCP/Custom)
│   ├── tracing/                   # OpenTelemetry 可观测性
│   ├── inspection/                # 健康检查 & 一致性检查
│   └── config/                    # Pydantic 配置模型
├── frontend/                      # Next.js 前端
├── memory_db/                     # Wiki 知识库持久化
├── docs/                          # 文档
└── tools/training/                # LoRA 训练工具
```

---

## 🧪 扩展开发

### 添加新 Provider

只需两个文件 + 一个装饰器，参考 `services/intelligence/llm/` 下的现有实现。框架会通过 `ProviderRegistry` 自动发现和加载。

### 添加新 Graph Node

```python
async def my_node(state: AgentState) -> dict[str, Any]:
    """Node 只做状态变换，业务逻辑委托给 services/"""
    result = await some_service.process(state["messages"])
    return {"my_output": result}
```

在 `graph/builder.py` 中注册节点和边。

### 添加新 Tool

```python
from langchain_core.tools import tool

@tool
async def my_tool(query: str) -> str:
    """工具描述 — LLM 会根据这段文字决定何时调用"""
    return await do_something(query)
```

在 `tools/custom_tools.py` 注册，或通过 MCP Bridge 接入外部服务。

---

## 📊 技术栈

| 层级 | 技术 |
|------|------|
| **编排** | LangGraph · LangChain |
| **后端** | FastAPI · Socket.IO · Starlette |
| **前端** | Vue 3 · Vite · TypeScript · pixi.js · Live2D Cubism SDK |
| **记忆** | ChromaDB · SQLite FTS5 · Markdown Wiki |
| **追踪** | OpenTelemetry · Prometheus · Langfuse |
| **AI** | OpenAI · 智谱 GLM · Ollama · Whisper · Edge TTS |
| **音频** | Demucs · GPT-SoVITS · RVC · yt-dlp |
| **游戏** | Mineflayer (Node.js) |

---

## 📄 License

[MIT License](LICENSE)
