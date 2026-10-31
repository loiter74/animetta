import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

import { createAdvancementAdapterV2 } from '../advancementAdapterV2.js';
import {
  inspectRegionBlocks,
  projectVisibleDiscovery,
} from '../gamebotEvidenceV2.js';
import { createGameBotRuntimeV2 } from '../gamebotRuntimeV2.js';
import { AIR_RECOVERY_MS, surfaceEscapePlan } from '../navigation.js';
import { ownOxygenLevel } from './playerVitals.js';
import { withActionEvidence } from './actionEvidence.js';
import { projectJumpTravel } from './motionBudget.js';
import { createCollectionSafety, MOVEMENT_STOPPING_RESERVE } from './collectionSafety.js';
import { findHostileThreat } from '../survivalThreats.js';
import { createRetreatPolicy } from '../survivalRetreat.js';
import {
  BroadcastMotionPolicy,
  resolvePresentationConfig,
} from './broadcastMotionPolicy.js';
import {
  MOVEMENT_CONTROLS,
  OperationScopeError,
  createOperationScope,
  runWithOperationScope,
} from './operationScope.js';
import {
  capturePresentationSnapshot,
  createPresentationPort,
  executePresentationDecision,
} from './presentationPort.js';


const schemaDigest = readFileSync(
  new URL('../../../../contracts/gamebot/v2/schema.sha256', import.meta.url),
  'utf8',
).trim();
export const VISUAL_PRESENTATION_CAPABILITIES = Object.freeze([
  'goto',
  'place',
  'collect',
  'mine',
  'craft',
  'smelt',
  'equip',
]);


function sha256(value) {
  return createHash('sha256').update(String(value), 'utf8').digest('hex');
}


function emptyBudget(overrides = {}) {
  return {
    max_actions: 0,
    max_strategy_attempts: 0,
    max_travel_distance: 0,
    max_blocks_changed: 0,
    max_damage_taken: 0,
    protected_items: [],
    resource_consumption: {},
    ...overrides,
  };
}


function normalizedBudgetNumber(rawValue, field, fallback, { integer = false } = {}) {
  if (rawValue === undefined) return fallback;
  const value = Number(rawValue);
  if (!Number.isFinite(value) || value < 0 || (integer && !Number.isInteger(value))) {
    const error = new TypeError(`Invalid capability budget field: ${field}`);
    error.code = 'INVALID_BUDGET_USAGE';
    error.details = { field, value: rawValue };
    throw error;
  }
  return value;
}


function normalizeBudgetUsage(usage, defaultMaxActions) {
  const source = usage && typeof usage === 'object' && !Array.isArray(usage) ? usage : {};
  const protectedItems = source.protected_items ?? [];
  const resourceConsumption = source.resource_consumption ?? {};
  if (!Array.isArray(protectedItems) || protectedItems.some((item) => typeof item !== 'string')) {
    const error = new TypeError('Invalid capability budget field: protected_items');
    error.code = 'INVALID_BUDGET_USAGE';
    error.details = { field: 'protected_items' };
    throw error;
  }
  if (
    !resourceConsumption
    || typeof resourceConsumption !== 'object'
    || Array.isArray(resourceConsumption)
  ) {
    const error = new TypeError('Invalid capability budget field: resource_consumption');
    error.code = 'INVALID_BUDGET_USAGE';
    error.details = { field: 'resource_consumption' };
    throw error;
  }
  const normalizedResources = Object.fromEntries(
    Object.entries(resourceConsumption).map(([item, amount]) => [
      item,
      normalizedBudgetNumber(amount, `resource_consumption.${item}`, 0, { integer: true }),
    ]),
  );
  return {
    max_actions: normalizedBudgetNumber(
      source.max_actions,
      'max_actions',
      defaultMaxActions,
      { integer: true },
    ),
    max_strategy_attempts: normalizedBudgetNumber(
      source.max_strategy_attempts,
      'max_strategy_attempts',
      0,
      { integer: true },
    ),
    max_travel_distance: normalizedBudgetNumber(
      source.max_travel_distance,
      'max_travel_distance',
      0,
    ),
    max_blocks_changed: normalizedBudgetNumber(
      source.max_blocks_changed,
      'max_blocks_changed',
      0,
      { integer: true },
    ),
    max_damage_taken: normalizedBudgetNumber(source.max_damage_taken, 'max_damage_taken', 0),
    protected_items: [...protectedItems],
    resource_consumption: normalizedResources,
  };
}


