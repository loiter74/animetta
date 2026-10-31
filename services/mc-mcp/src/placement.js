export function normalizePlacementBlockName(blockType) {
  return String(blockType).replace(/^minecraft:/, '');
}

export async function placeBlockAt(bot, { blockName, targetPosition, facing, context = {} }, { navigate, dig, wait }) {
  const checkpoint = () => {
    context.operation_scope?.checkpoint();
    context.signal?.throwIfAborted();
  };
  const failure = (code, message) => Object.assign(new Error(message), { code });
  const placementChanges = blockName.endsWith('_door') || blockName.endsWith('_bed') ? 2 : 1;
  const inspectTarget = () => {
    checkpoint();
    const block = bot.blockAt(targetPosition);
    if (!block) throw failure('REGION_NOT_LOADED', '放置目标尚未加载。');
    if (block.name === blockName) return block;
    if (!['air', 'water', 'lava', 'snow', 'short_grass', 'fern', 'dead_bush'].includes(block.name)) {
      throw failure('TARGET_OCCUPIED', `放置目标被 ${block.name} 占用。`);
    }
    const required = placementChanges + Number(block.name === 'snow');
    if ((context.budget?.max_blocks_changed ?? placementChanges) < required) {
      throw failure('BUDGET_EXHAUSTED', '本次预约不足以覆盖清雪与放置，已停止。');
    }
    return block;
  };
  const result = placed => ({ placed, output: placed
    ? `Placed ${blockName} at (${targetPosition.x}, ${targetPosition.y}, ${targetPosition.z})`
    : `Block already present at (${targetPosition.x}, ${targetPosition.y}, ${targetPosition.z})` });
  let current = inspectTarget();
  if (current.name === blockName) return result(false);
  if (!bot.inventory.items().some(item => item.name === blockName && item.count > 0)) {
    throw failure('MISSING_MATERIAL', `背包中没有 ${blockName}。`);
  }
  // Approach cannot spend a placement reservation on excavation or scaffolds.
  const movements = bot.pathfinder?.movements;
  const keys = ['canDig', 'allow1by1towers', 'scafoldingBlocks', 'canOpenDoors'];
  const previous = movements && keys.map(key => [key, Object.hasOwn(movements, key), movements[key]]);
  if (movements) Object.assign(movements, { canDig: false, allow1by1towers: false, scafoldingBlocks: [], canOpenDoors: false });
  try {
    await navigate();
  } finally {
    try { bot.pathfinder?.setGoal?.(null); } catch {}
    try { bot.pathfinder?.stop?.(); } catch {}
    if (movements) for (const [key, present, value] of previous) {
      if (present) movements[key] = value;
      else delete movements[key];
    }
  }
  current = inspectTarget();
  if (current.name === blockName) return result(false);
  if (current.name === 'snow') {
    await dig(current);
    checkpoint();
    if (bot.blockAt(targetPosition)?.name !== 'air') {
      throw failure('PLACEMENT_CLEARANCE_FAILED', '清雪后未确认目标为空气，已停止放置。');
    }
  }
  const placement = findPlacementReference(bot, targetPosition, targetPosition.constructor);
  if (!placement) throw failure('PLACEMENT_REFERENCE_MISSING', '目标旁没有可用的放置支撑。');
  const item = bot.inventory.items().find(stack => stack.name === blockName && stack.count > 0);
  if (!item) throw failure('MISSING_MATERIAL', `背包中没有 ${blockName}。`);
  await bot.equip(item, 'hand');
  if (bot.heldItem?.name !== blockName) {
    throw failure('PLACEMENT_ITEM_CHANGED', '装备物品与预期放置材料不一致，已停止。');
  }
  if (typeof bot.lookAt === 'function') await bot.lookAt(targetPosition.offset(0.5, 0.5, 0.5), true);
  checkpoint();
  if (bot.heldItem?.name !== blockName) {
    throw failure('PLACEMENT_ITEM_CHANGED', '瞄准后装备材料已变化，已停止放置。');
  }
  await placeOrientedBlock(bot, placement, blockName, facing);
  await wait(250);
  if (bot.blockAt(targetPosition)?.name !== blockName) {
    throw failure('PLACEMENT_NOT_OBSERVED', '未观测到预期方块，已停止。');
  }
  return result(true);
}

