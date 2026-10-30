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

test('R32 polar bears exclude the observed attack position and tree before more damage', () => {
  const bot = fixture();
  bot.entity.position = new Vec3(-5.499999999999962, 110, 27.332291181750815);
  bot.entities = {
    3: { id: 3, name: 'polar_bear', kind: 'Passive mobs', position: new Vec3(-5.014011325890211, 110, 26.29286605782957) },
    4: { id: 4, name: 'minecraft:polar_bear', kind: 'Passive mobs', position: new Vec3(-7.223787424897574, 110, 21.817199273317748) },
  };
  const threat = findHostileThreat(bot);
  assert.equal(threat?.entity_id, '3');
  assert.equal(threat.warning_radius, 12);
  const log = { name: 'spruce_log', type: bot.registry.blocksByName.spruce_log.id, position: new Vec3(-6, 115, 28) };
  assert.equal(collectionDigSafety(bot, log).reason_code, 'HOSTILE_THREAT');
  const movements = configureDryNavigation(new pathfinderPkg.Movements(bot), bot);
  assert.equal(movements.exclusionStep(bot.blockAt(bot.entity.position.floored())), Infinity);
});

test('polar bear warning preserves the existing melee radius and ordinary livestock behavior', () => {
  const bot = fixture();
  bot.entities = { 3: { id: 3, name: 'minecraft:polar_bear', kind: 'Passive mobs', position: bot.entity.position.offset(12, 0, 0) } };
  assert.equal(findHostileThreat(bot)?.warning_radius, 12);
  bot.entities[3].position.x += 0.01;
  assert.equal(findHostileThreat(bot), null);
  bot.entities[3].name = 'skeleton';
  assert.equal(findHostileThreat(bot)?.warning_radius, 24);
  bot.entities[3].name = 'cow';
  bot.entities[3].position = bot.entity.position.offset(1, 0, 0);
  assert.equal(findHostileThreat(bot), null);
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

function horizontalCoverFixture() {
  const bot = fixture();
  const Block = BlockLoader(bot.registry);
  bot.entity.position = new Vec3(3.5, 88, -9.681217716364884);
  bot.entity.height = 1.8;
  bot.entity.width = 0.6;
  Object.assign(bot.entities[540], {
    position: new Vec3(-10.756484719099214, 71, -0.7782001352427272),
    height: 1.99, width: 0.6,
  });
  let cover = 'full';
  const world = new WorldSync(null);
  world.getBlock = position => {
    const p = position.floored();
    const gap = p.x === -10 && p.z === -3;
    if (p.y === 74 && gap && cover === 'unloaded') return null;
    const name = p.y !== 74 || (gap && cover === 'hole') ? 'air'
      : cover === 'slab' ? 'oak_slab' : 'stone';
    const block = Block.fromStateId(bot.registry.blocksByName[name].defaultState, 0);
    block.position = p;
    return block;
  };
  bot.world = world;
  bot.blockAt = world.getBlock;
  return { bot, setCover(value) { cover = value; } };
}

test('a complete horizontal rock layer blocks steep physical attack lanes in either direction', () => {
  const { bot } = horizontalCoverFixture();
  assert.equal(findHostileThreat(bot), null);
  const upper = bot.entity.position;
  bot.entity.position = bot.entities[540].position;
  bot.entities[540].position = upper;
  assert.equal(findHostileThreat(bot), null);
});

test('horizontal cover needs the entire body-width cross section to be known full cubes', () => {
  const { bot, setCover } = horizontalCoverFixture();
  for (const cover of ['hole', 'unloaded', 'slab']) {
    setCover(cover);
    assert.equal(findHostileThreat(bot)?.warning_radius, 24, cover);
  }
});

test('a planned excavation inside the roof and special attacks retain their warning', () => {
  const { bot } = horizontalCoverFixture();
  assert.equal(findHostileThreat(bot, new Vec3(-10, 74, -3))?.entity_type, 'skeleton');
  bot.entities[540].name = 'warden';
  bot.entities[540].position = new Vec3(3.5, 78, -9.68);
  assert.equal(findHostileThreat(bot)?.warning_radius, 12);
});

function r33WallFixture(axis = 'x', reversed = false) {
  const bot = fixture();
  const Block = BlockLoader(bot.registry);
  const transpose = p => axis === 'x' ? p : new Vec3(p.z, p.y, p.x);
  const bodies = [
    { position: transpose(new Vec3(4.457569119409204, 86, 9.500102459971263)), height: 1.8, width: 0.6 },
    { position: transpose(new Vec3(27.55315511485964, 82.00129881501198, 11.295175302477936)), height: 1.99, width: 0.6 },
  ];
  if (reversed) bodies.reverse();
  Object.assign(bot.entity, bodies[0]);
  Object.assign(bot.entities[540], bodies[1]);
  let missing = null;
  let replacement = 'air';
  const world = new WorldSync(null);
  world.getBlock = position => {
    const p = position.floored();
    const original = transpose(p);
    if (original.x === 5 && original.y === missing && original.z === 9 && replacement === null) return null;
    const wall = original.x === 5 && original.z === 9 && original.y >= 85 && original.y <= 87;
    const floor = original.x === 4 && original.y === 85 && original.z === 9;
    const name = wall ? original.y === missing ? replacement : 'stone' : floor ? 'stone' : 'air';
    const block = Block.fromStateId(bot.registry.blocksByName[name].defaultState, 0);
    block.position = p;
    return block;
  };
  bot.world = world;
  bot.blockAt = world.getBlock;
  return { bot, transpose, changeCell(y, name) { missing = y; replacement = name; } };
}

test('R33 complete X and Z walls cover both full bodies despite different first-hit columns', () => {
  for (const axis of ['x', 'z']) for (const reversed of [false, true]) {
    const { bot } = r33WallFixture(axis, reversed);
    assert.equal(findHostileThreat(bot), null, `${axis} reversed=${reversed}`);
  }
});

test('R33 every critical wall cell must be a known full cube', () => {
  for (const axis of ['x', 'z']) for (const y of [85, 86, 87]) for (const block of ['air', 'oak_slab', null]) {
    const { bot, changeCell } = r33WallFixture(axis);
    changeCell(y, block);
    assert.equal(findHostileThreat(bot)?.entity_type, 'skeleton', `${axis} y=${y} ${block}`);
  }
});

test('R33 body-overlapping excavation and special attackers cannot use the wall exemption', () => {
  for (const axis of ['x', 'z']) {
    const { bot, transpose } = r33WallFixture(axis);
    assert.equal(findHostileThreat(bot, transpose(new Vec3(5.1, 86, 9.5)))?.entity_type, 'skeleton');
    assert.equal(findHostileThreat(bot, transpose(new Vec3(4.9, 86, 9.5)))?.entity_type, 'skeleton', 'full body width overlaps the wall');
    for (const name of ['warden', 'polar_bear']) {
      bot.entities[540].name = name;
      assert.equal(findHostileThreat(bot, bot.entity.position, 24)?.entity_type, name);
    }
  }
});

function r62CreeperFixture() {
  const bot = fixture();
  const Block = BlockLoader(bot.registry);
  const creeperData = bot.registry.entitiesByName.creeper;
  bot.entity.position = new Vec3(-72.50431682764764, 36, 14.460011918950478);
  // Raw R62 metadata was not retained, so this replay pairs the exact R62
  // geometry with a controlled inactive/uncharged/unignited creeper state.
  const metadata = [];
  metadata[creeperData.metadataKeys.indexOf('swell_dir')] = -1;
  metadata[creeperData.metadataKeys.indexOf('is_powered')] = false;
  metadata[creeperData.metadataKeys.indexOf('is_ignited')] = false;
  bot.entities = {
    62: {
      id: 62, name: 'creeper', metadata,
      position: new Vec3(-76.70654874609782, 34, 3.4513750279456477),
      height: creeperData.height, width: creeperData.width,
    },
  };
  // Only the six verified R62 wall cells are known stone; every other
  // position stays unknown (null) instead of forged air.
  const wallCells = new Set([
    '-76,34,8', '-76,35,8', '-76,36,8', '-75,34,8', '-75,35,8', '-75,36,8',
  ]);
  const replaced = new Map();
  const world = new WorldSync(null);
  world.getBlock = position => {
    const p = position.floored();
    const key = `${p.x},${p.y},${p.z}`;
    const name = replaced.has(key) ? replaced.get(key) : wallCells.has(key) ? 'stone' : null;
    if (name === null) return null;
    const block = Block.fromStateId(bot.registry.blocksByName[name].defaultState, 0);
    block.position = p;
    return block;
  };
  world.raycast = () => null;
  bot.world = world;
  bot.blockAt = world.getBlock;
  return {
    bot, creeper: bot.entities[62],
    breakCell(key, name) { replaced.set(key, name); },
  };
}

test('R62 geometry with an explicitly safe creeper behind the verified stone layer is not an immediate threat', () => {
  const { bot } = r62CreeperFixture();
  assert.equal(findHostileThreat(bot), null);
});

test('R62 creeper cover exemption demands exact safe metadata and a complete known wall', () => {
  const { bot, creeper, breakCell } = r62CreeperFixture();
  const keys = bot.registry.entitiesByName.creeper.metadataKeys;
  const safeCopy = () => {
    const metadata = [];
    metadata[keys.indexOf('swell_dir')] = -1;
    metadata[keys.indexOf('is_powered')] = false;
    metadata[keys.indexOf('is_ignited')] = false;
    return metadata;
  };
  // Explicitly dangerous creeper states keep the melee warning.
  for (const [key, value] of [['swell_dir', 1], ['is_powered', true], ['is_ignited', true]]) {
    creeper.metadata = safeCopy();
    creeper.metadata[keys.indexOf(key)] = value;
    const threat = findHostileThreat(bot);
    assert.equal(threat?.entity_type, 'creeper', `${key}=${value}`);
    assert.equal(threat?.warning_radius, 12, `${key}=${value}`);
  }
  // Unknown, missing, or mistyped metadata never proves a safe creeper.
  const registry = bot.registry;
  bot.registry = { ...registry, entitiesByName: { ...registry.entitiesByName, creeper: undefined } };
  creeper.metadata = safeCopy();
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'registry without creeper data');
  bot.registry = { ...registry, entitiesByName: { ...registry.entitiesByName,
    creeper: { ...registry.entitiesByName.creeper, metadataKeys: keys.filter(key => key !== 'swell_dir') } } };
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'metadataKeys missing swell_dir');
  bot.registry = registry;
  delete creeper.metadata;
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'entity without metadata');
  creeper.metadata = safeCopy();
  creeper.metadata[keys.indexOf('is_powered')] = 0;
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'numeric flag is not truthy-coerced to false');
  creeper.metadata = safeCopy();
  creeper.metadata[keys.indexOf('swell_dir')] = '-1';
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'string swell_dir is a wrong type');
  // Any hole or unknown cell in the verified layer keeps the warning.
  creeper.metadata = safeCopy();
  breakCell('-75,35,8', 'air');
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'known hole in the wall');
  breakCell('-75,35,8', null);
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'unknown wall cell');
  breakCell('-75,35,8', 'stone');
  // A proposed excavation origin inside the only wall cannot borrow the dug wall as cover.
  assert.equal(findHostileThreat(bot, new Vec3(-75.5, 35, 8.5))?.entity_type, 'creeper', 'excavation origin inside the wall');
  // The same geometry and metadata never exempt other special enemies.
  creeper.name = 'enderman';
  assert.equal(findHostileThreat(bot)?.entity_type, 'enderman', 'identical metadata on a non-creeper stays a threat');
});

