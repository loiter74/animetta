# Minecraft AI Gameplay Design

Anima AI 角色在直播中自动控制 Minecraft 角色进行游戏的设计文档。

## 概述

让 Anima 的 AI 角色（VTuber）通过 Mineflayer Bot API 控制 Minecraft Java Edition 中的角色，实现移动、挖掘、建造、战斗、聊天等操作。直播时 OBS 捕获游戏画面，观众可以通过弹幕驱动 AI 在游戏中行动。

## 架构

```
观众弹幕/语音输入
    ↓
Anima LLM (LangGraph)
    ↓ 调用 @tool 装饰的 minecraft tools
Minecraft Tool Bridge (Python)
    ↓ stdio JSON 协议
Mineflayer Bot (Node.js 子进程)
    ↓ Minecraft 协议
Minecraft Java Edition (本地服务器)
    ↓
OBS 直播捕获
```

### 三层结构

1. **Mineflayer Bot** (Node.js) — 独立子进程，直接与 Minecraft 服务器通信
2. **Minecraft Tool Bridge** (Python) — 管理 Bot 进程生命周期，转发命令
3. **Anima LLM Tools** (Python, `@tool`) — 注册到 LangGraph Tool Registry，供 LLM 调用

## 组件设计

### 1. Mineflayer Bot (`src/anima/tools/minecraft/bot/`)

Node.js 脚本，使用 [Mineflayer](https://github.com/PrismarineJS/mineflayer) 库。

**能力矩阵：**

| 能力 | Mineflayer 模块 | 说明 |
|------|----------------|------|
| 移动/寻路 | `mineflayer-pathfinder` | 自动寻路到目标坐标 |
| 挖掘 | `bot.dig()` | 挖掘指定类型的方块 |
| 放置 | `bot.place()` | 在指定位置放置方块 |
| 战斗 | `mineflayer-pvp` | 追踪并攻击实体 |
| 聊天 | `bot.chat()` | 向游戏聊天框发送消息 |
| 采集 | bot.dig + 捡起掉落物 | 自动采集并收集 |
| 状态查询 | bot 内置字段 | 坐标、血量、维度、装备等 |

**通信协议：** 通过 stdin/stdout JSON 行协议。

```json
// 请求 (Anima → Bot)
{"id": 1, "action": "goto", "params": {"x": 100, "y": 64, "z": 200}}
{"id": 2, "action": "mine", "params": {"block_type": "oak_log", "count": 5}}
{"id": 3, "action": "place", "params": {"block_type": "dirt", "x": 100, "y": 65, "z": 200}}
{"id": 4, "action": "attack", "params": {"target": "nearest_hostile"}}
{"id": 5, "action": "chat", "params": {"message": "大家好！我在直播呢！"}}
{"id": 6, "action": "status", "params": {}}

// 响应 (Bot → Anima)
{"id": 1, "status": "success", "result": "Arrived at (100, 64, 200)"}
{"id": 6, "status": "success", "result": {"position": [100, 64, 200], "health": 20, "dimension": "overworld"}}
```

### 2. Minecraft Tool Bridge (`src/anima/tools/minecraft/bridge.py`)

Python 进程管理器。

**职责：**
- 在 Anima 启动时自动 spawn Node.js 子进程
- 通过 subprocess stdin/stdout 发送/接收 JSON 命令
- 异步等待回复（每个请求带唯一 ID，通过 asyncio.Future 匹配）
- Bot 断线自动重连
- Anima 关闭时优雅终止子进程

**状态缓存：**
- 缓存 Bot 最近一次的位置、血量、维度信息，减少重复查询
- Bot 主动推状态更新（位置变化、受到伤害等）

### 3. LLM Tools (`src/anima/tools/minecraft/tools.py`)

LangChain `@tool` 装饰器定义的工具函数。

```python
@tool
async def mc_goto(x: int, y: int, z: int) -> str:
    """Move the Minecraft character to specific coordinates"""

@tool
async def mc_mine(block_type: str, count: int = 1) -> str:
    """Mine blocks of a specific type"""

@tool
async def mc_build(block_type: str, x: int, y: int, z: int) -> str:
    """Place a block at specific coordinates"""

@tool
async def mc_attack(target: str = "nearest_hostile") -> str:
    """Attack a nearby entity"""

@tool
async def mc_chat(message: str) -> str:
    """Send a chat message in the game"""

@tool
async def mc_status() -> str:
    """Get the current status of the Minecraft bot"""
```

## 配置

在 `config/tools.yaml` 中新增：

```yaml
minecraft:
  enabled: false            # 默认关闭，需要手动开启
  bot:
    host: "localhost"
    port: 25565
    username: "AnimaBot"
    version: false           # false = 自动检测
  safety:
    safe_spawn: ~            # 安全重生点（默认使用世界出生点）
    no_griefing: true
    auto_heal: true
    max_distance: 500
```

## 安全约束

- **防破坏 (no_griefing)**：Bot 不会挖掘玩家放置的方块，仅采集自然生成的方块
- **最大活动半径**：限制 Bot 不会跑出以出生点为中心的指定范围
- **自动回血**：血量低于 50% 时自动吃食物
- **防掉落**：检测到脚下是虚空或高空时停止移动
- **掉线重连**：Bot 断开后自动重连，恢复当前状态

## 直播交互模式

1. **观众驱动模式**：观众弹幕 → LLM 理解 → 执行游戏操作 → AI 口述动作
2. **AI 主动模式**：直播冷场时 AI 自主决定做什么（继续手头任务、探索、建造小建筑）
3. **任务序列模式**：复杂指令（"建个小木屋"）拆解为多步任务队列自动执行

## 文件结构

```
src/anima/tools/minecraft/
├── __init__.py
├── bridge.py              # 进程管理 + 通信
├── tools.py               # @tool 工具定义
├── config.py              # Pydantic 配置模型
└── bot/
    ├── package.json       # Node.js 依赖
    └── index.js           # Mineflayer bot 主脚本
```

## 依赖

- **Node.js** (运行时)：mineflayer, mineflayer-pathfinder, mineflayer-pvp, vec3
- **Python**：已内置 asyncio/subprocess
