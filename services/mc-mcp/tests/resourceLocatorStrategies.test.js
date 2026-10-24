import test from 'node:test';
import assert from 'node:assert/strict';
import { ResourceMemory } from '../src/resources/memory.js';
import { locateResource } from '../src/resources/locator.js';
import { getResourceDefinition } from '../src/resources/registry.js';
import {
  STRATEGIES,
  findNearestMatchingBlock,
} from '../src/resources/strategies.js';

test('species-specific wood search finds nearby spruce without moving or accepting it as oak', async () => {
  const spruce = { name: 'spruce_log', type: 12, position: pos(-51, 68, -196) };
  const bot = {
    entity: { position: pos(-48, 68, -193) },
    findBlock({ matching }) { return matching(spruce) ? spruce : null; },
    pathfinder: { goto() { assert.fail('visible spruce requires no exploratory movement'); } },
  };
  const candidate = await locateResource(bot, 'spruce_log', {
    mcData: { blocksByName: { oak_log: { id: 11 }, spruce_log: { id: 12 } } },
  });
  assert.equal(candidate.block, 'spruce_log');
  assert.equal(candidate.resource, 'spruce_log');
  assert.deepEqual(candidate.position, { x: -51, y: 68, z: -196 });
  assert.deepEqual(getResourceDefinition('oak_log').blocks, ['oak_log']);
  for (const field of ['maxDistance', 'attemptBudget', 'timeBudgetMs']) {
    assert.equal(getResourceDefinition('spruce_log')[field], getResourceDefinition('oak_log')[field]);
  }
});

test('locator retains a bounded history of strategy failures in its terminal error', async () => {
  const original = STRATEGIES.memory_first;
  let attempt = 0;
  STRATEGIES.memory_first = async () => {
    throw Object.assign(new Error(`path probe failed ${attempt++}`), { code: 'PATH_FAILED' });
  };
  try {
    await assert.rejects(locateResource({
      inventory: { items: () => [{ name: 'stone_pickaxe' }] },
    }, 'iron_ore', {
      mcData: {},
      allowedStrategies: Array.from({ length: 8 }, () => 'memory_first'),
    }), (error) => {
      assert.equal(error.code, 'RESOURCE_NOT_FOUND');
      assert.equal(error.search_failures.length, 5);
      assert.equal(error.search_failures[0].message, 'path probe failed 3');
      assert.equal(error.search_failures[4].message, 'path probe failed 7');
      assert.equal(error.search_failures[4].code, 'PATH_FAILED');
      return true;
    });
  } finally {
    STRATEGIES.memory_first = original;
  }
});

function pos(x, y, z) {
  return {
    x,
    y,
    z,
    offset(dx, dy, dz) {
      return pos(x + dx, y + dy, z + dz);
    },
    floored() {
      return pos(Math.floor(this.x), Math.floor(this.y), Math.floor(this.z));
    },
    clone() {
      return pos(this.x, this.y, this.z);
    },
    distanceTo(other) {
      return Math.hypot(this.x - other.x, this.y - other.y, this.z - other.z);
    },
  };
}

test('multi-species locator scans one palette and returns the actual nearest species', () => {
  const far = { name: 'oak_log', type: 11, position: pos(30, 64, 0) };
  const near = { name: 'birch_log', type: 12, position: pos(3, 64, 0) };
  let scans = 0;
  const bot = {
    findBlock({ matching, maxDistance }) {
      scans++;
      assert.equal(maxDistance, 48);
      return [near, far].find(matching) || null;
    },
  };
  const found = findNearestMatchingBlock(bot, {
    blocksByName: { oak_log: { id: 11 }, birch_log: { id: 12 } },
  }, ['oak_log', 'birch_log'], 48);
  assert.equal(found, near, 'species priority must not hide a closer usable tree');
  assert.equal(scans, 1);
});

function surfaceSearchContext(deadline = Date.now() + 20_000) {
  return {
    def: getResourceDefinition('any_log'), memory: new ResourceMemory(),
    options: { maxDistance: 48, excludedTargets: new Set() },
    mcData: { blocksByName: { oak_log: { id: 11 }, birch_log: { id: 12 } } },
    deadline, attempts: 0,
  };
}

test('surface exploration accepts natural ground height instead of an occupied old altitude', async () => {
  const ctx = surfaceSearchContext();
  let moved = false;
  const goals = [];
  const birch = { name: 'birch_log', type: 12, position: pos(-180, 72, -600) };
  const bot = {
    entity: { position: pos(-195, 71, -600) },
    findBlock: ({ matching }) => moved && matching(birch) ? birch : null,
    pathfinder: {
      stop() {},
      async goto(goal) {
        goals.push(goal);
        // R21 typed survey: (-187,71,-600) is grass; feet must be at Y=72.
        const surface = pos(goal.x, 72, goal.z);
        if (!goal.isEnd(surface)) throw new Error('goal requires the old height inside ground');
        bot.entity.position = surface;
        moved = true;
      },
    },
  };
  const found = await STRATEGIES.surface_sweep(bot, ctx);
  assert.equal(found?.block, 'birch_log');
  assert.equal(goals.length, 1);
  assert.equal(ctx.attempts, 1);
  assert.equal(goals[0].isEnd(pos(-187, 72, -600)), true, 'installed SDK goal permits surface height');
});

