import pathfinderPkg from 'mineflayer-pathfinder';
import Vec3 from 'vec3';
import {
  collectionResourceMutation,
  digCollectionBlock,
  isAirLikeForStanding,
  isSafeStandingPosition,
  stopCollectionMovement,
  withCollectionEvidence,
} from './collection.js';
import { findPlacementReference, placementMutation } from './placement.js';
import { navigateTo } from './navigation.js';
import { operationWait } from './runtime/operationScope.js';
import {
  aimWaterItem,
  approachWaterSources,
  canInteractFrom,
  isLavaSource,
  isWaterSource,
  standingCandidates,
  waterConfirmation,
} from './water.js';

const { Movements } = pathfinderPkg;

function fail(code, message, details = {}) {
  throw Object.assign(new Error(message), { code, details });
}

const hasItem = (bot, name) => bot.inventory.items().find(item => item.name === name && item.count > 0);

const isSolid = block => block && block.boundingBox === 'block' && block.name !== 'pointed_dripstone';

// Cells that can host poured fluid without digging (fluids replace them).
const TRENCH_REPLACEABLE = new Set(['air', 'cave_air', 'short_grass', 'fern', 'dead_bush', 'snow', 'water']);

// Common ground blocks the bot may carve a trench or farm shaft through.
const CARVABLE_GROUND = new Set([
  'dirt', 'grass_block', 'coarse_dirt', 'podzol', 'rooted_dirt', 'moss_block', 'clay',
  'stone', 'cobblestone', 'granite', 'diorite', 'andesite', 'tuff', 'calcite',
  'deepslate', 'cobbled_deepslate', 'sandstone', 'snow_block', 'dirt_path',
]);

const SOLID_BLOCK_OPTIONS = ['cobblestone', 'dirt'];
const SITE_SCAN_RADIUS = 6;
const NAVIGATION_ERROR_CODES = ['NoPath', 'PathStopped', 'Timeout', 'NAVIGATION_TARGET_NOT_REACHED',
  'SEARCH_TIMEOUT', 'ACTION_DEADLINE_EXPIRED'];

function dryMovementSet(bot) {
  const movements = new Movements(bot);
  movements.canDig = false;
  movements.allow1by1towers = false;
  movements.scafoldingBlocks = [];
  return movements;
}

// Navigate to a stance from which the bot can interact with (dig or pour onto)
// the target cell; digging itself is left to digCollectionBlock.
async function approachInteractionStance(bot, position, interactionTarget, context, options = {}) {
  const inReach = () => canInteractFrom(bot, position, interactionTarget, bot.entity.position)
    && isSafeStandingPosition(bot, bot.entity.position.floored());
  if (inReach()) return;
  const candidates = standingCandidates(bot, position, interactionTarget)
    .filter(feet => !(options.excludeDirectlyAbove
      && feet.x === position.x && feet.z === position.z && feet.y === position.y + 1));
  const previous = bot.pathfinder.movements;
  bot.pathfinder.setMovements(dryMovementSet(bot));
  try {
    for (const feet of candidates) {
      context.operation_scope?.checkpoint();
      context.signal?.throwIfAborted();
      try {
        await navigateTo(bot, feet, context);
        if (inReach()) return;
      } catch (error) {
        context.signal?.throwIfAborted();
        context.operation_scope?.checkpoint();
        if (!NAVIGATION_ERROR_CODES.includes(error.code || error.name)) throw error;
      }
    }
  } finally {
    stopCollectionMovement(bot);
    bot.pathfinder.setMovements(previous);
  }
  fail('WATER_TARGET_UNREACHABLE', '找不到有支撑且能安全接近目标的站位。', { position });
}

