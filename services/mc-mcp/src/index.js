import mineflayer from 'mineflayer';
import pathfinderPkg from 'mineflayer-pathfinder';
import pvpPkg from 'mineflayer-pvp';
import Vec3 from 'vec3';
import { stdin, stdout, argv } from 'node:process';

import { actionTimeoutFromDeadline } from './actionDeadline.js';
import { configureMineSupport } from './branch_mine.js';
import { findReachableCraftingTable } from './craftingTable.js';
import { availableMaterialCount, craftOperations, WOOD_PLANK_RECIPES } from './crafting/counts.js';
import {
  createCraftingTablePlacementBudget,
  recoverPlacedCraftingTableAfterTimeout,
} from './crafting/placement.js';
import {
  collectionBlockKey,
  collectionApproachGoal,
  collectionExcavationGoal,
  collectionDigTimeoutMs,
  collectionDigSafety,
  assertSafeDigTarget,
  configureDryNavigation,
  restrictNavigationHeight,
  collectionResourceMutation,
  configureCollectionNavigation,
  configurePickupNavigation,
  createCollectionBlockMatcher,
  digCollectionBlock,
  findCollectionTarget,
  findPickupItemEntities,
  pickupInventoryCount,
  incompleteCollectionError,
  isCollectionFluidHazard,
  isCollectionSettleHazard,
  isPreparedObsidianTarget,
  obsidianWorkMinimumY,
  safePickupDroppedItems,
  isCollectionBlockStillPresent,
  isRecoverableCollectionDigError,
  stopCollectionMovement,
  shouldPrepareUndergroundCollection,
  shouldRetryStructuredResourceSearch,
  waitForCollectionMovementToSettle,
  withCollectionEvidence,
} from './collection.js';
import { createEquip } from './equip.js';
import { eatFood, forageApples } from './food.js';
import { executeCombatWithEvidence } from './gamebotEvidenceV2.js';
import { createMineShaft } from './mine_shaft.js';
import { navigateTo } from './navigation.js';
import { backfillObsidianHole } from './obsidianSupport.js';
import { acquireFlint, ignitePortal } from './portal.js';
import { fillWaterBucket, prepareObsidian } from './water.js';
import {
  normalizePlacementBlockName,
  placeBlockAt,
  placementMutations,
} from './placement.js';
import { locateResource } from './resources/locator.js';
import {
  resolveRequestedBlockName,
  resolveRequestedBlockNames,
} from './resources/registry.js';
import { assertSurvivalChat } from './safeChat.js';
import { createSmelt } from './smelt.js';
import { runSurvivalIron } from './survival/runner.js';
import { setupClientViewer } from './clientViewer.js';
import { createGameBotV2Adapter } from './runtime/gamebotV2Adapter.js';
import { createRuntimeProcessProtocol } from './runtime/processProtocol.js';
import { presentBlockTarget } from './runtime/presentationAnchors.js';
import {
  activeOperationScope,
  createOperationScope,
  interruptRunningOperation,
  operationWait,
} from './runtime/operationScope.js';
import {
  presentationSeedDigest,
  resolvePresentationConfig,
} from './runtime/broadcastMotionPolicy.js';

const { pathfinder, Movements, goals } = pathfinderPkg;
const { GoalBlock, GoalNear, GoalXZ } = goals;
const { plugin: pvp } = pvpPkg;

// --- CLI arguments ---
const host = argv[2];
const port = parseInt(argv[3], 10);
const username = argv[4];
const version = argv[5] || undefined;

if (!host || !port || !username) {
  const msg = { id: null, status: 'error', result: 'Usage: node index.js <host> <port> <username>' };
  stdout.write(JSON.stringify(msg) + '\n');
  process.exit(1);
}

// --- Bot setup ---
const bot = mineflayer.createBot({ host, port, username, version });
bot.loadPlugin(pathfinder);
bot.loadPlugin(pvp);

// --- Pathfinder timeout patch (applied on spawn when pathfinder is ready) ---
let _pathfinderPatched = false;
function patchPathfinder() {
  if (_pathfinderPatched || !bot.pathfinder?.goto) return;
  _pathfinderPatched = true;
  const _originalGoto = bot.pathfinder.goto.bind(bot.pathfinder);
  bot.pathfinder.goto = async function patchedGoto(goal, ...args) {
    const scope = activeOperationScope() || createOperationScope({
      bot,
      deadlineMs: Date.now() + 15_000,
    });
    return scope.navigate(goal, () => _originalGoto(goal, ...args));
  };
}

let _operationMethodsPatched = false;
function patchInterruptibleBotMethods() {
  if (_operationMethodsPatched) return;
  _operationMethodsPatched = true;
  for (const [method, timeoutMs, includeContainers] of [
    ['dig', 10_000, false],
    ['placeBlock', 8_000, false],
    ['craft', 30_000, true],
    ['equip', 5_000, false],
  ]) {
    if (typeof bot[method] !== 'function') continue;
    const original = bot[method].bind(bot);
    bot[method] = (...args) => {
      const scope = activeOperationScope();
      if (method === 'dig') assertSafeDigTarget(bot, args[0]);
      if (!scope) return original(...args);
      return scope.runInterruptible(
        () => original(...args),
        {
          label: `bot.${method}`,
          timeoutMs: method === 'dig' ? collectionDigTimeoutMs(bot, args[0]) : timeoutMs,
          includeContainers,
        },
      );
    };
  }
}

// --- Lazy dynamic import for minecraft-data (CJS interop) ---
let _mcDataLoader = null;
let _mcDataCache = null;

async function getMcData() {
  if (!_mcDataLoader) {
    const mod = await import('minecraft-data');
    _mcDataLoader = mod.default;
  }
  _mcDataCache = _mcDataLoader(bot.version);
  return _mcDataCache;
}

async function setupMovements() {
  const mcData = await getMcData();
  const movements = new Movements(bot, mcData);
  configureMineSupport(movements, mcData);
  configureDryNavigation(movements, bot);
  bot.pathfinder.setMovements(movements);
  return mcData;
}

// ── Core action functions (single source of truth) ──

async function _goto(x, y, z, context = {}) {
  context.operation_scope?.checkpoint();
  await setupMovements();
  await navigateTo(bot, { x, y, z }, context);
  return `Moved to (${x}, ${y}, ${z})`;
}

async function _navigateFoodSurface(goal, context = {}) {
  context.operation_scope?.checkpoint();
  const movements = new Movements(bot, await getMcData());
  configureDryNavigation(movements, bot);
  movements.canDig = false;
  bot.pathfinder.setMovements(movements);
  try {
    await bot.pathfinder.goto(goal);
    return true;
  } catch (error) {
    context.signal?.throwIfAborted();
    if (error.operationSettlement || !context.operation_scope?.isQuiescent()) throw error;
    return false;
  }
}

// Blocks that are typically underground (need to dig down to find)
const UNDERGROUND_BLOCKS = new Set(['stone', 'coal_ore', 'iron_ore', 'gold_ore', 'diamond_ore', 'copper_ore', 'lapis_ore', 'redstone_ore', 'deepslate', 'cobbled_deepslate']);

async function _explore_for_block(
  block_type,
  max_distance = 64,
  max_attempts = 5,
  excludedTargets = new Set(),
) {
  const mcData = await getMcData();
  const blockNames = resolveRequestedBlockNames(block_type, mcData.blocksByName, ITEM_TO_BLOCK);
  const blockIds = blockNames.map(name => mcData.blocksByName[name].id);
  if (!blockIds.length) throw new Error(`Unknown block: ${block_type}`);

  const isUnderground = UNDERGROUND_BLOCKS.has(block_type);

  for (let i = 0; i < max_attempts; i++) {
    // Check if block is already nearby
    const block = findCollectionTarget(
      bot,
      blockIds,
      max_distance,
      excludedTargets,
    );
    if (block) {
      return `Found ${block_type} at (${block.position.x}, ${block.position.y}, ${block.position.z})`;
    }

    if (isUnderground) {
      // For underground blocks, dig down aggressively to reach stone layer
      try {
        const pos = bot.entity.position;
        const targetY = Math.max(pos.y - 20, 12); // Dig down up to 20 blocks
        for (let dy = 1; dy <= 20 && (pos.y - dy) > targetY; dy++) {
          const belowBlock = bot.blockAt(new Vec3(Math.floor(pos.x), Math.floor(pos.y) - dy, Math.floor(pos.z)));
          if (belowBlock && belowBlock.name !== 'air' && belowBlock.name !== 'bedrock') {
            try {
              await bot.dig(belowBlock);
              await operationWait(100);
            } catch (e) {
              break;
            }
          }
        }
        // Check again after digging down
        const found = findCollectionTarget(
          bot,
          blockIds,
          max_distance,
          excludedTargets,
        );
        if (found) {
          return `Found ${block_type} at (${found.position.x}, ${found.position.y}, ${found.position.z})`;
        }
      } catch (e) {
        // Fall through to random walk
      }
    }

    // Random walk with timeout
    const dx = Math.floor(Math.random() * 20) - 10;
    const dz = Math.floor(Math.random() * 20) - 10;
    const targetX = bot.entity.position.x + dx;
    const targetZ = bot.entity.position.z + dz;

    try {
      await bot.pathfinder.goto(new GoalBlock(targetX, bot.entity.position.y, targetZ));
    } catch (e) {
      // Ignore pathfinding errors
    }

    // Wait a bit for blocks to load
    await operationWait(500);
  }

  throw new Error(`Could not find ${block_type} after ${max_attempts} exploration attempts`);
}

