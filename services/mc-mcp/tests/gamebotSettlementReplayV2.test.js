import test from 'node:test';
import assert from 'node:assert/strict';

import { createGameBotRuntimeV2 } from '../src/gamebotRuntimeV2.js';


function budget(overrides = {}) {
  return {
    max_actions: 4,
    max_strategy_attempts: 1,
    max_travel_distance: 32,
    max_blocks_changed: 4,
    max_damage_taken: 2,
    protected_items: [],
    resource_consumption: {},
    ...overrides,
  };
}


function profile() {
  return {
    schema_version: '1',
    runtime_protocol: '2.0',
    minecraft_version: '1.21.1',
    capability_schema_digest: 'a'.repeat(64),
    skill_api_version: '1',
    policy_version: '1',
    server_identity_hash: 'b'.repeat(64),
    world_identity_hash: 'c'.repeat(64),
    dimension: 'minecraft:overworld',
    modset_digest: 'd'.repeat(64),
  };
}


function request(capability, parameters) {
  return {
    schema_version: '2',
    transport_id: 'transport-replay',
    command_id: `command-${capability}`,
    step_id: `step-${capability}`,
    correlation_id: `replay-${capability}`,
    runtime_instance_id: 'runtime-replay',
    capability,
    parameters,
    remaining_budget: budget(),
    deadline_ms: 1_900_000_000_000,
    previous_receipt_hash: '',
  };
}


function runtime({ capability, parametersSchema, observeState, invoke }) {
  let now = 1_800_000_000_000;
  let tick = 80;
  return createGameBotRuntimeV2({
    runtimeInstanceId: 'runtime-replay',
    environmentProfile: profile(),
    nowMs: () => ++now,
    getTick: () => ++tick,
    observeState,
    postActionSettleTimeoutMs: 20,
    postActionSettlePollMs: 10,
    postActionStableSamples: 2,
    waitMs: async () => {},
    capabilities: {
      [capability]: {
        risk: 'survival_safe',
        effectClass: 'state_changing',
        parametersSchema,
        maximumCost: budget({ max_actions: 1 }),
        invoke,
      },
    },
  });
}


function delayedPickupReplay({ pickupAtMs = 4614, deadlineAfterMs = 20000 } = {}) {
  const base = 1_800_000_000_000;
  let elapsed = 0;
  let active = false;
  const gamebot = createGameBotRuntimeV2({
    runtimeInstanceId: 'runtime-replay', environmentProfile: profile(),
    nowMs: () => base + elapsed, getTick: () => Math.floor(elapsed / 50),
    waitMs: async delay => { elapsed += delay; },
    observeState: async () => ({
      position: { x: 31.5, y: 50, z: 40.6 }, health: 20, food: 20,
      inventory: { cobblestone: active && elapsed >= pickupAtMs ? 91 : 90, gravel: 1 },
      environment: {
        dimension: 'minecraft:overworld', on_ground: true,
        velocity: { x: 0, y: -0.0784, z: 0 },
        pending_item_pickups: active && elapsed < pickupAtMs ? 1 : 0,
      },
    }),
    capabilities: { acquire_flint: {
      risk: 'survival_safe', effectClass: 'state_changing', parametersSchema: { type: 'object' },
      maximumCost: budget({ max_actions: 1, max_strategy_attempts: 0, max_travel_distance: 0, max_blocks_changed: 0, max_damage_taken: 0 }),
      invoke: async () => {
        active = true;
        throw Object.assign(new Error('remaining block reservation exhausted'), {
          code: 'BUDGET_EXHAUSTED',
          budget_usage: budget({ max_actions: 1, max_strategy_attempts: 0, max_travel_distance: 29.128, max_blocks_changed: 48, max_damage_taken: 0 }),
        });
      },
    } },
  });
  const action = { ...request('acquire_flint', {}), deadline_ms: base + deadlineAfterMs,
    remaining_budget: budget({ max_actions: 1, max_blocks_changed: 48, max_travel_distance: 64, max_damage_taken: 0 }) };
  return { gamebot, action, elapsed: () => elapsed };
}


