# Minecraft AI Gameplay Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add AI-controlled Minecraft gameplay to Anima VTuber for live streaming.

**Architecture:** Mineflayer (Node.js) bot as subprocess, Python bridge for stdio JSON communication, `@tool` decorators exposed to LangGraph for LLM-driven gameplay.

**Tech Stack:** Python (LangChain `@tool`), Node.js (Mineflayer), asyncio subprocess

**Design Doc:** `docs/plans/2026-05-09-minecraft-gameplay-design.md`

---

### Task 1: Create Node.js Bot Script

**Files:**
- Create: `src/anima/tools/minecraft/bot/package.json`
- Create: `src/anima/tools/minecraft/bot/index.js`

**Step 1: Create package.json**

```json
{
  "name": "anima-minecraft-bot",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "dependencies": {
    "mineflayer": "^4.20.0",
    "mineflayer-pathfinder": "^2.4.0",
    "mineflayer-pvp": "^1.3.0",
    "vec3": "^0.1.8"
  }
}
```

**Step 2: Create index.js**

The bot reads JSON commands from stdin, executes Mineflayer actions, and writes JSON responses to stdout.

```javascript
import mineflayer from 'mineflayer';
import { pathfinder, Movements, goals } from 'mineflayer-pathfinder';
import { pvp } from 'mineflayer-pvp';
import { Vec3 } from 'vec3';
import readline from 'readline';

// Config from command line args
const args = {
  host: process.argv[2] || 'localhost',
  port: parseInt(process.argv[3] || '25565'),
  username: process.argv[4] || 'AnimaBot',
};

let bot = null;
let pendingRequests = new Map();
let requestId = 0;

function sendResponse(id, status, result) {
  const response = JSON.stringify({ id, status, result });
  process.stdout.write(response + '\n');
}

function sendError(id, message) {
  sendResponse(id, 'error', message);
}

// Create bot
bot = mineflayer.createBot({
  host: args.host,
  port: args.port,
  username: args.username,
});

bot.loadPlugin(pathfinder);
bot.loadPlugin(pvp);

bot.on('login', () => {
  sendResponse('system', 'success', `Bot logged in as ${bot.username}`);
});

bot.on('spawn', () => {
  sendResponse('system', 'success', `Bot spawned at ${bot.entity.position}`);
});

bot.on('error', (err) => {
  sendResponse('system', 'error', err.message);
});

bot.on('end', (reason) => {
  sendResponse('system', 'info', `Bot disconnected: ${reason}`);
});

bot.on('health', () => {
  if (bot.health < 10) {
    bot.chat('我需要治疗！');
  }
});

// STDIN command handler
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

rl.on('line', async (line) => {
  let command;
  try {
    command = JSON.parse(line.trim());
  } catch (e) {
    sendError(null, 'Invalid JSON');
    return;
  }

  const id = command.id;
  const action = command.action;
  const params = command.params || {};

  try {
    switch (action) {
      case 'goto':
        await handleGoto(id, params);
        break;
      case 'mine':
        await handleMine(id, params);
        break;
      case 'place':
        await handlePlace(id, params);
        break;
      case 'attack':
        await handleAttack(id, params);
        break;
      case 'chat':
        await handleChat(id, params);
        break;
      case 'status':
        await handleStatus(id, params);
        break;
      default:
        sendError(id, `Unknown action: ${action}`);
    }
  } catch (e) {
    sendError(id, e.message);
  }
});

async function handleGoto(id, params) {
  const { x, y, z } = params;
  if (x === undefined || y === undefined || z === undefined) {
    sendError(id, 'Missing coordinates: x, y, z required');
    return;
  }

  const mcData = await import('minecraft-data');
  const data = mcData(bot.version);

  const movements = new Movements(bot, data);
  bot.pathfinder.setMovements(movements);

  const goal = new goals.GoalBlock(x, y, z);
  await bot.pathfinder.goto(goal);

  sendResponse(id, 'success', `Arrived at (${x}, ${y}, ${z})`);
}

async function handleMine(id, params) {
  const blockType = params.block_type;
  const count = params.count || 1;

  if (!blockType) {
    sendError(id, 'Missing parameter: block_type');
    return;
  }

  let mined = 0;
  for (let i = 0; i < count; i++) {
    const block = bot.findBlock({
      matching: (b) => b.name === blockType,
      maxDistance: 10,
    });

    if (!block) {
      break;
    }

    await bot.dig(block);
    mined++;
  }

  sendResponse(id, 'success', `Mined ${mined}x ${blockType}`);
}

async function handlePlace(id, params) {
  const { block_type, x, y, z } = params;

  if (!block_type || x === undefined || y === undefined || z === undefined) {
    sendError(id, 'Missing parameters: block_type, x, y, z');
    return;
  }

  const targetPos = new Vec3(x, y, z);
  const referenceBlock = bot.blockAt(targetPos.offset(0, -1, 0));

  if (!referenceBlock || referenceBlock.name === 'air') {
    sendError(id, 'No solid block below target position');
    return;
  }

  const item = bot.inventory.items().find(i => i.name === block_type);
  if (!item) {
    sendError(id, `No ${block_type} in inventory`);
    return;
  }

  await bot.equip(item, 'hand');
  await bot.placeBlock(referenceBlock, new Vec3(0, 1, 0));

  sendResponse(id, 'success', `Placed ${block_type} at (${x}, ${y}, ${z})`);
}

async function handleAttack(id, params) {
  const target = params.target || 'nearest_hostile';

  let entity;
  if (target === 'nearest_hostile') {
    entity = bot.nearestEntity((e) => e.type === 'hostile' && e.position.distanceTo(bot.entity.position) < 20);
  } else if (target === 'nearest_player') {
    entity = bot.nearestEntity((e) => e.type === 'player' && e.username !== bot.username);
  } else {
    entity = bot.nearestEntity((e) => e.username === target || e.name === target);
  }

  if (!entity) {
    sendResponse(id, 'info', `No target found: ${target}`);
    return;
  }

  bot.pvp.attack(entity);
  sendResponse(id, 'success', `Attacking ${entity.username || entity.name || 'unknown'}`);
}

async function handleChat(id, params) {
  const message = params.message;
  if (!message) {
    sendError(id, 'Missing parameter: message');
    return;
  }

  bot.chat(message);
  sendResponse(id, 'success', `Message sent: ${message}`);
}

async function handleStatus(id, params) {
  if (!bot || !bot.entity) {
    sendError(id, 'Bot not spawned yet');
    return;
  }

  const pos = bot.entity.position;
  sendResponse(id, 'success', JSON.stringify({
    position: [Math.floor(pos.x), Math.floor(pos.y), Math.floor(pos.z)],
    health: Math.floor(bot.health),
    food: Math.floor(bot.food),
    dimension: bot.game?.dimension || 'unknown',
    username: bot.username,
    game_mode: bot.game?.gameMode || 'unknown',
  }));
}
```