async function carveCell(bot, cell, context, mutations) {
  const block = bot.blockAt(cell);
  if (!block) fail('REGION_NOT_LOADED', '目标格所在区块尚未加载。', { position: cell });
  if (isAirLikeForStanding(block) || TRENCH_REPLACEABLE.has(block.name)) return;
  if (!CARVABLE_GROUND.has(block.name)) {
    fail('CARVE_TARGET_NOT_DIGGABLE', '目标格不是可安全开挖的常见地面方块。', { position: cell, block: block.name });
  }
  await approachInteractionStance(bot, cell, cell.offset(0.5, 0.5, 0.5), context, {
    excludeDirectlyAbove: true,
  });
  context.operation_scope?.checkpoint();
  context.signal?.throwIfAborted();
  const fresh = bot.blockAt(cell);
  if (!fresh || fresh.name !== block.name) {
    fail('CARVE_TARGET_CHANGED', '到达站位后目标格已发生变化。', { position: cell, expected: block.name });
  }
  await digCollectionBlock(bot, fresh);
  if (!isAirLikeForStanding(bot.blockAt(cell))) {
    fail('TRENCH_DIG_UNCONFIRMED', '挖除目标格后没有观察到空气。', { position: cell, block: block.name });
  }
  mutations.push(collectionResourceMutation(block.name, cell, bot.game?.dimension));
}

async function placeCellBlock(bot, cell, itemName, context, mutations) {
  const reference = findPlacementReference(bot, cell, Vec3);
  if (!reference) {
    fail('PLACEMENT_REFERENCE_NOT_FOUND', '目标格四周没有可借力的实心参照方块。', { position: cell, item: itemName });
  }
  const item = hasItem(bot, itemName);
  if (!item) fail('MISSING_MATERIAL', `放置 ${itemName} 前材料已耗尽。`, { position: cell, item: itemName });
  await bot.equip(item, 'hand');
  context.operation_scope?.checkpoint();
  context.signal?.throwIfAborted();
  await bot.placeBlock(reference.reference, reference.face);
  if (bot.blockAt(cell)?.name !== itemName) {
    fail('FARM_STRUCTURE_UNCONFIRMED', `放置 ${itemName} 后没有在目标格观察到该方块。`, { position: cell, item: itemName });
  }
  mutations.push(placementMutation(itemName, cell, bot.game?.dimension));
}

// Pour the currently held bucket fluid onto the top face of the floor below
// `cell`, then confirm the fluid landed as a level-zero source in `cell`.
async function pourFluidIntoCell(bot, cell, heldItemName, confirmation, context, mutations) {
  const floor = cell.offset(0, -1, 0);
  const target = floor.offset(0.5, 0.99, 0.5);
  await approachInteractionStance(bot, floor, target, context);
  const item = hasItem(bot, heldItemName);
  if (!item) fail('MISSING_MATERIAL', `倒出 ${heldItemName} 前物品已耗尽。`, { position: cell });
  await bot.equip(item, 'hand');
  await aimWaterItem(bot, target, confirmation);
  context.operation_scope?.checkpoint();
  context.signal?.throwIfAborted();
  if (!isSafeStandingPosition(bot, bot.entity.position.floored())
    || !canInteractFrom(bot, floor, target, bot.entity.position)) {
    fail('WATER_TARGET_UNREACHABLE', '倒出流体前当前位置已不满足安全浇灌条件。', { position: cell });
  }
  const isExpectedSource = () => (heldItemName === 'lava_bucket'
    ? isLavaSource(bot.blockAt(cell)) : isWaterSource(bot.blockAt(cell)));
  bot.activateItem();
  try {
    if (!await confirmation.until(isExpectedSource)) {
      fail('WATER_PLACEMENT_UNCONFIRMED', '倒出流体后没有在目标格观察到静态流体源。', { position: cell, target });
    }
  } finally {
    bot.deactivateItem?.();
  }
  mutations.push(placementMutation(heldItemName === 'lava_bucket' ? 'lava' : 'water', cell, bot.game?.dimension));
}

