import assert from 'node:assert/strict';
import test from 'node:test';
import { EventEmitter } from 'node:events';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import Vec3 from 'vec3';
import pathfinderPkg from 'mineflayer-pathfinder';
import minecraftData from 'minecraft-data';
import prismarineBlock from 'prismarine-block';
import sdkGoto from 'mineflayer-pathfinder/lib/goto.js';

import * as collection from '../src/collection.js';

const {
  collectionBlockKey,
  collectionDigTimeoutMs,
  createCollectionBlockMatcher,
  digCollectionBlock,
  findCollectionTarget,
  incompleteCollectionError,
  isCollectionFluidHazard,
  isPreparedObsidianTarget,
  obsidianWorkMinimumY,
  isCollectionBlockStillPresent,
  isRecoverableCollectionDigError,
  collectionResourceMutation,
  stopCollectionMovement,
  waitForCollectionMovementToSettle,
} = collection;

test('collection approach requires an exposed reachable face rather than proximity through dirt', () => {
  const target = { position: new Vec3(29, 61, 96) };
  const standing = new Vec3(29, 64, 96);
  let obstruction = new Vec3(29, 63, 96);
  const bot = { world: { raycast: () => ({ position: obstruction }) } };
  assert.equal(new pathfinderPkg.goals.GoalNear(29, 61, 96, 3).isEnd(standing), true);
  const goal = collection.collectionApproachGoal(bot, target);
  assert.equal(goal.isEnd(standing), false);
  obstruction = target.position;
  assert.equal(goal.isEnd(standing), true);
});

test('buried target access can be planned before its current-world visibility becomes true', () => {
  const target = { name: 'gravel', position: new Vec3(8, 58, 79) };
  const contact = new Vec3(8, 59, 79);
  let obstruction = new Vec3(8, 59, 79);
  const bot = { world: { raycast: () => ({ position: obstruction }) } };
  const visibility = collection.collectionApproachGoal(bot, target);
  const excavation = collection.collectionExcavationGoal(target);
  assert.equal(visibility.isEnd(contact), false);
  assert.equal(excavation.isEnd(contact), true);
  assert.equal(excavation.isEnd(new Vec3(8, 60, 79)), false);
  obstruction = target.position;
  assert.equal(visibility.isEnd(contact), true);
});

test('surface wood uses visible reach without forcing a climb into the tree', () => {
  const target = { name: 'oak_log', position: new Vec3(0, 68, 0) };
  const standing = new Vec3(3, 64, 0);
  const bot = { world: { raycast: (origin, _direction, range) => {
    assert.equal(range, 4.5, 'actual survival reach must not increase');
    return origin.distanceTo(target.position.offset(0.5, 0.5, 0.5)) <= range ? target : null;
  } }, entity: { eyeHeight: 1.62 } };
  assert.equal(collection.collectionApproachGoal(bot, target).isEnd(standing), true);
  assert.equal(collection.collectionApproachGoal(bot, target).isEnd(new Vec3(7, 64, 0)), false);
  assert.equal(new pathfinderPkg.goals.GoalGetToBlock(0, 68, 0).isEnd(standing), false);
  assert.equal(collection.collectionExcavationGoal(target), null);
  assert.ok(collection.collectionExcavationGoal({ name: 'iron_ore', position: target.position }));
});

test('real SDK rejects a jump onto leaf support but keeps a solid one-block ascent', () => {
  const registry = minecraftData('1.21');
  const Block = prismarineBlock(registry);
  let support = 'oak_leaves';
  const bot = {
    registry, game: { minY: -64 }, entity: { effects: {} },
    inventory: { items: () => [] }, pathfinder: { bestHarvestTool: () => null },
    blockAt(position) {
      const name = position.y < 64 ? 'stone'
        : position.equals(new Vec3(1, 64, 0)) ? support : 'air';
      const block = Block.fromStateId(registry.blocksByName[name].defaultState);
      block.position = position;
      return block;
    },
  };
  const movements = collection.configureDryNavigation(new pathfinderPkg.Movements(bot), bot);
  const node = { x: 0, y: 64, z: 0, remainingBlocks: 0 };
  const canopy = [];
  movements.getMoveJumpUp(node, { x: 1, z: 0 }, canopy);
  assert.deepEqual(canopy, []);
  support = 'stone';
  const ground = [];
  movements.getMoveJumpUp(node, { x: 1, z: 0 }, ground);
  assert.equal(ground[0]?.y, 65);
});

test('ordinary digging cannot remove support over a long fall, including a canopy leaf', async () => {
  const bot = {
    entity: { position: new Vec3(0.5, 93, 0.5) },
    blockAt: position => ({ name: position.y < 86 ? 'stone' : 'air', position,
      boundingBox: position.y < 86 ? 'block' : 'empty' }),
    dig: () => assert.fail('must not remove the only support over a seven-block drop'),
  };
  await assert.rejects(digCollectionBlock(bot, { name: 'oak_leaves', position: new Vec3(0, 92, 0) }),
    error => error.code === 'UNSAFE_AREA' && error.reason_code === 'UNSUPPORTED_DROP');
  const oneStep = { name: 'stone', position: new Vec3(0, 86, 0) };
  bot.entity.position.y = 87;
  assert.equal(collection.collectionDigSafety(bot, oneStep).safe, true);
});

