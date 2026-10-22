import { findMineSupportItem } from './branch_mine.js';
import { findPlacementReference, placementMutation } from './placement.js';
import Vec3 from 'vec3';

const FILLABLE = new Set(['air', 'cave_air', 'water', 'flowing_water', 'lava', 'flowing_lava']);
const HEADROOM = new Set(['air', 'cave_air']);
const SIDES = [[1, 0], [-1, 0], [0, 1], [0, -1]];

function fail(code, message) { throw Object.assign(new Error(message), { code }); }

export async function backfillObsidianHole(bot, position, context = {}) {
  context.operation_scope?.checkpoint();
  context.signal?.throwIfAborted();
  const current = bot.blockAt(position);
  if (current?.boundingBox === 'block') return null;
  if (!FILLABLE.has(current?.name)) fail('SUPPORT_HOLE_UNSAFE', '回填位置尚未加载或不能安全替换。');
  const item = findMineSupportItem(bot);
  if (!item) fail('SUPPORT_BLOCK_REQUIRED', '安全采掘需要保留普通实心方块回填脚下缺口。');
  const reference = findPlacementReference(bot, position, Vec3);
  if (!reference) fail('SUPPORT_REFERENCE_MISSING', '缺口附近没有可靠的放置参照。');
  await bot.equip(item, 'hand');
  context.operation_scope?.checkpoint();
  await bot.placeBlock(reference.reference, reference.face);
  if (bot.blockAt(position)?.name !== item.name) {
    fail('SUPPORT_PLACEMENT_UNCONFIRMED', '回填后没有观察到连续的工作地面。');
  }
  return placementMutation(item.name, position, bot.game?.dimension);
}

export async function restoreObsidianWorkSurface(bot, context = {}, mutations = []) {
  const feet = bot.entity.position.floored();
  const candidates = [];
  for (let dx = -2; dx <= 2; dx++) {
    for (let dz = -2; dz <= 2; dz++) {
      const position = feet.offset(dx, -1, dz);
      if (!FILLABLE.has(bot.blockAt(position)?.name)) continue;
      if (!['air', 'cave_air', 'water', 'flowing_water'].includes(bot.blockAt(position.offset(0, 1, 0))?.name)
        || !HEADROOM.has(bot.blockAt(position.offset(0, 2, 0))?.name)) continue;
      const neighbors = SIDES.map(([x, z]) => bot.blockAt(position.offset(x, 0, z)));
      if (!neighbors.some(block => block?.name === 'obsidian')
        || neighbors.filter(block => block?.boundingBox === 'block').length < 2) continue;
      candidates.push(position);
    }
  }
  candidates.sort((a, b) => bot.entity.position.distanceTo(a) - bot.entity.position.distanceTo(b));
  for (const position of candidates.slice(0, 4)) {
    const mutation = await backfillObsidianHole(bot, position, context);
    if (mutation) mutations.push(mutation);
  }
  return mutations;
}
