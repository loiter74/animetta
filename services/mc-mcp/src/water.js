import pathfinderPkg from 'mineflayer-pathfinder';
import Vec3 from 'vec3';
import {
  collectionResourceMutation,
  collectionDigSafety,
  configureDryNavigation,
  isAirLikeForStanding,
  isNaturallySafeObsidianTarget,
  isSafeStandingPosition,
  isWaterBlock,
  stopCollectionMovement,
  waitForCollectionMovementToSettle,
  withCollectionEvidence,
} from './collection.js';
import { placementMutation } from './placement.js';
import { configureMineSupport } from './branch_mine.js';
import { navigateTo } from './navigation.js';
import { restoreObsidianWorkSurface } from './obsidianSupport.js';
import { operationWait } from './runtime/operationScope.js';
import { createMineShaft } from './mine_shaft.js';

const { Movements, goals: { GoalBlock, GoalCompositeAny } } = pathfinderPkg;
const MAX_WATER_SOURCES = 16;

function fail(code, message, details = {}) { throw Object.assign(new Error(message), { code, details }); }
const hasItem = (bot, name) => bot.inventory.items().find(item => item.name === name && item.count > 0);

export function isWaterSource(block) {
  if (!isWaterBlock(block)) return false;
  return Number(block.getProperties?.().level ?? block.metadata) === 0;
}

// Exposed level-zero water occupies 8/9 of the block, unlike a solid top face.
const waterFillTarget = position => position.offset(0.5, 8 / 9 - 0.01, 0.5);

function waterConfirmation(context, wait) {
  let remaining = 30;
  const checkpoint = () => {
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
  };
  const pause = async () => {
    checkpoint();
    if (!remaining) return false;
    remaining--;
    await wait(100);
    return true;
  };
  return { checkpoint, pause, until: async predicate => {
    do {
      checkpoint();
      if (predicate()) return true;
    } while (await pause());
    return false;
  } };
}

async function aimWaterItem(bot, target, confirmation) {
  confirmation.checkpoint();
  const settled = await waitForCollectionMovementToSettle(bot, {
    timeoutMs: 3000,
    waitMs: async () => {
      if (!await confirmation.pause()) fail('WATER_TARGET_UNREACHABLE', '原有等待额度内没有稳定到达取放水站位。');
    },
  });
  if (!settled) fail('WATER_TARGET_UNREACHABLE', '取放水前移动尚未稳定。');
  confirmation.checkpoint();
  const position = bot.entity.position.clone();
  const eyeHeight = bot.entity.eyeHeight ?? 1.62;
  let sent = false;
  const onMove = () => { sent = true; };
  bot.on('move', onMove);
  try {
    // Nonforced SDK look completion checks yaw alone. Force sets both pending
    // angles; move is emitted only after the next position/look packet is sent.
    await bot.lookAt(target, true);
    if (!await confirmation.until(() => sent)) fail('WATER_TARGET_UNREACHABLE', '原有等待额度内没有确认取放水朝向已发送。');
  } finally {
    bot.removeListener('move', onMove);
  }
  confirmation.checkpoint();
  const entity = bot.entity;
  const delta = target.minus(entity.position.offset(0, entity.eyeHeight ?? 1.62, 0));
  const direction = new Vec3(-Math.sin(entity.yaw) * Math.cos(entity.pitch),
    Math.sin(entity.pitch), -Math.cos(entity.yaw) * Math.cos(entity.pitch));
  if (entity.position.distanceTo(position) > 0.01 || (entity.eyeHeight ?? 1.62) !== eyeHeight
    || !isSafeStandingPosition(bot, entity.position.floored()) || entity.onGround === false
    || delta.norm() > 4.25 || !Number.isFinite(direction.dot(delta))
    || direction.dot(delta.scaled(1 / delta.norm())) < 1 - 0.00001) {
    fail('WATER_TARGET_UNREACHABLE', '发送朝向后站位或瞄准已变化，停止取放水。');
  }
}

function canInteractFrom(bot, position, interactionTarget, feet) {
  const target = interactionTarget ?? position.offset(0.5, 0.5, 0.5);
  const eye = feet.offset(0, 1.62, 0);
  const delta = target.minus(eye);
  if (delta.norm() > 4.25) return false;
  if (!interactionTarget) return true;
  const hit = bot.world.raycast(eye, delta.scaled(1 / delta.norm()), delta.norm());
  return !hit || hit.position.equals(position);
}