test('collection pickup ignores unrelated loot and items without decoded metadata', () => {
  const bot = { entity: { position: { x: 0, y: 64, z: 0 } }, entities: {
    1: { name: 'item', position: { x: 1, y: 64, z: 0 }, getDroppedItem: () => ({ name: 'stick' }) },
    2: { name: 'item', position: { x: 2, y: 64, z: 0 }, getDroppedItem: () => ({ name: 'oak_log' }) },
    3: { name: 'item', position: { x: 1, y: 64, z: 1 }, getDroppedItem: () => null },
    4: { name: 'item', position: { x: 2, y: 64, z: 1 }, getDroppedItem: () => ({ name: 'flint' }) },
  } };
  assert.deepEqual(collection.findPickupItemEntities(bot, 20, 'minecraft:oak_log').map(row => row.entity), [bot.entities[2]]);
  assert.deepEqual(collection.findPickupItemEntities(bot, 20, ['gravel', 'flint']).map(row => row.entity), [bot.entities[4]]);
  assert.equal(collection.findPickupItemEntities(bot).length, 4);
});

test('pickup chooses a safe edge close to the drop instead of close to the bot', () => {
  const bot = {
    entity: { position: new Vec3(2.5, 64, 0.5) },
    blockAt(position) {
      const water = position.x === 0 && position.z === 0 && [63, 64].includes(position.y);
      const name = water ? 'water' : position.y < 64 ? 'stone' : 'air';
      return { name, boundingBox: name === 'stone' ? 'block' : 'empty', position };
    },
  };
  const item = new Vec3(0.25, 63, 0.25);
  const standing = collection.pickupStandingPosition(bot, item);
  assert.ok(standing.distanceTo(item) < 1.5);
  assert.equal(collection.isSafeStandingPosition(bot, standing), true);
});

test('pickup height floor rejects a temporarily dry pit below the obsidian work surface', () => {
  const bot = {
    entity: { position: new Vec3(2.5, 64, 0.5) },
    blockAt(position) {
      const pit = position.x === 0 && position.z === 0 && position.y === 63;
      const name = position.y < 64 && !pit ? 'stone' : 'air';
      return { name, boundingBox: name === 'stone' ? 'block' : 'empty', position };
    },
  };
  const item = new Vec3(0.25, 63, 0.25);
  assert.equal(collection.pickupStandingPosition(bot, item).y, 63);
  assert.equal(collection.pickupStandingPosition(bot, item, { minimumY: 64 }).y, 64);
});

test('safe pickup waits at a supported edge for a delayed floating item', async () => {
  const entity = { name: 'item', position: new Vec3(1.5, 64, 0.5), getDroppedItem: () => ({ name: 'obsidian' }) };
  const bot = {
    entity: { position: new Vec3(3.5, 64, 0.5) }, entities: { 1: entity },
    blockAt: position => ({ name: position.y < 64 ? 'stone' : 'air', boundingBox: position.y < 64 ? 'block' : 'empty', position }),
    setControlState() {},
  };
  bot.pathfinder = { async goto(goal) { bot.entity.position = new Vec3(goal.x + 0.5, goal.y, goal.z + 0.5); }, stop() {} };
  let elapsed = 0;
  const outcome = await collection.safePickupDroppedItems(bot, {
    GoalNear: pathfinderPkg.goals.GoalNear, itemName: 'obsidian', nowMs: () => elapsed,
    waitMs: async ms => { elapsed += ms; if (elapsed >= 1500) delete bot.entities[1]; },
  });
  assert.equal(outcome.navigations, 1);
  assert.equal(bot.entities[1], undefined);
  assert.ok(elapsed >= 1500 && elapsed < 8000);
});

function targetedPickupFixture(itemName = 'crafting_table') {
  const bag = [];
  const bot = new EventEmitter();
  bot.inventory = Object.assign(new EventEmitter(), { items: () => bag });
  bot.entity = { position: new Vec3(0.5, 64, 0.5) };
  const drop = (name, x) => ({ name: 'item', position: new Vec3(x, 64, 0.5), getDroppedItem: () => ({ name }) });
  bot.entities = { 1: drop('birch_sapling', 1.5), 2: drop(itemName, 4.5) };
  bot.blockAt = position => ({ name: position.y < 64 ? 'stone' : 'air',
    boundingBox: position.y < 64 ? 'block' : 'empty', position });
  bot.setControlState = () => {};
  const original = {};
  const goals = [];
  bot.pathfinder = { movements: original, setMovements(value) { this.movements = value; },
    stop() {}, setGoal() {}, async goto(goal) { goals.push(goal); delete bot.entities[2]; } };
  let elapsed = 0;
  const options = { itemName, minimumInventoryCount: 1,
    fallbackPos: new Vec3(4, 64, 0), GoalNear: pathfinderPkg.goals.GoalNear,
    movements: {}, nowMs: () => elapsed, waitMs: async ms => { elapsed += ms; } };
  return { bot, bag, original, goals, options };
}

test('targeted pickup skips a recovered workstation instead of chasing saplings or fallback', async () => {
  const fixture = targetedPickupFixture();
  fixture.bag.push({ name: 'crafting_table', count: 1 });
  const result = await collection.safePickupDroppedItems(fixture.bot, fixture.options);
  assert.equal(result.navigations, 0);
  assert.deepEqual(fixture.goals, []);
  assert.equal(fixture.bot.pathfinder.movements, fixture.original);
});

