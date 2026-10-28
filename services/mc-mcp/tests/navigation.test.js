import assert from 'node:assert/strict';
import test from 'node:test';
import { EventEmitter } from 'node:events';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import pathfinderPackage from 'mineflayer-pathfinder';
import prismarineBlock from 'prismarine-block';
import AStar from 'mineflayer-pathfinder/lib/astar.js';
import Move from 'mineflayer-pathfinder/lib/move.js';
import {
  collectionExcavationGoal,
  configureDryNavigation,
  getUndergroundCollectionPreparation,
} from '../src/collection.js';
import { escapeWaterToShore, navigateTo, surfaceEscapePlan } from '../src/navigation.js';

function fixture(y) {
  const goals = [];
  const bot = { entity: { position: new Vec3(18, y, 86) }, pathfinder: { thinkTimeout: 5000,
    movements: { allow1by1towers: true },
    async goto(goal) {
      goals.push(goal);
      if (goal.constructor.name === 'GoalY') bot.entity.position.y = goal.y;
      else bot.entity.position = new Vec3(goal.x, goal.y, goal.z);
    },
  } };
  return { bot, goals };
}

function diagnosticFixture(t) {
  const previous = process.env.COLLECT_DEBUG;
  process.env.COLLECT_DEBUG = '1';
  t.after(() => { if (previous === undefined) delete process.env.COLLECT_DEBUG; else process.env.COLLECT_DEBUG = previous; });
  const { bot } = fixture(64);
  const emitter = Object.assign(new EventEmitter(), bot);
  emitter.entity.velocity = new Vec3(0, 0, 0);
  emitter.entity.onGround = true;
  emitter.controlState = { forward: false, jump: false, sprint: false };
  return emitter;
}

test('failed navigation retains bounded passive path evidence and removes observers', async t => {
  const bot = diagnosticFixture(t);
  const failure = new Error('native route stalled');
  let calls = 0;
  bot.pathfinder.goto = async () => {
    calls++;
    bot.emit('path_update', { status: 'success', path: [new Vec3(17.5, 65, 86.5)] });
    bot.emit('physicsTick');
    bot.emit('path_reset', 'stuck');
    bot.emit('path_update', { status: 'noPath', path: [] });
    throw failure;
  };
  await assert.rejects(navigateTo(bot, { x: 17, y: 65, z: 86 }), error => {
    assert.equal(error, failure);
    const trace = error.details.navigation_trace;
    assert.equal(trace.latest_update.status, 'noPath');
    assert.equal(trace.last_reset.reason, 'stuck');
    assert.equal(trace.last_motion.on_ground, true);
    assert.deepEqual(trace.last_motion.controls, bot.controlState);
    assert.equal(trace.first_update.next_node.y, 65);
    return true;
  });
  assert.equal(calls, 1, 'observation must not submit another navigation');
  for (const name of ['path_update', 'path_reset', 'physicsTick']) assert.equal(bot.listenerCount(name), 0);
  assert.deepEqual(bot.controlState, { forward: false, jump: false, sprint: false });
});

test('successful navigation removes passive observers without changing controls or allowances', async t => {
  const bot = diagnosticFixture(t);
  bot._client = new EventEmitter();
  const controls = { ...bot.controlState };
  let calls = 0;
  bot.pathfinder.goto = async goal => {
    calls++;
    bot.emit('path_update', { status: 'success', path: [new Vec3(goal.x, goal.y, goal.z)] });
    bot.entity.position = new Vec3(goal.x, goal.y, goal.z);
    bot.emit('physicsTick');
  };
  await navigateTo(bot, { x: 17, y: 65, z: 86 });
  assert.equal(calls, 1);
  for (const name of ['path_update', 'path_reset', 'physicsTick']) assert.equal(bot.listenerCount(name), 0);
  assert.equal(bot.listenerCount('blockUpdate'), 0);
  assert.equal(bot._client.listenerCount('block_change'), 0);
  assert.deepEqual(bot.controlState, controls);
  assert.equal(bot.pathfinder.thinkTimeout, 5000);
  assert.equal(bot.pathfinder.movements.allow1by1towers, true);
});

