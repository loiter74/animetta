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
import { isFullCubeReference, placementMutation } from './placement.js';
import { configureMineSupport } from './branch_mine.js';
import { iteratePathSearch, navigateTo } from './navigation.js';
import { restoreObsidianWorkSurface } from './obsidianSupport.js';
import { OperationScopeError, operationWait } from './runtime/operationScope.js';
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

// Vanilla 1.21 also clips item use against decorative plants (shoreline
// short_grass, lily pads) even though the SDK exposes no collision shape for
// them, leaving the raycast below structurally blind to doomed sight lines
// (probe-verified on a live server: bucket fills failed whenever the line
// crossed such a cell below plant-relative height 0.75 and succeeded at or
// above it). Walk the exact cells the sight line passes through and require
// that clearance in every non-air, non-water cell; water cells are skipped
// because scooping any source along the line still fills the bucket, and
// zero-width corner grazes are skipped because the live server lets them
// pass (boundary-touch semantics, also probe-verified).
const DECORATIVE_CLEARANCE = 0.75;

function hasDecorativeClearance(bot, eye, delta, targetCell) {
  const distance = delta.norm();
  if (distance === 0) return true;
  const direction = delta.scaled(1 / distance);
  // Collect every parameter where the line crosses an integer grid plane;
  // between consecutive crossings the line stays inside one cell.
  const cuts = [0, distance];
  for (const axis of ['x', 'y', 'z']) {
    if (Math.abs(direction[axis]) < 1e-12) continue;
    const near = Math.min(eye[axis], eye[axis] + direction[axis] * distance);
    const far = Math.max(eye[axis], eye[axis] + direction[axis] * distance);
    for (let bound = Math.floor(near); bound <= Math.floor(far); bound++) {
      const cut = (bound - eye[axis]) / direction[axis];
      if (cut > 0 && cut < distance) cuts.push(cut);
    }
  }
  cuts.sort((a, b) => a - b);
  for (let index = 0; index + 1 < cuts.length; index++) {
    const enter = cuts[index];
    const exit = cuts[index + 1];
    if (exit - enter < 1e-9) continue;
    const cell = eye.plus(direction.scaled((enter + exit) / 2)).floored();
    if (cell.equals(targetCell)) continue;
    const block = bot.blockAt(cell);
    if (!block || block.name === 'air' || isWaterBlock(block)) continue;
    const low = Math.min(eye.y + direction.y * enter, eye.y + direction.y * exit);
    if (low - cell.y < DECORATIVE_CLEARANCE) return false;
  }
  return true;
}

function canInteractFrom(bot, position, interactionTarget, feet, expectedFace) {
  const target = interactionTarget ?? position.offset(0.5, 0.5, 0.5);
  const eye = feet.offset(0, 1.62, 0);
  const delta = target.minus(eye);
  if (delta.norm() > 4.25) return false;
  if (!interactionTarget) return true;
  const hit = bot.world.raycast(eye, delta.scaled(1 / delta.norm()), delta.norm());
  const visible = hit ? hit.position.equals(position) && (expectedFace === undefined || hit.face === expectedFace)
    : expectedFace === undefined;
  return visible && hasDecorativeClearance(bot, eye, delta, position);
}

function standingCandidates(bot, position, interactionTarget, expectedFace) {
  const candidates = [];
  for (let dx = -3; dx <= 3; dx++) {
    for (let dz = -3; dz <= 3; dz++) {
      for (let dy = -1; dy <= 2; dy++) {
        const feet = position.offset(dx, dy, dz);
        if (isSafeStandingPosition(bot, feet)
          && canInteractFrom(bot, position, interactionTarget, feet.offset(0.5, 0, 0.5), expectedFace)) candidates.push(feet);
      }
    }
  }
  candidates.sort((a, b) => bot.entity.position.distanceTo(a) - bot.entity.position.distanceTo(b));
  return candidates.slice(0, 4);
}