function normalizeCapabilityResult(value, { readOnly }) {
  const structured = value && typeof value === 'object' && !Array.isArray(value) && [
    'output',
    'explained_mutations',
    'budget_usage',
    'combat',
  ].some((field) => Object.hasOwn(value, field));
  const result = structured ? { ...value } : { output: value };
  return {
    ...result,
    output: Object.hasOwn(result, 'output') ? result.output : null,
    explained_mutations: Array.isArray(result.explained_mutations)
      ? [...result.explained_mutations]
      : [],
    budget_usage: normalizeBudgetUsage(result.budget_usage, readOnly ? 0 : 1),
  };
}


export function getStatusSnapshot(bot) {
  const inventory = {};
  const blocks = {};
  try {
    for (const item of bot.inventory?.items?.() ?? []) {
      inventory[item.name] = (inventory[item.name] || 0) + item.count;
    }
  } catch {
    // A pre-spawn bot may not expose inventory yet.
  }
  try {
    if (bot.entity?.position?.floored && bot.blockAt) {
      const base = bot.entity.position.floored();
      const samples = {
        feet: base,
        head: base.offset(0, 1, 0),
        below1: base.offset(0, -1, 0),
        below2: base.offset(0, -2, 0),
        north_support: base.offset(0, -1, -1),
        south_support: base.offset(0, -1, 1),
        east_support: base.offset(1, -1, 0),
        west_support: base.offset(-1, -1, 0),
      };
      for (const [name, position] of Object.entries(samples)) {
        const block = bot.blockAt(position);
        blocks[name] = block ? {
          name: block.name,
          boundingBox: block.boundingBox,
          position: { x: position.x, y: position.y, z: position.z },
        } : null;
      }
    }
  } catch {
    // Observation remains useful when local block sampling is unavailable.
  }
  return {
    position: bot.entity ? {
      x: Math.round(bot.entity.position.x),
      y: Math.round(bot.entity.position.y),
      z: Math.round(bot.entity.position.z),
    } : null,
    health: bot.health,
    food: bot.food,
    inventory,
    blocks,
    fall_distance: bot.entity?.fallDistance || 0,
    on_ground: bot.entity?.onGround !== false,
    velocity: bot.entity?.velocity ? {
      x: bot.entity.velocity.x,
      y: bot.entity.velocity.y,
      z: bot.entity.velocity.z,
    } : { x: 0, y: 0, z: 0 },
  };
}


function environmentProfile(bot, connection) {
  const { host, port, version } = connection;
  return {
    schema_version: '1',
    runtime_protocol: '2.0',
    minecraft_version: bot.version || version || 'unknown',
    server_identity_hash: sha256(`${host}:${port}`),
    world_identity_hash: sha256(process.env.GAMEBOT_WORLD_ID || `${host}:${port}:default`),
    dimension: bot.game?.dimension || 'minecraft:overworld',
    modset_digest: sha256(process.env.GAMEBOT_MODSET_ID || 'mineflayer-default'),
    capability_schema_digest: schemaDigest,
    skill_api_version: '1',
    policy_version: '1',
  };
}