const PLACEMENT_YAW = Object.freeze({
  // Beds extend from the foot in the placing player's horizontal look direction.
  // Mineflayer uses 0 for north and rotates clockwise toward west.
  north: 0,
  south: Math.PI,
  east: -Math.PI / 2,
  west: Math.PI / 2,
});

export async function orientForPlacement(bot, blockName, facing = 'north') {
  if (!String(blockName).endsWith('_bed')) return;
  const yaw = PLACEMENT_YAW[facing];
  if (yaw === undefined) throw new Error(`Unsupported placement facing: ${facing}`);
  await bot.look(yaw, 0);
}

export async function placeOrientedBlock(bot, placement, blockName, facing = 'north') {
  await orientForPlacement(bot, blockName, facing);
  if (!String(blockName).endsWith('_bed')) {
    return bot.placeBlock(placement.reference, placement.face);
  }
  if (typeof bot._placeBlockWithOptions !== 'function') {
    throw new Error('Mineflayer oriented placement API is unavailable');
  }
  // The public placeBlock method looks at the clicked face immediately before
  // sending the packet, which overwrites the yaw that controls bed direction.
  return bot._placeBlockWithOptions(placement.reference, placement.face, {
    forceLook: 'ignore',
    swingArm: 'right',
  });
}

export function isFullCubeReference(reference) {
  return Array.isArray(reference?.shapes) && reference.shapes.some(shape => (
    Array.isArray(shape)
    && shape.length === 6
    && shape[0] === 0
    && shape[1] === 0
    && shape[2] === 0
    && shape[3] === 1
    && shape[4] === 1
    && shape[5] === 1
  ));
}

export function findPlacementReference(bot, targetPosition, VectorClass) {
  const faces = [
    [0, 1, 0],
    [1, 0, 0],
    [-1, 0, 0],
    [0, 0, 1],
    [0, 0, -1],
    [0, -1, 0],
  ];
  const candidates = [];
  for (const [x, y, z] of faces) {
    const referencePosition = targetPosition.offset(-x, -y, -z);
    const reference = bot.blockAt(referencePosition);
    if (!reference || ['air', 'water', 'lava'].includes(reference.name)) continue;
    candidates.push({ reference, face: new VectorClass(x, y, z) });
  }
  return candidates.find(candidate => isFullCubeReference(candidate.reference))
    || candidates[0]
    || null;
}

export function placementMutation(
  blockType,
  position,
  dimension = 'minecraft:overworld',
) {
  const normalizedBlock = String(blockType).includes(':')
    ? String(blockType)
    : `minecraft:${blockType}`;
  const normalizedDimension = String(dimension).includes(':')
    ? String(dimension)
    : `minecraft:${dimension}`;
  return {
    kind: 'block',
    subject: `block:${normalizedDimension}:${position.x}:${position.y}:${position.z}`,
    delta: 1,
    details: { block_type: normalizedBlock },
  };
}

export function placementMutations(
  blockType,
  position,
  dimension = 'minecraft:overworld',
  observedSecondaryPositions = [],
) {
  const mutations = [placementMutation(blockType, position, dimension)];
  const normalizedBlock = normalizePlacementBlockName(blockType);
  if (normalizedBlock.endsWith('_door')) {
    mutations.push(placementMutation(
      blockType,
      position.offset(0, 1, 0),
      dimension,
    ));
  } else if (normalizedBlock.endsWith('_bed')) {
    mutations.push(...observedSecondaryPositions.map(secondary => (
      placementMutation(blockType, secondary, dimension)
    )));
  }
  return mutations;
}