test('R62 a safe creeper behind the wall never masks other visible enemies', () => {
  const { bot } = r62CreeperFixture();
  bot.entities[77] = { id: 77, name: 'skeleton', position: new Vec3(-68.5, 36, 12.5) };
  const threat = findHostileThreat(bot);
  assert.equal(threat?.entity_id, '77');
  assert.equal(threat?.warning_radius, 24);
});

test('vanilla spawn metadata omits default creeper flags only after initial state is known', () => {
  const { bot, creeper } = r62CreeperFixture();
  const keys = bot.registry.entitiesByName.creeper.metadataKeys;
  creeper.metadata = [];
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'spawn without initial metadata stays unknown');
  creeper.metadata[keys.indexOf('health')] = 20;
  assert.equal(findHostileThreat(bot), null, 'known vanilla initial metadata may omit all three default flags');
  creeper.metadata[keys.indexOf('is_ignited')] = true;
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'later non-default state overrides the implicit default');
  delete creeper.metadata[keys.indexOf('is_ignited')];
  creeper.metadata[keys.indexOf('is_powered')] = undefined;
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'an explicitly malformed slot is not an omitted default');
  delete creeper.metadata[keys.indexOf('is_powered')];
  const registry = bot.registry;
  bot.registry = { ...registry, version: { ...registry.version, version: -1 } };
  assert.equal(findHostileThreat(bot)?.entity_type, 'creeper', 'unknown protocol defaults remain unknown');
});