function standingCandidates(bot, position, interactionTarget) {
  const candidates = [];
  for (let dx = -3; dx <= 3; dx++) {
    for (let dz = -3; dz <= 3; dz++) {
      for (let dy = -1; dy <= 2; dy++) {
        const feet = position.offset(dx, dy, dz);
        if (isSafeStandingPosition(bot, feet)
          && canInteractFrom(bot, position, interactionTarget, feet.offset(0.5, 0, 0.5))) candidates.push(feet);
      }
    }
  }
  candidates.sort((a, b) => bot.entity.position.distanceTo(a) - bot.entity.position.distanceTo(b));
  return candidates.slice(0, 4);
}

async function approachObsidian(bot, position, context) {
  const inReach = () => canInteractFrom(bot, position, null, bot.entity.position);
  if (inReach() && isSafeStandingPosition(bot, bot.entity.position.floored())) return;
  const candidates = standingCandidates(bot, position, null);
  const previous = bot.pathfinder.movements;
  const movements = new Movements(bot);
  configureDryNavigation(movements, bot);
  movements.canDig = true;
  movements.allow1by1towers = false;
  configureMineSupport(movements, bot.registry);
  movements.blocksCantBreak.add(bot.registry.blocksByName.obsidian.id);
  movements.exclusionAreasBreak.push(block => collectionDigSafety(bot, block).safe ? 0 : Infinity);
  bot.pathfinder.setMovements(movements);
  try {
    for (const feet of candidates) {
      context.operation_scope?.checkpoint();
      try {
        await navigateTo(bot, feet, context);
        if (inReach() && isSafeStandingPosition(bot, bot.entity.position.floored())) return;
      } catch (error) {
        context.signal?.throwIfAborted();
        context.operation_scope?.checkpoint();
        if (!['NoPath', 'PathStopped', 'Timeout', 'NAVIGATION_TARGET_NOT_REACHED', 'ACTION_DEADLINE_EXPIRED'].includes(error.code || error.name)) throw error;
      }
    }
  } finally {
    stopCollectionMovement(bot);
    bot.pathfinder.setMovements(previous);
  }
  fail('WATER_TARGET_UNREACHABLE', '找不到有支撑且能安全接近目标的站位。');
}

function selectWaterSources(sources) {
  if (sources.length <= MAX_WATER_SOURCES) return sources;
  const selected = [sources[0]];
  const pending = sources.slice(1).map(source => ({
    source, nearestSquared: source.position.distanceSquared(sources[0].position),
  }));
  // Keep the nearest source, then cover the returned water rather than one bank.
  while (selected.length < MAX_WATER_SOURCES) {
    let best = 0;
    for (let i = 1; i < pending.length; i++) {
      if (pending[i].nearestSquared > pending[best].nearestSquared) best = i;
    }
    const [{ source }] = pending.splice(best, 1);
    selected.push(source);
    for (const candidate of pending) {
      candidate.nearestSquared = Math.min(candidate.nearestSquared,
        candidate.source.position.distanceSquared(source.position));
    }
  }
  return selected;
}

