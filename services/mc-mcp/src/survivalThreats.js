import Vec3 from 'vec3';

export const HOSTILE_NAMES = new Set([
  'blaze', 'cave_spider', 'creeper', 'drowned', 'enderman', 'endermite', 'evoker',
  'ghast', 'guardian', 'hoglin', 'husk', 'magma_cube', 'phantom', 'piglin_brute',
  'pillager', 'ravager', 'shulker', 'silverfish', 'skeleton', 'slime', 'spider',
  'stray', 'vex', 'vindicator', 'warden', 'witch', 'wither_skeleton', 'zoglin',
  'zombie', 'zombie_villager', 'zombified_piglin',
]);

const RANGED_HOSTILES = new Set(['skeleton', 'stray', 'pillager', 'witch', 'blaze', 'ghast', 'shulker', 'guardian', 'evoker', 'drowned']);
const PHYSICAL_ATTACKERS = new Set(['zombie', 'skeleton', 'stray', 'pillager', 'husk', 'drowned', 'zombie_villager']);
const isFullCube = block => block?.shapes?.some(shape => (
  shape.length === 6 && shape.every((value, index) => value === (index < 3 ? 0 : 1))
));

function hasSolidCover(bot, origin, entity) {
  if (typeof bot.world?.raycast !== 'function' || typeof bot.blockAt !== 'function') return false;
  const heights = [Math.max(1.8, bot.entity?.height || 1.8), entity.height || 1.8];
  const bodies = [[origin, heights[0]], [entity.position, heights[1]]];
  const isBodyCell = position => bodies.some(([feet, height]) => (
    position.x === Math.floor(feet.x) && position.z === Math.floor(feet.z)
    && position.y >= Math.floor(feet.y) && position.y < Math.ceil(feet.y + height)
  ));
  const hits = [];
  try {
    for (const fraction of [0, 0.5, 1]) {
      const start = new Vec3(origin.x, origin.y + 0.01 + fraction * (heights[0] - 0.02), origin.z);
      const end = new Vec3(entity.position.x, entity.position.y + 0.01 + fraction * (heights[1] - 0.02), entity.position.z);
      const delta = end.minus(start);
      const distance = delta.norm();
      if (distance === 0) return false;
      const hit = bot.world.raycast(start, delta.scaled(1 / distance), distance);
      // Neither planned excavation nor a body-overlapping cell proves cover.
      if (!isFullCube(hit) || !hit.position || isBodyCell(hit.position)
        || !hit.intersect || hit.intersect.distanceTo(start) >= distance) return false;
      hits.push(hit.position);
    }
    const column = hits[0];
    if (hits.some(hit => hit.x !== column.x || hit.z !== column.z)) return false;
    // Separate hit blocks do not prove that the space between them is filled.
    for (let y = Math.min(...hits.map(hit => hit.y)); y <= Math.max(...hits.map(hit => hit.y)); y++) {
      if (!isFullCube(bot.blockAt(new Vec3(column.x, y, column.z)))) return false;
    }
    return true;
  } catch {
    return false; // Missing world data never proves protective cover.
  }
}

// Retain the resource locator's melee warning and R17's earlier ranged warning.
// Only a complete known solid column can hide ordinary physical attackers.
export function findHostileThreat(bot, origin = bot.entity?.position, radius = null) {
  if (!origin) return null;
  let nearest = null;
  for (const entity of Object.values(bot.entities || {})) {
    if (!entity || entity === bot.entity) continue;
    const name = String(entity.name || entity.type || '').replace(/^minecraft:/, '');
    if (!HOSTILE_NAMES.has(name) && entity.kind !== 'Hostile mobs') continue;
    const position = entity.position;
    if (!position || !['x', 'y', 'z'].every(axis => Number.isFinite(position[axis]))) continue;
    const distance = Math.hypot(position.x - origin.x, position.y - origin.y, position.z - origin.z);
    const warningRadius = radius ?? (RANGED_HOSTILES.has(name) ? 24 : 12);
    if (distance <= warningRadius && (!nearest || distance < nearest.distance)
      && (!PHYSICAL_ATTACKERS.has(name) || !hasSolidCover(bot, origin, entity))) {
      nearest = { entity_id: String(entity.id), entity_type: name, distance,
        position: { x: position.x, y: position.y, z: position.z }, warning_radius: warningRadius };
    }
  }
  return nearest;
}
