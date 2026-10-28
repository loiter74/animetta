import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import injectEntities from 'mineflayer/lib/plugins/entities.js';
import pathfinderPkg from 'mineflayer-pathfinder';
import prismarineBlock from 'prismarine-block';
import { Physics, PlayerState } from 'prismarine-physics';

import { createGameBotV2Adapter } from '../src/runtime/gamebotV2Adapter.js';
import { withCollectionEvidence } from '../src/collection.js';
import { navigateTo } from '../src/navigation.js';


function budget(overrides = {}) {
  return {
    max_actions: 8,
    max_strategy_attempts: 8,
    max_travel_distance: 128,
    max_blocks_changed: 64,
    max_damage_taken: 20,
    protected_items: [],
    resource_consumption: { torch: 64 },
    ...overrides,
  };
}


function blockPosition(x, y, z) {
  return {
    x,
    y,
    z,
    offset(dx, dy, dz) { return blockPosition(x + dx, y + dy, z + dz); },
  };
}


function adapterFixture({ actions: actionOverrides = {}, look = async () => {}, presentation } = {}) {
  const bot = new EventEmitter();
  const protocolClient = new EventEmitter();
  protocolClient.state = 'play';
  const position = {
    x: 0,
    y: 64,
    z: 0,
    floored: () => blockPosition(0, 64, 0),
  };
  Object.assign(bot, {
    _client: protocolClient,
    version: '1.21.1',
    registry: minecraftData('1.21.1'),
    game: { dimension: 'minecraft:overworld' },
    time: { age: 40 },
    health: 20,
    food: 20,
    entities: {},
    entity: {
      id: 1,
      name: 'player',
      metadata: { 1: 300 },
      position,
      height: 1.62,
      eyeHeight: 1.62,
      yaw: 0,
      onGround: true,
      fallDistance: 0,
      velocity: { x: 0, y: 0, z: 0 },
    },
    inventory: { items: () => [], slots: [] },
    blockAt: (target) => ({
      name: 'air',
      boundingBox: 'empty',
      biome: { name: 'plains' },
      position: target,
    }),
    pathfinder: { isMoving: () => false, stop: () => {} },
    pvp: { target: null, stop: () => {} },
    targetDigBlock: null,
    currentWindow: null,
    controlState: {},
    look,
    setControlState: () => {},
    stopDigging: () => {},
  });
  const defaults = Object.fromEntries([
    'goto',
    'collectWithEvidence',
    'mine',
    'craft',
    'placeWithEvidence',
    'smelt',
    'equip',
    'attackWithEvidence',
    'chat',
    'recipes',
    'mineShaft',
  ].map((name) => [name, async () => `${name} complete`]));
  const adapter = createGameBotV2Adapter({
    bot,
    connection: { host: '127.0.0.1', port: 25565, username: 'AnimettaBot' },
    actions: { ...defaults, ...actionOverrides },
    abortActive: async () => {},
    emitEvent: () => {},
    presentation: presentation || { mode: 'off', tempo: 'normal', seed: 'test-seed' },
  });
  return { adapter, bot, protocolClient };
}

function navigationFixture(travelBeforeRoute) {
  const fixture = adapterFixture({ actions: {
    goto: async (x, y, z, context) => {
      fixture.bot.entity.position.x = travelBeforeRoute;
      fixture.bot.emit('move');
      return navigateTo(fixture.bot, { x, y, z }, context);
    },
  } });
  fixture.bot.entity.position = new Vec3(0, 64, 0);
  let nativeRoutes = 0;
  fixture.bot.pathfinder.goto = async goal => {
    nativeRoutes++;
    if (goal.constructor.name === 'GoalY') fixture.bot.entity.position.y = goal.y;
    else fixture.bot.entity.position = new Vec3(goal.x, goal.y, goal.z);
    fixture.bot.emit('move');
  };
  return { ...fixture, get nativeRoutes() { return nativeRoutes; } };
}

