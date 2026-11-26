import assert from 'node:assert/strict';
import test from 'node:test';
import { EventEmitter } from 'node:events';
import Vec3 from 'vec3';
import pathfinderPkg from 'mineflayer-pathfinder';
import minecraftData from 'minecraft-data';
import { buildInfiniteWaterSource, buildLavaDripFarm } from '../src/renewable.js';

const wait = async () => {};

function completeLook(bot, point) {
  const delta = point.minus(bot.entity.position.offset(0, 1.62, 0));
  bot.entity.yaw = Math.atan2(-delta.x, -delta.z);
  bot.entity.pitch = Math.atan2(delta.y, Math.hypot(delta.x, delta.z));
  bot.emit('move');
}

// Plain terrain fixture: solid ground below groundY, air above, plus a map of
// per-cell overrides that the bot's actions (dig, place, pour) mutate.
function terrainBot({ position, groundY = 63, groundName = 'stone', overrides = new Map() } = {}) {
  const bot = new EventEmitter();
  bot.health = 20;
  bot.entity = { position: position.clone(), onGround: true, velocity: new Vec3(0, 0, 0), effects: {} };
  bot.registry = { blocksByName: { water: { id: 1 }, lava: { id: 3 } } };
  bot.game = { minY: -64, height: 384 };
  bot.items = [];
  bot.inventory = { items: () => bot.items };
  bot.entities = {};
  bot.heldItem = null;
  bot.digs = 0;
  bot.uses = 0;
  bot.poured = [];
  bot.findBlocks = () => [];

  const key = p => `${p.x},${p.y},${p.z}`;
  const blockAt = p => {
    const position = new Vec3(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z));
    const name = overrides.has(key(position))
      ? overrides.get(key(position))
      : (position.y <= groundY ? groundName : 'air');
    const solid = name !== 'air' && name !== 'water' && name !== 'lava';
    return {
      name,
      boundingBox: solid ? 'block' : 'empty',
      shapes: solid ? [[0, 0, 0, 1, 1, 1]] : [],
      metadata: 0,
      position,
    };
  };
  bot.blockAt = blockAt;
  bot.world = { raycast: () => null, getBlock: p => blockAt(p) };

  bot.equip = async (item, _slot) => { bot.heldItem = item; };
  let lookTarget = null;
  bot.lookAt = async point => { lookTarget = point; completeLook(bot, point); };
  bot.activateItem = () => {
    bot.uses++;
    if (bot.heldItem?.name !== 'water_bucket' && bot.heldItem?.name !== 'lava_bucket') return;
    const cell = new Vec3(Math.floor(lookTarget.x), Math.floor(lookTarget.y) + 1, Math.floor(lookTarget.z));
    const fluid = bot.heldItem.name === 'water_bucket' ? 'water' : 'lava';
    overrides.set(key(cell), fluid);
    // A real inventory keeps one stack; pouring consumes one bucket from it.
    bot.heldItem.count--;
    if (bot.heldItem.count <= 0) {
      bot.items = bot.items.filter(item => item !== bot.heldItem);
      bot.items.push({ name: 'bucket', count: 1 });
      bot.heldItem = bot.items.find(item => item.name === 'bucket');
    }
    bot.poured.push(cell);
    if (fluid === 'water' && bot.poured.length === 2) {
      // Once both trench ends hold sources, the middle cell settles too.
      const [first, second] = bot.poured;
      overrides.set(key(first.plus(second).scaled(0.5).floored()), 'water');
    }
  };
  bot.deactivateItem = () => {};
  bot.dig = async block => {
    bot.digs++;
    overrides.set(key(block.position), 'air');
  };
  bot.placeBlock = async (reference, face) => {
    const cell = reference.position.plus(face);
    overrides.set(key(cell), bot.heldItem?.name);
  };
  return {
    bot,
    set: (position, name) => overrides.set(key(position), name),
    get: position => blockAt(position).name,
  };
}

test('infinite water source pours both trench ends without digging', async () => {
  const { bot, get } = terrainBot({
    position: new Vec3(3.5, 64, 1.5),
    overrides: new Map([['2,63,0', 'air'], ['3,63,0', 'air'], ['4,63,0', 'air']]),
  });
  bot.items = [{ name: 'water_bucket', count: 2 }];
  const result = await buildInfiniteWaterSource(bot, {}, { wait });
  assert.equal(result.output.created, true);
  assert.equal(result.output.position.toString(), new Vec3(3, 63, 0).toString());
  assert.deepEqual(result.output.cells.map(cell => cell.toString()),
    ['(2, 63, 0)', '(3, 63, 0)', '(4, 63, 0)']);
  assert.equal(bot.digs, 0);
  assert.equal(bot.uses, 2);
  assert.equal(result.explained_mutations.length, 2);
  assert.equal(get(new Vec3(3, 63, 0)), 'water');
  assert.equal(bot.items.filter(item => item.name === 'water_bucket').length, 0);
});