test('surface movement uses remaining deadline and admits no second move after expiry', async t => {
  t.mock.timers.enable({ apis: ['Date'], now: 10_000 });
  const originalTimeout = globalThis.setTimeout;
  const timeouts = [];
  t.mock.method(globalThis, 'setTimeout', (callback, ms) => {
    timeouts.push(ms);
    return originalTimeout(callback, ms);
  });
  const ctx = surfaceSearchContext(12_000);
  let moves = 0;
  const bot = {
    entity: { position: pos(0, 64, 0) }, findBlock: () => null,
    pathfinder: {
      stop() {},
      async goto() { moves++; t.mock.timers.setTime(14_001); },
    },
  };
  assert.equal(await STRATEGIES.surface_sweep(bot, ctx), null);
  assert.equal(moves, 1);
  assert.deepEqual(timeouts, [2000], 'the existing 6s move allowance is capped by time remaining');
});

test('resource scans ignore caller-excluded block coordinates', () => {
  const excluded = { name: 'iron_ore', type: 42, position: pos(11, 28, 0) };
  const available = { name: 'iron_ore', type: 42, position: pos(18, 16, 4) };
  const blocks = [excluded, available];
  const bot = {
    findBlock({ matching }) {
      assert.equal(
        matching({ type: 42 }),
        true,
        'palette prefilter blocks do not carry coordinates',
      );
      return blocks.find((block) => matching(block)) || null;
    },
  };

  const found = findNearestMatchingBlock(
    bot,
    { blocksByName: { iron_ore: { id: 42 } } },
    ['iron_ore'],
    64,
    new Set(['11,28,0']),
  );

  assert.equal(found, available);
});

test('branch_mine advances through a supported tunnel before rescanning for iron', async () => {
  const entityPosition = pos(0, 64, 0);
  const iron = { name: 'iron_ore', type: 42, boundingBox: 'block', position: pos(3, 64, 0) };
  const cleared = new Set();
  const key = position => `${position.x},${position.y},${position.z}`;
  const bot = {
    entity: { position: entityPosition, yaw: Math.PI / 2 },
    health: 20,
    food: 20,
    nearestEntity() {
      return null;
    },
    inventory: {
      items() {
        return [{ name: 'stone_pickaxe' }];
      },
    },
    pathfinder: {
      stop() {},
      async goto(goal) {
        assert.equal(bot.blockAt(pos(goal.x, goal.y - 1, goal.z)).boundingBox, 'block');
        assert.equal(bot.blockAt(pos(goal.x, goal.y, goal.z)).name, 'air');
        assert.equal(bot.blockAt(pos(goal.x, goal.y + 1, goal.z)).name, 'air');
        entityPosition.x = goal.x;
        entityPosition.y = goal.y;
        entityPosition.z = goal.z;
      },
    },
    stopDigging() {},
    async equip() {},
    async lookAt() {},
    async dig(block) { cleared.add(key(block.position)); },
    blockAt(blockPos) {
      if (cleared.has(key(blockPos))) {
        return { name: 'air', boundingBox: 'empty', position: blockPos };
      }
      if (blockPos.y === 63) {
        return { name: 'stone', boundingBox: 'block', position: blockPos };
      }
      return { name: 'stone', boundingBox: 'block', position: blockPos };
    },
    findBlock() {
      return entityPosition.z >= 1 ? iron : null;
    },
    setControlState(name, value) {
      assert.equal(value, false, `manual ${name} must not replace supported navigation`);
    },
  };
  const context = {
    def: {
      canonical: 'iron_ore',
      blocks: ['iron_ore'],
      requiredTool: 'stone_pickaxe',
      attemptBudget: 6,
    },
    memory: new ResourceMemory(),
    options: { maxDistance: 48 },
    mcData: { blocksByName: { iron_ore: { id: 42 } } },
    deadline: Date.now() + 15_000,
    attempts: 0,
  };

  const candidate = await STRATEGIES.branch_mine(bot, context);

  assert.equal(candidate?.block, 'iron_ore');
  assert.equal(candidate?.strategy, 'branch_mine');
  assert.equal(entityPosition.z, 1);
});

test('safe_descent advances toward the resource target layer instead of stopping at range maximum', async () => {
  const entityPosition = pos(0, 64, 0);
  const dug = [];
  const bot = {
    entity: { position: entityPosition },
    health: 20,
    food: 20,
    nearestEntity() {
      return null;
    },
    blockAt(blockPos) {
      return { name: 'stone', boundingBox: 'block', position: blockPos };
    },
    async dig(block) {
      dug.push(block.position.y);
    },
    findBlock() {
      return null;
    },
  };
  const context = {
    def: {
      canonical: 'iron_ore',
      blocks: ['iron_ore'],
      preferredY: { min: -16, max: 72 },
      targetY: 16,
      attemptBudget: 6,
    },
    memory: new ResourceMemory(),
    options: { maxDistance: 48 },
    mcData: { blocksByName: { iron_ore: { id: 42 } } },
    deadline: Date.now() + 15_000,
    attempts: 0,
  };

  await STRATEGIES.safe_descent(bot, context);

  assert.deepEqual(dug, [63, 62, 61, 60, 59, 58]);
});
