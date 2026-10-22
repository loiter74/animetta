import { withTimeout } from './actionDeadline.js';
import { operationWait } from './runtime/operationScope.js';
import { getResourceDefinition, isUndergroundCategory } from './resources/registry.js';
import Vec3 from 'vec3';
import pathfinderPkg from 'mineflayer-pathfinder';

const SOFT_LOCATOR_FAILURES = new Set(['RESOURCE_NOT_FOUND', 'SEARCH_TIMEOUT']);
const MOVEMENT_CONTROLS = ['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak'];
const POSITION_EPSILON = 0.02;
const FLUID_HAZARDS = new Set(['water', 'flowing_water', 'lava', 'flowing_lava']);
const LAVA_BLOCK_NAMES = new Set(['lava', 'flowing_lava']);
const NEIGHBOR_OFFSETS = Object.freeze([
  [1, 0, 0],
  [-1, 0, 0],
  [0, 0, 1],
  [0, 0, -1],
  [0, 1, 0],
  [0, -1, 0],
]);

export function isLavaBlock(block) {
  return LAVA_BLOCK_NAMES.has(block?.name);
}

export function isWaterBlock(block) {
  return block?.name === 'water' || block?.name === 'flowing_water';
}

export function configureDryNavigation(movements, bot, { allowSurfaceSwimming = false } = {}) {
  // The SDK compares the supporting floor, one cell below the actual landing.
  movements.maxDropDown = 2;
  movements.allowParkour = false;
  movements.allowSprinting = false;
  const stepCost = node => {
    const position = node.position ?? node;
    const feet = new Vec3(position.x, position.y, position.z);
    const body = bot.blockAt(feet);
    const head = bot.blockAt(feet.offset(0, 1, 0));
    if (isLavaBlock(body) || isLavaBlock(head) || isWaterBlock(head)) return Infinity;
    if (!allowSurfaceSwimming && isWaterBlock(body)
      && bot.blockAt(feet.offset(0, -1, 0))?.boundingBox !== 'block') return Infinity;
    return 0;
  };
  movements.exclusionAreasStep.push(stepCost);
  // Native downward moves do not apply exclusionStep to their landing block.
  const getLandingBlock = movements.getLandingBlock.bind(movements);
  movements.getLandingBlock = (node, direction) => {
    const landing = getLandingBlock(node, direction);
    if (!landing || node.y - landing.position.y > 1
      || movements.exclusionStep(landing) >= 100) return null;
    return landing;
  };
  return movements;
}

export function restrictNavigationHeight(movements, minimumY) {
  movements.exclusionAreasStep.push(node => (node.position ?? node).y < minimumY ? Infinity : 0);
}

export function isAirLikeForStanding(block) {
  return Boolean(block) && (block.name === 'air' || (
    block.boundingBox === 'empty'
    && !FLUID_HAZARDS.has(block.name)
  ));
}

function offsetPosition(position, dx, dy, dz) {
  if (typeof position?.offset === 'function') return position.offset(dx, dy, dz);
  return {
    x: Number(position.x) + dx,
    y: Number(position.y) + dy,
    z: Number(position.z) + dz,
  };
}

function flooredPosition(position) {
  if (typeof position?.floored === 'function') return position.floored();
  return {
    x: Math.floor(Number(position.x)),
    y: Math.floor(Number(position.y)),
    z: Math.floor(Number(position.z)),
  };
}

function positionDistance(left, right) {
  if (!left || !right) return Number.POSITIVE_INFINITY;
  if (typeof left.distanceTo === 'function') return left.distanceTo(right);
  return Math.hypot(
    Number(left.x) - Number(right.x),
    Number(left.y) - Number(right.y),
    Number(left.z) - Number(right.z),
  );
}

