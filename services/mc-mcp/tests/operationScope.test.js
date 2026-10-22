import assert from 'node:assert/strict';
import test from 'node:test';
import { EventEmitter } from 'node:events';
import minecraftData from 'minecraft-data';
import pathfinderPackage from 'mineflayer-pathfinder';
import Vec3 from 'vec3';

import { createOperationScope } from '../src/runtime/operationScope.js';

test('interaction navigation supports SDK goals with pos and vector-based visibility checks', async () => {
  const target = new Vec3(29, 61, 96);
  const bot = new EventEmitter();
  bot.entity = { position: new Vec3(29, 64, 96), onGround: true, velocity: new Vec3(0, 0, 0) };
  bot.pathfinder = { isMoving: () => false, setGoal() {}, stop() {} };
  bot.setControlState = () => {};
  const goal = new pathfinderPackage.goals.GoalLookAtBlock(target, { raycast: () => ({ position: target }) });
  const scope = createOperationScope({ bot, deadlineMs: Date.now() + 5000 });
  assert.equal(await scope.navigate(goal, async () => 'visible'), 'visible');
});

test('navigation clears an idle stop request before the real pathfinder accepts a new goal', async () => {
  const bot = new EventEmitter();
  bot.registry = minecraftData('1.21.1');
  bot.entity = { position: new Vec3(0, 64, 0), onGround: true, velocity: new Vec3(0, 0, 0) };
  bot.inventory = { items: () => [] };
  bot.clearControlStates = () => {};
  bot.setControlState = () => {};
  pathfinderPackage.pathfinder(bot);
  bot.pathfinder.stop();
  const goal = new pathfinderPackage.goals.GoalBlock(1, 64, 0);
  const scope = createOperationScope({ bot, deadlineMs: Date.now() + 5_000 });
  let failure = null;
  const pending = scope.navigate(goal, () => bot.pathfinder.goto(goal)).catch((error) => {
    failure = error;
  });
  await new Promise(setImmediate);
  bot.entity.position = new Vec3(1, 64, 0);
  bot.emit('goal_reached', goal);
  await pending;
  assert.equal(failure, null);
});

test('navigation timeout cancels the real SDK goal without waiting for its next waypoint', async () => {
  const bot = new EventEmitter();
  bot.registry = minecraftData('1.21.1');
  bot.entity = { position: new Vec3(0, 26, 0), onGround: true, velocity: new Vec3(0, 0, 0) };
  bot.inventory = { items: () => [] };
  bot.clearControlStates = () => {};
  bot.setControlState = () => {};
  pathfinderPackage.pathfinder(bot);
  const goal = new pathfinderPackage.goals.GoalY(30);
  const scope = createOperationScope({ bot, deadlineMs: Date.now() + 5000, quiescenceTimeoutMs: 100 });
  await assert.rejects(scope.navigate(goal, () => bot.pathfinder.goto(goal), { timeoutMs: 20 }),
    error => error.code === 'ACTION_DEADLINE_EXPIRED');
  assert.equal(bot.pathfinder.goal, null);
  assert.equal(bot.listenerCount('goal_reached'), 0);
});

test('distant navigation can finish beyond the short navigation window', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const { bot } = botFixture();
  const scope = createOperationScope({ bot, deadlineMs: Date.now() + 200_000 });
  const pending = scope.navigate(
    { x: 64, y: 64, z: 0, isEnd: (node) => node.x === 64 },
    () => new Promise((resolve) => setTimeout(() => {
      bot.entity.position.x = 64;
      resolve();
    }, 17_000)),
  ).then(() => true, (error) => error.code);
  await Promise.resolve();
  t.mock.timers.tick(17_000);
  assert.equal(await pending, true);
});

test('native height goals retain time for planning and pillar movement', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const { bot } = botFixture();
  bot.entity.position.y = 26;
  const scope = createOperationScope({ bot, deadlineMs: Date.now() + 200_000 });
  const goal = new pathfinderPackage.goals.GoalY(30);
  const pending = scope.navigate(goal, () => new Promise(resolve => setTimeout(() => {
    bot.entity.position.y = 30; resolve();
  }, 17_000))).then(() => true, error => error.code);
  await Promise.resolve();
  t.mock.timers.tick(17_000);
  assert.equal(await pending, true);
});