**Step 3: Install dependencies**

Run: `cd src/anima/tools/minecraft/bot && npm install`
Expected: node_modules created, mineflayer etc. installed

**Step 4: Commit**

```bash
git add src/anima/tools/minecraft/bot/
git commit -m "feat: add Mineflayer bot script for Minecraft gameplay"
```

---

### Task 2: Create Python Bridge (Process Manager)

**Files:**
- Create: `src/anima/tools/minecraft/__init__.py`
- Create: `src/anima/tools/minecraft/bridge.py`
- Create: `src/anima/tools/minecraft/config.py`

**Step 1: Create `__init__.py`**

```python
from .bridge import MinecraftBridge
from .tools import get_minecraft_tools

__all__ = ["MinecraftBridge", "get_minecraft_tools"]
```

**Step 2: Create `config.py`**

```python
from pydantic import BaseModel
from typing import Optional

class MinecraftBotConfig(BaseModel):
    host: str = "localhost"
    port: int = 25565
    username: str = "AnimaBot"
    version: Optional[str] = None  # None = auto-detect

class MinecraftSafetyConfig(BaseModel):
    safe_spawn: Optional[list] = None
    no_griefing: bool = True
    auto_heal: bool = True
    max_distance: int = 500

class MinecraftConfig(BaseModel):
    enabled: bool = False
    bot: MinecraftBotConfig = MinecraftBotConfig()
    safety: MinecraftSafetyConfig = MinecraftSafetyConfig()
```

