import test from 'node:test';
import assert from 'node:assert/strict';
import minecraftData from 'minecraft-data';
import pathfinderPackage from 'mineflayer-pathfinder';
import { configureMineSupport, createBranchMine } from '../src/branch_mine.js';

test('return navigation can use carried deepslate without spending portal obsidian', () => {
  const registry = minecraftData('1.21.1');
  const bot = { registry, inventory: { items: () => [
    { type: registry.itemsByName.cobbled_deepslate.id, count: 118 },
    { type: registry.itemsByName.cobblestone.id, count: 27 },
    { type: registry.itemsByName.dirt.id, count: 4 },
    { type: registry.itemsByName.obsidian.id, count: 14 },
  ] } };
  const movements = new pathfinderPackage.Movements(bot);
  assert.equal(movements.countScaffoldingItems(), 31);
  configureMineSupport(movements, registry);
  assert.equal(movements.countScaffoldingItems(), 149);
});

function pos(x, y, z) {
  return {
    x,
    y,
    z,
    offset(dx, dy, dz) {
      return pos(x + dx, y + dy, z + dz);
    },
  };
}

function branchFixture(options) {
  const bot = options.bot;
  bot.pathfinder = { stop() {}, ...bot.pathfinder, async goto(goal) {
    Object.assign(bot.entity.position, { x: goal.x + 0.5, y: goal.y, z: goal.z + 0.5 });
  } };
  return createBranchMine(options);
}

test('branchMine stops on navigation failure without manual forward fallback', async () => {
  const position = { x: 0, y: 64, z: 0, floored: () => pos(0, 64, 0) };
  const bot = {
    entity: { position },
    blockAt: p => ({ name: p.y === 63 ? 'stone' : 'air',
      boundingBox: p.y === 63 ? 'block' : 'empty', position: p }),
    lookAt: async () => {},
    pathfinder: { goto: async () => { throw new Error('No path'); }, stop() {} },
    setControlState: (_control, value) => assert.equal(value, false),
  };
  await assert.rejects(createBranchMine({ bot, wait: async () => {} }).branchMine(1), /No path/);
  assert.equal(position.x, 0);
});

test('branchMine digs a two-high tunnel and navigates only to each supported cell', async () => {
  const dug = [];
  const controls = [];
  const bot = {
    entity: {
      yaw: Math.PI / 2,
      position: {
        x: 0,
        y: -54,
        z: 0,
        floored() {
          return pos(Math.floor(this.x), Math.floor(this.y), Math.floor(this.z));
        },
        clone() {
          return { x: this.x, y: this.y, z: this.z };
        },
      },
    },
    inventory: {
      items() {
        return [{ name: 'iron_pickaxe' }];
      },
    },
    async equip() {},
    async lookAt() {},
    blockAt(p) {
      if (p.y === -55) return { name: 'deepslate', boundingBox: 'block', position: p };
      if (p.y === -54 || p.y === -53) return { name: 'deepslate', boundingBox: 'block', position: p };
      return { name: 'air', boundingBox: 'empty', position: p };
    },
    async dig(block) {
      dug.push(`${block.position.x},${block.position.y},${block.position.z}`);
    },
    setControlState(name, value) {
      controls.push([name, value]);
      if (name === 'forward' && value) this.entity.position.z += 1;
    },
  };

  const branch = branchFixture({ bot, wait: async () => {} });
  const result = await branch.branchMine(2);

  assert.match(result, /Branch mined/);
  assert.deepEqual(dug, ['0,-53,1', '0,-54,1', '0,-53,2', '0,-54,2']);
  assert(!controls.some(([_name, value]) => value === true));
  assert(controls.some(([name, value]) => name === 'forward' && value === false));
});

test('branchMine rejects unsupported forward steps', async () => {
  const bot = {
    entity: {
      yaw: Math.PI / 2,
      position: {
        x: 0,
        y: -54,
        z: 0,
        floored() {
          return pos(0, -54, 0);
        },
      },
    },
    blockAt(p) {
      return { name: p.y === -55 ? 'air' : 'deepslate', boundingBox: p.y === -55 ? 'empty' : 'block', position: p };
    },
    setControlState() {},
  };

  const branch = branchFixture({ bot, wait: async () => {} });

  await assert.rejects(
    () => branch.branchMine(1),
    (err) => {
      assert.equal(err.code, 'BRANCH_MINE_UNSAFE');
      return true;
    }
  );
});