function jumpPhysicsFixture(t, { prefix = 189.71167502464702, held = false, unknown = false } = {}) {
  let timer;
  let nativeJumpRequests = 0;
  let modelUnknown = false;
  const controls = { forward: false, back: false, left: false, right: false,
    jump: false, sprint: false, sneak: false };
  const fixture = adapterFixture({ actions: {
    goto: async (_x, _y, _z, context) => {
      fixture.bot.entity.position.x += prefix;
      fixture.bot.emit('move');
      modelUnknown = unknown;
      if (held) {
        controls.jump = true;
        fixture.bot.jumpQueued = true;
        fixture.bot.emit('physicsTick');
      } else fixture.bot.setControlState('jump', true);
      if (context.signal.aborted) fixture.bot.setControlState('forward', true);
      context.signal.throwIfAborted();
      if (unknown) return 'unexpectedly admitted an unknown jump';
      await new Promise((resolve, reject) => {
        let ticks = 0;
        timer = setInterval(() => {
          try {
            fixture.bot.physics.simulatePlayer(new PlayerState(fixture.bot, controls), world).apply(fixture.bot);
            assert.ok(['x', 'y', 'z'].every(axis => Number.isFinite(fixture.bot.entity.position[axis])));
            fixture.bot.emit('move');
            fixture.bot.emit('physicsTick');
            if (!held) fixture.bot.setControlState('jump', false);
            if (fixture.bot.entity.onGround && ticks > 0) { clearInterval(timer); resolve(); }
            else if (++ticks > 32) { clearInterval(timer); reject(new Error('Jump fixture did not settle')); }
          } catch (error) { clearInterval(timer); reject(error); }
        }, 1);
      });
      return 'jump settled';
    },
  } });
  const bot = fixture.bot;
  bot.entity.position = new Vec3(.5, 64, .5);
  bot.entity.velocity = new Vec3(0, 0, 0);
  Object.assign(bot.entity, { yaw: 0, pitch: 0, effects: {}, attributes: {} });
  bot.jumpTicks = 0;
  bot.jumpQueued = false;
  bot.controlState = controls;
  bot.setControlState = (control, value) => {
    controls[control] = value;
    if (control === 'jump' && value) { bot.jumpQueued = true; nativeJumpRequests++; }
  };
  const Block = prismarineBlock(bot.registry);
  bot.blockAt = position => {
    if (modelUnknown) return null;
    const pos = position.floored();
    const block = Block.fromStateId(bot.registry.blocksByName[pos.y < 64 ? 'stone' : 'air'].defaultState);
    block.position = pos;
    return block;
  };
  const world = { getBlock: position => bot.blockAt(position) };
  bot.physics = Physics(bot.registry, world);
  t.after(() => { clearInterval(timer); fixture.adapter.dispose(); });
  return { ...fixture, controls, get nativeJumpRequests() { return nativeJumpRequests; } };
}


function request(adapter, capability, parameters, correlationId) {
  return {
    schema_version: '2',
    transport_id: `transport-${correlationId}`,
    command_id: `command-${correlationId}`,
    step_id: `step-${correlationId}`,
    correlation_id: correlationId,
    runtime_instance_id: adapter.runtimeInstanceId,
    capability,
    parameters,
    remaining_budget: budget(),
    deadline_ms: Date.now() + 10_000,
    previous_receipt_hash: '',
  };
}

function nativeWorldWork(bot) {
  bot.entity.position = new Vec3(3, 68, 0);
  bot.emit('move');
  bot.health = 18;
  bot.emit('health');
  const stone = { name: 'stone', type: 1, position: new Vec3(1, 64, 0) };
  const air = { ...stone, name: 'air', type: 0 };
  bot.emit('blockUpdate', stone, air);
  bot.emit('diggingCompleted', air);
  bot.emit('blockPlaced', air, { ...stone, name: 'crafting_table', type: 2 });
}

test('generic action evidence charges goto work before an ordinary timeout', async () => {
  const fixture = adapterFixture({ actions: { goto: async () => {
    nativeWorldWork(fixture.bot);
    throw Object.assign(new Error('navigation timed out'), { code: 'ACTION_DEADLINE_EXPIRED' });
  } } });
  const receipt = await fixture.adapter.runtime.executeAction(request(
    fixture.adapter, 'goto', { x: 3, y: 68, z: 0 }, 'generic-goto-timeout',
  ));
  assert.equal(receipt.error.code, 'ACTION_DEADLINE_EXPIRED');
  assert.equal(receipt.budget_usage.max_actions, 1);
  assert.equal(receipt.budget_usage.max_travel_distance, 5);
  assert.equal(receipt.budget_usage.max_damage_taken, 2);
  assert.equal(receipt.budget_usage.max_blocks_changed, 2);
  assert.ok(receipt.explained_mutations.some(m => m.kind === 'block'
    && m.details.block_type === 'minecraft:crafting_table'));
  fixture.adapter.dispose();
});

test('generic action evidence includes craft world work and preserves explicit annotations', async () => {
  const fixture = adapterFixture({ actions: { craft: async () => {
    nativeWorldWork(fixture.bot);
    return { output: 'crafted', explained_mutations: [{
      kind: 'block', subject: 'block:minecraft:overworld:2:64:0', delta: 1,
      details: { block_type: 'minecraft:nether_portal' },
    }], budget_usage: { max_actions: 1, max_blocks_changed: 1 } };
  } } });
  const receipt = await fixture.adapter.runtime.executeAction(request(
    fixture.adapter, 'craft', { recipe: 'stone_pickaxe', count: 1 }, 'generic-craft',
  ));
  assert.equal(receipt.outcome, 'success');
  assert.equal(receipt.budget_usage.max_travel_distance, 5);
  assert.equal(receipt.budget_usage.max_damage_taken, 2);
  assert.equal(receipt.budget_usage.max_blocks_changed, 3);
  assert.ok(receipt.explained_mutations.some(m => m.details?.block_type === 'minecraft:nether_portal'));
  fixture.adapter.dispose();
});

