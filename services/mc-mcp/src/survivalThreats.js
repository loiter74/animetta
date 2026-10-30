import Vec3 from 'vec3';

export const HOSTILE_NAMES = new Set([
  'blaze', 'cave_spider', 'creeper', 'drowned', 'enderman', 'endermite', 'evoker',
  'ghast', 'guardian', 'hoglin', 'husk', 'magma_cube', 'phantom', 'piglin_brute',
  'pillager', 'polar_bear', 'ravager', 'shulker', 'silverfish', 'skeleton', 'slime', 'spider',
  'stray', 'vex', 'vindicator', 'warden', 'witch', 'wither_skeleton', 'zoglin',
  'zombie', 'zombie_villager', 'zombified_piglin',
]);

const RANGED_HOSTILES = new Set(['skeleton', 'stray', 'pillager', 'witch', 'blaze', 'ghast', 'shulker', 'guardian', 'evoker', 'drowned']);
const PHYSICAL_ATTACKERS = new Set(['zombie', 'skeleton', 'stray', 'pillager', 'husk', 'drowned', 'zombie_villager']);
// Only explicitly dormant, uncharged, unignited creepers may use the existing
// complete cover proof. A state change or lost cover keeps the warning.
const DORMANT_CREEPER_METADATA = [
  ['swell_dir', -1],
  ['is_powered', false],
  ['is_ignited', false],
];

function hasDormantCreeperMetadata(bot, entity) {
  const keys = bot.registry?.entitiesByName?.creeper?.metadataKeys;
  if (!Array.isArray(keys) || !Array.isArray(entity?.metadata)) return false;
  // Protocol 767 sends only non-default metadata at spawn. Its health update
  // proves initial metadata arrived; before that, absent flags remain unknown.
  const healthIndex = keys.indexOf('health');
  const health = healthIndex >= 0 ? entity.metadata[healthIndex] : null;
  const knownVanillaDefaults = bot.registry.version?.version === 767
    && Number.isFinite(health) && health > 0;
  // Every key must exist in the schema. Only omitted protocol defaults may
  // substitute for a slot; unknown or mistyped values retain the warning.
  return DORMANT_CREEPER_METADATA.every(([key, expected]) => {
    const index = keys.indexOf(key);
    return index >= 0 && (entity.metadata[index] === expected
      || (knownVanillaDefaults && !Object.hasOwn(entity.metadata, index)));
  });
}

const isFullCube = block => block?.shapes?.some(shape => (
  shape.length === 6 && shape.every((value, index) => value === (index < 3 ? 0 : 1))
));

function hasSeparatingCover(bot, origin, entity, heights) {
  const end = entity.position;
  const halfWidths = [bot.entity?.width, entity.width].map(width => Math.max(0.6, Number(width) || 0.6) / 2);
  if (![origin.x, origin.y, origin.z, end.x, end.y, end.z, ...heights, ...halfWidths].every(Number.isFinite)
    || heights.some(height => height <= 0)) return false;
  const boxes = [origin, end].map((feet, index) => [
    [feet.x - halfWidths[index], feet.x + halfWidths[index]],
    [feet.y, feet.y + heights[index]],
    [feet.z - halfWidths[index], feet.z + halfWidths[index]],
  ]);
  if (!boxes.flat(2).every(Number.isFinite)) return false;
  for (const axis of [0, 1, 2]) {
    const [from, to] = boxes[0][axis][1] <= boxes[1][axis][0] ? boxes : [boxes[1], boxes[0]];
    // A complete cube layer must fit between both entire bodies, including
    // the proposed excavation position. Overlapping bodies cannot prove cover.
    const transverse = [0, 1, 2].filter(index => index !== axis);
    for (let layer = Math.ceil(from[axis][1]); layer < Math.floor(to[axis][0]); layer++) {
      const bounds = transverse.map(() => [Infinity, -Infinity]);
      // Bound every body-to-body lane at both layer faces. The extrema occur
      // at body endpoints; all transverse endpoints are interpolated as well.
      for (const fromFace of from[axis]) for (const toFace of to[axis]) {
        for (const face of [layer, layer + 1]) {
          const t = (face - fromFace) / (toFace - fromFace);
          for (const [index, other] of transverse.entries()) {
            bounds[index][0] = Math.min(bounds[index][0], from[other][0] * (1 - t) + to[other][0] * t);
            bounds[index][1] = Math.max(bounds[index][1], from[other][1] * (1 - t) + to[other][1] * t);
          }
        }
      }
      let complete = true;
      for (let a = Math.floor(bounds[0][0]); a <= Math.floor(bounds[0][1]) && complete; a++) {
        for (let b = Math.floor(bounds[1][0]); b <= Math.floor(bounds[1][1]); b++) {
          const position = [0, 0, 0];
          position[axis] = layer;
          position[transverse[0]] = a;
          position[transverse[1]] = b;
          if (!isFullCube(bot.blockAt(new Vec3(...position)))) { complete = false; break; }
        }
      }
      if (complete) return true;
    }
  }
  return false;
}

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
    if (hasSeparatingCover(bot, origin, entity, heights)) return true;
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
// Only a complete known solid column or separating layer can hide physical
// attackers, plus creepers explicitly confirmed safe by their metadata.
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
    const mayProveCover = PHYSICAL_ATTACKERS.has(name)
      || (name === 'creeper' && hasDormantCreeperMetadata(bot, entity));
    if (distance <= warningRadius && (!nearest || distance < nearest.distance)
      && (!mayProveCover || !hasSolidCover(bot, origin, entity))) {
      nearest = { entity_id: String(entity.id), entity_type: name, distance,
        position: { x: position.x, y: position.y, z: position.z }, warning_radius: warningRadius };
    }
  }
  return nearest;
}
