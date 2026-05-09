import mineflayer from 'mineflayer';
import pathfinderPkg from 'mineflayer-pathfinder';
import pvpPkg from 'mineflayer-pvp';
import Vec3 from 'vec3';
import { createInterface } from 'readline';
import { stdin, stdout, argv } from 'process';

const { pathfinder, Movements, goals } = pathfinderPkg;
const { GoalBlock } = goals;
const { plugin: pvp } = pvpPkg;

// --- CLI arguments ---
const host = argv[2];
const port = parseInt(argv[3], 10);
const username = argv[4];

if (!host || !port || !username) {
  const msg = { id: null, status: 'error', result: 'Usage: node index.js <host> <port> <username>' };
  stdout.write(JSON.stringify(msg) + '\n');
  process.exit(1);
}

// --- Bot setup ---
const bot = mineflayer.createBot({ host, port, username });
bot.loadPlugin(pathfinder);
bot.loadPlugin(pvp);

// --- Lazy dynamic import for minecraft-data (CJS interop) ---
let _mcDataLoader = null;

async function getMcData() {
  if (!_mcDataLoader) {
    const mod = await import('minecraft-data');
    _mcDataLoader = mod.default;
  }
  return _mcDataLoader(bot.version);
}

async function setupMovements() {
  const mcData = await getMcData();
  const movements = new Movements(bot, mcData);
  bot.pathfinder.setMovements(movements);
  return mcData;
}

// --- Action timeout helper ---
function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`Action "${label}" timed out after ${ms}ms`)), ms);
  });
  return Promise.race([promise.finally(() => clearTimeout(timer)), timeout]);
}

// --- JSON line protocol helpers ---
function sendResponse(id, status, result) {
  const msg = { id, status, result };
  stdout.write(JSON.stringify(msg) + '\n');
}

function sendEvent(type, data = {}) {
  sendResponse(null, 'event', { type, ...data });
}

// --- Idle loop ---
// When no commands are being processed, the bot autonomously progresses toward its goal
let currentGoal = '';
let idleLoopInterval = null;

function setIdleGoal(goal) {
  currentGoal = goal;
}

function clearIdleGoal() {
  currentGoal = '';
}

function startIdleLoop() {
  if (idleLoopInterval) return;
  idleLoopInterval = setInterval(() => {
    if (busy || !bot.entity || !currentGoal) return;
    // Send heartbeat: current position + goal status so Python knows we're alive
    const pos = bot.entity.position;
    const status = {
      position: { x: Math.floor(pos.x), y: Math.floor(pos.y), z: Math.floor(pos.z) },
      health: Math.floor(bot.health),
      food: Math.floor(bot.food),
      goal: currentGoal,
      idle: true,
    };
    sendEvent('heartbeat', status);
  }, 5000);
}

function stopIdleLoop() {
  if (idleLoopInterval) {
    clearInterval(idleLoopInterval);
    idleLoopInterval = null;
  }
}

// --- Bot event handlers ---
bot.on('login', () => {
  sendEvent('login', { username: bot.username });
});

bot.on('spawn', () => {
  sendEvent('spawn');
});

bot.on('error', (err) => {
  sendEvent('error', { message: err.message });
});

bot.on('end', (reason) => {
  sendEvent('disconnect', { reason });
});

bot.on('health', () => {
  if (bot.health < 10 && bot.health > 0) {
    bot.chat('I need to heal!');
  }
});

// --- Command dispatch ---
let busy = false;
const DEFAULT_TIMEOUT = 60000; // 60s default timeout
const rl = createInterface({ input: stdin, terminal: false });

rl.on('line', async (line) => {
  if (busy) return;
  busy = true;
  try {
    const trimmed = line.trim();
    if (!trimmed) {
      busy = false;
      return;
    }
    const cmd = JSON.parse(trimmed);
    await handleCommand(cmd);
  } catch (err) {
    sendResponse(null, 'error', err.message);
  } finally {
    busy = false;
  }
});

