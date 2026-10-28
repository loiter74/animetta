import assert from 'node:assert/strict';
import test from 'node:test';
import { EventEmitter } from 'node:events';
import Vec3 from 'vec3';
import pathfinderPkg from 'mineflayer-pathfinder';
import minecraftData from 'minecraft-data';
import blockLoader from 'prismarine-block';
import WorldSync from 'prismarine-world/src/worldsync.js';
import ChunkLoader from 'prismarine-chunk';
import WorldLoader from 'prismarine-world';
import injectBlocks from 'mineflayer/lib/plugins/blocks.js';
import { fillWaterBucket, isWaterSource, prepareObsidian } from '../src/water.js';
import { configureDryNavigation, digCollectionBlock, isSafeStandingPosition, restrictNavigationHeight, safePickupDroppedItems } from '../src/collection.js';

function* directWaterPath(_movements, _start, goal) {
  const target = goal.goals[0];
  yield { result: { status: 'success', path: [new Vec3(target.x, target.y, target.z)] } };
}

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

function offsetShoreFixture(unsupportedArrival = false) {
  const bot = waterBot();
  bot.registry = minecraftData('1.21.1');
  bot.game = { minY: -64, height: 384 };
  bot.entity.position = new Vec3(8.5, 64, 0.5);
  bot.entity.velocity = new Vec3(0, 0, 0);
  bot.entity.effects = {};
  bot.entities = {};
  const Block = blockLoader(bot.registry), world = new WorldSync(null);
  const source = new Vec3(0, 62, 0);
  let arrival, facing, navigations = 0, activations = 0, scans = 0;
  world.getBlock = position => {
    const p = position.floored();
    const name = unsupportedArrival && arrival && p.equals(arrival.offset(0, -1, 0)) ? 'air'
      : p.y < 62 || (p.x >= 3 && p.y < 64) ? 'stone' : p.equals(source) ? 'water' : 'air';
    const block = Block.fromStateId(bot.registry.blocksByName[name].defaultState, 0);
    block.position = p;
    return block;
  };
  bot.world = world;
  bot.blockAt = position => world.getBlock(position.floored());
  bot.findBlocks = options => {
    scans++;
    assert.equal(options.maxDistance, 64);
    assert.equal(options.count, 512);
    return [source];
  };
  bot.controlState = {};
  bot.clearControlStates = () => { for (const key of Object.keys(bot.controlState)) bot.controlState[key] = false; };
  bot.setControlState = (key, value) => { bot.controlState[key] = value; };
  bot.lookAt = async point => { facing = point; };
  bot.activateItem = () => {
    activations++;
    const delta = source.offset(0.5, 8 / 9 - 0.01, 0.5).minus(bot.entity.position.offset(0, 1.62, 0));
    assert.ok(delta.norm() <= 4.25, 'the bucket is used only from the actual reachable eye position');
    bot.items = [{ name: 'water_bucket', count: 1 }];
  };
  pathfinderPkg.pathfinder(bot);
  bot.pathfinder.goto = async goal => {
    navigations++;
    arrival = new Vec3(goal.x, goal.y, goal.z);
    bot.entity.position = arrival.offset(0.9, 0, 0.9);
    assert.equal(goal.isEnd(bot.entity.position.floored()), true, 'SDK arrival still satisfies the original cell goal');
  };
  const wait = async ms => {
    // Controlled alignment movement; this fixture does not claim native physics.
    if (ms !== 50 || !bot.controlState.forward) return;
    assert.equal(bot.controlState.sneak, true);
    const delta = new Vec3(facing.x - bot.entity.position.x, 0, facing.z - bot.entity.position.z);
    bot.entity.position.add(delta.scaled(Math.min(0.06, delta.norm()) / delta.norm()));
  };
  return { bot, wait, counts: () => ({ navigations, activations, scans }) };
}

test('water fill centers an offset shore arrival before actual bucket interaction', async () => {
  const { bot, wait, counts } = offsetShoreFixture();
  const result = await fillWaterBucket(bot, {}, { wait });
  assert.equal(result.output.filled, true);
  assert.deepEqual(counts(), { navigations: 1, activations: 1, scans: 1 });
  assert.equal(Object.values(bot.controlState).some(Boolean), false);
});

test('water fill never aligns or uses the bucket after shore support disappears', async () => {
  const { bot, wait, counts } = offsetShoreFixture(true);
  await assert.rejects(fillWaterBucket(bot, {}, { wait }), { code: 'WATER_TARGET_UNREACHABLE' });
  assert.deepEqual(counts(), { navigations: 1, activations: 0, scans: 1 });
  assert.equal(Object.values(bot.controlState).some(Boolean), false);
});

