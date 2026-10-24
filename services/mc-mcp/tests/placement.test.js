import assert from 'node:assert/strict';
import test from 'node:test';
import { EventEmitter } from 'node:events';
import * as placementActions from '../src/placement.js';
import { withActionEvidence } from '../src/runtime/actionEvidence.js';

import {
  findPlacementReference,
  normalizePlacementBlockName,
  orientForPlacement,
  placeOrientedBlock,
  placementMutation,
  placementMutations,
} from '../src/placement.js';

class Vec {
  constructor(x, y, z) {
    this.x = x;
    this.y = y;
    this.z = z;
  }

  offset(x, y, z) {
    return new Vec(this.x + x, this.y + y, this.z + z);
  }
}

test('placement finds an adjacent wall reference when the block below is air', () => {
  const target = new Vec(6, 68, 6);
  const blocks = new Map([
    ['5,68,6', { name: 'oak_planks', position: new Vec(5, 68, 6) }],
  ]);
  const bot = {
    blockAt(position) {
      return blocks.get(`${position.x},${position.y},${position.z}`)
        || { name: 'air', position };
    },
  };

  const result = findPlacementReference(bot, target, Vec);

  assert.equal(result.reference.name, 'oak_planks');
  assert.deepEqual(result.face, new Vec(1, 0, 0));
});

test('placement prefers a full cube beside the target over a thin door below it', () => {
  const target = new Vec(6, 68, 4);
  const blocks = new Map([
    ['6,67,4', {
      name: 'oak_door',
      position: new Vec(6, 67, 4),
      shapes: [[0, 0, 0, 0.1875, 1, 1]],
    }],
    ['5,68,4', {
      name: 'oak_planks',
      position: new Vec(5, 68, 4),
      shapes: [[0, 0, 0, 1, 1, 1]],
    }],
  ]);
  const bot = {
    blockAt(position) {
      return blocks.get(`${position.x},${position.y},${position.z}`)
        || { name: 'air', position, shapes: [] };
    },
  };

  const result = findPlacementReference(bot, target, Vec);

  assert.equal(result.reference.name, 'oak_planks');
  assert.deepEqual(result.face, new Vec(1, 0, 0));
});

test('bed placement looks along the compiled head direction before use', async () => {
  const calls = [];
  const bot = {
    async look(...args) {
      calls.push(args);
    },
  };

  for (const facing of ['north', 'south', 'east', 'west']) {
    await orientForPlacement(bot, 'white_bed', facing);
  }

  assert.deepEqual(calls, [
    [0, 0],
    [Math.PI, 0],
    [-Math.PI / 2, 0],
    [Math.PI / 2, 0],
  ]);
});

test('bed placement preserves the chosen yaw while sending the place packet', async () => {
  const calls = [];
  const reference = { name: 'oak_planks' };
  const face = new Vec(0, 1, 0);
  const bot = {
    async look(...args) {
      calls.push(['look', ...args]);
    },
    async placeBlock(...args) {
      calls.push(['placeBlock', ...args]);
    },
    async _placeBlockWithOptions(...args) {
      calls.push(['placeBlockWithOptions', ...args]);
    },
  };

  await placeOrientedBlock(bot, { reference, face }, 'white_bed', 'south');

  assert.deepEqual(calls, [
    ['look', Math.PI, 0],
    [
      'placeBlockWithOptions',
      reference,
      face,
      { forceLook: 'ignore', swingArm: 'right' },
    ],
  ]);
});

test('placement normalizes namespaced palette entries and claims exact mutation', () => {
  assert.equal(normalizePlacementBlockName('minecraft:oak_planks'), 'oak_planks');
  assert.deepEqual(
    placementMutation(
      'minecraft:oak_planks',
      { x: 6, y: 68, z: 6 },
      'minecraft:overworld',
    ),
    {
      kind: 'block',
      subject: 'block:minecraft:overworld:6:68:6',
      delta: 1,
      details: { block_type: 'minecraft:oak_planks' },
    },
  );
});

test('two-block placements claim both mutations and consume two block changes', () => {
  const target = new Vec(6, 65, 6);

  const door = placementMutations('minecraft:oak_door', target);
  assert.deepEqual(
    door.map(mutation => mutation.subject),
    [
      'block:minecraft:overworld:6:65:6',
      'block:minecraft:overworld:6:66:6',
    ],
  );

  const bed = placementMutations(
    'minecraft:white_bed',
    target,
    'minecraft:overworld',
    [new Vec(6, 65, 7)],
  );
  assert.deepEqual(
    bed.map(mutation => mutation.subject),
    [
      'block:minecraft:overworld:6:65:6',
      'block:minecraft:overworld:6:65:7',
    ],
  );
});

