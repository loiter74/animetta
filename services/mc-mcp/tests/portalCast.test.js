import assert from 'node:assert/strict';
import test from 'node:test';
import { EventEmitter } from 'node:events';
import Vec3 from 'vec3';
import pathfinderPkg from 'mineflayer-pathfinder';
import minecraftData from 'minecraft-data';
import { buildInfiniteWaterSource } from '../src/renewable.js';
import { castNetherPortalFrame, fillLavaBucket, harvestLavaBucket, scoopLavaBucket } from '../src/portalCast.js';

const wait = async () => {};

function completeLook(bot, point) {
  const delta = point.minus(bot.entity.position.offset(0, 1.62, 0));
  bot.entity.yaw = Math.atan2(-delta.x, -delta.z);
  bot.entity.pitch = Math.atan2(delta.y, Math.hypot(delta.x, delta.z));
  bot.emit('move');
}

// Terrain fixture with a real 1.21.1 registry, pathfinder teleports, and
// bucket activation semantics for lava scooping/pouring and water casting.
function portalBot({ position, groundY = 63, groundName = 'stone', overrides = new Map() } = {}) {
  const registry = minecraftData('1.21.1');
  const bot = new EventEmitter();
  bot.registry = registry;
  bot.health = 20;
  bot.game = { minY: -64, height: 384 };
  bot.entity = { position: position.clone(), onGround: true, velocity: new Vec3(0, 0, 0), effects: {} };
  bot.items = [];
  bot.inventory = { items: () => bot.items };
  bot.entities = {};
  bot.heldItem = null;
  bot.digs = 0;
  bot.uses = 0;
  bot.poured = [];

  const key = p => `${p.x},${p.y},${p.z}`;
  const set = (position, name) => overrides.set(key(position), name);
  const get = position => blockAt(position).name;
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
  bot.findBlocks = ({ matching }) => {
    const ids = Array.isArray(matching) ? matching : [matching];
    const results = [];
    for (const [cell, name] of overrides) {
      const id = registry.blocksByName[name]?.id;
      if (ids.includes(id)) {
        const [x, y, z] = cell.split(',').map(Number);
        results.push(new Vec3(x, y, z));
      }
    }
    return results;
  };

  const addItem = (name, count = 1) => {
    const stack = bot.items.find(item => item.name === name);
    if (stack) stack.count += count;
    else bot.items.push({ name, count });
  };
  const consumeHeld = () => {
    bot.heldItem.count--;
    if (bot.heldItem.count <= 0) bot.items = bot.items.filter(item => item !== bot.heldItem);
    bot.heldItem = null;
  };

  bot.equip = async (item, _slot) => { bot.heldItem = item; };
  let lookTarget = null;
  bot.lookAt = async point => { lookTarget = point; completeLook(bot, point); };
  bot.activateItem = () => {
    bot.uses++;
    const held = bot.heldItem;
    if (!lookTarget || !held) return;
    const cell = new Vec3(Math.floor(lookTarget.x), Math.floor(lookTarget.y), Math.floor(lookTarget.z));
    if (held.name === 'lava_bucket') {
      set(cell.offset(0, 1, 0), 'lava');
      bot.poured.push(cell.offset(0, 1, 0));
      consumeHeld();
      addItem('bucket');
    } else if (held.name === 'water_bucket') {
      if (get(cell) === 'lava') {
        // Casting: water hits a lava source and solidifies it.
        set(cell, 'obsidian');
        if (get(cell.offset(0, 1, 0)) === 'air') set(cell.offset(0, 1, 0), 'water');
      } else {
        // Plain pour: the fluid lands one cell above the aimed floor face.
        set(cell.offset(0, 1, 0), 'water');
        bot.poured.push(cell.offset(0, 1, 0));
      }
      consumeHeld();
      addItem('bucket');
    } else if (held.name === 'bucket') {
      if (get(cell) === 'lava') {
        set(cell, 'air');
        consumeHeld();
        addItem('lava_bucket');
      } else if (get(cell) === 'lava_cauldron') {
        set(cell, 'cauldron');
        consumeHeld();
        addItem('lava_bucket');
      } else if (get(cell) === 'water') {
        set(cell, 'air');
        consumeHeld();
        addItem('water_bucket');
      }
    }
    // Once both trench ends hold water sources, the middle cell settles too.
    if (bot.poured.filter(cell => get(cell) === 'water').length === 2) {
      const [first, second] = bot.poured.filter(cell => get(cell) === 'water');
      const middle = first.plus(second).scaled(0.5).floored();
      if (get(middle) === 'air') set(middle, 'water');
    }
  };
  bot.deactivateItem = () => {};
  bot.dig = async block => {
    bot.digs++;
    set(block.position, 'air');
  };
  bot.placeBlock = async (reference, face) => {
    set(reference.position.plus(face), bot.heldItem?.name);
  };

  bot.controlState = {};
  bot.clearControlStates = () => { for (const k of Object.keys(bot.controlState)) bot.controlState[k] = false; };
  bot.setControlState = (state, value) => { bot.controlState[state] = value; };
  pathfinderPkg.pathfinder(bot);
  bot.pathfinder.goto = async goal => {
    if (goal.x !== undefined) {
      bot.entity.position = new Vec3(goal.x + 0.5, goal.y, goal.z + 0.5);
    } else {
      bot.entity.position = new Vec3(bot.entity.position.x, goal.y, bot.entity.position.z);
    }
  };

  return {
    bot,
    set: (position, name) => set(position, name),
    get,
    overrides,
  };
}

