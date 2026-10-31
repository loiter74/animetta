import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { runInNewContext } from 'node:vm';
import Vec3 from 'vec3';
import pathfinder from 'mineflayer-pathfinder';
import minecraftData from 'minecraft-data';
import prismarineBlock from 'prismarine-block';
import WorldSync from 'prismarine-world/src/worldsync.js';
import * as collection from '../src/collection.js';
import * as resources from '../src/resources/registry.js';

function partialOreApproach({ advance = true, abort = false } = {}) {
  const registry = minecraftData('1.21.1'), Block = prismarineBlock(registry);
  const removed = new Set(), bag = [], world = new WorldSync(null);
  const target = new Vec3(5, 64, 0), controller = new AbortController();
  world.getBlock = point => {
    const p = point.floored();
    const name = removed.has(p.toString()) || p.y > 66 ||
      (p.z === 0 && p.x <= 1 && p.y >= 64 && p.y <= 65) ? 'air'
      : p.equals(target) ? 'iron_ore' : 'stone';
    const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
    block.position = p;
    return block;
  };
  const bot = new EventEmitter();
  Object.assign(bot, { registry, world, game: { minY: -64, height: 384 }, entities: {},
    entity: { position: new Vec3(1.5, 64, .5), eyeHeight: 1.62, effects: {} },
    inventory: { items: () => [{ name: 'stone_pickaxe', type: registry.itemsByName.stone_pickaxe.id, count: 1 }, ...bag] },
    blockAt: p => world.getBlock(p),
    findBlock: ({ matching }) => matching(world.getBlock(target)) ? world.getBlock(target) : null,
  });
  pathfinder.pathfinder(bot);
  const movements = collection.configureDryNavigation(new pathfinder.Movements(bot, registry), bot);
  movements.allow1by1towers = false;
  let navigations = 0;
  const attempts = [];
  bot.pathfinder.stop = () => {};
  bot.pathfinder.goto = async goal => {
    navigations++;
    let result;
    for (const planned of bot.pathfinder.getPathFromTo(movements, bot.entity.position, goal)) {
      result = planned.result;
      if (result.status !== 'partial') break;
    }
    assert.equal(result.status, 'success', 'the installed SDK can plan this access tunnel');
    const move = result.path.find(p => !new Vec3(p.x, p.y, p.z).floored().equals(bot.entity.position.floored()));
    if (advance && move) {
      for (const p of move.toBreak) removed.add(new Vec3(p.x, p.y, p.z).toString());
      bot.entity.position = new Vec3(Math.floor(move.x) + .5, move.y, Math.floor(move.z) + .5);
    }
    if (abort) controller.abort(Object.assign(new Error('action budget stopped'), { code: 'BUDGET_EXHAUSTED' }));
    if (!goal.isEnd(bot.entity.position.floored())) {
      throw Object.assign(new Error('settled partial navigation'), { code: 'ACTION_DEADLINE_EXPIRED' });
    }
  };
  const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  const start = source.indexOf('async function _collectInner('), end = source.indexOf('\nfunction craftError(', start);
  assert.ok(start >= 0 && end > start);
  const collect = runInNewContext(`(${source.slice(start, end)})`, {
    ...collection, ...resources, bot, Vec3, ITEM_TO_BLOCK: {}, BLOCK_DROP_ITEM: { iron_ore: 'raw_iron' },
    shouldPrepareUndergroundCollection: () => null, _stabilizePosition: async () => {}, _collectDebug() {},
    presentBlockTarget: async ({ ordinal }) => { attempts.push(ordinal); return null; },
    _equipToolForBlock: async () => {}, operationWait: async () => {}, _pickupDroppedItems: async () => {},
    _inventoryCount: item => collection.pickupInventoryCount(bot, item), getMcData: async () => registry,
    locateResource: async () => { throw Object.assign(new Error('no additional target'), { code: 'RESOURCE_NOT_FOUND' }); },
    _explore_for_block: async () => {},
    digCollectionBlock: async (_bot, block) => {
      removed.add(block.position.toString());
      bag.push({ name: 'raw_iron', count: 1 });
    },
  });
  return { collect: () => collect('iron_ore', 1, registry, { signal: controller.signal }),
    attempts, bag, removed, navigations: () => navigations };
}

test('settled partial ore navigation keeps approaching the known reachable vein', async () => {
  const fixture = partialOreApproach();
  assert.equal(await fixture.collect(), 'Collected 1 iron_ore');
  assert.equal(fixture.navigations(), 3);
  assert.deepEqual(fixture.attempts, [0, 1, 2], 'progress uses the existing attempts, without another search cycle');
  assert.equal(fixture.bag[0].count, 1);
  assert.equal(fixture.removed.size, 7, 'six SDK-planned access blocks and the actual ore');
});

test('navigation without progress still excludes the target and terminates', async () => {
  const fixture = partialOreApproach({ advance: false });
  await assert.rejects(fixture.collect(), error => error.code === 'RESOURCE_NOT_FOUND' && error.details.attempts === 4);
  assert.equal(fixture.navigations(), 1);
  assert.deepEqual(fixture.bag, []);
  assert.equal(fixture.removed.size, 0);
});

test('action cancellation stops a partial approach before another navigation', async () => {
  const fixture = partialOreApproach({ abort: true });
  await assert.rejects(fixture.collect(), error => error.code === 'BUDGET_EXHAUSTED');
  assert.equal(fixture.navigations(), 1);
  assert.deepEqual(fixture.bag, []);
});
