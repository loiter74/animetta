import assert from 'node:assert/strict';
import test from 'node:test';
import { EventEmitter } from 'node:events';
import Vec3 from 'vec3';
import pathfinderPkg from 'mineflayer-pathfinder';
import minecraftData from 'minecraft-data';
import blockLoader from 'prismarine-block';
import WorldSync from 'prismarine-world/src/worldsync.js';
import { fillWaterBucket, isWaterSource, prepareObsidian } from '../src/water.js';
import { configureDryNavigation, digCollectionBlock, isSafeStandingPosition, restrictNavigationHeight, safePickupDroppedItems } from '../src/collection.js';

function waterBot() {
  const bot = new EventEmitter();
  bot.health = 20;
  bot.entity = { position: new Vec3(0.5, 64, 0.5), onGround: true };
  bot.registry = { blocksByName: { water: { id: 1 }, obsidian: { id: 2 } } };
  bot.items = [{ name: 'bucket', count: 1 }];
  bot.inventory = { items: () => bot.items };
  bot.world = { raycast: () => null };
  bot.findBlocks = () => [new Vec3(2, 64, 0)];
  bot.blockAt = position => ({
    name: position.y < 64 ? 'stone' : position.equals(new Vec3(2, 64, 0)) ? 'water' : 'air',
    boundingBox: position.y < 64 ? 'block' : 'empty',
    metadata: 0,
    position,
  });
  bot.equip = async () => {};
  bot.lookAt = async () => {};
  bot.activateItem = () => { bot.items = [{ name: 'water_bucket', count: 1 }]; };
  bot.deactivateItem = () => {};
  return bot;
}

test('survival navigation excludes submerged heads and unsupported water, while allowing shallow water', () => {
  const bot = waterBot();
  bot.registry = minecraftData('1.21');
  const movements = configureDryNavigation(new pathfinderPkg.Movements(bot), bot);
  assert.equal(movements.exclusionStep(bot.blockAt(new Vec3(2, 64, 0))), 0);
  assert.equal(movements.exclusionStep(bot.blockAt(new Vec3(2, 63, 0))), Infinity);
  bot.blockAt = position => ({ name: position.y === 64 ? 'water' : 'air', boundingBox: 'empty', position });
  assert.equal(movements.exclusionStep(bot.blockAt(new Vec3(2, 64, 0))), Infinity);
  assert.equal(movements.maxDropDown, 2);
});

test('real SDK downward edges cannot bypass dry landing and maximum drop checks', () => {
  const registry = minecraftData('1.21.1');
  const Block = blockLoader(registry);
  const bot = waterBot();
  bot.registry = registry;
  bot.game = { minY: -64 };
  bot.blockAt = position => {
    const name = position.y >= 63 ? 'air' : position.y >= 57 ? 'water' : 'stone';
    const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
    block.position = position;
    return block;
  };
  const movements = new pathfinderPkg.Movements(bot);
  movements.maxDropDown = 1;
  const node = { x: 0, y: 64, z: 0, remainingBlocks: 0 };
  const legacy = [];
  movements.getMoveDown(node, legacy);
  assert.equal(legacy[0].y, 62);
  configureDryNavigation(movements, bot);
  const guarded = [];
  movements.getMoveDown(node, guarded);
  movements.getMoveDropDown(node, { x: 1, z: 0 }, guarded);
  assert.deepEqual(guarded, []);
  bot.pathfinder = { bestHarvestTool: () => null };
  bot.blockAt = position => {
    const block = Block.fromStateId(registry.blocksByName[position.y < 64 ? 'stone' : 'air'].defaultState, 0);
    block.position = position;
    return block;
  };
  const dryStep = [];
  movements.getMoveDown(node, dryStep);
  assert.equal(dryStep[0]?.y, 63, 'a supported one-block descent must remain possible');
  assert.deepEqual(dryStep[0].toBreak, [new Vec3(0, 63, 0)]);
  restrictNavigationHeight(movements, 64);
  assert.equal(movements.getLandingBlock(node, { x: 1, z: 0 }), null);
});

test('water fill needs actual source and inventory confirmation, and is idempotent', async () => {
  assert.equal(isWaterSource({ name: 'water', metadata: 1 }), false);
  assert.equal(isWaterSource({ name: 'water', getProperties: () => ({ level: 0 }) }), true);
  const bot = waterBot();
  const result = await fillWaterBucket(bot);
  assert.equal(result.output.filled, true);
  assert.equal(result.budget_usage.max_blocks_changed, 1);
  assert.equal(result.explained_mutations[0].details.block_type, 'minecraft:water');
  bot.findBlocks = () => assert.fail('already full bucket must not search');
  assert.equal((await fillWaterBucket(bot)).output.already_present, true);
});

