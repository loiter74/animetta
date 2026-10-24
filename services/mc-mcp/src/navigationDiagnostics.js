function nodeSnapshot(node) {
  if (!node) return null;
  return {
    ...Object.fromEntries(['x', 'y', 'z'].filter(axis => Number.isFinite(node[axis])).map(axis => [axis, node[axis]])),
    to_break: node.toBreak?.length ?? 0,
    to_place: node.toPlace?.length ?? 0,
    jump_place: Boolean(node.toPlace?.some(placement => placement.jump)),
  };
}

function localBlockSnapshot(bot) {
  const origin = bot.entity?.position?.floored?.();
  if (!origin || typeof bot.blockAt !== 'function') return [];
  const blocks = [];
  for (let dy = -1; dy <= 3; dy++) for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) {
    const position = origin.offset(dx, dy, dz);
    const block = bot.blockAt(position);
    blocks.push({ x: position.x, y: position.y, z: position.z,
      name: block?.name ?? null, state_id: block?.stateId ?? null });
  }
  return blocks;
}

export function createNavigationTrace(bot, enabled = false) {
  if (!enabled || typeof bot.on !== 'function' || typeof bot.off !== 'function') return null;
  let path = [];
  let state;
  const begin = goal => {
    path = [];
    state = { goal: { type: goal?.constructor?.name, ...nodeSnapshot(goal) },
      updates: 0, resets: 0, first_update: null, latest_update: null, last_reset: null, last_motion: null };
  };
  const onUpdate = result => {
    path = result?.path ?? [];
    const update = { status: result?.status ?? 'unknown', path_nodes: path.length,
      next_node: nodeSnapshot(path[0]), planning_ms: result?.time ?? null };
    state.updates++;
    state.first_update ??= update;
    state.latest_update = update;
  };
  const onReset = reason => {
    state.resets++;
    state.last_reset = { reason: String(reason).slice(0, 160), next_node: nodeSnapshot(path[0]) };
    path = [];
  };
  const onTick = () => {
    state.last_motion = { position: nodeSnapshot(bot.entity?.position), velocity: nodeSnapshot(bot.entity?.velocity),
      on_ground: bot.entity?.onGround ?? null, next_node: nodeSnapshot(path[0]),
      controls: Object.fromEntries(['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak']
        .map(name => [name, bot.controlState?.[name]]).filter(([, value]) => typeof value === 'boolean')) };
  };
  begin(null);
  bot.on('path_update', onUpdate);
  bot.on('path_reset', onReset);
  bot.on('physicsTick', onTick);
  return { begin, snapshot: () => ({ ...state, local_blocks: localBlockSnapshot(bot) }), close() {
    bot.off('path_update', onUpdate);
    bot.off('path_reset', onReset);
    bot.off('physicsTick', onTick);
  } };
}
