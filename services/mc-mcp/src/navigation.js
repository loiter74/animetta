import pathfinderPkg from 'mineflayer-pathfinder';
import AStar from 'mineflayer-pathfinder/lib/astar.js';
import Vec3 from 'vec3';
import { configureDryNavigation, isAirLikeForStanding, isSafeStandingPosition, isWaterBlock } from './collection.js';
import { operationWait } from './runtime/operationScope.js';
import { createNavigationTrace } from './navigationDiagnostics.js';

const { GoalBlock, GoalY } = pathfinderPkg.goals;
const VERTICAL_STEP = 4;
export const AIR_RECOVERY_MS = 8000;
const GEOMETRY_VIEW = Symbol.for('animetta.pathfinder.geometryView');

export function isolatePathfinderGeometry() {
  const original = AStar.prototype.makeResult;
  if (original?.[GEOMETRY_VIEW]) return;
  if (typeof original !== 'function') throw new TypeError('已安装的寻路器缺少结果几何扩展点。');
  const isolated = function (...args) {
    const result = original.apply(this, args);
    // SDK centering changes coordinates in place. Its consumed work queues
    // remain shared so later slices do not repeat completed digs or placements.
    // reconstructPath omits the root, so recover the start move from the node
    // chain to give the first path move a predecessor for corner completion.
    let root = args[1];
    while (root?.parent) root = root.parent;
    const startMove = root?.data ?? null;
    const path = result.path.map((move, index) => {
      const clone = Object.assign(Object.create(Object.getPrototypeOf(move)), move);
      completeDiagonalAscentCorners(this, index > 0 ? result.path[index - 1] : startMove, clone);
      return clone;
    });
    return { ...result, path };
  };
  Object.defineProperty(isolated, GEOMETRY_VIEW, { value: true });
  AStar.prototype.makeResult = isolated;
}

// mineflayer-pathfinder validates only the cheaper orthogonal column when it
// emits a diagonal jump-up move (getMoveDiagonal keeps one of two approach
// columns and leaves the other untouched). The native executor beelines
// toward the landing point and cannot slide around a solid corner column, so
// such a move stalls in a stuck/reset loop until the segment deadline kills
// the action (first observed as the r110 water-return ascent failure). Mirror
// the losing column's dig targets so the native dig pipeline clears the
// corner before the beeline; flat diagonals, already planned digs and
// dig-forbidden movement sets keep their existing behavior.
function completeDiagonalAscentCorners(astar, previous, move) {
  const movements = astar.movements;
  const bot = movements?.bot;
  if (!previous || !bot || movements.canDig === false) return;
  if (!Array.isArray(move.toBreak) || move.toBreak.length > 0) return;
  const dx = move.x - previous.x;
  const dz = move.z - previous.z;
  if (move.y - previous.y !== 1 || Math.abs(dx) !== 1 || Math.abs(dz) !== 1) return;
  const corners = [];
  for (const [x, z] of [[previous.x + dx, previous.z], [previous.x, previous.z + dz]]) {
    for (const dy of [1, 2]) {
      const position = new Vec3(x, previous.y + dy, z);
      if (bot.blockAt(position)?.boundingBox === 'block') corners.push(position);
    }
  }
  if (corners.length > 0) move.toBreak = corners;
}

export function* iteratePathSearch(bot, movements, goal) {
  isolatePathfinderGeometry();
  const timeout = bot.pathfinder.thinkTimeout;
  const deadline = Number.isFinite(timeout) && timeout >= 0 ? Date.now() + timeout : null;
  // Keep discrete coordinates for callers. The SDK's slice check precedes its
  // total-time check, so enforce the same existing total limit here too.
  for (const planned of bot.pathfinder.getPathFromTo(movements, bot.entity.position, goal, { optimizePath: false })) {
    if (planned.result.status === 'partial' && deadline !== null && Date.now() >= deadline) {
      yield { ...planned, result: { ...planned.result, status: 'timeout' } };
      return;
    }
    yield planned;
    if (planned.result.status !== 'partial') return;
  }
}

function navigateGoal(bot, goal, context) {
  const navigate = () => bot.pathfinder.goto(goal);
  return context.operation_scope ? context.operation_scope.navigate(goal, navigate) : navigate();
}

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
      await navigateGoal(bot, new GoalBlock(plan.target.x, plan.target.y, plan.target.z), context);
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
  isolatePathfinderGeometry();
  const escape = surfaceEscapePlan(bot, target);
  if (escape) return escapeWaterToShore(bot, escape, context);
  const startY = Math.floor(bot.entity.position.y);
  const segments = Math.ceil(Math.abs(target.y - startY) / VERTICAL_STEP);
  if (segments > 128) throw Object.assign(new Error('垂直范围超过有限导航边界。'), { code: 'NAVIGATION_RANGE_TOO_LARGE' });
  const ascending = target.y > startY;
  const extendedPlanning = (ascending && segments > 1) || bot.entity.position.distanceTo(new Vec3(target.x, target.y, target.z)) > 16;
  const originalThinkTimeout = bot.pathfinder.thinkTimeout;
  const movements = bot.pathfinder.movements;
  const originalTowers = movements?.allow1by1towers;
  if (extendedPlanning) bot.pathfinder.thinkTimeout = Math.max(15_000, originalThinkTimeout || 0);
  if (ascending && movements) movements.allow1by1towers = false;
  if (context.retreat_policy) {
    bot.pathfinder.setMovements(configureDryNavigation(new pathfinderPkg.Movements(bot), bot, {
      retreatPolicy: context.retreat_policy,
    }));
  }
  const trace = createNavigationTrace(bot, Boolean(process.env.COLLECT_DEBUG));
  try {
    // A nearby height goal lets the native planner excavate a stair;
    // solving the full three-dimensional surface destination can exhaust A* first.
    for (let index = 0; index < segments - 1; index++) {
      context.operation_scope?.checkpoint();
      context.signal?.throwIfAborted();
      const currentY = Math.floor(bot.entity.position.y);
      const nextY = ascending ? Math.min(target.y, currentY + VERTICAL_STEP)
        : Math.max(target.y, currentY - VERTICAL_STEP);
      const goal = new GoalY(nextY);
      trace?.begin(goal);
      await navigateGoal(bot, goal, context);
      if (!goal.isEnd(bot.entity.position.floored())) {
        throw Object.assign(new Error('垂直导航没有到达已请求的高度。'), {
          code: ascending ? 'NAVIGATION_ASCENT_STALLED' : 'NAVIGATION_DESCENT_STALLED',
        });
      }
    }
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
    try {
      const goal = new GoalBlock(target.x, target.y, target.z);
      trace?.begin(goal);
      await navigateGoal(bot, goal, context);
    } catch (error) {
      const feet = bot.entity.position.floored();
      error.details = { ...error.details, recovery_phase: 'ordinary_navigation',
        recovery_position: { ...bot.entity.position },
        feet_block: bot.blockAt?.(feet)?.name ?? null,
        head_block: bot.blockAt?.(feet.offset(0, 1, 0))?.name ?? null };
      throw error;
    }
  } catch (error) {
    if (!error.code && !error.operationSettlement && !context.signal?.aborted) {
      if (error.name === 'Timeout') error.code = 'SEARCH_TIMEOUT';
      else if (error.name === 'NoPath') error.code = 'NAVIGATION_TARGET_NOT_REACHED';
    }
    if (trace) error.details = { ...error.details, navigation_trace: trace.snapshot() };
    throw error;
  } finally {
    trace?.close();
    if (context.retreat_policy) bot.pathfinder.setMovements(movements);
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