function botFixture(overrides = {}) {
  const controls = {};
  let stops = 0;
  const bot = {
    entity: {
      position: { x: 0, y: 64, z: 0 },
      onGround: true,
      velocity: { x: 0, y: 0, z: 0 },
    },
    pathfinder: {
      stop: () => { stops += 1; },
      isMoving: () => false,
    },
    pvp: { stop: async () => {}, target: null },
    setControlState: (name, value) => { controls[name] = value; },
    stopDigging: () => {},
    ...overrides,
  };
  return { bot, controls, stops: () => stops };
}

test('grounded gravity is settled but falling, jumping and horizontal drift are not', async () => {
  const { bot } = botFixture();
  bot.entity.velocity.y = -0.0784000015258789;
  const scope = createOperationScope({ bot });
  assert.equal(scope.isQuiescent(), true);
  assert.equal(await scope.interrupt(), true);
  bot.entity.onGround = false;
  assert.equal(scope.isQuiescent(), false);
  bot.entity.onGround = true;
  bot.entity.velocity.y = -0.2;
  assert.equal(scope.isQuiescent(), false);
  bot.entity.velocity.y = 0.2;
  assert.equal(scope.isQuiescent(), false);
  bot.entity.velocity.y = -0.0784;
  bot.entity.velocity.x = 0.1;
  assert.equal(scope.isQuiescent(), false);
});


test('navigation cannot report success before the goal predicate is satisfied', async () => {
  const { bot, stops } = botFixture();
  const scope = createOperationScope({ bot, deadlineMs: Date.now() + 10_000, waitMs: async () => {} });

  await assert.rejects(
    () => scope.navigate(
      { x: 10, y: 64, z: 0, isEnd: (node) => node.x === 10 },
      async () => undefined,
    ),
    (error) => error.code === 'NAVIGATION_TARGET_NOT_REACHED',
  );
  assert.ok(stops() >= 1);
});


test('navigation miss that cannot become quiescent is a settlement timeout', async () => {
  let now = 0;
  const { bot } = botFixture({
    pathfinder: { stop: () => {}, isMoving: () => true },
  });
  const scope = createOperationScope({
    bot,
    deadlineMs: 10_000,
    nowMs: () => now,
    waitMs: async (delayMs) => { now += delayMs; },
  });

  await assert.rejects(
    () => scope.navigate(
      { x: 10, y: 64, z: 0, isEnd: (node) => node.x === 10 },
      async () => undefined,
    ),
    (error) => error.code === 'ACTION_SETTLEMENT_TIMEOUT'
      && error.details.world_may_have_changed === true,
  );
});


test('accepted cancellation stops resources and waits for operation settlement plus quiescence', async () => {
  const controller = new AbortController();
  const { bot, controls, stops } = botFixture();
  const scope = createOperationScope({
    bot,
    signal: controller.signal,
    deadlineMs: Date.now() + 10_000,
    waitMs: async () => {},
  });
  let release;
  const operation = new Promise((resolve) => { release = resolve; });
  const pending = scope.runInterruptible(() => operation, { label: 'test movement' });
  controller.abort('operator stop');
  release();

  await assert.rejects(pending, (error) => error.name === 'AbortError');
  assert.ok(stops() >= 1);
  assert.equal(controls.forward, false);
  assert.equal(controls.sprint, false);
});


test('quiescent resources cannot make a still-pending operation a clean cancellation', async () => {
  const controller = new AbortController();
  let now = 0;
  let release;
  const operation = new Promise((resolve) => { release = resolve; });
  const { bot } = botFixture();
  const scope = createOperationScope({
    bot,
    signal: controller.signal,
    deadlineMs: 100_000,
    nowMs: () => { now += 500; return now; },
    waitMs: async () => {},
    quiescenceTimeoutMs: 2_000,
  });
  const pending = scope.runInterruptible(() => operation, { label: 'late placement' });
  controller.abort('operator stop');

  let settlement;
  await assert.rejects(pending, (error) => {
    settlement = error.operationSettlement;
    return error.code === 'CANCEL_SETTLEMENT_TIMEOUT'
      && error.details.world_may_have_changed === true;
  });
  let settled = false;
  settlement.then(() => { settled = true; });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(settled, false);

  release();
  await new Promise((resolve) => setTimeout(resolve, 120));
  assert.equal(settled, true);
});