test('generic action evidence does not double charge nested collection or leak listeners', async () => {
  const fixture = adapterFixture({ actions: { collectWithEvidence: async () => withCollectionEvidence(
    fixture.bot, async mutations => {
      nativeWorldWork(fixture.bot);
      mutations.push({ kind: 'block', subject: 'block:minecraft:overworld:1:64:0', delta: -1,
        details: { block_type: 'minecraft:stone' } });
      return 'collected';
    },
  ) } });
  const events = ['move', 'health', 'blockUpdate', 'diggingCompleted', 'blockPlaced'];
  const before = events.map(event => fixture.bot.listenerCount(event));
  const receipt = await fixture.adapter.runtime.executeAction(request(
    fixture.adapter, 'collect', { block_type: 'stone', count: 1 }, 'generic-nested',
  ));
  assert.equal(receipt.outcome, 'success');
  assert.equal(receipt.budget_usage.max_actions, 1);
  assert.equal(receipt.budget_usage.max_travel_distance, 5);
  assert.equal(receipt.budget_usage.max_damage_taken, 2);
  assert.equal(receipt.budget_usage.max_blocks_changed, 2);
  assert.deepEqual(events.map(event => fixture.bot.listenerCount(event)), before);
  fixture.adapter.dispose();
});

test('generic action evidence keeps read-only recipe inspection free', async () => {
  const fixture = adapterFixture();
  const receipt = await fixture.adapter.runtime.executeAction(request(
    fixture.adapter, 'recipes', { item: 'iron_pickaxe' }, 'generic-read-only',
  ));
  assert.equal(receipt.outcome, 'success');
  assert.equal(receipt.budget_usage.max_actions, 0);
  fixture.adapter.dispose();
});

test('generic budget guard permits stationary zero-block crafting and stops damage during goto', async () => {
  let continued = false;
  const fixture = adapterFixture({ actions: { goto: async (_x, _y, _z, context) => {
    nativeWorldWork(fixture.bot);
    context.signal.throwIfAborted();
    continued = true;
  } } });
  const craft = request(fixture.adapter, 'craft', { recipe: 'iron_pickaxe', count: 1 }, 'stationary-craft');
  craft.remaining_budget = budget({ max_travel_distance: 0, max_blocks_changed: 0, max_damage_taken: 0 });
  const crafted = await fixture.adapter.runtime.executeAction(craft);
  assert.equal(crafted.outcome, 'success');
  assert.equal(crafted.budget_usage.max_blocks_changed, 0);
  const goto = request(fixture.adapter, 'goto', { x: 3, y: 68, z: 0 }, 'goto-damage-stop');
  goto.remaining_budget = budget({ max_damage_taken: 0 });
  const stopped = await fixture.adapter.runtime.executeAction(goto);
  assert.equal(continued, false);
  assert.equal(stopped.outcome, 'unknown');
  assert.equal(stopped.error.code, 'BUDGET_CONTRACT_VIOLATION');
  assert.equal(stopped.budget_usage.max_damage_taken, 2);
  assert.equal(stopped.budget_usage.max_travel_distance, 5);
  assert.equal(stopped.budget_usage.max_blocks_changed, 2);
  fixture.adapter.dispose();
});

test('real SDK metadata from another entity cannot replace the bot own air supply', async () => {
  let bot;
  const fixture = adapterFixture({ actions: { goto: async (_x, _y, _z, context) => {
    fixture.protocolClient.emit('entity_metadata', {
      entityId: 2, metadata: [{ key: 1, type: 'varint', value: 210 }],
    });
    assert.equal(bot.oxygenLevel, 14, 'the installed SDK writes another entity air into this shared field');
    assert.equal(context.signal.aborted, false);
    return 'arrived';
  } } });
  bot = fixture.bot;
  bot.supportFeature = bot.registry.supportFeature;
  injectEntities(bot);
  bot.entities[1] = bot.entity;
  bot.entities[2] = { id: 2, name: 'item', metadata: {} };
  fixture.protocolClient.emit('entity_metadata', {
    entityId: 1, metadata: [{ key: 1, type: 'varint', value: 300 }],
  });
  const receipt = await fixture.adapter.runtime.executeAction(request(
    fixture.adapter, 'goto', { x: 0, y: 64, z: 0 }, 'own-air',
  ));
  assert.equal(receipt.outcome, 'success');
  const observation = await fixture.adapter.runtime.observe({
    correlation_id: 'own-air-observation', runtime_instance_id: fixture.adapter.runtimeInstanceId,
  });
  assert.equal(observation.environment.oxygen_level, 20);
  fixture.protocolClient.emit('entity_metadata', {
    entityId: 1, metadata: [{ key: 1, type: 'varint', value: 210 }],
  });
  const low = await fixture.adapter.runtime.executeAction(request(
    fixture.adapter, 'goto', { x: 0, y: 64, z: 0 }, 'own-low-air',
  ));
  assert.equal(low.error.code, 'OXYGEN_LOW');
  fixture.adapter.dispose();
});