// Standing requires solid support and clear headroom; grounded shallow water
// is permitted, while lava and unknown cells are rejected.
export function isSafeStandingPosition(bot, feetPosition) {
  if (typeof bot?.blockAt !== 'function' || !feetPosition) return false;
  const support = bot.blockAt(offsetPosition(feetPosition, 0, -1, 0));
  if (!support || support.boundingBox !== 'block') return false;
  return (isAirLikeForStanding(bot.blockAt(feetPosition)) || isWaterBlock(bot.blockAt(feetPosition)))
    && isAirLikeForStanding(bot.blockAt(offsetPosition(feetPosition, 0, 1, 0)));
}

export function nearestSafeStandingPosition(
  bot,
  {
    origin,
    maxRadius = 4,
    upRange = 2,
    downRange = 4,
    nearestTo = null,
    minimumY = Number.NEGATIVE_INFINITY,
  } = {},
) {
  if (typeof bot?.blockAt !== 'function' || !origin) return null;
  const reference = nearestTo ?? bot.entity?.position ?? origin;
  const base = flooredPosition(origin);
  const candidates = [];
  for (let dx = -maxRadius; dx <= maxRadius; dx++) {
    for (let dz = -maxRadius; dz <= maxRadius; dz++) {
      for (let dy = upRange; dy >= -downRange; dy--) {
        const feetPosition = offsetPosition(base, dx, dy, dz);
        if (feetPosition.y < minimumY) continue;
        if (!isSafeStandingPosition(bot, feetPosition)) continue;
        candidates.push({
          position: feetPosition,
          distance: positionDistance(reference, feetPosition),
        });
      }
    }
  }
  candidates.sort((left, right) => left.distance - right.distance);
  return candidates[0]?.position ?? null;
}

// Settlement accepts grounded shallow water only with solid support and an
// air-like head cell; lava or a submerged head remains a hazard.
export function isCollectionSettleHazard(bot) {
  const entity = bot?.entity;
  const position = entity?.position;
  if (!position || typeof bot.blockAt !== 'function') return false;
  const feetPosition = typeof position.floored === 'function' ? position.floored() : position;
  const feet = bot.blockAt(feetPosition);
  const head = bot.blockAt(offsetPosition(feetPosition, 0, 1, 0));
  if (isLavaBlock(feet) || isLavaBlock(head)) return true;
  if (isWaterBlock(head)) return true;
  if (!isWaterBlock(feet)) return false;
  if (entity.onGround === false) return true;
  const support = bot.blockAt(offsetPosition(feetPosition, 0, -1, 0));
  return !support || support.boundingBox !== 'block';
}

export function isCollectionFluidHazard(bot) {
  const position = bot.entity?.position;
  if (!position || typeof bot.blockAt !== 'function') return false;
  const feetPosition = typeof position.floored === 'function' ? position.floored() : position;
  const feet = bot.blockAt(feetPosition);
  let head = null;
  if (typeof feetPosition.offset === 'function') {
    head = bot.blockAt(feetPosition.offset(0, 1, 0));
  }
  return FLUID_HAZARDS.has(feet?.name) || FLUID_HAZARDS.has(head?.name);
}

export function stopCollectionMovement(bot) {
  try { bot.pathfinder?.stop?.(); } catch {}
  for (const control of MOVEMENT_CONTROLS) {
    try { bot.setControlState?.(control, false); } catch {}
  }
}

function positionsMatch(left, right) {
  if (!left || !right) return false;
  return ['x', 'y', 'z'].every((axis) => (
    Number.isFinite(left[axis])
    && Number.isFinite(right[axis])
    && Math.abs(left[axis] - right[axis]) <= POSITION_EPSILON
  ));
}

function movementIsSettled(bot, entity) {
  if (!entity || entity.onGround === false || isCollectionSettleHazard(bot)) return false;
  const velocity = entity.velocity || {};
  const x = Number(velocity.x);
  const y = Number(velocity.y);
  const z = Number(velocity.z);
  return (
    (!Number.isFinite(x) || Math.abs(x) <= 0.02)
    && (!Number.isFinite(y) || (y >= -0.09 && y <= 0.01))
    && (!Number.isFinite(z) || Math.abs(z) <= 0.02)
  );
}