test('passive navigation distinguishes pending native digging from a server block rollback', async t => {
  const bot = diagnosticFixture(t);
  bot._client = new EventEmitter();
  const position = new Vec3(17, 65, 86);
  const stone = { name: 'stone', stateId: 1, position };
  bot.pathfinder.isMining = () => true;
  bot.pathfinder.isBuilding = () => false;
  bot.targetDigBlock = stone;
  bot.heldItem = { name: 'iron_pickaxe', type: 834 };
  let calls = 0;
  bot.pathfinder.goto = async () => {
    calls++;
    bot.emit('path_update', { status: 'success', path: [{ ...position, toBreak: [position] }] });
    bot.emit('blockUpdate', stone, { name: 'air', stateId: 0, position });
    bot._client.emit('block_change', { location: position, type: 1 });
    bot.emit('physicsTick');
    throw new Error('route stalled');
  };
  await assert.rejects(navigateTo(bot, { x: 17, y: 65, z: 86 }), error => {
    const trace = error.details.navigation_trace;
    assert.equal(trace.last_motion.mining, true);
    assert.equal(trace.last_motion.building, false);
    assert.deepEqual(trace.last_motion.target_dig_block, { name: 'stone', state_id: 1, position: { x: 17, y: 65, z: 86 } });
    assert.equal(trace.last_motion.held_item, 'iron_pickaxe');
    assert.deepEqual(trace.latest_update.next_node.break_targets, [{ x: 17, y: 65, z: 86 }]);
    assert.equal(trace.block_updates.at(-1).after_state_id, 0);
    assert.equal(trace.server_block_updates.at(-1).state_id, 1);
    return true;
  });
  assert.equal(calls, 1);
  assert.equal(bot.listenerCount('blockUpdate'), 0);
  assert.equal(bot._client.listenerCount('block_change'), 0);
  assert.equal(bot.targetDigBlock, stone, 'observation must not stop the native dig');
});

test('passive navigation retains bounded segment and block histories without adding goals', async t => {
  const bot = diagnosticFixture(t);
  bot.entity.position.y = 57;
  bot._client = new EventEmitter();
  const goals = [];
  bot.pathfinder.goto = async goal => {
    goals.push(goal.constructor.name);
    for (let x = 0; x < 20; x++) {
      bot.emit('blockUpdate', { stateId: 1, position: new Vec3(x, 65, 86) }, { stateId: 0, position: new Vec3(x, 65, 86) });
      bot._client.emit('block_change', { location: new Vec3(x, 65, 86), type: 1 });
    }
    if (goal.constructor.name === 'GoalY') bot.entity.position.y = goal.y;
    else throw new Error('route stalled');
  };
  await assert.rejects(navigateTo(bot, { x: 17, y: 69, z: 86 }), error => {
    const trace = error.details.navigation_trace;
    assert.deepEqual(trace.completed_segments.map(s => s.goal.y), [61, 65]);
    assert.ok(trace.completed_segments.every(s => s.elapsed_ms >= 0));
    assert.equal(trace.block_update_count, 20);
    assert.equal(trace.server_block_update_count, 20);
    assert.equal(trace.block_updates.length, 8);
    assert.equal(trace.server_block_updates.length, 8);
    assert.equal(trace.server_block_updates[0].position.x, 12);
    return true;
  });
  assert.deepEqual(goals, ['GoalY', 'GoalY', 'GoalBlock']);
  assert.equal(bot.listenerCount('blockUpdate'), 0);
  assert.equal(bot._client.listenerCount('block_change'), 0);
});

test('passive navigation retains the last dig through settlement and tolerates unavailable activity', async t => {
  const bot = diagnosticFixture(t);
  const stone = { name: 'stone', stateId: 1, position: new Vec3(17, 65, 86) };
  const failure = new Error('native failure');
  bot.pathfinder.goto = async () => {
    bot.targetDigBlock = stone;
    bot.pathfinder.isMining = () => true;
    bot.emit('physicsTick');
    bot.targetDigBlock = null;
    bot.pathfinder.isMining = () => { throw new Error('activity unavailable'); };
    bot.emit('physicsTick');
    throw failure;
  };
  await assert.rejects(navigateTo(bot, { x: 17, y: 65, z: 86 }), error => {
    assert.equal(error, failure);
    const trace = error.details.navigation_trace;
    assert.equal(trace.last_motion.mining, null);
    assert.equal(trace.last_motion.target_dig_block, null);
    assert.equal(trace.last_dig.mining, true);
    assert.deepEqual(trace.last_dig.target_dig_block.position, { x: 17, y: 65, z: 86 });
    return true;
  });
  assert.equal(bot.listenerCount('physicsTick'), 0);
  assert.equal(bot.listenerCount('blockUpdate'), 0);
});

