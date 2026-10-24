import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import injectSimpleInventory from 'mineflayer/lib/plugins/simple_inventory.js';

import { createSmelt, fuelUnitsForSmelt } from '../src/smelt.js';
import { createOperationScope } from '../src/runtime/operationScope.js';
import { withActionEvidence } from '../src/runtime/actionEvidence.js';

function sdkFurnaceFixture({ rejectAll = false, solidRoom = false } = {}) {
  const registry = minecraftData('1.21.1');
  const bot = new EventEmitter();
  const slots = Array(46).fill(null);
  const stack = (name, slot, count = 8) => ({ name, type: registry.itemsByName[name].id, slot, count });
  slots[9] = stack('furnace', 9, 1);
  slots[10] = stack('raw_iron', 10, 7);
  slots[11] = stack('coal', 11, 1);
  ['stone_pickaxe', 'dirt', 'cobblestone', 'andesite', 'diorite', 'granite', 'oak_planks', 'stone', 'deepslate']
    .forEach((name, index) => { slots[36 + index] = stack(name, 36 + index); });
  const blocks = new Map();
  const key = p => `${p.x},${p.y},${p.z}`;
  const block = (name, p) => ({ name, type: registry.blocksByName[name].id, position: p.floored(), boundingBox: name === 'air' ? 'empty' : 'block' });
  let firstPlacement = true;
  const attempts = [];
  const mutations = [];
  Object.assign(bot, {
    health: 20, game: { dimension: 'minecraft:overworld' },
    entity: { position: new Vec3(0.5, 64, 0.5), onGround: true }, quickBarSlot: 0,
    supportFeature: () => false, _client: { write() {} },
    inventory: { slots, items: () => slots.filter(i => i?.count > 0),
      findInventoryItem: type => slots.find(i => i?.type === type && i.count > 0),
      firstEmptySlotRange: (start, end) => { for (let i = start; i < end; i++) if (!slots[i]) return i; return null; } },
    updateHeldItem() { bot.heldItem = slots[36 + bot.quickBarSlot]; },
    async moveSlotItem(from, to) {
      const a = slots[from], b = slots[to];
      slots[from] = b ? { ...b, slot: from } : null;
      slots[to] = a ? { ...a, slot: to } : null;
      bot.updateHeldItem();
    },
    blockAt(position) {
      const p = position.floored();
      if (blocks.has(key(p))) return blocks.get(key(p));
      const playerSpace = p.x === 0 && p.z === 0 && [64, 65].includes(p.y);
      return block(p.y < (solidRoom ? 66 : 64) && !playerSpace ? 'stone' : 'air', p);
    },
    findBlock: () => [...blocks.values()].find(b => b.name === 'furnace') || null,
    async dig(before) {
      const after = block('air', before.position);
      blocks.set(key(before.position), after); mutations.push(['dig', before.name]);
      bot.emit('blockUpdate', before, after); bot.emit('diggingCompleted', after);
    },
    async placeBlock(ref, face) {
      const name = bot.heldItem?.name;
      attempts.push(name);
      if (firstPlacement || (rejectAll && name === 'furnace')) {
        firstPlacement = false;
        throw new Error('Event blockUpdate did not fire within timeout of 5000ms');
      }
      if (!registry.blocksByName[name]) throw new Error('held item is not placeable');
      const p = ref.position.plus(face), before = bot.blockAt(p), after = block(name, p);
      blocks.set(key(p), after); mutations.push(['place', name]);
      bot.heldItem.count--; if (!bot.heldItem.count) slots[bot.heldItem.slot] = null;
      bot.updateHeldItem(); bot.emit('blockPlaced', before, after);
      if (name !== 'furnace') throw new Error('expected furnace update was not observed');
    },
    pathfinder: { stop() {}, setGoal() {}, async goto() {} }, lookAt: async () => {},
    async openFurnace() {
      return { putInput: async () => {}, putFuel: async () => {},
        outputItem: () => ({ name: 'iron_ingot', count: 1 }),
        takeOutput: async () => { slots[12] = stack('iron_ingot', 12, 1); return slots[12]; }, close: async () => {} };
    },
  });
  injectSimpleInventory(bot); bot.updateHeldItem();
  const smelt = createSmelt({ bot, getMcData: async () => registry, wait: async () => {} });
  return { bot, registry, smelt, attempts, mutations, blocks, block };
}