async function _mine(block_type, count = 1, context = {}) {
  return _mineInner(block_type, count, context);
}

async function _mineInner(block_type, count, context = {}) {
  context.operation_scope?.checkpoint();
  const mcData = await setupMovements();

  // If block_type is an item name, map to the block that drops it
  const resolvedBlockType = resolveRequestedBlockName(
    block_type,
    mcData.blocksByName,
    ITEM_TO_BLOCK,
  );
  const bi = resolvedBlockType ? mcData.blocksByName[resolvedBlockType] : null;
  if (!bi) throw new Error(`Unknown block: ${block_type}`);

  let mined = 0;
  for (let i = 0; i < count; i++) {
    context.operation_scope?.checkpoint();
    let b = bot.findBlock({ matching: bi.id, maxDistance: 10 });

    // If not found nearby, use Resource Locator (registry strategies + memory) first,
    // then fall back to blind _explore_for_block for compatibility.
    if (!b) {
      try {
        const cand = await locateResource(bot, resolvedBlockType, { mcData, getMcData });
        const at = bot.blockAt(new Vec3(cand.position.x, cand.position.y, cand.position.z));
        if (at && at.type === bi.id) b = at;
      } catch (_locErr) {
        // Hard locator errors are actionable; do not hide them behind blind exploration.
        if (_locErr && ['TOOL_REQUIRED', 'UNKNOWN_RESOURCE', 'UNSAFE_AREA'].includes(_locErr.code)) {
          throw _locErr;
        }
        if (shouldRetryStructuredResourceSearch(resolvedBlockType, _locErr)) {
          continue;
        }
        // Soft locator misses (RESOURCE_NOT_FOUND/SEARCH_TIMEOUT) → old fallback stays compatible.
      }
    }
    if (!b) {
      try {
        await _explore_for_block(resolvedBlockType, 32, 5);
        b = bot.findBlock({ matching: bi.id, maxDistance: 32 });
      } catch (e) {
        // Exploration failed, try one more time
      }
    }

    if (!b) throw new Error(`No more ${resolvedBlockType}, mined ${mined}`);

    const presentationTarget = await presentBlockTarget({
      context,
      phase: 'locating',
      position: b.position,
      ordinal: i,
      data: { attempt: i + 1 },
    });

    // Navigate with timeout
    try {
      await bot.pathfinder.goto(new GoalBlock(b.position.x, b.position.y + 1, b.position.z));
    } catch (e) {
      // Navigation failed, try to dig from current position
    }

    // Dig block (with retry on abort)
    context.report_phase?.('acting', {
      attempt: i + 1,
      ...(presentationTarget ? { target: presentationTarget } : {}),
    });
    let digSuccess = false;
    for (let retry = 0; retry < 3 && !digSuccess; retry++) {
      try {
        await _equipToolForBlock(b); // ❹ Equip best tool before digging
        await bot.dig(b);
        digSuccess = true;
      } catch (e) {
        if (
          retry < 2 &&
          (e.code === 'COLLECT_FAILED' || (e.message && e.message.includes('aborted')))
        ) {
          const stillThere = bot.blockAt(b.position);
          if (!stillThere || stillThere.type !== bi.id) {
            digSuccess = true;
            break;
          }
          b = stillThere;
          context.report_phase?.('recovering', {
            attempt: retry + 2,
            reason_code: 'DIG_RETRY',
            ...(presentationTarget ? { target: presentationTarget } : {}),
          });
          if (presentationTarget?.position) {
            await context.presentation?.focus?.({
              phase: 'recovering',
              ordinal: retry + 1,
              target: presentationTarget.position,
            });
          }
          await operationWait(500);
        } else {
          throw e;
        }
      }
    }

    if (digSuccess) {
      await operationWait(500);
      mined++;
    }
  }
  return `Mined ${mined} ${block_type}`;
}

async function _placeResult(block_type, x, y, z, facing = undefined, context = {}) {
  context.operation_scope?.checkpoint();
  await setupMovements();
  const targetPosition = new Vec3(Math.floor(x), Math.floor(y), Math.floor(z));
  const blockName = normalizePlacementBlockName(block_type);
  return placeBlockAt(bot, { blockName, targetPosition, facing, context }, {
    navigate: () => bot.pathfinder.goto(new GoalNear(
      targetPosition.x, Math.floor(bot.entity.position.y), targetPosition.z, 4,
    )),
    dig: block => digCollectionBlock(bot, block),
    wait: operationWait,
  });
}

async function _place(...parameters) {
  return (await _placeResult(...parameters)).output;
}

async function _placeWithEvidence(block_type, x, y, z, facing = undefined, context = {}) {
  const targetPosition = new Vec3(Math.floor(x), Math.floor(y), Math.floor(z));
  const { output, placed } = await _placeResult(block_type, x, y, z, facing, context);
  const blockName = normalizePlacementBlockName(block_type);
  const observedSecondaryPositions = blockName.endsWith('_bed')
    ? [
        targetPosition.offset(1, 0, 0),
        targetPosition.offset(-1, 0, 0),
        targetPosition.offset(0, 0, 1),
        targetPosition.offset(0, 0, -1),
      ].filter(position => bot.blockAt(position)?.name === blockName)
    : [];
  const explainedMutations = placed ? placementMutations(
    block_type,
    targetPosition,
    bot.game?.dimension || 'minecraft:overworld',
    observedSecondaryPositions,
  ) : [];
  return {
    output,
    explained_mutations: explainedMutations,
    budget_usage: {
      max_actions: 1,
      max_strategy_attempts: 0,
      max_travel_distance: placed ? 8 : 0,
      max_blocks_changed: explainedMutations.length,
      max_damage_taken: 0,
      protected_items: [],
      resource_consumption: {},
    },
  };
}

const HOSTILE_NAMES = ['zombie', 'skeleton', 'spider', 'creeper', 'witch', 'enderman', 'wither_skeleton'];
const ACTIVE_COMBAT_HOSTILE_NAMES = ['zombie', 'skeleton', 'spider', 'drowned', 'husk', 'stray', 'slime', 'wither_skeleton'];
const FOOD_ANIMAL_NAMES = ['cow', 'pig', 'chicken', 'sheep'];

function _resolveAttackTarget(target = 'nearest_hostile') {
  let entity;
  if (target === 'nearest_hostile') {
    entity = bot.nearestEntity(e => {
      const n = (e.name || '').toLowerCase();
      return ACTIVE_COMBAT_HOSTILE_NAMES.some(h => n.includes(h));
    });
  } else if (target === 'nearest_food_animal') {
    entity = bot.nearestEntity(e => {
      const n = (e.name || '').toLowerCase();
      return FOOD_ANIMAL_NAMES.some(name => n.includes(name));
    });
  } else if (target === 'nearest_player') {
    entity = bot.nearestEntity(e => e.type === 'player');
  } else {
    entity = bot.nearestEntity(e => e.name === target || (e.displayName && String(e.displayName) === target));
  }
  if (!entity) throw new Error(`Target not found: ${target}`);
  return entity;
}

async function _attackWithEvidence(target = 'nearest_hostile', context = {}) {
  context.operation_scope?.checkpoint();
  await setupMovements();
  const entity = _resolveAttackTarget(target);
  const combat = await executeCombatWithEvidence({
    bot,
    target: entity,
    signal: context.signal,
    deadlineMs: context.deadline_ms,
  });
  if (FOOD_ANIMAL_NAMES.includes(entity.name) && combat.outcome === 'defeated') {
    await _pickupDroppedItems(6000, entity.position);
  }
  return {
    output: `Combat with ${entity.name || target} ended: ${combat.outcome}`,
    combat,
    explained_mutations: [{
      kind: 'combat',
      subject: combat.target_entity_id,
      delta: null,
      details: {
        target_entity_type: combat.target_entity_type,
        outcome: combat.outcome,
      },
    }],
  };
}

// ── Item-to-block mapping (items that drop from mining a block) ──
const ITEM_TO_BLOCK = {
  raw_iron: 'iron_ore',
  raw_copper: 'copper_ore',
  raw_gold: 'gold_ore',
  diamond: 'diamond_ore',
  emerald: 'emerald_ore',
  lapis_lazuli: 'lapis_ore',
  redstone: 'redstone_ore',
  coal: 'coal_ore',
  cobblestone: 'stone',
};

// ── Drop item mapping (block name → item entity name that drops) ──
const BLOCK_DROP_ITEM = {
  oak_log: 'oak_log',
  spruce_log: 'spruce_log',
  birch_log: 'birch_log',
  stone: 'cobblestone',
  coal_ore: 'coal',
  iron_ore: 'raw_iron',
  gold_ore: 'raw_gold',
  diamond_ore: 'diamond',
  copper_ore: 'raw_copper',
  lapis_ore: 'lapis_lazuli',
  redstone_ore: 'redstone',
};