test('passive navigation evidence reads nonenumerable native controls without changing them', async t => {
  const bot = diagnosticFixture(t);
  const expected = { forward: false, back: false, left: true, right: false, jump: false, sprint: false, sneak: true };
  bot.controlState = {};
  for (const [name, value] of Object.entries(expected)) {
    Object.defineProperty(bot.controlState, name, { get: () => value });
  }
  assert.deepEqual(Object.entries(bot.controlState), [], 'matches native Mineflayer property descriptors');
  bot.pathfinder.goto = async () => {
    bot.emit('physicsTick');
    throw new Error('route stalled');
  };
  await assert.rejects(navigateTo(bot, { x: 17, y: 65, z: 86 }), error => {
    assert.deepEqual(error.details.navigation_trace.last_motion.controls, expected);
    return true;
  });
  for (const [name, value] of Object.entries(expected)) assert.equal(bot.controlState[name], value);
  for (const name of ['path_update', 'path_reset', 'physicsTick']) assert.equal(bot.listenerCount(name), 0);
});

test('failed navigation retains bounded final collision states including unknown cells', async t => {
  const bot = diagnosticFixture(t);
  const reads = [];
  bot.blockAt = point => {
    reads.push(point.clone());
    if (point.x === 17) return null;
    return { name: point.y < 64 ? 'stone' : 'air', stateId: point.y < 64 ? 1 : 0 };
  };
  const failure = new Error('route stalled');
  bot.pathfinder.goto = async () => { bot.emit('physicsTick'); throw failure; };
  await assert.rejects(navigateTo(bot, { x: 17, y: 65, z: 86 }), error => {
    assert.equal(error, failure);
    const terrain = error.details.navigation_trace.local_blocks;
    assert.equal(terrain.length, 45);
    assert.deepEqual(terrain.find(p => p.x === 18 && p.y === 63 && p.z === 86),
      { x: 18, y: 63, z: 86, name: 'stone', state_id: 1 });
    assert.deepEqual(terrain.find(p => p.x === 17 && p.y === 64 && p.z === 86),
      { x: 17, y: 64, z: 86, name: null, state_id: null });
    return true;
  });
  assert.equal(reads.length, 48, '45 passive collision reads plus the existing head and failure checks');
});

test('underground return reaches the surface through bounded native height goals', async () => {
  const { bot, goals } = fixture(26);
  await navigateTo(bot, { x: 11, y: 64, z: 75 });
  assert.ok(goals.length > 1);
  assert.ok(goals.slice(0, -1).every((goal, index) => goal.constructor.name === 'GoalY' && goal.y === 30 + index * 4));
  assert.deepEqual(bot.entity.position, new Vec3(11, 64, 75));
  assert.equal(bot.pathfinder.thinkTimeout, 5000);
  assert.equal(bot.pathfinder.movements.allow1by1towers, true);
});

function towerFixture(y) {
  const { bot } = fixture(y);
  bot.registry = minecraftData('1.21.1');
  const movements = new pathfinderPackage.Movements(bot);
  movements.getNumEntitiesAt = () => 0;
  movements.safeOrBreak = () => 0;
  movements.getBlock = (node, dx, dy, dz) => ({
    position: new Vec3(node.x + dx, node.y + dy, node.z + dz),
    liquid: false, climbable: false, replaceable: true, physical: dy < 0,
    height: node.y + dy + 1,
  });
  const node = { x: 18, y, z: 86, remainingBlocks: 63 };
  bot.pathfinder.movements = movements;
  return { bot, movements, node };
}

