## Context

Anima 当前的 TTS 架构分为三层：Pydantic 配置类（`config/providers/tts/`）→ `TTSFactory` 实例化（`services/speech/tts/factory.py`）→ `TTSInterface` 实现（`services/speech/tts/`），通过 `ServiceContext.init_tts()` 在运行时根据 `config.tts.type` 动态创建实例。

用户本地有 **RTX 5090D**（NVIDIA Blackwell 架构，24GB+ VRAM），可以本地运行 VibeVoice 模型（1.5B ~6GB / 7B ~16GB）。同时需要一个**双模设计**：既能本地 GPU 推理，也能通过远程 API 调用（适用于其他无 GPU 的场景）。

VibeVoice 官方提供：
- HuggingFace 模型权重（MIT 协议）
- 推理脚本（inference.py）
- 社区有 REST API 包装实现

## Goals / Non-Goals

**Goals:**
- 新增 `vibe_voice` TTS 提供者，支持在 `config/config.yaml` 中 `services.tts: vibe_voice` 切换
- **Local 模式**：RTX 5090D 本地运行 VibeVoice 1.5B/7B 模型，用 HuggingFace transformers + vLLM 或 VibeVoice 官方推理
- **Remote 模式**：通过 HTTP API 调用远程 VibeVoice 服务（兼容未来托管 API）
- 支持多说话人语音合成（最多 4 speaker），利用 VibeVoice 原生能力
- 遵循项目现有的 TTS 接入模式（配置类 + 服务类 + 工厂 + services.yaml）

**Non-Goals:**
- 不改动现有 TTS 接口和基础设施（`TTSInterface`、`ServiceContext`、`tts_node`）
- 不做 VibeVoice 模型训练或微调
- 不支持实时流式合成（VibeVoice 本身为长文本批量设计，实时用 VibeVoice-Realtime-0.5B 但不在本次范围）
- 不修改或迁移 `ServiceContext.init_tts()` 的工厂模式（继续用 `TTSFactory`）

## Decisions

### 1. 双模设计：Local + Remote

| 模式 | 适用场景 | 实现方式 |
|------|---------|---------|
| `local` | RTX 5090D 本机推理 | `subprocess`/`asyncio` 调本地 VibeVoice 推理脚本，通过 stdout / 临时文件获取音频 |
| `remote` | 无 GPU / 分布式 | `httpx.AsyncClient` 调 HTTP API |

**选择依据**：
- VibeVoice 官方没有提供直接的 Python API（不是 pip install 就能用的库），它是一个模型权重 + 推理脚本
- `subprocess` 模式简化依赖：不需要把 torch + transformers 加到 Anima 的 `requirements.txt`，推理进程独立管理
- 未来 VibeVoice 有官方 API 后，`remote` 模式可以无缝对接

### 2. 本地推理架构

```
┌──────────────────────────────────────────┐
│              Anima (主进程)                │
│  VibeVoiceTTS.synthesize(text)            │
│         │                                  │
│         ▼                                  │
│  asyncio.create_subprocess_exec(           │
│    "python", "vibe_infer.py",              │
│    "--text", text, "--output", tmp.wav     │
│  )                                         │
│         │                                  │
│         ▼                                  │
│  等待进程完成 → 读取 tmp.wav → 返回 bytes    │
└──────────────────────────────────────────┘
         │
         │ subprocess
         ▼
┌──────────────────────────────────────────┐
│           vibe_infer.py (独立进程)          │
│  - 加载 VibeVoice 1.5B/7B 模型到 GPU       │
│  - 接收 text + speaker 参数                 │
│  - 合成 → 写入 .wav 到 stdout / 文件        │
│  - 进程退出释放 GPU 显存                     │
└──────────────────────────────────────────┘
```

**注意**：每次调用都新建进程 + 加载模型效率低。优化方案：
- **常驻进程模式**：启动一个长期运行的 VibeVoice HTTP 服务（用 FastAPI / 官方推理 API），Anima 通过 HTTP 调用 → 这其实就是 `remote` 模式，本地部署时也可以启用
- **推荐方案**：本地推理直接用 `remote` 模式 + 本地 FastAPI 包装，避免 subprocess 开销

