import pathfinderPkg from 'mineflayer-pathfinder';
import {
  collectionResourceMutation,
  collectionDigSafety,
  configureDryNavigation,
  isAirLikeForStanding,
  isNaturallySafeObsidianTarget,
  isSafeStandingPosition,
  isWaterBlock,
  stopCollectionMovement,
  withCollectionEvidence,
} from './collection.js';
import { placementMutation } from './placement.js';
import { configureMineSupport } from './branch_mine.js';
import { navigateTo } from './navigation.js';
import { restoreObsidianWorkSurface } from './obsidianSupport.js';
import { operationWait } from './runtime/operationScope.js';

const { Movements, goals: { GoalBlock } } = pathfinderPkg;

function fail(code, message, details = {}) { throw Object.assign(new Error(message), { code, details }); }
const hasItem = (bot, name) => bot.inventory.items().find(item => item.name === name && item.count > 0);

export function isWaterSource(block) {
  if (!isWaterBlock(block)) return false;
  return Number(block.getProperties?.().level ?? block.metadata) === 0;
}

// Exposed level-zero water occupies 8/9 of the block, unlike a solid top face.
const waterFillTarget = position => position.offset(0.5, 8 / 9 - 0.01, 0.5);

async function confirm(context, predicate, wait = operationWait) {
  for (let attempt = 0; attempt < 30; attempt++) {
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
    if (predicate()) return true;
    await wait(100);
  }
  return false;
}

async function approach(bot, position, context, { excavate = false, interactionTarget = null } = {}) {
  const target = interactionTarget ?? position.offset(0.5, 0.5, 0.5);
  const inReachFrom = feet => {
    const eye = feet.offset(0, 1.62, 0);
    const delta = target.minus(eye);
    if (delta.norm() > 4.25) return false;
    if (!interactionTarget) return true;
    const hit = bot.world.raycast(eye, delta.scaled(1 / delta.norm()), delta.norm());
    return !hit || hit.position.equals(position);
  };
  const inReach = () => inReachFrom(bot.entity.position);
  if (inReach() && isSafeStandingPosition(bot, bot.entity.position.floored())) return;
  const candidates = [];
  for (let dx = -3; dx <= 3; dx++) {
    for (let dz = -3; dz <= 3; dz++) {
      for (let dy = -1; dy <= 2; dy++) {
        const feet = position.offset(dx, dy, dz);
        if (isSafeStandingPosition(bot, feet)
          && inReachFrom(feet.offset(0.5, 0, 0.5))) candidates.push(feet);
      }
    }
  }
  candidates.sort((a, b) => bot.entity.position.distanceTo(a) - bot.entity.position.distanceTo(b));
  const previous = bot.pathfinder.movements;
  const movements = new Movements(bot);
  configureDryNavigation(movements, bot);
  movements.canDig = excavate;
  movements.allow1by1towers = false;
  if (excavate) {
    configureMineSupport(movements, bot.registry);
    movements.blocksCantBreak.add(bot.registry.blocksByName.obsidian.id);
    movements.exclusionAreasBreak.push(block => collectionDigSafety(bot, block).safe ? 0 : Infinity);
  } else {
    movements.scafoldingBlocks = [];
  }
  bot.pathfinder.setMovements(movements);
  try {
    for (const feet of candidates.slice(0, 4)) {
      context.operation_scope?.checkpoint();
      try {
        if (excavate) await navigateTo(bot, feet, context);
        else await bot.pathfinder.goto(new GoalBlock(feet.x, feet.y, feet.z));
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
    let source;
    for (const candidate of sources.slice(0, 16)) {
      try {
        await approach(bot, candidate.position, context, {
          interactionTarget: waterFillTarget(candidate.position),
        });
        source = candidate;
        break;
      } catch (error) {
        if (error.code !== 'WATER_TARGET_UNREACHABLE') throw error;
      }
    }
    if (!source) fail('WATER_TARGET_UNREACHABLE', '有限次水源检查没有找到安全岸边站位。');
    if (!isWaterSource(bot.blockAt(source.position))) fail('WATER_SOURCE_CHANGED', '装水前水源发生变化。');
    await bot.equip(bucket, 'hand');
    const target = waterFillTarget(source.position);
    await bot.lookAt(target, false);
    context.operation_scope?.checkpoint();
    const interactionAtUse = {
      eye_height: bot.entity.eyeHeight ?? null, yaw: bot.entity.yaw ?? null, pitch: bot.entity.pitch ?? null,
      held_item: bot.heldItem?.name ?? null, expected_bucket_slot: bucket.slot ?? null,
      live_bucket_slot: hasItem(bot, 'bucket')?.slot ?? null,
    };
    bot.activateItem();
    try {
      if (!await confirm(context, () => hasItem(bot, 'water_bucket'), wait)) {
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
    await approach(bot, position, context, { excavate: true });
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
      await bot.lookAt(position.offset(0.5, 0.99, 0.5), false);
      context.operation_scope?.checkpoint();
      bot.activateItem();
      try {
        if (!await confirm(context, () => isWaterBlock(bot.blockAt(above)), wait)) {
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
