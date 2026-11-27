import Vec3 from 'vec3';
import {
  approachInteractionStance,
  CARVABLE_GROUND,
  carveCell,
  fail,
  hasItem,
  isSolid,
  NAVIGATION_ERROR_CODES,
  placeCellBlock,
  pourFluidIntoCell,
  TRENCH_REPLACEABLE,
} from './renewable.js';
import {
  collectionResourceMutation,
  isAirLikeForStanding,
  isSafeStandingPosition,
  withCollectionEvidence,
} from './collection.js';
import { placementMutation } from './placement.js';
import { operationWait } from './runtime/operationScope.js';
import {
  aimWaterItem,
  canInteractFrom,
  isLavaSource,
  isWaterSource,
  waterConfirmation,
  waterFillTarget,
} from './water.js';

const totalItemCount = (bot, name) => bot.inventory.items()
  .filter(item => item.name === name).reduce((total, item) => total + item.count, 0);

// Frame cells that must start out replaceable by the cast geometry.
const PORTAL_REPLACEABLE = new Set(['air', 'cave_air', 'short_grass', 'fern', 'dead_bush', 'snow']);

// Scoop lava from a nearby safe lava source with an empty bucket.
export async function fillLavaBucket(bot, context = {}, { wait = operationWait } = {}) {
  return withCollectionEvidence(bot, async mutations => {
    if (hasItem(bot, 'lava_bucket')) return { filled: true, already_present: true };
    const bucket = hasItem(bot, 'bucket');
    if (!bucket) fail('TOOL_REQUIRED', '舀取岩浆前需要先合成铁桶。');
    const lavaId = bot.registry?.blocksByName?.lava?.id;
    const positions = typeof bot.findBlocks === 'function' && lavaId !== undefined
      ? bot.findBlocks({
        matching: lavaId,
        maxDistance: 64,
        count: 512,
        useExtraInfo: block => isLavaSource(block)
          && isAirLikeForStanding(bot.blockAt(block.position.offset(0, 1, 0))),
      }) || []
      : [];
    const sources = positions
      .map(position => bot.blockAt(position))
      .filter(block => isLavaSource(block)
        && isAirLikeForStanding(bot.blockAt(block.position.offset(0, 1, 0))));
    if (!sources.length) {
      fail('LAVA_SOURCE_NOT_FOUND', '附近未观察到可以安全舀取的岩浆源。', {
        returned_candidates: positions.length,
      });
    }
    const origin = bot.entity.position.floored();
    sources.sort((a, b) => a.position.distanceTo(origin) - b.position.distanceTo(origin));
    const source = sources[0];
    const target = source.position.offset(0.5, 0.99, 0.5);
    await approachInteractionStance(bot, source.position, target, context);
    await bot.equip(bucket, 'hand');
    const confirmation = waterConfirmation(context, wait);
    await aimWaterItem(bot, target, confirmation);
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
    if (!isSafeStandingPosition(bot, bot.entity.position.floored())
      || !canInteractFrom(bot, source.position, target, bot.entity.position)) {
      fail('WATER_TARGET_UNREACHABLE', '使用铁桶前当前位置已不满足安全舀取岩浆条件。', {
        source: source.position,
      });
    }
    if (!isLavaSource(bot.blockAt(source.position))) {
      fail('TARGET_CHANGED', '舀取岩浆前岩浆源发生变化。', { source: source.position });
    }
    bot.activateItem();
    try {
      if (!await confirmation.until(() => hasItem(bot, 'lava_bucket'))) {
        fail('LAVA_FILL_UNCONFIRMED', '舀取岩浆后未在背包确认获得岩浆桶。', {
          source: source.position,
          target,
        });
      }
    } finally {
      bot.deactivateItem?.();
    }
    mutations.push(collectionResourceMutation('lava', source.position, bot.game?.dimension));
    return { filled: true, source: { position: source.position } };
  });
}