test('missing own air metadata stays unknown even if the SDK shared field has a value', async () => {
  const { adapter, bot } = adapterFixture();
  bot.entity.metadata = {};
  bot.oxygenLevel = 14;
  const observation = await adapter.runtime.observe({
    correlation_id: 'unknown-own-air', runtime_instance_id: adapter.runtimeInstanceId,
  });
  assert.equal(Object.hasOwn(observation.environment, 'oxygen_level'), false);
  adapter.dispose();
});

test('low air cancels an admitted collect before drowning and retains charged work', async () => {
  let started;
  const entered = new Promise(resolve => { started = resolve; });
  const { adapter, bot } = adapterFixture({ actions: {
    collectWithEvidence: async (_block, _count, context) => new Promise((_resolve, reject) => {
      context.signal.addEventListener('abort', () => reject(Object.assign(new Error('stopped'), {
        budget_usage: { max_actions: 1, max_blocks_changed: 4, max_travel_distance: 2 },
        explained_mutations: [],
      })), { once: true });
      started();
    }),
  } });
  const pending = adapter.runtime.executeAction(request(adapter, 'collect', { block_type: 'iron_ore', count: 7 }, 'low-air'));
  await entered;
  bot.oxygenLevel = 14;
  bot.entity.metadata[1] = 210;
  bot.emit('breath');
  const receipt = await pending;
  assert.equal(receipt.error.code, 'OXYGEN_LOW');
  assert.equal(receipt.budget_usage.max_actions, 1);
  assert.equal(receipt.budget_usage.max_blocks_changed, 4);
  assert.equal(receipt.budget_usage.max_travel_distance, 2);
  assert.equal(bot.listenerCount('breath'), 0);
  assert.equal(bot.health, 20);
  adapter.dispose();
});

test('low air permits only a known upward shore recovery and still rejects other travel', async () => {
  for (const targetY of [63, 56]) {
    let entered = false;
    let bot;
    const fixture = adapterFixture({ actions: { goto: async (x, y, z, context) => {
      entered = true;
      assert.equal(context.signal.aborted, false);
      bot.entity.position = new Vec3(x, y, z);
      bot.oxygenLevel = 20;
      bot.entity.metadata[1] = 300;
      return 'recovered';
    } } });
    bot = fixture.bot;
    bot.entity.position = new Vec3(0, 57, 0);
    bot.oxygenLevel = 10;
    bot.entity.metadata[1] = 150;
    bot.blockAt = position => {
      const water = position.x === 0 && position.z === 0 && position.y >= 57 && position.y < 63;
      const name = water ? 'water' : position.y < 63 ? 'stone' : 'air';
      return { name, boundingBox: name === 'stone' ? 'block' : 'empty', position };
    };
    const receipt = await fixture.adapter.runtime.executeAction(request(
      fixture.adapter, 'goto', { x: 3, y: targetY, z: 0 }, `air-return-${targetY}`,
    ));
    assert.equal(entered, targetY === 63);
    assert.equal(receipt.outcome, targetY === 63 ? 'success' : 'error');
    if (targetY === 56) assert.equal(receipt.error.code, 'OXYGEN_LOW');
    fixture.adapter.dispose();
  }
});

test('partial collection receipt preserves charged work and rejects over-budget errors', async () => {
  for (const blocks of [4, 65]) {
    const { adapter } = adapterFixture({ actions: {
      collectWithEvidence: async () => {
        throw Object.assign(new Error('partial'), {
          code: 'PARTIAL_COLLECT',
          budget_usage: { max_actions: 1, max_blocks_changed: blocks },
          explained_mutations: [],
        });
      },
    } });
    const receipt = await adapter.runtime.executeAction(
      request(adapter, 'collect', { block_type: 'oak_log', count: 8 }, `partial-${blocks}`),
    );
    assert.equal(receipt.budget_usage.max_actions, 1);
    assert.equal(receipt.budget_usage.max_blocks_changed, blocks);
    assert.equal(receipt.outcome, blocks === 4 ? 'error' : 'unknown');
    assert.equal(receipt.reconciliation, blocks === 4 ? 'accepted' : 'pending');
    assert.equal(receipt.error.code, blocks === 4 ? 'PARTIAL_COLLECT' : 'BUDGET_CONTRACT_VIOLATION');
    adapter.close?.();
  }
});

test('collection stops cumulative backtracking before travel budget and keeps actual usage', async () => {
  let moves = 0;
  let completed = false;
  const fixture = adapterFixture({ actions: {
    collectWithEvidence: async (_block, _count, context) => withCollectionEvidence(fixture.bot, async () => {
      for (; moves < 12; moves++) {
        await context.operation_scope.wait(1);
        fixture.bot.entity.position.x = moves % 2 === 0 ? 1 : 0;
        fixture.bot.emit('move');
      }
      completed = true;
      return 'collected';
    }),
  } });
  const action = request(fixture.adapter, 'collect', { block_type: 'oak_log', count: 8 }, 'travel-guard');
  action.remaining_budget = budget({ max_travel_distance: 8 });
  const receipt = await fixture.adapter.runtime.executeAction(action);
  assert.equal(receipt.error?.code, 'BUDGET_EXHAUSTED');
  assert.equal(receipt.outcome, 'error');
  assert.equal(receipt.reconciliation, 'accepted');
  assert.equal(receipt.budget_usage.max_travel_distance, 6);
  assert.equal(completed, false);
  assert.equal(moves, 6);
  assert.equal(fixture.bot.listenerCount('move'), 0);
  assert.equal(fixture.bot.listenerCount('health'), 0);
  fixture.adapter.dispose();
});

