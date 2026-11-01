import test from 'node:test';
import assert from 'node:assert/strict';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import { projectItemPickupState } from '../src/runtime/itemPickupState.js';

function fixture(x = 0.5, y = 64, z = 0) {
  return {
    registry: minecraftData('1.21'),
    entity: { name: 'player', position: new Vec3(0, 64, 0), width: 0.6, height: 1.8 },
    entities: { 7: { id: 7, name: 'item', position: new Vec3(x, y, z),
      width: 0.25, height: 0.25, onGround: true, velocity: new Vec3(0, 0, 0) } },
  };
}

test('resting items in the old 2m search sphere outside pickup contact are not transfers', () => {
  const result = projectItemPickupState(fixture(1.75));
  assert.equal(result.pending, 0);
  assert.equal(result.evidence[0].reason, 'outside_pickup_area');
  assert.deepEqual(result.evidence[0].position, { x: 1.75, y: 64, z: 0 });
  const grounded = fixture(1.75);
  grounded.entities[7].velocity.y = -0.04;
  assert.equal(projectItemPickupState(grounded).pending, 0);
});

test('actual contact includes diagonal item boxes and the head region beyond a 2m sphere', () => {
  assert.equal(projectItemPickupState(fixture(1.4, 64, 1.4)).pending, 1);
  assert.equal(projectItemPickupState(fixture(0, 66.2)).pending, 1);
  assert.equal(projectItemPickupState(fixture(0, 63)).pending, 0);
});

test('unknown motion, falling items and missing metadata stay conservative', () => {
  const bot = fixture(1.75);
  delete bot.entities[7].velocity;
  assert.equal(projectItemPickupState(bot).pending, 1);
  bot.entities[7].velocity = new Vec3(0, -0.1, 0);
  bot.entities[7].onGround = false;
  assert.equal(projectItemPickupState(bot).pending, 1);
  bot.entities[7].position.x = 0.5;
  bot.entities[7].getDroppedItem = () => { throw new Error('metadata not ready'); };
  assert.equal(projectItemPickupState(bot).pending, 1);
});

test('riding uses the player and vehicle union without vertical inflation', () => {
  const bot = fixture(3.6);
  bot.vehicle = { position: new Vec3(2, 64, 0), width: 1.375, height: 0.5625 };
  assert.equal(projectItemPickupState(bot).pending, 1);
  bot.entities[7].position = new Vec3(0, 66, 0);
  assert.equal(projectItemPickupState(bot).pending, 0);
});

test('witness limits never truncate the pending count; mobs do not count', () => {
  const bot = fixture();
  bot.entities = Object.fromEntries(Array.from({ length: 12 }, (_, id) => [id,
    { ...bot.entities[7], id }]));
  bot.entities[99] = { name: 'cow', position: new Vec3(0, 64, 0) };
  const result = projectItemPickupState(bot);
  assert.equal(result.pending, 12);
  assert.equal(result.evidence.length, 8);
});
