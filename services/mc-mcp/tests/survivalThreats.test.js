import assert from 'node:assert/strict';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import BlockLoader from 'prismarine-block';
import pathfinderPkg from 'mineflayer-pathfinder';
import WorldSync from 'prismarine-world/src/worldsync.js';
import { findHostileThreat } from '../src/survivalThreats.js';
import { collectionDigSafety, configureDryNavigation, createCollectionBlockMatcher } from '../src/collection.js';

function fixture() {
  const registry = minecraftData('1.21.1');
  const Block = BlockLoader(registry);
  const bot = {
    registry, entity: { position: new Vec3(22, 106, -42) },
    entities: { 540: { id: 540, name: 'skeleton', position: new Vec3(18.500886216870562, 107, -58.86411845527901) } },
    blockAt(position) {
      const block = Block.fromStateId(registry.blocksByName.stone.defaultState, 0);
      block.position = position;
      return block;
    },
  };
  return bot;
}

test('R17 skeleton is a threat before a nearby arrow or lost health, while livestock is not', () => {
  const bot = fixture();
  assert.equal(findHostileThreat(bot)?.entity_id, '540');
  bot.entities[540].name = 'minecraft:cow';
  assert.equal(findHostileThreat(bot), null);
  bot.entities[540].name = 'minecraft:skeleton';
  assert.equal(findHostileThreat(bot)?.entity_type, 'skeleton');
  bot.entities[540].position = new Vec3(100, 106, -42);
  assert.equal(findHostileThreat(bot), null);
});

test('R17 threatened ore is excluded before its approach consumes movement or damage', () => {
  const bot = fixture();
  const ore = { name: 'iron_ore', type: bot.registry.blocksByName.iron_ore.id, position: new Vec3(21, 111, -43) };
  assert.equal(collectionDigSafety(bot, ore).reason_code, 'HOSTILE_THREAT');
  const matching = createCollectionBlockMatcher(ore.type, new Set(), block => collectionDigSafety(bot, block).safe);
  assert.equal(matching(ore), false);
  bot.entities = {};
  assert.equal(matching(ore), true);
});

test('dry navigation rejects a threatened path node and still permits distant ordinary terrain', () => {
  const bot = fixture();
  const movements = configureDryNavigation(new pathfinderPkg.Movements(bot), bot);
  assert.equal(movements.exclusionStep(bot.blockAt(new Vec3(22, 106, -42))), Infinity);
  assert.equal(movements.exclusionStep(bot.blockAt(new Vec3(50, 106, -42))), 0);
  assert.equal(movements.maxDropDown, 2);
  assert.equal(movements.allowSprinting, false);
});

test('R18 distant melee warning uses the existing 12-block policy while ranged threats retain 24', () => {
  const bot = fixture();
  bot.entity.position = new Vec3(7.5, 85, 0.5);
  bot.entities = { 134: { id: 134, name: 'zombie', position: new Vec3(29.510740665845766, 78.76636799395752, 7.504898004852723) } };
  assert.equal(findHostileThreat(bot), null);
  bot.entities[134].name = 'skeleton';
  assert.equal(findHostileThreat(bot)?.warning_radius, 24);
  bot.entities[134].name = 'zombie';
  bot.entities[134].position = bot.entity.position.offset(12, 0, 0);
  assert.equal(findHostileThreat(bot)?.warning_radius, 12);
});

function coverFixture() {
  const bot = fixture();
  const Block = BlockLoader(bot.registry);
  bot.entity.position = new Vec3(0.5, 64, 0.5);
  bot.entities[540].position = new Vec3(20.5, 64, 0.5);
  let wall = 'full';
  const world = new WorldSync(null);
  world.getBlock = position => {
    if (wall === 'unloaded' && position.x === 10 && position.y === 65) return null;
    const name = position.x === 10 && position.z === 0 && [64, 65].includes(position.y)
      ? wall === 'slab' ? 'oak_slab' : wall === 'hole' && position.y === 65 ? 'air' : 'stone'
      : 'air';
    const block = Block.fromStateId(bot.registry.blocksByName[name].defaultState, 0);
    block.position = position;
    return block;
  };
  bot.world = world;
  bot.blockAt = world.getBlock;
  return { bot, setWall(value) { wall = value; } };
}

test('only complete known solid cover suppresses a physical projectile warning', () => {
  const { bot, setWall } = coverFixture();
  assert.equal(findHostileThreat(bot), null);
  for (const wall of ['hole', 'unloaded', 'slab']) {
    setWall(wall);
    assert.equal(findHostileThreat(bot)?.entity_type, 'skeleton', wall);
  }
});

test('the block being considered for excavation cannot itself prove protective cover', () => {
  const { bot } = coverFixture();
  assert.equal(findHostileThreat(bot, new Vec3(10.5, 64, 0.5))?.entity_type, 'skeleton');
  bot.entities[540].position = new Vec3(10.5, 64, 0.5);
  assert.equal(findHostileThreat(bot)?.entity_type, 'skeleton', 'an enemy overlapping a solid cell must not become invisible to safety');
  bot.entities[540].name = 'warden';
  bot.entities[540].position = new Vec3(11.5, 64, 0.5);
  assert.equal(findHostileThreat(bot)?.entity_type, 'warden', 'special abilities retain conservative proximity checks');
});