export async function waitForCollectionMovementToSettle(bot, {
  timeoutMs = 10_000,
  pollMs = 100,
  stableSamples = 3,
  nowMs = () => Date.now(),
  waitMs = operationWait,
} = {}) {
  stopCollectionMovement(bot);
  const deadline = nowMs() + timeoutMs;
  let previousPosition = null;
  let stableStreak = 0;

  while (true) {
    const entity = bot.entity;
    const position = entity?.position;
    if (movementIsSettled(bot, entity)) {
      stableStreak = positionsMatch(previousPosition, position) ? stableStreak + 1 : 1;
    } else {
      stableStreak = 0;
    }
    previousPosition = position
      ? { x: Number(position.x), y: Number(position.y), z: Number(position.z) }
      : null;
    if (stableStreak >= stableSamples) return true;
    if (nowMs() >= deadline) return false;
    await waitMs(pollMs);
  }
}

export function collectionBlockKey(block) {
  const { x, y, z } = block.position;
  return `${x},${y},${z}`;
}

export function collectionApproachGoal(bot, block) {
  return new pathfinderPkg.goals.GoalLookAtBlock(block.position, bot.world, {
    reach: 4.5, entityHeight: bot.entity?.eyeHeight || 1.62,
  });
}

export function collectionExcavationGoal(block) {
  const { x, y, z } = block.position;
  return new pathfinderPkg.goals.GoalGetToBlock(x, y, z);
}

export function collectionResourceMutation(blockType, position, dimension = 'minecraft:overworld') {
  const normalizedBlock = String(blockType).includes(':')
    ? String(blockType)
    : `minecraft:${blockType}`;
  const normalizedDimension = String(dimension).includes(':')
    ? String(dimension)
    : `minecraft:${dimension}`;
  return {
    kind: 'block',
    subject: `block:${normalizedDimension}:${position.x}:${position.y}:${position.z}`,
    delta: -1,
    details: { block_type: normalizedBlock },
  };
}

export function createCollectionBlockMatcher(blockId, excludedKeys = new Set(), eligible = () => true) {
  const blockIds = blockId instanceof Set
    ? blockId
    : new Set(Array.isArray(blockId) ? blockId : [blockId]);
  return (block) => (
    blockIds.has(block?.type) &&
    (!block.position || (!excludedKeys.has(collectionBlockKey(block)) && eligible(block)))
  );
}

export function findCollectionTarget(bot, blockId, maxDistance, excludedKeys = new Set()) {
  return bot.findBlock({
    matching: createCollectionBlockMatcher(blockId, excludedKeys),
    maxDistance,
  });
}

export function isCollectionBlockStillPresent(bot, block) {
  const current = bot.blockAt(block.position);
  return current?.type === block.type;
}

export function isRecoverableCollectionDigError(error) {
  return (
    error?.code === 'COLLECT_FAILED' ||
    String(error?.message || '').includes('Digging aborted')
  );
}

export function shouldRetryStructuredResourceSearch(resourceName, error) {
  if (!SOFT_LOCATOR_FAILURES.has(error?.code)) return false;
  try {
    return isUndergroundCategory(getResourceDefinition(resourceName).category);
  } catch {
    return false;
  }
}

export function getUndergroundCollectionPreparation(resourceName, count, observedTargetY = null) {
  try {
    const definition = getResourceDefinition(resourceName);
    const targetY = definition.targetY ?? (definition.category === 'common_underground'
      && Number.isFinite(observedTargetY) ? Math.floor(observedTargetY) + 2 : null);
    if (!isUndergroundCategory(definition.category) || !Number.isFinite(targetY)) {
      return null;
    }
    return {
      targetY,
      minimumCobblestone: definition.drops.includes('cobblestone')
        ? Math.max(0, Number(count) || 0)
        : 0,
    };
  } catch {
    return null;
  }
}