test('ascent suppresses real SDK jump-place tower edges and restores movement policy', async () => {
  const { bot, movements, node } = towerFixture(26);
  const before = [];
  movements.getMoveUp(node, before);
  assert.equal(before[0].toPlace[0].jump, true);
  bot.pathfinder.movements = movements;
  const originalGoto = bot.pathfinder.goto;
  bot.pathfinder.goto = async goal => {
    const edges = [];
    movements.getMoveUp(node, edges);
    assert.deepEqual(edges, []);
    await originalGoto.call(bot.pathfinder, goal);
  };
  await navigateTo(bot, { x: 11, y: 64, z: 75 });
  assert.equal(movements.allow1by1towers, true);
});

for (const rise of [1, 4]) {
  test(`short ascent of ${rise} blocks also excludes native jump-place edges without extending planning`, async () => {
    const { bot, movements, node } = towerFixture(115);
    const before = [];
    movements.getMoveUp(node, before);
    assert.equal(before[0].toPlace[0].jump, true);
    const originalGoto = bot.pathfinder.goto;
    let calls = 0;
    bot.pathfinder.goto = async goal => {
      calls++;
      assert.equal(bot.pathfinder.thinkTimeout, 5000, 'short routes keep the original planning allowance');
      const edges = [];
      movements.getMoveUp(node, edges);
      assert.deepEqual(edges, [], 'short ascent must not admit the same SDK pillar primitive');
      await originalGoto.call(bot.pathfinder, goal);
    };
    await navigateTo(bot, { x: 19, y: 115 + rise, z: 86 });
    assert.equal(calls, 1, 'no additional navigation action or retry');
    assert.equal(movements.allow1by1towers, true);
    assert.equal(bot.pathfinder.thinkTimeout, 5000);
  });
}

test('failed short ascent restores an originally absent tower policy', async () => {
  const { bot } = fixture(115);
  delete bot.pathfinder.movements.allow1by1towers;
  const error = new Error('native route blocked');
  bot.pathfinder.goto = async () => {
    assert.equal(bot.pathfinder.movements.allow1by1towers, false);
    throw error;
  };
  await assert.rejects(navigateTo(bot, { x: 19, y: 119, z: 86 }), actual => actual === error);
  assert.equal(Object.hasOwn(bot.pathfinder.movements, 'allow1by1towers'), false);
  assert.equal(bot.pathfinder.thinkTimeout, 5000);
});

test('flat travel keeps one native goal and does not change planning settings', async () => {
  const { bot, goals } = fixture(64);
  await navigateTo(bot, { x: 11, y: 64, z: 75 });
  assert.equal(goals.length, 1);
  assert.equal(bot.pathfinder.thinkTimeout, 5000);
  assert.equal(bot.pathfinder.movements.allow1by1towers, true);
});

test('failed ascent stops after one request and restores planning settings', async () => {
  const { bot, goals } = fixture(26);
  bot.pathfinder.goto = async goal => { goals.push(goal); };
  await assert.rejects(navigateTo(bot, { x: 11, y: 64, z: 75 }), error => error.code === 'NAVIGATION_ASCENT_STALLED');
  assert.equal(goals.length, 1);
  assert.equal(bot.pathfinder.thinkTimeout, 5000);
});

test('cancellation prevents a new ascent request', async () => {
  const { bot, goals } = fixture(26);
  const controller = new AbortController(); controller.abort();
  await assert.rejects(navigateTo(bot, { x: 11, y: 64, z: 75 }, { signal: controller.signal }), error => error.name === 'AbortError');
  assert.equal(goals.length, 0);
  assert.equal(bot.pathfinder.thinkTimeout, 5000);
});

function submergedFixture() {
  const { bot, goals } = fixture(26);
  bot.registry = minecraftData('1.21.1');
  bot.inventory = { items: () => [] };
  bot.blockAt = position => {
    const column = position.x === 18 && position.z === 86 && position.y >= 26 && position.y < 32;
    const name = column ? 'water' : position.y < 32 ? 'stone' : 'air';
    return { name, boundingBox: name === 'stone' ? 'block' : 'empty', position };
  };
  const controls = [];
  bot.setControlState = (control, value) => controls.push([control, value]);
  bot.pathfinder.setGoal = () => {};
  bot.pathfinder.setMovements = value => { bot.pathfinder.movements = value; };
  return { bot, goals, controls };
}

