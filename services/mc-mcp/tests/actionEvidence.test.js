import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

import { blockMutation, withActionEvidence } from '../src/runtime/actionEvidence.js';

function installedSdkDiggingCancellation(bot) {
  const source = readFileSync(new URL('../node_modules/mineflayer-pathfinder/index.js', import.meta.url), 'utf8');
  const start = source.indexOf('function detectDiggingStopped () {');
  const end = source.indexOf('\n  function resetPath', start);
  assert.ok(start >= 0 && end > start);
  const stop = runInNewContext(`(${source.slice(start, end)})`, { bot, digging: true });
  bot.on('diggingAborted', stop);
  bot.emit('diggingAborted');
  assert.equal(bot.listenerCount('diggingCompleted'), 0, 'installed SDK removes all bot completion listeners');
}

for (const failed of [false, true]) {
  test(`SDK digging cancellation cannot erase ${failed ? 'failed' : 'successful'} action mutation evidence`, async () => {
    const bot = Object.assign(new EventEmitter(), {
      entity: { position: new Vec3(0, 64, 0) }, health: 20,
    });
    const emit = bot.emit;
    const air = { type: 0, name: 'air', position: new Vec3(1, 64, 0) };
    const stone = { ...air, type: 1, name: 'stone' };
    const invoke = async annotations => {
      installedSdkDiggingCancellation(bot);
      // Ordinary pathfinder excavation has no explicit collection annotation.
      bot.emit('blockUpdate', stone, air);
      bot.emit('diggingCompleted', air);
      bot.emit('blockPlaced', air, stone);
      annotations.push(blockMutation('stone', stone.position, undefined, 1));
      bot.emit('blockUpdate', stone, air);
      bot.emit('diggingCompleted', air);
      // An unrelated removal without a bot dig completion is not ours.
      bot.emit('blockUpdate', { ...stone, position: new Vec3(9, 64, 0) }, air);
      if (failed) throw Object.assign(new Error('navigation deadline'), { code: 'ACTION_DEADLINE_EXPIRED' });
      return 'finished';
    };
    const verify = result => {
      assert.equal(result.budget_usage.max_blocks_changed, 3);
      assert.deepEqual(result.explained_mutations.map(m => m.delta), [-1, 1, -1]);
    };
    if (failed) await assert.rejects(withActionEvidence(bot, invoke), error => {
      assert.equal(error.code, 'ACTION_DEADLINE_EXPIRED');
      verify(error);
      return true;
    });
    else verify(await withActionEvidence(bot, invoke));
    assert.equal(bot.emit, emit);
    assert.deepEqual(bot.eventNames(), []);
  });
}

test('nested action observers retain one charge and restore the emitter after SDK listener removal', async () => {
  const bot = Object.assign(new EventEmitter(), {
    entity: { position: new Vec3(0, 64, 0) }, health: 20,
  });
  const emit = bot.emit;
  const air = { type: 0, name: 'air', position: new Vec3(1, 64, 0) };
  const stone = { ...air, type: 1, name: 'stone' };
  const inner = () => withActionEvidence(bot, async () => {
    installedSdkDiggingCancellation(bot);
    bot.emit('blockUpdate', stone, air);
    bot.emit('diggingCompleted', air);
    return 'inner';
  });
  const result = await withActionEvidence(bot, inner, { normalizeResult: value => value });
  assert.equal(result.budget_usage.max_blocks_changed, 1);
  assert.equal(result.explained_mutations.length, 1, 'native and inner annotations describe the same occurrence');
  assert.equal(bot.emit, emit);
  assert.deepEqual(bot.eventNames(), []);
});

test('action observation preserves emitter dispatch and never overwrites another emitter replacement', async () => {
  const bot = Object.assign(new EventEmitter(), {
    entity: { position: new Vec3(0, 64, 0) }, health: 20,
  });
  const original = bot.emit;
  const received = [];
  bot.on('custom', function (...args) {
    assert.equal(this, bot);
    received.push(args);
  });
  let replacement;
  await withActionEvidence(bot, async () => {
    assert.equal(bot.emit('unobserved', 1), false);
    assert.equal(bot.emit('custom', 1, { key: 'value' }), true);
    const observed = bot.emit;
    replacement = function (...args) { return observed.apply(this, args); };
    bot.emit = replacement;
    return 'finished';
  });
  assert.equal(bot.emit, replacement);
  await withActionEvidence(bot, async () => {
    assert.equal(bot.emit('custom', 2), true);
    return 'next';
  });
  assert.equal(bot.emit, replacement, 'the next scope also restores the current external emitter');
  assert.deepEqual(received, [[1, { key: 'value' }], [2]]);
  assert.equal(bot.listenerCount('custom'), 1, 'external listeners remain installed');
  bot.emit = original;
  bot.removeAllListeners('custom');
  assert.deepEqual(bot.eventNames(), []);
});

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