export function shouldPrepareUndergroundCollection(
  resourceName,
  count,
  currentY,
  hasNearbyTarget,
  observedTargetY = null,
) {
  if (hasNearbyTarget) return null;
  const preparation = getUndergroundCollectionPreparation(resourceName, count, observedTargetY);
  if (!preparation || Math.floor(currentY) <= preparation.targetY) return null;
  return preparation;
}

export function collectionDigTimeoutMs(bot, block) {
  const duration = bot.digTime?.(block);
  return Number.isFinite(duration)
    ? Math.min(120_000, Math.max(10_000, Math.ceil(duration * 1.5 + 2_000)))
    : 10_000;
}

export function blockHasWaterNeighbor(bot, position) {
  if (typeof bot?.blockAt !== 'function' || !position) return false;
  return NEIGHBOR_OFFSETS.some(([dx, dy, dz]) => (
    isWaterBlock(bot.blockAt(offsetPosition(position, dx, dy, dz)))
  ));
}

// Obsidian digs are refused when the target is the bot's own support block, or
// when adjacent/underlying lava has no verified water contact that would cool
// the exposed flow. Holding a bucket alone never authorizes the dig.
export function obsidianDigSafety(bot, block) {
  const target = block?.position;
  if (!target) return { safe: false, reason_code: 'TARGET_NOT_OBSERVED' };
  const entityPosition = bot?.entity?.position;
  if (entityPosition) {
    const feet = {
      x: Math.floor(Number(entityPosition.x)),
      y: Math.floor(Number(entityPosition.y)),
      z: Math.floor(Number(entityPosition.z)),
    };
    if (feet.x === target.x && feet.z === target.z && target.y === feet.y - 1) {
      return { safe: false, reason_code: 'SUPPORT_BLOCK_UNDER_FEET' };
    }
  }
  if (typeof bot?.blockAt !== 'function') return { safe: false, reason_code: 'REGION_NOT_LOADED' };
  const hazards = [];
  const targetCooledByWater = blockHasWaterNeighbor(bot, target);
  for (const [dx, dy, dz] of NEIGHBOR_OFFSETS) {
    const neighborPosition = offsetPosition(target, dx, dy, dz);
    const neighbor = bot.blockAt(neighborPosition);
    if (!neighbor) return { safe: false, reason_code: 'REGION_NOT_LOADED' };
    if (!isLavaBlock(neighbor)) continue;
    if (targetCooledByWater || blockHasWaterNeighbor(bot, neighborPosition)) continue;
    hazards.push({
      position: {
        x: neighborPosition.x,
        y: neighborPosition.y,
        z: neighborPosition.z,
      },
      relation: dy === -1 ? 'below' : dy === 1 ? 'above' : 'adjacent',
    });
  }
  if (hazards.length > 0) {
    return { safe: false, reason_code: 'UNPROTECTED_LAVA', hazards };
  }
  return { safe: true };
}

export function assertObsidianDigSafety(bot, block) {
  const safety = obsidianDigSafety(bot, block);
  if (safety.safe) return safety;
  const error = new Error(`拒绝不安全的黑曜石采掘：${safety.reason_code}`);
  error.code = 'UNSAFE_AREA';
  error.reason_code = safety.reason_code;
  error.details = { hazards: safety.hazards || [] };
  throw error;
}

export function isPreparedObsidianTarget(bot, block, minimumY = Number.NEGATIVE_INFINITY) {
  const above = block?.position && bot.blockAt(block.position.offset(0, 1, 0));
  return Boolean(block?.position) && block.position.y + 1 >= minimumY
    && (isAirLikeForStanding(above) || isWaterBlock(above))
    && obsidianDigSafety(bot, block).safe;
}

export function isNaturallySafeObsidianTarget(bot, block) {
  return block?.name === 'obsidian' && isPreparedObsidianTarget(bot, block)
    && NEIGHBOR_OFFSETS.every(([dx, dy, dz]) => (
      !isLavaBlock(bot.blockAt(offsetPosition(block.position, dx, dy, dz)))
    ));
}

