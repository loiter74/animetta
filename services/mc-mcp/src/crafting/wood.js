import { WOOD_PLANK_RECIPES } from './counts.js';

export function plankCount(bot) {
  return bot.inventory.items().reduce((total, item) => total
    + (Object.hasOwn(WOOD_PLANK_RECIPES, item.name) ? Math.max(0, Number(item.count) || 0) : 0), 0);
}

export async function craftMixedPlanks(bot, count, context, craftSingle) {
  if (!Number.isSafeInteger(count) || count < 1 || count > 64) {
    throw Object.assign(new Error('木板合成数量必须在原有1至64范围内。'), { code: 'INVALID_ARGUMENT' });
  }
  let remaining = Math.ceil(count / 4);
  const stock = new Map();
  for (const item of bot.inventory.items()) stock.set(item.name,
    (stock.get(item.name) || 0) + Math.max(0, Number(item.count) || 0));
  const plan = [];
  for (const [recipe, definition] of Object.entries(WOOD_PLANK_RECIPES)) {
    const log = Object.keys(definition.ingredients)[0];
    const operations = Math.min(remaining, stock.get(log) || 0);
    if (operations) plan.push({ recipe, count: operations * definition.result });
    remaining -= operations;
  }
  if (remaining) throw Object.assign(new Error('背包中的原木不足以合成所需木板。'), {
    code: 'MISSING_MATERIALS', details: { missing_logs: remaining },
  });
  const initial = plankCount(bot);
  for (const part of plan) {
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
    const before = plankCount(bot);
    await craftSingle(part.recipe, part.count, context);
    if (plankCount(bot) - before !== part.count) {
      throw Object.assign(new Error('分物种合成后木板增量未得到确认，停止后续合成。'), {
        code: 'CRAFT_OUTPUT_UNCONFIRMED', details: { recipe: part.recipe, expected: part.count },
      });
    }
  }
  return `Crafted ${plankCount(bot) - initial} any_planks`;
}
