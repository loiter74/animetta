import assert from 'node:assert/strict';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import BlockLoader from 'prismarine-block';
import pathfinderPkg from 'mineflayer-pathfinder';
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