export function obsidianWorkMinimumY(bot, targets) {
  const currentY = Math.floor(bot.entity.position.y);
  const surfaces = targets.map(position => position.offset(0, 1, 0)).filter(position => (
    position.y >= currentY - 1 && position.y <= currentY
    && isSafeStandingPosition(bot, position)
  ));
  return surfaces.length ? Math.max(...surfaces.map(position => position.y)) : currentY;
}

export function collectionDigSafety(bot, block) {
  if (block?.name === 'obsidian') return obsidianDigSafety(bot, block);
  if (!block?.position || typeof bot.blockAt !== 'function') {
    return { safe: false, reason_code: 'REGION_NOT_LOADED' };
  }
  for (const [dx, dy, dz] of NEIGHBOR_OFFSETS) {
    const neighbor = bot.blockAt(offsetPosition(block.position, dx, dy, dz));
    if (!neighbor || isLavaBlock(neighbor) || isWaterBlock(neighbor)) {
      return { safe: false, reason_code: 'FLUID_BREACH', block: neighbor?.name ?? 'unknown' };
    }
  }
  return { safe: true };
}

export function assertSafeDigTarget(bot, block) {
  const safety = collectionDigSafety(bot, block);
  if (!safety.safe) throw Object.assign(new Error('目标挖开后可能暴露水层、岩浆或失去安全支撑。'), {
    code: 'UNSAFE_AREA', reason_code: safety.reason_code, details: safety,
  });
}

export async function digCollectionBlock(bot, block, timeoutMs) {
  let digTarget = block;
  if (block.name === 'obsidian') {
    const minimumTool = getResourceDefinition('obsidian').requiredTool;
    const items = bot.inventory?.items?.() || [];
    const item = ['netherite_pickaxe', minimumTool]
      .map((name) => items.find((candidate) => candidate.name === name))
      .find(Boolean);
    if (!item) {
      throw Object.assign(new Error('采集黑曜石需要钻石镐或更好的镐。'), {
        code: 'TOOL_REQUIRED',
      });
    }
    assertObsidianDigSafety(bot, block);
    if (bot.heldItem?.name !== item.name) await bot.equip(item, 'hand');
    // Some 1.21 registries use a harvest restriction tag as obsidian's material,
    // losing the pickaxe speed table. Correct only this dig instance.
    if (block.material?.startsWith('incorrect_for_')
      && bot.registry?.materials?.['mineable/pickaxe']?.[item.type]) {
      digTarget = Object.assign(Object.create(Object.getPrototypeOf(block)), block, {
        material: 'mineable/pickaxe',
      });
    }
  } else assertSafeDigTarget(bot, block);
  const digTimeoutMs = timeoutMs ?? collectionDigTimeoutMs(bot, digTarget);
  const digContext = {
    expected_duration_ms: bot.digTime?.(digTarget) ?? null,
    timeout_ms: digTimeoutMs,
    held_item: bot.heldItem?.name ?? null,
    on_ground: bot.entity?.onGround ?? null,
    eye_block: bot._getBlockAtEyeLevel?.()?.name ?? null,
    effects: Object.values(bot.entity?.effects ?? {}).map(({ id, amplifier, duration }) => ({
      id, amplifier, duration,
    })),
    ...(digTarget !== block ? { original_material: block.material, effective_material: digTarget.material } : {}),
  };
  if (process.env.COLLECT_DEBUG) console.error(`[collect-debug] dig context=${JSON.stringify(digContext)}`);
  try {
    return await withTimeout(
      () => bot.dig(digTarget),
      digTimeoutMs,
      `collect dig ${block.name}@${block.position.x},${block.position.y},${block.position.z}`,
      () => bot.stopDigging?.(),
    );
  } catch (error) {
    error.details = {
      ...error.details,
      dig_context: {
        ...digContext,
        target_after: bot.blockAt?.(block.position)?.name ?? null,
      },
    };
    if (String(error?.message || '').includes('timed out')) {
      error.code = 'COLLECT_FAILED';
      error.operation = 'dig';
    }
    throw error;
  }
}

