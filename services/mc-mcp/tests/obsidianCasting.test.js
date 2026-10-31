import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import BlockLoader from 'prismarine-block';
import WorldSync from 'prismarine-world/src/worldsync.js';
import { prepareObsidian } from '../src/water.js';

const faceOffsets = [
  new Vec3(0, -1, 0), new Vec3(0, 1, 0), new Vec3(0, 0, -1),
  new Vec3(0, 0, 1), new Vec3(-1, 0, 0), new Vec3(1, 0, 0),
];

function basinBot({ sizes = [10], unknown = false, flowing = false,
  abort = false, noWater = false, blockLimit = 16, changeWallOnLook = false } = {}) {
  const registry = minecraftData('1.21.1'), Block = BlockLoader(registry);
  const bot = new EventEmitter(), world = new WorldSync(null), controller = new AbortController();
  const pools = sizes.map((size, index) => Array.from({ length: size }, (_, x) => new Vec3(index * 20 + x, 64, 0)));
  const lava = new Set(pools.flat().map(p => p.toString())), converted = new Set(), water = new Map();
  let uses = 0, lastLook, wallMissing = unknown;
  bot.items = noWater ? [] : [{ name: 'water_bucket', count: 1 }];
  Object.assign(bot, { registry, world, health: 20,
    game: { dimension: 'minecraft:overworld', minY: -64, height: 384 },
    entity: { position: new Vec3(Math.floor(sizes[0] / 2) + .5, 66, -.5),
      onGround: true, velocity: new Vec3(0, 0, 0), height: 1.8, width: .6,
      eyeHeight: 1.62, effects: {} },
    inventory: { items: () => bot.items },
  });
  world.getBlock = point => {
    const p = point.floored(), key = p.toString();
    if (wallMissing && p.equals(new Vec3(0, 65, -1))) return null;
    const name = water.has(key) ? 'water' : converted.has(key) ? 'obsidian'
      : lava.has(key) ? 'lava' : p.y === 65 && lava.has(p.offset(0, -1, 0).toString())
        ? 'air' : p.y < 66 ? 'stone' : 'air';
    const block = Block.fromStateId(registry.blocksByName[name].defaultState + (name === 'lava' && flowing ? 1 : 0), 0);
    block.position = p;
    return block;
  };
  bot.blockAt = p => world.getBlock(p);
  const scans = [];
  bot.findBlocks = options => {
    scans.push(options);
    return pools.flat().filter(p => {
      const block = bot.blockAt(p);
      return typeof options.matching === 'function' ? options.matching(block) : block.type === options.matching;
    }).slice(0, options.count);
  };
  bot.pathfinder = {
    movements: {}, stop() {}, setGoal() {},
    setMovements(movements) { this.movements = movements; },
    async goto(goal) { bot.entity.position = new Vec3(goal.x + .5, goal.y, goal.z + .5); bot.emit('move'); },
  };
  bot.equip = async item => { bot.heldItem = item; };
  bot.lookAt = async point => {
    lastLook = point;
    const delta = point.minus(bot.entity.position.offset(0, bot.entity.eyeHeight, 0));
    bot.entity.yaw = Math.atan2(-delta.x, -delta.z);
    bot.entity.pitch = Math.atan2(delta.y, Math.hypot(delta.x, delta.z));
    bot.emit('move');
    if (changeWallOnLook) wallMissing = true;
  };
  bot.activateItem = () => {
    uses++;
    if (bot.heldItem.name === 'bucket') {
      const p = lastLook.floored(), before = bot.blockAt(p);
      assert.ok(water.has(p.toString()), 'pickup must address the actual placed source');
      water.delete(p.toString());
      bot.items = [{ name: 'water_bucket', count: 1 }];
      bot.emit('blockUpdate', before, bot.blockAt(p));
      return;
    }
    const eye = bot.entity.position.offset(0, bot.entity.eyeHeight, 0);
    const delta = lastLook.minus(eye), hit = world.raycast(eye, delta.scaled(1 / delta.norm()), 4.25);
    assert.ok(hit && Number.isInteger(hit.face), 'placement needs a real solid face');
    const p = hit.position.plus(faceOffsets[hit.face]), pool = pools.find(cells => cells.some(c => c.equals(p.offset(0, -1, 0))));
    assert.ok(pool, 'the clicked face must place water inside the bounded basin');
    const before = bot.blockAt(p);
    water.set(p.toString(), p);
    bot.items = [{ name: 'bucket', count: 1 }];
    bot.emit('blockUpdate', before, bot.blockAt(p));
    for (const cell of pool) {
      const old = bot.blockAt(cell);
      converted.add(cell.toString());
      bot.emit('blockUpdate', old, bot.blockAt(cell));
      if (abort) { controller.abort(new Error('cast interrupted')); break; }
    }
  };
  bot.deactivateItem = () => {};
  const context = { signal: controller.signal,
    budget: { max_blocks_changed: blockLimit, max_travel_distance: 128 } };
  return { bot, context, scans, converted, water, uses: () => uses,
    run: () => prepareObsidian(bot, context, { wait: async () => {} }) };
}

test('no existing obsidian can be prepared from observed lava inside the original allowance', async () => {
  const f = basinBot(), original = { ...f.context.budget };
  const result = await f.run();
  assert.equal(result.output.protected, true);
  assert.equal(result.output.created_obsidian.length, 10);
  assert.equal(f.converted.size, 10);
  assert.equal(result.budget_usage.max_blocks_changed, 11);
  assert.deepEqual(f.context.budget, original);
  assert.ok(f.scans.every(scan => scan.maxDistance === 64 && scan.count === 64));
  assert.equal(f.uses(), 1);
  assert.equal(f.bot.listenerCount('blockUpdate'), 0);
});

test('separate bounded basins reuse the same water within the same original action account', async () => {
  const f = basinBot({ sizes: [7, 3] });
  const result = await f.run();
  assert.equal(result.output.created_obsidian.length, 10);
  assert.equal(result.budget_usage.max_blocks_changed, 13);
  assert.equal(f.uses(), 3, 'place, recover and reuse the original bucket');
  assert.equal(f.bot.listenerCount('blockUpdate'), 0);
});

for (const [name, options] of Object.entries({
  missing_water: { noWater: true }, flowing_lava: { flowing: true },
  unknown_wall: { unknown: true }, oversized_basin: { sizes: [17] },
  insufficient_allowance: { blockLimit: 8 },
  changed_boundary: { changeWallOnLook: true },
})) {
  test(`casting rejects ${name} before a world mutation`, async () => {
    const f = basinBot(options);
    await assert.rejects(f.run());
    assert.equal(f.uses(), 0);
    assert.equal(f.converted.size, 0);
    assert.equal(f.bot.listenerCount('blockUpdate'), 0);
  });
}

test('interrupted conversion retains observed effects and forbids treating an unfinished cast as settled', async () => {
  const f = basinBot({ abort: true });
  await assert.rejects(f.run(), error => {
    assert.equal(error.code, 'ACTION_SETTLEMENT_TIMEOUT');
    assert.equal(error.budget_usage.max_blocks_changed, 2);
    return true;
  });
  assert.equal(f.uses(), 1);
  assert.equal(f.converted.size, 1);
  assert.equal(f.bot.listenerCount('blockUpdate'), 0);
});