// Refill an empty bucket from a nearby natural water source without nesting
// another evidence scope.
async function ensureWaterBucket(bot, context, wait, mutations) {
  if (hasItem(bot, 'water_bucket')) return;
  const bucket = hasItem(bot, 'bucket');
  if (!bucket) fail('TOOL_REQUIRED', '建造水池前需要铁桶。');
  const waterId = bot.registry?.blocksByName?.water?.id;
  const positions = typeof bot.findBlocks === 'function' && waterId !== undefined
    ? bot.findBlocks({ matching: waterId, maxDistance: 32, count: 128 }) || []
    : [];
  const sources = positions.map(position => bot.blockAt(position)).filter(block => (
    isWaterSource(block) && isAirLikeForStanding(bot.blockAt(block.position.offset(0, 1, 0)))
  ));
  if (!sources.length) {
    fail('WATER_SOURCE_NOT_FOUND', '附近没有可以补水的静态水源。');
  }
  const source = await approachWaterSources(bot, sources, context, wait);
  const confirmation = waterConfirmation(context, wait);
  await bot.equip(bucket, 'hand');
  await aimWaterItem(bot, source.position.offset(0.5, 8 / 9 - 0.01, 0.5), confirmation);
  context.operation_scope?.checkpoint();
  context.signal?.throwIfAborted();
  bot.activateItem();
  try {
    if (!await confirmation.until(() => hasItem(bot, 'water_bucket'))) {
      fail('WATER_FILL_UNCONFIRMED', '补水后背包没有出现水桶。', { source: source.position });
    }
  } finally {
    bot.deactivateItem?.();
  }
  mutations.push(collectionResourceMutation('water', source.position, bot.game?.dimension));
}

function findExistingPool(bot, sources) {
  const byKey = new Map(sources.map(source => [source.position.toString(), source]));
  for (const a of sources) {
    for (const [b, c] of [[a.position.offset(0, 0, 1), a.position.offset(0, 0, 2)],
      [a.position.offset(1, 0, 0), a.position.offset(2, 0, 0)]]) {
      const blockB = byKey.get(b.toString());
      const blockC = byKey.get(c.toString());
      if (!blockB || !blockC) continue;
      const cells = [a.position, b, c];
      if (cells.every(cell => isSolid(bot.blockAt(cell.offset(0, -1, 0))))) {
        return { center: b, cells };
      }
    }
  }
  return null;
}

function selectTrenchSite(bot) {
  const origin = bot.entity.position.floored();
  const groundY = origin.y - 1;
  const candidates = [];
  for (const direction of [[1, 0], [0, 1]]) {
    const [dx, dz] = direction;
    for (let cx = -SITE_SCAN_RADIUS; cx <= SITE_SCAN_RADIUS; cx++) {
      for (let cz = -SITE_SCAN_RADIUS; cz <= SITE_SCAN_RADIUS; cz++) {
        const start = new Vec3(origin.x + cx, groundY, origin.z + cz);
        const cells = [start, start.offset(dx, 0, dz), start.offset(dx * 2, 0, dz * 2)];
        let needsDig = 0;
        let valid = true;
        for (const cell of cells) {
          const block = bot.blockAt(cell);
          if (!block || !bot.blockAt(cell.offset(0, -1, 0)) || !bot.blockAt(cell.offset(0, 1, 0))) {
            valid = false;
            break;
          }
          if (TRENCH_REPLACEABLE.has(block.name)) continue;
          if (CARVABLE_GROUND.has(block.name)) { needsDig++; continue; }
          valid = false;
          break;
        }
        if (!valid) continue;
        // Never carve away the bot's own support column; other sites exist.
        if (cells.some(cell => cell.x === origin.x && cell.z === origin.z && cell.y === groundY)) continue;
        const rim = [];
        for (const cell of cells) {
          rim.push(cell.offset(dz, 0, dx), cell.offset(-dz, 0, -dx));
        }
        rim.push(cells[0].offset(-dx, 0, -dz), cells[2].offset(dx, 0, dz));
        if (!rim.every(position => isSolid(bot.blockAt(position)))) continue;
        if (!cells.every(cell => isSolid(bot.blockAt(cell.offset(0, -1, 0))))) continue;
        if (!cells.every(cell => isAirLikeForStanding(bot.blockAt(cell.offset(0, 1, 0))))) continue;
        candidates.push({ cells, needsDig, distance: bot.entity.position.distanceTo(cells[1]) });
      }
    }
  }
  candidates.sort((a, b) => a.needsDig - b.needsDig || a.distance - b.distance);
  return candidates[0] || null;
}