function capabilityDescriptors(bot, actions) {
  return {
    observe: {
      parameters: {},
      invoke: () => getStatusSnapshot(bot),
    },
    status: {
      parameters: {},
      invoke: () => getStatusSnapshot(bot),
    },
    goto: {
      parameters: { x: { type: 'number' }, y: { type: 'number' }, z: { type: 'number' } },
      invoke: ({ x, y, z }, context) => actions.goto(x, y, z, context),
      target: ({ x, y, z }) => ({ x, y: y + 0.5, z }),
    },
    collect: {
      parameters: {
        block_type: { type: 'string' },
        count: { type: 'integer', minimum: 1, maximum: 64 },
      },
      invoke: ({ block_type, count = 1 }, context) => (
        actions.collectWithEvidence(block_type, count, context)
      ),
    },
    mine: {
      parameters: {
        block_type: { type: 'string' },
        count: { type: 'integer', minimum: 1, maximum: 64 },
      },
      invoke: ({ block_type, count = 1 }, context) => actions.mine(block_type, count, context),
    },
    craft: {
      parameters: {
        recipe: { type: 'string' },
        count: { type: 'integer', minimum: 1, maximum: 64 },
      },
      invoke: ({ recipe, count = 1 }, context) => actions.craft(recipe, count, context),
    },
    place: {
      parameters: {
        block_type: { type: 'string' },
        x: { type: 'number' },
        y: { type: 'number' },
        z: { type: 'number' },
        facing: { type: 'string', enum: ['north', 'south', 'east', 'west'] },
      },
      invoke: ({ block_type, x, y, z, facing }, context) => (
        actions.placeWithEvidence(block_type, x, y, z, facing, context)
      ),
      target: ({ x, y, z }) => ({ x: x + 0.5, y: y + 0.5, z: z + 0.5 }),
    },
    smelt: {
      parameters: {
        item: { type: 'string' },
        fuel: { type: 'string' },
        count: { type: 'integer', minimum: 1, maximum: 64 },
      },
      invoke: ({ item, fuel, count = 1 }, context) => actions.smelt(item, fuel, count, context),
    },
    equip: {
      parameters: { item: { type: 'string' }, destination: { type: 'string' } },
      invoke: ({ item, destination = 'hand' }, context) => actions.equip(item, destination, context),
    },
    attack: {
      parameters: { target: { type: 'string' } },
      invoke: ({ target = 'nearest_hostile' }, context) => (
        actions.attackWithEvidence(target, context)
      ),
    },
    chat: {
      parameters: { message: { type: 'string' } },
      invoke: ({ message }, context) => actions.chat(message, context),
    },
    recipes: {
      parameters: { item: { type: 'string' } },
      invoke: ({ item }, context) => actions.recipes(item, context),
    },
    mine_shaft: {
      parameters: {
        target_y: { type: 'integer', minimum: -64, maximum: 64 },
        minimum_cobblestone: { type: 'integer', minimum: 0, maximum: 64 },
      },
      invoke: ({ target_y = 50, minimum_cobblestone = 0 }, context) => (
        actions.mineShaft(target_y, minimum_cobblestone, context)
      ),
    },
    acquire_flint: {
      parameters: { max_attempts: { type: 'integer', minimum: 1, maximum: 32 } },
      invoke: ({ max_attempts = 16 }, context) => actions.acquireFlint(max_attempts, context),
    },
    fill_water_bucket: {
      parameters: {},
      invoke: (_parameters, context) => actions.fillWaterBucket(context),
    },
    prepare_obsidian: {
      parameters: {},
      invoke: (_parameters, context) => actions.prepareObsidian(context),
    },
    eat: {
      parameters: { item: { type: 'string' } },
      invoke: ({ item }, context) => actions.eat(item, context),
    },
    forage_apples: {
      parameters: { max_blocks: { type: 'integer', minimum: 1, maximum: 8 } },
      invoke: ({ max_blocks = 8 }, context) => actions.forageApples(max_blocks, context),
    },
    wait_for_regeneration: {
      parameters: {},
      invoke: (_parameters, context) => actions.waitForRegeneration(context),
    },
    explore_surface: {
      parameters: { x: { type: 'integer' }, z: { type: 'integer' } },
      invoke: ({ x, z }, context) => actions.exploreSurface(x, z, context),
    },
    ignite_portal: {
      parameters: { x: { type: 'integer' }, y: { type: 'integer' }, z: { type: 'integer' } },
      invoke: (parameters, context) => actions.ignitePortal(parameters, context),
    },
  };
}