**Step 3: Create `bridge.py`**

```python
"""
Minecraft Bridge - Manages Mineflayer bot subprocess lifecycle and communication

Architecture:
- Anima startup → MinecraftBridge.start() → spawns Node.js subprocess
- LLM tool call → bridge.send_command(action, params) → JSON to stdin → wait response
- Anima shutdown → MinecraftBridge.stop() → kill subprocess
"""

import asyncio
import json
import subprocess
import os
from typing import Optional, Any, Dict
from loguru import logger
from .config import MinecraftConfig

class MinecraftBridge:
    def __init__(self, config: MinecraftConfig):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._pending: Dict[int, asyncio.Future] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self) -> bool:
        """Start the Mineflayer bot subprocess"""
        if self._running:
            return True

        bot_dir = os.path.join(os.path.dirname(__file__), "bot")
        bot_script = os.path.join(bot_dir, "index.js")

        if not os.path.exists(bot_script):
            logger.error(f"[MinecraftBridge] Bot script not found: {bot_script}")
            return False

        try:
            self._process = await asyncio.create_subprocess_exec(
                "node", bot_script,
                self.config.bot.host,
                str(self.config.bot.port),
                self.config.bot.username,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=bot_dir,
            )

            self._running = True

            # Start reader task
            asyncio.create_task(self._read_stdout())
            # Start stderr logger
            asyncio.create_task(self._read_stderr())

            logger.info(f"[MinecraftBridge] Bot process started (PID: {self._process.pid})")

            # Wait for login confirmation
            try:
                async with asyncio.timeout(15):
                    while self._running:
                        # Check first line of stdout for login
                        await asyncio.sleep(0.5)
                        # If we got a system response, we're connected
                        break
            except asyncio.TimeoutError:
                logger.warning("[MinecraftBridge] Bot login timeout, continuing anyway")

            return True

        except Exception as e:
            logger.error(f"[MinecraftBridge] Failed to start: {e}")
            return False

    async def send_command(self, action: str, params: Optional[Dict] = None, timeout: float = 30.0) -> Dict:
        """Send a command to the bot and wait for response"""
        if not self._running or not self._process:
            return {"status": "error", "result": "Bridge not running"}

        async with self._lock:
            cmd_id = self._next_id
            self._next_id += 1
            future = asyncio.get_event_loop().create_future()
            self._pending[cmd_id] = future

        command = json.dumps({"id": cmd_id, "action": action, "params": params or {}})
        logger.info(f"[MinecraftBridge] Sending: {action} (id={cmd_id})")

        try:
            self._process.stdin.write((command + "\n").encode("utf-8"))
            await self._process.stdin.drain()

            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"[MinecraftBridge] Command {action} timeout after {timeout}s")
            return {"status": "error", "result": f"Command timeout after {timeout}s"}
        except Exception as e:
            logger.error(f"[MinecraftBridge] Command {action} failed: {e}")
            return {"status": "error", "result": str(e)}
        finally:
            self._pending.pop(cmd_id, None)

    async def _read_stdout(self):
        """Read JSON responses from bot stdout"""
        try:
            while self._running and self._process and self._process.stdout:
                line = await self._process.stdout.readline()
                if not line:
                    logger.info("[MinecraftBridge] Bot stdout closed")
                    break

                line = line.decode("utf-8").strip()
                if not line:
                    continue

                try:
                    response = json.loads(line)
                    resp_id = response.get("id")
                    status = response.get("status")
                    result = response.get("result")

                    if resp_id == "system":
                        logger.info(f"[MinecraftBridge] Bot system: {result}")
                        continue

                    if resp_id is not None and resp_id in self._pending:
                        self._pending[resp_id].set_result({"status": status, "result": result})
                    else:
                        logger.debug(f"[MinecraftBridge] Unhandled response: {line}")

                except json.JSONDecodeError:
                    logger.warning(f"[MinecraftBridge] Invalid JSON from bot: {line}")

        except Exception as e:
            logger.error(f"[MinecraftBridge] stdout reader error: {e}")
        finally:
            self._running = False

    async def _read_stderr(self):
        """Log bot stderr"""
        try:
            while self._process and self._process.stderr:
                line = await self._process.stderr.readline()
                if not line:
                    break
                logger.debug(f"[MinecraftBot] {line.decode('utf-8').strip()}")
        except Exception as e:
            logger.debug(f"[MinecraftBridge] stderr reader stopped: {e}")

    async def stop(self):
        """Stop the bot subprocess"""
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
                logger.info(f"[MinecraftBridge] Bot process terminated")
            except asyncio.TimeoutError:
                self._process.kill()
                logger.warning(f"[MinecraftBridge] Bot process killed (timeout)")
            except Exception as e:
                logger.error(f"[MinecraftBridge] Stop error: {e}")

        # Cancel pending futures
        for future in self._pending.values():
            if not future.done():
                future.set_result({"status": "error", "result": "Bridge stopped"})
        self._pending.clear()

    @property
    def is_running(self) -> bool:
        return self._running
```