function _inventoryCount(itemName) {
  let total = 0;
  for (const item of bot.inventory.items()) {
    if (item.name === itemName) total += item.count;
  }
  return total;
}

async function _waitForInventoryIncrease(itemName, beforeCount, minimumIncrease = 1, timeout = 5000) {
  const deadline = Date.now() + timeout;
  const expected = beforeCount + Math.max(1, minimumIncrease);
  while (Date.now() < deadline) {
    if (_inventoryCount(itemName) >= expected) return true;
    await operationWait(100);
  }
  if (_inventoryCount(itemName) >= expected) return true;
  throw craftError(`Craft result not observed: ${itemName}`, 'CRAFT_FAILED');
}

function _collectDebug(message) {
  if (process.env.COLLECT_DEBUG) {
    console.error(`[collect-debug] ${message}`);
  }
}

function _isAirLike(block) {
  return !block || block.name === 'air' || (
    block.boundingBox === 'empty'
    && !['water', 'flowing_water', 'lava', 'flowing_lava'].includes(block.name)
  );
}

function _findNearestStandable(maxRadius = 8) {
  if (!bot.entity?.position) return null;
  const origin = bot.entity.position.floored();
  const candidates = [];

  for (let dx = -maxRadius; dx <= maxRadius; dx++) {
    for (let dz = -maxRadius; dz <= maxRadius; dz++) {
      for (let dy = 3; dy >= -8; dy--) {
        const groundPos = origin.offset(dx, dy, dz);
        const ground = bot.blockAt(groundPos);
        if (ground?.boundingBox !== 'block') continue;

        const feet = bot.blockAt(groundPos.offset(0, 1, 0));
        const head = bot.blockAt(groundPos.offset(0, 2, 0));
        if (!_isAirLike(feet) || !_isAirLike(head)) continue;

        const standPos = groundPos.offset(0, 1, 0);
        candidates.push({
          pos: standPos,
          distance: bot.entity.position.distanceTo(standPos.offset(0.5, 0, 0.5)),
        });
      }
    }
  }

  candidates.sort((a, b) => a.distance - b.distance);
  return candidates[0]?.pos || null;
}

async function _stabilizePosition(timeout = 7000) {
  if (!bot.entity) return false;
  stopCollectionMovement(bot);
  if (bot.entity.onGround !== false && !isCollectionSettleHazard(bot)) return true;

  const standPos = _findNearestStandable(8);
  if (!standPos) {
    _collectDebug('stabilize skipped: no nearby standable position');
    return false;
  }

  try {
    _collectDebug(`stabilize goto=${standPos.x},${standPos.y},${standPos.z}`);
    await bot.pathfinder.goto(new GoalBlock(standPos.x, standPos.y, standPos.z));
  } catch (e) {
    _collectDebug(`stabilize path failed: ${e.message}`);
    stopCollectionMovement(bot);
    activeOperationScope()?.checkpoint();
  } finally {
    stopCollectionMovement(bot);
  }

  await operationWait(300);
  return bot.entity?.onGround !== false && !isCollectionSettleHazard(bot);
}

const PICKAXE_TIERS = ['netherite_pickaxe', 'diamond_pickaxe', 'iron_pickaxe', 'stone_pickaxe', 'wooden_pickaxe'];
const IRON_PICKAXE_REQUIRED = new Set(['diamond_ore', 'deepslate_diamond_ore', 'emerald_ore', 'deepslate_emerald_ore', 'gold_ore', 'deepslate_gold_ore', 'redstone_ore', 'deepslate_redstone_ore']);
const PICKAXE_BLOCKS = new Set([
  'stone', 'deepslate', 'cobbled_deepslate', 'obsidian', 'coal_ore', 'deepslate_coal_ore',
  'iron_ore', 'deepslate_iron_ore', 'copper_ore', 'deepslate_copper_ore',
  'lapis_ore', 'deepslate_lapis_ore', ...IRON_PICKAXE_REQUIRED,
]);
const AXE_SUFFIXES = ['_log', '_wood', '_stem', '_hyphae'];

async function _equipToolForBlock(block, context = null) {
  const name = block?.name;
  if (!name) return null;

  let candidates = [];
  if (IRON_PICKAXE_REQUIRED.has(name)) {
    candidates = ['netherite_pickaxe', 'diamond_pickaxe', 'iron_pickaxe'];
  } else if (PICKAXE_BLOCKS.has(name)) {
    candidates = PICKAXE_TIERS;
  } else if (AXE_SUFFIXES.some(suffix => name.endsWith(suffix))) {
    candidates = ['netherite_axe', 'diamond_axe', 'iron_axe', 'stone_axe', 'wooden_axe'];
  }

  for (const toolName of candidates) {
    const item = bot.inventory.items().find(i => i.name === toolName);
    if (item && (typeof block.canHarvest !== 'function' || block.canHarvest(item.type))) {
      await bot.equip(item, 'hand');
      _collectDebug(`equipped ${toolName} for ${name}`);
      return toolName;
    }
  }
  if (typeof block.canHarvest === 'function' && !block.canHarvest(null)) {
    // A path can consume the last stone pickaxe before reaching the ore.
    // Replace it from observed stock inside this action's original budget.
    const mcData = context ? await getMcData() : null;
    const replacement = mcData?.itemsByName.stone_pickaxe;
    const sticks = _inventoryCount('stick');
    const planks = bot.inventory.items().reduce((sum, item) => (
      sum + (item.name.endsWith('_planks') ? item.count : 0)
    ), 0);
    if (replacement && block.canHarvest(replacement.id) && _inventoryCount('cobblestone') >= 3
      && (sticks >= 2 || planks >= 2)) {
      if (sticks < 2) await _craft('stick', 2 - sticks, context);
      await _craft('stone_pickaxe', 1, context);
      return _equipToolForBlock(block);
    }
    throw Object.assign(new Error(`采集 ${name} 缺少可获得掉落物的工具。`), {
      code: 'TOOL_REQUIRED', details: { block_type: name },
    });
  }
  return null;
}

async function _pickupDroppedItems(
  timeout = 5000, fallbackPos = null, itemName = null,
  minimumY = Number.NEGATIVE_INFINITY, minimumInventoryCount = null,
) {
  const mcData = await getMcData();
  const movements = configurePickupNavigation(new Movements(bot, mcData), bot);
  await operationWait(300);
  const debugDrops = phase => {
    if (!process.env.COLLECT_DEBUG) return;
    const drops = findPickupItemEntities(bot, 20, itemName).map(({ entity }) => ({
      id: entity.id, position: entity.position,
    }));
    _collectDebug(`pickup ${phase}=${JSON.stringify({ item: itemName, minimum_y: minimumY, drops })}`);
  };
  debugDrops('before');
  const result = await safePickupDroppedItems(bot, {
    timeoutMs: timeout, fallbackPos, itemName, GoalNear, movements, minimumY, minimumInventoryCount,
    context: { operation_scope: activeOperationScope(), signal: activeOperationScope()?.signal },
  });
  debugDrops('after');
  _collectDebug(`pickup outcome=${JSON.stringify(result)}`);
  return result;
}

async function _collect(block_type, count = 1, context = {}) {
  await setupMovements();
  const mcData = await getMcData();
  configureCollectionNavigation(bot.pathfinder.movements,
    resolveRequestedBlockNames(block_type, mcData.blocksByName, ITEM_TO_BLOCK));

  try {
    return await _collectInner(block_type, count, mcData, context);
  } finally {
    stopCollectionMovement(bot);
    if (!context.signal?.aborted) {
      await _stabilizePosition(10_000);
      await waitForCollectionMovementToSettle(bot);
    }
  }
}

async function _collectWithEvidence(block_type, count = 1, context = {}) {
  return withCollectionEvidence(bot, (resourceMutations) => (
    _collect(block_type, count, { ...context, resourceMutations })
  ));
}

