# Anima

> AI 虚拟伴侣 / VTuber 框架

一个可配置的 AI 虚拟形象框架，支持 Live2D 模型、语音交互和多种 LLM 服务商。

---

## 特性

- **插件化架构** - 使用装饰器注册新服务，零修改扩展 LLM/ASR/TTS/VAD
- **流式响应** - 支持 LLM 流式对话和 TTS 实时合成
- **事件驱动** - 基于 EventBus 的解耦架构，支持优先级和异常隔离
- **记忆系统** - Chroma + SQLite 混合检索，支持长期记忆
- **Live2D 支持** - 表情同步、唇同步、动作控制

---

## 支持的服务商

| 类型 | 服务商 |
|------|--------|
| **LLM** | GLM, OpenAI, Ollama, Local LoRA |
| **ASR** | FasterWhisper, GLM, OpenAI |
| **TTS** | Edge TTS, GLM, OpenAI, ChatTTS |
| **VAD** | Silero |

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件：

```bash
GLM_API_KEY=your_api_key_here
```

### 运行

```bash
# 一键启动
python scripts/start.py

# 或手动启动后端
python -m anima.socketio_server
```

后端运行在 `http://localhost:12394`

---

## 配置说明

### 切换服务商

编辑 `config/config.yaml`：

```yaml
services:
  agent: glm           # LLM: glm, openai, ollama, local_lora
  asr: faster_whisper  # ASR: faster_whisper, glm, openai
  tts: edge            # TTS: edge, glm, openai, chattts
  vad: silero          # VAD: silero
```

### 人设配置

人设文件位于 `config/personas/`：

```yaml
# config/personas/neuro-vtuber.yaml
identity: "Neuro-sama"
personality: "好奇、活泼、喜欢游戏"
speaking_style: "使用网络用语和emoji，偶尔提到游戏"
```

---

## 项目结构

```
src/anima/
├── socketio_server.py    # Socket.IO 主入口
├── service_context.py    # 服务容器
├── config/               # 配置系统 (YAML + Pydantic)
│   ├── core/registry.py  # 服务注册表
│   └── providers/        # 服务商配置类
├── adapters/             # 通道适配器层
│   ├── base.py           # ChannelAdapter 基类
│   └── implementations/  # DesktopLive2DChatter
├── services/             # 服务实现
│   ├── llm/              # LLM 服务
│   ├── asr/              # 语音识别
│   ├── tts/              # 语音合成
│   ├── vad/              # 语音活动检测
│   └── live2d/           # Live2D 控制
├── pipeline/             # 责任链处理
│   ├── base.py           # PipelineStep 基类
│   └── steps/            # ASR/文本清洗/情感提取
├── events/               # 事件驱动架构
│   ├── bus.py            # EventBus
│   ├── router.py         # EventRouter
│   └── models.py         # OutputEvent
├── handlers/             # 事件处理器
│   ├── text.py           # TextHandler
│   └── unified.py        # UnifiedEventHandler
├── memory/               # 对话记忆
│   ├── memory_manager.py # 核心管理器
│   ├── chroma_store.py   # 向量存储
│   └── sqlite_store.py   # FTS5 存储
└── utils/                # 工具函数
```

---

## 扩展开发

### 添加新的 LLM 服务

1. 创建配置类：

```python
# src/anima/config/providers/llm/my_llm.py
from anima.config.core.registry import ProviderRegistry

@ProviderRegistry.register_config("llm", "my_llm")
class MyLLMConfig(BaseModel):
    type: Literal["my_llm"] = "my_llm"
    api_key: str
    model: str = "my-model"
```

2. 创建服务实现：

```python
# src/anima/services/llm/implementations/my_llm.py
from anima.services.llm.base import LLMInterface

@ProviderRegistry.register_service("llm", "my_llm")
class MyLLMAgent(LLMInterface):
    @classmethod
    def from_config(cls, config):
        return cls(api_key=config.api_key, model=config.model)

    async def chat_stream(self, text, conversation_history=None):
        async for chunk in your_llm_api_call(text):
            yield chunk
```

3. 添加到 `config/services.yaml`：

```yaml
llm:
  my_llm:
    type: my_llm
    api_key: "${MY_LLM_API_KEY}"
    model: "my-model"
```

详细指南：[添加新服务](docs/development/adding-services.md)

---

## 架构设计

### 数据流

```
用户输入 (文本/音频)
    ↓
InputPipeline (ASR → 清洗 → 情感提取)
    ↓
Agent (LLM 流式对话)
    ↓
OutputPipeline (句子分割 → TTS 合成)
    ↓
EventBus (按优先级分发事件)
    ↓
Handlers (文本/音频/表情处理)
    ↓
前端渲染
```

### 设计模式

| 模式 | 应用场景 |
|------|----------|
| Factory | 服务创建 (LLMFactory, ASRFactory) |
| Strategy | 情感分析器、TTS 调度 |
| Provider Registry | 服务商自动注册 |
| Observer | EventBus 事件系统 |
| Pipeline | 输入/输出数据处理 |
| Orchestrator | 对话流程编排 |

---

## 文档

- [快速开始](docs/development/quickstart.md)
- [添加服务](docs/development/adding-services.md)
- [数据流设计](docs/architecture/data-flow.md)
- [事件系统](docs/architecture/event-system.md) - **面试重点**
- [设计模式](docs/architecture/patterns.md)
- [内存系统](docs/modules/memory.md)
- [实现计划](docs/plans/history.md)

---

## 技术栈

**后端**: Python, FastAPI, Socket.IO

**前端**: Electron, vanilla JS/HTML/CSS, pixi-live2d-display

**AI/ML**: GLM, OpenAI, FasterWhisper, Silero VAD, Chroma

---

## 许可证

MIT License
