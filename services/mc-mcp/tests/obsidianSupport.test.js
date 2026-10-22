import assert from 'node:assert/strict';
import test from 'node:test';
import Vec3 from 'vec3';
import { backfillObsidianHole, restoreObsidianWorkSurface } from '../src/obsidianSupport.js';

function fixture() {
  const holes = new Map([['0,63,0', 'water'], ['1,63,0', 'air']]);
  const placements = [];
  const bot = {
    entity: { position: new Vec3(2.5, 64, 0.5) },
    inventory: { items: () => [{ name: 'obsidian', count: 1 }, { name: 'cobblestone', count: 25 }] },
    game: { dimension: 'overworld' },
    blockAt(position) {
      const key = `${position.x},${position.y},${position.z}`;
      const name = holes.get(key) ?? (position.y < 63 ? 'deepslate' : position.y === 63 ? 'obsidian' : 'air');
      const solid = ['obsidian', 'cobblestone', 'deepslate'].includes(name);
      return { name, position, boundingBox: solid ? 'block' : 'empty', shapes: solid ? [[0, 0, 0, 1, 1, 1]] : [] };
    },
    async equip(item) { bot.heldItem = item; },
    async placeBlock(reference, face) {
      const position = reference.position.plus(face);
      holes.set(`${position.x},${position.y},${position.z}`, bot.heldItem.name);
      placements.push(position);
    },
  };
  return { bot, holes, placements };
}

test('obsidian holes are replaced with carried common support before pickup, preserving portal stock', async () => {
  const { bot, placements } = fixture();
  const position = new Vec3(0, 63, 0);
  const mutation = await backfillObsidianHole(bot, position);
  assert.equal(bot.blockAt(position).name, 'cobblestone');
  assert.equal(mutation.details.block_type, 'minecraft:cobblestone');
  assert.equal(placements.length, 1);
  assert.equal(await backfillObsidianHole(bot, position), null);
  assert.equal(placements.length, 1);
});

test('preparation restores existing adjacent pits with a finite four-block bound', async () => {
  const { bot, holes, placements } = fixture();
  for (let x = 0; x < 5; x++) holes.set(`${x},63,1`, 'water');
  const mutations = await restoreObsidianWorkSurface(bot);
  assert.ok(mutations.length > 0 && mutations.length <= 4);
  assert.equal(placements.length, mutations.length);
  assert.equal(bot.blockAt(new Vec3(2, 63, 0)).name, 'obsidian');
});

test('partial restoration retains confirmed placements when the next placement fails', async () => {
  const { bot, placements } = fixture();
  const placeBlock = bot.placeBlock;
  bot.placeBlock = async (...args) => {
    if (placements.length) throw new Error('second placement rejected');
    await placeBlock(...args);
  };
  const mutations = [];
  await assert.rejects(
    restoreObsidianWorkSurface(bot, {}, mutations),
    /second placement rejected/,
  );
  assert.equal(placements.length, 1);
  assert.equal(mutations.length, 1);
  assert.equal(mutations[0].details.block_type, 'minecraft:cobblestone');
});

test('missing support or cancelled backfill cannot consume obsidian as scaffold', async () => {
  const { bot, placements } = fixture();
  bot.inventory.items = () => [{ name: 'obsidian', count: 14 }];
  await assert.rejects(backfillObsidianHole(bot, new Vec3(0, 63, 0)), error => error.code === 'SUPPORT_BLOCK_REQUIRED');
  const controller = new AbortController(); controller.abort();
  await assert.rejects(backfillObsidianHole(bot, new Vec3(0, 63, 0), { signal: controller.signal }), error => error.name === 'AbortError');
  assert.equal(placements.length, 0);
});