test('R103 pending pickup cannot publish a stable error before the inventory update', async () => {
  const { gamebot, action, elapsed } = delayedPickupReplay();
  const receipt = await gamebot.executeAction(action);
  assert.equal(receipt.outcome, 'error');
  assert.equal(receipt.error.code, 'BUDGET_EXHAUSTED');
  assert.equal(receipt.post_observation, 'stable');
  assert.equal(receipt.reconciliation, 'accepted');
  assert.ok(elapsed() >= 4614 && elapsed() < 10000);
  const after = receipt.explained_mutations.find(m => m.subject === 'observable_state').details.after_state;
  assert.equal(after.inventory.cobblestone, 91);
  assert.equal(receipt.budget_usage.max_blocks_changed, 48);
});


test('pending pickup remains unreconciled when the original deadline expires', async () => {
  const { gamebot, action, elapsed } = delayedPickupReplay({ pickupAtMs: Infinity, deadlineAfterMs: 1000 });
  const receipt = await gamebot.executeAction(action);
  assert.equal(receipt.post_observation, 'unstable');
  assert.equal(receipt.reconciliation, 'pending');
  assert.ok(elapsed() <= 1000);
  assert.equal(receipt.settlement_trace.at(-1).stable_streak, 0);
});


test('grounded Mineflayer gravity remainder counts as settled', async () => {
  let actionComplete = false;
  const gamebot = runtime({
    capability: 'collect',
    parametersSchema: {
      type: 'object',
      properties: { count: { type: 'integer', minimum: 1 } },
      required: ['count'],
      additionalProperties: false,
    },
    invoke: async () => {
      actionComplete = true;
      return {
        output: { collected: 1 },
        explained_mutations: [
          { kind: 'inventory', subject: 'cobblestone', delta: 1, details: {} },
        ],
        budget_usage: budget({ max_actions: 1 }),
      };
    },
    observeState: async () => ({
      position: { x: 4, y: 65, z: 2 },
      health: 20,
      food: 20,
      inventory: actionComplete ? { cobblestone: 1 } : {},
      equipment: { hand: 'stone_pickaxe' },
      environment: {
        dimension: 'minecraft:overworld',
        on_ground: true,
        velocity: { x: 0, y: -0.0784000015, z: 0 },
      },
    }),
  });

  const receipt = await gamebot.executeAction(request('collect', { count: 1 }));

  assert.equal(receipt.post_observation, 'stable');
  assert.equal(receipt.reconciliation, 'accepted');
  assert.equal(receipt.settlement_trace.at(-1).stable_streak, 2);
});


test('grounded state does not hide a large downward velocity', async () => {
  let actionComplete = false;
  const gamebot = runtime({
    capability: 'collect',
    parametersSchema: {
      type: 'object',
      properties: { count: { type: 'integer', minimum: 1 } },
      required: ['count'],
      additionalProperties: false,
    },
    invoke: async () => {
      actionComplete = true;
      return {
        output: { collected: 1 },
        explained_mutations: [
          { kind: 'inventory', subject: 'cobblestone', delta: 1, details: {} },
        ],
        budget_usage: budget({ max_actions: 1 }),
      };
    },
    observeState: async () => ({
      position: { x: 4, y: 65, z: 2 },
      health: 20,
      food: 20,
      inventory: actionComplete ? { cobblestone: 1 } : {},
      equipment: { hand: 'stone_pickaxe' },
      environment: {
        dimension: 'minecraft:overworld',
        on_ground: true,
        velocity: { x: 0, y: -2, z: 0 },
      },
    }),
  });

  const receipt = await gamebot.executeAction(request('collect', { count: 1 }));

  assert.equal(receipt.post_observation, 'unstable');
  assert.equal(receipt.reconciliation, 'pending');
  assert.equal(receipt.settlement_trace.at(-1).stable_streak, 0);
  assert.equal(receipt.settlement_trace.at(-1).rejection_reason, 'motion_unsettled');
});