async function approachWaterSources(bot, sources, context, wait) {
  const reachableSource = pool => isSafeStandingPosition(bot, bot.entity.position.floored())
    ? pool.find(source => canInteractFrom(bot, source.position,
      waterFillTarget(source.position), bot.entity.position)) : undefined;
  const nearby = reachableSource(sources.slice(0, MAX_WATER_SOURCES));
  if (nearby) return nearby;
  const selected = selectWaterSources(sources);
  const candidates = new Map();
  for (const source of selected) {
    for (const feet of standingCandidates(bot, source.position, waterFillTarget(source.position))) {
      candidates.set(feet.toString(), new GoalBlock(feet.x, feet.y, feet.z));
    }
  }
  if (!candidates.size) fail('WATER_TARGET_UNREACHABLE', '有限次水源检查没有找到安全岸边站位。');
  const previous = bot.pathfinder.movements;
  const movements = configureDryNavigation(new Movements(bot), bot);
  movements.canDig = false;
  movements.allow1by1towers = false;
  movements.scafoldingBlocks = [];
  bot.pathfinder.setMovements(movements);
  try {
    // Plan within the SDK's existing search/time bounds before spending movement.
    // The native navigation still uses a single GoalBlock and its unchanged guards.
    const goal = new GoalCompositeAny([...candidates.values()]);
    const planner = bot.pathfinder.getPathFromTo(movements, bot.entity.position, goal);
    let result;
    for (const planned of planner) {
      context.operation_scope?.checkpoint();
      context.signal?.throwIfAborted();
      result = planned.result;
      if (result.status !== 'partial') break;
      await operationWait(1);
    }
    if (result?.status !== 'success') fail('WATER_TARGET_UNREACHABLE', '现有规划范围内没有找到通向安全岸边的完整路径。', {
      planning_status: result?.status ?? null, candidate_standings: candidates.size,
    });
    const end = result.path.at(-1) ?? bot.entity.position.floored();
    const target = candidates.get(new Vec3(Math.floor(end.x), Math.floor(end.y), Math.floor(end.z)).toString());
    if (!target) fail('WATER_TARGET_UNREACHABLE', '规划终点不是已核验的安全岸边站位。');
    await bot.pathfinder.goto(target);
    let source = reachableSource(selected);
    // GoalBlock admits a whole cell; the validated interaction used its center.
    // Reuse bounded in-cell alignment without another navigation or source scan.
    if (!source && target.isEnd(bot.entity.position.floored())) {
      const aligned = await createMineShaft({ bot, wait }).centerAboveSupport({
        tolerance: 0.05,
        checkpoint: () => {
          context.operation_scope?.checkpoint();
          context.signal?.throwIfAborted();
        },
      });
      if (aligned) source = reachableSource(selected);
    }
    if (source) return source;
    fail('WATER_TARGET_UNREACHABLE', '导航结束后没有到达可安全取水的岸边站位。');
  } finally {
    stopCollectionMovement(bot);
    bot.pathfinder.setMovements(previous);
  }
}

export async function fillWaterBucket(bot, context = {}, { wait = operationWait } = {}) {
  return withCollectionEvidence(bot, async mutations => {
    if (hasItem(bot, 'water_bucket')) return { filled: true, already_present: true };
    const bucket = hasItem(bot, 'bucket');
    if (!bucket) fail('TOOL_REQUIRED', '装水前需要先合成铁桶。');
    const scan = { search_radius: 64, candidate_limit: 512, source_checks: 0,
      check_scope: 'sdk_pre_radius_and_final_live_recheck',
      origin: bot.entity.position.floored(), samples: {},
      rejected_non_source: 0, rejected_covered: 0, rejected_unknown_above: 0 };
    const reject = (reason, block, above = null) => {
      scan[`rejected_${reason}`]++;
      // One sample per reason (at most three), never an unbounded voxel trace.
      if (!Object.hasOwn(scan.samples, reason)) {
        const level = block?.getProperties?.()?.level;
        scan.samples[reason] = { position: block?.position ?? null, state_id: block?.stateId ?? null,
          level: level ?? null, level_type: typeof level, metadata: block?.metadata ?? null,
          above_name: above?.name ?? null, above_bounding_box: above?.boundingBox ?? null };
      }
      return false;
    };
    const eligible = block => {
      scan.source_checks++;
      if (!isWaterSource(block)) return reject('non_source', block);
      const above = bot.blockAt(block.position.offset(0, 1, 0));
      if (!above) return reject('unknown_above', block);
      if (!isAirLikeForStanding(above)) return reject('covered', block, above);
      return true;
    };
    // Retain the palette's water-ID fast path, but reject unusable cells before
    // the SDK's chunk-layer early stop and candidate truncation can hide shores.
    const positions = bot.findBlocks({ matching: bot.registry.blocksByName.water.id,
      maxDistance: 64, count: 512, useExtraInfo: eligible });
    const sources = positions.map(position => bot.blockAt(position)).filter(eligible);
    if (!sources.length) fail('WATER_SOURCE_NOT_FOUND', '附近未观察到可以装取的静态水源。', {
      ...scan, returned_candidates: positions.length,
    });
    const source = await approachWaterSources(bot, sources, context, wait);
    await bot.equip(bucket, 'hand');
    const target = waterFillTarget(source.position);
    const confirmation = waterConfirmation(context, wait);
    await aimWaterItem(bot, target, confirmation);
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
    if (!isSafeStandingPosition(bot, bot.entity.position.floored())
      || !canInteractFrom(bot, source.position, target, bot.entity.position)) {
      fail('WATER_TARGET_UNREACHABLE', '使用铁桶前当前位置已不满足安全取水条件。');
    }
    if (!isWaterSource(bot.blockAt(source.position))) fail('WATER_SOURCE_CHANGED', '装水前水源发生变化。');
    const interactionAtUse = {
      eye_height: bot.entity.eyeHeight ?? null, yaw: bot.entity.yaw ?? null, pitch: bot.entity.pitch ?? null,
      held_item: bot.heldItem?.name ?? null, expected_bucket_slot: bucket.slot ?? null,
      live_bucket_slot: hasItem(bot, 'bucket')?.slot ?? null,
    };
    bot.activateItem();
    try {
      if (!await confirmation.until(() => hasItem(bot, 'water_bucket'))) {
        fail('WATER_FILL_UNCONFIRMED', '使用铁桶后背包没有出现水桶。', {
          source: source.position, target, position: bot.entity.position, interaction_at_use: interactionAtUse,
        });
      }
    } finally { bot.deactivateItem?.(); }
    mutations.push(collectionResourceMutation('water', source.position, bot.game?.dimension));
    return { filled: true, source: source.position };
  });
}