test('collection damage immediately stops work without hiding a real budget overage', async () => {
  let continued = false;
  const fixture = adapterFixture({ actions: {
    collectWithEvidence: async (_block, _count, context) => withCollectionEvidence(fixture.bot, async () => {
      fixture.bot.health = 18;
      fixture.bot.emit('health');
      await context.operation_scope.wait(1);
      continued = true;
      return 'must not finish';
    }),
  } });
  const action = request(fixture.adapter, 'collect', { block_type: 'oak_log', count: 8 }, 'damage-guard');
  action.remaining_budget = budget({ max_damage_taken: 0 });
  const receipt = await fixture.adapter.runtime.executeAction(action);
  assert.equal(continued, false);
  assert.equal(receipt.budget_usage.max_damage_taken, 2);
  assert.equal(receipt.outcome, 'unknown');
  assert.equal(receipt.error.code, 'BUDGET_CONTRACT_VIOLATION');
  assert.equal(fixture.bot.listenerCount('move'), 0);
  assert.equal(fixture.bot.listenerCount('health'), 0);
  fixture.adapter.dispose();
});

test('a newly approaching skeleton stops collection before damage and removes threat listeners', async () => {
  let continued = false;
  const fixture = adapterFixture({ actions: {
    collectWithEvidence: async (_block, _count, context) => withCollectionEvidence(fixture.bot, async () => {
      fixture.bot.entities[540] = { id: 540, name: 'skeleton', position: new Vec3(18, 64, 0) };
      fixture.bot.emit('entityMoved', fixture.bot.entities[540]);
      await context.operation_scope.wait(1);
      continued = true;
    }),
  } });
  fixture.bot.entities = {};
  const action = request(fixture.adapter, 'collect', { block_type: 'iron_ore', count: 7 }, 'approaching-skeleton');
  action.remaining_budget = budget({ max_damage_taken: 0 });
  const receipt = await fixture.adapter.runtime.executeAction(action);
  assert.equal(continued, false);
  assert.equal(receipt.outcome, 'error');
  assert.equal(receipt.reconciliation, 'accepted');
  assert.equal(receipt.error.code, 'UNSAFE_AREA');
  assert.equal(receipt.error.details.threat.entity_type, 'skeleton');
  assert.equal(receipt.budget_usage.max_damage_taken, 0);
  for (const event of ['physicsTick', 'entityMoved', 'entitySpawn']) assert.equal(fixture.bot.listenerCount(event), 0);
  fixture.adapter.dispose();
});

test('navigation refuses a new route whose minimum distance cannot fit before the existing stopping reserve', async () => {
  let navigated = false;
  const fixture = adapterFixture({ actions: {
    collectWithEvidence: async (_block, _count, context) => withCollectionEvidence(fixture.bot, async () => {
      fixture.bot.entity.position.x = 189;
      fixture.bot.emit('move');
      const goal = new pathfinderPkg.goals.GoalBlock(200, 64, 0);
      await context.operation_scope.navigate(goal, async () => {
        navigated = true;
        fixture.bot.entity.position.x = 200;
        fixture.bot.emit('move');
      });
    }),
  } });
  const action = request(fixture.adapter, 'collect', { block_type: 'iron_ore', count: 7 }, 'route-admission');
  action.remaining_budget = budget({ max_travel_distance: 192 });
  const receipt = await fixture.adapter.runtime.executeAction(action);
  assert.equal(navigated, false);
  assert.equal(receipt.outcome, 'error');
  assert.equal(receipt.error.code, 'BUDGET_EXHAUSTED');
  assert.equal(receipt.budget_usage.max_travel_distance, 189);
  assert.equal(receipt.error.details.stopping_reserve, 2);
  fixture.adapter.dispose();
});

for (const [leg, destination] of [
  ['final', { x: 200, y: 64, z: 0 }],
  ['ascent', { x: 189, y: 72, z: 0 }],
]) {
  test(`goto checks the remaining travel budget before its ${leg} leg`, async () => {
    const fixture = navigationFixture(189);
    const action = request(fixture.adapter, 'goto', destination, `goto-admission-${leg}`);
    action.remaining_budget = budget({ max_travel_distance: 192 });
    const receipt = await fixture.adapter.runtime.executeAction(action);
    assert.equal(fixture.nativeRoutes, 0, 'do not start a route that cannot fit with the existing reserve');
    assert.equal(receipt.outcome, 'error');
    assert.equal(receipt.error.code, 'BUDGET_EXHAUSTED');
    assert.equal(receipt.budget_usage.max_travel_distance, 189);
    assert.equal(receipt.error.details.stopping_reserve, 2);
    fixture.adapter.dispose();
  });
}