test('real SDK water level strings distinguish static sources from flowing water', () => {
  const registry = minecraftData('1.21.1');
  const Block = blockLoader(registry);
  const { minStateId, maxStateId } = registry.blocksByName.water;
  const source = Block.fromStateId(minStateId, 0);
  assert.equal(source.getProperties().level, '0');
  assert.equal(isWaterSource(source), true);
  for (let stateId = minStateId + 1; stateId <= maxStateId; stateId++) {
    assert.equal(isWaterSource(Block.fromStateId(stateId, 0)), false);
  }
});

test('water fill skips an inaccessible source and uses the next exposed shore source', async () => {
  const bot = waterBot();
  bot.registry = minecraftData('1.21.1');
  const buried = new Vec3(0, 40, 0);
  const shore = new Vec3(2, 64, 0);
  bot.findBlocks = () => [buried, shore];
  const blockAt = bot.blockAt;
  bot.blockAt = position => position.equals(buried)
    ? { name: 'water', boundingBox: 'empty', metadata: 0, position }
    : position.equals(buried.offset(0, 1, 0))
      ? { name: 'air', boundingBox: 'empty', position }
      : blockAt(position);
  const original = {};
  bot.pathfinder = {
    movements: original, setMovements(value) { this.movements = value; }, stop() {},
    async goto() { throw Object.assign(new Error('No dry route'), { name: 'NoPath' }); },
  };
  const result = await fillWaterBucket(bot);
  assert.equal(result.output.filled, true);
  assert.deepEqual(result.output.source, shore);
  assert.equal(bot.pathfinder.movements, original);
});

test('water fill aims above a real SDK shoreline obstruction and waits for ordinary look completion', async () => {
  const bot = waterBot();
  const registry = minecraftData('1.21.1');
  const Block = blockLoader(registry);
  const source = new Vec3(8, 62, 60);
  const bank = new Set(['9,62,61', '8,62,61', '9,62,60']);
  const world = new WorldSync(null);
  bot.world = world;
  world.getBlock = position => {
    const name = bank.has(`${position.x},${position.y},${position.z}`) ? 'grass_block' : 'air';
    const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
    block.position = position;
    return block;
  };
  bot.entity.position = new Vec3(10.5, 63, 63.5);
  const eye = bot.entity.position.offset(0, 1.62, 0);
  const center = source.offset(0.5, 0.5, 0.5).minus(eye);
  assert.equal(world.raycast(eye, center.scaled(1 / center.norm()), center.norm()).name, 'grass_block');
  bot.findBlocks = () => [source];
  bot.blockAt = position => ({
    name: position.equals(source) ? 'water' : position.y < 63 ? 'stone' : 'air',
    boundingBox: position.y < 63 && !position.equals(source) ? 'block' : 'empty',
    metadata: 0, position,
  });
  let aimed = false;
  bot.lookAt = async (point, force) => {
    assert.equal(force, false);
    const delta = point.minus(eye);
    assert.equal(world.raycast(eye, delta.scaled(1 / delta.norm()), delta.norm()), null);
    aimed = true;
  };
  bot.activateItem = () => {
    assert.equal(aimed, true);
    bot.items = [{ name: 'water_bucket', count: 1 }];
  };
  assert.equal((await fillWaterBucket(bot)).output.filled, true);
});

function sourceRayBot(position, source, solids = new Set(), floor = position.y) {
  const bot = waterBot();
  const registry = minecraftData('1.21.1');
  const Block = blockLoader(registry);
  bot.registry = registry;
  bot.entity.position = position;
  bot.findBlocks = () => [source];
  bot.blockAt = point => {
    const name = point.equals(source) ? 'water'
      : point.y < floor || solids.has(`${point.x},${point.y},${point.z}`) ? 'stone' : 'air';
    const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
    block.position = point;
    return block;
  };
  bot.world = new WorldSync(null);
  bot.world.getBlock = bot.blockAt;
  const fluidWorld = new WorldSync(null);
  fluidWorld.getBlock = point => {
    const block = bot.blockAt(point);
    // A source with air above has fluid height 1 - (level + 1) / 9.
    if (point.equals(source)) block.shapes = [[0, 0, 0, 1, 8 / 9, 1]];
    return block;
  };
  const ray = (world, target) => {
    const eye = bot.entity.position.offset(0, 1.62, 0);
    const delta = target.minus(eye);
    return world.raycast(eye, delta.scaled(1 / delta.norm()), delta.norm());
  };
  let target;
  bot.lookAt = async (point, force) => {
    assert.equal(force, false);
    target = point;
  };
  bot.activateItem = () => {
    if (ray(fluidWorld, target)?.position.equals(source)) {
      bot.items = [{ name: 'water_bucket', count: 1 }];
    }
  };
  const original = {};
  const goals = [];
  bot.pathfinder = {
    movements: original, setMovements(value) { this.movements = value; }, stop() {},
    async goto(goal) {
      goals.push(goal);
      assert.equal(isSafeStandingPosition(bot, new Vec3(goal.x, goal.y, goal.z)), true);
      bot.entity.position = new Vec3(goal.x + 0.5, goal.y, goal.z + 0.5);
    },
  };
  return { bot, ray, fluidWorld, goals, original };
}

