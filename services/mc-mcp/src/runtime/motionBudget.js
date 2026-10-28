import { PlayerState } from 'prismarine-physics';

import { MOVEMENT_CONTROLS } from './operationScope.js';

// Admit a committed jump before takeoff, including its unavoidable landing.
// This is a read-only forecast, not a replacement for observed movement usage.
export function projectJumpTravel(bot, controls) {
  let unknownBlock = false;
  const world = { getBlock(position) {
    const block = bot.blockAt(position);
    if (!block) unknownBlock = true;
    return block;
  } };
  try {
    let state = new PlayerState(bot, controls);
    const stoppedControls = Object.fromEntries(MOVEMENT_CONTROLS.map(name => [name, false]));
    let distance = 0;
    for (let tick = 0; tick < 64; tick++) {
      const before = state.pos.clone();
      state = bot.physics.simulatePlayer(state, world);
      if (unknownBlock || !['x', 'y', 'z'].every(axis => (
        Number.isFinite(state.pos[axis]) && Number.isFinite(state.vel[axis])
      ))) return null;
      distance += state.pos.distanceTo(before);
      state.control = stoppedControls;
      state.jumpQueued = false;
      if (state.onGround && state.vel.x === 0 && state.vel.z === 0 && state.vel.y <= 0) return distance;
    }
  } catch {
    // Missing terrain or unsupported physics cannot prove an affordable landing.
  }
  return null;
}