async function _collectInner(block_type, count, mcData, context = {}) {
  await _stabilizePosition(5000);
  context.signal?.throwIfAborted();

  // If block_type is an item name (e.g. "coal"), map to the block that drops it
  const resolvedBlockType = resolveRequestedBlockName(
    block_type,
    mcData.blocksByName,
    ITEM_TO_BLOCK,
  );
  const resolvedBlockTypes = resolveRequestedBlockNames(
    block_type,
    mcData.blocksByName,
    ITEM_TO_BLOCK,
  );
  const bi = resolvedBlockType ? mcData.blocksByName[resolvedBlockType] : null;
  if (!bi) throw new Error(`Unknown block: ${block_type}`);

  const genericWood = String(block_type).trim().toLowerCase() === 'any_log';
  const initialWoodCounts = genericWood
    ? new Map(resolvedBlockTypes.map(name => [name, _inventoryCount(name)])) : null;
  let selectedWood = null;
  let dropItem = genericWood ? resolvedBlockType : BLOCK_DROP_ITEM[resolvedBlockType] || block_type;
  let minimumY = resolvedBlockType === 'obsidian'
    ? Math.floor(bot.entity.position.y) : Number.NEGATIVE_INFINITY;
  let startingCount = _inventoryCount(dropItem);
  _collectDebug(`start block=${block_type} resolved=${resolvedBlockType} drop=${dropItem} need=${count} starting=${startingCount}`);
  let collected = 0;
  const excludedTargets = context.excludedTargets instanceof Set
    ? context.excludedTargets
    : new Set();
  const blockIds = resolvedBlockTypes.map((name) => mcData.blocksByName[name].id);
  const matchesAvailableTarget = createCollectionBlockMatcher(
    blockIds,
    excludedTargets,
    block => collectionDigSafety(bot, block).safe
      && (!selectedWood || block.name === selectedWood)
      && (resolvedBlockType !== 'obsidian' || isPreparedObsidianTarget(bot, block, minimumY)),
  );
  const workTargets = resolvedBlockType === 'obsidian'
    ? bot.findBlocks({
      matching: createCollectionBlockMatcher(blockIds, excludedTargets, block => isPreparedObsidianTarget(bot, block)),
      maxDistance: 32, count: 64,
    }) : null;
  if (workTargets) {
    minimumY = obsidianWorkMinimumY(bot, workTargets);
    restrictNavigationHeight(bot.pathfinder.movements, minimumY);
  }
  let discoveredTarget = workTargets?.map(position => bot.blockAt(position)).find(matchesAvailableTarget)
    ?? bot.findBlock({ matching: matchesAvailableTarget, maxDistance: 32 });
  const preparation = shouldPrepareUndergroundCollection(
    resolvedBlockType,
    count,
    bot.entity.position.y,
    Boolean(discoveredTarget && collectionApproachGoal(bot, discoveredTarget).isEnd(bot.entity.position.floored())),
    discoveredTarget && collectionDigSafety(bot, discoveredTarget).safe ? discoveredTarget.position.y : null,
  );
  if (preparation) {
    await mineShaftMod.mineShaft(
      preparation.targetY,
      preparation.minimumCobblestone,
      context,
    );
    collected = Math.min(
      Math.max(0, _inventoryCount(dropItem) - startingCount),
      count,
    );
    if (collected >= count) {
      return `Collected ${collected} ${block_type}`;
    }
  }
  let attempts = 0;
  const maxAttempts = Math.max(count * 3, count + 3);
  const searchFailures = [];
  const recordSearchFailure = (stage, error, target = null) => {
    searchFailures.push({
      stage,
      code: error?.code || null,
      message: String(error?.message || error),
      strategy_failures: error?.search_failures || [],
      target,
    });
    if (searchFailures.length > 5) searchFailures.shift();
  };
  while (collected < count && attempts < maxAttempts) {
    context.signal?.throwIfAborted();
    collected = Math.min(Math.max(0, _inventoryCount(dropItem) - startingCount), count);
    if (collected >= count) break;
    attempts++;
    // Find block
    let block = discoveredTarget
      || bot.findBlock({ matching: matchesAvailableTarget, maxDistance: 32 });
    discoveredTarget = null;
    const searchResource = selectedWood || (genericWood ? 'any_log' : resolvedBlockType);

    // If not found, use Resource Locator (registry strategies + memory) first,
    // then fall back to blind _explore_for_block for compatibility.
    if (!block) {
      try {
        const cand = await locateResource(bot, searchResource, {
          mcData,
          getMcData,
          excludedTargets,
        });
        const at = bot.blockAt(new Vec3(cand.position.x, cand.position.y, cand.position.z));
        if (at && matchesAvailableTarget(at)) block = at;
      } catch (_locErr) {
        context.signal?.throwIfAborted();
        recordSearchFailure('locate', _locErr);
        // Hard locator errors are actionable; do not hide them behind blind exploration.
        if (_locErr && ['TOOL_REQUIRED', 'UNKNOWN_RESOURCE', 'UNSAFE_AREA'].includes(_locErr.code)) {
          throw _locErr;
        }
        if (shouldRetryStructuredResourceSearch(resolvedBlockType, _locErr)) {
          continue;
        }
        // Soft locator misses (RESOURCE_NOT_FOUND/SEARCH_TIMEOUT) → old fallback stays compatible.
      }
    }
    if (!block) {
      try {
        await _explore_for_block(searchResource, 32, 3, excludedTargets);
        block = bot.findBlock({ matching: matchesAvailableTarget, maxDistance: 32 });
      } catch (e) {
        context.signal?.throwIfAborted();
        // Exploration failed
      }
    }

    if (!block) break;
    if (!collectionDigSafety(bot, block).safe) {
      excludedTargets.add(collectionBlockKey(block));
      continue;
    }
    if (genericWood && !selectedWood) {
      selectedWood = block.name;
      dropItem = selectedWood;
      startingCount = initialWoodCounts.get(selectedWood);
      _collectDebug(`bound wood=${selectedWood} starting=${startingCount}`);
    }
    await _equipToolForBlock(block, context);
    _collectDebug(`target block=${block.name}@${block.position.x},${block.position.y},${block.position.z}`);
    const presentationTarget = await presentBlockTarget({
      context,
      phase: 'locating',
      position: block.position,
      ordinal: attempts - 1,
      data: { attempt: attempts },
    });

    // Reach a visible block face, rather than stopping above a buried target.
    const approachGoal = collectionApproachGoal(bot, block);
    const excavationGoal = collectionExcavationGoal(block);
    try {
      // Visibility goals inspect the current world, so an enclosed ore cannot
      // satisfy them until a coordinate goal has first excavated its access.
      if (block.name !== 'obsidian' && excavationGoal && !approachGoal.isEnd(bot.entity.position.floored())) {
        await bot.pathfinder.goto(excavationGoal);
      }
      if (!approachGoal.isEnd(bot.entity.position.floored())) {
        await bot.pathfinder.goto(approachGoal);
      }
    } catch (e) {
      context.signal?.throwIfAborted();
      recordSearchFailure('navigate', e, { ...block.position });
      // A fresh interaction check below decides whether the current spot is usable.
    }

    // Stop pathfinder and wait for bot to fully stop
    bot.pathfinder.stop();
    await operationWait(200);
    collected = Math.min(Math.max(0, _inventoryCount(dropItem) - startingCount), count);
    if (collected >= count) break;
    _collectDebug(`after navigation pos=${bot.entity.position.x.toFixed(2)},${bot.entity.position.y.toFixed(2)},${bot.entity.position.z.toFixed(2)}`);
    if (!collectionDigSafety(bot, block).safe) {
      excludedTargets.add(collectionBlockKey(block));
      continue;
    }
    if (!approachGoal.isEnd(bot.entity.position.floored())) {
      recordSearchFailure('reach', new Error('Target remains outside digging reach'), {
        ...block.position,
        distance: bot.entity.position.distanceTo(block.position),
      });
      excludedTargets.add(collectionBlockKey(block));
      _collectDebug(`excluded unreachable target=${collectionBlockKey(block)}`);
      continue;
    }

    // Dig block (with retry on abort)
    const pickupItemName = resolvedBlockType === 'gravel' ? ['gravel', 'flint'] : dropItem;
    const minimumPickupCount = pickupInventoryCount(bot, pickupItemName) + 1;
    context.report_phase?.('acting', {
      attempt: attempts,
      ...(presentationTarget ? { target: presentationTarget } : {}),
    });
    let digSuccess = false;
    for (let retry = 0; retry < 3 && !digSuccess; retry++) {
      try {
        await _equipToolForBlock(block, context);
        await digCollectionBlock(bot, block);
        digSuccess = true;
        const afterBlock = bot.blockAt(block.position);
        _collectDebug(`dig success afterBlock=${afterBlock?.name || 'null'}@${block.position.x},${block.position.y},${block.position.z}`);
      } catch (e) {
        context.signal?.throwIfAborted();
        _collectDebug(`dig failed retry=${retry} message=${e.message}`);
        if (retry < 2 && isRecoverableCollectionDigError(e)) {
          if (!isCollectionBlockStillPresent(bot, block)) {
            digSuccess = true;
            break;
          }
          block = bot.blockAt(block.position) || block;
          context.report_phase?.('recovering', {
            attempt: retry + 2,
            reason_code: 'DIG_RETRY',
            ...(presentationTarget ? { target: presentationTarget } : {}),
          });
          if (presentationTarget?.position) {
            await context.presentation?.focus?.({
              phase: 'recovering',
              ordinal: retry + 1,
              target: presentationTarget.position,
            });
          }
          await operationWait(500);
        } else if (isRecoverableCollectionDigError(e)) {
          excludedTargets.add(collectionBlockKey(block));
          _collectDebug(`excluded stalled dig target=${collectionBlockKey(block)}`);
          break;
        } else {
          throw e;
        }
      }
    }

    if (!digSuccess) continue;
    if (digSuccess) {
      if (Array.isArray(context.resourceMutations)) {
        context.resourceMutations.push(collectionResourceMutation(
          block.name,
          block.position,
          bot.game?.dimension || 'minecraft:overworld',
        ));
      }
      if (block.name === 'obsidian') {
        const support = await backfillObsidianHole(bot, block.position, context);
        if (support && Array.isArray(context.resourceMutations)) context.resourceMutations.push(support);
      }
      // Wait for item entity to register and pick up drops
      await operationWait(500);
      await _pickupDroppedItems(8000, block.position, pickupItemName, minimumY, minimumPickupCount);
      context.signal?.throwIfAborted();
      const actual = Math.max(0, _inventoryCount(dropItem) - startingCount);
      collected = Math.min(actual, count);
      _collectDebug(`after pickup actual=${actual} collected=${collected} inventoryCount=${_inventoryCount(dropItem)}`);
    }
  }
  if (collected < count) {
    throw incompleteCollectionError(block_type, dropItem, collected, count, {
      attempts,
      excluded_targets: [...excludedTargets].slice(-5),
      search_failures: searchFailures,
    });
  }
  return `Collected ${collected} ${block_type}`;
}