// Collect a full lava cauldron (from a lava drip farm) into a bucket.
export async function harvestLavaBucket(bot, context = {}, { wait = operationWait } = {}) {
  return withCollectionEvidence(bot, async mutations => {
    const bucket = hasItem(bot, 'bucket');
    if (!bucket) fail('TOOL_REQUIRED', '舀取岩浆前需要先合成铁桶。');
    const lavaCauldronId = bot.registry?.blocksByName?.['lava_cauldron']?.id;
    const cauldronId = bot.registry?.blocksByName?.cauldron?.id;
    const positions = [];
    if (typeof bot.findBlocks === 'function') {
      for (const id of [lavaCauldronId, cauldronId]) {
        if (id === undefined) continue;
        positions.push(...(bot.findBlocks({ matching: id, maxDistance: 16, count: 64 }) || []));
      }
    }
    const blocks = positions
      .map(position => bot.blockAt(position))
      .filter(block => block?.name === 'lava_cauldron' || block?.name === 'cauldron');
    const origin = bot.entity.position.floored();
    const ready = blocks
      .filter(block => block.name === 'lava_cauldron')
      .sort((a, b) => a.position.distanceTo(origin) - b.position.distanceTo(origin))[0];
    if (!ready) {
      if (blocks.some(block => block.name === 'cauldron')) {
        fail('LAVA_CAULDRON_NOT_READY', '炼药锅尚未积满岩浆。', {
          empty_cauldrons: blocks.filter(block => block.name === 'cauldron').map(block => block.position),
        });
      }
      fail('LAVA_CAULDRON_NOT_FOUND', '附近未找到岩浆滴落农场的炼药锅。', {
        returned_candidates: positions.length,
      });
    }
    const target = ready.position.offset(0.5, 0.99, 0.5);
    await approachInteractionStance(bot, ready.position, target, context);
    await bot.equip(bucket, 'hand');
    const confirmation = waterConfirmation(context, wait);
    await aimWaterItem(bot, target, confirmation);
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
    if (!isSafeStandingPosition(bot, bot.entity.position.floored())
      || !canInteractFrom(bot, ready.position, target, bot.entity.position)) {
      fail('WATER_TARGET_UNREACHABLE', '舀取炼药锅前当前位置已不满足安全舀取条件。', {
        cauldron: ready.position,
      });
    }
    bot.activateItem();
    try {
      if (!await confirmation.until(() => hasItem(bot, 'lava_bucket')
        && bot.blockAt(ready.position)?.name === 'cauldron')) {
        fail('LAVA_HARVEST_UNCONFIRMED', '舀取炼药锅中的岩浆后未得到确认。', {
          cauldron: ready.position,
        });
      }
    } finally {
      bot.deactivateItem?.();
    }
    mutations.push(collectionResourceMutation('lava', ready.position, bot.game?.dimension));
    return { harvested: true, position: ready.position };
  });
}

// ---------------------------------------------------------------------------
// Cast nether portal frame
// ---------------------------------------------------------------------------

function portalFrameGeometry(origin) {
  const corners = [];
  const obsidian = [];
  const interior = [];
  for (let dy = 0; dy <= 4; dy++) {
    for (let dx = 0; dx <= 3; dx++) {
      const position = origin.offset(dx, dy, 0);
      if ((dx === 0 || dx === 3) && (dy === 0 || dy === 4)) corners.push(position);
      else if (dx === 0 || dx === 3 || dy === 0 || dy === 4) obsidian.push(position);
      else interior.push(position);
    }
  }
  return { corners, obsidian, interior };
}

// Temporary support geometry, all relative to the origin. Walls contain each
// poured lava layer; molds close the top of the bottom row; the stair lets the
// bot climb beside the frame. Upper stair steps get a backing block because a
// diagonal step has no face-adjacent solid neighbour to place against.
function portalTempGeometry(origin) {
  const walls = [];
  for (const dz of [1, -1]) {
    for (let dx = 0; dx <= 3; dx++) walls.push(origin.offset(dx, 0, dz));
    for (let dy = 1; dy <= 3; dy++) {
      walls.push(origin.offset(0, dy, dz), origin.offset(3, dy, dz));
    }
    // Extra layer-3 bases so the top-row walls stack onto something solid.
    walls.push(origin.offset(1, 3, dz), origin.offset(2, 3, dz));
    walls.push(origin.offset(1, 4, dz), origin.offset(2, 4, dz));
  }
  const molds = [];
  for (let dy = 1; dy <= 3; dy++) {
    molds.push(origin.offset(1, dy, 0), origin.offset(2, dy, 0));
  }
  const stairs = [];
  for (let k = 0; k <= 4; k++) {
    if (k > 0) stairs.push(origin.offset(k, k - 1, 2));
    stairs.push(origin.offset(k, k, 2));
  }
  return { walls, molds, stairs };
}