test('final20 replay preserves acquisition success while reconciliation waits for stability', async () => {
  let actionComplete = false;
  let postActionSample = 0;
  const gamebot = runtime({
    capability: 'collect',
    parametersSchema: {
      type: 'object',
      properties: { count: { type: 'integer', minimum: 1 } },
      required: ['count'],
      additionalProperties: false,
    },
    invoke: async () => {
      actionComplete = true;
      return {
        output: { collected: 2 },
        explained_mutations: [
          { kind: 'inventory', subject: 'raw_copper', delta: 2, details: {} },
        ],
        budget_usage: budget({ max_actions: 1 }),
      };
    },
    observeState: async () => {
      if (!actionComplete) {
        return {
          position: { x: 8, y: 59, z: 5 },
          health: 20,
          food: 20,
          inventory: { raw_copper: 2 },
          equipment: { hand: 'stone_sword' },
          environment: {
            dimension: 'minecraft:overworld',
            blocks: { feet: 'air', below1: 'stone' },
            on_ground: true,
            velocity: { x: 0, y: 0, z: 0 },
          },
        };
      }
      postActionSample += 1;
      return {
        position: { x: 8 + (postActionSample * 0.25), y: 59, z: 5 },
        health: 20,
        food: 20,
        inventory: { raw_copper: 4 },
        equipment: { hand: postActionSample === 1 ? 'stone_sword' : 'dirt' },
        environment: {
          dimension: 'minecraft:overworld',
          blocks: { feet: postActionSample === 1 ? 'air' : 'stone', below1: 'stone' },
          on_ground: true,
          velocity: { x: 0, y: 0, z: 0 },
        },
      };
    },
  });

  const receipt = await gamebot.executeAction(request('collect', { count: 2 }));

  assert.equal(receipt.outcome, 'success');
  assert.equal(receipt.error, null);
  assert.equal(receipt.post_observation, 'unstable');
  assert.equal(receipt.reconciliation, 'pending');
  assert.equal(receipt.goal_verification, 'unknown');
  assert.equal(receipt.reconciliation_error.code, 'POST_ACTION_OBSERVATION_UNSTABLE');
  assert.equal(receipt.settlement_trace.length, 3);
  assert.deepEqual(
    Object.keys(receipt.settlement_trace[0]).sort(),
    [
      'captured_at_ms',
      'durable_state_hash',
      'on_ground',
      'position',
      'rejection_reason',
      'sample_index',
      'stable_streak',
      'velocity',
    ],
  );
});


test('final21 replay preserves defeated combat outcome while reconciliation is pending', async () => {
  let actionComplete = false;
  let postActionSample = 0;
  const gamebot = runtime({
    capability: 'attack',
    parametersSchema: {
      type: 'object',
      properties: { entity_id: { type: 'string' } },
      required: ['entity_id'],
      additionalProperties: false,
    },
    invoke: async () => {
      actionComplete = true;
      return {
        output: { attacked: 'zombie-1' },
        explained_mutations: [
          { kind: 'combat', subject: 'zombie-1', delta: -20, details: {} },
        ],
        combat: {
          target_entity_id: 'zombie-1',
          target_entity_type: 'zombie',
          outcome: 'defeated',
          bot_health_before: 20,
          bot_health_after: 20,
          target_health_before: 20,
          target_health_after: 0,
          started_tick: 81,
          finished_tick: 83,
        },
        budget_usage: budget({ max_actions: 1 }),
      };
    },
    observeState: async () => {
      if (!actionComplete) {
        return {
          position: { x: 16, y: 65, z: 0 },
          health: 20,
          food: 20,
          inventory: {},
          equipment: { hand: 'stone_sword' },
          environment: { dimension: 'minecraft:overworld', on_ground: true },
          visible_entities: [
            {
              entity_id: 'zombie-1',
              entity_type: 'zombie',
              position: { x: 17, y: 65, z: 0 },
              health: 20,
            },
          ],
        };
      }
      postActionSample += 1;
      return {
        position: { x: 16 + (postActionSample * 0.25), y: 65, z: 0 },
        health: 20,
        food: 20,
        inventory: {},
        equipment: { hand: 'stone_sword' },
        environment: {
          dimension: 'minecraft:overworld',
          on_ground: true,
          velocity: { x: 0, y: 0, z: 0 },
        },
        visible_entities: [],
      };
    },
  });

  const receipt = await gamebot.executeAction(request('attack', { entity_id: 'zombie-1' }));

  assert.equal(receipt.outcome, 'success');
  assert.equal(receipt.combat.outcome, 'defeated');
  assert.equal(receipt.combat.target_health_after, 0);
  assert.equal(receipt.post_observation, 'unstable');
  assert.equal(receipt.reconciliation, 'pending');
  assert.equal(receipt.goal_verification, 'unknown');
  assert.ok(receipt.settlement_trace.every((sample) => sample.stable_streak === 1));
});