```
推荐的本地架构：
┌──────────────┐     HTTP      ┌──────────────────┐
│   Anima      │──────────────▶│  VibeVoice Server │
│  (主进程)     │◀──────────────│  (本地 FastAPI)    │
│  remote 模式  │   audio bytes │  GPU 常驻, 模型预热  │
└──────────────┘               └──────────────────┘
```

### 3. 配置结构

```yaml
# config/services.yaml
tts:
  vibe_voice:
    type: vibe_voice
    
    # === 部署模式 ===
    mode: remote              # "local" | "remote"
    
    # === Remote 模式参数 ===
    base_url: "http://localhost:8765"    # 本地推理服务的 API 地址
    api_key: ""                          # 如需要
    
    # === Local 模式参数（仅 mode=local 时使用）===  
    model_size: "1.5b"                   # "1.5b" | "7b"
    model_path: "E:/anima_data/models/VibeVoice"  # 模型权重路径
    device: "cuda:0"
    
    # === 合成参数 ===
    voice: "default"                     # 默认音色
    num_speakers: 1                      # 说话人数 1-4
    language: "zh"                       # "zh" | "en" | "mix"
```

### 4. 配置类设计

```python
@ProviderRegistry.register("tts", "vibe_voice")
class VibeVoiceTTSConfig(TTSBaseConfig):
    type: Literal["vibe_voice"] = "vibe_voice"
    mode: str = Field(default="remote", description="部署模式: local / remote")
    
    # Remote
    base_url: str = Field(default="http://localhost:8765")
    api_key: Optional[str] = None
    
    # Local
    model_size: str = Field(default="1.5b")
    model_path: Optional[str] = None
    device: str = Field(default="cuda:0")
    
    # Synthesis
    voice: str = Field(default="default")
    num_speakers: int = Field(default=1, ge=1, le=4)
    language: str = Field(default="zh")
```

### 5. 服务类设计

```python
@ProviderRegistry.register_service("tts", "vibe_voice")
class VibeVoiceTTS(TTSInterface):
    def __init__(self, mode="remote", base_url=None, model_size="1.5b", ...):
        ...
    
    async def synthesize(self, text, output_path=None, voice=None, **kwargs) -> Union[bytes, str]:
        if self.mode == "remote":
            return await self._synthesize_remote(text, output_path, voice)
        else:
            return await self._synthesize_local(text, output_path, voice)
    
    async def _synthesize_remote(self, text, output_path, voice):
        # httpx POST → audio bytes
        ...
    
    async def _synthesize_local(self, text, output_path, voice):
        # subprocess 调本地推理脚本
        ...
    
    async def close(self):
        ...
```

### 6. 文件改动清单

| # | 文件 | 操作 |
|---|------|------|
| 1 | `src/anima/config/providers/tts/vibe_voice.py` | 新建配置类 |
| 2 | `src/anima/config/providers/tts/__init__.py` | 加入 Union |
| 3 | `src/anima/services/speech/tts/vibe_voice_tts.py` | 新建服务实现 |
| 4 | `src/anima/services/speech/tts/factory.py` | 加 elif 分支 |
| 5 | `src/anima/services/speech/tts/__init__.py` | 导出新类 |
| 6 | `config/services.yaml` | 加配置项 |
| 7 | `scripts/setup_vibevoice.py` (可选) | 一键下载模型脚本 |

## Risks / Trade-offs

- **[性能] subprocess 调用延迟**: 每次 synthesize 都启动子进程加载模型 → **Mitigation**: 推荐使用 remote 模式 + 本地常驻推理服务，subprocess 模式作为 fallback
- **[依赖体积] torch + transformers**: 本地推理模式下需要 ~5GB 的 Python 包 → **Mitigation**: 不作为核心依赖，仅在 local 模式时按需导入，文档说明
- **[模型权重] 下载体积**: VibeVoice 权重 ~3-15GB → **Mitigation**: 提供自动下载脚本，模型文件放在独立目录
- **[兼容性] 双模测试**: 两种模式需要分别测试 → **Mitigation**: remote 模式可 mock 测试，local 模式需要 GPU 环境
- **[流式] 不支持实时**: VibeVoice 是批量推理模型，不适合逐字流式 → **Mitigation**: 不做流式，只做完整句子合成（当前 graph 的 tts_node 本身就是一次合成整句）
