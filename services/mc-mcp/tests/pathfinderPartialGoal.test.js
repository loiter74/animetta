import assert from 'node:assert/strict';
import { EventEmitter, once } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';
import pathfinder from 'mineflayer-pathfinder';
import sdkGoto from 'mineflayer-pathfinder/lib/goto.js';
import { createOperationScope } from '../src/runtime/operationScope.js';

function fixture({ signal } = {}) {
  const bot = new EventEmitter(), goal = new pathfinder.goals.GoalBlock(8, 64, 0);
  const state = { nativeCalls: 0, settled: false };
  Object.assign(bot, { controlState: {}, targetDigBlock: null,
    entity: { position: new Vec3(0, 64, 0), onGround: true, velocity: { x: 0, y: 0, z: 0 } },
    setControlState(control, value) { this.controlState[control] = value; },
    stopDigging() {},
    pathfinder: { goal: null, isMoving: () => false,
      stop() { bot.emit('path_stop'); },
      setGoal(next) {
        this.goal = next;
        bot.emit('goal_updated', next);
        if (next) queueMicrotask(() => bot.emit('path_update', { status: 'partial', path: [] }));
      },
    },
  });
  const scope = createOperationScope({ bot, signal, deadlineMs: Date.now() + 5_000 });
  const partial = once(bot, 'path_update');
  const start = options => {
    const pending = scope.navigate(goal, () => { state.nativeCalls++; return sdkGoto(bot, goal); }, options);
    pending.then(() => { state.settled = true; }, () => { state.settled = true; });
    return pending;
  };
  const afterPartial = async () => {
    await partial;
    // SDK goto schedules its completion on the next event stack.
    await new Promise(resolve => setTimeout(resolve, 0));
  };
  const assertClean = () => {
    for (const event of ['path_update', 'goal_updated', 'goal_reached', 'path_stop']) {
      assert.equal(bot.listenerCount(event), 0, event);
    }
    assert.equal(state.nativeCalls, 1, 'never restart the native goal');
  };
  return { bot, goal, scope, state, start, afterPartial, assertClean };
}

test('empty partial paths keep the same native navigation active until actual arrival', async () => {
  const f = fixture(), pending = f.start();
  await f.afterPartial();
  assert.equal(f.state.settled, false);
  assert.equal(f.bot.pathfinder.goal, f.goal);
  f.bot.emit('path_update', { status: 'partial', path: [] });
  f.bot.emit('goal_reached', f.goal);
  await Promise.resolve();
  assert.equal(f.state.settled, false, 'a goal event alone is not arrival evidence');
  f.bot.entity.position.x = 8;
  f.bot.emit('goal_reached', f.goal);
  await pending;
  f.assertClean();
});

test('terminal search failure still stops and settles an unfinished partial navigation', async () => {
  for (const status of ['noPath', 'timeout']) {
    const f = fixture(), pending = f.start();
    await f.afterPartial();
    f.bot.emit('path_update', { status, path: [] });
    await assert.rejects(pending, { code: 'NAVIGATION_TARGET_NOT_REACHED' });
    assert.equal(f.bot.pathfinder.goal, null);
    f.assertClean();
  }
});

test('waiting on partial progress preserves the original navigation timeout', async () => {
  const f = fixture(), deadline = f.scope.deadlineMs;
  await assert.rejects(f.start({ timeoutMs: 10 }), { code: 'ACTION_DEADLINE_EXPIRED' });
  assert.equal(f.scope.deadlineMs, deadline);
  assert.equal(f.bot.pathfinder.goal, null);
  f.assertClean();
});

test('external cancellation also settles partial navigation without another native call', async () => {
  const controller = new AbortController(), f = fixture({ signal: controller.signal }), pending = f.start();
  await f.afterPartial();
  controller.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  assert.equal(f.bot.pathfinder.goal, null);
  f.assertClean();
});

test('partial-navigation cleanup cannot stop a successor goal', async () => {
  const f = fixture(), pending = f.start();
  await f.afterPartial();
  const successor = new pathfinder.goals.GoalBlock(12, 64, 0);
  f.bot.pathfinder.setGoal(successor);
  await assert.rejects(pending, { name: 'GoalChanged' });
  assert.equal(f.bot.pathfinder.goal, successor);
  f.assertClean();
});
