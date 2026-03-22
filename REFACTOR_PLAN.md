# Anima 目录重构方案

## 现状分析

```
src/anima/
├── avatar/           # 17 files - 结构松散
├── config/           # 38 files - 过大
├── graph/            # 14 files - 结构合理 ✅
├── memory/           # 16 files - 结构混乱
├── server/           # 7 files
├── services/         # 42 files - 过大
├── tools/            # 6 files
└── utils/            # 4 files
```

## 目标结构

```
src/anima/
├── core/                          # 核心模块
│   ├── __init__.py
│   ├── socketio_server.py         # 从根目录移入
│   ├── service_context.py         # 从根目录移入
│   └── config/
│       ├── app.py                 # 应用配置
│       ├── system.py              # 系统配置
│       └── user_settings.py       # 用户设置
│
├── orchestration/                 # 编排层
│   ├── __init__.py
│   ├── graph/                     # LangGraph 状态图
│   │   ├── __init__.py
│   │   ├── builder.py
│   │   ├── orchestrator.py
│   │   ├── state.py
│   │   ├── nodes/                 # 图节点
│   │   ├── config_store.py
│   │   ├── tool_manager.py
│   │   └── interrupt_handler.py
│   └── server/                    # WebSocket 服务器
│       ├── __init__.py
│       ├── routes.py
│       ├── session.py
│       ├── websocket.py
│       ├── lifecycle.py
│       ├── desktop.py
│       └── live2d.py
│
├── services/                      # 服务层（按功能分组）
│   ├── __init__.py
│   ├── speech/                    # 语音相关
│   │   ├── __init__.py
│   │   ├── asr/                   # 语音识别
│   │   │   ├── interface.py
│   │   │   ├── factory.py
│   │   │   └── implementations/
│   │   └── tts/                   # 语音合成
│   │       ├── interface.py
│   │       ├── factory.py
│   │       └── implementations/
│   ├── intelligence/              # AI 相关
│   │   ├── __init__.py
│   │   ├── llm/                   # 大语言模型
│   │   │   ├── interface.py
│   │   │   ├── factory.py
│   │   │   ├── langchain_adapter.py
│   │   │   └── implementations/
│   │   └── vad/                   # 语音活动检测
│   │       ├── interface.py
│   │       ├── factory.py
│   │       └── implementations/
│   ├── audio/                     # 音频处理
│   │   ├── __init__.py
│   │   ├── processor.py
│   │   └── implementations/
│   └── live2d/                    # Live2D 控制
│       ├── __init__.py
│       ├── action_queue.py
│       ├── viseme_sync.py
│       └── preset_loader.py
│
├── expression/                    # 表情系统（重命名 avatar）
│   ├── __init__.py
│   ├── analyzers/                 # 情感分析
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── keyword.py
│   │   ├── llm_tag.py
│   │   └── audio.py
│   ├── mappers/                   # 参数映射
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── emotion_param_mapper.py
│   ├── strategies/                # 时间轴策略
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── intensity.py
│   │   ├── duration.py
│   │   └── position.py
│   ├── factory.py
│   └── prompts.py
│
├── memory/                        # 记忆系统（重组）
│   ├── __init__.py
│   ├── manager.py                 # 主入口（从 memory_manager.py）
│   ├── system.py                  # 记忆系统（从 memory_system.py）
│   ├── stores/                    # 存储层
│   │   ├── __init__.py
│   │   ├── long_term.py           # 长期记忆
│   │   └── short_term.py          # 短期记忆
│   ├── search/                    # 搜索层
│   │   ├── __init__.py
│   │   ├── hybrid.py              # 混合搜索
│   │   ├── scorer.py
│   │   └── prompt_builder.py
│   ├── storage/                   # 底层存储
│   │   ├── __init__.py
│   │   ├── sqlite_store.py
│   │   └── chroma_store.py
│   └── models/                    # 数据模型
│       ├── __init__.py
│       ├── chunks.py              # 合并 chunker.py + models.py
│       └── turns.py               # 从 memory_turn.py
│
├── tools/                         # 工具系统
│   ├── __init__.py
│   ├── base.py                    # 内置工具
│   ├── custom_tools.py
│   ├── langchain_tools.py
│   ├── config.py
│   └── mcp/                       # MCP 协议
│       ├── __init__.py
│       └── bridge.py              # 从 mcp_bridge.py
│
└── utils/                         # 工具函数
    ├── __init__.py
    ├── env.py                     # 从 env_helper.py
    ├── auto_config.py
    └── logger.py                  # 从 logger_manager.py
```

