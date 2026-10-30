import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import prismarineBlock from 'prismarine-block';
import * as placement from '../src/placement.js';
import { withActionEvidence } from '../src/runtime/actionEvidence.js';

import {
  createCraftingTablePlacementBudget,
  placeCraftingTableWithTimeout,
  recoverPlacedCraftingTableAfterTimeout,
} from '../src/crafting/placement.js';

test('native table selection skips the R60 fern reference and keeps its single table for solid ground', async () => {
  const registry = minecraftData('1.21.1');
  const Block = prismarineBlock(registry);
  const world = new Map();
  const make = (name, position) => {
    const block = Block.fromStateId(registry.blocksByName[name].minStateId, 0);
    block.position = position;
    return block;
  };
  for (const [name, x, y, z] of [
    ['dirt', -10, 63, 21], ['fern', -9, 63, 21], ['grass_block', -11, 63, 21],
    ['vine', -10, 63, 20], ['grass_block', -10, 63, 22],
  ]) {
    const block = make(name, new Vec3(x, y, z));
    world.set(String(block.position), block);
  }
  const item = { name: 'crafting_table', count: 1 };
  const references = [];
  const bot = Object.assign(new EventEmitter(), {
    entity: { position: new Vec3(-10, 64, 21), onGround: true }, health: 20,
    inventory: { items: () => item.count ? [item] : [] },
    blockAt: position => world.get(String(position)) || make('air', position),
    findBlock: () => [...world.values()].find(b => b.name === 'crafting_table') || null,
    async equip() { assert.equal(item.count, 1); this.heldItem = item; },
    async lookAt() {},
    async placeBlock(reference, face) {
      references.push(reference.name);
      const replace = reference.name === 'fern';
      const position = replace ? reference.position : reference.position.plus(face);
      const before = this.blockAt(position);
      const table = make('crafting_table', position);
      world.set(String(position), table);
      item.count = 0;
      this.emit('blockUpdate', before, table);
      if (replace) throw Object.assign(new Error('SDK waited above the replaced fern'), { code: 'ACTION_TIMEOUT' });
      this.emit('blockPlaced', before, table);
    },
  });
  const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  const start = source.indexOf('async function _ensureCraftingTable(');
  const end = source.indexOf('\nasync function _reclaimCraftingTable(', start);
  assert.ok(start >= 0 && end > start);
  const ensure = runInNewContext(`(${source.slice(start, end)})`, {
    bot, Vec3, operationWait: async () => {},
    createCraftingTablePlacementBudget, recoverPlacedCraftingTableAfterTimeout,
    isFullCubeReference: placement.isFullCubeReference,
    findReachableCraftingTable: () => assert.fail('a local table must not require remote navigation'),
  });
  const result = await withActionEvidence(bot, () => ensure(registry, { budget: { max_blocks_changed: 8 } }));
  assert.equal(result.output?.name, 'crafting_table');
  assert.deepEqual(references, ['grass_block']);
  assert.equal(result.output.position.equals(new Vec3(-11, 64, 21)), true);
  assert.equal(bot.blockAt(new Vec3(-9, 63, 21)).name, 'fern');
  assert.equal(result.budget_usage.max_blocks_changed, 1);
  assert.equal(item.count, 0);
});

test('crafting table placement returns the completed placement result', async () => {
  const result = await placeCraftingTableWithTimeout(async () => 'placed', 50);

  assert.equal(result, 'placed');
});

test('crafting table placement rejects a stalled Mineflayer action with a structured timeout', async () => {
  const stalled = new Promise(() => {});

  await assert.rejects(
    placeCraftingTableWithTimeout(() => stalled, 5),
    (error) => error.code === 'CRAFT_TABLE_PLACE_TIMEOUT',
  );
});

test('crafting table placement recovers a table that appears just after timeout', async () => {
  const placed = { name: 'crafting_table' };
  let visible = false;
  const result = await recoverPlacedCraftingTableAfterTimeout({
    error: { code: 'CRAFT_TABLE_PLACE_TIMEOUT' },
    findPlaced: () => visible ? placed : null,
    wait: async () => { visible = true; },
  });

  assert.equal(result, placed);
});

test('crafting table placement budget bounds the number of candidate blocks', async () => {
  const budget = createCraftingTablePlacementBudget({
    maxAttempts: 2,
    totalTimeoutMs: 1_000,
    perAttemptTimeoutMs: 50,
  });
  let calls = 0;
  const rejectPlacement = async () => {
    calls += 1;
    throw new Error('invalid candidate');
  };

  await assert.rejects(budget.place(rejectPlacement), /invalid candidate/);
  await assert.rejects(budget.place(rejectPlacement), /invalid candidate/);
  await assert.rejects(
    budget.place(rejectPlacement),
    (error) => error.code === 'CRAFT_TABLE_PLACE_BUDGET_EXHAUSTED',
  );
  assert.equal(calls, 2);
});

test('crafting table placement budget rejects candidates after its total deadline', async () => {
  let now = 100;
  const budget = createCraftingTablePlacementBudget({
    totalTimeoutMs: 30,
    now: () => now,
  });
  now = 131;

  await assert.rejects(
    budget.place(async () => 'placed'),
    (error) => error.code === 'CRAFT_TABLE_PLACE_BUDGET_EXHAUSTED',
  );
});