function guardBotAction(
  bot,
  abortActive,
  invoke,
  context,
  includeContainers,
  abortLifecycle,
  airRecoveryDeadline = 0,
  readBlockChanges = () => 0,
) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let lifecycleError = null;
    let invocationSettlement = Promise.resolve();
    let invocationEvidence;
    const actionBudget = ['observe', 'status', 'recipes'].includes(context.capability) ? null : context.budget;
    let previousPosition = { ...bot.entity?.position };
    let previousHealth = bot.health;
    const motionUsage = context.motion_usage;
    const retreatPolicy = () => context.retreat_policy || context.collection_safety?.retreatPolicy;
    let damage = 0;
    const originalSetControlState = bot.setControlState;
    let guardedSetControlState;
    const guardedMutations = new Map();
    let pendingBlockChanges = 0;
    const cleanup = () => {
      context.collection_safety?.dispose();
      bot.removeListener('death', onDeath);
      bot.removeListener('end', onEnd);
      bot.removeListener('breath', onBreath);
      bot.removeListener('move', onMove);
      bot.removeListener('health', onHealth);
      bot.removeListener('physicsTick', checkPhysicsSafety);
      bot.removeListener('entityMoved', checkSurvivalThreat);
      bot.removeListener('entitySpawn', checkSurvivalThreat);
      context.signal?.removeEventListener('abort', onAbort);
      if (guardedSetControlState && bot.setControlState === guardedSetControlState) {
        bot.setControlState = originalSetControlState;
      }
      for (const [method, { original, guarded }] of guardedMutations) {
        if (bot[method] === guarded) bot[method] = original;
      }
    };
    const fail = (code, message, details = {}) => {
      if (settled || lifecycleError) return;
      const error = new Error(message);
      error.code = code;
      error.retryable = true;
      const position = bot.entity?.position;
      error.details = {
        oxygen_level: ownOxygenLevel(bot),
        position: position ? { x: position.x, y: position.y, z: position.z } : null,
        ...details,
      };
      lifecycleError ??= error;
      abortLifecycle(message);
      void Promise.resolve(abortActive()).catch(() => {});
    };
    const checkActionBudget = () => {
      if (!actionBudget) return;
      // Dry navigation walks without sprinting/parkour. Stop two blocks early
      // for the current physics tick and braking; never alter charged usage.
      if (((context.capability === 'collect' || motionUsage.travel > 0)
        && motionUsage.travel >= Math.max(0, actionBudget.max_travel_distance - MOVEMENT_STOPPING_RESERVE))
        || damage > actionBudget.max_damage_taken) {
        fail('BUDGET_EXHAUSTED', '动作接近移动预算上限或已超过伤害预算，已停止当前动作。', {
          travel_distance: motionUsage.travel, damage_taken: damage, stopping_reserve: MOVEMENT_STOPPING_RESERVE,
        });
      }
    };
    const onMove = () => {
      const position = bot.entity?.position;
      if (!position) return;
      if (retreatPolicy() && !retreatPolicy().permitsMove(previousPosition, position, true)) {
        fail('UNSAFE_AREA', '避险移动开始靠近敌对生物，已停止当前动作。');
      }
      motionUsage.travel += Math.hypot(position.x - previousPosition.x,
        position.y - previousPosition.y, position.z - previousPosition.z);
      previousPosition = { ...position };
      checkActionBudget();
    };
    const checkSurvivalThreat = () => {
      if (!actionBudget || context.capability === 'attack') return;
      const threat = findHostileThreat(bot);
      if (threat && !retreatPolicy()?.permitsThreat(threat)
        && !context.collection_safety?.requestPause(threat)) {
        fail('UNSAFE_AREA', '附近敌对生物已进入预警范围，已停止危险动作。', { threat });
      }
    };
    const checkJumpBudget = (requested = false) => {
      if (!actionBudget || !bot.physics?.simulatePlayer || bot.entity?.onGround !== true
        || bot.entity.isInWater || bot.entity.isInLava || bot.entity.elytraFlying) return true;
      const current = bot.controlState || bot.controlStates || {};
      if (!requested && !current.jump && !bot.jumpQueued) return true;
      const controls = Object.fromEntries(MOVEMENT_CONTROLS.map(name => [name, current[name] === true]));
      if (requested) controls.jump = true;
      const distance = projectJumpTravel(bot, controls);
      if (distance === null || motionUsage.travel + distance + MOVEMENT_STOPPING_RESERVE > actionBudget.max_travel_distance) {
        fail('BUDGET_EXHAUSTED', '剩余移动预算无法覆盖已知跳跃和安全停止。', {
          travel_distance: motionUsage.travel, minimum_motion_distance: distance,
          motion_prediction: distance === null ? 'unknown' : 'settled',
          stopping_reserve: MOVEMENT_STOPPING_RESERVE,
        });
        return false;
      }
      return true;
    };
    const checkPhysicsSafety = () => {
      checkSurvivalThreat();
      if (!context.signal?.aborted) checkJumpBudget();
    };
    const onHealth = () => {
      damage += Math.max(0, previousHealth - bot.health);
      previousHealth = bot.health;
      checkActionBudget();
    };
    const onDeath = () => fail('BOT_DIED', 'Bot died during capability execution');
    const onBreath = () => {
      const oxygen = ownOxygenLevel(bot);
      if (oxygen !== null && oxygen <= 14 && Date.now() >= airRecoveryDeadline) {
        fail('OXYGEN_LOW', '空气不足，已中止当前动作以保护角色。');
      }
    };
    const onEnd = (reason) => fail(
      'RUNTIME_DISCONNECTED',
      `Runtime disconnected during capability execution: ${reason || 'unknown'}`,
    );
    const onAbort = async () => {
      if (settled) return;
      let quiet = false;
      try {
        quiet = await context.operation_scope.interrupt({
          includeContainers,
          operationSettlement: invocationSettlement,
        });
      } catch {
        // Failed cleanup is treated as a settlement timeout below.
      }
      if (settled) return;
      settled = true;
      cleanup();
      const failure = quiet
        ? lifecycleError || new OperationScopeError('ACTION_CANCELLED', 'Action cancelled')
        : new OperationScopeError(
          'CANCEL_SETTLEMENT_TIMEOUT',
          'Mineflayer operation did not settle after cancellation',
          { world_may_have_changed: true, cause_code: lifecycleError?.code ?? 'ACTION_CANCELLED',
            cause_details: lifecycleError?.details ?? {} },
        );
      // Both successful and rejected native settlements can carry partial work.
      // Keep the cancellation outcome, but charge the evidence after braking.
      for (const key of ['budget_usage', 'explained_mutations']) {
        if (invocationEvidence?.[key] !== undefined) failure[key] = invocationEvidence[key];
      }
      if (!quiet) {
        Object.defineProperty(failure, 'operationSettlement', {
          value: Promise.all([
            invocationSettlement,
            context.operation_scope.waitForEventualQuiescence({ includeContainers }),
          ]).then(() => {}),
        });
      }
      reject(failure);
    };
    bot.once('death', onDeath);
    bot.once('end', onEnd);
    bot.on('breath', onBreath);
    if (actionBudget) {
      // Pathfinder digs and scaffolds through the same native methods. Admit
      // them against the receipt's live evidence, before any world mutation.
      for (const method of ['dig', 'placeBlock']) {
        const original = bot[method];
        if (typeof original !== 'function') continue;
        const guarded = async function (...args) {
          context.signal?.throwIfAborted();
          if (retreatPolicy()) {
            fail('UNSAFE_AREA', '避险移动禁止挖掘或放置方块。');
            context.signal?.throwIfAborted();
            throw lifecycleError;
          }
          if (context.collection_safety?.pending) {
            throw new OperationScopeError('COLLECTION_SAFETY_PAUSED', '采集正在安全暂停，暂不允许新的方块操作。');
          }
          const changed = readBlockChanges();
          if (changed + pendingBlockChanges >= actionBudget.max_blocks_changed) {
            fail('BUDGET_EXHAUSTED', '剩余方块预算不足以执行下一次挖掘或放置。', {
              blocks_changed: changed, pending_block_changes: pendingBlockChanges,
              maximum_blocks_changed: actionBudget.max_blocks_changed,
            });
            context.signal?.throwIfAborted();
            throw lifecycleError;
          }
          pendingBlockChanges++;
          try { return await original.apply(this, args); }
          finally { pendingBlockChanges--; }
        };
        guardedMutations.set(method, { original, guarded });
        bot[method] = guarded;
      }
      if (typeof originalSetControlState === 'function') {
        guardedSetControlState = function (control, value) {
          if (value === true && context.signal?.aborted) return;
          if (value === true && context.collection_safety?.pending && !retreatPolicy()) return;
          if (control === 'jump' && value === true && !checkJumpBudget(true)) return;
          return originalSetControlState.call(bot, control, value);
        };
        bot.setControlState = guardedSetControlState;
      }
      bot.on('move', onMove);
      bot.on('health', onHealth);
      bot.on('physicsTick', checkPhysicsSafety);
      bot.on('entityMoved', checkSurvivalThreat);
      bot.on('entitySpawn', checkSurvivalThreat);
    }
    context.signal?.addEventListener('abort', onAbort, { once: true });
    if (context.signal?.aborted) {
      void onAbort();
      return;
    }
    onBreath();
    checkActionBudget();
    checkSurvivalThreat();
    if (context.signal?.aborted) return;
    const invocationPromise = Promise.resolve().then(() => invoke((minimumDistance) => {
      if (!actionBudget || minimumDistance <= 0) return;
      if (motionUsage.travel + minimumDistance + MOVEMENT_STOPPING_RESERVE > actionBudget.max_travel_distance) {
        fail('BUDGET_EXHAUSTED', '剩余移动预算不足以完成下一段路径并安全停止。', {
          travel_distance: motionUsage.travel, minimum_navigation_distance: minimumDistance, stopping_reserve: MOVEMENT_STOPPING_RESERVE,
        });
        context.signal?.throwIfAborted();
      }
    }));
    invocationSettlement = invocationPromise.then(
      (value) => { invocationEvidence = value; },
      (error) => {
        invocationEvidence = error;
        return error?.operationSettlement ?? undefined;
      },
    );
    invocationPromise.then(
      (value) => {
        if (settled || context.signal?.aborted) return;
        settled = true;
        cleanup();
        resolve(value);
      },
      (error) => {
        if (settled || context.signal?.aborted) return;
        settled = true;
        cleanup();
        reject(error);
      },
    );
  });
}