// An infinite water source is a three-cell line whose end cells are poured as
// level-zero sources; the middle cell then settles into a source itself, so
// the pool never depletes no matter how many buckets are scooped from it.
export async function buildInfiniteWaterSource(bot, context = {}, { wait = operationWait } = {}) {
  return withCollectionEvidence(bot, async mutations => {
    const waterId = bot.registry?.blocksByName?.water?.id;
    const nearby = typeof bot.findBlocks === 'function' && waterId !== undefined
      ? bot.findBlocks({ matching: waterId, maxDistance: 16, count: 64 }) || []
      : [];
    const nearbySources = nearby.map(position => bot.blockAt(position)).filter(isWaterSource);
    const existing = findExistingPool(bot, nearbySources);
    if (existing) {
      return { created: false, already_present: true, position: existing.center, cells: existing.cells };
    }
    const site = selectTrenchSite(bot);
    if (!site) {
      fail('WATER_SOURCE_SITE_NOT_FOUND', '附近没有适合建造水池的地形：需要三格沟槽、实心底板和封闭侧壁。');
    }
    for (const cell of site.cells) {
      await carveCell(bot, cell, context, mutations);
    }
    const confirmation = waterConfirmation(context, wait);
    for (const index of [0, 2]) {
      await ensureWaterBucket(bot, context, wait, mutations);
      await pourFluidIntoCell(bot, site.cells[index], 'water_bucket', confirmation, context, mutations);
    }
    if (!await confirmation.until(() => site.cells.every(cell => isWaterSource(bot.blockAt(cell))))) {
      fail('INFINITE_POOL_UNCONFIRMED', '两端注水后沟槽没有全部凝固为静态水源。', { cells: site.cells });
    }
    return { created: true, position: site.cells[1], cells: site.cells };
  });
}

function countSolidBlocks(bot) {
  return SOLID_BLOCK_OPTIONS.reduce((total, name) => {
    const item = hasItem(bot, name);
    return total + (item?.count || 0);
  }, 0);
}

// A renewable lava farm stacks, top to bottom: lava source, solid support,
// down-pointing dripstone, cauldron. The dripstone sees the source two blocks
// above its head and drips lava into the cauldron on random ticks, refilling
// it roughly once per in-game day, so pooled lava is fully renewable.
function selectLavaFarmSite(bot) {
  const origin = bot.entity.position.floored();
  const surfaceY = origin.y - 1;
  const candidates = [];
  for (let x = -SITE_SCAN_RADIUS; x <= SITE_SCAN_RADIUS; x++) {
    for (let z = -SITE_SCAN_RADIUS; z <= SITE_SCAN_RADIUS; z++) {
      const ax = origin.x + x;
      const az = origin.z + z;
      const A = (y) => new Vec3(ax, y, az);
      const B = (y) => new Vec3(ax + 1, y, az);
      const C = (y) => new Vec3(ax + 2, y, az);
      const diggable = position => CARVABLE_GROUND.has(bot.blockAt(position)?.name);
      const solid = position => isSolid(bot.blockAt(position));
      const airLike = position => isAirLikeForStanding(bot.blockAt(position));
      if (![A(surfaceY), A(surfaceY - 1), A(surfaceY - 2), A(surfaceY - 3),
        B(surfaceY), B(surfaceY - 1), B(surfaceY - 2), C(surfaceY), C(surfaceY - 1)].every(diggable)) continue;
      if (!solid(A(surfaceY - 4)) || !solid(B(surfaceY - 3)) || !solid(C(surfaceY - 2))) continue;
      // Lava containment on the surface plus shaft walls that keep the drip
      // column enclosed and the stair dig safe.
      const walls = [
        A(surfaceY).offset(-1, 0, 0), A(surfaceY).offset(0, 0, 1), A(surfaceY).offset(0, 0, -1),
        ...[surfaceY - 3, surfaceY - 2, surfaceY - 1].flatMap(y => [
          A(y).offset(-1, 0, 0), A(y).offset(0, 0, 1), A(y).offset(0, 0, -1)]),
        ...[surfaceY - 3, surfaceY - 2, surfaceY - 1, surfaceY].flatMap(y => [
          B(y).offset(0, 0, 1), B(y).offset(0, 0, -1)]),
        ...[surfaceY - 2, surfaceY - 1, surfaceY].flatMap(y => [
          C(y).offset(0, 0, 1), C(y).offset(0, 0, -1)]),
      ];
      if (!walls.every(solid)) continue;
      if (!airLike(A(surfaceY + 1)) || !airLike(B(surfaceY + 1)) || !airLike(B(surfaceY + 2))
        || !airLike(C(surfaceY + 1))) continue;
      const position = A(surfaceY);
      candidates.push({
        cells: {
          lava: A(surfaceY), support: A(surfaceY - 1), dripstone: A(surfaceY - 2),
          cauldron: A(surfaceY - 3), stairB: [B(surfaceY), B(surfaceY - 1), B(surfaceY - 2)],
          stairC: [C(surfaceY), C(surfaceY - 1)], seal: B(surfaceY), pourStance: B(surfaceY + 1),
        },
        distance: bot.entity.position.distanceTo(position),
      });
    }
  }
  candidates.sort((a, b) => a.distance - b.distance);
  return candidates[0] || null;
}

