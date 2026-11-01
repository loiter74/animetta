import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import minecraftData from 'minecraft-data';
import injectCraft from 'mineflayer/lib/plugins/craft.js';
import { craftOperations, WOOD_PLANK_RECIPES } from '../src/crafting/counts.js';
import { craftMixedPlanks } from '../src/crafting/wood.js';
import { OperationScope, activeOperationScope, operationWait, runWithOperationScope } from '../src/runtime/operationScope.js';

const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');

function fixture(stock, { delayed = true, deadlineMs = 10_000, abortOnWait = false } = {}) {
  const registry = minecraftData('1.21');
  const bag = { ...stock };
  const calls = [];
  const samples = [];
  const abort = new AbortController();
  let clock = 0;
  let pending = null;
  const bot = { registry, inventory: {
    items: () => Object.entries(bag).filter(([, count]) => count > 0).map(([name, count]) => ({ name, count })),
    count: id => bag[registry.items[id].name] || 0,
  } };
  injectCraft(bot);
  bot.craft = async (recipe, operations) => {
    calls.push({ recipe: registry.items[recipe.result.id].name, operations, bag: { ...bag } });
    for (const delta of recipe.delta) {
      const name = registry.items[delta.id].name;
      const gain = delta.count * operations;
      assert.ok((bag[name] || 0) + gain >= 0);
      if (gain > 0) {
        const initial = bag[name] || 0;
        bag[name] = initial + Math.min(4, gain);
        pending = () => { bag[name] = initial + gain; };
      } else bag[name] += gain;
    }
  };
  const scope = new OperationScope({ bot, signal: abort.signal, deadlineMs,
    nowMs: () => clock,
    waitMs: async ms => {
      clock += ms;
      samples.push({ clock, bag: { ...bag } });
      if (abortOnWait) abort.abort();
      if (delayed && pending) { pending(); pending = null; }
    },
  });
  const inventoryCount = name => bag[name] || 0;
  const craftError = (message, code, extra = {}) => Object.assign(new Error(message), { code, ...extra });
  const start = source.indexOf('async function _waitForInventoryIncrease(');
  const end = source.indexOf('\nfunction _collectDebug(', start);
  assert.ok(start > 0 && end > start);
  const waitForInventoryIncrease = runInNewContext(`(${source.slice(start, end)})`, {
    Date: { now: () => clock }, _inventoryCount: inventoryCount,
    operationWait, activeOperationScope, craftError,
  });
  const craftStart = source.indexOf('async function _craft(');
  const craftEnd = source.indexOf('\nfunction _getRecipeIngredientNames(', craftStart);
  const craft = runInNewContext(`(${source.slice(craftStart, craftEnd)})`, {
    bot, process: { env: {} }, FALLBACK_RECIPES: WOOD_PLANK_RECIPES, craftOperations,
    craftMixedPlanks, getMcData: async () => registry, craftError,
    presentBlockTarget: async () => null,
    _inventoryCount: inventoryCount, _waitForInventoryIncrease: waitForInventoryIncrease,
    _checkCraftMaterials: () => [], _orderRecipesForInventory: recipes => recipes,
    _reclaimCraftingTable: async () => {},
    _ensureCraftingTable: () => { throw new Error('planks use inventory crafting'); },
  });
  return { bag, calls, samples, get clock() { return clock; },
    run: (recipe = 'any_planks') => runWithOperationScope(scope,
      () => craft(recipe, 32, { operation_scope: scope, signal: abort.signal })),
  };
}

test('R107 family craft waits for all 32 birch planks after SDK completion', async () => {
  const f = fixture({ birch_log: 8 });
  await f.run();
  assert.equal(f.bag.birch_planks, 32);
  assert.equal(f.calls.length, 1);
  assert.equal(f.calls[0].operations, 8);
  assert.equal(f.samples[0].bag.birch_planks, 4);
  assert.equal(f.clock, 100);
});

test('exact-item craft also confirms the requested batch, rather than its first item', async () => {
  const f = fixture({ birch_log: 8 });
  await f.run('birch_planks');
  assert.equal(f.bag.birch_planks, 32);
  assert.equal(f.clock, 100);
});

test('mixed craft confirms the first species before starting the second', async () => {
  const f = fixture({ oak_log: 5, spruce_log: 3 });
  await f.run();
  assert.deepEqual(f.calls.map(c => [c.recipe, c.operations]), [['oak_planks', 5], ['spruce_planks', 3]]);
  assert.equal(f.calls[1].bag.oak_planks, 20);
  assert.equal(f.bag.oak_planks + f.bag.spruce_planks, 32);
});

test('missing full output stops after the original five seconds without another craft', async () => {
  const f = fixture({ oak_log: 5, spruce_log: 3 }, { delayed: false });
  await assert.rejects(f.run(), { code: 'CRAFT_OUTPUT_UNCONFIRMED' });
  assert.equal(f.clock, 5000);
  assert.equal(f.calls.length, 1);
  assert.equal(f.bag.spruce_log, 3);
});

test('deadline and cancellation stop confirmation without another recipe', async () => {
  const deadline = fixture({ birch_log: 8 }, { delayed: false, deadlineMs: 350 });
  await assert.rejects(deadline.run(), { code: 'ACTION_DEADLINE_EXPIRED' });
  assert.ok(deadline.clock <= 350);
  assert.equal(deadline.calls.length, 1);
  const cancelled = fixture({ birch_log: 8 }, { delayed: false, abortOnWait: true });
  await assert.rejects(cancelled.run(), { code: 'ACTION_CANCELLED' });
  assert.equal(cancelled.calls.length, 1);
});