test('low-eye water fill aims inside the source fluid instead of above its surface', async () => {
  const source = new Vec3(2, 63, 0);
  const { bot, ray, fluidWorld, goals } = sourceRayBot(new Vec3(0.5, 62, 0.5), source);
  assert.equal(ray(fluidWorld, source.offset(0.5, 0.99, 0.5)), null);
  assert.equal((await fillWaterBucket(bot, {}, { wait: async () => {} })).output.filled, true);
  assert.equal(goals.length, 0);
});

test('water fill leaves the R15 obstructed stance for a supported visible source approach', async () => {
  const source = new Vec3(-88, 55, 106);
  const solids = new Set(['-89,55,104', '-88,55,105', '-90,54,104']);
  const { bot, ray, fluidWorld, goals, original } = sourceRayBot(
    new Vec3(-89.5, 54, 103.60271738777713), source, solids,
  );
  assert.equal(ray(bot.world, source.offset(0.5, 0.99, 0.5)).name, 'stone');
  assert.equal(ray(fluidWorld, source.offset(0.5, 8 / 9 - 0.01, 0.5)).name, 'stone');
  assert.equal((await fillWaterBucket(bot, {}, { wait: async () => {} })).output.filled, true);
  assert.equal(goals.length, 1);
  assert.ok(Math.abs(goals[0].y - 54) <= 1, 'the visible stance is reachable by an ordinary step');
  assert.equal(bot.pathfinder.movements, original);
});

test('a bucket-use event without inventory change never reports filled', async () => {
  const bot = waterBot();
  bot.activateItem = () => {};
  await assert.rejects(fillWaterBucket(bot, {}, { wait: async () => {} }), error => error.code === 'WATER_FILL_UNCONFIRMED');
});

test('obsidian preparation must observe water after actual item use', async () => {
  const bot = waterBot();
  bot.items = [{ name: 'water_bucket', count: 1 }];
  let placed = false;
  bot.activateItem = () => { placed = true; };
  bot.blockAt = position => ({
    name: position.equals(new Vec3(2, 63, 0)) ? 'lava' : position.y < 64 ? 'stone'
      : position.equals(new Vec3(2, 64, 0)) ? 'obsidian'
        : placed && position.equals(new Vec3(2, 65, 0)) ? 'water' : 'air',
    boundingBox: position.y < 64 || position.equals(new Vec3(2, 64, 0)) ? 'block' : 'empty',
    position,
  });
  assert.equal((await prepareObsidian(bot, {}, { wait: async () => {} })).output.protected, true);
  placed = false;
  bot.activateItem = () => {};
  await assert.rejects(prepareObsidian(bot, {}, { wait: async () => {} }), error => error.code === 'WATER_PLACEMENT_UNCONFIRMED');
});

test('resumed obsidian preparation reuses verified water before choosing a nearer dry block', async () => {
  const bot = waterBot();
  const dry = new Vec3(1, 64, 0);
  const protectedBlock = new Vec3(2, 64, 0);
  bot.findBlocks = () => [dry, protectedBlock];
  bot.blockAt = position => {
    const name = position.equals(dry) || position.equals(protectedBlock) ? 'obsidian'
      : position.equals(protectedBlock.offset(0, 1, 0)) ? 'water'
        : position.y < 64 ? 'stone' : 'air';
    return { name, boundingBox: ['stone', 'obsidian'].includes(name) ? 'block' : 'empty', position };
  };
  bot.activateItem = () => assert.fail('existing water must be reused with the empty bucket');
  const result = await prepareObsidian(bot, {}, { wait: async () => {} });
  assert.deepEqual(result.output.water_position, protectedBlock.offset(0, 1, 0));
});

