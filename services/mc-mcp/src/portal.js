import Vec3 from 'vec3';
import { placementMutation } from './placement.js';
import { operationWait } from './runtime/operationScope.js';

function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}

export async function ignitePortal(bot, { x, y, z }, context = {}) {
  context.operation_scope?.checkpoint();
  const origin = new Vec3(x, y, z);
  const interior = [];
  for (let dy = 0; dy < 5; dy++) {
    for (let dx = 0; dx < 4; dx++) {
      const position = origin.offset(dx, dy, 0);
      const name = bot.blockAt(position)?.name;
      if ((dx === 0 || dx === 3) && (dy === 0 || dy === 4)) continue;
      if (dx === 0 || dx === 3 || dy === 0 || dy === 4) {
        if (name !== 'obsidian') fail('PORTAL_FRAME_INCOMPLETE', '黑曜石门框尚未完整。');
      } else {
        if (!['air', 'cave_air', 'nether_portal'].includes(name)) {
          fail('PORTAL_INTERIOR_BLOCKED', '传送门内部被占用或尚未加载。');
        }
        interior.push(position);
      }
    }
  }
  const missing = interior.filter(position => bot.blockAt(position)?.name !== 'nether_portal');
  if (missing.length) {
    const item = bot.inventory.items().find(candidate => candidate.name === 'flint_and_steel');
    if (!item) fail('PORTAL_IGNITER_MISSING', '背包缺少打火石。');
    const reference = bot.blockAt(origin.offset(1, 0, 0));
    if (bot.entity.position.distanceTo(reference.position) > 4.5) {
      fail('PORTAL_OUT_OF_REACH', '需要先移动到门框旁边再点火。');
    }
    await bot.equip(item, 'hand');
    context.operation_scope?.checkpoint();
    await bot.activateBlock(reference, new Vec3(0, 1, 0));
    for (let attempt = 0; attempt < 20; attempt++) {
      context.operation_scope?.checkpoint();
      if (interior.every(position => bot.blockAt(position)?.name === 'nether_portal')) break;
      await operationWait(100);
    }
  }
  if (!interior.every(position => bot.blockAt(position)?.name === 'nether_portal')) {
    fail('PORTAL_ACTIVATION_UNCONFIRMED', '点火后未观察到完整的六格传送门。');
  }
  return {
    output: { activated: true, portal_blocks: 6 },
    explained_mutations: missing.map(position => (
      placementMutation('nether_portal', position, bot.game?.dimension)
    )),
    budget_usage: { max_actions: 1, max_blocks_changed: missing.length },
  };
}

export async function acquireFlint(bot, maxAttempts, context, { collect, place }) {
  const mutations = [];
  for (let attempt = 0; attempt <= maxAttempts; attempt++) {
    context.operation_scope?.checkpoint();
    if (bot.inventory.items().some(item => item.name === 'flint' && item.count > 0)) {
      return {
        output: { acquired: 'flint', attempts: attempt },
        explained_mutations: mutations,
        budget_usage: { max_actions: 1, max_blocks_changed: mutations.length },
      };
    }
    if (attempt === maxAttempts) break;
    const gravel = bot.inventory.items().find(item => item.name === 'gravel');
    if (gravel) {
      const base = bot.entity.position.floored();
      const target = [[2, 0], [-2, 0], [0, 2], [0, -2]]
        .map(([dx, dz]) => base.offset(dx, 0, dz))
        .find(position => ['air', 'cave_air'].includes(bot.blockAt(position)?.name)
          && bot.blockAt(position.offset(0, -1, 0))?.boundingBox === 'block');
      if (target) {
        const result = await place(target, context);
        mutations.push(...result.explained_mutations);
      }
    }
    try {
      await collect({ ...context, resourceMutations: mutations });
    } catch (error) {
      // A gravel dig can produce flint instead of the requested gravel drop.
      if (!bot.inventory.items().some(item => item.name === 'flint')) throw error;
    }
  }
  fail('FLINT_ATTEMPTS_EXHAUSTED', '有限次砂砾采掘未得到燧石，请保留进度后继续。');
}