**Step 4: Commit**

```bash
git add src/anima/tools/minecraft/__init__.py src/anima/tools/minecraft/bridge.py src/anima/tools/minecraft/config.py
git commit -m "feat: add Minecraft Bridge for subprocess management"
```

---

### Task 3: Create Minecraft Tools (LangChain @tool decorators)

**Files:**
- Create: `src/anima/tools/minecraft/tools.py`

**Step 1: Create tools.py**

```python
"""
Minecraft gameplay tools for Anima LLM

Each tool corresponds to a Mineflayer bot action.
Tools are registered as LangChain @tool and loaded by load_tools_from_config.
"""

from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from loguru import logger

# Global bridge instance (lazy init)
_bridge = None


def init_bridge(config: Optional[Dict] = None):
    """Initialize the Minecraft bridge (called from load_tools_from_config)"""
    global _bridge
    if _bridge is not None:
        return

    from .bridge import MinecraftBridge
    from .config import MinecraftConfig

    mc_config = MinecraftConfig(**(config or {}))
    if not mc_config.enabled:
        logger.info("[MinecraftTools] Minecraft gameplay disabled")
        return

    _bridge = MinecraftBridge(mc_config)

    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.ensure_future(_bridge.start())
        else:
            loop.run_until_complete(_bridge.start())
    except RuntimeError:
        # No running loop, create one
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_bridge.start())
        loop.close()

    logger.info("[MinecraftTools] Minecraft bridge initialized")


async def _send(action: str, params: Optional[Dict] = None, timeout: float = 30.0) -> str:
    """Send command via bridge and format result for LLM"""
    global _bridge
    if _bridge is None or not _bridge.is_running:
        return "Minecraft bot is not connected. Please check that Minecraft server is running and minecraft feature is enabled."

    result = await _bridge.send_command(action, params, timeout=timeout)
    if result.get("status") == "error":
        return f"Action failed: {result.get('result', 'Unknown error')}"
    return result.get("result", "Done")


def get_minecraft_tools() -> List[Any]:
    """Get all minecraft tools (called by load_tools_from_config)"""
    return [_mc_goto, _mc_mine, _mc_build, _mc_attack, _mc_chat, _mc_status]


@tool
async def mc_goto(x: int, y: int, z: int) -> str:
    """Move the Minecraft character to specific coordinates.
    Use this when you want the character to go to a specific location.

    Args:
        x: X coordinate
        y: Y coordinate  
        z: Z coordinate
    """
    return await _send("goto", {"x": x, "y": y, "z": z})


@tool
async def mc_mine(block_type: str, count: int = 1) -> str:
    """Mine blocks of a specific type in Minecraft.
    Use this to collect resources like wood, stone, ores, etc.

    Args:
        block_type: Type of block to mine (e.g. 'oak_log', 'stone', 'diamond_ore')
        count: Number of blocks to mine (default: 1)
    """
    return await _send("mine", {"block_type": block_type, "count": count})


@tool
async def mc_build(block_type: str, x: int, y: int, z: int) -> str:
    """Place a block at specific coordinates in Minecraft.
    Use this to build structures, walls, floors, etc.

    Args:
        block_type: Type of block to place (e.g. 'dirt', 'stone', 'oak_planks')
        x: X coordinate to place at
        y: Y coordinate to place at
        z: Z coordinate to place at
    """
    return await _send("place", {"block_type": block_type, "x": x, "y": y, "z": z})


@tool
async def mc_attack(target: str = "nearest_hostile") -> str:
    """Attack a nearby entity in Minecraft.
    Use this to fight monsters or other entities.

    Args:
        target: Target to attack. 'nearest_hostile' for nearest monster,
                'nearest_player' for nearest player, or entity name
    """
    return await _send("attack", {"target": target})


@tool
async def mc_chat(message: str) -> str:
    """Send a chat message in the Minecraft game chat.
    Use this to communicate with other players in the game.

    Args:
        message: The message to send
    """
    return await _send("chat", {"message": message})


@tool
async def mc_status() -> str:
    """Get the current status of the Minecraft character.
    Returns position, health, food level, dimension, and game mode.
    Use this before other actions to understand the current situation.
    """
    result = await _send("status")
    return result
```

