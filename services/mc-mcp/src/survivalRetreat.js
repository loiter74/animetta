import Vec3 from 'vec3';
import { hostileWarningRadius } from './survivalThreats.js';

const POSITION_EPSILON = 0.02;
const AIR = new Set(['air', 'cave_air', 'void_air']);
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);

function hostiles(bot) {
  return Object.values(bot.entities || {}).flatMap(entity => {
    const radius = hostileWarningRadius(entity);
    const p = entity?.position;
    return entity !== bot.entity && radius !== null && p
      && ['x', 'y', 'z'].every(axis => Number.isFinite(p[axis]))
      ? [{ entity, radius }] : [];
  });
}

function clearStanding(bot, destination) {
  if (typeof bot.blockAt !== 'function') return false;
  const feet = new Vec3(destination.x, destination.y, destination.z).floored();
  const support = bot.blockAt(feet.offset(0, -1, 0));
  return AIR.has(bot.blockAt(feet)?.name) && AIR.has(bot.blockAt(feet.offset(0, 1, 0))?.name)
    && !['magma_block', 'sand', 'red_sand', 'gravel', 'suspicious_sand', 'suspicious_gravel'].includes(support?.name)
    && !support?.name?.endsWith('_concrete_powder')
    && support?.shapes?.some(shape => shape.length === 6
      && shape.every((value, index) => value === (index < 3 ? 0 : 1)));
}

function safeDestination(bot, target, threats) {
  return threats.every(({ entity, radius }) => distance(target, entity.position) > radius)
    && clearStanding(bot, target);
}

export function createRetreatPolicy(bot, destination) {
  const origin = bot.entity?.position;
  if (!origin || !['x', 'y', 'z'].every(axis => Number.isFinite(destination?.[axis]))) return null;
  const target = new Vec3(Math.floor(destination.x) + 0.5, Math.floor(destination.y), Math.floor(destination.z) + 0.5);
  const threats = hostiles(bot);
  if (!threats.some(({ entity, radius }) => distance(origin, entity.position) <= radius)
    || !safeDestination(bot, target, threats)) return null;
  const inwardDrift = new Map();
  return {
    permitsThreat(threat) {
      return distance(target, threat.position) > threat.warning_radius;
    },
    permitsMove(from, to, commit = false) {
      return hostiles(bot).every(({ entity, radius }) => {
        const before = distance(from, entity.position), after = distance(to, entity.position);
        if (Math.min(before, after) > radius) return true;
        const key = entity.id ?? entity;
        const drift = Math.max(0, (commit ? inwardDrift.get(key) || 0 : 0) + before - after);
        if (commit) inwardDrift.set(key, drift);
        return drift <= POSITION_EPSILON;
      });
    },
  };
}

// Reuse only the already bounded discovery cells. Unknown air, partial support,
// fluids and destinations inside any warning radius never become candidates.
export function projectRetreatCandidates(bot, observedPositions, maximumDistance = 16) {
  const origin = bot.entity?.position;
  const threats = hostiles(bot);
  if (!origin || !threats.some(({ entity, radius }) => distance(origin, entity.position) <= radius)) return null;
  const candidates = new Map();
  for (const p of observedPositions) {
    const target = new Vec3(p.x, p.y + 1, p.z).floored();
    const center = target.offset(0.5, 0, 0.5);
    if (distance(origin, center) <= maximumDistance && safeDestination(bot, center, threats)) {
      candidates.set(target.toString(), { x: target.x, y: target.y, z: target.z });
    }
  }
  return { origin: { x: origin.x, y: origin.y, z: origin.z }, candidates: [...candidates.values()] };
}
