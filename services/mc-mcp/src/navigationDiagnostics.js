function positionSnapshot(position) {
  return Object.fromEntries(['x', 'y', 'z'].filter(axis => Number.isFinite(position?.[axis]))
    .map(axis => [axis, position[axis]]));
}

function retainRecent(history, entry) {
  history.push(entry);
  if (history.length > 8) history.shift();
}

function nodeSnapshot(node) {
  if (!node) return null;
  return {
    ...positionSnapshot(node),
    to_break: node.toBreak?.length ?? 0,
    ...(node.toBreak ? { break_targets: node.toBreak.map(positionSnapshot) } : {}),
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
  const client = typeof bot._client?.on === 'function' && typeof bot._client?.off === 'function' ? bot._client : null;
  const completedSegments = [];
  let path = [];
  let state;
  const begin = goal => {
    if (state?.goal.type) retainRecent(completedSegments, { goal: state.goal,
      elapsed_ms: Date.now() - state.started_at_ms, updates: state.updates, resets: state.resets,
      last_motion: state.last_motion, block_update_count: state.block_update_count,
      server_block_update_count: state.server_block_update_count });
    path = [];
    state = { goal: { type: goal?.constructor?.name, ...nodeSnapshot(goal) }, started_at_ms: Date.now(),
      updates: 0, resets: 0, first_update: null, latest_update: null, last_reset: null, last_motion: null,
      last_dig: null, last_stuck: null, block_update_count: 0, server_block_update_count: 0, block_updates: [], server_block_updates: [] };
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
    if (state.last_reset.reason === 'stuck') {
      // Native resetPath clears controls after this event; settlement ticks
      // must not replace the motion and terrain that caused the replan.
      state.last_stuck = { motion: motionSnapshot(), local_blocks: localBlockSnapshot(bot) };
    }
    path = [];
  };
  const activity = name => {
    try { return bot.pathfinder?.[name]?.() ?? null; } catch { return null; }
  };
  const motionSnapshot = () => {
    const digBlock = bot.targetDigBlock;
    return { position: nodeSnapshot(bot.entity?.position), velocity: nodeSnapshot(bot.entity?.velocity),
      on_ground: bot.entity?.onGround ?? null, next_node: nodeSnapshot(path[0]),
      elapsed_ms: Date.now() - state.started_at_ms, mining: activity('isMining'), building: activity('isBuilding'),
      target_dig_block: digBlock ? { name: digBlock.name ?? null, state_id: digBlock.stateId ?? null,
        position: positionSnapshot(digBlock.position) } : null, held_item: bot.heldItem?.name ?? null,
      controls: Object.fromEntries(['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak']
        .map(name => [name, bot.controlState?.[name]]).filter(([, value]) => typeof value === 'boolean')) };
  };
  const onTick = () => {
    state.last_motion = motionSnapshot();
    if (state.last_motion.mining || state.last_motion.target_dig_block) state.last_dig = state.last_motion;
  };
  const onBlockUpdate = (before, after) => {
    state.block_update_count++;
    retainRecent(state.block_updates, { position: positionSnapshot(after?.position ?? before?.position),
      before_state_id: before?.stateId ?? null, after_state_id: after?.stateId ?? null,
      elapsed_ms: Date.now() - state.started_at_ms });
  };
  const onServerBlockUpdate = packet => {
    if (!['x', 'y', 'z'].every(axis => Number.isFinite(packet?.location?.[axis])) || !Number.isInteger(packet.type)) return;
    state.server_block_update_count++;
    retainRecent(state.server_block_updates, { position: positionSnapshot(packet.location), state_id: packet.type,
      elapsed_ms: Date.now() - state.started_at_ms });
  };
  begin(null);
  bot.on('path_update', onUpdate);
  bot.on('path_reset', onReset);
  bot.on('physicsTick', onTick);
  bot.on('blockUpdate', onBlockUpdate);
  client?.on('block_change', onServerBlockUpdate);
  return { begin, snapshot: () => ({ ...state, completed_segments: [...completedSegments], local_blocks: localBlockSnapshot(bot) }), close() {
    bot.off('path_update', onUpdate);
    bot.off('path_reset', onReset);
    bot.off('physicsTick', onTick);
    bot.off('blockUpdate', onBlockUpdate);
    client?.off('block_change', onServerBlockUpdate);
  } };
}
