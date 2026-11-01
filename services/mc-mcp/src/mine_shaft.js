import Vec3 from 'vec3';
import pathfinderPkg from 'mineflayer-pathfinder';
import { collectionDigSafety, configureDryNavigation } from './collection.js';
import { activeOperationScope, operationWait } from './runtime/operationScope.js';
import { ownOxygenLevel } from './runtime/playerVitals.js';
import { findHostileThreat } from './survivalThreats.js';

// mine_shaft.js — 系统下矿（垂直挖矿井，从 index.js 提取，中度重构）。
// 依赖注入：bot / disableAuto / enableAuto。
// 区别于 collect 随机探索：挖出阶梯并用第一人称移动控制走下去。

export function createMineShaft({
  bot,
  disableAuto,
  enableAuto,
  getSurvivalThreat = () => null,
  wait = operationWait,
}) {
  function debug(message) {
    if (process.env.MINE_SHAFT_DEBUG) {
      console.error(`[mine_shaft] ${message}`);
    }
  }

  function propagateInterruptedOperation(error) {
    if (error?.operationSettlement || error?.current_position_unsafe
      || error?.code === 'COLLECTION_SAFETY_PAUSED'
      || activeOperationScope()?.signal?.aborted) throw error;
  }

  async function withActionTimeout(operation, timeoutMs, label, onTimeout = () => {}) {
    const start = typeof operation === 'function' ? operation : () => operation;
    const scope = activeOperationScope();
    if (scope) {
      return scope.runInterruptible(
        start,
        { label, timeoutMs, includeContainers: false },
      );
    }
    let timer;
    try {
      return await Promise.race([
        Promise.resolve().then(start),
        new Promise((_, reject) => {
          timer = setTimeout(() => {
            try { onTimeout(); } catch {}
            const err = new Error(`${label} timed out after ${timeoutMs}ms`);
            err.code = 'MINE_SHAFT_ACTION_TIMEOUT';
            err.action = label;
            reject(err);
          }, timeoutMs);
        }),
      ]);
    } finally {
      clearTimeout(timer);
    }
  }

  async function withDigTimeout(block, timeoutMs = 8000) {
    return withActionTimeout(
      () => bot.dig(block),
      timeoutMs,
      `dig ${block.name}@${block.position.x},${block.position.y},${block.position.z}`,
      () => bot.stopDigging?.()
    );
  }

  function isSolid(block) {
    return block && block.boundingBox === 'block' && block.name !== 'bedrock';
  }

  function isStableSupport(block) {
    return isSolid(block) && !['sand', 'red_sand', 'gravel', 'suspicious_sand',
      'suspicious_gravel', 'anvil', 'chipped_anvil', 'damaged_anvil', 'dragon_egg'].includes(block.name)
      && !block.name?.endsWith('_concrete_powder');
  }

  function standingCell() {
    const position = bot.entity.position, cell = position.floored();
    // Match the SDK's grounded partial-block start offset. Mud and slabs
    // support the player inside their own cell, rather than the cell below it.
    return position.y - cell.y > 0.001 && bot.entity.onGround === true
      && isStableSupport(bot.blockAt(cell)) ? cell.offset(0, 1, 0) : cell;
  }

  function assertDryState() {
    activeOperationScope()?.checkpoint();
    const base = bot.entity?.position?.floored?.();
    if (!base) return;
    const feet = bot.blockAt(base);
    const head = bot.blockAt(base.offset(0, 1, 0));
    const oxygen = ownOxygenLevel(bot);
    if (!feet || !head || isFluidHazard(feet) || isFluidHazard(head)
      || (oxygen !== null && oxygen <= 14)) {
      const error = fluidHazard(head || feet || { name: 'unknown' });
      error.message = '矿井当前位置或空气不足以安全继续，已停止下降。';
      error.current_position_unsafe = true;
      error.details = { oxygen_level: oxygen,
        feet: feet?.name ?? null, head: head?.name ?? null };
      throw error;
    }
  }

  function isFluidHazard(block) {
    return !!block && [
      'water',
      'flowing_water',
      'lava',
      'flowing_lava',
    ].includes(block.name);
  }

  function fluidHazard(block) {
    const err = new Error(`${block.name} hazard blocks safe shaft descent`);
    err.code = 'MINE_SHAFT_HAZARD';
    err.block = block.name;
    return err;
  }

  function isClear(block) {
    return Boolean(block) && (!isFluidHazard(block) && (
      block.boundingBox === 'empty' || block.name === 'air' || block.name === 'cave_air'
    ));
  }

  function hasSafeLandingBelow(base, minimumDepth = 1, maximumDepth = 3) {
    for (let depth = minimumDepth; depth <= maximumDepth; depth += 1) {
      const landing = bot.blockAt(base.offset(0, -depth, 0));
      if (isFluidHazard(landing)) throw fluidHazard(landing);
      if (isStableSupport(landing)) return true;
    }
    return false;
  }

  function findSealBlock() {
    if (!bot.inventory?.items) return null;
    return bot.inventory.items().find((i) => [
      'cobblestone',
      'stone',
      'dirt',
      'andesite',
      'diorite',
      'granite',
      'deepslate',
      'cobbled_deepslate',
    ].includes(i.name));
  }

  function stopMovement() {
    for (const control of ['forward', 'back', 'left', 'right', 'jump', 'sprint', 'sneak']) {
      bot.setControlState?.(control, false);
    }
  }

  async function centerAboveSupport({ tolerance = 0.2, checkpoint = () => {} } = {}) {
    checkpoint();
    const base = standingCell();
    const center = base.offset(0.5, 0, 0.5);
    const centered = tolerance => Math.abs(bot.entity.position.x - center.x) <= tolerance
      && Math.abs(bot.entity.position.z - center.z) <= tolerance;
    if (centered(tolerance)) return true; // The default keeps the 0.6m footprint on this support.
    if (typeof bot.lookAt !== 'function' || typeof bot.setControlState !== 'function'
      || !isSolid(bot.blockAt(base.offset(0, -1, 0)))
      || !isClear(bot.blockAt(base)) || !isClear(bot.blockAt(base.offset(0, 1, 0)))) return false;
    // A player straddling two floor blocks does not fall when just one is dug.
    // Align inside this known clear tile; sneaking limits drift before digging.
    stopMovement();
    try {
      for (let step = 0; step < 20 && !centered(0.05); step++) {
        checkpoint();
        assertDryState();
        const current = standingCell();
        if (current.x !== base.x || current.z !== base.z) return false;
        await withActionTimeout(() => bot.lookAt(
          center.offset(0, bot.entity.eyeHeight || 1.62, 0), true,
        ), 2000, 'align above shaft support');
        bot.setControlState('sneak', true);
        bot.setControlState('forward', true);
        await wait(50);
      }
    } finally {
      stopMovement();
    }
    await wait(150);
    checkpoint();
    assertDryState();
    return centered(Math.min(0.18, tolerance)) && bot.entity.onGround !== false;
  }

  async function advanceIntoSideStep(target) {
    assertDryState();
    if (!isStableSupport(bot.blockAt(target.offset(0, -1, 0)))
      || !isClear(bot.blockAt(target)) || !isClear(bot.blockAt(target.offset(0, 1, 0)))) return false;
    if (typeof bot.pathfinder?.goto !== 'function') return false;
    const previous = bot.pathfinder.movements;
    if (bot.registry && bot.pathfinder.setMovements) {
      const movements = configureDryNavigation(new pathfinderPkg.Movements(bot), bot);
      movements.canDig = false;
      movements.allow1by1towers = false;
      bot.pathfinder.setMovements(movements);
    }
    try {
      await withActionTimeout(() => bot.pathfinder.goto(
        new pathfinderPkg.goals.GoalBlock(target.x, target.y, target.z)),
      5000, 'move to supported shaft step', () => bot.pathfinder.stop?.());
      assertDryState();
      const actual = standingCell();
      return actual.x === target.x && actual.y === target.y && actual.z === target.z;
    } catch (error) {
      propagateInterruptedOperation(error);
      assertDryState();
      return false;
    } finally {
      bot.pathfinder.stop?.();
      if (bot.registry && bot.pathfinder.setMovements) bot.pathfinder.setMovements(previous);
      stopMovement();
    }
  }

  async function waitForStableY(timeoutMs = 1800, samples = 4) {
    const deadline = Date.now() + timeoutMs;
    let lastY = Math.floor(bot.entity.position.y);
    let stable = 0;
    while (Date.now() < deadline) {
      assertDryState();
      await wait(100);
      const currentY = Math.floor(bot.entity.position.y);
      if (currentY === lastY) {
        stable++;
        if (stable >= samples) return currentY;
      } else {
        lastY = currentY;
        stable = 0;
      }
    }
    return Math.floor(bot.entity.position.y);
  }

  async function waitForDescent(startY, startExactY, timeoutMs = 12000) {
    const deadline = Date.now() + timeoutMs;
    stopMovement();
    while (Date.now() < deadline) {
      assertDryState();
      if (Math.floor(bot.entity.position.y) < startY || bot.entity.position.y < startExactY - 0.2) {
        stopMovement();
        await waitForGround(1500);
        await waitForStableY(1800, 3);
        return true;
      }
      await wait(100);
    }
    stopMovement();
    return Math.floor(bot.entity.position.y) < startY || bot.entity.position.y < startExactY - 0.2;
  }

  function candidateDirections() {
    const yaw = bot.entity?.yaw || 0;
    const dirs = [
      { x: 0, z: 1, score: Math.abs(Math.sin(yaw) - 1) },
      { x: 1, z: 0, score: Math.abs(Math.cos(yaw) - 1) },
      { x: 0, z: -1, score: Math.abs(Math.sin(yaw) + 1) },
      { x: -1, z: 0, score: Math.abs(Math.cos(yaw) + 1) },
    ];
    return dirs.sort((a, b) => a.score - b.score);
  }

  function canExcavateTo(positions, destination = null) {
    if (!Object.keys(bot.entities || {}).length) return true;
    const key = p => `${Math.floor(p.x)},${Math.floor(p.y)},${Math.floor(p.z)}`;
    const removed = new Set(positions.map(key));
    const preview = Object.create(bot);
    const world = Object.create(bot.world || null);
    if (typeof bot.world?.raycast === 'function') {
      Object.defineProperty(world, 'raycast', { value: (...args) => {
        const hit = bot.world.raycast(...args);
        // A ray hit on a block about to be removed cannot prove cover. Do not
        // invent a second hit behind it when the remaining world is unknown.
        return hit?.position && removed.has(key(hit.position)) ? null : hit;
      } });
    }
    Object.defineProperties(preview, {
      blockAt: { value: p => removed.has(key(p))
        ? { name: 'air', boundingBox: 'empty', shapes: [], position: p } : bot.blockAt(p) },
      world: { value: world },
    });
    return !findHostileThreat(preview, bot.entity.position)
      && (!destination || !findHostileThreat(preview, destination));
  }

  function needsIronPickaxe(blockName = '') {
    return blockName.includes('diamond_ore')
      || blockName.includes('deepslate_diamond_ore')
      || blockName.includes('redstone_ore')
      || blockName.includes('gold_ore')
      || blockName.includes('emerald_ore');
  }

  function isRockLike(blockName = '') {
    return blockName.includes('stone')
      || blockName.includes('deepslate')
      || blockName.includes('diorite')
      || blockName.includes('andesite')
      || blockName.includes('granite')
      || blockName.includes('ore');
  }

  async function digIfNeeded(block) {
    assertDryState();
    if (block?.position) block = bot.blockAt(block.position);
    if (!block) throw fluidHazard({ name: 'unknown' });
    if (isFluidHazard(block)) throw fluidHazard(block);
    if (isClear(block)) return false;
    if (!isSolid(block)) return false;
    if (!canExcavateTo([block.position])) throw fluidHazard({ name: 'HOSTILE_THREAT' });
    const safety = collectionDigSafety(bot, block, { standingPosition: bot.entity.position });
    if (!safety.safe) throw fluidHazard({ name: safety.block || safety.reason_code });
    const tool = await withActionTimeout(
      () => equipBestPickaxe(block.name),
      3000,
      'equip pickaxe',
    );
    if (!tool && isRockLike(block.name)) {
      const err = new Error(`pickaxe required for ${block.name}`);
      err.code = 'TOOL_REQUIRED';
      err.block = block.name;
      throw err;
    }
    if ((!tool || tool === 'wooden_pickaxe') && block.name.includes('deepslate')) {
      const err = new Error(`stone pickaxe or better required for ${block.name}`);
      err.code = 'TOOL_REQUIRED';
      err.block = block.name;
      throw err;
    }
    if (typeof bot.lookAt === 'function' && block.position?.offset) {
      await withActionTimeout(
        () => bot.lookAt(block.position.offset(0.5, 0.5, 0.5), true),
        2000,
        'look at stair block'
      );
    }
    try {
      await withDigTimeout(block, 8000);
    } catch (err) {
      propagateInterruptedOperation(err);
      const refreshed = bot.blockAt(block.position);
      if (isClear(refreshed)) return true;
      if (String(err?.message || '').includes('Digging aborted')) {
        await wait(250);
        await withDigTimeout(refreshed || block, 8000);
      } else {
        throw err;
      }
    }
    return true;
  }

  async function placeBlockAtAir(targetPos) {
    if (typeof bot.placeBlock !== 'function') return false;
    if (!isClear(bot.blockAt(targetPos))) return false;
    const item = findSealBlock();
    if (!item) return false;
    const refs = [
      { offset: new Vec3(0, -1, 0), face: new Vec3(0, 1, 0) },
      { offset: new Vec3(0, 1, 0), face: new Vec3(0, -1, 0) },
      { offset: new Vec3(1, 0, 0), face: new Vec3(-1, 0, 0) },
      { offset: new Vec3(-1, 0, 0), face: new Vec3(1, 0, 0) },
      { offset: new Vec3(0, 0, 1), face: new Vec3(0, 0, -1) },
      { offset: new Vec3(0, 0, -1), face: new Vec3(0, 0, 1) },
    ];
    for (const ref of refs) {
      const refBlock = bot.blockAt(
        targetPos.offset(ref.offset.x, ref.offset.y, ref.offset.z),
      );
      if (!isSolid(refBlock)) continue;
      try {
        await withActionTimeout(
          () => bot.equip(item, 'hand'),
          3000,
          'equip shaft seal block',
        );
        if (typeof bot.lookAt === 'function' && targetPos?.offset) {
          await withActionTimeout(
            () => bot.lookAt(targetPos.offset(0.5, 0.5, 0.5), true),
            2000,
            'look at shaft seal block'
          );
        }
        await withActionTimeout(
          () => bot.placeBlock(refBlock, ref.face),
          4000,
          `place shaft seal block@${targetPos.x},${targetPos.y},${targetPos.z}`
        );
        await wait(150);
        return isSolid(bot.blockAt(targetPos));
      } catch (err) {
        propagateInterruptedOperation(err);
        debug(`seal failed at ${targetPos.x},${targetPos.y},${targetPos.z}: ${err?.message || err}`);
      }
    }
    return false;
  }

  async function sealShaftOpenings() {
    const base = bot.entity.position.floored();
    let sealed = 0;
    for (const dir of [
      new Vec3(1, 0, 0),
      new Vec3(-1, 0, 0),
      new Vec3(0, 0, 1),
      new Vec3(0, 0, -1),
    ]) {
      for (const yOffset of [-1]) {
        const target = base.offset(dir.x, yOffset, dir.z);
        if (await placeBlockAtAir(target)) sealed += 1;
      }
    }
    return sealed;
  }

  async function harvestEmergencySupportBlock() {
    if (findSealBlock()) return true;
    const base = standingCell();
    const harvestable = (block) => isSolid(block) && (
      isRockLike(block.name)
      || block.name === 'dirt'
      || block.name === 'grass_block'
    );
    for (const dir of candidateDirections()) {
      if (!canExcavateTo([base.offset(dir.x, 0, dir.z), base.offset(dir.x, 1, dir.z)])) continue;
      for (const yOffset of [0, 1]) {
        const block = bot.blockAt(base.offset(dir.x, yOffset, dir.z));
        if (!harvestable(block)) continue;
        await digIfNeeded(block);
        for (let attempt = 0; attempt < 20; attempt += 1) {
          if (findSealBlock()) return true;
          await wait(100);
        }
      }
    }
    return false;
  }

  async function moveToSupportedLedge() {
    const base = standingCell();
    const startX = bot.entity.position.x;
    const startZ = bot.entity.position.z;
    for (const dir of candidateDirections()) {
      const feetPos = base.offset(dir.x, 0, dir.z);
      const headPos = feetPos.offset(0, 1, 0);
      const support = bot.blockAt(feetPos.offset(0, -1, 0));
      if (!isStableSupport(support)) continue;

      const headBlock = bot.blockAt(headPos);
      const feetBlock = bot.blockAt(feetPos);
      if (isFluidHazard(headBlock) || isFluidHazard(feetBlock)) continue;
      if (!canExcavateTo([headPos, feetPos], feetPos.offset(.5, 0, .5))) continue;
      try {
        await digIfNeeded(headBlock);
        await digIfNeeded(feetBlock);
      } catch (error) {
        propagateInterruptedOperation(error);
        if (error.code === 'MINE_SHAFT_HAZARD') continue;
        throw error;
      }
      if (typeof bot.lookAt === 'function' && feetPos?.offset) {
        await withActionTimeout(
          () => bot.lookAt(feetPos.offset(0.5, 0.5, 0.5), true),
          2000,
          'look toward supported ledge'
        );
      }
      if (!await advanceIntoSideStep(feetPos)) continue;
      await waitForGround(1500);
      await waitForStableY(1800, 3);

      const moved = Math.hypot(
        bot.entity.position.x - startX,
        bot.entity.position.z - startZ,
      ) >= 0.45;
      if (moved) return true;
    }
    return false;
  }

  async function digStairStep(preserveReturnPath = false) {
    const base = standingCell();
    const startY = base.y;
    for (const dir of candidateDirections()) {
      const feetPos = base.offset(dir.x, -1, dir.z);
      const headPos = feetPos.offset(0, 1, 0);
      const support = bot.blockAt(feetPos.offset(0, -1, 0));
      if (!isStableSupport(support)) continue;

      const feetBlock = bot.blockAt(feetPos);
      const headBlock = bot.blockAt(headPos);
      if (isFluidHazard(feetBlock) || isFluidHazard(headBlock)) continue;
      const returnHeadPos = headPos.offset(0, 1, 0);
      const returnHead = preserveReturnPath ? bot.blockAt(returnHeadPos) : null;
      if (preserveReturnPath && !isClear(returnHead) && !isSolid(returnHead)) continue;
      const excavation = preserveReturnPath ? [returnHeadPos, headPos, feetPos] : [headPos, feetPos];
      if (!canExcavateTo(excavation, feetPos.offset(.5, 0, .5))) continue;
      try {
        // A downward step needs this extra headroom to be climbed in reverse.
        if (preserveReturnPath) await digIfNeeded(returnHead);
        await digIfNeeded(headBlock);
        await digIfNeeded(feetBlock);
      } catch (error) {
        propagateInterruptedOperation(error);
        if (error.code === 'MINE_SHAFT_HAZARD') continue;
        throw error;
      }

      if (typeof bot.lookAt === 'function' && feetPos?.offset) {
        await withActionTimeout(
          () => bot.lookAt(feetPos.offset(0.5, 1.0, 0.5), true),
          2000,
          'look into stair step'
        );
      }

      if (!await advanceIntoSideStep(feetPos)) continue;
      await waitForGround(1500);
      await waitForStableY(1800, 3);

      if (standingCell().y < startY) {
        return true;
      }
    }
    return false;
  }

  async function digVerticalStep(shouldStop = () => false) {
    if (!await centerAboveSupport()) return false;
    const startY = Math.floor(bot.entity.position.y);
    const startExactY = bot.entity.position.y;
    const base = standingCell();
    const currentFeet = bot.blockAt(base);
    const currentHead = bot.blockAt(base.offset(0, 1, 0));
    if (isFluidHazard(currentFeet)) throw fluidHazard(currentFeet);
    if (isFluidHazard(currentHead)) throw fluidHazard(currentHead);
    await sealShaftOpenings();
    let below = bot.blockAt(base.offset(0, -1, 0));
    if (isFluidHazard(below)) throw fluidHazard(below);
    if (!isSolid(below)) {
      below = bot.blockAt(base.offset(0, -2, 0));
      if (isFluidHazard(below)) throw fluidHazard(below);
    }
    if (!isSolid(below)) {
      await placeBlockAtAir(base.offset(0, -2, 0));
      await placeBlockAtAir(base.offset(0, -1, 0));
      below = bot.blockAt(base.offset(0, -1, 0));
    }
    if (!isSolid(below)) {
      if (!hasSafeLandingBelow(base)) return false;
      return waitForDescent(startY, startExactY, 12000);
    }

    const digDepth = Math.max(1, base.y - below.position.y);
    if (!hasSafeLandingBelow(base, digDepth + 1)) {
      debug(`brace needed below depth=${digDepth} at ${base.x},${base.y},${base.z}`);
      await placeBlockAtAir(base.offset(0, -(digDepth + 1), 0));
      debug(`brace result safe=${hasSafeLandingBelow(base, digDepth + 1)}`);
      if (!hasSafeLandingBelow(base, digDepth + 1)) return false;
    }
    if (!canExcavateTo([below.position], below.position.offset(.5, 0, .5))) return false;
    await digIfNeeded(below);
    if (shouldStop()) return true;
    stopMovement();
    let retriedBelow = false;
    const deadline = Date.now() + 12000;
    while (Date.now() < deadline) {
      const currentFeet = bot.blockAt(bot.entity.position.floored());
      if (isFluidHazard(currentFeet)) throw fluidHazard(currentFeet);
      if (Math.floor(bot.entity.position.y) < startY || bot.entity.position.y < startExactY - 0.2) {
        stopMovement();
        await waitForGround(1500);
        await waitForStableY(1800, 3);
        await sealShaftOpenings();
        return true;
      }
      const refreshedBelow = bot.blockAt(base.offset(0, -1, 0));
      if (isFluidHazard(refreshedBelow)) throw fluidHazard(refreshedBelow);
      if (!retriedBelow && isSolid(refreshedBelow)) {
        retriedBelow = true;
        await digIfNeeded(refreshedBelow);
        if (shouldStop()) return true;
        stopMovement();
      }
      await wait(100);
    }
    return Math.floor(bot.entity.position.y) < startY || bot.entity.position.y < startExactY - 0.2;
  }

  async function waitForGround(timeoutMs = 3000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (bot.entity?.onGround) return true;
        assertDryState();
        await wait(100);
      }
    return !!bot.entity?.onGround;
  }

  async function equipBestPickaxe(blockName = '') {
    if (!bot.inventory?.items) return null;
    const currentY = Math.floor(bot.entity?.position?.y ?? 999);
    const allowIronFallback = currentY <= 64;
    const preferIronForOre = allowIronFallback && blockName.includes('ore');
    const preferIronForDeepslate = allowIronFallback && blockName.includes('deepslate');
    const pickaxes = needsIronPickaxe(blockName)
      ? ['netherite_pickaxe', 'diamond_pickaxe', 'iron_pickaxe', 'stone_pickaxe', 'wooden_pickaxe']
      : (preferIronForOre || preferIronForDeepslate
        ? ['iron_pickaxe', 'stone_pickaxe', 'wooden_pickaxe']
        : allowIronFallback
        ? ['stone_pickaxe', 'wooden_pickaxe', 'iron_pickaxe']
        : ['stone_pickaxe', 'wooden_pickaxe']);
    for (const name of pickaxes) {
      const item = bot.inventory.items().find((i) => i.name === name);
      if (item) {
        await bot.equip(item, 'hand');
        return name;
      }
    }
    return null;
  }

  function inventoryCount(name) {
    if (!bot.inventory?.items) return 0;
    return bot.inventory.items()
      .filter((item) => item.name === name)
      .reduce((total, item) => total + (item.count || 0), 0);
  }

  async function waitForSurvivalThreatToClear() {
    for (let check = 0; getSurvivalThreat(); check += 1) {
      assertDryState();
      if (check >= 40) {
        const threat = getSurvivalThreat();
        const err = new Error(`mine_shaft paused by persistent ${threat?.type || 'survival'} threat`);
        err.code = 'MINE_SHAFT_THREAT';
        err.threat = threat;
        throw err;
      }
      await wait(250);
    }
  }

  async function mineShaft(targetY = 20, minimumCobblestone = 0, context = {}) {
    context.operation_scope?.checkpoint();
    if (!bot.entity) throw new Error('bot not spawned');
    assertDryState();
    const cobblestoneTarget = Math.max(0, Number(minimumCobblestone) || 0);
    const startingCobblestone = inventoryCount('cobblestone');
    const cobblestoneGained = () => Math.max(
      0,
      inventoryCount('cobblestone') - startingCobblestone,
    );
    const quotaResult = () => (
      cobblestoneTarget > 0 && cobblestoneGained() >= cobblestoneTarget
        ? `Shaft mined cobblestone quota ${cobblestoneGained()} (target ${cobblestoneTarget})`
        : null
    );
    const keepSurvivalSystems = process.env.MINE_SHAFT_KEEP_SURVIVAL !== 'false';
    if (!keepSurvivalSystems && typeof disableAuto === 'function') disableAuto();
    const startY = Math.floor(bot.entity.position.y);
    let lastY = standingCell().y;
    let stuck = 0;
    const depth = Math.max(1, startY - targetY);
    const deadline = Date.now() + Math.max(180000, depth * 6000);
    const preserveReturnPath = context.preserve_return_path === true;
    const descend = () => preserveReturnPath
      ? digStairStep(true) : digVerticalStep(() => quotaResult() !== null);
    try {
      await waitForGround(3000);
      while (standingCell().y > targetY && Date.now() < deadline) {
        assertDryState();
        await waitForSurvivalThreatToClear();
        const completedQuota = quotaResult();
        if (completedQuota) return completedQuota;
        let attemptedDig = false;
        try {
          attemptedDig = await descend();
          const completedQuotaAfterDescent = quotaResult();
          if (completedQuotaAfterDescent) return completedQuotaAfterDescent;
          if (!attemptedDig) {
            attemptedDig = await moveToSupportedLedge();
          }
          if (!attemptedDig && !preserveReturnPath) {
            attemptedDig = await digStairStep();
          }
          if (!attemptedDig && !findSealBlock()) {
            const harvestedSupport = await harvestEmergencySupportBlock();
            if (harvestedSupport) {
              attemptedDig = await descend();
              if (!attemptedDig && !preserveReturnPath) {
                attemptedDig = await digStairStep();
              }
            }
          }
        } catch (e) {
          if (context.collection_safety?.pending) throw e;
          propagateInterruptedOperation(e);
          if (getSurvivalThreat()) {
            await waitForSurvivalThreatToClear();
            continue;
          }
          if (e?.code === 'MINE_SHAFT_HAZARD') {
            attemptedDig = await moveToSupportedLedge();
            if (!attemptedDig) attemptedDig = await digStairStep(preserveReturnPath);
            if (!attemptedDig) throw e;
            continue;
          }
          if (e && [
            'MINE_SHAFT_ACTION_TIMEOUT',
            'TOOL_REQUIRED',
          ].includes(e.code)) {
            throw e;
          }
        }
        if (!attemptedDig) {
          stopMovement();
          const currentY = standingCell().y;
          const err = new Error(
            `mine_shaft stuck above target: y=${currentY}, target=${targetY}; no safe stair step`
          );
          err.code = 'MINE_SHAFT_STUCK';
          err.currentY = currentY;
          err.targetY = targetY;
          throw err;
        }
        stopMovement();
        await waitForGround(1500);
        await waitForStableY(1800, 3);
        const curY = standingCell().y;
        if (curY === lastY) {
          if (bot.entity.onGround || attemptedDig) stuck++;
          if (stuck > 6) {
            const err = new Error(
              `mine_shaft stuck above target: y=${curY}, target=${targetY}`
            );
            err.code = 'MINE_SHAFT_STUCK';
            err.currentY = curY;
            err.targetY = targetY;
            throw err;
          }
        } else {
          stuck = 0;
          lastY = curY;
        }
      }
      stopMovement();
      await waitForGround(1500);
      await waitForStableY(1800, 3);
      const completedQuota = quotaResult();
      if (completedQuota) return completedQuota;
      const finalY = standingCell().y;
      if (finalY > targetY) {
        const err = new Error(`mine_shaft timed out above target: y=${finalY}, target=${targetY}`);
        err.code = 'MINE_SHAFT_TIMEOUT';
        err.currentY = finalY;
        err.targetY = targetY;
        throw err;
      }
      return `Shaft mined ${startY} -> y=${finalY} (target ${targetY})`;
    } finally {
      stopMovement();
      if (!keepSurvivalSystems && typeof enableAuto === 'function') enableAuto();
    }
  }
  return { mineShaft, centerAboveSupport };
}