test('fill_lava_bucket scoops a nearby safe lava source', async () => {
  const source = new Vec3(8, 63, 0);
  const { bot, get, set } = portalBot({ position: new Vec3(10.5, 64, 1.5) });
  bot.items = [{ name: 'bucket', count: 1 }];
  set(source, 'lava');
  const result = await fillLavaBucket(bot, {}, { wait });
  assert.equal(result.output.filled, true);
  assert.equal(result.output.source.position.toString(), source.toString());
  assert.equal(get(source), 'air');
  assert.equal(bot.items.filter(item => item.name === 'lava_bucket').length, 1);
  assert.equal(bot.items.filter(item => item.name === 'bucket').length, 0);
});

test('scoop_lava_bucket scoops a nearby safe lava source', async () => {
  const source = new Vec3(8, 63, 0);
  const { bot, get, set } = portalBot({ position: new Vec3(10.5, 64, 1.5) });
  bot.items = [{ name: 'bucket', count: 1 }];
  set(source, 'lava');
  const result = await scoopLavaBucket(bot, {}, { wait });
  assert.equal(result.output.scooped, true);
  assert.equal(result.output.source.position.toString(), source.toString());
  assert.deepEqual(result.output.scout_waypoints, []);
  assert.equal(get(source), 'air');
  assert.equal(bot.items.filter(item => item.name === 'lava_bucket').length, 1);
  assert.equal(bot.items.filter(item => item.name === 'bucket').length, 0);
});

test('scoop_lava_bucket keeps scooping with lava buckets already held', async () => {
  const source = new Vec3(8, 63, 0);
  const { bot, get, set } = portalBot({ position: new Vec3(10.5, 64, 1.5) });
  bot.items = [
    { name: 'lava_bucket', count: 2 },
    { name: 'bucket', count: 1 },
  ];
  set(source, 'lava');
  const result = await scoopLavaBucket(bot, {}, { wait });
  assert.equal(result.output.scooped, true);
  assert.equal(get(source), 'air');
  const lavaBuckets = bot.items.find(item => item.name === 'lava_bucket');
  assert.equal(lavaBuckets.count, 3);
  assert.equal(bot.items.filter(item => item.name === 'bucket').length, 0);
});

test('scoop_lava_bucket fails without an empty bucket', async () => {
  const { bot } = portalBot({ position: new Vec3(10.5, 64, 1.5) });
  bot.items = [{ name: 'lava_bucket', count: 2 }];
  await assert.rejects(scoopLavaBucket(bot, {}, { wait }), {
    code: 'TOOL_REQUIRED',
    message: '舀取岩浆前需要先合成铁桶。',
  });
});

test('scoop_lava_bucket returns gracefully when scouting finds no lava', async () => {
  const { bot } = portalBot({ position: new Vec3(10.5, 64, 1.5) });
  bot.items = [{ name: 'bucket', count: 10 }];
  const gotoCalls = [];
  const originalGoto = bot.pathfinder.goto.bind(bot.pathfinder);
  bot.pathfinder.goto = async goal => {
    gotoCalls.push({ x: goal.x, y: goal.y, z: goal.z });
    await originalGoto(goal);
  };
  const result = await scoopLavaBucket(bot, {}, { wait });
  assert.equal(result.output.scooped, false);
  assert.equal(result.output.reason, 'LAVA_REGION_NOT_FOUND');
  assert.equal(result.output.scout_waypoints.length, 4);
  assert.equal(gotoCalls.length, 4);
  const anchor = new Vec3(10, 64, 1);
  assert.deepEqual(result.output.scout_waypoints.map(entry => entry.position.toString()), [
    anchor.offset(32, 0, 0).toString(),
    anchor.offset(32, 0, 32).toString(),
    anchor.offset(0, 0, 32).toString(),
    anchor.offset(-32, 0, 32).toString(),
  ]);
  assert.equal(result.explained_mutations.length, 0);
  assert.equal(bot.items.filter(item => item.name === 'lava_bucket').length, 0);
});

