import assert from 'node:assert/strict';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import prismarineBlock from 'prismarine-block';
import { createCollectionSafety } from '../src/runtime/collectionSafety.js';
import { findHostileThreat } from '../src/survivalThreats.js';

function fixture({ remaining = 32, candidates = [{ x: -5, y: 64, z: 0 }] } = {}) {
  const registry = minecraftData('1.21.1'), Block = prismarineBlock(registry);
  const controller = new AbortController(), motionUsage = { travel: 0 };
  const bot = { entity: { position: new Vec3(.5, 64, .5) }, entities: {
    1: { id: 1, name: 'skeleton', position: new Vec3(20.5, 64, .5) },
  }, blockAt(position) {
    const block = Block.fromStateId(registry.blocksByName[position.y < 64 ? 'stone' : 'air'].defaultState, 0);
    block.position = position.floored();
    return block;
  } };
  let settle, discoveries = 0, interruptions = 0, routes = 0;
  const events = [], eventual = Promise.resolve();
  const scope = { signal: controller.signal, checkpoint() { controller.signal.throwIfAborted(); },
    interrupt() { interruptions++; return new Promise(resolve => { settle = resolve; }); },
    waitForEventualQuiescence: () => eventual,
    reportPhase: (...args) => events.push(args),
  };
  const safety = createCollectionSafety({ bot, scope, motionUsage,
    budget: { max_travel_distance: remaining },
    discover: () => { discoveries++; return { survival_retreat: { candidates } }; },
    navigate: async (_bot, destination, context) => {
      routes++;
      assert.equal(await safety.checkpoint(), false, 'nested navigation must not recurse');
      assert.equal(safety.requestPause(findHostileThreat(bot)), false, 'another warning cannot start a second retreat');
      const next = new Vec3(destination.x + .5, destination.y, destination.z + .5);
      assert.equal(context.retreat_policy.permitsMove(bot.entity.position, next, true), true);
      motionUsage.travel += next.distanceTo(bot.entity.position);
      bot.entity.position = next;
    },
  });
  return { bot, controller, scope, safety, motionUsage, eventual, events,
    settle: value => settle(value), threat: () => findHostileThreat(bot),
    counts: () => ({ discoveries, interruptions, routes }) };
}

test('one cooperative pause awaits settlement and shares recovery before resuming', async () => {
  const f = fixture();
  assert.equal(f.safety.requestPause(f.threat()), false);
  f.safety.enable();
  assert.equal(f.safety.requestPause(f.threat()), true);
  assert.equal(f.safety.requestPause(f.threat()), true);
  const one = f.safety.checkpoint(), two = f.safety.checkpoint();
  assert.equal(one, two);
  assert.deepEqual(f.counts(), { discoveries: 1, interruptions: 1, routes: 0 });
  f.settle(true);
  assert.equal(await one, true);
  assert.equal(await two, true);
  assert.equal(f.safety.pending, false);
  assert.equal(f.safety.recoveryCount, 1);
  assert.equal(f.motionUsage.travel, 5);
  assert.equal(f.events[0][1].reason_code, 'HOSTILE_RETREAT');
  f.safety.dispose();
  assert.equal(f.safety.requestPause(f.threat()), false);
});

test('no known exit or an exact stopping-reserve boundary keeps the hard stop', () => {
  for (const options of [{ candidates: [] }, { remaining: 7 }]) {
    const f = fixture(options);
    f.safety.enable();
    assert.equal(f.safety.requestPause(f.threat()), false);
    assert.equal(f.counts().interruptions, 0);
  }
});

test('failed settlement never starts escape and retains eventual-settlement evidence', async () => {
  const f = fixture();
  f.safety.enable(); f.safety.requestPause(f.threat()); f.settle(false);
  await assert.rejects(f.safety.checkpoint(), error => {
    assert.equal(error.code, 'ACTION_SETTLEMENT_TIMEOUT');
    assert.equal(error.operationSettlement, f.eventual);
    return true;
  });
  assert.equal(f.counts().routes, 0);
});

test('abort, a blocked exit or spent braking budget prevents escape', async () => {
  for (const mode of ['abort', 'blocked', 'budget']) {
    const f = fixture({ remaining: 8 });
    f.safety.enable(); f.safety.requestPause(f.threat());
    if (mode === 'abort') f.controller.abort(new Error('cancelled'));
    if (mode === 'blocked') f.bot.entities[2] = { id: 2, name: 'zombie', position: new Vec3(-8, 64, .5) };
    if (mode === 'budget') f.motionUsage.travel = 1;
    f.settle(true);
    await assert.rejects(async () => f.safety.checkpoint(), mode === 'abort' ? /cancelled/ : { code: 'UNSAFE_AREA' });
    assert.equal(f.counts().routes, 0);
  }
});

test('the original deadline and terminal recovery failure cannot be retried', async () => {
  const f = fixture(), error = Object.assign(new Error('original deadline expired'), { code: 'ACTION_DEADLINE_EXPIRED' });
  f.safety.enable(); f.safety.requestPause(f.threat());
  f.scope.checkpoint = () => { throw error; };
  f.settle(true);
  await assert.rejects(f.safety.checkpoint(), e => e === error);
  await assert.rejects(f.safety.checkpoint(), e => e === error);
  assert.equal(f.safety.requestPause(f.threat()), false);
  assert.deepEqual(f.counts(), { discoveries: 1, interruptions: 1, routes: 0 });
});
