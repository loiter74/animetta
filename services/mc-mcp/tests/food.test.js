import assert from 'node:assert/strict';
import test from 'node:test';
import Vec3 from 'vec3';
import { eatFood, forageApples } from '../src/food.js';

test('eat uses a real food item and preserves cancellation before consumption', async () => {
  let consumed = 0;
  const bot = {
    inventory: { items: () => [{ name: 'apple', count: 1 }] },
    registry: { foodsByName: { apple: {} } },
    equip: async () => {}, consume: async () => { consumed++; },
  };
  await eatFood(bot, 'apple');
  assert.equal(consumed, 1);
  await assert.rejects(eatFood(bot, 'apple', {
    operation_scope: { checkpoint() { throw new Error('cancelled'); } },
  }), /cancelled/);
  assert.equal(consumed, 1);
  await assert.rejects(eatFood(bot, 'poisonous_potato'), { code: 'SAFE_FOOD_MISSING' });
});

test('foraging reports harvested leaves separately from actually collected apples', async () => {
  let dug = false;
  let apples = 0;
  const leaf = { name: 'oak_leaves', position: new Vec3(0, 65, 1) };
  const bot = {
    inventory: { items: () => apples ? [{ name: 'apple', count: apples }] : [] },
    entity: { position: new Vec3(0, 64, 0) },
    findBlock: () => dug ? null : leaf,
    async dig() { dug = true; },
  };
  const result = await forageApples(bot, 8, {}, {
    navigate: async () => {}, pickup: async () => { apples = 1; },
  });
  assert.deepEqual(result.output, { apples_found: 1, leaves_harvested: 1 });
  assert.equal(result.explained_mutations[0].delta, -1);
  const empty = await forageApples(bot, 8, {}, {
    navigate: async () => {}, pickup: async () => {},
  });
  assert.deepEqual(empty.output, { apples_found: 0, leaves_harvested: 0 });
});

test('cancellation releases item use while the consume acknowledgement is pending', async () => {
  const controller = new AbortController();
  let stopped = false;
  const bot = {
    inventory: { items: () => [{ name: 'apple', count: 1 }] },
    registry: { foodsByName: { apple: {} } },
    equip: async () => {},
    consume: () => new Promise(() => {}),
    deactivateItem() { stopped = true; },
  };
  const eating = eatFood(bot, 'apple', { signal: controller.signal });
  await Promise.resolve();
  controller.abort(new Error('cancel eating'));
  await assert.rejects(eating, /cancel eating/);
  assert.equal(stopped, true);
});