test('infinite water source is idempotent when a pool already exists', async () => {
  const cells = [new Vec3(2, 63, 0), new Vec3(3, 63, 0), new Vec3(4, 63, 0)];
  const pool = terrainBot({
    position: new Vec3(3.5, 64, 1.5),
    overrides: new Map(cells.map(cell => [`${cell.x},${cell.y},${cell.z}`, 'water'])),
  });
  pool.bot.findBlocks = () => cells;
  const result = await buildInfiniteWaterSource(pool.bot, {}, { wait });
  assert.equal(result.output.created, false);
  assert.equal(result.output.already_present, true);
  assert.equal(pool.bot.uses, 0);
});

test('infinite water source fails when no carvable terrain exists nearby', async () => {
  const { bot } = terrainBot({ position: new Vec3(3.5, 64, 1.5), groundName: 'bedrock' });
  await assert.rejects(buildInfiniteWaterSource(bot, {}, { wait }), {
    code: 'WATER_SOURCE_SITE_NOT_FOUND',
  });
});

test('infinite water source digs the trench through plain ground before pouring', async () => {
  const { bot, get } = terrainBot({ position: new Vec3(3.5, 64, 1.5), groundName: 'dirt' });
  bot.items = [{ name: 'water_bucket', count: 2 }];
  const result = await buildInfiniteWaterSource(bot, {}, { wait });
  assert.equal(result.output.created, true);
  assert.equal(bot.digs, 3);
  assert.equal(bot.uses, 2);
  assert.equal(get(result.output.position), 'water');
});

test('lava drip farm rejects a missing material kit up front', async () => {
  const { bot } = terrainBot({ position: new Vec3(3.5, 64, 1.5) });
  bot.items = [{ name: 'cauldron', count: 1 }, { name: 'lava_bucket', count: 1 }];
  await assert.rejects(buildLavaDripFarm(bot, {}, { wait }), { code: 'MISSING_MATERIAL' });
});

function lavaFarmFixture() {
  const fixture = terrainBot({ position: new Vec3(10.5, 64, 0.5) });
  const bot = fixture.bot;
  // The stair navigation and pour-approach paths need a real registry and the
  // pathfinder plugin; goto is a teleport so physics never runs.
  bot.registry = minecraftData('1.21.1');
  bot.items = [
    { name: 'cauldron', count: 1 },
    { name: 'pointed_dripstone', count: 1 },
    { name: 'lava_bucket', count: 1 },
    { name: 'cobblestone', count: 2 },
  ];
  bot.controlState = {};
  bot.clearControlStates = () => { for (const k of Object.keys(bot.controlState)) bot.controlState[k] = false; };
  bot.setControlState = (key, value) => { bot.controlState[key] = value; };
  pathfinderPkg.pathfinder(bot);
  bot.pathfinder.goto = async goal => {
    bot.entity.position = new Vec3(goal.x + 0.5, goal.y, goal.z + 0.5);
  };
  return fixture;
}

test('lava drip farm digs the stair shaft, assembles the farm and pours the source', async () => {
  const { bot, get } = lavaFarmFixture();
  const result = await buildLavaDripFarm(bot, {}, { wait });
  assert.equal(result.output.created, true);
  assert.equal(result.output.fills_over_time, true);
  // Structure: lava source, support, dripstone, cauldron stacked downward.
  assert.equal(get(result.output.position), 'lava');
  assert.equal(get(result.output.lava_support), 'cobblestone');
  assert.equal(get(result.output.dripstone), 'pointed_dripstone');
  assert.equal(get(result.output.cauldron), 'cauldron');
  // The stair column is sealed so the surface stays lava-tight.
  assert.equal(get(result.output.position.offset(1, 0, 0)), 'cobblestone');
  assert.equal(bot.digs, 9);
  assert.equal(bot.uses, 1);
  assert.equal(bot.items.find(item => item.name === 'lava_bucket'), undefined);
  // 9 carved cells + 4 placed blocks + 1 poured lava source.
  assert.equal(result.explained_mutations.length, 14);
});

test('lava drip farm fails when the terrain cannot host the shaft', async () => {
  const { bot } = terrainBot({ position: new Vec3(3.5, 64, 1.5), groundName: 'bedrock' });
  bot.items = [
    { name: 'cauldron', count: 1 },
    { name: 'pointed_dripstone', count: 1 },
    { name: 'lava_bucket', count: 1 },
    { name: 'cobblestone', count: 2 },
  ];
  await assert.rejects(buildLavaDripFarm(bot, {}, { wait }), { code: 'LAVA_FARM_SITE_NOT_FOUND' });
});