function snowPlacementFixture(name = 'snow') {
  const bot = new EventEmitter();
  const targetPosition = new Vec(6, 64, 6);
  let target = { name, type: name === 'air' ? 0 : 1, position: targetPosition };
  let stock = [{ name: 'obsidian', count: 10, slot: 10 }];
  const calls = [];
  const movements = { canDig: true, allow1by1towers: true, scafoldingBlocks: [4], canOpenDoors: true };
  Object.assign(bot, {
    entity: { position: { x: 4.5, y: 64, z: 6.5 } }, health: 20,
    game: { dimension: 'minecraft:overworld' },
    inventory: { items: () => stock },
    pathfinder: { movements, setGoal() {}, stop() {} },
    blockAt(p) {
      if (p.x === 6 && p.y === 64 && p.z === 6) return target;
      return { name: 'stone', type: 2, position: p, shapes: [[0, 0, 0, 1, 1, 1]] };
    },
    async equip(item) { calls.push(['equip', item.slot]); bot.heldItem = item; },
    async lookAt() {},
    async placeBlock() {
      calls.push(['place']);
      const before = target;
      target = { name: 'obsidian', type: 3, position: targetPosition };
      bot.emit('blockPlaced', before, target);
    },
  });
  const context = { budget: { max_blocks_changed: 2 } };
  const options = { blockName: 'obsidian', targetPosition, context };
  const effects = {
    async navigate() {
      calls.push(['navigate']);
      assert.equal(movements.canDig, false);
      assert.equal(movements.allow1by1towers, false);
      assert.deepEqual(movements.scafoldingBlocks, []);
    },
    async dig(block) {
      calls.push(['dig', block.name]);
      target = { name: 'air', type: 0, position: targetPosition };
      bot.emit('blockUpdate', block, target);
      bot.emit('diggingCompleted', target);
      stock = [{ name: 'obsidian', count: 10, slot: 36 }];
    },
    async wait() {},
  };
  const run = () => withActionEvidence(bot, () => placementActions.placeBlockAt(bot, options, effects));
  return { bot, context, options, effects, calls, run, replaceTarget(value) { target = value; } };
}

test('snow clearance and placement charge two confirmed changes and equip the live stack', async () => {
  const f = snowPlacementFixture();
  const result = await f.run();
  assert.equal(result.output.placed, true);
  assert.equal(result.budget_usage.max_blocks_changed, 2);
  assert.deepEqual(f.calls, [['navigate'], ['dig', 'snow'], ['equip', 36], ['place']]);
  assert.equal(f.bot.pathfinder.movements.canDig, true);
});

test('snow with only a one-block reservation stops before movement or mutation', async () => {
  const f = snowPlacementFixture();
  f.context.budget.max_blocks_changed = 1;
  await assert.rejects(f.run(), error => error.code === 'BUDGET_EXHAUSTED');
  assert.deepEqual(f.calls, []);
});

test('clear success followed by placement failure preserves the one actual change', async () => {
  const f = snowPlacementFixture();
  const failure = Object.assign(new Error('placement failed'), { code: 'ACTION_FAILED' });
  f.bot.placeBlock = async () => { throw failure; };
  await assert.rejects(f.run(), error => error === failure && error.budget_usage.max_blocks_changed === 1);
});

test('an already-present block is idempotent without a phantom placement mutation', async () => {
  const f = snowPlacementFixture('obsidian');
  const result = await f.run();
  assert.equal(result.output.placed, false);
  assert.equal(result.budget_usage.max_blocks_changed, 0);
  assert.deepEqual(f.calls, []);
});

test('snow clearance never admits other occupied or unknown target blocks', async () => {
  for (const name of ['snow_block', 'powder_snow', 'stone', null]) {
    const f = snowPlacementFixture(name);
    if (name === null) f.replaceTarget(null);
    await assert.rejects(f.run());
    assert.deepEqual(f.calls, []);
  }
});

test('a target changed during navigation is read again before any excavation', async () => {
  const f = snowPlacementFixture();
  f.effects.navigate = async () => {
    f.replaceTarget({ name: 'stone', type: 2, position: f.options.targetPosition });
  };
  await assert.rejects(f.run());
  assert.deepEqual(f.calls, []);
});

test('cancellation after clearing snow cannot proceed to placement', async () => {
  const f = snowPlacementFixture();
  const controller = new AbortController();
  f.context.signal = controller.signal;
  const dig = f.effects.dig;
  f.effects.dig = async block => { await dig(block); controller.abort(); };
  await assert.rejects(f.run(), error => error.name === 'AbortError' && error.budget_usage.max_blocks_changed === 1);
  assert.equal(f.calls.some(([kind]) => kind === 'place'), false);
});

test('empty or changed held material after equip or aiming stops before placement', async () => {
  for (const phase of ['equip', 'aim-empty', 'aim-changed']) {
    const f = snowPlacementFixture();
    if (phase === 'equip') f.bot.equip = async () => { f.bot.heldItem = null; };
    else f.bot.lookAt = async () => {
      f.bot.heldItem = phase === 'aim-empty' ? null : { name: 'stone_pickaxe' };
    };
    await assert.rejects(f.run(), error => error.code === 'PLACEMENT_ITEM_CHANGED'
      && error.budget_usage.max_blocks_changed === 1);
    assert.equal(f.calls.some(([kind]) => kind === 'place'), false);
  }
});