function runtimeCapabilities(bot, actions, abortActive, motionPolicy) {
  return Object.fromEntries(
    Object.entries(capabilityDescriptors(bot, actions)).map(([name, descriptor]) => {
      const readOnly = ['observe', 'status', 'recipes'].includes(name);
      return [name, {
        risk: 'survival_safe',
        effectClass: readOnly ? 'read_only' : 'state_changing',
        parametersSchema: {
          type: 'object',
          properties: descriptor.parameters,
          additionalProperties: false,
        },
        maximumCost: emptyBudget({ max_actions: readOnly ? 0 : 1 }),
        async invoke(parameters, context) {
          context.signal?.throwIfAborted();
          const airRecoveryDeadline = name === 'goto' && surfaceEscapePlan(bot, parameters)
            ? Date.now() + AIR_RECOVERY_MS : 0;
          const lifecycleController = new AbortController();
          const operationSignal = context.signal
            ? AbortSignal.any([context.signal, lifecycleController.signal])
            : lifecycleController.signal;
          let checkNavigationBudget = () => {};
          let collectionSafety = null;
          const motionUsage = { travel: 0 };
          const scope = createOperationScope({
            bot,
            signal: operationSignal,
            deadlineMs: context.deadline_ms,
            reportPhase: context.report_phase,
            checkNavigationBudget: distance => checkNavigationBudget(distance),
            beforeOperation: name === 'collect' ? async () => {
              if (await collectionSafety?.checkpoint()) {
                throw new OperationScopeError('COLLECTION_SAFETY_PAUSED', '避险已完成，请重新选择安全的采集目标。');
              }
            } : null,
            containerCapable: ['craft', 'smelt'].includes(name),
          });
          if (name === 'collect') {
            collectionSafety = createCollectionSafety({
              bot, scope, signal: operationSignal, budget: context.budget, motionUsage,
            });
          }
          const targetPosition = descriptor.target?.(parameters) || null;
          const target = targetPosition
            ? { kind: name === 'place' ? 'block' : 'position', position: targetPosition }
            : undefined;
          const effectPort = createPresentationPort({
            bot,
            scope,
            reportPhase: context.report_phase,
          });
          let presentationUsage = { anchorCount: 0, dwellMs: 0 };
          const safeFocus = async ({
            phase,
            ordinal = 0,
            target: focusTarget = targetPosition,
            heldItemName = null,
          }) => {
            try {
              const presentation = {
                correlationId: context.correlation_id,
                capability: name,
                phase,
                ordinal,
                snapshot: capturePresentationSnapshot(bot, scope),
                usage: presentationUsage,
              };
              const decision = heldItemName
                ? motionPolicy.decideFocus({
                    ...presentation,
                    heldItemName,
                  })
                : motionPolicy.decideFocus({ ...presentation, target: focusTarget });
              presentationUsage = decision.nextUsage;
              await executePresentationDecision(decision, effectPort);
              return decision;
            } catch (error) {
              if (scope.signal?.aborted || error?.name === 'AbortError') throw error;
              return { applied: false, reason: 'presentation_error' };
            }
          };
          const presentationFacade = VISUAL_PRESENTATION_CAPABILITIES.includes(name)
            ? Object.freeze({
                focus: ({ phase, ordinal = 0, target: focusTarget }) => safeFocus({
                  phase,
                  ordinal,
                  target: focusTarget,
                }),
                focusHeldItem: ({ phase, ordinal = 0, itemName }) => safeFocus({
                  phase,
                  ordinal,
                  heldItemName: itemName,
                }),
              })
            : undefined;
          const scopedContext = Object.freeze({
            ...context,
            signal: operationSignal,
            operation_scope: scope,
            presentation: presentationFacade,
            retreat_policy: name === 'goto' ? createRetreatPolicy(bot, parameters) : null,
            collection_safety: collectionSafety,
            motion_usage: motionUsage,
          });
          const invoke = (_annotations, readBlockChanges) => runWithOperationScope(scope, () => guardBotAction(
            bot,
            abortActive,
            async (navigationBudgetGuard) => {
              checkNavigationBudget = navigationBudgetGuard;
              if (name === 'goto') {
                if (!airRecoveryDeadline) {
                  context.report_phase?.('aiming', { target });
                  await safeFocus({ phase: 'aiming' });
                }
                context.report_phase?.('moving', { target });
              } else if (name === 'place') {
                context.report_phase?.('aiming', { target });
                await safeFocus({ phase: 'aiming' });
                context.report_phase?.('acting', { target });
              } else if (['collect', 'mine', 'craft', 'smelt'].includes(name)) {
                context.report_phase?.('locating');
              } else {
                context.report_phase?.('acting');
              }
              const result = await descriptor.invoke(parameters, scopedContext);
              if (!operationSignal.aborted) await collectionSafety?.checkpoint();
              if (targetPosition && ['goto', 'place'].includes(name)) {
                await safeFocus({ phase: 'verifying', ordinal: 1 });
              }
              return result;
            },
            scopedContext,
            ['craft', 'smelt'].includes(name),
            (reason) => lifecycleController.abort(reason),
            airRecoveryDeadline,
            readBlockChanges,
          ));
          const normalizeResult = value => {
            return normalizeCapabilityResult(value, { readOnly });
          };
          return readOnly ? normalizeResult(await invoke())
            : withActionEvidence(bot, invoke, { normalizeResult });
        },
      }];
    }),
  );
}


