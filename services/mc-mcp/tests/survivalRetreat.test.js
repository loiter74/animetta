import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import BlockLoader from 'prismarine-block';
import pathfinder from 'mineflayer-pathfinder';
import WorldSync from 'prismarine-world/src/worldsync.js';
import { configureDryNavigation } from '../src/collection.js';
import { createRetreatPolicy, projectRetreatCandidates } from '../src/survivalRetreat.js';

function fixture() {
  const registry = minecraftData('1.21.1'), Block = BlockLoader(registry);
  const world = new WorldSync(null), overrides = new Map(), bot = new EventEmitter();
  world.getBlock = point => {
    const p = point.floored(), key = p.toString();
    const name = overrides.has(key) ? overrides.get(key) : p.y < 64 ? 'stone' : 'air';
    if (name === null) return null;
    const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
    block.position = p;
    return block;
  };
  Object.assign(bot, { registry, world, game: { minY: -64, height: 384 }, blockAt: p => world.getBlock(p),
    entity: { position: new Vec3(.5, 64, .5), effects: {} },
    inventory: { items: () => [] },
    entities: { 192: { id: 192, name: 'skeleton', position: new Vec3(20.5, 64, .5) } },
  });
  pathfinder.pathfinder(bot);
  return { bot, overrides };
}

test('installed SDK plans a dry, non-excavating retreat outside the unchanged warning radius', () => {
  const { bot } = fixture(), destination = new Vec3(-5, 64, 0);
  const candidates = projectRetreatCandidates(bot, [destination.offset(0, -1, 0)]);
  assert.deepEqual(candidates, { origin: { x: .5, y: 64, z: .5 }, candidates: [{ x: -5, y: 64, z: 0 }] });
  const policy = createRetreatPolicy(bot, destination);
  const movements = configureDryNavigation(new pathfinder.Movements(bot), bot, { retreatPolicy: policy });
  let result;
  for (const planned of bot.pathfinder.getPathFromTo(movements, bot.entity.position,
    new pathfinder.goals.GoalBlock(-5, 64, 0))) {
    result = planned.result;
    if (result.status !== 'partial') break;
  }
  assert.equal(result.status, 'success');
  assert.ok(result.path.length >= 4);
  let previous = bot.entity.position;
  for (const move of result.path) {
    assert.equal(move.toBreak.length, 0);
    assert.equal(move.toPlace.length, 0);
    const next = new Vec3(Math.floor(move.x) + .5, move.y, Math.floor(move.z) + .5);
    assert.equal(policy.permitsMove(previous, next), true);
    previous = next;
  }
  assert.ok(previous.distanceTo(bot.entities[192].position) > 24);
  assert.equal(movements.canDig, false);
  assert.equal(movements.allow1by1towers, false);
});

test('retreat rejects an approaching step, a newly blocked exit and destinations within warning range', () => {
  const { bot } = fixture(), policy = createRetreatPolicy(bot, new Vec3(-5, 64, 0));
  assert.equal(policy.permitsMove(bot.entity.position, bot.entity.position.offset(1, 0, 0)), false);
  assert.equal(createRetreatPolicy(bot, new Vec3(-2, 64, 0)), null);
  const intruder = { position: { x: -10, y: 64, z: 0 }, warning_radius: 12 };
  assert.equal(policy.permitsThreat(intruder), false);
  bot.entities[193] = { id: 193, name: 'zombie', position: new Vec3(-10, 64, 0) };
  assert.equal(policy.permitsMove(bot.entity.position, bot.entity.position.offset(-1, 0, 0)), false);
});

test('only supplied discovery cells with known air and full support become retreat destinations', () => {
  const { bot, overrides } = fixture(), floor = new Vec3(-5, 63, 0);
  assert.deepEqual(projectRetreatCandidates(bot, []).candidates, []);
  for (const [p, name] of [[floor, 'oak_slab'], [floor, 'water'], [floor, null],
    [floor.offset(0, 1, 0), 'water'], [floor.offset(0, 2, 0), null]]) {
    overrides.set(p.toString(), name);
    assert.deepEqual(projectRetreatCandidates(bot, [floor]).candidates, [], String(name));
    overrides.clear();
  }
  bot.entities = {};
  assert.equal(projectRetreatCandidates(bot, [floor]), null);
});
