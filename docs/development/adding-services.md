# 添加新服务

零修改扩展 LLM/ASR/TTS/VAD 服务的指南。

---

## 扩展概述

Anima 使用 **Provider Registry Pattern** 实现零修改扩展：

```
@ProviderRegistry.register_config()  ← 注册配置类
        ↓
@ProviderRegistry.register_service()  ← 注册服务类
        ↓
YAML 配置文件  ← 服务配置
        ↓
Factory.create()  ← 工厂创建
```

### 支持的服务类型

| 类型 | 接口 | 用途 |
|------|------|------|
| LLM | `LLMInterface` | 对话生成 |
| ASR | `ASRInterface` | 语音识别 |
| TTS | `TTSInterface` | 语音合成 |
| VAD | `VADInterface` | 语音活动检测 |

---

## 扩展步骤

### 步骤 1：定义配置类

1. 使用 `@ProviderRegistry.register_config()` 装饰器
2. 定义 `type` 字段
3. 继承自 `BaseModel`
4. 定义必要参数（API 密钥、模型名称等）

**文件位置**: `src/anima/config/providers/{service_type}/{provider_name}.py`

### 步骤 2：实现服务类

1. 使用 `@ProviderRegistry.register_service()` 装饰器
2. 实现接口方法
3. 提供 `from_config()` 类方法
4. 处理流式响应（`yield str` 返回文本片段）

**文件位置**: `src/anima/services/{service_type}/implementations/{provider_name}.py`

### 步骤 3：创建配置文件

在 `config/services.yaml` 中添加配置：

```yaml
{service_type}:
  {provider_name}:
    type: "{provider_name}"
    api_key: "${API_KEY}"  # 从环境变量读取
    model: "model-name"
    # ... 其他参数
```

### 步骤 4：导出服务类

更新 `src/anima/services/{service_type}/implementations/__init__.py` 导出类。

---

## 接口说明

### LLM 接口

```python
class LLMInterface(ABC):
    @abstractmethod
    async def chat_stream(
        self,
        text: str,
        conversation_history: List[Dict] = None
    ) -> AsyncIterator[str | dict]:
        """流式对话"""
        pass
```

### ASR 接口

```python
class ASRInterface(ABC):
    @abstractmethod
    async def transcribe(self, audio_data: np.ndarray) -> str:
        """音频转文本"""
        pass
```

### TTS 接口

```python
class TTSInterface(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> str:
        """文本转语音，返回音频文件路径"""
        pass
```

### VAD 接口

```python
class VADInterface(ABC):
    @abstractmethod
    async def detect(self, audio_chunk: np.ndarray) -> bool:
        """检测语音活动"""
        pass
```

---

## 验证注册

```python
from anima.config.core.registry import ProviderRegistry

# 列出所有已注册的提供者
print(ProviderRegistry.get_providers("llm"))
# 输出: ["openai", "glm", "ollama", "mock", "your_provider"]
```

---

## 关键要点

1. **装饰器**：必须使用 `@ProviderRegistry.register_config()` 和 `@ProviderRegistry.register_service()`
2. **类型字段**：配置类必须定义 `type: Literal["provider_name"]`
3. **工厂方法**：服务类必须实现 `from_config()` 类方法
4. **接口方法**：服务类必须实现接口的 `async` 方法
5. **配置文件**：YAML 配置的 `type` 必须匹配注册名称