test('branchMine tries another direction when the forward step is unsupported', async () => {
  const dug = [];
  const bot = {
    entity: {
      yaw: Math.PI / 2,
      position: {
        x: 0,
        y: -54,
        z: 0,
        floored() {
          return pos(Math.floor(this.x), Math.floor(this.y), Math.floor(this.z));
        },
        clone() {
          return { x: this.x, y: this.y, z: this.z };
        },
      },
    },
    inventory: {
      items() {
        return [{ name: 'iron_pickaxe' }];
      },
    },
    async equip() {},
    async lookAt() {},
    blockAt(p) {
      if (p.y === -55 && p.x === 1 && p.z === 0) return { name: 'deepslate', boundingBox: 'block', position: p };
      if (p.y === -55) return { name: 'air', boundingBox: 'empty', position: p };
      if (p.y === -54 || p.y === -53) return { name: 'deepslate', boundingBox: 'block', position: p };
      return { name: 'air', boundingBox: 'empty', position: p };
    },
    async dig(block) {
      dug.push(`${block.position.x},${block.position.y},${block.position.z}`);
    },
    setControlState(name, value) {
      if (name === 'forward' && value) this.entity.position.x += 1;
    },
  };

  const branch = branchFixture({ bot, wait: async () => {} });
  const result = await branch.branchMine(1);

  assert.match(result, /Branch mined/);
  assert.deepEqual(dug, ['1,-53,0', '1,-54,0']);
});

test('branchMine bridges one support block when all adjacent steps are unsupported', async () => {
  const dug = [];
  const placed = [];
  const support = new Set(['0,-55,0']);
  const bot = {
    entity: {
      yaw: Math.PI / 2,
      position: {
        x: 0,
        y: -54,
        z: 0,
        floored() {
          return pos(Math.floor(this.x), Math.floor(this.y), Math.floor(this.z));
        },
        clone() {
          return { x: this.x, y: this.y, z: this.z };
        },
      },
    },
    inventory: {
      items() {
        return [{ name: 'cobblestone' }, { name: 'iron_pickaxe' }];
      },
    },
    async equip() {},
    async lookAt() {},
    blockAt(p) {
      const key = `${p.x},${p.y},${p.z}`;
      if (support.has(key)) return { name: 'cobblestone', boundingBox: 'block', position: p };
      if (p.y === -55) return { name: 'air', boundingBox: 'empty', position: p };
      if (p.y === -54 || p.y === -53) return { name: 'deepslate', boundingBox: 'block', position: p };
      return { name: 'air', boundingBox: 'empty', position: p };
    },
    async placeBlock(reference, face) {
      placed.push(`${reference.position.x + face.x},${reference.position.y + face.y},${reference.position.z + face.z}`);
      support.add(placed.at(-1));
    },
    async dig(block) {
      dug.push(`${block.position.x},${block.position.y},${block.position.z}`);
    },
    setControlState(name, value) {
      if (name === 'forward' && value) this.entity.position.z += 1;
    },
  };

  const branch = branchFixture({ bot, wait: async () => {} });
  const result = await branch.branchMine(1);

  assert.match(result, /Branch mined/);
  assert.deepEqual(placed, ['0,-55,1']);
  assert.deepEqual(dug, ['0,-53,1', '0,-54,1']);
});

test('branchMine retries once after stale Digging aborted state', async () => {
  let digCalls = 0;
  let stopped = 0;
  const bot = {
    entity: {
      yaw: Math.PI / 2,
      position: {
        x: 0,
        y: -54,
        z: 0,
        floored() {
          return pos(0, -54, 0);
        },
        clone() {
          return { x: this.x, y: this.y, z: this.z };
        },
      },
    },
    inventory: {
      items() {
        return [{ name: 'iron_pickaxe' }];
      },
    },
    pathfinder: {
      stop() {},
    },
    stopDigging() {
      stopped += 1;
    },
    async equip() {},
    async lookAt() {},
    blockAt(p) {
      if (p.y === -55) return { name: 'deepslate', boundingBox: 'block', position: p };
      if (p.y === -54) return { name: 'deepslate', boundingBox: 'block', position: p };
      return { name: 'air', boundingBox: 'empty', position: p };
    },
    async dig() {
      digCalls += 1;
      if (digCalls === 1) throw new Error('Digging aborted');
    },
    setControlState(name, value) {
      if (name === 'forward' && value) this.entity.position.z += 1;
    },
  };

  const branch = branchFixture({ bot, wait: async () => {} });
  const result = await branch.branchMine(1);

  assert.match(result, /Branch mined/);
  assert.equal(digCalls, 2);
  assert(stopped >= 2);
});
