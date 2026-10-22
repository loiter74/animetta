import assert from 'node:assert/strict';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import pathfinderPackage from 'mineflayer-pathfinder';
import prismarineBlock from 'prismarine-block';
import AStar from 'mineflayer-pathfinder/lib/astar.js';
import Move from 'mineflayer-pathfinder/lib/move.js';
import { configureDryNavigation } from '../src/collection.js';
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

test('underground return reaches the surface through bounded native height goals', async () => {
  const { bot, goals } = fixture(26);
  await navigateTo(bot, { x: 11, y: 64, z: 75 });
  assert.ok(goals.length > 1);
  assert.ok(goals.slice(0, -1).every((goal, index) => goal.constructor.name === 'GoalY' && goal.y === 30 + index * 4));
  assert.deepEqual(bot.entity.position, new Vec3(11, 64, 75));
  assert.equal(bot.pathfinder.thinkTimeout, 5000);
  assert.equal(bot.pathfinder.movements.allow1by1towers, true);
});

test('ascent suppresses real SDK jump-place tower edges and restores movement policy', async () => {
  const { bot } = fixture(26);
  bot.registry = minecraftData('1.21.1');
  const movements = new pathfinderPackage.Movements(bot);
  movements.getNumEntitiesAt = () => 0;
  movements.safeOrBreak = () => 0;
  movements.getBlock = (node, dx, dy, dz) => ({
    position: new Vec3(node.x + dx, node.y + dy, node.z + dz),
    liquid: false, climbable: false, replaceable: true, physical: dy < 0,
    height: node.y + dy + 1,
  });
  const node = { x: 18, y: 26, z: 86, remainingBlocks: 63 };
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