export async function buildLavaDripFarm(bot, context = {}, { wait = operationWait } = {}) {
  return withCollectionEvidence(bot, async mutations => {
    if (!hasItem(bot, 'cauldron') || !hasItem(bot, 'pointed_dripstone') || !hasItem(bot, 'lava_bucket')
      || countSolidBlocks(bot) < 2) {
      fail('MISSING_MATERIAL', '建造岩浆滴落农场缺少材料：需要炼药锅、滴水石锥、岩浆桶和两块实心方块。', {
        cauldron: Boolean(hasItem(bot, 'cauldron')),
        pointed_dripstone: Boolean(hasItem(bot, 'pointed_dripstone')),
        lava_bucket: Boolean(hasItem(bot, 'lava_bucket')),
        solid_blocks: countSolidBlocks(bot),
      });
    }
    const site = selectLavaFarmSite(bot);
    if (!site) {
      fail('LAVA_FARM_SITE_NOT_FOUND', '附近没有适合建造岩浆滴落农场的地形：需要可开挖的阶梯井与封闭侧壁。');
    }
    const { cells } = site;
    // Open the surface, then descend one stair cell at a time so each dig
    // happens from a supported stance whose floor is still solid.
    for (const cell of [cells.lava, cells.stairB[0], cells.stairC[0]]) {
      await carveCell(bot, cell, context, mutations);
    }
    await navigateTo(bot, cells.stairC[0], context);
    await carveCell(bot, cells.stairB[1], context, mutations);
    await navigateTo(bot, cells.stairB[1], context);
    for (const cell of [cells.stairC[1], cells.support]) {
      await carveCell(bot, cell, context, mutations);
    }
    await navigateTo(bot, cells.stairC[1], context);
    await carveCell(bot, cells.stairB[2], context, mutations);
    await navigateTo(bot, cells.stairB[2], context);
    for (const cell of [cells.dripstone, cells.cauldron]) {
      await carveCell(bot, cell, context, mutations);
    }
    // Assemble the farm from the bottom of the shaft upward.
    await placeCellBlock(bot, cells.cauldron, 'cauldron', context, mutations);
    const supportName = hasItem(bot, 'cobblestone') ? 'cobblestone' : 'dirt';
    await placeCellBlock(bot, cells.support, supportName, context, mutations);
    await placeCellBlock(bot, cells.dripstone, 'pointed_dripstone', context, mutations);
    // Climb out of the shaft, seal the stair column, and pour lava from the
    // seal so the source sits level with the ground and stays contained.
    const exit = cells.seal.offset(0, 1, 1);
    await navigateTo(bot, exit, context);
    await placeCellBlock(bot, cells.seal, supportName, context, mutations);
    const confirmation = waterConfirmation(context, wait);
    await pourFluidIntoCell(bot, cells.lava, 'lava_bucket', confirmation, context, mutations);
    const structureOk = () => isLavaSource(bot.blockAt(cells.lava))
      && bot.blockAt(cells.support)?.name === supportName
      && bot.blockAt(cells.dripstone)?.name === 'pointed_dripstone'
      && bot.blockAt(cells.cauldron)?.name === 'cauldron';
    if (!await confirmation.until(structureOk)) {
      fail('FARM_STRUCTURE_UNCONFIRMED', '岩浆滴落农场的最终结构没有全部就位。', { cells });
    }
    return {
      created: true,
      position: cells.lava,
      cauldron: cells.cauldron,
      dripstone: cells.dripstone,
      lava_support: cells.support,
      fills_over_time: true,
    };
  });
}