export function findPickupItemEntities(bot, radius = 20, itemName = null) {
  const items = [];
  const acceptedNames = itemName ? new Set((Array.isArray(itemName) ? itemName : [itemName])
    .map(name => name.replace(/^minecraft:/, ''))) : null;
  const selfPosition = bot?.entity?.position;
  for (const entity of Object.values(bot?.entities ?? {})) {
    if (!entity || entity.name !== 'item' || !entity.position || !selfPosition) continue;
    if (acceptedNames) {
      try {
        if (!acceptedNames.has(entity.getDroppedItem?.()?.name)) continue;
      } catch { continue; }
    }
    const distance = positionDistance(selfPosition, entity.position);
    if (distance <= radius) items.push({ entity, distance });
  }
  return items.sort((left, right) => left.distance - right.distance);
}

export function pickupStandingPosition(
  bot,
  itemPosition,
  { maxRadius = 2, upRange = 1, downRange = 1, minimumY = Number.NEGATIVE_INFINITY } = {},
) {
  const base = flooredPosition(itemPosition);
  if (base.y >= minimumY && isSafeStandingPosition(bot, base)) return base;
  return nearestSafeStandingPosition(bot, {
    origin: base,
    maxRadius,
    upRange,
    downRange,
    nearestTo: itemPosition,
    minimumY,
  });
}

// Drops are only approached through pathfinder goals that end on a spot with
// solid support and headroom. A failed path is never replaced by blind manual
// forward motion, and movement states are always restored in `finally`.
export async function safePickupDroppedItems(bot, {
  timeoutMs = 8_000,
  fallbackPos = null,
  maxNavigations = 8,
  maxAttemptsPerEntity = 2,
  scanRadius = 20,
  itemName = null,
  nowMs = () => Date.now(),
  waitMs = operationWait,
  GoalNear = null,
  movements = null,
  minimumY = Number.NEGATIVE_INFINITY,
  context = {},
} = {}) {
  const outcome = {
    navigations: 0,
    navigations_succeeded: 0,
    path_failures: 0,
    unsafe_targets_skipped: 0,
  };
  if (typeof GoalNear !== 'function' || typeof bot?.pathfinder?.goto !== 'function') {
    // Without pathfinding there is no safe way to approach drops.
    stopCollectionMovement(bot);
    return outcome;
  }
  context.operation_scope?.checkpoint();
  const deadline = nowMs() + Math.max(0, timeoutMs);
  const attemptsByEntity = new Map();
  let triedFallbackPosition = false;
  let previousMovements;
  if (movements && typeof bot.pathfinder.setMovements === 'function') {
    if (Number.isFinite(minimumY)) restrictNavigationHeight(movements, minimumY);
    previousMovements = bot.pathfinder.movements ?? null;
    bot.pathfinder.setMovements(movements);
  }
  const markAttempt = (entity) => {
    const attempts = (attemptsByEntity.get(entity) || 0) + 1;
    attemptsByEntity.set(entity, attempts);
    return attempts;
  };
  const exhausted = (entity) => (attemptsByEntity.get(entity) || 0) >= maxAttemptsPerEntity;
  try {
    while (nowMs() < deadline && outcome.navigations < maxNavigations) {
      context.operation_scope?.checkpoint();
      const [nearest] = findPickupItemEntities(bot, scanRadius, itemName)
        .filter(({ entity }) => !exhausted(entity));
      let goalPosition = null;
      let trackedEntity = null;
      if (nearest) {
        trackedEntity = nearest.entity;
        goalPosition = pickupStandingPosition(bot, trackedEntity.position, { minimumY });
        if (!goalPosition) {
          // The drop has no safe standing spot nearby; skip it permanently.
          attemptsByEntity.set(trackedEntity, maxAttemptsPerEntity);
          outcome.unsafe_targets_skipped += 1;
          continue;
        }
      } else if (fallbackPos && !triedFallbackPosition) {
        triedFallbackPosition = true;
        goalPosition = nearestSafeStandingPosition(bot, {
          origin: flooredPosition(fallbackPos),
          maxRadius: 2,
          upRange: 1,
          downRange: 2,
          nearestTo: fallbackPos,
          minimumY,
        });
        if (!goalPosition) outcome.unsafe_targets_skipped += 1;
      }
      if (!goalPosition) {
        if (!nearest && (triedFallbackPosition || !fallbackPos)) break;
        await waitMs(250);
        continue;
      }
      outcome.navigations += 1;
      try {
        await withTimeout(
          () => bot.pathfinder.goto(new GoalNear(goalPosition.x, goalPosition.y, goalPosition.z, 0)),
          Math.max(1, deadline - nowMs()),
          'safe drop pickup',
          () => bot.pathfinder.stop?.(),
        );
        outcome.navigations_succeeded += 1;
        // Waterborne drops can take time to rise into pickup range. Reaching
        // a safe edge alone does not prove that the item has been collected.
        for (let sample = 0; sample < 40 && nowMs() < deadline && trackedEntity
          && Object.values(bot.entities ?? {}).includes(trackedEntity); sample++) {
          context.operation_scope?.checkpoint();
          await waitMs(Math.min(100, Math.max(0, deadline - nowMs())));
        }
      } catch (error) {
        context.signal?.throwIfAborted();
        context.operation_scope?.checkpoint();
        outcome.path_failures += 1;
        // A failed path is never replaced by blind manual movement.
      } finally {
        try { bot.pathfinder.stop?.(); } catch {}
        if (trackedEntity) markAttempt(trackedEntity);
      }
      await waitMs(200);
    }
  } finally {
    if (movements && typeof bot.pathfinder.setMovements === 'function') {
      try { bot.pathfinder.setMovements(previousMovements); } catch {}
    }
    stopCollectionMovement(bot);
  }
  return outcome;
}