function craftError(message, code, extra = {}) {
  const err = new Error(message);
  err.code = code;
  Object.assign(err, extra);
  return err;
}

async function _ensureCraftingTable(mcData, context = {}) {
  const waitUntilGround = async (timeoutMs = 3000) => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (bot.entity?.onGround) return;
      await operationWait(100);
    }
  };

  // First: find existing crafting table within 5 blocks (close enough to interact)
  try {
    const veryClose = bot.findBlock({ matching: mcData.blocksByName.crafting_table.id, maxDistance: 5 });
    if (veryClose) return veryClose;
  } catch (e) {}

  if (context.budget?.max_blocks_changed === 0) {
    throw craftError('当前动作没有方块预算，且附近没有可复用的工作台。', 'NO_CRAFTING_TABLE');
  }

  // Second: place a fresh table from inventory. Avoid pathing to stale tables
  // from previous runs when the bot can make a local survival-valid table.
  let tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
  if (!tableItem) {
    try {
      const tableInfo = mcData.itemsByName.crafting_table;
      const hasPlanks = bot.inventory.items().some(i => PLANK_ALIASES.has(i.name) && i.count >= 4);
      if (tableInfo && hasPlanks) {
        const recipes = bot.recipesFor(tableInfo.id, null, 1, null) || [];
        if (recipes.length > 0) {
          await bot.craft(recipes[0], 1, null);
          await operationWait(500);
          tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
        }
      }
    } catch (e) {}
  }
  if (tableItem) {
    const placementBudget = createCraftingTablePlacementBudget();
    await waitUntilGround();
    const pos = bot.entity.position;
    const offsets = [[1, -1, 0], [-1, -1, 0], [0, -1, 1], [0, -1, -1], [0, -1, 0]];
    for (const [dx, dy, dz] of offsets) {
      const bx = Math.floor(pos.x) + dx;
      const by = Math.floor(pos.y) + dy;
      const bz = Math.floor(pos.z) + dz;
      const block = bot.blockAt(new Vec3(bx, by, bz));
      if (block && block.name !== 'air' && block.name !== 'water' && block.name !== 'lava') {
        try {
          const targetPos = new Vec3(bx, by + 1, bz);
          let targetBlock = bot.blockAt(targetPos);
          if (targetBlock && !['air', 'water', 'lava', 'crafting_table'].includes(targetBlock.name)) {
            await _equipToolForBlock(targetBlock);
            await bot.dig(targetBlock);
            await operationWait(300);
            targetBlock = bot.blockAt(targetPos);
          }
          if (targetBlock?.name === 'crafting_table') return targetBlock;
          if (targetBlock && targetBlock.name !== 'air') continue;

          await bot.equip(tableItem, 'hand');
          const target = new Vec3(bx + 0.5, by + 1.5, bz + 0.5);
          if (typeof bot.lookAt === 'function') {
            await bot.lookAt(target, true);
          }
          const canControl = typeof bot.setControlState === 'function';
          const directUnderfoot = dx === 0 && dy === -1 && dz === 0;
          if (canControl && directUnderfoot) {
            bot.setControlState('jump', true);
            await operationWait(150);
            bot.setControlState('jump', false);
            await operationWait(200);
          }
          if (canControl) {
            bot.setControlState('sneak', true);
            await operationWait(100);
          }
          try {
            await placementBudget.place(
              () => bot.placeBlock(block, new Vec3(0, 1, 0)),
            );
          } finally {
            if (canControl) bot.setControlState('sneak', false);
          }
          await operationWait(1000);
          const placed = bot.findBlock({ matching: mcData.blocksByName.crafting_table.id, maxDistance: 5 });
          if (placed) return placed;
        } catch (e) {
          const placed = await recoverPlacedCraftingTableAfterTimeout({
            error: e,
            findPlaced: () => bot.findBlock({
              matching: mcData.blocksByName.crafting_table.id,
              maxDistance: 5,
            }),
          });
          if (placed) return placed;
        }
      }
    }
    const feet = new Vec3(Math.floor(bot.entity.position.x), Math.floor(bot.entity.position.y), Math.floor(bot.entity.position.z));
    const faces = [
      new Vec3(0, 1, 0),
      new Vec3(1, 0, 0),
      new Vec3(-1, 0, 0),
      new Vec3(0, 0, 1),
      new Vec3(0, 0, -1),
    ];
    for (let dx = -2; dx <= 2; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        for (let dz = -2; dz <= 2; dz++) {
          if (!placementBudget.canAttempt()) return null;
          const targetPos = feet.offset(dx, dy, dz);
          if (targetPos.equals(feet) || targetPos.equals(feet.offset(0, 1, 0))) continue;
          const targetBlock = bot.blockAt(targetPos);
          if (!targetBlock || targetBlock.name !== 'air') continue;
          for (const face of faces) {
            const refPos = targetPos.minus(face);
            const refBlock = bot.blockAt(refPos);
            if (!refBlock || ['air', 'water', 'lava'].includes(refBlock.name)) continue;
            try {
              tableItem = bot.inventory.items().find(i => i.name === 'crafting_table');
              if (!tableItem) break;
              await bot.equip(tableItem, 'hand');
              await bot.lookAt(targetPos.offset(0.5, 0.5, 0.5), true);
              await placementBudget.place(() => bot.placeBlock(refBlock, face));
              await operationWait(700);
              const placed = bot.findBlock({ matching: mcData.blocksByName.crafting_table.id, maxDistance: 5 });
              if (placed) return placed;
            } catch (e) {
              const placed = await recoverPlacedCraftingTableAfterTimeout({
                error: e,
                findPlaced: () => bot.findBlock({
                  matching: mcData.blocksByName.crafting_table.id,
                  maxDistance: 5,
                }),
              });
              if (placed) return placed;
            }
          }
        }
      }
    }
    return null;
  }

  // Last: recover a previously placed table, including surface tables above
  // the mining shaft.
  try {
    const far = await findReachableCraftingTable({
      bot,
      craftingTableId: mcData.blocksByName.crafting_table.id,
      GoalNear,
    });
    if (far) return far;
  } catch (e) {}

  return null;
}

async function _reclaimCraftingTable(craftingTable, context = {}) {
  if (context.keep_crafting_table || context.budget?.max_blocks_changed === 0) return;
  if (!craftingTable) return;
  if (bot.inventory.items().some(i => i.name === 'crafting_table')) return;
  try {
    const block = bot.blockAt(craftingTable.position);
    if (!block || block.name !== 'crafting_table') return;
    await _equipToolForBlock(block);
    await bot.dig(block);
    await _pickupDroppedItems(5000, block.position, 'crafting_table', Number.NEGATIVE_INFINITY, 1);
  } catch (e) {
    if (process.env.CRAFT_DEBUG) {
      process.stderr.write(`[craft-debug] reclaim table failed: ${e.message}\n`);
    }
  }
}

// ── Hardcoded fallback recipes for Minecraft 1.21+ ──
// The recipe API sometimes fails to find recipes due to item ID changes.
// These are the standard vanilla recipes as a safety net.
const FALLBACK_RECIPES = {
  ...WOOD_PLANK_RECIPES,
  crafting_table: { ingredients: { oak_planks: 4 }, result: 1, requiresTable: false },
  stick: { ingredients: { oak_planks: 2 }, result: 4, requiresTable: false },
  wooden_pickaxe: { ingredients: { oak_planks: 3, stick: 2 }, result: 1, requiresTable: true },
  stone_pickaxe: { ingredients: { cobblestone: 3, stick: 2 }, result: 1, requiresTable: true },
  iron_pickaxe: { ingredients: { iron_ingot: 3, stick: 2 }, result: 1, requiresTable: true },
  stone_sword: { ingredients: { cobblestone: 2, stick: 1 }, result: 1, requiresTable: true },
  iron_sword: { ingredients: { iron_ingot: 2, stick: 1 }, result: 1, requiresTable: true },
  torch: { ingredients: { coal: 1, stick: 1 }, result: 4, requiresTable: false },
  furnace: { ingredients: { cobblestone: 8 }, result: 1, requiresTable: true },
  iron_chestplate: { ingredients: { iron_ingot: 8 }, result: 1, requiresTable: true },
  chest: { ingredients: { oak_planks: 8 }, result: 1, requiresTable: true },
};