test('furnace retries resolve live slots using the installed SDK equip implementation', async () => {
  const { smelt, attempts, mutations } = sdkFurnaceFixture();
  const result = await smelt.smelt('raw_iron', 'coal', 1, { budget: { max_blocks_changed: 8 } });
  assert.match(result, /Smelted 1\/1/);
  assert.deepEqual(attempts, ['furnace', 'furnace'], 'a cached slot must not equip the pickaxe or construction stock');
  assert.deepEqual(mutations, [['place', 'furnace']]);
});

test('furnace preparation reserves the original block allowance and keeps actual evidence unchanged', async () => {
  const { bot, smelt, mutations } = sdkFurnaceFixture({ rejectAll: true, solidRoom: true });
  await assert.rejects(withActionEvidence(bot, () => smelt.smelt('raw_iron', 'coal', 1,
    { budget: { max_blocks_changed: 2 } })), error => {
    assert.equal(error.code, 'BUDGET_EXHAUSTED');
    assert.equal(error.details.reserved_mutation_attempts, 2);
    assert.equal(error.budget_usage.max_blocks_changed, mutations.length, 'report actual changes, never reservation or a clamp');
    assert.equal(mutations.length, 1, 'one dig plus an unconfirmed placement occupy both reservations');
    return true;
  });
});

test('approaching an existing furnace cannot add unreserved digging or scaffolding', async () => {
  const { bot, smelt, blocks, block } = sdkFurnaceFixture();
  blocks.set('3,64,0', block('furnace', new Vec3(3, 64, 0)));
  const movements = { canDig: true, allow1by1towers: true, scafoldingBlocks: [1], canOpenDoors: true };
  bot.pathfinder.movements = movements;
  let destructive = false;
  bot.pathfinder.goto = async () => {
    destructive ||= movements.canDig || movements.allow1by1towers || movements.scafoldingBlocks.length > 0;
  };
  await smelt.smelt('raw_iron', 'coal', 1, { budget: { max_blocks_changed: 0 } });
  assert.equal(destructive, false);
  assert.deepEqual(movements, { canDig: true, allow1by1towers: true, scafoldingBlocks: [1], canOpenDoors: true });
});

test('furnace preparation does not swallow cancellation into another placement attempt', async () => {
  const { bot, smelt } = sdkFurnaceFixture();
  const controller = new AbortController();
  const failure = Object.assign(new Error('cancel furnace placement'), { name: 'AbortError', code: 'ACTION_CANCELLED' });
  let calls = 0;
  bot.placeBlock = async () => { calls++; controller.abort(); throw failure; };
  await assert.rejects(smelt.smelt('raw_iron', 'coal', 1,
    { signal: controller.signal, budget: { max_blocks_changed: 8 } }), error => error === failure);
  assert.equal(calls, 1);
});

test('furnace placement rejects a different held item before any world mutation', async () => {
  const { bot, smelt, attempts, mutations } = sdkFurnaceFixture();
  const equip = bot.equip;
  bot.equip = async (...args) => { await equip(...args); bot.heldItem = { name: 'dirt' }; };
  await assert.rejects(smelt.smelt('raw_iron', 'coal', 1,
    { budget: { max_blocks_changed: 8 } }), error => error.code === 'FURNACE_ITEM_CHANGED');
  assert.deepEqual(attempts, []);
  assert.deepEqual(mutations, []);
});

test('smelt allocates two planks for three furnace operations', () => {
  assert.equal(fuelUnitsForSmelt('oak_planks', 3), 2);
  assert.equal(fuelUnitsForSmelt('coal', 3), 1);
});

function createMcData() {
  return {
    blocksByName: {
      furnace: { id: 61 },
    },
    itemsByName: {
      raw_iron: { id: 100 },
      coal: { id: 101 },
      furnace: { id: 102 },
    },
  };
}