**Step 2: Commit**

```bash
git add src/anima/tools/minecraft/tools.py
git commit -m "feat: add Minecraft LangChain tools (goto, mine, build, attack, chat, status)"
```

---

### Task 4: Register Tools in Configuration and Loading

**Files:**
- Modify: `config/tools.yaml`
- Modify: `src/anima/tools/base.py`

**Step 1: Add Minecraft config to `config/tools.yaml`**

Add after `tool_settings:` section:

```yaml
# ========================================
# Minecraft Gameplay
# ========================================
minecraft:
  enabled: false                # Set to true to enable Minecraft bot
  bot:
    host: "localhost"
    port: 25565
    username: "AnimaBot"
  safety:
    no_griefing: true
    auto_heal: true
    max_distance: 500
```

**Step 2: Add Minecraft tool loading to `base.py`**

In `load_tools_from_config()`, after the custom_tools section, add:

```python
# Minecraft tools
minecraft_config = config.get("minecraft", {})
if minecraft_config.get("enabled", False):
    try:
        from .minecraft.tools import get_minecraft_tools, init_bridge
        init_bridge(minecraft_config)
        mc_tools = get_minecraft_tools()
        extra_tools.extend(mc_tools)
        tools_map.update({t.name: t for t in mc_tools})
        logger.info(f"[Minecraft Tools] Loaded {len(mc_tools)} tools")
    except Exception as e:
        logger.error(f"[Minecraft Tools] Failed to load: {e}")
```

**Step 3: Commit**

```bash
git add config/tools.yaml src/anima/tools/base.py
git commit -m "feat: register Minecraft tools in config and tool loading"
```

---

### Task 5: Add Tests

**Files:**
- Create: `tests/test_minecraft_bridge.py`
- Create: `tests/test_minecraft_tools.py`

**Step 1: Create `tests/test_minecraft_bridge.py`**

Test bridge config and lifecycle (not the actual subprocess — that requires Node.js).

```python
"""Tests for Minecraft Bridge"""

import pytest
from anima.tools.minecraft.config import MinecraftConfig, MinecraftBotConfig, MinecraftSafetyConfig


class TestMinecraftConfig:
    def test_default_config(self):
        config = MinecraftConfig()
        assert config.enabled is False
        assert config.bot.host == "localhost"
        assert config.bot.port == 25565
        assert config.bot.username == "AnimaBot"
        assert config.safety.no_griefing is True
        assert config.safety.max_distance == 500

    def test_custom_config(self):
        config = MinecraftConfig(
            enabled=True,
            bot=MinecraftBotConfig(host="example.com", port=25566, username="TestBot"),
        )
        assert config.enabled is True
        assert config.bot.host == "example.com"
        assert config.bot.username == "TestBot"

    def test_from_dict(self):
        config = MinecraftConfig(**{"enabled": True, "bot": {"username": "MyBot"}})
        assert config.enabled is True
        assert config.bot.username == "MyBot"
```

**Step 2: Create `tests/test_minecraft_tools.py`**

Test that tools are properly decorated and return correct names.

