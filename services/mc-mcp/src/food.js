import { collectionResourceMutation } from './collection.js';
import { operationWait } from './runtime/operationScope.js';

export async function eatFood(bot, itemName, context = {}) {
  context.operation_scope?.checkpoint();
  const item = bot.inventory.items().find(candidate => candidate.name === itemName);
  const unsafe = ['rotten_flesh', 'spider_eye', 'poisonous_potato', 'pufferfish', 'chicken'];
  if (!item || !bot.registry.foodsByName?.[item.name] || unsafe.includes(item.name)) {
    const error = new Error('背包中没有所选的安全食物。');
    error.code = 'SAFE_FOOD_MISSING';
    throw error;
  }
  await bot.equip(item, 'hand');
  context.operation_scope?.checkpoint();
  let onAbort;
  const cancelled = new Promise((resolve, reject) => {
    onAbort = () => {
      bot.deactivateItem();
      reject(context.signal.reason || new Error('进食已取消。'));
    };
    context.signal?.addEventListener('abort', onAbort, { once: true });
  });
  try {
    await Promise.race([bot.consume(), cancelled]);
  } finally {
    context.signal?.removeEventListener('abort', onAbort);
  }
  return { output: { eaten: itemName }, budget_usage: { max_actions: 1 } };
}

export async function forageApples(bot, maxBlocks, context, { navigate, pickup }) {
  const mutations = [];
  const initialApples = () => bot.inventory.items()
    .filter(item => item.name === 'apple').reduce((total, item) => total + item.count, 0);
  const before = initialApples();
  for (let attempt = 0; attempt < maxBlocks; attempt++) {
    context.operation_scope?.checkpoint();
    const leaf = bot.findBlock({
      matching: block => ['oak_leaves', 'dark_oak_leaves'].includes(block?.name),
      maxDistance: 16,
    });
    if (!leaf) break;
    if (await navigate(leaf.position, context) === false) break;
    context.operation_scope?.checkpoint();
    if (bot.entity.position.distanceTo(leaf.position) > 4.5) break;
    await bot.dig(leaf);
    mutations.push(collectionResourceMutation(leaf.name, leaf.position, bot.game?.dimension));
    await operationWait(100);
    await pickup(1000, leaf.position);
    if (initialApples() > before) break;
  }
  return {
    output: { apples_found: initialApples() - before, leaves_harvested: mutations.length },
    explained_mutations: mutations,
    budget_usage: { max_actions: 1, max_blocks_changed: mutations.length },
  };
}