test('aborting the default cancellable wait clears its timer handle', async () => {
  const controller = new AbortController();
  const { bot } = botFixture();
  const originalSetTimeout = globalThis.setTimeout;
  const originalClearTimeout = globalThis.clearTimeout;
  const timerHandle = { kind: 'operation-wait' };
  const cleared = [];
  globalThis.setTimeout = () => timerHandle;
  globalThis.clearTimeout = (handle) => { cleared.push(handle); };
  try {
    const scope = createOperationScope({
      bot,
      signal: controller.signal,
      deadlineMs: Date.now() + 10_000,
    });
    const pending = scope.wait(1_000);
    controller.abort('operator stop');

    await assert.rejects(pending, (error) => error.code === 'ACTION_CANCELLED');
    assert.deepEqual(cleared, [timerHandle]);
  } finally {
    globalThis.setTimeout = originalSetTimeout;
    globalThis.clearTimeout = originalClearTimeout;
  }
});


test('failed cancellation settlement is explicit and quarantine-worthy', async () => {
  const controller = new AbortController();
  let now = 0;
  const { bot } = botFixture({
    pathfinder: { stop: () => {}, isMoving: () => true },
  });
  const scope = createOperationScope({
    bot,
    signal: controller.signal,
    deadlineMs: 100_000,
    nowMs: () => { now += 500; return now; },
    waitMs: async () => {},
    quiescenceTimeoutMs: 2_000,
  });
  const pending = scope.runInterruptible(
    () => new Promise(() => {}),
    { label: 'stuck movement' },
  );
  controller.abort('operator stop');

  await assert.rejects(
    pending,
    (error) => error.code === 'CANCEL_SETTLEMENT_TIMEOUT'
      && error.details.world_may_have_changed === true,
  );
});


test('settlement timeout exposes the real late operation and quiescence lifetime', async () => {
  const controller = new AbortController();
  let now = 0;
  let moving = true;
  let release;
  const operation = new Promise((resolve) => { release = resolve; });
  const { bot } = botFixture({
    pathfinder: { stop: () => {}, isMoving: () => moving },
  });
  const scope = createOperationScope({
    bot,
    signal: controller.signal,
    deadlineMs: 100_000,
    nowMs: () => { now += 500; return now; },
    waitMs: async () => {},
    quiescenceTimeoutMs: 2_000,
  });
  const pending = scope.runInterruptible(() => operation, { label: 'late movement' });
  controller.abort('operator stop');

  let settlement;
  await assert.rejects(pending, (error) => {
    settlement = error.operationSettlement;
    return error.code === 'CANCEL_SETTLEMENT_TIMEOUT';
  });
  let settled = false;
  settlement.then(() => { settled = true; });
  release();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(settled, false);

  moving = false;
  await new Promise((resolve) => setTimeout(resolve, 120));
  assert.equal(settled, true);
});


test('deadline reserves the full movement settlement window before starting', async () => {
  let invoked = false;
  const { bot } = botFixture();
  const scope = createOperationScope({ bot, deadlineMs: Date.now() + 2_000 });

  await assert.rejects(
    () => scope.runInterruptible(
      () => { invoked = true; },
      { label: 'no-room action' },
    ),
    (error) => error.code === 'ACTION_DEADLINE_EXPIRED'
      && error.details.reserve_ms === 2_000,
  );
  assert.equal(invoked, false);
});


test('action timeout plus failed settlement stays inside the caller deadline', async () => {
  let now = 0;
  const deadlineMs = 2_050;
  const { bot } = botFixture({
    pathfinder: { stop: () => {}, isMoving: () => true },
  });
  const scope = createOperationScope({
    bot,
    deadlineMs,
    nowMs: () => now,
    waitMs: async (delayMs) => { now += delayMs; },
  });

  await assert.rejects(
    () => scope.runInterruptible(
      () => new Promise(() => {}),
      { label: 'deadline movement' },
    ),
    (error) => error.code === 'ACTION_SETTLEMENT_TIMEOUT',
  );
  assert.ok(now <= deadlineMs);
});


test('container deadline reserves three seconds and closes before quarantine', async () => {
  let now = 0;
  let closes = 0;
  const deadlineMs = 3_050;
  const currentWindow = { close: () => { closes += 1; } };
  const { bot } = botFixture({ currentWindow });
  const scope = createOperationScope({
    bot,
    deadlineMs,
    nowMs: () => now,
    waitMs: async (delayMs) => { now += delayMs; },
    containerCapable: true,
  });

  await assert.rejects(
    () => scope.runInterruptible(
      () => new Promise(() => {}),
      { label: 'deadline container', includeContainers: true },
    ),
    (error) => error.code === 'ACTION_SETTLEMENT_TIMEOUT',
  );
  assert.equal(closes, 1);
  assert.ok(now <= deadlineMs);
});