test('smelt places a carried furnace when none is nearby', async () => {
  const calls = [];
  const solidBlock = { name: 'stone', position: { x: 1, y: 63, z: 1 } };
  const placedFurnace = { name: 'furnace', position: { x: 1, y: 64, z: 1 } };
  let findBlockCalls = 0;
  const furnaceWindow = {
    putInput: async (...args) => calls.push(['putInput', ...args]),
    putFuel: async (...args) => calls.push(['putFuel', ...args]),
    outputItem: () => ({ name: 'iron_ingot', count: 3 }),
    takeOutput: async () => {
      calls.push(['takeOutput']);
      return { name: 'iron_ingot', count: 3 };
    },
    close: async () => calls.push(['close']),
  };
  let equipped = null;

  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }],
    },
    findBlock: ({ matching }) => {
      if (matching === 61) {
        findBlockCalls += 1;
        return findBlockCalls === 1 ? null : placedFurnace;
      }
      return null;
    },
    blockAt: () => solidBlock,
    equip: async (item, destination) => calls.push(['equip', item.name, destination]),
    placeBlock: async (block, vec) => calls.push(['placeBlock', block.name, vec.x, vec.y, vec.z]),
    openFurnace: async (block) => {
      calls.push(['openFurnace', block.name]);
      return furnaceWindow;
    },
    chat: (message) => calls.push(['chat', message]),
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    botUsername: 'AnimettaView',
    wait: async () => {},
  });

  const result = await smelt.smelt('raw_iron', 'coal', 3);

  assert.match(result, /Smelted 3\/3 raw_iron -> iron_ingot/);
  assert.deepEqual(calls.slice(0, 4), [
    ['equip', 'furnace', 'hand'],
    ['placeBlock', 'stone', 0, 1, 0],
    ['openFurnace', 'furnace'],
    ['putInput', 100, null, 3],
  ]);
  assert.deepEqual(calls[4], ['putFuel', 101, null, 1]);
  assert(calls.some((call) => call[0] === 'takeOutput'));
  assert(!calls.some((call) => call[0] === 'chat' && String(call[1]).startsWith('/')));
});

test('smelt accepts a placed furnace when placeBlock times out after world update', async () => {
  const calls = [];
  const support = { name: 'andesite', position: { x: -15, y: 47, z: -13 } };
  const placedFurnace = { name: 'furnace', position: { x: -15, y: 48, z: -13 } };
  let placed = false;
  const furnaceWindow = {
    putInput: async (...args) => calls.push(['putInput', ...args]),
    putFuel: async (...args) => calls.push(['putFuel', ...args]),
    outputItem: () => ({ name: 'iron_ingot', count: 3 }),
    takeOutput: async () => calls.push(['takeOutput']),
    close: async () => calls.push(['close']),
  };

  const bot = {
    entity: {
      position: { x: -14.7, y: 48, z: -12.7 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }],
    },
    findBlock: ({ matching }) => (matching === 61 && placed ? placedFurnace : null),
    blockAt: (pos) => {
      if (placed && pos.x === -15 && pos.y === 48 && pos.z === -13) return placedFurnace;
      if (pos.x === -15 && pos.y === 47 && pos.z === -13) return support;
      return { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } };
    },
    equip: async () => {},
    lookAt: async () => {},
    setControlState: () => {},
    placeBlock: async () => {
      placed = true;
      throw new Error('Event blockUpdate:(-15, 48, -13) did not fire within timeout of 5000ms');
    },
    openFurnace: async (block) => {
      calls.push(['openFurnace', block.name, block.position.x, block.position.y, block.position.z]);
      return furnaceWindow;
    },
    chat: (message) => calls.push(['chat', message]),
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });
  const result = await smelt.smelt('raw_iron', 'coal', 3);

  assert.match(result, /Smelted 3\/3 raw_iron -> iron_ingot/);
  assert(calls.some((call) => call[0] === 'openFurnace' && call[1] === 'furnace'));
  assert(!calls.some((call) => call[0] === 'chat' && String(call[1]).startsWith('/')));
});