test('ore pickup skips the old landing spot when the mined drop already entered inventory', async () => {
  const { bot, bag, goals, options } = targetedPickupFixture('raw_iron');
  bag.push({ name: 'raw_iron', count: 2 });
  const minimumInventoryCount = collection.pickupInventoryCount(bot, options.itemName) + 1;
  bag.push({ name: 'minecraft:raw_iron', count: 1 });
  const result = await collection.safePickupDroppedItems(bot, { ...options, minimumInventoryCount });
  assert.equal(result.navigations, 0);
  assert.deepEqual(goals, []);
});

test('ore pickup clears an active goal as soon as the new drop enters inventory', async () => {
  const { bot, bag, options } = targetedPickupFixture('raw_iron');
  bag.push({ name: 'raw_iron', count: 2 });
  const minimumInventoryCount = collection.pickupInventoryCount(bot, options.itemName) + 1;
  let hardStopped = false;
  let walkedPastPickup = false;
  bot.pathfinder.setGoal = goal => { if (goal === null) hardStopped = true; };
  bot.pathfinder.goto = async () => {
    assert.equal(hardStopped, false);
    bag[0].count += 1;
    bot.inventory.emit('updateSlot', 0, null, bag[0]);
    walkedPastPickup = !hardStopped;
  };
  const result = await collection.safePickupDroppedItems(bot, { ...options, minimumInventoryCount });
  assert.equal(result.navigations, 1);
  assert.equal(hardStopped, true);
  assert.equal(walkedPastPickup, false);
  assert.equal(result.path_failures, 0);
  assert.equal(bot.inventory.listenerCount('updateSlot'), 0);
});

test('gravel pickup needs a new gravel or flint item beyond their combined existing stock', async () => {
  const { bot, bag, options } = targetedPickupFixture('gravel');
  bag.push({ name: 'gravel', count: 2 }, { name: 'minecraft:flint', count: 4 },
    { name: 'raw_iron', count: 10 });
  const itemName = ['minecraft:gravel', 'flint'];
  const minimumInventoryCount = collection.pickupInventoryCount(bot, itemName) + 1;
  assert.equal(minimumInventoryCount, 7);
  let hardStopped = false;
  bot.pathfinder.setGoal = goal => { if (goal === null) hardStopped = true; };
  bot.pathfinder.goto = async () => {
    assert.equal(hardStopped, false, 'old flint stock must not satisfy a new pickup');
    bag[1].count += 1;
    bot.inventory.emit('updateSlot', 1, null, bag[1]);
    assert.equal(hardStopped, true);
  };
  const result = await collection.safePickupDroppedItems(bot, { ...options, itemName, minimumInventoryCount });
  assert.equal(result.navigations, 1);
  assert.equal(collection.pickupInventoryCount(bot, itemName), 7);
});

test('native collection passes the pre-dig inventory threshold to ordinary ore pickup', async () => {
  const { bot, bag, goals, options } = targetedPickupFixture('raw_iron');
  const ore = { name: 'iron_ore', type: 15, position: new Vec3(4, 64, 0) };
  bot.findBlock = () => ore;
  let dug = false;
  const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  const start = source.indexOf('async function _collectInner(');
  const end = source.indexOf('\nfunction craftError(', start);
  assert.ok(start >= 0 && end > start);
  // Execute the actual private native function without starting Mineflayer.
  const collect = runInNewContext(`(${source.slice(start, end)})`, {
    ...collection,
    bot,
    ITEM_TO_BLOCK: {},
    BLOCK_DROP_ITEM: { iron_ore: 'raw_iron' },
    resolveRequestedBlockName: () => 'iron_ore',
    resolveRequestedBlockNames: () => ['iron_ore'],
    shouldPrepareUndergroundCollection: () => null,
    collectionDigSafety: () => ({ safe: true }),
    collectionApproachGoal: () => ({ isEnd: () => true }),
    presentBlockTarget: async () => null,
    _stabilizePosition: async () => true,
    _collectDebug() {},
    _inventoryCount: item => collection.pickupInventoryCount(bot, item),
    _equipToolForBlock: async () => {},
    digCollectionBlock: async () => { dug = true; },
    operationWait: async ms => {
      if (dug && ms === 500) {
        bag.push({ name: 'raw_iron', count: 1 });
        delete bot.entities[2];
      }
    },
    _pickupDroppedItems: async (timeoutMs, fallbackPos, itemName, minimumY, minimumInventoryCount) => (
      collection.safePickupDroppedItems(bot, {
        ...options, timeoutMs, fallbackPos, itemName, minimumY, minimumInventoryCount,
      })
    ),
  });
  const result = await collect('iron_ore', 1, { blocksByName: { iron_ore: { id: 15 } } });
  assert.equal(result, 'Collected 1 iron_ore');
  assert.equal(dug, true);
  assert.equal(collection.pickupInventoryCount(bot, 'raw_iron'), 1);
  assert.deepEqual(goals, [], 'an automatically collected ore must not start an old fallback route');
});

