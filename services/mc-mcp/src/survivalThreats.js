export const HOSTILE_NAMES = new Set([
  'blaze', 'cave_spider', 'creeper', 'drowned', 'enderman', 'endermite', 'evoker',
  'ghast', 'guardian', 'hoglin', 'husk', 'magma_cube', 'phantom', 'piglin_brute',
  'pillager', 'ravager', 'shulker', 'silverfish', 'skeleton', 'slime', 'spider',
  'stray', 'vex', 'vindicator', 'warden', 'witch', 'wither_skeleton', 'zoglin',
  'zombie', 'zombie_villager', 'zombified_piglin',
]);

// Warn before R17's observed projectile danger. This conservative proximity
// check does not prove cover or provide an escape plan; budgets stay unchanged.
export function findHostileThreat(bot, origin = bot.entity?.position, radius = 24) {
  if (!origin) return null;
  let nearest = null;
  for (const entity of Object.values(bot.entities || {})) {
    if (!entity || entity === bot.entity) continue;
    const name = String(entity.name || entity.type || '').replace(/^minecraft:/, '');
    if (!HOSTILE_NAMES.has(name) && entity.kind !== 'Hostile mobs') continue;
    const position = entity.position;
    if (!position || !['x', 'y', 'z'].every(axis => Number.isFinite(position[axis]))) continue;
    const distance = Math.hypot(position.x - origin.x, position.y - origin.y, position.z - origin.z);
    if (distance <= radius && (!nearest || distance < nearest.distance)) {
      nearest = { entity_id: String(entity.id), entity_type: name, distance,
        position: { x: position.x, y: position.y, z: position.z }, warning_radius: radius };
    }
  }
  return nearest;
}
