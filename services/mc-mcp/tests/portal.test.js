import assert from 'node:assert/strict';
import test from 'node:test';
import Vec3 from 'vec3';
import { acquireFlint, ignitePortal } from '../src/portal.js';

function portalBot() {
  const blocks = new Map();
  for (let y = 0; y < 5; y++) {
    for (let x = 0; x < 4; x++) {
      blocks.set(`${x},${64 + y},0`, x === 0 || x === 3 || y === 0 || y === 4 ? 'obsidian' : 'air');
    }
  }
  let ignitions = 0;
  return {
    blocks,
    entity: { position: new Vec3(1, 65, 2) },
    inventory: { items: () => [{ name: 'flint_and_steel', count: 1 }] },
    blockAt(position) {
      return { name: blocks.get(`${position.x},${position.y},${position.z}`) ?? 'air', position };
    },
    equip: async () => {},
    async activateBlock() {
      ignitions++;
      for (let y = 65; y <= 67; y++) {
        for (let x = 1; x <= 2; x++) blocks.set(`${x},${y},0`, 'nether_portal');
      }
    },
    get ignitions() { return ignitions; },
  };
}

test('activation confirms six portal blocks and repeat activation makes no new mutations', async () => {
  const bot = portalBot();
  const first = await ignitePortal(bot, { x: 0, y: 64, z: 0 });
  assert.equal(first.explained_mutations.length, 6);
  assert.equal(first.output.activated, true);
  const again = await ignitePortal(bot, { x: 0, y: 64, z: 0 });
  assert.equal(again.explained_mutations.length, 0);
  assert.equal(bot.ignitions, 1);
});

test('incomplete frame fails before using the igniter', async () => {
  const bot = portalBot();
  bot.blocks.set('0,66,0', 'air');
  await assert.rejects(ignitePortal(bot, { x: 0, y: 64, z: 0 }), { code: 'PORTAL_FRAME_INCOMPLETE' });
  assert.equal(bot.ignitions, 0);
});

test('ten obsidian blocks without corners still activate six real portal blocks', async () => {
  const bot = portalBot();
  for (const x of [0, 3]) {
    for (const y of [64, 68]) bot.blocks.set(`${x},${y},0`, 'air');
  }
  assert.equal([...bot.blocks.values()].filter(name => name === 'obsidian').length, 10);
  const result = await ignitePortal(bot, { x: 0, y: 64, z: 0 });
  assert.equal(result.output.portal_blocks, 6);
  assert.equal(result.explained_mutations.length, 6);
});

test('flint drop can satisfy collection even when no gravel drop is received', async () => {
  let inventory = [];
  const result = await acquireFlint({ inventory: { items: () => inventory } }, 1, {}, {
    async collect() {
      inventory = [{ name: 'flint', count: 1 }];
      throw new Error('gravel drop missing');
    },
    place: async () => { throw new Error('unexpected placement'); },
  });
  assert.equal(result.output.acquired, 'flint');
});