test('smelt continues when putInput throws after moving the item into the furnace', async () => {
  const calls = [];
  const presentation = [];
  const furnaceBlock = { name: 'furnace', position: { x: 1, y: 64, z: 1 } };
  let input = null;
  let fuel = null;
  const furnaceWindow = {
    putInput: async (...args) => {
      calls.push(['putInput', ...args]);
      input = { name: 'raw_iron', count: 3 };
      throw new Error("Can't find raw_iron in slots [3 - 39], (item id: 100)");
    },
    inputItem: () => input,
    putFuel: async (...args) => {
      calls.push(['putFuel', ...args]);
      fuel = { name: 'coal', count: 1 };
    },
    fuelItem: () => fuel,
    outputItem: () => ({ name: 'iron_ingot', count: 3 }),
    takeOutput: async () => {
      calls.push(['takeOutput']);
      return { name: 'iron_ingot', count: 3 };
    },
    close: async () => calls.push(['close']),
  };

  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
    },
    inventory: {
      items: () => [
        { name: 'raw_iron', count: 3 },
        { name: 'coal', count: 1 },
      ],
    },
    findBlock: ({ matching }) => (matching === 61 ? furnaceBlock : null),
    pathfinder: {
      goto: async (goal) => calls.push(['goto', goal.x, goal.y, goal.z, goal.range]),
    },
    lookAt: async () => {},
    openFurnace: async (block) => {
      calls.push(['openFurnace', block.name]);
      return furnaceWindow;
    },
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  const result = await smelt.smelt('raw_iron', 'coal', 3, {
    report_phase: (phase, data) => presentation.push(['phase', phase, data]),
    presentation: {
      focus: async (request) => presentation.push(['focus', request]),
    },
  });

  assert.match(result, /Smelted 3\/3 raw_iron -> iron_ingot/);
  assert(calls.some((call) => call[0] === 'takeOutput'));
  assert(calls.some((call) => call[0] === 'close'));
  assert.equal(presentation[0][1], 'aiming');
  assert.deepEqual(presentation[1], ['focus', {
    phase: 'aiming',
    ordinal: 0,
    target: { x: 1.5, y: 64.5, z: 1.5 },
  }]);
  assert.equal(presentation[2][1], 'acting');
});

test('smelt retries opening furnace after a stale windowOpen timeout', async () => {
  const calls = [];
  const furnaceBlock = { name: 'furnace', position: { x: 4, y: 64, z: 4 } };
  let openAttempts = 0;
  const furnaceWindow = {
    putInput: async (...args) => calls.push(['putInput', ...args]),
    putFuel: async (...args) => calls.push(['putFuel', ...args]),
    outputItem: () => ({ name: 'iron_ingot', count: 3 }),
    takeOutput: async () => calls.push(['takeOutput']),
    close: async () => calls.push(['close']),
  };

  const bot = {
    entity: {
      position: { x: 4.5, y: 64, z: 4.5 },
    },
    inventory: {
      items: () => [
        { name: 'raw_iron', count: 3 },
        { name: 'coal', count: 1 },
      ],
    },
    findBlock: ({ matching }) => (matching === 61 ? furnaceBlock : null),
    blockAt: () => furnaceBlock,
    pathfinder: {
      goto: async (goal) => calls.push(['goto', goal.x, goal.y, goal.z, goal.range]),
    },
    lookAt: async () => calls.push(['lookAt']),
    openFurnace: async (block) => {
      openAttempts += 1;
      calls.push(['openFurnace', openAttempts, block.name]);
      if (openAttempts === 1) {
        throw new Error('Event windowOpen did not fire within timeout of 20000ms');
      }
      return furnaceWindow;
    },
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });
  const phases = [];

  const result = await smelt.smelt('raw_iron', 'coal', 3, {
    report_phase: (phase, data) => phases.push([phase, data]),
  });

  assert.match(result, /Smelted 3\/3 raw_iron -> iron_ingot/);
  assert.equal(openAttempts, 2);
  assert(calls.some((call) => call[0] === 'takeOutput'));
  assert.deepEqual(
    phases.filter(([phase]) => phase === 'recovering'),
    [['recovering', { attempt: 2, reason_code: 'CONTAINER_OPEN_RETRY' }]],
  );
});


test('smelt cancellation closes a live furnace before rejecting', async () => {
  const controller = new AbortController();
  const furnaceBlock = { name: 'furnace', position: { x: 1, y: 64, z: 1 } };
  let bot;
  let closes = 0;
  let markInputStarted;
  const inputStarted = new Promise((resolve) => { markInputStarted = resolve; });
  let releaseInput;
  const inputGate = new Promise((resolve) => { releaseInput = resolve; });
  const furnaceWindow = {
    putInput: async () => {
      markInputStarted();
      await inputGate;
    },
    inputItem: () => null,
    close: async () => {
      closes += 1;
      bot.currentWindow = null;
    },
  };
  bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
      onGround: true,
      velocity: { x: 0, y: 0, z: 0 },
    },
    health: 20,
    food: 20,
    controlState: {},
    currentWindow: null,
    inventory: {
      items: () => [
        { name: 'raw_iron', count: 1 },
        { name: 'coal', count: 1 },
      ],
    },
    findBlock: ({ matching }) => (matching === 61 ? furnaceBlock : null),
    blockAt: () => furnaceBlock,
    pathfinder: {
      goto: async () => {},
      isMoving: () => false,
      stop: () => {},
    },
    pvp: { target: null, stop: () => {} },
    lookAt: async () => {},
    openFurnace: async () => {
      bot.currentWindow = furnaceWindow;
      return furnaceWindow;
    },
    setControlState: (control, state) => { bot.controlState[control] = state; },
    stopDigging: () => {},
  };
  const scope = createOperationScope({
    bot,
    signal: controller.signal,
    deadlineMs: Date.now() + 10_000,
    waitMs: async () => {},
    containerCapable: true,
  });
  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  const pending = smelt.smelt('raw_iron', 'coal', 1, { operation_scope: scope });
  await inputStarted;
  controller.abort('operator stop');
  releaseInput();

  await assert.rejects(pending, (error) => error.name === 'AbortError');
  assert.ok(closes >= 1);
  assert.equal(bot.currentWindow, null);
});