async function _craftWithFallback(recipe, count, craftingTable, context = {}) {
  const fallback = FALLBACK_RECIPES[recipe];
  if (!fallback) return null;

  // Check if we have materials
  const inventory = {};
  for (const item of bot.inventory.items()) {
    inventory[item.name] = (inventory[item.name] || 0) + item.count;
  }

  const missing = {};
  // How many times we need to perform the craft
  const craftCount = Math.ceil(count / fallback.result);
  for (const [mat, needed] of Object.entries(fallback.ingredients)) {
    const have = availableMaterialCount(inventory, mat, PLANK_ALIASES);
    const totalNeeded = needed * craftCount;
    if (have < totalNeeded) {
      missing[mat] = totalNeeded - have;
    }
  }

  if (Object.keys(missing).length > 0) {
    const missingStr = Object.entries(missing).map(([k, v]) => `${k} (need ${v})`).join(', ');
    throw craftError(`Missing materials for ${recipe}: ${missingStr}`, 'MISSING_MATERIALS', { missing });
  }

  // For 2x2 recipes, craft without table
  if (!fallback.requiresTable) {
    try {
      const mcData = await getMcData();
      const item = mcData.itemsByName[recipe];
      if (!item) throw new Error(`Unknown item: ${recipe}`);

      // Try recipesFor first
      let recipes = bot.recipesFor(item.id, null, count, craftingTable);
      if (!recipes || recipes.length === 0) {
        recipes = bot.recipesFor(item.id, null, count, null);
      }

      // If still empty, get ALL recipes and try manually
      if (!recipes || recipes.length === 0) {
        const allRecipes = bot.recipesAll(item.id, null, null);
        if (allRecipes && allRecipes.length > 0) {
          // Filter recipes to only use materials we actually have
          const viable = allRecipes.filter(r => {
            const missing = _checkCraftMaterials(r, count);
            return missing.length === 0;
          });
          // Prefer recipes using common materials (oak_planks, cobblestone, etc.)
          const preferred = viable.find(r => {
            const names = _getRecipeIngredientNames(r, mcData);
            return names.some(n => n.includes('oak_planks') || n.includes('oak_log') || n.includes('cobblestone'));
          }) || viable[0];
          if (preferred) {
            // Try all viable recipes until one works (wood variants may fail)
            const toTry = preferred ? [preferred, ...viable.filter(r => r !== preferred)] : viable;
            for (const candidateRecipe of toTry) {
              try {
                const before = _inventoryCount(recipe);
                await bot.craft(candidateRecipe, craftOperations(candidateRecipe, count, fallback.result), null);
                await _waitForInventoryIncrease(recipe, before, 1);
                return `Crafted ${count} ${recipe} (fallback)`;
              } catch (e) { /* try next */ }
            }
          }
        }
        // Last resort: try craftingTable
        if (craftingTable) {
          const allTable = bot.recipesAll(item.id, null, craftingTable);
          if (allTable && allTable.length > 0) {
            const viable = allTable.filter(r => {
              const missing = _checkCraftMaterials(r, count);
              return missing.length === 0;
            });
            const preferred = viable.find(r => {
              const names = _getRecipeIngredientNames(r, mcData);
              return names.some(n => n.includes('oak_planks') || n.includes('oak_log') || n.includes('cobblestone'));
            }) || viable[0];
            if (preferred) {
              const toTry = preferred ? [preferred, ...viable.filter(r => r !== preferred)] : viable;
              for (const candidateRecipe of toTry) {
                try {
                  const before = _inventoryCount(recipe);
                  await bot.craft(
                    candidateRecipe,
                    craftOperations(candidateRecipe, count, fallback.result),
                    craftingTable,
                  );
                  await _waitForInventoryIncrease(recipe, before, 1);
                  await _reclaimCraftingTable(craftingTable, context);
                  return `Crafted ${count} ${recipe} (fallback-table)`;
                } catch (e) { /* try next */ }
              }
            }
          }
        }
        throw new Error('No recipes found even with fallback');
      }

      const before = _inventoryCount(recipe);
      await bot.craft(
        recipes[0],
        craftOperations(recipes[0], count, fallback.result),
        craftingTable || null,
      );
      await _waitForInventoryIncrease(recipe, before, 1);
      await _reclaimCraftingTable(craftingTable, context);
      return `Crafted ${count} ${recipe}`;
    } catch (e) {
      if (e.code) throw e;
      throw craftError(`Fallback craft failed: ${e.message}`, 'CRAFT_FAILED');
    }
  }

  // For 3x3 recipes, need crafting table
  if (!craftingTable) {
    throw craftError(`No crafting table for ${recipe}`, 'NO_CRAFTING_TABLE', { needsTable: true });
  }

  try {
    const mcData = await getMcData();
    const item = mcData.itemsByName[recipe];
    if (!item) throw new Error(`Unknown item: ${recipe}`);

    const recipes = bot.recipesFor(item.id, null, count, craftingTable);
    if (recipes && recipes.length > 0) {
      const before = _inventoryCount(recipe);
      await bot.craft(
        recipes[0],
        craftOperations(recipes[0], count, fallback.result),
        craftingTable,
      );
      await _waitForInventoryIncrease(recipe, before, 1);
      await _reclaimCraftingTable(craftingTable, context);
      return `Crafted ${count} ${recipe}`;
    }

    // Try recipesAll as fallback
    const allRecipes = bot.recipesAll(item.id, null, craftingTable);
    if (allRecipes && allRecipes.length > 0) {
      // Filter to recipes using materials we have
      const viable = allRecipes.filter(r => {
        const missing = _checkCraftMaterials(r, count);
        return missing.length === 0;
      });
      const preferred = viable.find(r => {
        const names = _getRecipeIngredientNames(r, mcData);
        return names.some(n => n.includes('oak_planks') || n.includes('cobblestone') || n.includes('iron'));
      }) || viable[0];
      if (preferred) {
        try {
          const before = _inventoryCount(recipe);
          await bot.craft(
            preferred,
            craftOperations(preferred, count, fallback.result),
            craftingTable,
          );
          await _waitForInventoryIncrease(recipe, before, 1);
          await _reclaimCraftingTable(craftingTable, context);
          return `Crafted ${count} ${recipe} (fallback)`;
        } catch (e) { /* continue */ }
      }
    }

    throw new Error('No recipes found even with fallback');
  } catch (e) {
    if (e.code) throw e;
    throw craftError(`Fallback craft failed: ${e.message}`, 'CRAFT_FAILED');
  }
}

