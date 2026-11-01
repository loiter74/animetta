import { findPickupItemEntities } from '../collection.js';

const finitePosition = position => position && ['x', 'y', 'z'].every(axis => Number.isFinite(position[axis]));
const point = position => finitePosition(position)
  ? { x: position.x, y: position.y, z: position.z } : null;

function entityBox(entity, registry, name = entity?.name) {
  const definition = registry?.entitiesByName?.[name];
  const width = Number(entity?.width ?? definition?.width);
  const height = Number(entity?.height ?? definition?.height);
  if (!finitePosition(entity?.position) || !(width > 0) || !(height > 0)
    || !Number.isFinite(width) || !Number.isFinite(height)) return null;
  return {
    min: { x: entity.position.x - width / 2, y: entity.position.y, z: entity.position.z - width / 2 },
    max: { x: entity.position.x + width / 2, y: entity.position.y + height, z: entity.position.z + width / 2 },
  };
}

function pickupArea(bot) {
  const player = entityBox(bot.entity, bot.registry, 'player');
  if (!player) return null;
  let vertical = 0.5;
  if (bot.vehicle) {
    const vehicle = entityBox(bot.vehicle, bot.registry);
    if (!vehicle) return null;
    for (const axis of ['x', 'y', 'z']) {
      player.min[axis] = Math.min(player.min[axis], vehicle.min[axis]);
      player.max[axis] = Math.max(player.max[axis], vehicle.max[axis]);
    }
    vertical = 0;
  }
  // Java 1.21 Player.aiStep: inflate(1, .5, 1); riding uses the union and (1, 0, 1).
  for (const axis of ['x', 'y', 'z']) {
    const expansion = axis === 'y' ? vertical : 1;
    player.min[axis] -= expansion;
    player.max[axis] += expansion;
  }
  return player;
}

export function projectItemPickupState(bot) {
  const area = pickupArea(bot);
  let pending = 0;
  const evidence = [];
  for (const { entity, distance } of findPickupItemEntities(bot, Infinity)) {
    const box = entityBox(entity, bot.registry);
    const overlaps = area && box && ['x', 'y', 'z'].every(axis =>
      box.max[axis] > area.min[axis] && box.min[axis] < area.max[axis]);
    if (!overlaps && distance > 2) continue;
    const outsideHorizontal = area && box && ['x', 'z'].some(axis =>
      box.max[axis] <= area.min[axis] || box.min[axis] >= area.max[axis]);
    const resting = entity.onGround === true && finitePosition(entity.velocity)
      && ['x', 'z'].every(axis => Math.abs(entity.velocity[axis]) <= 0.0001)
      && (outsideHorizontal || Math.abs(entity.velocity.y) <= 0.0001);
    // Unknown bounds/motion stay conservative. A resting item outside contact
    // needs another movement/action; it cannot be treated as a pending transfer.
    const reason = overlaps ? 'pickup_overlap'
      : area && box && resting ? 'outside_pickup_area' : 'nearby_item_unsettled';
    if (reason !== 'outside_pickup_area') pending++;
    if (evidence.length < 8) {
      let name = null;
      try { name = entity.getDroppedItem?.()?.name ?? null; } catch {}
      evidence.push({
        entity_id: entity.id ?? null, item_name: name, position: point(entity.position),
        velocity: point(entity.velocity), on_ground: entity.onGround ?? null,
        distance, reason,
      });
    }
  }
  return { pending, evidence };
}