test('goto completes scoped ascent and final legs that fit the unchanged travel budget', async () => {
  const fixture = navigationFixture(180);
  const action = request(fixture.adapter, 'goto', { x: 181, y: 72, z: 0 }, 'goto-admission-fits');
  action.remaining_budget = budget({ max_travel_distance: 192 });
  const receipt = await fixture.adapter.runtime.executeAction(action);
  assert.equal(receipt.outcome, 'success');
  assert.equal(fixture.nativeRoutes, 2);
  assert.equal(receipt.budget_usage.max_travel_distance, 184 + Math.hypot(1, 4));
  assert.deepEqual(fixture.bot.entity.position, new Vec3(181, 72, 0));
  fixture.adapter.dispose();
});

for (const held of [false, true]) {
  test(`jump motion admission rejects an unaffordable real flight before takeoff: held=${held}`, async t => {
    const fixture = jumpPhysicsFixture(t, { held });
    const setter = fixture.bot.setControlState;
    const action = request(fixture.adapter, 'goto', { x: 200, y: 64, z: 0 }, `jump-motion-${held}`);
    action.remaining_budget = budget({ max_travel_distance: 192 });
    const receipt = await fixture.adapter.runtime.executeAction(action);
    assert.equal(receipt.outcome, 'error');
    assert.equal(receipt.error.code, 'BUDGET_EXHAUSTED');
    assert.ok(Math.abs(receipt.budget_usage.max_travel_distance - 189.71167502464702) < 1e-9);
    assert.equal(fixture.nativeJumpRequests, 0);
    assert.equal(fixture.bot.entity.position.y, 64);
    assert.equal(fixture.bot.jumpQueued, false);
    assert.ok(Object.values(fixture.controls).every(value => value === false));
    assert.deepEqual(fixture.bot.entity.velocity, new Vec3(0, 0, 0));
    assert.equal(fixture.bot.setControlState, setter);
    assert.equal(fixture.bot.listenerCount('physicsTick'), 0);
    assert.equal(fixture.bot.listenerCount('move'), 0);
  });
}

test('jump motion admission allows a real flight within the unchanged budget and charges it', async t => {
  const fixture = jumpPhysicsFixture(t, { prefix: 180 });
  const setter = fixture.bot.setControlState;
  const action = request(fixture.adapter, 'goto', { x: 200, y: 64, z: 0 }, 'jump-motion-fits');
  action.remaining_budget = budget({ max_travel_distance: 192 });
  const receipt = await fixture.adapter.runtime.executeAction(action);
  assert.equal(receipt.outcome, 'success');
  assert.equal(fixture.nativeJumpRequests, 1);
  assert.ok(Math.abs(receipt.budget_usage.max_travel_distance - 182.50440668050742) < 1e-9);
  assert.equal(fixture.bot.entity.position.y, 64);
  assert.equal(fixture.bot.setControlState, setter);
});

test('jump motion admission refuses an unknown landing without changing actual usage', async t => {
  const fixture = jumpPhysicsFixture(t, { prefix: .8, unknown: true });
  const action = request(fixture.adapter, 'goto', { x: 20, y: 64, z: 0 }, 'jump-motion-unknown');
  action.remaining_budget = budget({ max_travel_distance: 192 });
  const receipt = await fixture.adapter.runtime.executeAction(action);
  assert.equal(receipt.outcome, 'error');
  assert.equal(receipt.error.code, 'BUDGET_EXHAUSTED');
  assert.ok(Math.abs(receipt.budget_usage.max_travel_distance - .8) < 1e-9);
  assert.equal(fixture.nativeJumpRequests, 0);
});

test('navigation budget admission respects the real SDK goal radius and foot cell', async () => {
  for (const goal of [new pathfinderPkg.goals.GoalNear(200, 64, 0, 16), new pathfinderPkg.goals.GoalBlock(189, 64, 0)]) {
    let navigated = false;
    const fixture = adapterFixture({ actions: {
      collectWithEvidence: async (_block, _count, context) => withCollectionEvidence(fixture.bot, async () => {
        fixture.bot.entity.position.x = 189;
        fixture.bot.emit('move');
        await context.operation_scope.navigate(goal, async () => { navigated = true; });
        return 'already inside the goal region';
      }),
    } });
    const action = request(fixture.adapter, 'collect', { block_type: 'iron_ore', count: 1 }, `admission-${goal.constructor.name}`);
    action.remaining_budget = budget({ max_travel_distance: 192 });
    const receipt = await fixture.adapter.runtime.executeAction(action);
    assert.equal(navigated, true);
    assert.equal(receipt.outcome, 'success');
    assert.equal(receipt.budget_usage.max_travel_distance, 189);
    fixture.adapter.dispose();
  }
});