async function _craft(recipe, count = 1, context = {}) {
  context.operation_scope?.checkpoint();
  context = { ...context, keep_crafting_table: recipe === 'furnace' };
  const mcData = await getMcData();
  const fallbackRecipe = FALLBACK_RECIPES[recipe] || null;

  // Look up item by name
  const item = mcData.itemsByName[recipe];
  if (!item) {
    throw craftError(`Item not found: ${recipe}`, 'NO_RECIPE');
  }
  const inventoryRecipes = fallbackRecipe ? [] : (bot.recipesFor(item.id, null, count, null) || []);
  const needsCraftingTable = fallbackRecipe?.requiresTable ?? (inventoryRecipes.length === 0);

  // Only locate/place a table for recipes that may actually need one.
  // Inventory recipes like logs -> planks must stay local, otherwise the bot can
  // waste the command timeout pathing to an old table in the world.
  const craftingTable = needsCraftingTable === false ? null : await _ensureCraftingTable(mcData, context);
  const presentationTarget = await presentBlockTarget({
    context,
    phase: 'aiming',
    position: craftingTable?.position,
  });
  context.report_phase?.('acting', presentationTarget ? { target: presentationTarget } : {});
  if (fallbackRecipe?.requiresTable) {
    const deterministicResult = await _craftWithFallback(recipe, count, craftingTable, context);
    if (deterministicResult) return deterministicResult;
  }
  let allRecipes = inventoryRecipes;
  if (allRecipes.length === 0 && needsCraftingTable !== true) {
    allRecipes = bot.recipesAll(item.id, null, null) || [];
  }
  if (allRecipes.length === 0 && craftingTable) {
    allRecipes = bot.recipesAll(item.id, null, craftingTable) || [];
  }
  if (allRecipes.length === 0 && needsCraftingTable !== true) {
    allRecipes = bot.recipesAll(item.id, null, null) || [];
  }
  if (allRecipes.length === 0 && mcData.recipes && mcData.recipes[item.id]) {
    allRecipes = mcData.recipes[item.id] || [];
  }

  // Debug: log recipe info
  const debugInfo = {
    recipe, itemId: item.id, hasTable: !!craftingTable,
    recipesWithTable: craftingTable ? (bot.recipesAll(item.id, null, craftingTable) || []).length : 0,
    recipesWithoutTable: (bot.recipesAll(item.id, null, null) || []).length,
    recipesFromData: (mcData.recipes && mcData.recipes[item.id] ? mcData.recipes[item.id] : []).length,
    totalRecipes: allRecipes.length,
  };
  if (process.env.CRAFT_DEBUG) {
    process.stderr.write(`[craft-debug] ${JSON.stringify(debugInfo)}\n`);
  }

  if (!allRecipes || allRecipes.length === 0) {
    // Try hardcoded fallback recipes (1.21.4 compatibility)
    const fallbackTable = fallbackRecipe?.requiresTable ? craftingTable : null;
    const fallbackResult = await _craftWithFallback(recipe, count, fallbackTable, context);
    if (fallbackResult) {
      return fallbackResult;
    }
    throw craftError(`No recipes for ${recipe}`, 'NO_RECIPE');
  }

  // Find a recipe whose ingredients match items we actually have in inventory
  // Use _checkCraftMaterials which handles plank aliases (1.21.4 wood variants)
  const viable = allRecipes.filter(r => {
    const missing = _checkCraftMaterials(r, count);
    return missing.length === 0;
  });
  const orderedViable = _orderRecipesForInventory(viable, mcData);

  if (viable.length === 0) {
    // No recipes match — try all recipes anyway (some may work despite mismatched IDs)
    for (const r of allRecipes) {
      try {
        const before = _inventoryCount(recipe);
        await bot.craft(
          r,
          craftOperations(r, count, fallbackRecipe?.result),
          needsCraftingTable === false ? null : craftingTable || null,
        );
        await _waitForInventoryIncrease(recipe, before, 1);
        await _reclaimCraftingTable(needsCraftingTable === false ? null : craftingTable || null, context);
        return `Crafted ${count} ${recipe} (tried-all)`;
      } catch (e) { /* try next */ }
    }
    if (fallbackRecipe) {
      const fallbackTable = fallbackRecipe.requiresTable ? (craftingTable || await _ensureCraftingTable(mcData, context)) : null;
      const fallbackResult = await _craftWithFallback(recipe, count, fallbackTable, context);
      await _reclaimCraftingTable(fallbackTable, context);
      return fallbackResult;
    }
    const missing = _checkCraftMaterials(allRecipes[0], count);
    throw craftError(`Missing materials for ${recipe}: ${missing.join(', ')}`, 'MISSING_MATERIALS');
  }

  // Try all viable recipes until one works (wood variants may fail)
  for (const recipeToUse of orderedViable) {
    try {
      const before = _inventoryCount(recipe);
      await bot.craft(
        recipeToUse,
        craftOperations(recipeToUse, count, fallbackRecipe?.result),
        needsCraftingTable === false ? null : craftingTable || null,
      );
      await _waitForInventoryIncrease(recipe, before, 1);
      await _reclaimCraftingTable(needsCraftingTable === false ? null : craftingTable || null, context);
      return `Crafted ${count} ${recipe}`;
    } catch (e) { /* try next */ }
  }

  // If no viable recipe worked, try all recipes as last resort
  for (const r of allRecipes) {
    try {
      const before = _inventoryCount(recipe);
      await bot.craft(
        r,
        craftOperations(r, count, fallbackRecipe?.result),
        needsCraftingTable === false ? null : craftingTable || null,
      );
      await _waitForInventoryIncrease(recipe, before, 1);
      await _reclaimCraftingTable(needsCraftingTable === false ? null : craftingTable || null, context);
      return `Crafted ${count} ${recipe} (all-recipes)`;
    } catch (e) { /* try next */ }
  }

  if (fallbackRecipe) {
    const fallbackTable = fallbackRecipe.requiresTable ? (craftingTable || await _ensureCraftingTable(mcData, context)) : null;
    const fallbackResult = await _craftWithFallback(recipe, count, fallbackTable, context);
    await _reclaimCraftingTable(fallbackTable, context);
    return fallbackResult;
  }

  throw craftError(`Craft failed for ${recipe}: no working recipe`, 'CRAFT_FAILED');
}

function _getRecipeIngredientNames(recipe, mcData) {
  const names = [];
  if (recipe.inShape) {
    for (const row of recipe.inShape) {
      for (const cell of row) {
        const cellId = typeof cell === 'number' ? cell : (cell && cell.id);
        if (cellId && cellId !== -1 && cellId !== 0) {
          names.push(mcData.items[cellId]?.name || mcData.blocks[cellId]?.name || '');
        }
      }
    }
  }
  if (recipe.ingredients) {
    for (const ing of recipe.ingredients) {
      const ingId = typeof ing === 'number' ? ing : (ing && ing.id);
      if (ingId && ingId !== -1 && ingId !== 0) {
        names.push(mcData.items[ingId]?.name || mcData.blocks[ingId]?.name || '');
      }
    }
  }
  return names;
}

async function _manualCraft(recipeObj, itemName, count) {
  // Manual crafting using window API
  // Supports both inShape (shaped) and ingredients (shapeless) recipes

  const mcData = await getMcData();

  // Get required materials from recipe
  const required = {};
  let isShapeless = false;

  if (recipeObj.inShape) {
    // Shaped recipe: inShape is a 2D array of item IDs
    for (const row of recipeObj.inShape) {
      for (const cell of row) {
        const cellId = typeof cell === 'number' ? cell : (cell && cell.id);
        if (cellId && cellId !== -1) {
          const name = (mcData.items[cellId] || mcData.blocks[cellId] || {}).name;
          if (name) {
            required[name] = (required[name] || 0) + 1;
          }
        }
      }
    }
  } else if (recipeObj.ingredients) {
    // Shapeless recipe: ingredients is a flat array of item IDs
    isShapeless = true;
    for (const ing of recipeObj.ingredients) {
      const ingId = typeof ing === 'number' ? ing : (ing && ing.id);
      if (ingId && ingId !== -1) {
        const name = (mcData.items[ingId] || mcData.blocks[ingId] || {}).name;
        if (name) {
          required[name] = (required[name] || 0) + 1;
        }
      }
    }
  }

  if (Object.keys(required).length === 0) {
    return null; // No materials required — bad recipe
  }

  // Check if we have all materials
  const inventory = {};
  for (const item of bot.inventory.items()) {
    inventory[item.name] = (inventory[item.name] || 0) + item.count;
  }

  for (const [name, needed] of Object.entries(required)) {
    if ((inventory[name] || 0) < needed * count) {
      return null; // Not enough materials
    }
  }

  // Place materials in crafting grid (3x3)
  const window = bot.inventory;
  const craftingSlots = [1, 2, 3, 4, 5, 6, 7, 8, 9]; // 3x3 grid

  let slotIndex = 0;
  for (const [name, needed] of Object.entries(required)) {
    const items = bot.inventory.items().filter(i => i.name === name);
    let placed = 0;
    for (const item of items) {
      if (placed >= needed * count) break;
      if (slotIndex >= craftingSlots.length) break;
      for (let i = 0; i < Math.min(item.count, needed * count - placed) && slotIndex < craftingSlots.length; i++) {
        await bot.moveSlotItem(item.slot, craftingSlots[slotIndex]);
        slotIndex++;
        placed++;
      }
    }
  }

  // Wait for crafting result
  await operationWait(500);

  // Check if we have a result
  const result = window.slots[0];
  if (result && result.name === itemName) {
    // Click to craft
    await bot.clickWindow(0, 0, 0);
    return `Crafted ${count} ${itemName}`;
  }

  return null;
}

// ── Plank type aliases (all planks are interchangeable for crafting) ──
const PLANK_ALIASES = new Set([
  'oak_planks', 'spruce_planks', 'birch_planks', 'jungle_planks',
  'acacia_planks', 'dark_oak_planks', 'mangrove_planks', 'cherry_planks',
  'bamboo_planks', 'crimson_planks', 'warped_planks', 'pale_oak_planks',
]);

function _checkCraftMaterials(recipeObj, count) {
  const missing = [];
  const inventory = {};
  for (const item of bot.inventory.items()) {
    inventory[item.name] = (inventory[item.name] || 0) + item.count;
  }

  // Count total planks available (all types are interchangeable)
  let totalPlanks = 0;
  for (const p of PLANK_ALIASES) {
    totalPlanks += inventory[p] || 0;
  }

  const required = {};
  const addIngredient = (id, qty) => {
    const mcData = _mcDataCache;
    const name = (mcData.items[id] || mcData.blocks[id] || {}).name || `item(${id})`;
    required[name] = (required[name] || 0) + qty;
  };

  if (recipeObj.inShape) {
    for (const row of recipeObj.inShape) {
      for (const cell of row) {
        const cellId = typeof cell === 'number' ? cell : (cell && cell.id);
        if (cellId !== null && cellId !== undefined && cellId !== -1) {
          addIngredient(cellId, 1);
        }
      }
    }
  }
  if (recipeObj.ingredients) {
    for (const ing of recipeObj.ingredients) {
      const ingId = typeof ing === 'number' ? ing : (ing && ing.id);
      if (ingId !== null && ingId !== undefined && ingId !== -1) {
        addIngredient(ingId, 1);
      }
    }
  }

  for (const [name, needed] of Object.entries(required)) {
    const totalNeeded = needed * count;
    // Check if this is a plank type — use total plank count
    if (PLANK_ALIASES.has(name)) {
      if (totalPlanks < totalNeeded) {
        missing.push(`${name} (need ${totalNeeded}, have ${totalPlanks})`);
      }
    } else {
      const have = inventory[name] || 0;
      if (have < totalNeeded) {
        missing.push(`${name} (need ${totalNeeded}, have ${have})`);
      }
    }
  }
  return missing;
}