test('natural obsidian over solid rock needs no water, while adjacent lava still requires it', async () => {
  const bot = waterBot();
  const target = new Vec3(2, 64, 0);
  bot.findBlocks = () => [target];
  bot.blockAt = position => ({
    name: position.equals(target) ? 'obsidian' : position.y < 64 ? 'stone' : 'air',
    boundingBox: position.y < 64 || position.equals(target) ? 'block' : 'empty',
    position,
  });
  bot.activateItem = () => assert.fail('dry solid rock has no lava to cool');
  const result = await prepareObsidian(bot, {}, { wait: async () => {} });
  assert.equal(result.output.protected, true);
  assert.equal(result.output.natural_support, true);
  const blockAt = bot.blockAt;
  bot.blockAt = position => position.equals(target.offset(0, -1, 0))
    ? { name: 'lava', boundingBox: 'empty', position } : blockAt(position);
  await assert.rejects(prepareObsidian(bot, {}, { wait: async () => {} }), error => error.code === 'TOOL_REQUIRED');
});

test('obsidian preparation skips covered targets and can excavate a dry approach without mining obsidian', async () => {
  const bot = waterBot();
  bot.registry = minecraftData('1.21.1');
  bot.items = [{ name: 'water_bucket', count: 1 }];
  const covered = new Vec3(2, 64, 0);
  const target = new Vec3(32, 64, 0);
  let placed = false;
  bot.findBlocks = () => [covered, target];
  bot.blockAt = position => {
    const name = position.equals(covered) || position.equals(target) ? 'obsidian'
      : position.equals(covered.offset(0, 1, 0)) ? 'stone'
        : position.equals(target.offset(0, -1, 0)) ? 'lava'
        : position.equals(new Vec3(1, 64, 0)) || placed && position.equals(target.offset(0, 1, 0)) ? 'water'
          : position.y < 64 ? 'stone' : 'air';
    return { name, boundingBox: ['stone', 'obsidian'].includes(name) ? 'block' : 'empty', position };
  };
  const original = {};
  let navigationCalls = 0;
  bot.pathfinder = {
    movements: original, thinkTimeout: 5000,
    setMovements(value) { this.movements = value; },
    async goto(goal) {
      navigationCalls++;
      assert.equal(this.movements.canDig, true);
      assert.equal(this.movements.blocksCantBreak.has(bot.registry.blocksByName.obsidian.id), true);
      assert.equal(this.movements.exclusionBreak(bot.blockAt(new Vec3(1, 63, 0))), Infinity);
      if (navigationCalls === 1) {
        assert.ok(this.thinkTimeout >= 15000);
        bot.entity.position = new Vec3(goal.x - 1, goal.y, goal.z);
        throw Object.assign(new Error('local navigation window expired'), { code: 'ACTION_DEADLINE_EXPIRED' });
      }
      bot.entity.position = new Vec3(goal.x, goal.y, goal.z);
    },
    stop() {},
  };
  bot.activateItem = () => { placed = true; };
  const result = await prepareObsidian(bot, {}, { wait: async () => {} });
  assert.deepEqual(result.output.water_position, target.offset(0, 1, 0));
  assert.equal(bot.pathfinder.movements, original);
  assert.equal(bot.pathfinder.thinkTimeout, 5000);
  assert.equal(navigationCalls, 2);
});

test('obsidian beneath the bot and unprotected lava both prevent digging', async () => {
  const bot = waterBot();
  bot.items = [{ name: 'diamond_pickaxe', count: 1 }];
  bot.dig = () => assert.fail('unsafe obsidian must not be dug');
  await assert.rejects(digCollectionBlock(bot, { name: 'obsidian', position: new Vec3(0, 63, 0) }), error => error.reason_code === 'SUPPORT_BLOCK_UNDER_FEET');
  bot.blockAt = position => ({ name: position.y === 63 ? 'lava' : 'air', boundingBox: 'empty', position });
  await assert.rejects(digCollectionBlock(bot, { name: 'obsidian', position: new Vec3(2, 64, 0) }), error => error.reason_code === 'UNPROTECTED_LAVA');
});

test('unloaded headroom never qualifies as safe standing', () => {
  const bot = waterBot();
  bot.blockAt = position => position.y === 63 ? { name: 'stone', boundingBox: 'block' } : null;
  assert.equal(isSafeStandingPosition(bot, new Vec3(0, 64, 0)), false);
});

test('failed pickup paths never enable forward or sprint and restore movements', async () => {
  const bot = waterBot();
  bot.entities = { 1: { name: 'item', position: new Vec3(1.5, 64, 0.5) } };
  const original = {};
  bot.pathfinder = {
    movements: original,
    setMovements(value) { this.movements = value; },
    goto: async () => { throw new Error('no path'); }, stop() {},
  };
  bot.setControlState = (name, value) => assert.equal(value, false, `must not enable ${name}`);
  const result = await safePickupDroppedItems(bot, {
    GoalNear: class { constructor() {} }, movements: {}, waitMs: async () => {},
  });
  assert.equal(result.path_failures, 2);
  assert.equal(bot.pathfinder.movements, original);
});