for (const completion of ['throw-abort-reason', 'return-after-abort', 'external-cancel']) {
  test(`interrupted collection keeps settled evidence: ${completion}`, async () => {
    const mutation = { kind: 'block', subject: 'block:minecraft:overworld:0:64:1', delta: -1,
      details: { block_type: 'minecraft:iron_ore' } };
    const fixture = adapterFixture({ actions: {
      collectWithEvidence: async (_block, _count, context) => withCollectionEvidence(fixture.bot, async (mutations) => {
        mutations.push(mutation);
        fixture.bot.entity.position.x = 6;
        fixture.bot.emit('move');
        if (completion === 'external-cancel') {
          const acknowledgement = await fixture.adapter.runtime.cancelAction({
            schema_version: '2', runtime_instance_id: fixture.adapter.runtimeInstanceId,
            correlation_id: 'settled-external-cancel', reason: 'controller stop',
          });
          assert.equal(acknowledgement.accepted, true);
        }
        // Final movement while braking is part of the same action's bill.
        fixture.bot.entity.position.x = 6.5;
        fixture.bot.emit('move');
        if (completion !== 'return-after-abort') context.signal.throwIfAborted();
        return 'collected before cancellation settled';
      }),
    } });
    const action = request(fixture.adapter, 'collect', { block_type: 'iron_ore', count: 7 }, `settled-${completion}`);
    action.remaining_budget = budget({ max_travel_distance: completion === 'external-cancel' ? 16 : 8 });
    const receipt = await fixture.adapter.runtime.executeAction(action);
    assert.equal(receipt.outcome, completion === 'external-cancel' ? 'cancelled' : 'error');
    assert.equal(receipt.error?.code, completion === 'external-cancel' ? undefined : 'BUDGET_EXHAUSTED');
    assert.equal(receipt.budget_usage.max_actions, 1);
    assert.equal(receipt.budget_usage.max_travel_distance, 6.5);
    assert.equal(receipt.budget_usage.max_blocks_changed, 1);
    assert.deepEqual(receipt.explained_mutations.filter(item => item.kind === 'block'), [mutation]);
    assert.equal(fixture.bot.listenerCount('move'), 0);
    assert.equal(fixture.bot.listenerCount('health'), 0);
    fixture.adapter.dispose();
  });
}

test('collection preserves ordinary work within travel and damage budgets', async () => {
  const fixture = adapterFixture({ actions: {
    collectWithEvidence: async () => withCollectionEvidence(fixture.bot, async () => {
      fixture.bot.entity.position.x = 1;
      fixture.bot.emit('move');
      fixture.bot.health = 19;
      fixture.bot.emit('health');
      return 'collected';
    }),
  } });
  const action = request(fixture.adapter, 'collect', { block_type: 'oak_log', count: 1 }, 'within-budget');
  action.remaining_budget = budget({ max_travel_distance: 8, max_damage_taken: 1 });
  const receipt = await fixture.adapter.runtime.executeAction(action);
  assert.equal(receipt.outcome, 'success');
  assert.equal(receipt.budget_usage.max_travel_distance, 1);
  assert.equal(receipt.budget_usage.max_damage_taken, 1);
  assert.equal(fixture.bot.listenerCount('move'), 0);
  assert.equal(fixture.bot.listenerCount('health'), 0);
  fixture.adapter.dispose();
});

test('collection refuses to start with less than the movement stopping reserve', async () => {
  let started = false;
  const { adapter } = adapterFixture({ actions: { collectWithEvidence: async () => { started = true; } } });
  const action = request(adapter, 'collect', { block_type: 'oak_log', count: 8 }, 'no-travel-room');
  action.remaining_budget = budget({ max_travel_distance: 1 });
  const receipt = await adapter.runtime.executeAction(action);
  assert.equal(started, false);
  assert.equal(receipt.error?.code, 'BUDGET_EXHAUSTED');
  assert.equal(receipt.budget_usage.max_travel_distance, 0);
  adapter.dispose();
});


test('adapter preserves and normalizes budget usage from a non-evidence capability', async () => {
  const rawReported = {
    max_actions: '2',
    max_strategy_attempts: '3',
    max_travel_distance: '7.5',
    max_blocks_changed: '2',
    max_damage_taken: '1.5',
    protected_items: ['diamond_pickaxe'],
    resource_consumption: { torch: '2' },
  };
  const normalizedReported = {
    max_actions: 2,
    max_strategy_attempts: 3,
    max_travel_distance: 7.5,
    max_blocks_changed: 2,
    max_damage_taken: 1.5,
    protected_items: ['diamond_pickaxe'],
    resource_consumption: { torch: 2 },
  };
  const { adapter } = adapterFixture({
    actions: {
      mine: async () => ({
        output: { mined: 2 },
        explained_mutations: [],
        budget_usage: rawReported,
        details: { strategy: 'vein' },
      }),
    },
  });

  const receipt = await adapter.runtime.executeAction(request(
    adapter,
    'mine',
    { block_type: 'stone', count: 2 },
    'budget-path',
  ));

  assert.equal(receipt.outcome, 'success');
  assert.deepEqual(receipt.budget_usage, normalizedReported);
  adapter.dispose();
});