## 配置目录拆分

```
config/
├── __init__.py
├── app.py                         # AppConfig
├── system.py                      # SystemConfig
├── user_settings.py               # UserSettings
├── live2d.py                      # Live2DConfig
│
└── providers/                     # 提供者配置
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── base.py                # BaseConfig
    │   └── registry.py            # ProviderRegistry
    │
    ├── llm/                       # LLM 配置
    │   ├── __init__.py
    │   ├── base.py
    │   ├── glm.py
    │   ├── openai.py
    │   ├── ollama.py
    │   └── local_lora.py
    │
    ├── asr/                       # ASR 配置
    ├── tts/                       # TTS 配置
    └── vad/                       # VAD 配置
```

## 前端重构

```
frontend/
├── main/                          # Electron 主进程
│   ├── index.js
│   ├── audio/
│   ├── config/
│   ├── windows/                   # 窗口管理
│   │   ├── WindowManager.js
│   │   ├── Live2DWindow.js
│   │   └── ChatWindow.js
│   └── ipc/                       # IPC 处理器
│       ├── IpcBridge.js           # 主桥接
│       └── handlers/
│           ├── live2d.js
│           ├── chat.js
│           └── display.js
│
├── renderer/                      # 渲染进程
│   ├── live2d/                    # Live2D 窗口
│   │   ├── index.js
│   │   ├── renderer/
│   │   │   ├── ExpressionController.js
│   │   │   ├── ScaleManager.js
│   │   │   └── BackgroundManager.js
│   │   ├── core/
│   │   │   ├── PixiApp.js
│   │   │   └── ModelLoader.js
│   │   └── ipc/
│   │
│   ├── chat/                      # 聊天窗口
│   │   ├── index.js
│   │   ├── ChatWindow.js          # 主窗口
│   │   ├── audio/
│   │   │   └── AudioCapture.js
│   │   ├── state/
│   │   │   └── ChatState.js
│   │   ├── ui/                    # UI 组件
│   │   │   ├── MessageList.js
│   │   │   ├── InputBar.js
│   │   │   ├── VoiceButton.js
│   │   │   └── TypingIndicator.js
│   │   └── ipc/
│   │       └── IpcListeners.js
│   │
│   └── shared/                    # 共享模块
│       ├── constants.js
│       ├── ipcChannels.js
│       └── utils.js               # 新增：工具函数
│
├── web/                           # Web 配置面板
│   └── static/
│       └── js/
│           ├── config.js          # 主入口
│           ├── socket.js          # Socket.IO
│           ├── state.js           # 状态管理
│           └── ui.js              # UI 渲染
│
├── preload/
│   └── index.js
│
└── public/                        # 静态资源
    └── live2d/
```

## 迁移计划

### 阶段 1: 后端核心模块
1. 创建 `src/anima/core/` 目录
2. 移动 `socketio_server.py` 和 `service_context.py`
3. 拆分 `config/` 目录

### 阶段 2: 服务层重组
1. 创建 `src/anima/services/speech/`, `intelligence/`, `audio/`
2. 移动现有实现文件
3. 更新导入路径

### 阶段 3: 记忆系统重组
1. 创建 `memory/stores/`, `memory/search/`, `memory/storage/`
2. 合并 `chunker.py` 和 `models.py`
3. 重命名 `memory_manager.py` → `manager.py`

### 阶段 4: 表情系统重命名
1. 重命名 `avatar/` → `expression/`
2. 更新所有引用

### 阶段 5: 前端重组
1. 创建 `renderer/shared/`
2. 统一 IPC 处理器
3. 更新导入路径

## 影响评估

### 需要更新的文件
- 所有 `from anima.xxx import` 导入
- 配置文件路径
- 前端 import 语句

### 风险
- 大量文件移动可能导致 git 历史混乱
- 建议使用 `git mv` 保留历史

### 预期收益
- 目录结构更清晰直观
- 模块职责更明确
- 新人更容易理解项目