export function incompleteCollectionError(blockType, dropItem, collected, requested, diagnostics = {}) {
  if (collected === 0) {
    const error = new Error(`No reachable ${blockType} found within the bounded search`);
    error.code = 'RESOURCE_NOT_FOUND';
    error.collected = 0;
    error.requested = requested;
    error.resource = blockType;
    error.details = diagnostics;
    return error;
  }
  const error = new Error(
    `Collected ${collected}/${requested} ${blockType}; drops were not fully picked up`,
  );
  error.code = 'PARTIAL_COLLECT';
  error.collected = collected;
  error.requested = requested;
  error.reason = `inventory gained ${collected} ${dropItem}`;
  error.details = diagnostics;
  return error;
}

export async function withCollectionEvidence(bot, collect) {
  const resourceMutations = [];
  let previousPosition = { ...bot.entity.position };
  let previousHealth = bot.health;
  let travel = 0;
  let damage = 0;
  const onMove = () => {
    const current = bot.entity.position;
    travel += Math.hypot(
      current.x - previousPosition.x,
      current.y - previousPosition.y,
      current.z - previousPosition.z,
    );
    previousPosition = { ...current };
  };
  const onHealth = () => {
    damage += Math.max(0, previousHealth - bot.health);
    previousHealth = bot.health;
  };
  const evidence = () => ({
    explained_mutations: resourceMutations,
    budget_usage: {
      max_actions: 1,
      max_travel_distance: travel,
      max_blocks_changed: resourceMutations.length,
      max_damage_taken: damage,
    },
  });
  bot.on('move', onMove);
  bot.on('health', onHealth);
  try {
    const output = await collect(resourceMutations);
    onMove();
    onHealth();
    return { output, ...evidence() };
  } catch (error) {
    onMove();
    onHealth();
    Object.assign(error, evidence());
    throw error;
  } finally {
    bot.removeListener('move', onMove);
    bot.removeListener('health', onHealth);
  }
}