test('water shore alignment stops on cancellation without another route or bucket use', async () => {
  const fixture = offsetShoreFixture();
  const controller = new AbortController();
  await assert.rejects(fillWaterBucket(fixture.bot, { signal: controller.signal }, {
    wait: async ms => {
      await fixture.wait(ms);
      if (ms === 50) controller.abort();
    },
  }), { name: 'AbortError' });
  assert.deepEqual(fixture.counts(), { navigations: 1, activations: 0, scans: 1 });
  assert.equal(Object.values(fixture.bot.controlState).some(Boolean), false);
});

test('water interaction rejects drift after aiming without repeating alignment or navigation', async () => {
  const fixture = offsetShoreFixture();
  const lookAt = fixture.bot.lookAt;
  fixture.bot.lookAt = async (point, force) => {
    await lookAt(point, force);
    if (force === false) fixture.bot.entity.position = fixture.bot.entity.position.floored().offset(0.9, 0, 0.9);
  };
  await assert.rejects(fillWaterBucket(fixture.bot, {}, { wait: fixture.wait }), { code: 'WATER_TARGET_UNREACHABLE' });
  assert.deepEqual(fixture.counts(), { navigations: 1, activations: 0, scans: 1 });
  assert.equal(Object.values(fixture.bot.controlState).some(Boolean), false);
});

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

test('water approach cannot spend the source-change allowance on native SDK bridges', async () => {
  const bot = waterBot();
  bot.registry = minecraftData('1.21.1');
  const Block = blockLoader(bot.registry);
  const source = new Vec3(8, 64, 0);
  bot.findBlocks = () => [source];
  bot.items.push({ name: 'dirt', type: bot.registry.itemsByName.dirt.id, count: 8 },
    { name: 'cobblestone', type: bot.registry.itemsByName.cobblestone.id, count: 8 });
  bot.blockAt = position => {
    const gap = position.equals(new Vec3(1, 63, 0));
    const name = position.equals(source) ? 'water' : position.y < 64 && !gap ? 'stone' : 'air';
    const block = Block.fromStateId(bot.registry.blocksByName[name].defaultState, 0);
    block.position = position;
    return block;
  };
  const original = {};
  let goals = 0;
  bot.pathfinder = {
    movements: original, setMovements(value) { this.movements = value; }, stop() {},
    getPathFromTo: directWaterPath,
    bestHarvestTool: () => null,
    async goto(goal) {
      goals++;
      const edges = [];
      this.movements.getMoveForward({ x: 0, y: 64, z: 0,
        remainingBlocks: this.movements.countScaffoldingItems() }, { x: 1, z: 0 }, edges);
      assert.equal(edges.some(edge => edge.toPlace.length > 0), false,
        'a non-excavating water approach must not generate bridge placement edges');
      bot.entity.position = new Vec3(goal.x + 0.5, goal.y, goal.z + 0.5);
    },
  };
  const result = await fillWaterBucket(bot);
  assert.equal(result.output.filled, true);
  assert.equal(result.budget_usage.max_blocks_changed, 1);
  assert.equal(goals, 1);
  assert.equal(bot.pathfinder.movements, original);
});