test('smelt clears an occupied target block before placing a carried furnace', async () => {
  const calls = [];
  const support = { name: 'andesite', position: { x: -14, y: 47, z: -13 } };
  const targetStone = { name: 'andesite', position: { x: -14, y: 48, z: -13 } };
  const placedFurnace = { name: 'furnace', position: { x: -14, y: 48, z: -13 } };
  let targetCleared = false;
  let placed = false;
  const furnaceWindow = {
    putInput: async () => {},
    putFuel: async () => {},
    outputItem: () => ({ name: 'iron_ingot', count: 1 }),
    takeOutput: async () => {},
    close: async () => {},
  };

  const bot = {
    entity: {
      position: { x: -14.7, y: 48, z: -12.7 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }, { name: 'stone_pickaxe', count: 1 }],
    },
    findBlock: ({ matching }) => (matching === 61 && placed ? placedFurnace : null),
    blockAt: (pos) => {
      if (placed && pos.x === -14 && pos.y === 48 && pos.z === -13) return placedFurnace;
      if (pos.x === -14 && pos.y === 48 && pos.z === -13) {
        return targetCleared ? { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } } : targetStone;
      }
      if (pos.x === -14 && pos.y === 47 && pos.z === -13) return support;
      return { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } };
    },
    equip: async (item) => calls.push(['equip', item.name]),
    dig: async (block) => {
      calls.push(['dig', block.name]);
      targetCleared = true;
    },
    lookAt: async () => {},
    setControlState: () => {},
    placeBlock: async () => {
      calls.push(['placeBlock']);
      placed = true;
    },
    openFurnace: async () => furnaceWindow,
    chat: () => {},
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  await smelt.smelt('raw_iron', 'coal', 1);

  assert(calls.some((call) => call[0] === 'dig' && call[1] === 'andesite'));
  assert(calls.some((call) => call[0] === 'placeBlock'));
});