test('submerged return swims only through known water to air then uses native shore navigation', async () => {
  const { bot, goals, controls } = submergedFixture();
  const previous = bot.pathfinder.movements;
  const plan = surfaceEscapePlan(bot, { x: 11, y: 32, z: 75 });
  assert.equal(plan.air_y, 32);
  await escapeWaterToShore(bot, plan, {}, { wait: async () => { bot.entity.position.y += 1; } });
  assert.deepEqual(bot.entity.position, new Vec3(11, 32, 75));
  assert.equal(goals.length, 1);
  assert.deepEqual(controls, [['jump', true], ['jump', false]]);
  assert.equal(bot.pathfinder.movements, previous);
  const blockAt = bot.blockAt;
  bot.entity.position = new Vec3(18, 26, 86);
  bot.blockAt = p => p.y === 30 ? { name: 'stone', boundingBox: 'block', position: p } : blockAt(p);
  assert.equal(surfaceEscapePlan(bot, { x: 11, y: 32, z: 75 }), null);
});

test('surface escape is time bounded and cancellation cannot enable jump', async () => {
  const { bot, controls } = submergedFixture();
  const plan = surfaceEscapePlan(bot, { x: 11, y: 32, z: 75 });
  let time = 0;
  await assert.rejects(escapeWaterToShore(bot, plan, {}, {
    now: () => time, wait: async ms => { time += ms; },
  }), error => error.code === 'SURFACE_ESCAPE_TIMEOUT');
  assert.deepEqual(controls.at(-1), ['jump', false]);
  controls.length = 0;
  const controller = new AbortController(); controller.abort();
  await assert.rejects(escapeWaterToShore(bot, plan, { signal: controller.signal }), error => error.name === 'AbortError');
  assert.deepEqual(controls, []);
});

test('recovery can reach a supported breathing station through a known surface-water channel', async () => {
  const registry = minecraftData('1.21.1');
  const Block = prismarineBlock(registry);
  const bot = { registry, inventory: { items: () => [] }, entities: {}, game: { minY: -64 },
    entity: { position: new Vec3(56.5, -55, 123.7), effects: {} },
    blockAt(position) {
      const p = position.floored();
      if (p.x !== 56 || p.z < 121 || p.z > 123 || p.y < -56 || p.y > -52) return null;
      const name = p.y >= -53 ? 'air' : p.y === -54 ? 'water'
        : p.y === -55 && p.z !== 121 ? 'water' : 'deepslate';
      const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
      block.position = p;
      return block;
    },
  };
  const plan = surfaceEscapePlan(bot, { x: 56, y: -54, z: 121 });
  assert.equal(plan?.air_y, -53);
  assert.equal(surfaceEscapePlan(bot, { x: 56, y: -54, z: 122 }), null);
  const movements = configureDryNavigation(new pathfinderPackage.Movements(bot), bot, { allowSurfaceSwimming: true });
  movements.canDig = false;
  movements.allow1by1towers = false;
  movements.allowEntityDetection = false;
  const result = new AStar(new Move(56, -54, 123, 0, 0), movements,
    new pathfinderPackage.goals.GoalBlock(56, -54, 121), 1000, 1000).compute();
  assert.equal(result.status, 'success');
  assert.ok(result.path.every(node => node.y === -54 && node.toBreak.length === 0 && node.toPlace.length === 0));
});