function portalReplaceable(block) {
  return Boolean(block) && PORTAL_REPLACEABLE.has(block.name);
}

function portalTempClearable(block) {
  return Boolean(block) && (PORTAL_REPLACEABLE.has(block.name) || CARVABLE_GROUND.has(block.name)
    || TRENCH_REPLACEABLE.has(block.name));
}

// Approach, then place one temporary dirt cell; carves ground first when the
// cell sits inside carvable terrain.
async function placeTempCell(bot, cell, context, mutations, tracker) {
  const block = bot.blockAt(cell);
  if (!block) fail('REGION_NOT_LOADED', '目标格所在区块尚未加载。', { position: cell });
  if (isSolid(block)) {
    tracker.push(cell);
    return;
  }
  if (!portalTempClearable(block)) {
    fail('PORTAL_SITE_NOT_FOUND', '指定位置不适合浇铸传送门框架。', { position: cell, block: block.name });
  }
  await carveCell(bot, cell, context, mutations);
  await approachInteractionStance(bot, cell, cell.offset(0.5, 0.5, 0.5), context);
  await placeCellBlock(bot, cell, 'dirt', context, mutations);
  tracker.push(cell);
}

// Pour water over the lava source in `cell` to solidify it into obsidian, then
// scoop the residual water source above it back into the bucket.
async function waterCastCell(bot, cell, confirmation, context, mutations) {
  const target = cell.offset(0.5, 0.99, 0.5);
  await approachInteractionStance(bot, cell, target, context);
  const waterBucket = hasItem(bot, 'water_bucket');
  if (!waterBucket) {
    fail('MISSING_MATERIAL', '浇水固化黑曜石前水桶已耗尽。', { position: cell });
  }
  await bot.equip(waterBucket, 'hand');
  await aimWaterItem(bot, target, confirmation);
  context.operation_scope?.checkpoint();
  context.signal?.throwIfAborted();
  if (!isSafeStandingPosition(bot, bot.entity.position.floored())
    || !canInteractFrom(bot, cell, target, bot.entity.position)) {
    fail('WATER_TARGET_UNREACHABLE', '浇水前当前位置已不满足安全浇铸条件。', { position: cell });
  }
  if (!isLavaSource(bot.blockAt(cell))) {
    fail('TARGET_CHANGED', '浇水固化前岩浆源发生变化。', { position: cell });
  }
  bot.activateItem();
  try {
    if (!await confirmation.until(() => bot.blockAt(cell)?.name === 'obsidian')) {
      fail('CAST_UNCONFIRMED', '浇水固化黑曜石后未得到确认。', { position: cell });
    }
  } finally {
    bot.deactivateItem?.();
  }
  mutations.push(placementMutation('obsidian', cell, bot.game?.dimension));
  // The poured water settles as a source right above the fresh obsidian.
  // Scoop it back so the cast leaves no stray fluids in the frame volume.
  const waterPosition = cell.offset(0, 1, 0);
  if (isWaterSource(bot.blockAt(waterPosition))) {
    const bucket = hasItem(bot, 'bucket');
    if (bucket) {
      const scoopTarget = waterFillTarget(waterPosition);
      await approachInteractionStance(bot, waterPosition, scoopTarget, context);
      await bot.equip(bucket, 'hand');
      await aimWaterItem(bot, scoopTarget, confirmation);
      context.operation_scope?.checkpoint();
      bot.activateItem();
      try {
        if (!await confirmation.until(() => hasItem(bot, 'water_bucket'))) {
          fail('CAST_UNCONFIRMED', '回收浇铸用水后未得到确认。', { position: waterPosition });
        }
      } finally {
        bot.deactivateItem?.();
      }
      mutations.push(collectionResourceMutation('water', waterPosition, bot.game?.dimension));
    }
  }
}