async function handleCommand(cmd) {
  const { id, action, params = {} } = cmd;
  const timeout = params.timeout || DEFAULT_TIMEOUT;

  let handler;
  switch (action) {
    case 'goto':     handler = handleGoto(id, params); break;
    case 'mine':     handler = handleMine(id, params); break;
    case 'place':    handler = handlePlace(id, params); break;
    case 'attack':   handler = handleAttack(id, params); break;
    case 'chat':     handler = handleChat(id, params); break;
    case 'status':   handler = handleStatus(id, params); break;
    case 'setgoal':  handler = handleSetGoal(id, params); break;
    case 'stop':     handler = handleStop(id, params); break;
    case 'collect':  handler = handleCollect(id, params); break;
    default:
      sendResponse(id, 'error', `Unknown action: ${action}`);
      return;
  }

  try {
    await withTimeout(handler, timeout, action);
  } catch (err) {
    // Interrupt any ongoing Mineflayer operations
    bot.pathfinder?.stop();
    bot.pvp?.stop();
    bot.stopDigging?.();
    sendResponse(id, 'error', err.message);
  }
}

// --- Action handlers ---

async function handleGoto(id, params) {
  const { x, y, z } = params;
  await setupMovements();
  await bot.pathfinder.goto(new GoalBlock(Math.floor(x), Math.floor(y), Math.floor(z)));
  sendResponse(id, 'success', `Moved to (${x}, ${y}, ${z})`);
}

async function handleMine(id, params) {
  const { block_type, count = 1 } = params;
  const mcData = await setupMovements();

  const blockInfo = mcData.blocksByName[block_type];
  if (!blockInfo) {
    sendResponse(id, 'error', `Unknown block type: ${block_type}`);
    return;
  }

  let mined = 0;
  for (let i = 0; i < count; i++) {
    const block = bot.findBlock({
      matching: blockInfo.id,
      maxDistance: 10,
    });

    if (!block) {
      const msg = mined > 0
        ? `No more ${block_type} found within 10 blocks, mined ${mined}`
        : `No ${block_type} found within 10 blocks`;
      sendResponse(id, 'error', msg);
      return;
    }

    // Approach the block from the direction we came
    const pos = block.position;
    const dx = Math.sign(Math.round(bot.entity.position.x) - pos.x) || 1;
    const dz = Math.sign(Math.round(bot.entity.position.z) - pos.z) || 1;
    await bot.pathfinder.goto(new GoalBlock(pos.x + dx, pos.y, pos.z + dz));

    await bot.dig(block);
    mined++;
  }

  sendResponse(id, 'success', `Mined ${mined} ${block_type} block(s)`);
}

async function handlePlace(id, params) {
  const { block_type, x, y, z } = params;
  await setupMovements();

  const targetPos = new Vec3(x, y, z);
  const blockBelow = bot.blockAt(new Vec3(x, y - 1, z));

  if (!blockBelow || blockBelow.name === 'air') {
    sendResponse(id, 'error', 'No solid block below target position');
    return;
  }

  const item = bot.inventory.items().find((i) => i.name === block_type);
  if (!item) {
    sendResponse(id, 'error', `No ${block_type} in inventory`);
    return;
  }

  await bot.equip(item, 'hand');

  // Approach near the target
  await bot.pathfinder.goto(new GoalBlock(x + 1, y, z));

  // Place against the top face of the block below
  await bot.placeBlock(blockBelow, new Vec3(0, 1, 0));
  sendResponse(id, 'success', `Placed ${block_type} at (${x}, ${y}, ${z})`);
}

async function handleAttack(id, params) {
  const { target } = params;
  await setupMovements();

  let entity;
  if (target === 'nearest_hostile') {
    entity = bot.nearestEntity((e) => e.type === 'mob');
  } else if (target === 'nearest_player') {
    entity = bot.nearestEntity((e) => e.type === 'player');
  } else {
    // Match by entity name or custom display name
    entity = bot.nearestEntity(
      (e) => e.name === target || (e.displayName && String(e.displayName) === target)
    );
  }

  if (!entity) {
    sendResponse(id, 'error', `Target not found: ${target}`);
    return;
  }

  const ePos = entity.position;
  await bot.pathfinder.goto(new GoalBlock(
    Math.floor(ePos.x),
    Math.floor(ePos.y),
    Math.floor(ePos.z)
  ));

  bot.attack(entity);
  sendResponse(id, 'success', `Attacked ${entity.name || target}`);
}