test('unconfirmed water fill retains the interaction state before confirmation cleanup', async () => {
  const bot = waterBot();
  Object.assign(bot.entity, { eyeHeight: 1.62, yaw: 1.5, pitch: -0.2 });
  bot.items[0].slot = 36;
  bot.heldItem = bot.items[0];
  let uses = 0;
  bot.activateItem = () => { uses++; };
  let waits = 0;
  await assert.rejects(fillWaterBucket(bot, {}, { wait: async () => {
    waits++;
    bot.entity.pitch = 0;
    bot.heldItem = null;
  } }), error => {
    assert.equal(error.code, 'WATER_FILL_UNCONFIRMED');
    assert.deepEqual(error.details.interaction_at_use, {
      eye_height: 1.62, yaw: 1.5, pitch: -0.2, held_item: 'bucket',
      expected_bucket_slot: 36, live_bucket_slot: 36,
    });
    return true;
  });
  assert.equal(uses, 1);
  assert.equal(waits, 30);
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

test('installed SDK water search filters covered water before the unchanged candidate limit', async () => {
  const bot = waterBot();
  bot.registry = minecraftData('1.21.1');
  bot.version = '1.21.1';
  bot.game = { minY: -64, height: 384 };
  bot._client = new EventEmitter();
  const Chunk = ChunkLoader(bot.registry);
  const World = WorldLoader(bot.registry);
  const world = new World(null).sync;
  const center = new Chunk({ minY: -64, worldHeight: 384 });
  const diagonal = new Chunk({ minY: -64, worldHeight: 384 });
  const ids = bot.registry.blocksByName;
  for (let x=0;x<16;x++) for (let z=0;z<16;z++) {
    center.setBlockStateId(new Vec3(x,63,z),ids.stone.defaultState);
    diagonal.setBlockStateId(new Vec3(x,63,z),ids.stone.defaultState);
  }
  for (let x=1;x<=8;x++) for (let z=1;z<=8;z++) {
    for (let y=64;y<72;y++) center.setBlockStateId(new Vec3(x,y,z),ids.water.defaultState);
    center.setBlockStateId(new Vec3(x,72,z),ids.stone.defaultState);
  }
  const shore = new Vec3(-1,64,-1);
  diagonal.setBlockStateId(new Vec3(15,64,15),ids.water.defaultState);
  world.setColumn(0,0,center);
  world.setColumn(-1,-1,diagonal);
  bot.world = world;
  injectBlocks(bot,{version:bot.version});
  const initial = bot.findBlocks({ matching:ids.water.id,maxDistance:64,count:512 });
  assert.equal(initial.length,512);
  assert.equal(initial.some(position=>position.equals(shore)),false);
  const findBlocks = bot.findBlocks;
  bot.findBlocks = options => {
    assert.equal(options.maxDistance,64);
    assert.equal(options.count,512);
    return findBlocks(options);
  };
  const result = await fillWaterBucket(bot);
  assert.equal(result.output.filled,true);
  assert.deepEqual(result.output.source,shore);
  bot.items = [{ name:'bucket',count:1 }];
  const getBlock = world.getBlock.bind(world);
  world.getBlock = position => position.equals(shore.offset(0,1,0)) ? null : getBlock(position);
  await assert.rejects(fillWaterBucket(bot),error => error.code === 'WATER_SOURCE_NOT_FOUND'
    && error.details.rejected_unknown_above > 0 && error.details.returned_candidates === 0
    && error.details.samples.unknown_above.above_name === null
    && Object.keys(error.details.samples).length <= 3);
});

test('missing source diagnostics preserve the original search bounds without extra attempts', async () => {
  const bot = waterBot();
  let searches = 0;
  bot.findBlocks = () => { searches++; return []; };
  await assert.rejects(fillWaterBucket(bot),error => error.code === 'WATER_SOURCE_NOT_FOUND'
    && error.details.search_radius === 64 && error.details.candidate_limit === 512
    && error.details.source_checks === 0);
  assert.equal(searches,1);
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
    getPathFromTo: directWaterPath,
    async goto() { throw Object.assign(new Error('No dry route'), { name: 'NoPath' }); },
  };
  const result = await fillWaterBucket(bot);
  assert.equal(result.output.filled, true);
  assert.deepEqual(result.output.source, shore);
  assert.equal(bot.pathfinder.movements, original);
});

for (const crowded of [false, true]) {
  test(crowded ? 'water source beyond a crowded nearest prefix remains reachable within sixteen selected sources'
    : 'water fill plans one reachable shore without walking separate sealed-source goals', async () => {
    const bot = waterBot();
    bot.registry = minecraftData('1.21.1');
    bot.game = { minY: -64, height: 384 };
    bot.entity.velocity = new Vec3(0, 0, 0);
    bot.entity.effects = {};
    bot.entities = {};
    bot.clearControlStates = () => {};
    bot.setControlState = () => {};
    const Block = blockLoader(bot.registry);
    const sealed = crowded ? Array.from({ length: 16 }, (_, i) => new Vec3(6 + i % 4, 64, -2 + Math.floor(i / 4)))
      : [new Vec3(8, 64, 0)];
    const accessible = new Vec3(0, 64, crowded ? 16 : 8);
    const world = new WorldSync(null);
    world.getBlock = position => {
      const wall = position.y >= 64 && position.y <= 70
        && (([4, 12].includes(position.x) && Math.abs(position.z) <= 4)
          || (Math.abs(position.z) === 4 && position.x >= 4 && position.x <= 12));
      const name = position.y < 64 || wall ? 'stone'
        : sealed.some(source => position.equals(source)) || position.equals(accessible) ? 'water' : 'air';
      const block = Block.fromStateId(bot.registry.blocksByName[name].defaultState, 0);
      block.position = position;
      return block;
    };
    bot.world = world;
    bot.blockAt = position => world.getBlock(position.floored());
    bot.findBlocks = options => {
      assert.equal(options.maxDistance, 64);
      assert.equal(options.count, 512);
      return [...sealed, accessible];
    };
    pathfinderPkg.pathfinder(bot);
    const nativePlanner = bot.pathfinder.getPathFromTo.bind(bot.pathfinder);
    bot.pathfinder.getPathFromTo = function* (movements, start, goal, options) {
      const before = bot.entity.position.clone();
      if (goal instanceof pathfinderPkg.goals.GoalCompositeAny) {
        assert.ok(goal.goals.length <= Math.min(16, sealed.length + 1) * 4);
        assert.equal(new Set(goal.goals.map(g => `${g.x},${g.y},${g.z}`)).size, goal.goals.length);
      }
      for (const planned of nativePlanner(movements, start, goal,
        options ?? (crowded ? { timeout: 200, tickTimeout: 40, optimizePath: false } : undefined))) {
        assert.deepEqual(bot.entity.position, before, 'planning must not move the bot');
        yield planned;
      }
    };
    let navigations = 0;
    bot.pathfinder.goto = async goal => {
      navigations++;
      const generator = bot.pathfinder.getPathFromTo(bot.pathfinder.movements,
        bot.entity.position, goal, { timeout: 100, tickTimeout: 20, optimizePath: false });
      let result;
      for (const value of generator) {
        result = value.result;
        if (result.status !== 'partial') break;
      }
      if (result.status !== 'success') {
        throw Object.assign(new Error('sealed source'), { name: 'Timeout' });
      }
      assert.equal(result.path.some(move => move.toBreak.length || move.toPlace.length), false);
      const end = result.path.at(-1);
      bot.entity.position = new Vec3(end.x + 0.5, end.y, end.z + 0.5);
    };
    const result = await fillWaterBucket(bot);
    assert.equal(result.output.filled, true);
    assert.deepEqual(result.output.source, accessible);
    assert.equal(navigations, 1, 'an unreachable source must not cause separate native navigation attempts');
    assert.equal(result.budget_usage.max_blocks_changed, 1);
  });
}

test('water planning timeout preserves zero movement and does not execute its partial route', async () => {
  const bot = waterBot();
  bot.registry = minecraftData('1.21.1');
  bot.entity.position = new Vec3(-8.5, 64, 0.5);
  const original = {};
  let plans = 0;
  bot.pathfinder = {
    movements: original, setMovements(value) { this.movements = value; }, stop() {},
    *getPathFromTo() { plans++; yield { result: { status: 'timeout', path: [new Vec3(0, 64, 0)] } }; },
    goto: () => assert.fail('a partial route is not a proven shore route'),
  };
  await assert.rejects(fillWaterBucket(bot), error => error.code === 'WATER_TARGET_UNREACHABLE'
    && error.details.planning_status === 'timeout' && error.budget_usage.max_travel_distance === 0
    && error.budget_usage.max_blocks_changed === 0);
  assert.equal(plans, 1);
  assert.equal(bot.pathfinder.movements, original);
});

test('visible nearby water is used before sampling a crowded source set', async () => {
  const bot = waterBot();
  const positions = [new Vec3(1, 64, 0), new Vec3(2, 64, 0),
    ...Array.from({ length: 16 }, (_, i) => new Vec3(30 + i, 64, 0))];
  const blockAt = bot.blockAt;
  bot.blockAt = position => positions.some(source => position.equals(source))
    ? { name: 'water', boundingBox: 'empty', metadata: 0, position } : blockAt(position);
  bot.findBlocks = () => positions;
  bot.world.raycast = (_eye, _direction, distance) => distance < 2
    ? { position: new Vec3(0, 65, 0) } : null;
  bot.pathfinder = { getPathFromTo: () => assert.fail('visible water must not trigger a route search') };
  const result = await fillWaterBucket(bot);
  assert.equal(result.output.filled, true);
  assert.deepEqual(result.output.source, positions[1]);
});

test('water planning observes cancellation before starting native navigation', async () => {
  const bot = waterBot();
  bot.registry = minecraftData('1.21.1');
  bot.entity.position = new Vec3(-8.5, 64, 0.5);
  const controller = new AbortController();
  const original = {};
  bot.pathfinder = {
    movements: original, setMovements(value) { this.movements = value; }, stop() {},
    *getPathFromTo() {
      yield { result: { status: 'partial', path: [] } };
      controller.abort();
      yield { result: { status: 'success', path: [new Vec3(0, 64, 0)] } };
    },
    goto: () => assert.fail('cancelled planning must not start movement'),
  };
  await assert.rejects(fillWaterBucket(bot, { signal: controller.signal }), error => error.name === 'AbortError'
    && error.budget_usage.max_travel_distance === 0);
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
    getPathFromTo: directWaterPath,
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
