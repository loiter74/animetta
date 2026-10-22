// Mineflayer's shared oxygenLevel can be overwritten by another entity's
// metadata packet. Only the controlled player's own air supply is authoritative.
export function ownOxygenLevel(bot) {
  const entity = bot?.entity;
  const metadataKeys = bot?.registry?.entitiesByName?.[entity?.name]?.metadataKeys;
  const airIndex = metadataKeys?.indexOf('air_supply') ?? -1;
  const airSupply = airIndex >= 0 ? entity?.metadata?.[airIndex] : undefined;
  return Number.isFinite(airSupply) ? Math.max(0, Math.round(airSupply / 15)) : null;
}
