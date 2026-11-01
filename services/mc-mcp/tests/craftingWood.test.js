import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { craftMixedPlanks, plankCount } from '../src/crafting/wood.js';

function fixture(stock) {
  const bag = { ...stock };
  const calls = [];
  const bot = { inventory: { items: () => Object.entries(bag)
    .filter(([, count]) => count > 0).map(([name, count]) => ({ name, count })) } };
  const craft = async (recipe, count) => {
    const log = recipe.replace(/_planks$/, '_log');
    assert.ok(bag[log] >= count / 4);
    bag[log] -= count / 4;
    bag[recipe] = (bag[recipe] || 0) + count;
    calls.push([recipe, count]);
  };
  return { bot, bag, calls, craft };
}

test('one native family craft makes 32 planks from five oak and three spruce logs', async () => {
  const f = fixture({ oak_log: 5, spruce_log: 3 });
  await craftMixedPlanks(f.bot, 32, {}, f.craft);
  assert.deepEqual(f.calls, [['oak_planks', 20], ['spruce_planks', 12]]);
  assert.equal(plankCount(f.bot), 32);
  assert.equal(f.bag.oak_log + f.bag.spruce_log, 0);
});

test('native craft entry delegates the family before exact-item lookup', async () => {
  const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  const start = source.indexOf('async function _craft(');
  const end = source.indexOf('\nasync function _manualCraft(', start);
  assert.ok(start > 0 && end > start);
  const f = fixture({ birch_log: 4 });
  const craft = runInNewContext(source.slice(start, end) + '\n_craft', {
    bot: f.bot, craftMixedPlanks: (bot, count, context) => craftMixedPlanks(bot, count, context, f.craft),
    getMcData: () => { throw new Error('family must not look up a fake item ID'); },
  });
  await craft('any_planks', 16, {});
  assert.equal(f.bag.birch_planks, 16);
});

test('missing logs fail before any recipe transaction', async () => {
  const f = fixture({ oak_log: 5, spruce_log: 2 });
  await assert.rejects(craftMixedPlanks(f.bot, 32, {}, f.craft), { code: 'MISSING_MATERIALS' });
  assert.deepEqual(f.calls, []);
  assert.equal(plankCount(f.bot), 0);
});

test('an unconfirmed recipe or cancellation never starts another species', async () => {
  const f = fixture({ oak_log: 5, spruce_log: 3 });
  let calls = 0;
  await assert.rejects(craftMixedPlanks(f.bot, 32, {}, async () => { calls++; }), {
    code: 'CRAFT_OUTPUT_UNCONFIRMED',
  });
  assert.equal(calls, 1);
  const abort = new AbortController();
  await assert.rejects(craftMixedPlanks(f.bot, 32, { signal: abort.signal }, async (...args) => {
    await f.craft(...args); abort.abort();
  }), { name: 'AbortError' });
  assert.deepEqual(f.calls, [['oak_planks', 20]]);
});
