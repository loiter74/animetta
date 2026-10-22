import pathfinderPkg from 'mineflayer-pathfinder';
import Vec3 from 'vec3';
import { configureDryNavigation, isAirLikeForStanding, isSafeStandingPosition, isWaterBlock } from './collection.js';
import { operationWait } from './runtime/operationScope.js';

const { GoalBlock, GoalY } = pathfinderPkg.goals;
const ASCENT_STEP = 4;
export const AIR_RECOVERY_MS = 8000;

export function surfaceEscapePlan(bot, destination) {
  const feet = bot.entity?.position?.floored?.();
  if (!feet || typeof bot.blockAt !== 'function' || !isWaterBlock(bot.blockAt(feet.offset(0, 1, 0)))) return null;
  const values = ['x', 'y', 'z'].map(axis => Math.floor(destination[axis]));
  if (!values.every(Number.isFinite)) return null;
  const target = new Vec3(...values);
  if (target.y <= feet.y || feet.distanceTo(target) > 64 || !isSafeStandingPosition(bot, target)) return null;
  for (let height = 1; height <= 16; height++) {
    const head = feet.offset(0, height, 0);
    const block = bot.blockAt(head);
    if (isAirLikeForStanding(block) && isAirLikeForStanding(bot.blockAt(head.offset(0, 1, 0)))) {
      return { target, air_y: head.y };
    }
    if (!isWaterBlock(block)) return null;
  }
  return null;
}

export async function escapeWaterToShore(bot, plan, context, { wait = operationWait, now = Date.now } = {}) {
  context.operation_scope?.checkpoint();
  context.signal?.throwIfAborted();
  const previous = bot.pathfinder.movements;
  const deadline = now() + AIR_RECOVERY_MS;
  bot.pathfinder.setGoal(null);
  try {
    bot.setControlState('jump', true);
    while (isWaterBlock(bot.blockAt(bot.entity.position.floored().offset(0, 1, 0)))) {
      context.operation_scope?.checkpoint();
      context.signal?.throwIfAborted();
      if (now() >= deadline) throw Object.assign(new Error('有限上浮未能到达已知空气层。'), { code: 'SURFACE_ESCAPE_TIMEOUT' });
      if (bot.entity.position.floored().y + 1 >= plan.air_y) {
        throw Object.assign(new Error('原先确认的空气层已被水覆盖。'), { code: 'SURFACE_ESCAPE_BLOCKED' });
      }
      await wait(100);
    }
    if (!isAirLikeForStanding(bot.blockAt(bot.entity.position.floored().offset(0, 1, 0)))) {
      throw Object.assign(new Error('上浮路线没有保持已知空气层。'), { code: 'SURFACE_ESCAPE_BLOCKED' });
    }
    const movements = configureDryNavigation(new pathfinderPkg.Movements(bot), bot, { allowSurfaceSwimming: true });
    movements.canDig = false;
    movements.allow1by1towers = false;
    bot.pathfinder.setMovements(movements);
    try {
      await bot.pathfinder.goto(new GoalBlock(plan.target.x, plan.target.y, plan.target.z));
    } catch (error) {
      error.details = { ...error.details, recovery_phase: 'shore_navigation',
        recovery_position: { ...bot.entity.position }, air_y: plan.air_y };
      throw error;
    }
    const feet = bot.entity.position.floored();
    if (!isSafeStandingPosition(bot, feet)) {
      throw Object.assign(new Error('上浮恢复没有到达有支撑且可以呼吸的站位。'), { code: 'SURFACE_ESCAPE_UNCONFIRMED' });
    }
  } finally {
    bot.pathfinder.setGoal(null);
    bot.setControlState('jump', false);
    bot.pathfinder.setMovements(previous);
  }
}

export async function navigateTo(bot, destination, context = {}) {
  const target = Object.fromEntries(['x', 'y', 'z'].map(axis => [axis, Math.floor(destination[axis])]));
  if (!Object.values(target).every(Number.isFinite)) throw new TypeError('导航坐标必须是有限数值。');
  const escape = surfaceEscapePlan(bot, target);
  if (escape) return escapeWaterToShore(bot, escape, context);
  const startY = Math.floor(bot.entity.position.y);
  const segments = Math.ceil(Math.max(0, target.y - startY) / ASCENT_STEP);
  if (segments > 128) throw Object.assign(new Error('上升范围超过有限导航边界。'), { code: 'NAVIGATION_RANGE_TOO_LARGE' });
  const ascending = segments > 1;
  const extendedPlanning = ascending || bot.entity.position.distanceTo(new Vec3(target.x, target.y, target.z)) > 16;
  const originalThinkTimeout = bot.pathfinder.thinkTimeout;
  const movements = bot.pathfinder.movements;
  const originalTowers = movements?.allow1by1towers;
  if (extendedPlanning) bot.pathfinder.thinkTimeout = Math.max(15_000, originalThinkTimeout || 0);
  if (ascending && movements) movements.allow1by1towers = false;
  try {
    // A nearby height goal lets the native planner excavate a stair;
    // solving the full three-dimensional surface destination can exhaust A* first.
    for (let index = 0; index < segments - 1; index++) {
      context.operation_scope?.checkpoint();
      context.signal?.throwIfAborted();
      const nextY = Math.min(target.y, Math.floor(bot.entity.position.y) + ASCENT_STEP);
      const goal = new GoalY(nextY);
      await bot.pathfinder.goto(goal);
      if (!goal.isEnd(bot.entity.position.floored())) {
        throw Object.assign(new Error('上升导航没有到达已请求的高度。'), { code: 'NAVIGATION_ASCENT_STALLED' });
      }
    }
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
    try {
      await bot.pathfinder.goto(new GoalBlock(target.x, target.y, target.z));
    } catch (error) {
      const feet = bot.entity.position.floored();
      error.details = { ...error.details, recovery_phase: 'ordinary_navigation',
        recovery_position: { ...bot.entity.position },
        feet_block: bot.blockAt?.(feet)?.name ?? null,
        head_block: bot.blockAt?.(feet.offset(0, 1, 0))?.name ?? null };
      throw error;
    }
  } finally {
    if (extendedPlanning) {
      if (originalThinkTimeout === undefined) delete bot.pathfinder.thinkTimeout;
      else bot.pathfinder.thinkTimeout = originalThinkTimeout;
    }
    if (ascending) {
      if (movements) {
        if (originalTowers === undefined) delete movements.allow1by1towers;
        else movements.allow1by1towers = originalTowers;
      }
    }
  }
}
