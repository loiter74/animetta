export function blockMutation(blockType, position, dimension = 'minecraft:overworld', delta = -1) {
  const resourceId = value => String(value).includes(':') ? String(value) : `minecraft:${value}`;
  return {
    kind: 'block',
    subject: `block:${resourceId(dimension)}:${position.x}:${position.y}:${position.z}`,
    delta,
    details: { block_type: resourceId(blockType) },
  };
}

// Match occurrences rather than positions: a block may be placed and dug more
// than once during one action. Explicit fluid/portal changes have no SDK event.
function mergeMutations(native, annotations) {
  const unmatched = [...native];
  return [...native, ...annotations.filter(mutation => {
    const index = unmatched.findIndex(event => event.kind === mutation.kind
      && event.subject === mutation.subject && event.delta === mutation.delta
      && event.details.block_type === mutation.details?.block_type);
    if (index < 0) return true;
    unmatched.splice(index, 1);
    return false;
  })];
}

export async function withActionEvidence(bot, invoke, { normalizeResult } = {}) {
  const annotations = [];
  const native = [];
  const removed = new Map();
  const key = block => `${block.position.x},${block.position.y},${block.position.z}`;
  const mutation = (block, delta) => blockMutation(
    block.name, block.position, bot.game?.dimension || 'minecraft:overworld', delta,
  );
  const onBlockUpdate = (before, after) => {
    if (before?.position && before.type !== 0 && after?.type === 0) removed.set(key(before), before);
  };
  const onDiggingCompleted = after => {
    if (!after?.position) return;
    const block = removed.get(key(after));
    if (!block) return;
    removed.delete(key(after));
    native.push(mutation(block, -1));
  };
  const onBlockPlaced = (before, after) => {
    if (after?.position && after.type !== 0 && before?.type !== after.type) native.push(mutation(after, 1));
  };
  let previousPosition = { ...bot.entity.position };
  let previousHealth = bot.health;
  let travel = 0;
  let damage = 0;
  const onMove = () => {
    const current = bot.entity.position;
    travel += Math.hypot(current.x - previousPosition.x,
      current.y - previousPosition.y, current.z - previousPosition.z);
    previousPosition = { ...current };
  };
  const onHealth = () => {
    damage += Math.max(0, previousHealth - bot.health);
    previousHealth = bot.health;
  };
  const evidence = (declared = {}) => {
    onMove();
    onHealth();
    const mutations = mergeMutations(native, [...annotations, ...(declared.explained_mutations || [])]);
    const usage = declared.budget_usage || {};
    return {
      explained_mutations: mutations,
      budget_usage: {
        ...usage,
        max_actions: Math.max(1, usage.max_actions || 0),
        max_travel_distance: Math.max(travel, usage.max_travel_distance || 0),
        max_blocks_changed: Math.max(mutations.filter(change => change.kind === 'block').length,
          usage.max_blocks_changed || 0),
        max_damage_taken: Math.max(damage, usage.max_damage_taken || 0),
      },
    };
  };
  const listeners = { move: onMove, health: onHealth, blockUpdate: onBlockUpdate,
    diggingCompleted: onDiggingCompleted, blockPlaced: onBlockPlaced };
  for (const [event, listener] of Object.entries(listeners)) bot.on(event, listener);
  try {
    const value = await invoke(annotations);
    const result = normalizeResult ? normalizeResult(value) : { output: value };
    return { ...result, ...evidence(result) };
  } catch (error) {
    let failure = error instanceof Error ? error : new Error(String(error), { cause: error });
    let declared = failure;
    try {
      if (normalizeResult) declared = normalizeResult(failure);
    } catch (invalidEvidence) {
      failure = invalidEvidence;
      declared = {};
    }
    Object.assign(failure, evidence(declared));
    throw failure;
  } finally {
    for (const [event, listener] of Object.entries(listeners)) bot.removeListener(event, listener);
  }
}