test('scoop_lava_bucket scouts to a lava source beyond the local radius', async () => {
  const { bot, get, set } = portalBot({ position: new Vec3(10.5, 64, 1.5) });
  bot.items = [{ name: 'bucket', count: 10 }];
  const gotoCalls = [];
  const originalGoto = bot.pathfinder.goto.bind(bot.pathfinder);
  bot.pathfinder.goto = async goal => {
    gotoCalls.push(goal);
    await originalGoto(goal);
    // Lava only shows up once the first scout waypoint has been reached.
    if (gotoCalls.length === 1) set(new Vec3(40, 63, 1), 'lava');
  };
  const result = await scoopLavaBucket(bot, {}, { wait });
  assert.equal(result.output.scooped, true);
  assert.equal(result.output.source.position.toString(), new Vec3(40, 63, 1).toString());
  assert.equal(result.output.scout_waypoints.length, 1);
  assert.equal(result.output.scout_waypoints[0].position.toString(), new Vec3(42, 64, 1).toString());
  assert.equal(get(new Vec3(40, 63, 1)), 'air');
  assert.equal(bot.items.find(item => item.name === 'lava_bucket').count, 1);
});

test('scoop_lava_bucket skips an unreachable scout waypoint', async () => {
  const { bot, get, set } = portalBot({ position: new Vec3(10.5, 64, 1.5) });
  bot.items = [{ name: 'bucket', count: 10 }];
  const gotoCalls = [];
  const originalGoto = bot.pathfinder.goto.bind(bot.pathfinder);
  bot.pathfinder.goto = async goal => {
    gotoCalls.push(goal);
    if (goal.x === 42 && goal.z === 1) {
      // First waypoint is unreachable; lava near the second one (32, +32)
      // only becomes observable after scouting started.
      set(new Vec3(40, 63, 33), 'lava');
      throw Object.assign(new Error('第一个侦察点无法抵达。'), { code: 'NoPath' });
    }
    await originalGoto(goal);
  };
  const source = new Vec3(40, 63, 33);
  const result = await scoopLavaBucket(bot, {}, { wait });
  assert.equal(result.output.scooped, true);
  assert.equal(result.output.source.position.toString(), source.toString());
  assert.equal(result.output.scout_waypoints.length, 1);
  assert.equal(result.output.scout_waypoints[0].position.toString(), new Vec3(42, 64, 33).toString());
  assert.equal(get(source), 'air');
  assert.equal(gotoCalls.length, 2);
});

test('fill_lava_bucket fails without a nearby lava source', async () => {
  const { bot } = portalBot({ position: new Vec3(10.5, 64, 1.5) });
  bot.items = [{ name: 'bucket', count: 1 }];
  await assert.rejects(fillLavaBucket(bot, {}, { wait }), {
    code: 'LAVA_SOURCE_NOT_FOUND',
    message: '附近未观察到可以安全舀取的岩浆源。',
  });
});

test('harvest_lava_bucket drains a full lava cauldron', async () => {
  const cauldron = new Vec3(6, 63, 2);
  const { bot, get, set } = portalBot({ position: new Vec3(8.5, 64, 2.5) });
  bot.items = [{ name: 'bucket', count: 1 }];
  set(cauldron, 'lava_cauldron');
  const result = await harvestLavaBucket(bot, {}, { wait });
  assert.equal(result.output.harvested, true);
  assert.equal(result.output.position.toString(), cauldron.toString());
  assert.equal(get(cauldron), 'cauldron');
  assert.equal(bot.items.filter(item => item.name === 'lava_bucket').length, 1);
});

test('harvest_lava_bucket rejects an empty cauldron', async () => {
  const { bot, set } = portalBot({ position: new Vec3(8.5, 64, 2.5) });
  bot.items = [{ name: 'bucket', count: 1 }];
  set(new Vec3(6, 63, 2), 'cauldron');
  await assert.rejects(harvestLavaBucket(bot, {}, { wait }), {
    code: 'LAVA_CAULDRON_NOT_READY',
    message: '炼药锅尚未积满岩浆。',
  });
});