test('targeted pickup stops an active route on inventory evidence and keeps the absolute threshold', async () => {
  const { bot, bag, original, options } = targetedPickupFixture();
  bag.push({ name: 'crafting_table', count: 1 });
  let stopped = false;
  let walkedPastPickup = false;
  const goals = [];
  bot.pathfinder.stop = () => { stopped = true; };
  bot.pathfinder.goto = async goal => {
    goals.push(goal);
    bag[0].count = 2;
    bot.inventory.emit('updateSlot', 0, null, bag[0]);
    if (stopped) throw new Error('path stopped');
    walkedPastPickup = true;
    bot.entity.position = new Vec3(goal.x + 0.5, goal.y, goal.z + 0.5);
  };
  const result = await collection.safePickupDroppedItems(bot, { ...options, minimumInventoryCount: 2 });
  assert.equal(walkedPastPickup, false);
  assert.equal(goals.length, 1);
  assert.equal(goals[0].x, 4, 'the closer sapling is not the requested workstation');
  assert.equal(result.path_failures, 0);
  assert.equal(bot.pathfinder.movements, original);
  assert.equal(bot.inventory.listenerCount('updateSlot'), 0);
  assert.equal(bot.listenerCount('move'), 0);
});

test('targeted pickup does not treat a vanished drop as inventory gain', async () => {
  const { bot, bag, goals, options } = targetedPickupFixture();
  await collection.safePickupDroppedItems(bot, options);
  assert.equal(bag.length, 0);
  assert.equal(goals.length, 2, 'the uncollected target still permits the one bounded fallback');
  assert.ok(goals.every(goal => goal.x === 4));
});

test('targeted pickup cancellation restores movements and removes completion listeners', async () => {
  const { bot, original, options } = targetedPickupFixture();
  const controller = new AbortController();
  bot.pathfinder.goto = async () => { controller.abort('operator stop'); throw new Error('stopped'); };
  await assert.rejects(collection.safePickupDroppedItems(bot, {
    ...options, context: { signal: controller.signal },
  }), error => error === 'operator stop');
  assert.equal(bot.pathfinder.movements, original);
  assert.equal(bot.inventory.listenerCount('updateSlot'), 0);
  assert.equal(bot.listenerCount('move'), 0);
});

test('targeted pickup settles the real SDK goto without waiting for another path step', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const { bot, bag, options } = targetedPickupFixture();
  let activeGoal;
  bot.pathfinder.goto = goal => sdkGoto(bot, goal);
  bot.pathfinder.setGoal = goal => {
    activeGoal = goal;
    bot.emit('goal_updated', goal);
    if (goal) queueMicrotask(() => {
      bag.push({ name: 'crafting_table', count: 1 });
      bot.inventory.emit('updateSlot', 0, null, bag[0]);
    });
  };
  // The installed SDK's stop() only sets a flag until another path step.
  bot.pathfinder.stop = () => {};
  const pending = collection.safePickupDroppedItems(bot, options);
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(activeGoal, null);
  t.mock.timers.tick(0);
  const result = await pending;
  assert.equal(result.path_failures, 0);
  assert.equal(result.navigations_succeeded, 0, 'inventory gain is distinct from reaching the old route goal');
  for (const event of ['goal_updated', 'goal_reached', 'path_stop', 'path_update', 'move']) {
    assert.equal(bot.listenerCount(event), 0);
  }
  assert.equal(bot.inventory.listenerCount('updateSlot'), 0);
});

test('obsidian mining switches from scaffold to diamond pickaxe before calculating dig duration', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const block = { name: 'obsidian', position: { x: 53, y: -55, z: 127 } };
  const bot = {
    heldItem: { name: 'cobblestone' },
    entity: { position: { x: 52, y: -54, z: 125 } },
    blockAt: () => ({ name: 'air', boundingBox: 'empty' }),
    inventory: { items: () => [{ name: 'iron_pickaxe' }, { name: 'diamond_pickaxe' }] },
    async equip(item) { this.heldItem = item; },
    digTime() { return this.heldItem.name === 'diamond_pickaxe' ? 9_400 : 250_000; },
    dig() { return new Promise((resolve) => setTimeout(() => resolve('dug'), this.digTime())); },
    stopDigging() {},
  };
  const pending = digCollectionBlock(bot, block).then((value) => value, (error) => error.code);
  await Promise.resolve();
  await Promise.resolve();
  t.mock.timers.tick(10_000);
  assert.equal(await pending, 'dug');
  assert.equal(bot.heldItem.name, 'diamond_pickaxe');
});

test('dig duration remains bounded and includes slow submerged obsidian mining', () => {
  assert.ok(collectionDigTimeoutMs({ digTime: () => 47_000 }, {}) > 47_000);
  assert.equal(collectionDigTimeoutMs({ digTime: () => 250_000 }, {}), 120_000);
});

test('real SDK obsidian digging applies pickaxe speed without changing registry blocks', async () => {
  const registry = minecraftData('1.21');
  const Block = prismarineBlock('1.21');
  for (const [tool, expected] of [['diamond_pickaxe', 9400], ['netherite_pickaxe', 8350]]) {
    const block = Block.fromStateId(registry.blocksByName.obsidian.defaultState);
    block.position = new Vec3(1, 63, 0);
    const material = block.material;
    const item = { name: tool, type: registry.itemsByName[tool].id };
    const bot = {
      registry,
      heldItem: item,
      entity: { position: new Vec3(0, 64, 0), onGround: true },
      inventory: { items: () => [item] },
      blockAt: () => ({ name: 'air' }),
      digTime: target => target.digTime(item.type, false, false, false),
      async dig(target) {
        assert.ok(target instanceof Block);
        assert.equal(bot.digTime(target), expected);
        assert.equal(target.position, block.position);
        return 'dug';
      },
    };
    assert.equal(await digCollectionBlock(bot, block), 'dug');
    assert.equal(block.material, material);
    assert.equal(registry.blocksByName.obsidian.material, material);
  }
});

