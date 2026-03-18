# Anima 项目文档

AI 虚拟伴侣/VTuber 框架。

---

## 文档导航

### 开发指南

| 文档 | 描述 |
|------|------|
| [快速开始](development/quickstart.md) | 5 分钟运行项目 |
| [添加服务](development/adding-services.md) | 扩展 LLM/ASR/TTS 服务 |

### 架构设计

| 文档 | 描述 |
|------|------|
| [数据流](architecture/data-flow.md) | Pipeline + EventBus + Orchestrator |
| [事件系统](architecture/event-system.md) | EventBus 实现（**面试重点**） |
| [设计模式](architecture/patterns.md) | 6 种设计模式应用 |
| [可扩展性](architecture/extensibility.md) | 插件化架构 |

### 功能模块

| 文档 | 描述 |
|------|------|
| [内存系统](modules/memory.md) | Chroma + SQLite 混合检索 |

### 实现计划

| 文档 | 描述 |
|------|------|
| [历史计划](plans/history.md) | 已完成和计划中的功能 |

---

## 项目结构

```
src/anima/
├── socketio_server.py    # 主入口
├── config/               # 配置 (YAML + Pydantic)
├── adapters/             # 通道适配器层
├── services/             # ASR/TTS/LLM/VAD 服务
├── pipeline/             # 责任链处理
├── events/               # 事件驱动架构
├── memory/               # 对话记忆
└── utils/                # 工具函数
```

---

## 快速开始

```bash
# 启动项目
python scripts/start.py

# 配置 API Key
echo "GLM_API_KEY=your_key" > .env

# 停止项目
python scripts/stop.py
```

---

## 技术栈

- **后端**: Python, FastAPI, Socket.IO
- **前端**: Electron, vanilla JS/HTML/CSS
- **LLM**: GLM, OpenAI, Ollama
- **ASR**: FasterWhisper, GLM
- **TTS**: Edge TTS, GLM
- **VAD**: Silero