test('smelt preserves an existing crafting table when placing a carried furnace', async () => {
  const calls = [];
  // Player base block is (-15, 48, -13): the first fixed placement candidate
  // targets (-14, 48, -13) on top of the support at (-14, 47, -13).
  const tablePos = { x: -14, y: 48, z: -13 };
  const altSupportPos = { x: -16, y: 47, z: -13 };
  const altTargetPos = { x: -16, y: 48, z: -13 };
  const craftingTable = { name: 'crafting_table', position: { ...tablePos } };
  const tableSupport = { name: 'stone', position: { x: -14, y: 47, z: -13 } };
  const altSupport = { name: 'stone', position: { ...altSupportPos } };
  let tableDug = false;
  let furnaceAt = null;
  const furnaceWindow = {
    putInput: async () => {},
    putFuel: async () => {},
    outputItem: () => ({ name: 'iron_ingot', count: 1 }),
    takeOutput: async () => ({ name: 'iron_ingot', count: 1 }),
    close: async () => {},
  };

  const bot = {
    entity: {
      position: { x: -14.7, y: 48, z: -12.7 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }, { name: 'stone_pickaxe', count: 1 }],
    },
    findBlock: ({ matching }) => (
      matching === 61 && furnaceAt ? { name: 'furnace', position: { ...furnaceAt } } : null
    ),
    blockAt: (pos) => {
      if (furnaceAt && pos.x === furnaceAt.x && pos.y === furnaceAt.y && pos.z === furnaceAt.z) {
        return { name: 'furnace', position: { ...furnaceAt } };
      }
      if (pos.x === tablePos.x && pos.y === tablePos.y && pos.z === tablePos.z) {
        return tableDug ? { name: 'air', position: { ...tablePos } } : craftingTable;
      }
      if (pos.x === -14 && pos.y === 47 && pos.z === -13) return tableSupport;
      if (pos.x === altSupportPos.x && pos.y === altSupportPos.y && pos.z === altSupportPos.z) return altSupport;
      return { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } };
    },
    equip: async (item) => calls.push(['equip', item.name]),
    dig: async (block) => {
      calls.push(['dig', block.name, block.position.x, block.position.y, block.position.z]);
      if (block.name === 'crafting_table') tableDug = true;
    },
    lookAt: async () => {},
    setControlState: () => {},
    placeBlock: async (ref, face) => {
      const target = {
        x: ref.position.x + face.x,
        y: ref.position.y + face.y,
        z: ref.position.z + face.z,
      };
      calls.push(['placeBlock', ref.name, target.x, target.y, target.z]);
      furnaceAt = target;
    },
    openFurnace: async (block) => {
      calls.push(['openFurnace', block.name, block.position.x, block.position.y, block.position.z]);
      return furnaceWindow;
    },
    chat: () => {},
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  const result = await smelt.smelt('raw_iron', 'coal', 1);

  assert.match(result, /Smelted 1\/1 raw_iron -> iron_ingot/);
  assert(!calls.some((call) => call[0] === 'dig' && call[1] === 'crafting_table'));
  assert(!calls.some((call) => (
    call[0] === 'placeBlock'
    && call[2] === tablePos.x
    && call[3] === tablePos.y
    && call[4] === tablePos.z
  )));
  assert.equal(bot.blockAt(tablePos).name, 'crafting_table');
  assert(calls.some((call) => (
    call[0] === 'placeBlock'
    && call[1] === 'stone'
    && call[2] === altTargetPos.x
    && call[3] === altTargetPos.y
    && call[4] === altTargetPos.z
  )));
  assert.equal(bot.blockAt(altTargetPos).name, 'furnace');
  assert(calls.some((call) => call[0] === 'openFurnace' && call[1] === 'furnace'));
});

test('smelt still reports missing furnace when none is nearby or carried', async () => {
  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
    },
    inventory: {
      items: () => [],
    },
    findBlock: () => null,
    blockAt: () => ({ name: 'stone' }),
  };
  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  await assert.rejects(
    () => smelt.smelt('raw_iron', 'coal', 1),
    /No furnace nearby and no furnace in inventory/,
  );
});

test('smelt looks at the placement target before placing a carried furnace', async () => {
  const calls = [];
  const solidBlock = { name: 'stone', position: { x: 2, y: 63, z: 1 } };
  const placedFurnace = { name: 'furnace', position: { x: 2, y: 64, z: 1 } };
  let findBlockCalls = 0;
  let lookedAtPlacementTarget = false;
  const furnaceWindow = {
    putInput: async () => {},
    putFuel: async () => {},
    outputItem: () => ({ name: 'iron_ingot', count: 1 }),
    takeOutput: async () => ({ name: 'iron_ingot', count: 1 }),
    close: async () => {},
  };

  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }],
    },
    findBlock: ({ matching }) => {
      if (matching === 61) {
        findBlockCalls += 1;
        return findBlockCalls === 1 ? null : placedFurnace;
      }
      return null;
    },
    blockAt: () => solidBlock,
    equip: async () => {},
    lookAt: async (target, force) => {
      calls.push(['lookAt', Math.round(target.x * 10) / 10, Math.round(target.y * 10) / 10, Math.round(target.z * 10) / 10, force]);
      lookedAtPlacementTarget = true;
    },
    placeBlock: async () => {
      if (!lookedAtPlacementTarget) {
        throw new Error('cannot place without aiming at target');
      }
      calls.push(['placeBlock']);
    },
    openFurnace: async () => furnaceWindow,
    chat: () => {},
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  await smelt.smelt('raw_iron', 'coal', 1);

  assert.deepEqual(calls, [
    ['lookAt', 2.5, 64.5, 1.5, true],
    ['placeBlock'],
    ['lookAt', 2.5, 64.5, 1.5, true],
  ]);
});