test('obsidian collection refuses to dig without a harvest-capable pickaxe', async () => {
  await assert.rejects(digCollectionBlock({
    inventory: { items: () => [{ name: 'iron_pickaxe' }] },
    dig: () => assert.fail('obsidian must not be destroyed with an iron pickaxe'),
  }, { name: 'obsidian' }), (error) => error.code === 'TOOL_REQUIRED');
});

test('collection matcher admits palette entries before filtering positioned blocks', () => {
  const matcher = createCollectionBlockMatcher([42, 43], new Set(['2,19,130']));
  assert.equal(matcher({ type: 42 }), true);
  assert.equal(matcher({ type: 43 }), true);
  assert.equal(matcher({ type: 41 }), false);
  assert.equal(matcher({ type: 42, position: { x: 2, y: 19, z: 130 } }), false);
  assert.equal(matcher({ type: 42, position: { x: 2, y: 20, z: 130 } }), true);
});

test('obsidian discovery skips covered and unsafe targets while preserving SDK palette filtering', () => {
  const covered = { type: 170, name: 'obsidian', position: new Vec3(55, -55, 122) };
  const exposed = { ...covered, position: new Vec3(56, -55, 122) };
  const unsafe = { ...covered, position: new Vec3(57, -55, 122) };
  const unloaded = { ...covered, position: new Vec3(58, -55, 122) };
  let lookups = 0;
  const bot = {
    entity: { position: new Vec3(54, -54, 122) },
    blockAt(position) {
      lookups++;
      if (position.y === -54 && position.x === 58) return null;
      const name = position.y === -54 && [56, 57].includes(position.x) ? 'air'
        : position.x === 57 && position.y === -56 ? 'lava' : 'cobblestone';
      return { name, position, boundingBox: name === 'cobblestone' ? 'block' : 'empty' };
    },
  };
  const matches = createCollectionBlockMatcher(170, new Set(), block => isPreparedObsidianTarget(bot, block));
  assert.equal(matches({ type: 170 }), true);
  assert.equal(lookups, 0);
  assert.equal(matches(covered), false);
  assert.equal(matches(unsafe), false);
  assert.equal(matches(unloaded), false);
  assert.equal(matches(exposed), true);
});

test('obsidian work height permits one supported step down from a bank but excludes a flooded pit', () => {
  const floor = new Vec3(58, -55, 122);
  const pit = new Vec3(56, -56, 123);
  const bot = {
    entity: { position: new Vec3(57.5, -53, 122.5) },
    blockAt(position) {
      const name = position.equals(floor) || position.equals(pit) ? 'obsidian'
        : position.x === 56 && position.z === 123 ? 'water' : 'air';
      return { name, boundingBox: name === 'obsidian' ? 'block' : 'empty', position };
    },
  };
  assert.equal(obsidianWorkMinimumY(bot, [floor, pit]), -54);
  assert.equal(isPreparedObsidianTarget(bot, { position: floor }, -53), false);
  assert.equal(isPreparedObsidianTarget(bot, { position: floor }, -54), true);
  assert.equal(isPreparedObsidianTarget(bot, { position: pit }, -54), false);
  assert.equal(obsidianWorkMinimumY(bot, [pit]), -53);
  bot.entity.position.y = -54;
  assert.equal(obsidianWorkMinimumY(bot, [floor, pit]), -54);
});

test('ordinary ore collection also refuses a water breach before invoking dig', async () => {
  const bot = {
    blockAt: position => ({ name: position.x === 2 ? 'water' : 'stone' }),
    dig: () => assert.fail('must not open the aquifer'),
  };
  await assert.rejects(digCollectionBlock(bot, { name: 'iron_ore', position: { x: 1, y: 16, z: 0 } }),
    error => error.code === 'UNSAFE_AREA' && error.reason_code === 'FLUID_BREACH');
});

test('collection evidence charges partial work and removes event listeners', async () => {
  const bot = new EventEmitter();
  bot.entity = { position: { x: 0, y: 64, z: 0 } };
  bot.health = 20;
  const error = incompleteCollectionError('oak_log', 'oak_log', 4, 8);
  await assert.rejects(collection.withCollectionEvidence(bot, async (mutations) => {
    mutations.push(...Array.from({ length: 4 }, (_, ordinal) => ({ kind: 'block', ordinal })));
    bot.entity.position.x = 3;
    bot.emit('move');
    bot.entity.position.x = 0;
    bot.emit('move');
    bot.health = 19;
    bot.emit('health');
    throw error;
  }), (caught) => caught === error);
  assert.equal(error.budget_usage.max_actions, 1);
  assert.equal(error.budget_usage.max_blocks_changed, 4);
  assert.equal(error.budget_usage.max_travel_distance, 6);
  assert.equal(error.budget_usage.max_damage_taken, 1);
  assert.equal(error.explained_mutations.length, 4);
  assert.equal(bot.listenerCount('move'), 0);
  assert.equal(bot.listenerCount('health'), 0);
});