export async function prepareObsidian(bot, context = {}, { wait = operationWait } = {}) {
  return withCollectionEvidence(bot, async mutations => {
    const positions = bot.findBlocks({ matching: bot.registry.blocksByName.obsidian.id, maxDistance: 64, count: 64 });
    const feet = bot.entity.position.floored();
    const usable = positions.filter(p => {
      if (p.x === feet.x && p.z === feet.z && p.y === feet.y - 1) return false;
      const above = bot.blockAt(p.offset(0, 1, 0));
      return isWaterBlock(above) || ['air', 'cave_air'].includes(above?.name);
    });
    const position = usable.find(p => isWaterBlock(bot.blockAt(p.offset(0, 1, 0))))
      ?? usable.find(p => isNaturallySafeObsidianTarget(bot, bot.blockAt(p))) ?? usable[0];
    if (!position) fail('RESOURCE_NOT_FOUND', '附近没有可准备采集的黑曜石。');
    await approachObsidian(bot, position, context);
    const reference = bot.blockAt(position);
    const above = position.offset(0, 1, 0);
    if (reference?.name !== 'obsidian') fail('TARGET_CHANGED', '放水前黑曜石目标发生变化。');
    if (!isWaterBlock(bot.blockAt(above))) {
      if (isNaturallySafeObsidianTarget(bot, reference)) {
        await restoreObsidianWorkSurface(bot, context, mutations);
        return { protected: true, natural_support: true, water_position: null };
      }
      const bucket = hasItem(bot, 'water_bucket');
      if (!bucket) fail('TOOL_REQUIRED', '安全采集黑曜石前需要装满的水桶。');
      if (!['air', 'cave_air'].includes(bot.blockAt(above)?.name)) fail('UNSAFE_AREA', '黑曜石上方没有安全放水空间。');
      await bot.equip(bucket, 'hand');
      const confirmation = waterConfirmation(context, wait);
      await aimWaterItem(bot, position.offset(0.5, 0.99, 0.5), confirmation);
      context.operation_scope?.checkpoint();
      bot.activateItem();
      try {
        if (!await confirmation.until(() => isWaterBlock(bot.blockAt(above)))) {
          fail('WATER_PLACEMENT_UNCONFIRMED', '放水后没有观察到黑曜石上方的水。');
        }
      } finally { bot.deactivateItem?.(); }
      mutations.push(placementMutation('water', above, bot.game?.dimension));
    }
    // Give the flow time to cover the work area before any obsidian is removed.
    await wait(2000);
    if (!isWaterBlock(bot.blockAt(above))) fail('WATER_PROTECTION_LOST', '采矿前水流保护已消失。');
    await restoreObsidianWorkSurface(bot, context, mutations);
    return { protected: true, water_position: above };
  });
}