test('cast_nether_portal pours the full frame layer by layer', async () => {
  const origin = new Vec3(10, 64, 30);
  const { bot, get, set, overrides } = portalBot({ position: new Vec3(14.5, 64, 32.5) });
  bot.items = [
    { name: 'lava_bucket', count: 10 },
    { name: 'cobbled_deepslate', count: 4 },
    { name: 'dirt', count: 64 },
    { name: 'water_bucket', count: 1 },
  ];
  const result = await castNetherPortalFrame(bot, {}, { wait, x: 10, y: 64, z: 30 });
  assert.equal(result.output.created, true);
  assert.deepEqual(result.output.origin, { x: 10, y: 64, z: 30 });

  const corners = [[0, 0], [3, 0], [0, 4], [3, 4]];
  for (const [dx, dy] of corners) {
    assert.equal(get(origin.offset(dx, dy, 0)), 'cobbled_deepslate');
  }
  const obsidianCells = [
    [1, 0], [2, 0], [1, 4], [2, 4],
    [0, 1], [3, 1], [0, 2], [3, 2], [0, 3], [3, 3],
  ];
  for (const [dx, dy] of obsidianCells) {
    assert.equal(get(origin.offset(dx, dy, 0)), 'obsidian');
  }
  for (let dy = 1; dy <= 3; dy++) {
    for (const dx of [1, 2]) {
      assert.equal(get(origin.offset(dx, dy, 0)), 'air');
    }
  }
  // Temporary walls, molds, and stairs are fully removed.
  for (const dz of [1, -1]) {
    for (let dx = 0; dx <= 3; dx++) assert.equal(get(origin.offset(dx, 0, dz)), 'air');
    for (let dy = 1; dy <= 4; dy++) {
      for (const dx of [0, 3]) assert.equal(get(origin.offset(dx, dy, dz)), 'air');
      if (dy >= 3) for (const dx of [1, 2]) assert.equal(get(origin.offset(dx, dy, dz)), 'air');
    }
  }
  for (let k = 0; k <= 4; k++) {
    assert.equal(get(origin.offset(k, k, 2)), 'air');
    if (k > 0) assert.equal(get(origin.offset(k, k - 1, 2)), 'air');
  }
  // No residual fluids inside or next to the frame volume.
  for (const name of overrides.values()) {
    assert.notEqual(name, 'lava');
    assert.notEqual(name, 'water');
  }
  // 10 obsidian + 4 corner supports were placed as final frame mutations.
  const blockTypes = result.explained_mutations
    .map(mutation => mutation.details?.block_type).filter(Boolean);
  assert.equal(blockTypes.filter(type => type === 'minecraft:obsidian').length, 10);
  assert.equal(blockTypes.filter(type => type === 'minecraft:cobbled_deepslate').length, 4);
});

test('cast_nether_portal rejects an incomplete material kit', async () => {
  const { bot } = portalBot({ position: new Vec3(14.5, 64, 32.5) });
  bot.items = [
    { name: 'lava_bucket', count: 5 },
    { name: 'cobbled_deepslate', count: 4 },
    { name: 'dirt', count: 64 },
    { name: 'water_bucket', count: 1 },
  ];
  await assert.rejects(castNetherPortalFrame(bot, {}, { wait, x: 10, y: 64, z: 30 }), {
    code: 'MISSING_MATERIAL',
    message: '浇铸传送门缺少材料：需要十个岩浆桶、四块深板岩圆石、三十二个泥土和一个铁桶。',
  });
});

test('cast_nether_portal rejects an obstructed site', async () => {
  const { bot, set } = portalBot({ position: new Vec3(14.5, 64, 32.5) });
  bot.items = [
    { name: 'lava_bucket', count: 10 },
    { name: 'cobbled_deepslate', count: 4 },
    { name: 'dirt', count: 64 },
    { name: 'water_bucket', count: 1 },
  ];
  set(new Vec3(11, 64, 30), 'stone');
  await assert.rejects(castNetherPortalFrame(bot, {}, { wait, x: 10, y: 64, z: 30 }), {
    code: 'PORTAL_SITE_NOT_FOUND',
    message: '指定位置不适合浇铸传送门框架。',
  });
});

test('build_infinite_water_source builds at the requested origin', async () => {
  const origin = new Vec3(10, 63, 5);
  const { bot, get, set } = portalBot({ position: new Vec3(14.5, 64, 2.5) });
  bot.items = [{ name: 'water_bucket', count: 2 }];
  const result = await buildInfiniteWaterSource(bot, {}, { wait }, { origin: { x: 10, y: 63, z: 5 } });
  assert.equal(result.output.created, true);
  for (const dx of [0, 1, 2]) {
    assert.equal(get(origin.offset(dx, 0, 0)), 'water');
  }
  assert.equal(bot.digs, 3);
  assert.equal(bot.uses, 2);
});