test('collection evidence counts native access excavation without double charging target annotations', async () => {
  const bot = new EventEmitter();
  bot.entity = { position: { x: 0, y: 64, z: 0 } };
  bot.health = 20;
  const target = { name: 'iron_ore', type: 15, position: { x: 1, y: 64, z: 0 } };
  const access = { name: 'stone', type: 1, position: { x: 1, y: 65, z: 0 } };
  const controller = new AbortController();
  await assert.rejects(collection.withCollectionEvidence(bot, async (mutations) => {
    for (const block of [access, target]) {
      const air = { name: 'air', type: 0, position: block.position };
      bot.emit('blockUpdate', block, air);
      bot.emit('diggingCompleted', air);
    }
    mutations.push(collection.collectionResourceMutation(target.name, target.position));
    controller.abort('budget guard stopped collection');
    controller.signal.throwIfAborted();
  }), error => {
    assert.equal(error.budget_usage.max_blocks_changed, 2);
    assert.equal(error.explained_mutations.length, 2);
    assert.equal(error.budget_usage.max_actions, 1);
    return true;
  });
  assert.equal(bot.listenerCount('diggingCompleted'), 0);
  assert.equal(bot.listenerCount('blockUpdate'), 0);
});

test('collection settlement rejects an apparently grounded position inside water', () => {
  const position = { floored: () => ({ x: 2, y: 58, z: 64 }) };
  const bot = {
    entity: { position, onGround: true, velocity: { x: 0, y: 0, z: 0 } },
    blockAt: () => ({ name: 'water' }),
  };

  assert.equal(isCollectionFluidHazard(bot), true);
});

test('zero-progress collection reports resource absence instead of missing drops', () => {
  const diagnostics = { search_failures: [{ stage: 'navigate', message: 'no path' }] };
  const error = incompleteCollectionError('oak_log', 'oak_log', 0, 8, diagnostics);

  assert.equal(error.code, 'RESOURCE_NOT_FOUND');
  assert.equal(error.collected, 0);
  assert.equal(error.requested, 8);
  assert.match(error.message, /No reachable oak_log/);
  assert.deepEqual(error.details.search_failures, diagnostics.search_failures);
});

test('productive incomplete collection keeps partial-drop recovery metadata', () => {
  const error = incompleteCollectionError('stone', 'cobblestone', 15, 16);

  assert.equal(error.code, 'PARTIAL_COLLECT');
  assert.equal(error.collected, 15);
  assert.equal(error.requested, 16);
  assert.match(error.reason, /inventory gained 15 cobblestone/);
});

test('collection cleanup stops pathfinding and clears every movement control', () => {
  let pathfinderStops = 0;
  const controls = [];
  const bot = {
    pathfinder: { stop: () => { pathfinderStops += 1; } },
    setControlState: (control, state) => controls.push([control, state]),
  };

  stopCollectionMovement(bot);

  assert.equal(pathfinderStops, 1);
  assert.deepEqual(controls, [
    ['forward', false],
    ['back', false],
    ['left', false],
    ['right', false],
    ['jump', false],
    ['sprint', false],
    ['sneak', false],
  ]);
});

test('collection cleanup waits for grounded position stability after stopping navigation', async () => {
  let now = 0;
  let pathfinderStops = 0;
  const samples = [
    { position: { x: 0, y: 62, z: 0 }, onGround: false, velocity: { x: 0, y: -0.2, z: 0 } },
    { position: { x: 0, y: 61, z: 0 }, onGround: false, velocity: { x: 0, y: -0.1, z: 0 } },
    { position: { x: 0, y: 60, z: 0 }, onGround: true, velocity: { x: 0, y: 0, z: 0 } },
    { position: { x: 0, y: 60, z: 0 }, onGround: true, velocity: { x: 0, y: 0, z: 0 } },
    { position: { x: 0, y: 60, z: 0 }, onGround: true, velocity: { x: 0, y: 0, z: 0 } },
  ];
  let sampleIndex = 0;
  const bot = {
    pathfinder: { stop: () => { pathfinderStops += 1; } },
    setControlState: () => {},
    get entity() { return samples[Math.min(sampleIndex, samples.length - 1)]; },
  };

  const settled = await waitForCollectionMovementToSettle(bot, {
    timeoutMs: 1_000,
    pollMs: 100,
    stableSamples: 3,
    nowMs: () => now,
    waitMs: async (delayMs) => {
      now += delayMs;
      sampleIndex += 1;
    },
  });

  assert.equal(settled, true);
  assert.ok(pathfinderStops >= 1);
});

test('collection dig returns the completed Mineflayer result', async () => {
  const block = { name: 'iron_ore', position: { x: 1, y: 2, z: 3 } };
  const bot = {
    blockAt: () => ({ name: 'air', boundingBox: 'empty' }),
    dig: async (target) => {
      assert.equal(target, block);
      return 'dug';
    },
    stopDigging: () => assert.fail('successful dig must not be stopped'),
  };

  assert.equal(await digCollectionBlock(bot, block, 50), 'dug');
});

test('collection evidence identifies the exact mined block instance', () => {
  assert.deepEqual(
    collectionResourceMutation(
      'minecraft:copper_ore',
      { x: 20, y: 63, z: 20 },
      'minecraft:overworld',
    ),
    {
      kind: 'block',
      subject: 'block:minecraft:overworld:20:63:20',
      delta: -1,
      details: { block_type: 'minecraft:copper_ore' },
    },
  );
});

