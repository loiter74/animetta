import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';

import { blockMutation, withActionEvidence } from '../src/runtime/actionEvidence.js';

test('action evidence preserves primitive abort reasons, repeated block changes and cleanup', async () => {
  const bot = Object.assign(new EventEmitter(), {
    entity: { position: new Vec3(0, 64, 0) }, health: 20,
  });
  const air = { type: 0, name: 'air', position: new Vec3(1, 64, 0) };
  const stone = { ...air, type: 1, name: 'stone' };
  await assert.rejects(withActionEvidence(bot, async annotations => {
    for (let i = 0; i < 2; i++) {
      bot.emit('blockPlaced', air, stone);
      bot.emit('blockUpdate', stone, air);
      bot.emit('diggingCompleted', air);
      annotations.push(blockMutation('stone', stone.position, undefined, 1));
      annotations.push(blockMutation('stone', stone.position));
    }
    bot.entity.position = new Vec3(3, 68, 0);
    bot.emit('move');
    bot.entity.position = new Vec3(0, 64, 0);
    bot.emit('move');
    bot.health = 18;
    bot.emit('health');
    bot.health = 20;
    bot.emit('health');
    throw 'operator stop';
  }), error => {
    assert.equal(error.cause, 'operator stop');
    assert.equal(error.budget_usage.max_actions, 1);
    assert.equal(error.budget_usage.max_travel_distance, 10);
    assert.equal(error.budget_usage.max_damage_taken, 2);
    assert.equal(error.budget_usage.max_blocks_changed, 4);
    assert.deepEqual(error.explained_mutations.map(m => m.delta), [1, -1, 1, -1]);
    return true;
  });
  assert.deepEqual(bot.eventNames(), []);
});

test('action evidence preserves structured output and does not count non-block annotations as blocks', async () => {
  const bot = Object.assign(new EventEmitter(), {
    entity: { position: new Vec3(0, 64, 0) }, health: 20,
  });
  const result = await withActionEvidence(bot, async () => ({
    output: { defeated: true }, combat: { won: true },
    explained_mutations: [{ kind: 'entity', subject: 'zombie-1', delta: -1 }],
    budget_usage: { max_actions: 1, resource_consumption: { arrow: 2 } },
  }), { normalizeResult: value => value });
  assert.deepEqual(result.output, { defeated: true });
  assert.deepEqual(result.combat, { won: true });
  assert.equal(result.budget_usage.max_blocks_changed, 0);
  assert.deepEqual(result.budget_usage.resource_consumption, { arrow: 2 });
});