test('real SDK can leave an anchored canopy by supported steps without breaking its footing', () => {
  const registry = minecraftData('1.21');
  const Block = prismarineBlock(registry);
  let unstable = false;
  let obstructed = false;
  const heights = [74, 74, 73, 72, 71];
  const bot = { registry, inventory: { items: () => [] }, entities: {}, game: { minY: -64 },
    entity: { position: new Vec3(0.5, 75, 0.5), effects: {} },
    pathfinder: { bestHarvestTool: () => null },
    blockAt(position) {
      const p = position.floored();
      if (p.x < 0 || p.x > 4 || p.z !== 0 || p.y < 70 || p.y > 77) return null;
      const name = obstructed && p.x === 1 && p.y === 75 ? 'oak_leaves'
        : p.y > heights[p.x] ? 'air' : p.x < 3 ? 'oak_leaves' : 'stone';
      const block = name === 'oak_leaves'
        ? Block.fromProperties(registry.blocksByName[name].id,
          { distance: unstable && p.x === 1 ? 7 : 1, persistent: false, waterlogged: false }, 0)
        : Block.fromStateId(registry.blocksByName[name].defaultState, 0);
      block.position = p;
      return block;
    },
  };
  const movements = configureDryNavigation(new pathfinderPackage.Movements(bot), bot);
  movements.allowEntityDetection = false;
  const search = () => new AStar(new Move(0, 75, 0, 0, 0), movements,
    new pathfinderPackage.goals.GoalBlock(4, 72, 0), 1000, 1000).compute();
  const result = search();
  assert.equal(result.status, 'success');
  assert.ok(result.path.every(node => node.toBreak.length === 0 && node.toPlace.length === 0));
  for (const [index, node] of result.path.entries()) {
    const previousY = index ? result.path[index - 1].y : 75;
    assert.ok(previousY - node.y <= 1);
    assert.ok(node.y <= 75);
  }
  assert.equal(movements.safeToBreak(bot.blockAt(new Vec3(0, 74, 0))), false);
  const downward = [];
  movements.getMoveDown(new Move(1, 75, 0, 0, 0), downward);
  assert.deepEqual(downward, [], 'future path nodes cannot excavate their leaf footing either');
  obstructed = true;
  const clearedPath = search();
  assert.equal(clearedPath.status, 'success');
  assert.ok(clearedPath.path.some(node => node.toBreak.some(p => p.equals(new Vec3(1, 75, 0)))));
  assert.ok(clearedPath.path.flatMap(node => node.toBreak).every(p => p.y >= 75));
  obstructed = false;
  unstable = true;
  assert.notEqual(search().status, 'success', 'decaying unanchored leaves remain forbidden');
});

test('prepared iron access stays at the observed vein layer without pillaring back up a blind shaft', () => {
  // Synthetic bounded regression fixture for target-layer selection; this is
  // not a replay of any live map.
  const preparation = getUndergroundCollectionPreparation('iron_ore', 7, 30);
  assert.deepEqual(preparation, { targetY: 32, minimumCobblestone: 0 });
  const registry = minecraftData('1.21');
  const Block = prismarineBlock(registry);
  const search = startY => {
    const bot = {
      registry, inventory: { items: () => [
        { name: 'cobblestone', type: registry.itemsByName.cobblestone.id, count: 64 },
      ] }, entities: {}, game: { minY: -64 },
      entity: { position: new Vec3(0.5, startY, 0.5), effects: {} },
      pathfinder: { bestHarvestTool: () => ({ type: registry.itemsByName.stone_pickaxe.id }) },
      blockAt(position) {
        const p = position.floored();
        if (p.x < 0 || p.x > 2 || p.z !== 0 || p.y < 15 || p.y > 34) return null;
        const name = p.x === 1 && p.y === 30 ? 'iron_ore'
          : p.x === 0 && p.y >= startY ? 'air' : 'stone';
        const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
        block.position = p;
        return block;
      },
    };
    const movements = configureDryNavigation(new pathfinderPackage.Movements(bot), bot);
    movements.allowEntityDetection = false;
    return new AStar(new Move(0, startY, 0, 64, 0), movements,
      collectionExcavationGoal({ name: 'iron_ore', position: new Vec3(1, 30, 0) }),
      1000, 1000).compute();
  };
  const blind = search(16);
  assert.equal(blind.status, 'success');
  assert.ok(blind.path.some(node => node.toPlace.length > 0),
    'the original deeper shaft can reach the vein only by building back up');
  const result = search(preparation.targetY);
  assert.equal(result.status, 'success');
  assert.ok(result.path.every(node => node.toPlace.length === 0),
    'access to the observed vein must not pillar up the shaft');
  assert.ok(result.path.every(node => node.y <= preparation.targetY),
    'access must not climb above the prepared layer');
  assert.ok(result.path.every(node => node.y >= 30),
    'access must not tunnel below the observed vein floor');
  assert.equal(result.path.flatMap(node => node.toBreak).length, 2);
});
