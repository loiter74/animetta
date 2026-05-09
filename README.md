# Anima

<div align="center">

![Anima Chat Demo](assets/demo/anima-chat-preview.gif)

**打造你的专属 AI 虚拟角色！ | Build Your Own AI Virtual Companion!** 🎭

支持 Live2D 动画、实时语音交互，可自由切换不同 AI 模型
Live2D animation, real-time voice interaction, swappable AI models

[![Test](https://github.com/loiter74/Anima-LLM-Vtuber/actions/workflows/test.yml/badge.svg)](https://github.com/loiter74/Anima-LLM-Vtuber/actions/workflows/test.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://github.com/loiter74/Anima-LLM-Vtuber)
![Python](https://img.shields.io/badge/python-3.12%20|%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-81%20passing-brightgreen)

</div>

---

## ✨ 为什么选择 Anima？ | Why Anima?

<div align="center">

### 🎭 会"动"的虚拟角色 | Living Avatar

**CN:** Live2D 角色会根据对话内容改变表情和动作，仿佛有真正的灵魂
**EN:** Live2D avatars react with expressions and gestures — they feel alive.

### 💬 自然流畅的对话 | Natural Conversations

**CN:** 支持文本和语音双模态输入，像和朋友聊天一样自然
**EN:** Text or voice input, streamed replies — chat like you're talking to a friend.

### 🔄 随心切换 AI 模型 | Swap AI Models Freely

**CN:** 无需修改代码，一键切换不同的 LLM/ASR/TTS 服务商
**EN:** Switch between LLM/ASR/TTS providers without touching config code.

</div>

---

## 🚀 快速开始 | Quick Start

### 1️⃣ 安装依赖 | Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ 配置 API Key | Configure API Key

```bash
# 复制环境变量模板 | Copy the environment template
cp .env.example .env
# 编辑 .env 填入你的 API Key | Edit .env with your API keys
```

### 3️⃣ 启动应用 | Launch

```bash
python scripts/start.py
```

打开桌面应用，开始和你的 AI 角色聊天吧！
Open the desktop app and start chatting with your AI character!

---

## 🎮 核心特性 | Features

### 智能对话引擎 | Smart Dialogue Engine

| Feature | Description |
|---------|-------------|
| **实时回复** Real-time Replies | 流式输出，边说边显示 / Stream output token by token |
| **长期记忆** Long-term Memory | 记住你们的对话历史 / Remembers conversation history |
| **工具调用** Tool Calling | 联网搜索、计算等能力 / Web search, calculator, and more |
| **多模态输入** Multi-modal Input | 文字或语音，随你选择 / Text or voice, your choice |

### 生动角色表现 | Lively Character

| Feature | Description |
|---------|-------------|
| **表情同步** Expression Sync | 情绪驱动面部表情 / Emotion-driven facial expressions |
| **口型同步** Lip Sync | 语音与嘴型精确匹配 / Audio-driven viseme matching |
| **动作控制** Motion Control | 自定义触发动作和姿势 / Custom trigger motions & poses |
| **🎬 双语字幕** Bilingual Subtitles | Live2D 画布底部叠加萌系字幕，支持 LLM 翻译 / Anime-style subtitle overlay with LLM translation |

### 灵活配置选择 | Flexible Config

| Feature | Description |
|---------|-------------|
| **多种 AI 模型** Multi-LLM | GLM、OpenAI、DeepSeek、Ollama、本地模型 |
| **语音识别** ASR | FasterWhisper、GLM、OpenAI、FunASR |
| **语音合成** TTS | Edge TTS、GLM、OpenAI、ChatTTS、VibeVoice |
| **语音检测** VAD | Silero VAD |
| **自定义人设** Persona | 创建独一无二的角色性格 / Create unique character personalities |

---

## 🛠️ 技术栈 | Tech Stack

| Layer | Technology |
|-------|-----------|
| **后端 Backend** | Python 3.13, FastAPI, Socket.IO, LangGraph, LangChain |
| **前端 Frontend** | Electron, Vue 3, TypeScript, UnoCSS, Pinia, pixi-live2d-display |
| **AI 服务 AI Services** | GLM, OpenAI, DeepSeek, Ollama, FasterWhisper, Edge TTS, Silero VAD |
| **记忆系统 Memory** | Chroma (Vector DB), SQLite FTS5, Hybrid Search (70% Vector + 30% BM25) |
| **基础设施 Infra** | Docker, GitHub Actions, pytest, mypy, ruff |

---

## 📝 字幕功能 | Subtitles

<div align="center">

**在 Live2D 画布底部显示 AI 回复字幕，支持双语展示和 LLM 实时翻译**
**Display AI response subtitles at the bottom of the Live2D canvas with bilingual LLM translation**

</div>

### 主要特性 | Features

| Feature | Description |
|---------|-------------|
| **萌系泡泡风格** Cute Bubble Style | 毛玻璃面板 + 粉紫装饰 + 弹簧弹跳动画 / Glassmorphism panel with spring pop-in animation |
| **三种显示模式** 3 Display Modes | 原文 / 翻译 / 双语，一键切换 / Original / Translated / Bilingual |
| **LLM 实时翻译** Real-time LLM Translation | 使用同一 LLM 将回复翻译为目标语言 / Uses the same LLM provider for translation |
| **可配置开关** Configurable | 在设置面板中可随时启用/禁用 / Toggle on/off in Settings panel |
| **多语言目标** Multi-language Target | 支持英日韩法德西俄等语言 / Supports English, Japanese, Korean, French, German, Spanish, Russian |

### 使用方法 | Usage

1. 在右侧面板点击 **📝 字幕** 标签进入设置
2. 打开 **启用字幕** 开关
3. 选择显示模式：原文 / 翻译 / 双语
4. 选择翻译目标语言
5. AI 回复时，字幕会自动出现在 Live2D 画布底部

### 配置 | Configuration

字幕配置在设置面板中管理，实时生效，无需重启。翻译使用当前 LLM 服务商（`config.yaml` 中的 `services.agent`）进行翻译。

---

### 数据流 | Data Flow

```
User Input (Text / Audio)
    ↓
[START] → route_input()
    │
    ├── (audio) → [asr_node] → Speech Recognition → user_text
    │
    └── (text) ──────────────────→ [llm_node]
                                      │
                                  RAG: Retrieve Memory Context
                                      │
                                  LLM Reasoning (Streaming / Tools)
                                      │
                             ┌────────┴────────┐
                             │                 │
                       (Tool Calls)      (Direct Reply)
                             │                 │
                        [tool_node]      [tts_node]
                             │                 │
                      Execute Results ←─────────┤
                                               ↓
                                         [emotion_node]
                                               ↓
                                         [output_node]
                                    ┌──────────┴──────────┐
                                    ↓                     ↓
                            Socket.IO Events        Memory Storage
                              → Frontend           → SQLite / Chroma
```

### 项目结构 | Project Structure

```
src/anima/
├── core/                    # Entry point + service container
│   └── socketio_server.py   # Main ASGI server (FastAPI + Socket.IO)
├── config/                  # Configuration (YAML + Pydantic)
│   ├── app.py              # AppConfig — main configuration
│   ├── persona/            # Character personality configs
│   ├── providers/          # LLM/ASR/TTS/VAD provider configs
│   └── core/registry.py    # Plugin-style service registry
├── orchestration/           # LangGraph state graph
│   ├── graph/              # Graph nodes + orchestrator
│   │   ├── state.py       # AgentState TypedDict
│   │   ├── builder.py     # StateGraph builder
│   │   ├── orchestrator.py # LangGraphOrchestrator
│   │   ├── llm_node.py    # LLM reasoning (with RAG + tools)
│   │   ├── tts_node.py    # Speech synthesis
│   │   ├── emotion_node.py # Emotion analysis
│   │   ├── output_node.py # Output + memory storage
│   │   ├── tool_node.py   # Tool execution
│   │   └── asr_node.py    # Speech recognition
│   └── server/             # WebSocket routes + session management
├── services/                # Service implementations
│   ├── speech/             # ASR + TTS implementations
│   ├── intelligence/       # LLM + VAD implementations
│   └── live2d/             # Live2D action queue + viseme sync
├── memory/                  # Memory system (Wiki architecture)
│   ├── search/             # Hybrid search (Vector + BM25)
│   ├── storage/            # Chroma + SQLite stores
│   └── wiki/               # Markdown-based wiki memory
├── avatar/                  # Live2D expression analysis
│   ├── analyzers/          # Keyword + LLM-based emotion extraction
│   └── strategies/         # Duration/intensity/position strategies
├── tools/                   # Tool calling system
│   ├── base.py             # Built-in tools (web_search, calculator, etc.)
│   ├── mcp_bridge.py       # MCP protocol bridge
│   └── custom_tools.py     # Custom tool definitions
└── utils/                   # Helpers
```

---

## 📦 容器化部署 | Container Deployment

```bash
# Build & start
docker-compose up --build -d

# Verify health
curl http://localhost:12394/health

# View logs
docker-compose logs -f
```

### Fly.io 部署 | Fly.io Deployment

```bash
# 一键部署 | One-command deploy
flyctl launch --ha=false

# 设置密钥 | Set secrets
flyctl secrets set GLM_API_KEY=your_key_here

# 部署 | Deploy
flyctl deploy

# 验证 | Verify
curl https://anima-demo.fly.dev/health
```

---

## 🧪 测试 | Testing

```bash
# Run all tests
PYTHONPATH=src python -m pytest tests/ -v

# With coverage
PYTHONPATH=src python -m pytest tests/ --cov=src/anima --cov-report=term-missing

# Type checking
mypy src/ --ignore-missing-imports

# Linting
ruff check src/ tests/
```

详见 [TESTING.md](TESTING.md) | See [TESTING.md](TESTING.md) for details.

---

## 📖 文档导航 | Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构总览 / System Architecture |
| [TESTING.md](TESTING.md) | 测试指南 / Testing Guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 / Contributing Guide |
| [Enterprise Upgrade Plan](docs/plans/2026-05-01-enterprise-upgrade-plan.md) | 工程能力增强计划 / Engineering Upgrade Plan |

---

## 📄 许可证 | License

MIT License — 自由使用、修改和分发 | Free to use, modify, and distribute.

---

<div align="center">
<sub>Built with ❤️ by the Anima team</sub>
</div>
