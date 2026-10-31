import Vec3 from 'vec3';
import { projectVisibleDiscovery } from '../gamebotEvidenceV2.js';
import { navigateTo } from '../navigation.js';
import { createRetreatPolicy } from '../survivalRetreat.js';
import { findHostileThreat } from '../survivalThreats.js';
import { OperationScopeError } from './operationScope.js';

export const MOVEMENT_STOPPING_RESERVE = 2;

// This is a cooperative pause inside one collection, never another command.
export function createCollectionSafety({
  bot, scope, signal = scope.signal, budget, motionUsage,
  discover = () => projectVisibleDiscovery(bot), navigate = navigateTo,
}) {
  let enabled = false;
  let disposed = false;
  let pause = null;
  let recovery = null;
  let recoveryCount = 0;
  const available = destination => {
    const center = new Vec3(destination.x + .5, destination.y, destination.z + .5);
    const distance = center.distanceTo(bot.entity.position);
    return distance + MOVEMENT_STOPPING_RESERVE < budget.max_travel_distance - motionUsage.travel;
  };
  const unsafe = () => new OperationScopeError(
    'UNSAFE_AREA', '采集避险出口已失效或剩余预算不足，已停止当前动作。',
  );
  return {
    enable() { if (!disposed) enabled = true; },
    get pending() { return pause !== null; },
    get retreatPolicy() { return pause?.retreating ? pause.policy : null; },
    get recoveryCount() { return recoveryCount; },
    requestPause(threat) {
      if (!enabled || disposed || signal?.aborted) return false;
      if (pause) return !pause.failure && !pause.retreating && pause.policy.permitsThreat(threat);
      const candidates = discover().survival_retreat?.candidates || [];
      const origin = bot.entity.position;
      const ordered = [...candidates].sort((a, b) => (
        origin.distanceTo(new Vec3(a.x + .5, a.y, a.z + .5))
        - origin.distanceTo(new Vec3(b.x + .5, b.y, b.z + .5))
      ));
      for (const destination of ordered) {
        const policy = available(destination) && createRetreatPolicy(bot, destination);
        if (policy) { pause = { destination, policy, retreating: false }; break; }
      }
      if (!pause) return false;
      // Interrupt synchronously, before another native mutation can be admitted.
      try {
        pause.settlement = Promise.resolve(scope.interrupt({ includeContainers: false })).catch(() => false);
      } catch { pause.settlement = Promise.resolve(false); }
      return true;
    },
    checkpoint() {
      signal?.throwIfAborted();
      if (pause?.failure) return Promise.reject(pause.failure);
      // The retreat navigation enters this hook itself; never recurse.
      if (!pause || pause.retreating) return Promise.resolve(false);
      if (recovery) return recovery;
      recovery = (async () => {
        const current = pause;
        const settled = await current.settlement;
        signal?.throwIfAborted();
        if (!settled) {
          const error = new OperationScopeError(
            'ACTION_SETTLEMENT_TIMEOUT', '采集暂停后原动作未停稳，已禁止继续避险。',
            { world_may_have_changed: true },
          );
          Object.defineProperty(error, 'operationSettlement', {
            value: scope.waitForEventualQuiescence({ includeContainers: false }),
          });
          throw error;
        }
        scope.checkpoint();
        const policy = createRetreatPolicy(bot, current.destination);
        if (disposed || !policy || !available(current.destination)) throw unsafe();
        current.policy = policy;
        current.retreating = true;
        await navigate(bot, current.destination, { operation_scope: scope, signal, retreat_policy: policy });
        signal?.throwIfAborted();
        scope.checkpoint();
        if (findHostileThreat(bot)) throw unsafe();
        pause = null;
        recoveryCount++;
        scope.reportPhase('recovering', {
          reason_code: 'HOSTILE_RETREAT', count: recoveryCount, destination: current.destination,
        });
        return true;
      })().catch(error => {
        if (pause) pause.failure = error;
        throw error;
      }).finally(() => { recovery = null; });
      return recovery;
    },
    dispose() { disposed = true; enabled = false; },
  };
}