test('smelt can place a carried furnace on the side of the block underfoot on narrow terrain', async () => {
  const calls = [];
  const belowFeet = { name: 'stone', position: { x: 1, y: 63, z: 1 } };
  const placedFurnace = { name: 'furnace', position: { x: 2, y: 63, z: 1 } };
  let findBlockCalls = 0;
  let sidePlacementSucceeded = false;
  const furnaceWindow = {
    putInput: async () => {},
    putFuel: async () => {},
    outputItem: () => ({ name: 'iron_ingot', count: 1 }),
    takeOutput: async () => ({ name: 'iron_ingot', count: 1 }),
    close: async () => {},
  };

  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }],
    },
    findBlock: ({ matching }) => {
      if (matching === 61) {
        findBlockCalls += 1;
        return findBlockCalls === 1 || !sidePlacementSucceeded ? null : placedFurnace;
      }
      return null;
    },
    blockAt: (pos) => {
      if (pos.x === 1 && pos.y === 63 && pos.z === 1) return belowFeet;
      return { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } };
    },
    equip: async () => {},
    lookAt: async (target) => calls.push(['lookAt', Math.round(target.x * 10) / 10, Math.round(target.y * 10) / 10, Math.round(target.z * 10) / 10]),
    placeBlock: async (_block, face) => {
      calls.push(['placeBlock', face.x, face.y, face.z]);
      if (face.y === 1) {
        throw new Error('Event blockUpdate:(1, 64, 1) did not fire within timeout of 5000ms');
      }
      sidePlacementSucceeded = true;
    },
    openFurnace: async () => furnaceWindow,
    chat: () => {},
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  await smelt.smelt('raw_iron', 'coal', 1);

  assert(calls.some((call) => call[0] === 'placeBlock' && call[1] === 1 && call[2] === 0 && call[3] === 0));
});

test('smelt reports placement failures without command fallback', async () => {
  const calls = [];
  const support = { name: 'crafting_table', position: { x: 1, y: 63, z: 1 } };

  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }],
    },
    findBlock: () => null,
    blockAt: (pos) => {
      if (pos.x === 1 && pos.y === 63 && pos.z === 1) return support;
      return { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } };
    },
    equip: async () => {},
    lookAt: async () => {},
    placeBlock: async () => {
      throw new Error('Event blockUpdate:(2, 63, 1) did not fire within timeout of 5000ms');
    },
    chat: (message) => {
      calls.push(['chat', message]);
    },
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    botUsername: 'AnimettaView',
    wait: async () => {},
  });

  await assert.rejects(
    () => smelt.smelt('raw_iron', 'coal', 1),
    /No placeable support block for furnace nearby/,
  );

  assert(!calls.some((call) => call[0] === 'chat' && String(call[1]).startsWith('/')));
});

test('smelt builds a carried support block when natural furnace placement keeps timing out', async () => {
  const calls = [];
  const floor = { name: 'stone', position: { x: 1, y: 63, z: 1 } };
  const carriedSupport = { name: 'cobblestone', position: { x: 2, y: 63, z: 1 } };
  const placedFurnace = { name: 'furnace', position: { x: 2, y: 64, z: 1 } };
  let supportPlaced = false;
  let furnacePlaced = false;
  let equipped = null;
  const furnaceWindow = {
    putInput: async () => {},
    putFuel: async () => {},
    outputItem: () => ({ name: 'iron_ingot', count: 1 }),
    takeOutput: async () => ({ name: 'iron_ingot', count: 1 }),
    close: async () => {},
  };

  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
      onGround: true,
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }, { name: 'cobblestone', count: 32 }],
    },
    findBlock: ({ matching }) => (matching === 61 && furnacePlaced ? placedFurnace : null),
    blockAt: (pos) => {
      if (furnacePlaced && pos.x === 2 && pos.y === 64 && pos.z === 1) return placedFurnace;
      if (supportPlaced && pos.x === 2 && pos.y === 63 && pos.z === 1) return carriedSupport;
      if (pos.x === 1 && pos.y === 63 && pos.z === 1) return floor;
      return { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } };
    },
    equip: async (item) => {
      equipped = item.name;
      calls.push(['equip', item.name]);
    },
    lookAt: async () => {},
    setControlState: () => {},
    placeBlock: async (ref, face) => {
      calls.push(['placeBlock', ref.name, face.x, face.y, face.z]);
      if (equipped === 'cobblestone' && ref.name === 'stone') {
        supportPlaced = true;
        return;
      }
      if (equipped === 'furnace' && ref.name === 'cobblestone') {
        furnacePlaced = true;
        return;
      }
      throw new Error('Event blockUpdate:(2, 64, 1) did not fire within timeout of 5000ms');
    },
    openFurnace: async () => furnaceWindow,
    chat: () => {},
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  await smelt.smelt('raw_iron', 'coal', 1);

  assert(calls.some((call) => call[0] === 'equip' && call[1] === 'cobblestone'));
  assert(calls.some((call) => call[0] === 'placeBlock' && call[1] === 'cobblestone' && call[3] === 1));
});