test('collection dig bounds a stalled Mineflayer action and stops it', async () => {
  let stops = 0;
  const block = { name: 'iron_ore', position: { x: 4, y: 5, z: 6 } };
  const bot = {
    blockAt: () => ({ name: 'air', boundingBox: 'empty' }),
    heldItem: { name: 'diamond_pickaxe' },
    entity: { onGround: false, effects: {} },
    _getBlockAtEyeLevel: () => ({ name: 'water' }),
    digTime: () => 235_000,
    dig: async () => new Promise(() => {}),
    stopDigging: () => {
      stops += 1;
    },
  };

  await assert.rejects(
    digCollectionBlock(bot, block, 5),
    (error) => {
      assert.equal(error.code, 'COLLECT_FAILED');
      assert.equal(error.operation, 'dig');
      assert.deepEqual(error.details.dig_context, {
        expected_duration_ms: 235_000,
        timeout_ms: 5,
        held_item: 'diamond_pickaxe',
        on_ground: false,
        eye_block: 'water',
        effects: [],
        target_after: 'air',
      });
      return true;
    },
  );
  assert.equal(stops, 1);
});

test('collection matcher excludes an unreachable block while accepting another block of the same type', () => {
  const unreachable = { type: 15, position: { x: 4, y: 5, z: 6 } };
  const reachable = { type: 15, position: { x: 7, y: 8, z: 9 } };
  const excluded = new Set([collectionBlockKey(unreachable)]);
  const matches = createCollectionBlockMatcher(15, excluded);

  assert.equal(matches(unreachable), false);
  assert.equal(matches(reachable), true);
  assert.equal(matches({ type: 16, position: reachable.position }), false);
});

test('collection matcher accepts every registered block variant', () => {
  const matches = createCollectionBlockMatcher([15, 16]);

  assert.equal(matches({ type: 15, position: { x: 1, y: -54, z: 1 } }), true);
  assert.equal(matches({ type: 16, position: { x: 2, y: -54, z: 1 } }), true);
  assert.equal(matches({ type: 17, position: { x: 3, y: -54, z: 1 } }), false);
});

test('collection target lookup never returns an excluded discovery', () => {
  const unreachable = { type: 15, position: { x: 4, y: 5, z: 6 } };
  const reachable = { type: 15, position: { x: 7, y: 8, z: 9 } };
  const seenMatchers = [];
  const bot = {
    findBlock: ({ matching }) => {
      seenMatchers.push(matching);
      return [unreachable, reachable].find((block) => matching(block)) ?? null;
    },
  };

  assert.equal(
    findCollectionTarget(bot, 15, 32, new Set([collectionBlockKey(unreachable)])),
    reachable,
  );
  assert.equal(typeof seenMatchers[0], 'function');
});

test('collection treats an exhausted digging-aborted retry as a recoverable target failure', () => {
  assert.equal(isRecoverableCollectionDigError(new Error('Digging aborted')), true);
  assert.equal(isRecoverableCollectionDigError({ code: 'COLLECT_FAILED' }), true);
  assert.equal(isRecoverableCollectionDigError(new Error('permission denied')), false);
});

test('collection verifies a timed-out dig at the exact target coordinate', () => {
  const target = { type: 15, position: { x: 29, y: 15, z: -2 } };
  const bot = {
    blockAt(position) {
      assert.equal(position, target.position);
      return target;
    },
  };

  assert.equal(isCollectionBlockStillPresent(bot, target), true);
  assert.equal(
    isCollectionBlockStillPresent(
      { blockAt: () => ({ type: 1, position: target.position }) },
      target,
    ),
    false,
  );
});

test('registered underground resources retry structured search after a soft miss', () => {
  assert.equal(typeof collection.shouldRetryStructuredResourceSearch, 'function');
  const { shouldRetryStructuredResourceSearch } = collection;
  assert.equal(
    shouldRetryStructuredResourceSearch('iron_ore', { code: 'RESOURCE_NOT_FOUND' }),
    true,
  );
  assert.equal(
    shouldRetryStructuredResourceSearch('iron_ore', { code: 'SEARCH_TIMEOUT' }),
    true,
  );
  assert.equal(
    shouldRetryStructuredResourceSearch('oak_log', { code: 'RESOURCE_NOT_FOUND' }),
    false,
  );
  assert.equal(
    shouldRetryStructuredResourceSearch('iron_ore', { code: 'UNSAFE_AREA' }),
    false,
  );
});

test('underground collection prepares a bounded shaft only for resources with a target layer', () => {
  assert.equal(typeof collection.getUndergroundCollectionPreparation, 'function');
  const { getUndergroundCollectionPreparation } = collection;
  assert.deepEqual(getUndergroundCollectionPreparation('stone', 24), {
    targetY: 50,
    minimumCobblestone: 24,
  });
  assert.deepEqual(getUndergroundCollectionPreparation('iron_ore', 13), {
    targetY: 16,
    minimumCobblestone: 0,
  });
  assert.equal(getUndergroundCollectionPreparation('coal_ore', 5), null);
});

test('visible discovered ore is collected in place before any underground preparation', () => {
  assert.equal(typeof collection.shouldPrepareUndergroundCollection, 'function');
  const { shouldPrepareUndergroundCollection } = collection;

  assert.equal(
    shouldPrepareUndergroundCollection('iron_ore', 1, 63, true),
    null,
  );
  assert.deepEqual(
    shouldPrepareUndergroundCollection('iron_ore', 1, 63, false),
    { targetY: 16, minimumCobblestone: 0 },
  );
});

test('buried gravel uses its observed layer without inventing a blind descent target', () => {
  const { shouldPrepareUndergroundCollection } = collection;
  assert.equal(shouldPrepareUndergroundCollection('gravel', 1, 62, false), null);
  assert.deepEqual(shouldPrepareUndergroundCollection('gravel', 1, 62, false, 58), {
    targetY: 60, minimumCobblestone: 0,
  });
  assert.equal(shouldPrepareUndergroundCollection('gravel', 1, 62, true, 58), null);
  assert.equal(shouldPrepareUndergroundCollection('gravel', 1, 60, false, 58), null);
  assert.equal(shouldPrepareUndergroundCollection('oak_log', 1, 62, false, 30), null);
});