async function handleChat(id, params) {
  const { message } = params;
  bot.chat(message);
  sendResponse(id, 'success', 'Chat message sent');
}

async function handleStatus(id, _params) {
  if (!bot.entity) {
    sendResponse(id, 'error', 'Bot not spawned yet');
    return;
  }
  const pos = bot.entity.position;
  const weather = bot.rainState > 0 ? (bot.thunderState > 0 ? 'thunderstorm' : 'rain') : 'clear';
  const timeOfDay = bot.time?.timeOfDay ?? 0;
  const timeLabel = timeOfDay < 6000 ? 'morning' : timeOfDay < 12000 ? 'afternoon' : 'night';

  // Count inventory items
  const inventory = {};
  for (const item of bot.inventory.items()) {
    inventory[item.name] = (inventory[item.name] || 0) + item.count;
  }

  // Find nearby entities
  const nearbyEntities = {};
  if (bot.entity) {
    const radius = 16;
    for (const e of Object.values(bot.entities)) {
      if (e === bot.entity) continue;
      if (!e.position) continue;
      const dist = e.position.distanceTo(pos);
      if (dist <= radius) {
        const name = e.name || e.username || 'unknown';
        nearbyEntities[name] = (nearbyEntities[name] || 0) + 1;
      }
    }
  }

  sendResponse(id, 'success', {
    position: { x: Math.floor(pos.x * 100) / 100, y: Math.floor(pos.y * 100) / 100, z: Math.floor(pos.z * 100) / 100 },
    health: Math.floor(bot.health * 10) / 10,
    food: Math.floor(bot.food * 10) / 10,
    dimension: bot.game ? bot.game.dimension : null,
    game_mode: bot.game ? bot.game.gameMode : null,
    weather,
    time: timeLabel,
    biome: bot.blockAt(pos)?.biome?.name || 'unknown',
    inventory,
    nearby_entities: nearbyEntities,
    current_goal: currentGoal || null,
  });
}

async function handleSetGoal(id, params) {
  const { goal } = params;
  if (goal) {
    setIdleGoal(goal);
    startIdleLoop();
    sendResponse(id, 'success', `Goal set: ${goal}`);
  } else {
    clearIdleGoal();
    stopIdleLoop();
    sendResponse(id, 'success', 'Goal cleared');
  }
}

async function handleStop(id, _params) {
  clearIdleGoal();
  stopIdleLoop();
  bot.pathfinder?.stop();
  bot.pvp?.stop();
  bot.stopDigging?.();
  try { bot.collectBlock?.cancelTask(); } catch {}
  sendResponse(id, 'success', 'All actions stopped');
}

async function handleCollect(id, params) {
  const { block_type, count = 1 } = params;
  await setupMovements();

  // Dynamic import mineflayer-collectblock
  let collectBlock;
  try {
    const mod = await import('mineflayer-collectblock');
    collectBlock = mod.default || mod;
    bot.loadPlugin(collectBlock);
  } catch {
    // Fallback: use mine + pickup logic
    sendResponse(id, 'error', 'mineflayer-collectblock not installed, use mine action instead');
    return;
  }

  const mcData = await getMcData();
  const blockInfo = mcData.blocksByName[block_type];
  if (!blockInfo) {
    sendResponse(id, 'error', `Unknown block type: ${block_type}`);
    return;
  }

  try {
    await bot.collectBlock.collect(b => b.name === block_type, { maxCount: count });
    sendResponse(id, 'success', `Collected ${count} ${block_type}(s)`);
  } catch (err) {
    sendResponse(id, 'error', `Collection failed: ${err.message}`);
  }
}
