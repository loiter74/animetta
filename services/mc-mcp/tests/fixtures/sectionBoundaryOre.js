import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { createRequire } from 'node:module';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import prismarineBlock from 'prismarine-block';
import world from 'prismarine-world';

const require = createRequire(import.meta.url);
const source = readFileSync(require.resolve('mineflayer/lib/plugins/blocks.js'), 'utf8');
const start = source.indexOf('  function getMatchingFunction (matching) {');
const end = source.indexOf('\n  function findBlock (options)', start);
if (start < 0 || end <= start) throw new Error('Pinned native block search fixture is unavailable');

export function sectionBoundaryOreFixture() {
  const registry = minecraftData('1.21.1'), Block = prismarineBlock(registry);
  const near = new Vec3(32, 64, -15), far = new Vec3(36, 63, -2);
  const positions = new Set([near.toString(), far.toString()]), columns = new Map(), calls = [];
  for (const p of [near, far]) {
    const key = `${Math.floor(p.x / 16)},${Math.floor(p.z / 16)}`;
    if (!columns.has(key)) columns.set(key, { sections: [] });
    columns.get(key).sections[Math.floor(p.y / 16) + 4] = {
      palette: [registry.blocksByName.air.defaultState, registry.blocksByName.iron_ore.defaultState],
    };
  }
  let blockReads = 0;
  const bot = {
    registry, game: { minY: -64, height: 384 }, entity: { position: new Vec3(31.32, 63, -14.47) },
    world: { getColumn: (x, z) => columns.get(`${x},${z}`) },
    blockAt(point) {
      blockReads++;
      const p = point.floored(), name = positions.has(p.toString()) ? 'iron_ore' : 'air';
      const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
      block.position = p; return block;
    },
  };
  // Exercise the installed SDK's unmodified section iterator and early stop.
  runInNewContext(`(() => { ${source.slice(start, end)} })()`, {
    bot, Block, Vec3, blockAt: bot.blockAt.bind(bot), OctahedronIterator: world.iterators.OctahedronIterator,
  });
  bot.findBlock = options => {
    calls.push({ radius: options.maxDistance, count: options.count ?? 1 });
    const found = bot.findBlocks(options);
    return found.length ? bot.blockAt(found[0]) : null;
  };
  return { bot, near, far, calls, blockId: registry.blocksByName.iron_ore.id,
    get blockReads() { return blockReads; } };
}