function observationState(bot, advancementAdapter) {
  const snapshot = getStatusSnapshot(bot);
  const discovery = projectVisibleDiscovery(bot);
  const equipment = {};
  if (bot.heldItem?.name) equipment.hand = bot.heldItem.name;
  const slots = bot.inventory?.slots || [];
  for (const [name, slot] of Object.entries({ head: 5, torso: 6, legs: 7, feet: 8 })) {
    if (slots[slot]?.name) equipment[name] = slots[slot].name;
  }
  const biome = bot.entity ? bot.blockAt(bot.entity.position)?.biome?.name || 'unknown' : null;
  const oxygen = ownOxygenLevel(bot);
  return {
    position: snapshot.position,
    health: snapshot.health,
    food: Number.isFinite(snapshot.food) ? Math.trunc(snapshot.food) : null,
    inventory: snapshot.inventory,
    equipment,
    environment: {
      dimension: bot.game?.dimension || null,
      biome,
      blocks: snapshot.blocks,
      fall_distance: snapshot.fall_distance,
      on_ground: snapshot.on_ground,
      velocity: snapshot.velocity,
      ...(discovery.survival_retreat ? { survival_retreat: discovery.survival_retreat } : {}),
      ...(oxygen !== null ? { oxygen_level: oxygen } : {}),
    },
    biome,
    visible_blocks: discovery.visible_blocks,
    visible_entities: discovery.visible_entities,
    active_advancements: advancementAdapter?.getActiveAdvancements() || [],
  };
}