test('every action-backed capability cooperatively settles a mid-action cancellation', async () => {
  const cases = [
    ['goto', 'goto', { x: 3, y: 64, z: 0 }],
    ['collect', 'collectWithEvidence', { block_type: 'stone', count: 1 }],
    ['mine', 'mine', { block_type: 'stone', count: 1 }],
    ['craft', 'craft', { recipe: 'stick', count: 1 }],
    ['place', 'placeWithEvidence', {
      block_type: 'stone', x: 1, y: 64, z: 0, facing: 'north',
    }],
    ['smelt', 'smelt', { item: 'raw_iron', fuel: 'coal', count: 1 }],
    ['equip', 'equip', { item: 'iron_pickaxe', destination: 'hand' }],
    ['attack', 'attackWithEvidence', { target: 'nearest_hostile' }],
    ['chat', 'chat', { message: 'hello' }],
    ['recipes', 'recipes', { item: 'iron_pickaxe' }],
    ['mine_shaft', 'mineShaft', { target_y: 50, minimum_cobblestone: 0 }],
  ];

  for (const [capability, actionName, parameters] of cases) {
    let markStarted;
    const started = new Promise((resolve) => { markStarted = resolve; });
    let observedSignal;
    const action = async (...args) => {
      const context = args.at(-1);
      observedSignal = context.signal;
      markStarted();
      await new Promise((resolve, reject) => {
        const abort = () => reject(new DOMException('operator stop', 'AbortError'));
        if (context.signal.aborted) abort();
        else context.signal.addEventListener('abort', abort, { once: true });
      });
    };
    const { adapter } = adapterFixture({ actions: { [actionName]: action } });
    const actionRequest = request(adapter, capability, parameters, `cancel-${capability}`);
    const pending = adapter.runtime.executeAction(actionRequest);
    await started;

    const acknowledgement = await adapter.runtime.cancelAction({
      schema_version: '2',
      runtime_instance_id: adapter.runtimeInstanceId,
      correlation_id: actionRequest.correlation_id,
      reason: 'operator stop',
    });
    const receipt = await pending;

    assert.equal(acknowledgement.accepted, true, capability);
    assert.equal(observedSignal.aborted, true, capability);
    assert.equal(receipt.outcome, 'cancelled', capability);
    adapter.dispose();
  }
});


test('bot end during initial presentation is protected before the action starts', async () => {
  let markLookStarted;
  const lookStarted = new Promise((resolve) => { markLookStarted = resolve; });
  let releaseLook;
  const lookGate = new Promise((resolve) => { releaseLook = resolve; });
  let actionInvoked = false;
  const { adapter, bot, protocolClient } = adapterFixture({
    look: async () => {
      markLookStarted();
      await lookGate;
    },
    actions: {
      goto: async () => {
        actionInvoked = true;
        return 'moved';
      },
    },
    presentation: { mode: 'full', tempo: 'normal', seed: 'lifecycle-seed' },
  });

  const pending = adapter.runtime.executeAction(request(
    adapter,
    'goto',
    { x: 3, y: 64, z: 0 },
    'lifecycle-focus',
  ));
  await lookStarted;
  protocolClient.state = 'ended';
  bot.emit('end', 'connection lost');
  releaseLook();
  const receipt = await Promise.race([
    pending,
    new Promise((resolve) => setTimeout(() => resolve('timed_out'), 1_000)),
  ]);

  assert.notEqual(receipt, 'timed_out');
  assert.equal(receipt.outcome, 'error');
  assert.equal(receipt.error.code, 'RUNTIME_DISCONNECTED');
  assert.equal(actionInvoked, false);
  adapter.dispose();
});


test('quiescent bot with a pending mutation stays quarantined and busy after cancellation', async () => {
  let markStarted;
  const started = new Promise((resolve) => { markStarted = resolve; });
  let release;
  const mutationGate = new Promise((resolve) => { release = resolve; });
  let worldMutations = 0;
  const { adapter } = adapterFixture({
    actions: {
      placeWithEvidence: async () => {
        markStarted();
        await mutationGate;
        worldMutations += 1;
        return 'placed';
      },
    },
  });
  const actionRequest = request(
    adapter,
    'place',
    { block_type: 'stone', x: 1, y: 64, z: 0, facing: 'north' },
    'late-place-cancel',
  );
  const pending = adapter.runtime.executeAction(actionRequest);
  await started;

  const acknowledgement = await adapter.runtime.cancelAction({
    schema_version: '2',
    runtime_instance_id: adapter.runtimeInstanceId,
    correlation_id: actionRequest.correlation_id,
    reason: 'operator stop',
  });
  assert.equal(acknowledgement.accepted, true);

  const receipt = await pending;
  assert.equal(receipt.outcome, 'unknown');
  assert.equal(receipt.error.code, 'CANCEL_SETTLEMENT_TIMEOUT');
  assert.equal(receipt.error.world_may_have_changed, true);
  assert.equal((await adapter.runtime.health()).busy, true);
  assert.equal(worldMutations, 0);

  release();
  await receipt.operationSettlement;
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(worldMutations, 1);
  const settledHealth = await adapter.runtime.health();
  assert.equal(settledHealth.busy, false);
  assert.equal(settledHealth.ready, false);
  adapter.dispose();
});