async function pourAndCastCell(bot, cell, context, wait, mutations) {
  // Each pour/cast cycle gets a fresh confirmation budget; a single shared
  // confirmation would run dry across the ten casting cells.
  const confirmation = waterConfirmation(context, wait);
  await pourFluidIntoCell(bot, cell, 'lava_bucket', confirmation, context, mutations);
  await waterCastCell(bot, cell, confirmation, context, mutations);
}

export async function castNetherPortalFrame(bot, context = {}, { wait = operationWait, x, y, z } = {}) {
  return withCollectionEvidence(bot, async mutations => {
    for (const [axis, value] of [['x', x], ['y', y], ['z', z]]) {
      if (!Number.isFinite(Number(value)) || !Number.isInteger(Number(value))) {
        fail('INVALID_PARAMETERS', '浇铸传送门需要整数原点坐标。', { axis, value });
      }
    }
    const origin = new Vec3(x, y, z);
    const geometry = portalFrameGeometry(origin);
    const temp = portalTempGeometry(origin);

    const lavaBuckets = totalItemCount(bot, 'lava_bucket');
    const deepslate = totalItemCount(bot, 'cobbled_deepslate');
    const dirt = totalItemCount(bot, 'dirt');
    if (lavaBuckets < 10 || deepslate < 4 || dirt < 32 || !hasItem(bot, 'water_bucket')) {
      fail('MISSING_MATERIAL', '浇铸传送门缺少材料：需要十个岩浆桶、四块深板岩圆石、三十二个泥土和一个铁桶。', {
        lava_bucket: lavaBuckets,
        cobbled_deepslate: deepslate,
        dirt,
        water_bucket: Boolean(hasItem(bot, 'water_bucket')),
      });
    }

    // Site validation: every frame cell starts replaceable, the ground under
    // the casting zone is solid, and the temporary geometry has room.
    for (const cell of [...geometry.corners, ...geometry.obsidian, ...geometry.interior]) {
      const block = bot.blockAt(cell);
      if (!portalReplaceable(block)) {
        fail('PORTAL_SITE_NOT_FOUND', '指定位置不适合浇铸传送门框架。', {
          position: cell, block: block?.name ?? null,
        });
      }
    }
    for (let dx = 0; dx <= 3; dx++) {
      for (const dz of [-1, 0, 1]) {
        if (!isSolid(bot.blockAt(origin.offset(dx, -1, dz)))) {
          fail('PORTAL_SITE_NOT_FOUND', '指定位置不适合浇铸传送门框架。', {
            position: origin.offset(dx, -1, dz),
          });
        }
      }
    }
    for (let dx = 0; dx <= 4; dx++) {
      if (!isSolid(bot.blockAt(origin.offset(dx, -1, 2)))) {
        fail('PORTAL_SITE_NOT_FOUND', '指定位置不适合浇铸传送门框架。', {
          position: origin.offset(dx, -1, 2),
        });
      }
    }
    for (const cell of [...temp.walls, ...temp.molds, ...temp.stairs]) {
      if (!portalTempClearable(bot.blockAt(cell))) {
        fail('PORTAL_SITE_NOT_FOUND', '指定位置不适合浇铸传送门框架。', {
          position: cell, block: bot.blockAt(cell)?.name ?? null,
        });
      }
    }

    const placedTemp = [];

    // 1. Stair: s_k at (k, k, +2) with a backing block below each upper step.
    for (let k = 0; k <= 4; k++) {
      if (k > 0) {
        await placeTempCell(bot, origin.offset(k, k - 1, 2), context, mutations, placedTemp);
      }
      await placeTempCell(bot, origin.offset(k, k, 2), context, mutations, placedTemp);
    }

    // 2. Bottom row: corner supports, containment walls, cast both cells.
    await placeCellBlock(bot, origin.offset(0, 0, 0), 'cobbled_deepslate', context, mutations);
    await placeCellBlock(bot, origin.offset(3, 0, 0), 'cobbled_deepslate', context, mutations);
    for (const dx of [0, 1, 2, 3]) {
      for (const dz of [1, -1]) {
        await placeTempCell(bot, origin.offset(dx, 0, dz), context, mutations, placedTemp);
      }
    }
    await pourAndCastCell(bot, origin.offset(1, 0, 0), context, wait, mutations);
    await pourAndCastCell(bot, origin.offset(2, 0, 0), context, wait, mutations);

    // 3. Middle layers: mold over the cast bottom, walls, cast side pillars.
    for (let layer = 1; layer <= 3; layer++) {
      for (const dx of [1, 2]) {
        await placeTempCell(bot, origin.offset(dx, layer, 0), context, mutations, placedTemp);
      }
      const wallColumns = layer === 3 ? [0, 3, 1, 2] : [0, 3];
      for (const dx of wallColumns) {
        for (const dz of [1, -1]) {
          await placeTempCell(bot, origin.offset(dx, layer, dz), context, mutations, placedTemp);
        }
      }
      await pourAndCastCell(bot, origin.offset(0, layer, 0), context, wait, mutations);
      await pourAndCastCell(bot, origin.offset(3, layer, 0), context, wait, mutations);
    }

    // 4. Top row: corner supports stand on the cast pillars below them.
    await placeCellBlock(bot, origin.offset(0, 4, 0), 'cobbled_deepslate', context, mutations);
    await placeCellBlock(bot, origin.offset(3, 4, 0), 'cobbled_deepslate', context, mutations);
    for (const dx of [1, 2]) {
      for (const dz of [1, -1]) {
        await placeTempCell(bot, origin.offset(dx, 4, dz), context, mutations, placedTemp);
      }
    }
    await pourAndCastCell(bot, origin.offset(1, 4, 0), context, wait, mutations);
    await pourAndCastCell(bot, origin.offset(2, 4, 0), context, wait, mutations);

    // 5. Cleanup: dig every temporary block we placed. Walls first (top down),
    // then molds, then the stair from its top step downward.
    const digOrder = [];
    const wallKey = cell => `${cell.x},${cell.y},${cell.z}`;
    const placedSet = new Set(placedTemp.map(wallKey));
    for (const cell of temp.walls) if (placedSet.has(wallKey(cell))) digOrder.push(cell);
    digOrder.sort((a, b) => b.y - a.y);
    for (const cell of temp.molds) if (placedSet.has(wallKey(cell))) digOrder.push(cell);
    const stairOrder = [];
    for (let k = 4; k >= 0; k--) {
      if (k > 0) stairOrder.push(origin.offset(k, k, 2), origin.offset(k, k - 1, 2));
      else stairOrder.push(origin.offset(0, 0, 2));
    }
    for (const cell of stairOrder) if (placedSet.has(wallKey(cell))) digOrder.push(cell);
    for (const cell of digOrder) {
      if (bot.blockAt(cell)?.name !== 'dirt') continue;
      try {
        await carveCell(bot, cell, context, mutations);
      } catch (error) {
        if (!NAVIGATION_ERROR_CODES.includes(error.code || error.name)) throw error;
        fail('CAST_UNCONFIRMED', '浇铸完成后无法清理临时方块。', { position: cell });
      }
    }

    // 6. Final verification: exact frame materials and a clear interior.
    for (const cell of geometry.corners) {
      if (bot.blockAt(cell)?.name !== 'cobbled_deepslate') {
        fail('CAST_UNCONFIRMED', '浇铸传送门后角落支撑未确认。', { position: cell });
      }
    }
    for (const cell of geometry.obsidian) {
      if (bot.blockAt(cell)?.name !== 'obsidian') {
        fail('CAST_UNCONFIRMED', '浇铸传送门后黑曜石框架未确认。', { position: cell });
      }
    }
    for (const cell of geometry.interior) {
      if (!isAirLikeForStanding(bot.blockAt(cell))) {
        fail('CAST_UNCONFIRMED', '浇铸传送门后内部空间未清理干净。', { position: cell });
      }
    }
    return { created: true, origin: { x, y, z } };
  });
}