export function createGameBotV2Adapter({
  bot,
  connection,
  actions,
  abortActive,
  emitEvent,
  presentation = resolvePresentationConfig(),
}) {
  const runtimeInstanceId = [
    `${connection.username}@${connection.host}:${connection.port}`,
    process.pid,
    Date.now(),
  ].join(':');
  const presentationConfig = resolvePresentationConfig(presentation);
  const motionPolicy = new BroadcastMotionPolicy(presentationConfig);
  let advancementAdapter = null;
  const runtime = createGameBotRuntimeV2({
    runtimeInstanceId,
    environmentProfile: environmentProfile(bot, connection),
    capabilities: runtimeCapabilities(bot, actions, abortActive, motionPolicy),
    observeState: async () => observationState(bot, advancementAdapter),
    inspectRegionState: async (bounds) => inspectRegionBlocks(bot, bounds),
    maxRegionInspectionVolume: 4096,
    cancelActive: async () => abortActive(),
    getTick: () => bot.time?.age || 0,
    presentationMode: presentationConfig.mode,
    emitActionPhase: (event) => emitEvent('action_phase', event),
  });
  advancementAdapter = createAdvancementAdapterV2({
    runtimeInstanceId,
    captureObservation: (correlationId) => runtime.observe({
      runtime_instance_id: runtimeInstanceId,
      correlation_id: correlationId,
    }),
    emitEvent: (event) => emitEvent('advancement_observed', event),
    onError: (error) => emitEvent('error', {
      code: 'ADVANCEMENT_ADAPTER_ERROR',
      message: error.message,
    }),
  });
  advancementAdapter.attach(bot._client);
  return {
    runtime,
    runtimeInstanceId,
    dispose: () => advancementAdapter?.dispose(),
  };
}