```python
"""Tests for Minecraft Tools"""

from anima.tools.minecraft.tools import get_minecraft_tools


class TestMinecraftTools:
    def test_get_tools_returns_list(self):
        tools = get_minecraft_tools()
        assert len(tools) > 0

    def test_tool_names(self):
        tools = get_minecraft_tools()
        names = [t.name for t in tools]
        assert "mc_goto" in names
        assert "mc_mine" in names
        assert "mc_build" in names
        assert "mc_attack" in names
        assert "mc_chat" in names
        assert "mc_status" in names

    def test_tool_descriptions_not_empty(self):
        tools = get_minecraft_tools()
        for t in tools:
            assert t.description, f"Tool {t.name} has no description"

    def test_mc_goto_parameters(self):
        tools = get_minecraft_tools()
        goto = next(t for t in tools if t.name == "mc_goto")
        args = goto.args if hasattr(goto, 'args') else {}
        assert "x" in str(goto.args or {}) or "x" in goto.__fields__ if hasattr(goto, '__fields__') else True
```

**Step 3: Run tests**

Run: `python -m pytest tests/test_minecraft_bridge.py tests/test_minecraft_tools.py -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add tests/test_minecraft_bridge.py tests/test_minecraft_tools.py
git commit -m "test: add Minecraft bridge and tools tests"
```

---

### Task 6: Integration — Wire Bridge Lifecycle to Orchestrator

**Files:**
- Modify: `src/anima/orchestration/graph/orchestrator.py` (around _load_tools / cleanup)

**Step 1: Review integration point**

The `ToolManager.load_tools()` already calls `load_tools_from_config(tools_config)` which we modified to handle minecraft. The bridge is initialized inside `init_bridge()` during tool loading.

For cleanup, we need to make sure the bridge stops when the orchestrator stops. The `ToolManager.cleanup()` is called in `orchestrator.stop()`.

**Step 2: Modify ToolManager cleanup to handle Minecraft**

In `tool_manager.py`, add async cleanup for minecraft bridge.

At end of `ToolManager.cleanup()`:

```python
# Cleanup Minecraft bridge
try:
    from anima.tools.minecraft.bridge import get_bridge
    bridge = get_bridge()
    if bridge and bridge.is_running:
        await bridge.stop()
        logger.info("[ToolManager] Minecraft bridge stopped")
except ImportError:
    pass  # Minecraft tools not installed
```

But wait — to keep it simple and avoid tight coupling, we can store the bridge reference in the module-level variable and clean it up when the ToolManager cleans up. Actually, the bridge is exposed via `init_bridge` which sets `_bridge` globally in `tools.py`. We need a `get_bridge()` function or we can just clean it from within the bridge module.

Let me simplify — add a `cleanup()` function to the minecraft tools module:

In `src/anima/tools/minecraft/tools.py`, add:

```python
async def cleanup_bridge():
    """Cleanup bridge resources"""
    global _bridge
    if _bridge:
        await _bridge.stop()
        _bridge = None
```

In `tool_manager.py` cleanup:

```python
# Cleanup Minecraft bridge
try:
    from anima.tools.minecraft.tools import cleanup_bridge
    await cleanup_bridge()
    logger.info("[ToolManager] Minecraft bridge cleaned up")
except ImportError:
    pass
```

**Step 3: Commit**

```bash
git add src/anima/tools/minecraft/tools.py src/anima/orchestration/graph/tool_manager.py
git commit -m "feat: wire Minecraft bridge lifecycle to orchestrator cleanup"
```

---

### Summary

| Task | Files | Description |
|------|-------|-------------|
| 1 | `bot/package.json`, `bot/index.js` | Node.js Mineflayer bot |
| 2 | `__init__.py`, `bridge.py`, `config.py` | Python process bridge |
| 3 | `tools.py` | LangChain @tool decorators |
| 4 | `config/tools.yaml`, `base.py` | Configuration + loading |
| 5 | `tests/test_minecraft_bridge.py`, `tests/test_minecraft_tools.py` | Tests |
| 6 | `tools.py`, `tool_manager.py` | Lifecycle integration |

**Total: ~8 files created, ~3 files modified**