// 冶炼/穿戴/下矿 模块（smelt.js / equip.js / mine_shaft.js）
const smeltMod = createSmelt({ bot, getMcData, botUsername: username });
const equipMod = createEquip({ bot });
const mineShaftMod = createMineShaft({
  bot,
});

async function _recipes(item, context = {}) {
  context.operation_scope?.checkpoint();
  const mcData = await getMcData();
  const itemInfo = mcData.itemsByName[item];
  if (!itemInfo) throw new Error(`Unknown item: ${item}`);

  // Get ALL possible recipes (not filtered by inventory)
  const craftingTable = bot.findBlock({ matching: mcData.blocksByName.crafting_table.id, maxDistance: 32 });
  let recipes = bot.recipesAll(itemInfo.id, null, null) || [];

  // Also check with crafting table if available
  if (craftingTable) {
    const tableRecipes = bot.recipesAll(itemInfo.id, null, craftingTable) || [];
    const seen = new Set(recipes.map(r => JSON.stringify(r.inShape || r.ingredients)));
    for (const r of tableRecipes) {
      const key = JSON.stringify(r.inShape || r.ingredients);
      if (!seen.has(key)) recipes.push(r);
    }
  }

  if (recipes.length === 0) return `No recipes for ${item}`;

  const formatIngredient = (id) => {
    if (typeof id === 'object' && id !== null) {
      return id.name || mcData.items[id.id]?.name || mcData.blocks[id.id]?.name || `item(${id.id})`;
    }
    return mcData.items[id]?.name || mcData.blocks[id]?.name || `item(${id})`;
  };

  return recipes.map(r => {
    const parts = [];
    if (r.inShape) {
      for (const row of r.inShape) {
        for (const cell of row) {
          const cellId = typeof cell === 'number' ? cell : (cell && cell.id);
          if (cellId && cellId !== -1 && cellId !== 0) {
            parts.push(formatIngredient(cell));
          }
        }
      }
    } else if (r.ingredients) {
      for (const ing of r.ingredients) {
        const ingId = typeof ing === 'number' ? ing : (ing && ing.id);
        if (ingId && ingId !== -1 && ingId !== 0) {
          parts.push(formatIngredient(ing));
        }
      }
    }
    return `${item}: ${parts.join(' + ')}${r.requiresTable ? ' [requires crafting table]' : ''}`;
  }).join('\n');
}

function _orderRecipesForInventory(recipes, mcData) {
  const inventoryNames = new Set(bot.inventory.items().map(item => item.name));
  return [...recipes].sort((left, right) => {
    const exactMatches = (recipe) => _getRecipeIngredientNames(recipe, mcData)
      .filter(name => inventoryNames.has(name)).length;
    return exactMatches(right) - exactMatches(left);
  });
}


async function abortCurrentAction() {
  stopCollectionMovement(bot);
  await bot.pvp?.stop?.();
  bot.stopDigging?.();
  return interruptRunningOperation();
}


let gameBotV2Adapter;
let clientViewerCtx;
const protocol = createRuntimeProcessProtocol({
  input: stdin,
  output: stdout,
  abortActive: abortCurrentAction,
  commands: {
    gamebot_v2_manifest: {
      bypassBusy: true,
      timeoutMs: 5_000,
      execute: () => gameBotV2Adapter.runtime.getManifest(),
    },
    gamebot_v2_observe: {
      bypassBusy: true,
      timeoutMs: 5_000,
      execute: (params) => gameBotV2Adapter.runtime.observe(params),
    },
    gamebot_v2_execute_action: {
      timeoutMs: (params) => actionTimeoutFromDeadline(params.deadline_ms),
      execute: (params) => gameBotV2Adapter.runtime.executeAction(params),
    },
    gamebot_v2_inspect_region: {
      bypassBusy: true,
      timeoutMs: 10_000,
      execute: (params) => gameBotV2Adapter.runtime.inspectRegion(params),
    },
    gamebot_v2_inspect_action: {
      bypassBusy: true,
      timeoutMs: 5_000,
      execute: (params) => gameBotV2Adapter.runtime.inspectAction(params),
    },
    gamebot_v2_cancel_action: {
      bypassBusy: true,
      timeoutMs: 10_000,
      execute: (params) => gameBotV2Adapter.runtime.cancelAction(params),
    },
    gamebot_v2_health: {
      bypassBusy: true,
      timeoutMs: 5_000,
      async execute() {
        const health = await gameBotV2Adapter.runtime.health();
        const transport = protocol.getState();
        return {
          ...health,
          ready: health.ready && Boolean(bot.entity) && !transport.quarantined,
        };
      },
    },
    survival_iron: {
      timeoutMs: (_params, command) => command.timeout_ms ?? 2_130_000,
      async execute(params) {
        try {
          return await runSurvivalIron(bot, {
            globalTimeoutMs: params.timeout_ms
              || (params.timeout ? params.timeout * 1_000 : 25 * 60 * 1_000),
          });
        } catch (error) {
          error.code ||= 'SURVIVAL_IRON_ERROR';
          throw error;
        }
      },
    },
    spectate: {
      timeoutMs: 15_000,
      execute() {
        if (!clientViewerCtx.config.enabled || !clientViewerCtx.config.username) {
          const error = new Error('No viewer username configured');
          error.code = 'VIEWER_NOT_CONFIGURED';
          throw error;
        }
        const status = clientViewerCtx.requestAttach('manual_retry');
        return {
          binding_state: status.binding_state,
          confirmed: status.confirmed,
          target: status.target,
          attempt: status.attempt,
          reason: status.reason,
        };
      },
    },
  },
});
const { sendEvent } = protocol;
const presentation = resolvePresentationConfig();

gameBotV2Adapter = createGameBotV2Adapter({
  bot,
  connection: { host, port, username, version },
  abortActive: abortCurrentAction,
  emitEvent: sendEvent,
  presentation,
  actions: {
    goto: _goto,
    collectWithEvidence: _collectWithEvidence,
    mine: _mine,
    craft: _craft,
    placeWithEvidence: _placeWithEvidence,
    eat: (item, context) => eatFood(bot, item, context),
    forageApples: (maxBlocks, context) => forageApples(bot, maxBlocks, context, {
      navigate: (position) => (
        _navigateFoodSurface(new GoalNear(position.x, position.y, position.z, 3), context)
      ),
      pickup: _pickupDroppedItems,
    }),
    async exploreSurface(x, z, context) {
      const before = bot.entity.position.clone();
      const reached = await _navigateFoodSurface(new GoalXZ(x, z), context);
      return {
        output: { reached },
        budget_usage: { max_actions: 1, max_travel_distance: before.distanceTo(bot.entity.position) },
      };
    },
    async waitForRegeneration(context) {
      context.operation_scope?.checkpoint();
      await operationWait(2000);
      return { output: { health: bot.health, food: bot.food }, budget_usage: { max_actions: 1 } };
    },
    ignitePortal: (parameters, context) => ignitePortal(bot, parameters, context),
    fillWaterBucket: (context) => fillWaterBucket(bot, context),
    prepareObsidian: (context) => prepareObsidian(bot, context),
    acquireFlint: (maxAttempts, context) => acquireFlint(bot, maxAttempts, context, {
      collect: (scopedContext) => _collect('gravel', 1, scopedContext),
      place: (position, scopedContext) => (
        _placeWithEvidence('gravel', position.x, position.y, position.z, undefined, scopedContext)
      ),
    }),
    smelt: (item, fuel, count, context) => smeltMod.smelt(item, fuel, count, context),
    equip: (item, destination, context) => equipMod.equip(item, destination, context),
    attackWithEvidence: _attackWithEvidence,
    chat(message, context = {}) {
      context.operation_scope?.checkpoint();
      bot.chat(assertSurvivalChat(message));
      return 'Chat message sent';
    },
    recipes: _recipes,
    mineShaft: (targetY, minimumCobblestone, context) => (
      mineShaftMod.mineShaft(targetY, minimumCobblestone, context)
    ),
  },
});

clientViewerCtx = setupClientViewer(bot, username, sendEvent);
if (clientViewerCtx.config?.enabled) {
  console.error(
    `[index] client-viewer enabled: username=${clientViewerCtx.config.username}, `
    + `mode=${clientViewerCtx.config.mode}`,
  );
}

bot.on('login', () => {
  sendEvent('login', { username: bot.username });
  sendEvent('presentation_configured', {
    mode: presentation.mode,
    tempo: presentation.tempo,
    seed_digest: presentationSeedDigest(presentation.seed),
  });
});

bot.on('spawn', () => {
  patchPathfinder();
  patchInterruptibleBotMethods();
  sendEvent('spawn');
  bot._collect = _collect;
  bot._craft = _craft;
  bot._smelt = smeltMod.smelt.bind(smeltMod);
  bot._equipTo = async (item, destination) => equipMod.equip(item, destination || 'hand');
});

bot.on('error', (error) => {
  sendEvent('error', { message: error.message });
});

bot.on('end', (reason) => {
  clientViewerCtx.dispose();
  gameBotV2Adapter.dispose();
  sendEvent('disconnect', { reason });
});

protocol.start();