test('observed safe underground layer overrides the blind registry default for iron', () => {
  const { getUndergroundCollectionPreparation, shouldPrepareUndergroundCollection } = collection;

  assert.deepEqual(getUndergroundCollectionPreparation('iron_ore', 7, 30), {
    targetY: 32,
    minimumCobblestone: 0,
  });
  assert.deepEqual(shouldPrepareUndergroundCollection('iron_ore', 7, 40, false, 30), {
    targetY: 32,
    minimumCobblestone: 0,
  });
  // Already at or below the prepared layer: no climb, no preparation.
  assert.equal(shouldPrepareUndergroundCollection('iron_ore', 7, 32, false, 30), null);
  // A nearby visible target still suppresses preparation entirely.
  assert.equal(shouldPrepareUndergroundCollection('iron_ore', 7, 40, true, 30), null);
  // Without observation the registry defaults remain untouched.
  assert.deepEqual(getUndergroundCollectionPreparation('iron_ore', 7), {
    targetY: 16,
    minimumCobblestone: 0,
  });
  // Deep-ore observations are honored too; no iron-only special case.
  assert.deepEqual(getUndergroundCollectionPreparation('diamond_ore', 1, -51), {
    targetY: -49,
    minimumCobblestone: 0,
  });
});

test('collection evidence counts SDK-confirmed placements and not raw server block updates', async () => {
  const bot = new EventEmitter();
  bot.entity = { position: { x: 0, y: 64, z: 0 } };
  bot.health = 20;
  const position = { x: 5, y: 60, z: -3 };
  const evidence = await collection.withCollectionEvidence(bot, async () => {
    bot.emit('blockPlaced', { name: 'air', type: 0, position },
      { name: 'cobblestone', type: 1, position });
    bot.emit('blockUpdate', { name: 'air', type: 0, position: { x: 6, y: 60, z: -3 } },
      { name: 'cobblestone', type: 1, position: { x: 6, y: 60, z: -3 } });
  });
  assert.deepEqual(evidence.explained_mutations, [{
    kind: 'block',
    subject: 'block:minecraft:overworld:5:60:-3',
    delta: 1,
    details: { block_type: 'minecraft:cobblestone' },
  }]);
  assert.equal(evidence.budget_usage.max_blocks_changed, 1);
  assert.equal(bot.listenerCount('blockPlaced'), 0);
});

test('placement annotations merge with confirmed native placements event by event', async () => {
  const bot = new EventEmitter();
  bot.entity = { position: { x: 0, y: 64, z: 0 } };
  bot.health = 20;
  const evidence = await collection.withCollectionEvidence(bot, async (mutations) => {
    for (const position of [{ x: 1, y: -50, z: 2 }, { x: 1, y: -49, z: 2 }]) {
      bot.emit('blockPlaced', { name: 'air', type: 0, position },
        { name: 'cobblestone', type: 1, position });
      mutations.push(collectionResourceMutation('cobblestone', position, 'minecraft:overworld', 1));
    }
    // An annotation without a confirming native event stays attributed.
    mutations.push(collectionResourceMutation('cobblestone', { x: 1, y: -50, z: 2 }, 'minecraft:overworld', 1));
  });
  assert.deepEqual(evidence.explained_mutations.map(({ subject, delta }) => ({ subject, delta })), [
    { subject: 'block:minecraft:overworld:1:-50:2', delta: 1 },
    { subject: 'block:minecraft:overworld:1:-49:2', delta: 1 },
    { subject: 'block:minecraft:overworld:1:-50:2', delta: 1 },
  ]);
  assert.equal(evidence.budget_usage.max_blocks_changed, 3);
});

test('same-position place, break, and re-place each count once on an abort receipt', async () => {
  const bot = new EventEmitter();
  bot.entity = { position: { x: 0, y: 64, z: 0 } };
  bot.health = 20;
  const position = { x: -16, y: 30, z: 7 };
  const controller = new AbortController();
  await assert.rejects(collection.withCollectionEvidence(bot, async () => {
    bot.emit('blockPlaced', { name: 'air', type: 0, position },
      { name: 'cobblestone', type: 1, position });
    bot.emit('blockUpdate', { name: 'cobblestone', type: 1, position },
      { name: 'air', type: 0, position });
    bot.emit('diggingCompleted', { name: 'air', type: 0, position });
    bot.emit('blockPlaced', { name: 'air', type: 0, position },
      { name: 'cobblestone', type: 1, position });
    controller.abort('budget guard stopped collection');
    controller.signal.throwIfAborted();
  }), (error) => {
    assert.ok(error instanceof Error);
    assert.equal(error.message, 'budget guard stopped collection');
    assert.deepEqual(error.explained_mutations.map(({ subject, delta }) => ({ subject, delta })), [
      { subject: 'block:minecraft:overworld:-16:30:7', delta: 1 },
      { subject: 'block:minecraft:overworld:-16:30:7', delta: -1 },
      { subject: 'block:minecraft:overworld:-16:30:7', delta: 1 },
    ]);
    assert.equal(error.budget_usage.max_blocks_changed, 3);
    return true;
  });
  assert.equal(bot.listenerCount('blockPlaced'), 0);
});
