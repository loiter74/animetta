import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

import { blockMutation, withActionEvidence } from '../src/runtime/actionEvidence.js';

function nativePlacementFixture(mode) {
  const bot = Object.assign(new EventEmitter(), {
    entity: { position: new Vec3(-10, 64, 21) }, health: 20,
    heldItem: { name: 'crafting_table', count: 1 },
  });
  const reference = { name: mode === 'replacement-timeout' ? 'fern' : 'dirt',
    type: mode === 'replacement-timeout' ? 3 : 1, position: new Vec3(-9, 63, 21),
    boundingBox: mode === 'replacement-timeout' ? 'empty' : 'block' };
  const target = reference.position.offset(0, 1, 0);
  const world = new Map([[String(reference.position), reference]]);
  bot.blockAt = position => world.get(String(position)) || { name: 'air', type: 0, position };
  const update = (position, name = 'crafting_table', type = 2) => {
    const before = bot.blockAt(position);
    const after = { name, type, position };
    world.set(String(position), after);
    bot.emit('blockUpdate', before, after);
    return after;
  };
  bot._genericPlace = async () => {
    if (mode === 'foreign-updates') {
      update(target.offset(10, 0, 0));
      update(target, 'stone', 1);
    } else {
      update(mode === 'replacement-timeout' ? reference.position : target);
      bot.heldItem.count = 0;
    }
    if (mode === 'rejected-after-update' || mode === 'foreign-updates') {
      throw Object.assign(new Error('native placement rejected after server update'), { code: 'ACTION_CANCELLED' });
    }
  };
  // Execute the installed SDK verbatim; replace only its timed wait with a
  // controlled timeout, keeping the real destination and event logic intact.
  const sdk = { exports: {} };
  runInNewContext(readFileSync(new URL('../node_modules/mineflayer/lib/plugins/place_block.js', import.meta.url), 'utf8'), {
    module: sdk,
    require: name => {
      assert.equal(name, '../promise_utils');
      return { onceWithCleanup: async (_bot, event, options) => {
        assert.equal(event, `blockUpdate:${target}`);
        assert.equal(options.timeout, 5000);
        throw new Error(`Event ${event} did not fire within timeout of 5000ms`);
      } };
    },
  });
  sdk.exports(bot);
  return { bot, reference, target, update };
}

for (const mode of ['success', 'replacement-timeout', 'rejected-after-update', 'foreign-updates']) {
  test(`native placement evidence retains exact server changes: ${mode}`, async () => {
    const { bot, reference, target } = nativePlacementFixture(mode);
    const originalPlace = bot.placeBlock;
    const originalEmit = bot.emit;
    const verify = result => {
      const expected = mode === 'foreign-updates' ? 0 : 1;
      assert.equal(result.budget_usage.max_blocks_changed, expected);
      assert.equal(result.explained_mutations.length, expected);
      if (expected) {
        const position = mode === 'replacement-timeout' ? reference.position : target;
        assert.equal(result.explained_mutations[0].subject, `block:minecraft:overworld:${position.x}:${position.y}:${position.z}`);
        assert.equal(result.explained_mutations[0].details.block_type, 'minecraft:crafting_table');
        assert.equal(result.explained_mutations[0].delta, 1);
      }
    };
    const action = () => withActionEvidence(bot, async () => {
      await bot.placeBlock(reference, new Vec3(0, 1, 0));
      return 'placed';
    });
    if (mode === 'success') verify(await action());
    else await assert.rejects(action, error => { verify(error); return true; });
    assert.equal(bot.placeBlock, originalPlace);
    assert.equal(bot.emit, originalEmit);
    assert.deepEqual(bot.eventNames(), []);
  });
}

test('nested native placement evidence counts repeated place-dig-place occurrences once each', async () => {
  const { bot, reference, target, update } = nativePlacementFixture('success');
  const originalPlace = bot.placeBlock;
  const originalEmit = bot.emit;
  const result = await withActionEvidence(bot, () => withActionEvidence(bot, async () => {
    await bot.placeBlock(reference, new Vec3(0, 1, 0));
    const air = update(target, 'air', 0);
    bot.emit('diggingCompleted', air);
    bot.heldItem.count = 1;
    await bot.placeBlock(reference, new Vec3(0, 1, 0));
    return 'placed twice';
  }), { normalizeResult: value => value });
  assert.equal(result.budget_usage.max_blocks_changed, 3);
  assert.deepEqual(result.explained_mutations.map(m => m.delta), [1, -1, 1]);
  assert.equal(bot.placeBlock, originalPlace);
  assert.equal(bot.emit, originalEmit);
  assert.deepEqual(bot.eventNames(), []);
});

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