test('smelt sneaks while placing against an interactable support block', async () => {
  const calls = [];
  const support = { name: 'crafting_table', position: { x: 1, y: 63, z: 1 } };
  const placedFurnace = { name: 'furnace', position: { x: 2, y: 63, z: 1 } };
  let findBlockCalls = 0;
  let isSneaking = false;
  let naturalPlacementSucceeded = false;
  const furnaceWindow = {
    putInput: async () => {},
    putFuel: async () => {},
    outputItem: () => ({ name: 'iron_ingot', count: 1 }),
    takeOutput: async () => ({ name: 'iron_ingot', count: 1 }),
    close: async () => {},
  };

  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }],
    },
    findBlock: ({ matching }) => {
      if (matching === 61) {
        findBlockCalls += 1;
        return findBlockCalls === 1 || !naturalPlacementSucceeded ? null : placedFurnace;
      }
      return null;
    },
    blockAt: (pos) => {
      if (pos.x === 1 && pos.y === 63 && pos.z === 1) return support;
      return { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } };
    },
    equip: async () => {},
    lookAt: async () => {},
    setControlState: (control, state) => {
      calls.push(['setControlState', control, state]);
      if (control === 'sneak') isSneaking = state;
    },
    placeBlock: async () => {
      if (!isSneaking) {
        throw new Error('opened crafting table instead of placing');
      }
      naturalPlacementSucceeded = true;
      calls.push(['placeBlock']);
    },
    openFurnace: async () => furnaceWindow,
    chat: () => {},
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  await smelt.smelt('raw_iron', 'coal', 1);

  assert.deepEqual(calls.slice(0, 3), [
    ['setControlState', 'sneak', true],
    ['placeBlock'],
    ['setControlState', 'sneak', false],
  ]);
});

test('smelt jumps before placing a carried furnace on the block directly underfoot', async () => {
  const calls = [];
  const support = { name: 'crafting_table', position: { x: 1, y: 63, z: 1 } };
  const placedFurnace = { name: 'furnace', position: { x: 1, y: 64, z: 1 } };
  let findBlockCalls = 0;
  let jumped = false;
  let directTopPlacementSucceeded = false;
  const furnaceWindow = {
    putInput: async () => {},
    putFuel: async () => {},
    outputItem: () => ({ name: 'iron_ingot', count: 1 }),
    takeOutput: async () => ({ name: 'iron_ingot', count: 1 }),
    close: async () => {},
  };

  const bot = {
    entity: {
      position: { x: 1.5, y: 64, z: 1.5 },
    },
    inventory: {
      items: () => [{ name: 'furnace', count: 1 }],
    },
    findBlock: ({ matching }) => {
      if (matching === 61) {
        findBlockCalls += 1;
        return findBlockCalls === 1 || !directTopPlacementSucceeded ? null : placedFurnace;
      }
      return null;
    },
    blockAt: (pos) => {
      if (pos.x === 1 && pos.y === 63 && pos.z === 1) return support;
      return { name: 'air', position: { x: pos.x, y: pos.y, z: pos.z } };
    },
    equip: async () => {},
    lookAt: async () => {},
    setControlState: (control, state) => {
      calls.push(['setControlState', control, state]);
      if (control === 'jump' && state) jumped = true;
    },
    placeBlock: async (_block, face) => {
      calls.push(['placeBlock', face.x, face.y, face.z]);
      if (face.y !== 1 || !jumped) {
        throw new Error('target occupied');
      }
      directTopPlacementSucceeded = true;
    },
    openFurnace: async () => furnaceWindow,
    chat: () => {},
  };

  const smelt = createSmelt({
    bot,
    getMcData: async () => createMcData(),
    wait: async () => {},
  });

  await smelt.smelt('raw_iron', 'coal', 1);

  assert(calls.some((call) => call[0] === 'setControlState' && call[1] === 'jump' && call[2] === true));
  assert(calls.some((call) => call[0] === 'placeBlock' && call[1] === 0 && call[2] === 1 && call[3] === 0));
});
