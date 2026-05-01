# Anima

<div align="center">

![Anima Chat Demo](assets/demo/anima-chat-preview.gif)

**打造你的专属 AI 虚拟角色！** 🎭

支持 Live2D 动画、实时语音交互，可自由切换不同 AI 模型

[![Test](https://github.com/loiter74/Anima-LLM-Vtuber/actions/workflows/test.yml/badge.svg)](https://github.com/loiter74/Anima-LLM-Vtuber/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/python-3.12%20|%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## ✨ 为什么选择 Anima？

<div align="center">

### 🎭 会"动"的虚拟角色

Live2D 角色会根据对话内容改变表情和动作，仿佛有真正的灵魂

### 💬 自然流畅的对话

支持文本和语音双模态输入，像和朋友聊天一样自然

### 🔄 随心切换 AI 模型

无需修改代码，一键切换不同的 LLM/ASR/TTS 服务商

</div>

---

## 🚀 3 步开始体验

### 1️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 2️⃣ 配置 API Key

创建 `.env` 文件，添加你的 API 密钥：

```bash
GLM_API_KEY=your_api_key_here
```

### 3️⃣ 启动应用

```bash
python scripts/start.py
```

打开桌面应用，开始和你的 AI 角色聊天吧！

---

## 🎮 核心特性

### 智能对话引擎
- AI 实时理解并生成自然语言回复
- 支持流式输出，边说边显示
- 长期记忆功能，记住你们的对话历史

### 生动角色表现
- **表情同步** - 角色会根据对话情绪展现不同表情
- **唇型同步** - 说话时嘴巴动作与语音完美匹配
- **动作控制** - 支持自定义触发动作和姿势

### 灵活配置选择
- **多种 AI 模型** - GLM、OpenAI、Ollama、本地模型等
- **语音输入输出** - 可选语音识别和合成服务
- **自定义人设** - 创建独一无二的角色性格

---

## 🛠️ 支持的服务

| 类型 | 支持的服务 |
|:----:|:----------|
| **🧠 AI 模型** | GLM、OpenAI、Ollama、本地 LoRA |
| **🎤 语音识别** | FasterWhisper、GLM、OpenAI |
| **🔊 语音合成** | Edge TTS、GLM、OpenAI、ChatTTS |
| **🎯 语音检测** | Silero VAD |

---

## 📝 配置示例

### 切换 AI 模型

编辑 `config/config.yaml`：

```yaml
services:
  agent: glm           # 可选: glm, openai, ollama, local_lora
  asr: faster_whisper  # 可选: faster_whisper, glm, openai
  tts: edge            # 可选: edge, glm, openai, chattts
```

### 自定义角色性格

创建 `config/personas/my-character.yaml`：

```yaml
identity: "你的角色名"
personality: "活泼开朗，喜欢开玩笑"
speaking_style: "使用轻松的语气，偶尔加emoji"
```

---

## 🎬 完整演示

**[点击查看高清演示 →](assets/demo/anima-chat-demo.gif)** (1.2MB GIF)

演示内容：
- ✅ AI 实时对话响应
- ✅ Live2D 角色表情和动作变化
- ✅ 流畅的低延迟交互体验
- ✅ 文本和语音双模态输入

---

## 🛠️ 技术栈

**后端**: Python、FastAPI、Socket.IO

**前端**: Electron、原生 JS、pixi-live2d-display

**AI 服务**: GLM、OpenAI、FasterWhisper、Silero VAD、Chroma

---

## 📚 详细文档

<details>
<summary><b>📖 展开开发者文档</b></summary>

### 项目结构

```
src/anima/
├── socketio_server.py    # 主服务器入口
├── service_context.py    # 服务容器管理
├── config/               # 配置系统
│   ├── core/registry.py  # 服务注册表
│   └── providers/        # 服务商配置类
├── adapters/             # 通道适配器层
├── services/             # 服务实现 (LLM/ASR/TTS/VAD)
├── pipeline/             # 数据处理管道
├── events/               # 事件驱动架构
├── handlers/             # 事件处理器
├── memory/               # 对话记忆系统
└── avatar/               # Live2D 表情分析
```

### 数据流架构

```
用户输入 (文本/音频)
    ↓
InputPipeline (语音识别 → 文本清洗)
    ↓
Agent (LLM 流式对话)
    ↓
OutputPipeline (句子分割 → TTS 合成 → 情感提取)
    ↓
EventBus (按优先级分发事件)
    ↓
前端渲染 (文字显示 + 语音播放 + Live2D 动作)
```

### 扩展开发

#### 添加新的 LLM 服务

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

更多文档：
- [快速开始指南](docs/development/quickstart.md)
- [添加新服务](docs/development/adding-services.md)
- [数据流设计](docs/architecture/data-flow.md)
- [事件系统](docs/architecture/event-system.md)
- [设计模式](docs/architecture/patterns.md)
- [内存系统](docs/modules/memory.md)

</details>

---

## 📄 许可证

MIT License - 自由使用、修改和分发