async function approachObsidian(bot, position, context, {
  interactionTarget = null, expectedFace, allowDig = true,
} = {}) {
  const inReach = () => canInteractFrom(bot, position, interactionTarget, bot.entity.position, expectedFace);
  if (inReach() && isSafeStandingPosition(bot, bot.entity.position.floored())) return;
  const candidates = standingCandidates(bot, position, interactionTarget, expectedFace);
  const previous = bot.pathfinder.movements;
  const movements = new Movements(bot);
  configureDryNavigation(movements, bot);
  movements.canDig = allowDig;
  if (!allowDig) movements.scafoldingBlocks = [];
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
    const planner = iteratePathSearch(bot, movements, goal);
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

const BASIN_SIDES = [
  { x: 1, z: 0, face: 4 }, { x: -1, z: 0, face: 5 },
  { x: 0, z: 1, face: 2 }, { x: 0, z: -1, face: 3 },
];
const isLavaSource = block => block?.name === 'lava'
  && Number(block.getProperties?.().level ?? block.metadata) === 0;
const castingAir = block => ['air', 'cave_air'].includes(block?.name);

function closedLavaBasin(bot, start, maximum, origin) {
  const cells = new Map(), pending = [start];
  while (pending.length) {
    const p = pending.pop(), key = p.toString();
    if (cells.has(key)) continue;
    if (cells.size >= maximum || p.distanceTo(origin) > 64
      || !isLavaSource(bot.blockAt(p))
      || !isFullCubeReference(bot.blockAt(p.offset(0, -1, 0)))
      || !castingAir(bot.blockAt(p.offset(0, 1, 0)))) return null;
    cells.set(key, p);
    for (const side of BASIN_SIDES) {
      const adjacent = p.offset(side.x, 0, side.z);
      const boundary = bot.blockAt(adjacent.offset(0, 1, 0));
      if (isFullCubeReference(boundary)) continue;
      // Known full walls and floors contain the whole water reaction. An open,
      // flowing or unloaded boundary cannot support a bounded conversion proof.
      if (!castingAir(boundary) || !isLavaSource(bot.blockAt(adjacent))) return null;
      pending.push(adjacent);
    }
  }
  return [...cells.values()];
}

async function castObservedObsidian(bot, context, mutations, wait) {
  if (!hasItem(bot, 'water_bucket')) fail('TOOL_REQUIRED', '制备黑曜石前需要装满的水桶。');
  const maximum = context.budget?.max_blocks_changed;
  if (!Number.isSafeInteger(maximum) || maximum < 2) fail('BUDGET_EXHAUSTED', '剩余方块额度不足以制备黑曜石。');
  const lavaId = bot.registry.blocksByName.lava?.id;
  if (lavaId === undefined) fail('RESOURCE_NOT_FOUND', '附近没有可制备黑曜石的已知熔岩源。');
  const origin = bot.entity.position.clone();
  const sources = bot.findBlocks({ matching: lavaId, maxDistance: 64, count: 64 });
  const seen = new Set(), basins = [];
  for (const source of sources) {
    if (seen.has(source.toString())) continue;
    const basin = closedLavaBasin(bot, source, maximum - 1, origin);
    if (!basin) continue;
    for (const p of basin) seen.add(p.toString());
    basins.push(basin);
  }
  basins.sort((a, b) => b.length - a.length || a[0].distanceTo(origin) - b[0].distanceTo(origin));
  const selected = [];
  let remaining = maximum;
  for (const basin of basins) {
    const cost = basin.length + 1 + (selected.length ? 1 : 0);
    if (cost > remaining) continue;
    selected.push(basin); remaining -= cost;
  }
  if (!selected.length) fail('RESOURCE_NOT_FOUND', '原范围和预算内没有已知封闭、可安全制备的熔岩盆地。');
  const confirmation = waterConfirmation(context, wait), created = new Map();
  let lastWater;
  for (let index = 0; index < selected.length; index++) {
    confirmation.checkpoint();
    const basin = selected[index];
    const options = basin.flatMap(p => BASIN_SIDES.flatMap(side => {
      const water = p.offset(0, 1, 0), reference = water.offset(side.x, 0, side.z);
      if (!isFullCubeReference(bot.blockAt(reference))) return [];
      return [{ water, reference, face: side.face,
        target: reference.offset(.5 - side.x * (.5 - .01), .5, .5 - side.z * (.5 - .01)),
        span: Math.max(...basin.map(cell => Math.abs(cell.x - p.x) + Math.abs(cell.z - p.z))) }];
    })).sort((a, b) => a.span - b.span || a.water.distanceTo(bot.entity.position) - b.water.distanceTo(bot.entity.position));
    const placement = options.find(option => standingCandidates(bot, option.reference, option.target, option.face).length);
    if (!placement) fail('WATER_TARGET_UNREACHABLE', '封闭熔岩盆地没有可安全瞄准的放水面。');
    await approachObsidian(bot, placement.reference, context, {
      interactionTarget: placement.target, expectedFace: placement.face, allowDig: false,
    });
    const keys = new Set(basin.map(p => p.toString()));
    let placed = false, recovered = false, retrieving = false, activated = false, settled = false;
    const recordWater = () => {
      if (!placed) { mutations.push(placementMutation('water', placement.water, bot.game?.dimension)); placed = true; }
    };
    const recordPickup = () => {
      if (!recovered) { mutations.push(collectionResourceMutation('water', placement.water, bot.game?.dimension)); recovered = true; }
    };
    const recordObsidian = p => {
      if (created.has(p.toString())) return;
      created.set(p.toString(), p);
      mutations.push(placementMutation('obsidian', p, bot.game?.dimension));
    };
    const onUpdate = (before, after) => {
      if (!activated || !after?.position) return;
      if (keys.has(after.position.toString()) && before?.name === 'lava' && after.name === 'obsidian') recordObsidian(after.position);
      if (!after.position.equals(placement.water)) return;
      if (isWaterSource(after)) recordWater();
      else if (retrieving && isWaterSource(before)) recordPickup();
    };
    bot.on('blockUpdate', onUpdate);
    try {
      await bot.equip(hasItem(bot, 'water_bucket'), 'hand');
      await aimWaterItem(bot, placement.target, confirmation);
      const live = closedLavaBasin(bot, basin[0], maximum - 1, origin);
      if (!live || live.length !== basin.length || !live.every(p => basin.some(cell => cell.equals(p)))) {
        fail('TARGET_CHANGED', '放水前熔岩盆地或封闭边界发生变化。');
      }
      if (!canInteractFrom(bot, placement.reference, placement.target, bot.entity.position, placement.face)
        || !castingAir(bot.blockAt(placement.water))) fail('TARGET_CHANGED', '使用水桶前放水面已失效。');
      activated = true;
      bot.activateItem();
      try {
        if (!await confirmation.until(() => isWaterSource(bot.blockAt(placement.water))
          && basin.every(p => bot.blockAt(p)?.name === 'obsidian'))) {
          fail('WATER_PLACEMENT_UNCONFIRMED', '原等待额度内没有确认封闭盆地完成黑曜石转化。');
        }
      } finally { bot.deactivateItem?.(); }
      recordWater();
      for (const p of basin) recordObsidian(p);
      if (index + 1 < selected.length) {
        const bucket = hasItem(bot, 'bucket');
        if (!bucket) fail('WATER_FILL_UNCONFIRMED', '回收水源前没有观察到空铁桶。');
        await bot.equip(bucket, 'hand');
        const target = waterFillTarget(placement.water);
        await aimWaterItem(bot, target, confirmation);
        if (!isWaterSource(bot.blockAt(placement.water))
          || !canInteractFrom(bot, placement.water, target, bot.entity.position)) fail('TARGET_CHANGED', '回收前水源或安全站位发生变化。');
        retrieving = true;
        bot.activateItem();
        try {
          if (!await confirmation.until(() => hasItem(bot, 'water_bucket') && !isWaterSource(bot.blockAt(placement.water)))) {
            fail('WATER_FILL_UNCONFIRMED', '原等待额度内没有确认水源回收。');
          }
        } finally { bot.deactivateItem?.(); }
        recordPickup();
      }
      settled = true;
      lastWater = placement.water;
    } catch (error) {
      if (activated && !settled) throw new OperationScopeError('ACTION_SETTLEMENT_TIMEOUT',
        '放水后的转化或回收结果尚未确认，已禁止重放并保留实际消耗。', { cause_code: error.code ?? null });
      throw error;
    } finally {
      bot.removeListener('blockUpdate', onUpdate);
      if (activated) {
        for (const p of basin) if (bot.blockAt(p)?.name === 'obsidian') recordObsidian(p);
        if (isWaterSource(bot.blockAt(placement.water))) recordWater();
        else if (retrieving && placed) recordPickup();
      }
    }
  }
  return { position: lastWater.offset(0, -1, 0), created: [...created.values()] };
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
    let position = usable.find(p => isWaterBlock(bot.blockAt(p.offset(0, 1, 0))))
      ?? usable.find(p => isNaturallySafeObsidianTarget(bot, bot.blockAt(p))) ?? usable[0];
    let created = [];
    if (!position) {
      const prepared = await castObservedObsidian(bot, context, mutations, wait);
      position = prepared.position;
      created = prepared.created;
    }
    await approachObsidian(bot, position, context, { allowDig: !created.length });
    const reference = bot.blockAt(position);
    const above = position.offset(0, 1, 0);
    if (reference?.name !== 'obsidian') fail('TARGET_CHANGED', '放水前黑曜石目标发生变化。');
    if (!isWaterBlock(bot.blockAt(above))) {
      if (isNaturallySafeObsidianTarget(bot, reference)) {
        await restoreObsidianWorkSurface(bot, context, mutations);
        return { protected: true, natural_support: true, water_position: null,
          ...(created.length ? { created_obsidian: created } : {}) };
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
    return { protected: true, water_position: above,
      ...(created.length ? { created_obsidian: created } : {}) };
  });
}
