import test from 'node:test';
import assert from 'node:assert/strict';
import Vec3 from 'vec3';
import { createMineShaft } from '../src/mine_shaft.js';

test('mineShaft throws when it gets stuck above targetY', async () => {
  const bot = {
    entity: {
      position: {
        y: 80,
        offset() {
          return { x: 0, y: 79, z: 0 };
        },
      },
    },
    blockAt() {
      return { boundingBox: 'block' };
    },
    async dig() {
      // y never changes, simulating a stuck shaft.
    },
  };

  const shaft = createMineShaft({ bot });

  await assert.rejects(
    () => shaft.mineShaft(32),
    (err) => {
      assert.equal(err.code, 'MINE_SHAFT_STUCK');
      assert.match(err.message, /stuck above target/);
      return true;
    }
  );
});

test('mineShaft succeeds before an unsafe gap after collecting its cobblestone quota', async () => {
  let cobblestone = 0;
  const position = new Vec3(0.5, 80, 0.5);
  const bot = {
    entity: { position, onGround: true },
    inventory: {
      items: () => [
        { name: 'wooden_pickaxe', count: 1 },
        { name: 'cobblestone', count: cobblestone },
      ],
    },
    async equip() {},
    blockAt(pos) {
      return { name: 'stone', boundingBox: 'block', position: pos };
    },
    async dig() {
      cobblestone += 12;
    },
    setControlState() {},
  };
  const shaft = createMineShaft({ bot, wait: async () => {} });

  const result = await shaft.mineShaft(50, 12);

  assert.match(result, /cobblestone quota 12/);
});

test('mineShaft pauses excavation until a creeper retreat has cleared', async () => {
  let cobblestone = 0;
  let threat = { type: 'creeper', distance: 6 };
  let waitedForThreat = false;
  const position = new Vec3(0.5, 80, 0.5);
  const bot = {
    entity: { position, onGround: true },
    inventory: {
      items: () => [
        { name: 'wooden_pickaxe', count: 1 },
        { name: 'cobblestone', count: cobblestone },
      ],
    },
    async equip() {},
    blockAt(pos) {
      return { name: 'stone', boundingBox: 'block', position: pos };
    },
    async dig() {
      assert.equal(threat, null, 'excavation resumed before creeper retreat cleared');
      cobblestone += 12;
    },
    setControlState() {},
  };
  const shaft = createMineShaft({
    bot,
    getSurvivalThreat: () => threat,
    wait: async () => {
      if (threat) {
        waitedForThreat = true;
        threat = null;
      }
    },
  });

  const result = await shaft.mineShaft(50, 12);

  assert.equal(waitedForThreat, true);
  assert.match(result, /cobblestone quota 12/);
});

test('mineShaft descends by digging directly below when stair steps are unavailable', async () => {
  let belowCleared = false;
  let waitsAfterDig = 0;
  const position = new Vec3(0.5, 80, 0.5);
  const bot = {
    entity: {
      position,
      onGround: true,
    },
    inventory: {
      items: () => [{ name: 'stone_pickaxe', count: 1 }],
    },
    async equip() {},
    blockAt(pos) {
      if (pos.x !== 0 || pos.z !== 0) {
        return { name: 'air', boundingBox: 'empty', position: pos };
      }
      if (pos.y === 79 && !belowCleared) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      if (pos.y <= 78) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.y === 79) {
        belowCleared = true;
      }
    },
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (belowCleared) {
        waitsAfterDig += 1;
      }
      if (waitsAfterDig >= 2) {
        position.y = 79;
      }
    },
  });

  const result = await shaft.mineShaft(79);

  assert.match(result, /Shaft mined 80 -> y=79/);
});

test('mineShaft reserves iron pickaxe for ores that require it', async () => {
  let belowCleared = false;
  let waitsAfterDig = 0;
  const equipped = [];
  const position = new Vec3(0.5, 80, 0.5);
  const bot = {
    entity: {
      position,
      onGround: true,
    },
    inventory: {
      items: () => [
        { name: 'iron_pickaxe', count: 1 },
        { name: 'stone_pickaxe', count: 1 },
      ],
    },
    async equip(item) {
      equipped.push(item.name);
    },
    blockAt(pos) {
      if (pos.x !== 0 || pos.z !== 0) {
        return { name: 'air', boundingBox: 'empty', position: pos };
      }
      if (pos.y === 79 && !belowCleared) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      if (pos.y <= 78) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.y === 79) belowCleared = true;
    },
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (belowCleared) waitsAfterDig += 1;
      if (waitsAfterDig >= 2) position.y = 79;
    },
  });

  await shaft.mineShaft(79);

  assert.equal(equipped[0], 'stone_pickaxe');
  assert(!equipped.includes('iron_pickaxe'));
});

test('mineShaft asks for tool recovery instead of spending iron pickaxe on stone', async () => {
  const equipped = [];
  const position = new Vec3(0.5, 80, 0.5);
  const bot = {
    entity: {
      position,
      onGround: true,
    },
    inventory: {
      items: () => [{ name: 'iron_pickaxe', count: 1 }],
    },
    async equip(item) {
      equipped.push(item.name);
    },
    blockAt(pos) {
      if (pos.x !== 0 || pos.z !== 0) {
        return { name: 'air', boundingBox: 'empty', position: pos };
      }
      if (pos.y <= 79) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig() {},
    setControlState() {},
  };

  const shaft = createMineShaft({ bot, wait: async () => {} });

  await assert.rejects(
    () => shaft.mineShaft(79),
    (err) => {
      assert.equal(err.code, 'TOOL_REQUIRED');
      assert.match(err.message, /pickaxe required for stone/);
      return true;
    },
  );
  assert(!equipped.includes('iron_pickaxe'));
});

test('mineShaft allows iron pickaxe fallback in deeper layers', async () => {
  let belowCleared = false;
  let waitsAfterDig = 0;
  const equipped = [];
  const position = new Vec3(0.5, 31, 0.5);
  const bot = {
    entity: {
      position,
      onGround: true,
    },
    inventory: {
      items: () => [{ name: 'iron_pickaxe', count: 1 }],
    },
    async equip(item) {
      equipped.push(item.name);
    },
    blockAt(pos) {
      if (pos.x !== 0 || pos.z !== 0) {
        return { name: 'air', boundingBox: 'empty', position: pos };
      }
      if (pos.y === 30 && !belowCleared) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      if (pos.y <= 29) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.y === 30) belowCleared = true;
    },
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (belowCleared) waitsAfterDig += 1;
      if (waitsAfterDig >= 2) position.y = 30;
    },
  });

  await shaft.mineShaft(30);

  assert(equipped.includes('iron_pickaxe'));
});

test('mineShaft prefers iron pickaxe for ore below y64', async () => {
  let belowCleared = false;
  let waitsAfterDig = 0;
  const equipped = [];
  const position = new Vec3(0.5, 53, 0.5);
  const bot = {
    entity: {
      position,
      onGround: true,
    },
    inventory: {
      items: () => [
        { name: 'stone_pickaxe', count: 1 },
        { name: 'iron_pickaxe', count: 1 },
      ],
    },
    async equip(item) {
      equipped.push(item.name);
    },
    blockAt(pos) {
      if (pos.x !== 0 || pos.z !== 0) {
        return { name: 'air', boundingBox: 'empty', position: pos };
      }
      if (pos.y === 52 && !belowCleared) {
        return { name: 'copper_ore', boundingBox: 'block', position: pos };
      }
      if (pos.y <= 51) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.y === 52) belowCleared = true;
    },
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (belowCleared) waitsAfterDig += 1;
      if (waitsAfterDig >= 2) position.y = 52;
    },
  });

  await shaft.mineShaft(52);

  assert.equal(equipped[0], 'iron_pickaxe');
});

test('mineShaft waits for descent when already over an open air column', async () => {
  let waits = 0;
  const position = new Vec3(0.5, 62, 0.5);
  const controls = [];
  const bot = {
    entity: {
      position,
      onGround: false,
    },
    blockAt(pos) {
      if (pos.x !== 0 || pos.z !== 0 || pos.y >= 60) {
        return { name: 'air', boundingBox: 'empty', position: pos };
      }
      return { name: 'stone', boundingBox: 'block', position: pos };
    },
    setControlState(control, state) {
      controls.push([control, state]);
    },
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      waits += 1;
      if (waits >= 3) {
        position.y = 61;
        bot.entity.onGround = true;
      }
    },
  });

  const result = await shaft.mineShaft(61);

  assert.match(result, /Shaft mined 62 -> y=61/);
  assert(controls.some(([control]) => control === 'forward'));
});

test('mineShaft refuses an unsupported drop deeper than the safe fall limit', async () => {
  const position = new Vec3(0.5, 62, 0.5);
  let simulatedFatalFall = false;
  const bot = {
    entity: {
      position,
      onGround: true,
      yaw: 0,
    },
    inventory: {
      items: () => [],
    },
    blockAt(pos) {
      if (pos.x === 0 && pos.z === 0 && pos.y <= 50) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    setControlState() {},
  };
  const shaft = createMineShaft({
    bot,
    wait: async () => {
      simulatedFatalFall = true;
      position.y = 40;
      bot.entity.onGround = true;
    },
  });

  await assert.rejects(
    shaft.mineShaft(40),
    (error) => error.code === 'MINE_SHAFT_STUCK',
  );
  assert.equal(simulatedFatalFall, false);
  assert.equal(position.y, 62);
});

test('mineShaft does not dig the solid cap above a deep open cavity', async () => {
  const position = new Vec3(0.5, 62, 0.5);
  let capDug = false;
  let simulatedFatalFall = false;
  const bot = {
    entity: {
      position,
      onGround: true,
      yaw: 0,
    },
    inventory: {
      items: () => [{ name: 'stone_pickaxe', count: 1 }],
    },
    async equip() {},
    blockAt(pos) {
      if (pos.x === 0 && pos.z === 0 && pos.y === 61) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y <= 50) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.x === 0 && block.position.y === 61 && block.position.z === 0) {
        capDug = true;
      }
    },
    setControlState() {},
  };
  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (capDug) {
        simulatedFatalFall = true;
        position.y = 40;
        bot.entity.onGround = true;
      }
    },
  });

  await assert.rejects(
    shaft.mineShaft(40),
    (error) => error.code === 'MINE_SHAFT_STUCK',
  );
  assert.equal(capDug, false);
  assert.equal(simulatedFatalFall, false);
});

test('mineShaft braces a solid cap before descending over a deep cavity', async () => {
  const position = new Vec3(0.5, 62, 0.5);
  const placed = new Set();
  let capDug = false;
  const key = (pos) => `${pos.x},${pos.y},${pos.z}`;
  const bot = {
    entity: {
      position,
      onGround: true,
      yaw: 0,
    },
    inventory: {
      items: () => [
        { name: 'stone_pickaxe', count: 1 },
        { name: 'cobblestone', count: 8 },
      ],
    },
    async equip() {},
    async lookAt() {},
    blockAt(pos) {
      if (placed.has(key(pos))) {
        return { name: 'cobblestone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y === 61 && !capDug) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y <= 50) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async placeBlock(refBlock, face) {
      placed.add(key(refBlock.position.plus(face)));
    },
    async dig(block) {
      if (block.position.x === 0 && block.position.y === 61 && block.position.z === 0) {
        capDug = true;
      }
    },
    setControlState() {},
  };
  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (capDug) {
        position.y = 61;
        bot.entity.onGround = true;
      }
    },
  });

  const result = await shaft.mineShaft(61);

  assert.match(result, /Shaft mined 62 -> y=61/);
  assert.equal(capDug, true);
  assert(placed.has('0,60,0'));
});

test('mineShaft builds temporary support when suspended over a shallow air gap', async () => {
  let belowCleared = false;
  let waitsAfterDig = 0;
  const placed = new Set();
  const position = new Vec3(0.5, 95, 0.5);
  const key = (pos) => `${pos.x},${pos.y},${pos.z}`;
  const bot = {
    entity: {
      position,
      onGround: false,
    },
    inventory: {
      items: () => [
        { name: 'stone_pickaxe', count: 1 },
        { name: 'cobblestone', count: 16 },
      ],
    },
    async equip() {},
    blockAt(pos) {
      if (placed.has(key(pos))) {
        return { name: 'cobblestone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y === 94 && placed.has('0,94,0') && !belowCleared) {
        return { name: 'cobblestone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y <= 92) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.y === 94) belowCleared = true;
    },
    async placeBlock(refBlock, face) {
      placed.add(key(refBlock.position.plus(face)));
    },
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (belowCleared) waitsAfterDig += 1;
      if (waitsAfterDig >= 2) {
        position.y = 94;
        bot.entity.onGround = true;
      }
    },
  });

  await shaft.mineShaft(94);

  assert(placed.has('0,93,0'));
  assert(placed.has('0,94,0'));
});

test('mineShaft harvests a real support block before crossing an unsupported gap', async () => {
  let cobblestone = 0;
  let belowCleared = false;
  let waitsAfterDig = 0;
  const placed = new Set();
  const position = new Vec3(0.5, 70, 0.5);
  const key = (pos) => `${pos.x},${pos.y},${pos.z}`;
  const bot = {
    entity: {
      position,
      onGround: false,
      yaw: 0,
    },
    inventory: {
      items: () => [
        { name: 'wooden_pickaxe', count: 1 },
        ...(cobblestone > 0 ? [{ name: 'cobblestone', count: cobblestone }] : []),
      ],
    },
    async equip() {},
    async lookAt() {},
    blockAt(pos) {
      if (placed.has(key(pos))) {
        return { name: 'cobblestone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 1 && pos.y === 70 && pos.z === 0) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y === 69 && !belowCleared) {
        return { name: 'air', boundingBox: 'empty', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y === 67) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.x === 1 && block.position.y === 70 && block.position.z === 0) {
        cobblestone += 2;
      }
      if (block.position.x === 0 && block.position.y === 69 && block.position.z === 0) {
        belowCleared = true;
      }
    },
    async placeBlock(refBlock, face) {
      placed.add(key(refBlock.position.plus(face)));
    },
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (belowCleared) waitsAfterDig += 1;
      if (waitsAfterDig >= 2) {
        position.y = 69;
        bot.entity.onGround = true;
      }
    },
  });

  const result = await shaft.mineShaft(69);

  assert.match(result, /Shaft mined 70 -> y=69/);
  assert(placed.has('0,68,0'));
  assert(placed.has('0,69,0'));
});

test('mineShaft relocates onto a same-level supported ledge before descending', async () => {
  let lookingAtLedge = false;
  let movedToLedge = false;
  let belowCleared = false;
  let waitsAfterDig = 0;
  const position = new Vec3(0.5, 52, 0.5);
  const bot = {
    entity: {
      position,
      onGround: false,
      yaw: 0,
    },
    inventory: {
      items: () => [
        { name: 'wooden_pickaxe', count: 1 },
        { name: 'cobblestone', count: 8 },
      ],
    },
    async equip() {},
    async lookAt(target) {
      if (target.x >= 1 && target.y > 52.25) lookingAtLedge = true;
    },
    blockAt(pos) {
      if (pos.x === 1 && pos.z === 0 && pos.y === 51 && !belowCleared) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 1 && pos.z === 0 && pos.y <= 50) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.x === 1 && block.position.y === 51 && block.position.z === 0) {
        belowCleared = true;
      }
    },
    async placeBlock() {},
    pathfinder: {
      async goto(goal) {
        position.x = goal.x + 0.5;
        position.y = goal.y;
        position.z = goal.z + 0.5;
        bot.entity.onGround = true;
        movedToLedge = true;
      },
      stop() {},
    },
    setControlState(control, state) {
      if (control === 'forward' && state && lookingAtLedge && !movedToLedge) {
        movedToLedge = true;
      }
    },
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (movedToLedge && position.x < 1) {
        position.x = 1.5;
        bot.entity.onGround = true;
      }
      if (belowCleared && movedToLedge) waitsAfterDig += 1;
      if (waitsAfterDig >= 2) position.y = 51;
    },
  });

  const result = await shaft.mineShaft(51);

  assert.match(result, /Shaft mined 52 -> y=51/);
  assert.equal(movedToLedge, true);
});

test('mineShaft seals side openings while descending a vertical shaft', async () => {
  let belowCleared = false;
  let waitsAfterDig = 0;
  const placed = new Set();
  const position = new Vec3(0.5, 80, 0.5);
  const key = (pos) => `${pos.x},${pos.y},${pos.z}`;
  const bot = {
    entity: {
      position,
      onGround: true,
    },
    inventory: {
      items: () => [
        { name: 'stone_pickaxe', count: 1 },
        { name: 'cobblestone', count: 16 },
      ],
    },
    async equip() {},
    blockAt(pos) {
      if (placed.has(key(pos))) {
        return { name: 'cobblestone', boundingBox: 'block', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y === 79 && !belowCleared) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      if (pos.y <= 78) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.position.y === 79) belowCleared = true;
    },
    async placeBlock(refBlock, face) {
      placed.add(key(refBlock.position.plus(face)));
    },
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (belowCleared) waitsAfterDig += 1;
      if (waitsAfterDig >= 2) position.y = 79;
    },
  });

  await shaft.mineShaft(79);

  assert(placed.size > 0);
  assert(placed.has('1,79,0') || placed.has('-1,79,0') || placed.has('0,79,1') || placed.has('0,79,-1'));
});

test('mineShaft digs down through dirt when stair fallback has no safe step', async () => {
  let dirtCleared = false;
  let waitsAfterDig = 0;
  const position = new Vec3(-0.3, 73, 8.3);
  const bot = {
    entity: {
      position,
      onGround: true,
    },
    inventory: {
      items: () => [
        { name: 'stone_pickaxe', count: 1 },
        { name: 'cobblestone', count: 16 },
      ],
    },
    async equip() {},
    blockAt(pos) {
      if (pos.x === -1 && pos.z === 8 && pos.y === 72 && !dirtCleared) {
        return { name: 'dirt', boundingBox: 'block', position: pos };
      }
      if (pos.y <= 71) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      if (block.name === 'dirt' && block.position.y === 72) dirtCleared = true;
    },
    async placeBlock() {},
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      if (dirtCleared) waitsAfterDig += 1;
      if (waitsAfterDig >= 2) position.y = 72;
    },
  });

  const result = await shaft.mineShaft(72);

  assert.match(result, /Shaft mined 73 -> y=72/);
  assert.equal(dirtCleared, true);
});

test('mineShaft refuses to descend through a water column', async () => {
  let waits = 0;
  let digs = 0;
  const position = new Vec3(0.5, 62, 0.5);
  const bot = {
    entity: {
      position,
      onGround: true,
      yaw: 0,
    },
    inventory: {
      items: () => [
        { name: 'wooden_pickaxe', count: 1 },
        { name: 'cobblestone', count: 8 },
      ],
    },
    async equip() {},
    blockAt(pos) {
      if (pos.x === 0 && pos.z === 0 && pos.y === 61) {
        return { name: 'water', boundingBox: 'empty', position: pos };
      }
      if (pos.x === 0 && pos.z === 0 && pos.y <= 60) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig() {
      digs += 1;
    },
    async placeBlock() {},
    setControlState() {},
  };

  const shaft = createMineShaft({
    bot,
    wait: async () => {
      waits += 1;
      if (waits >= 2) position.y = 61;
    },
  });

  await assert.rejects(
    () => shaft.mineShaft(61),
    (error) => error.code === 'MINE_SHAFT_HAZARD' && /water/.test(error.message),
  );
  assert.equal(digs, 0);
});

test('mineShaft routes around a water wall without breaking its dry barrier', async () => {
  const position = new Vec3(0.5, 62, 0.5);
  let cleared = false;
  const visited = [];
  const bot = {
    entity: { position, onGround: true, yaw: 0 },
    inventory: { items: () => [{ name: 'wooden_pickaxe', count: 1 }] },
    async equip() {}, async lookAt() {},
    blockAt(pos) {
      if (pos.x >= 0 && pos.x <= 4 && pos.z === 0 && pos.y === 60) return { name: 'water', boundingBox: 'empty', position: pos };
      if (pos.x >= 0 && pos.z === 0 && pos.y <= 61 && !(cleared && pos.x === 5 && pos.y === 61)) {
        return { name: 'stone', boundingBox: 'block', position: pos };
      }
      return { name: 'air', boundingBox: 'empty', position: pos };
    },
    async dig(block) {
      assert.equal(block.position.x, 5, 'the solid roof above the aquifer must remain intact');
      cleared = true;
    },
    setControlState(_control, state) { assert.equal(state, false); },
    pathfinder: {
      async goto(goal) {
        visited.push(goal.x);
        position.x = goal.x + 0.5; position.y = goal.y; position.z = goal.z + 0.5;
      }, stop() {},
    },
  };
  const result = await createMineShaft({ bot, wait: async () => { if (cleared) position.y = 61; } }).mineShaft(61);
  assert.match(result, /Shaft mined 62 -> y=61/);
  assert.deepEqual(visited, [1, 2, 3, 4, 5]);
});

test('mineShaft exits flooded or low-air starts without excavation or blind swimming', async () => {
  for (const [feet, head, oxygen] of [['water', 'air', 20], ['air', 'water', 20], ['air', 'air', 14]]) {
    const bot = {
      entity: { position: new Vec3(0.5, 62, 0.5), onGround: true, name: 'player', metadata: { 1: oxygen * 15 } },
      registry: { entitiesByName: { player: { metadataKeys: ['shared_flags', 'air_supply'] } } },
      blockAt: pos => ({ name: pos.y === 62 ? feet : head, boundingBox: 'empty', position: pos }),
      dig: async () => assert.fail('unsafe start must not dig'),
      setControlState: (_control, enabled) => assert.equal(enabled, false),
    };
    await assert.rejects(createMineShaft({ bot, wait: async () => assert.fail('must fail promptly') }).mineShaft(16),
      error => error.code === 'MINE_SHAFT_HAZARD' && error.current_position_unsafe);
  }
});

test('mineShaft never digs a solid wall that would expose a water layer', async () => {
  const bot = {
    entity: { position: new Vec3(0.5, 80, 0.5), onGround: true },
    blockAt(pos) {
      const name = pos.x === 1 && pos.y === 79 && pos.z === 0 ? 'water'
        : pos.x === 0 && pos.z === 0 && pos.y <= 79 ? 'stone' : 'air';
      return { name, boundingBox: name === 'stone' ? 'block' : 'empty', position: pos };
    },
    dig: async () => assert.fail('must not breach the aquifer'),
    setControlState: (_control, enabled) => assert.equal(enabled, false),
  };
  await assert.rejects(createMineShaft({ bot, wait: async () => {} }).mineShaft(79), error => error.code === 'MINE_SHAFT_HAZARD');
});

test('failed supported-step navigation never enables manual forward or jump', async () => {
  const bot = {
    entity: { position: new Vec3(0.5, 62, 0.5), onGround: true },
    blockAt(pos) {
      const name = pos.x === 0 && pos.z === 0 && pos.y === 61 ? 'water'
        : pos.x === 1 && pos.z === 0 && pos.y <= 61 ? 'stone' : 'air';
      return { name, boundingBox: name === 'stone' ? 'block' : 'empty', position: pos };
    },
    pathfinder: { goto: async () => { throw new Error('No path'); }, stop() {} },
    setControlState: (_control, enabled) => assert.equal(enabled, false),
  };
  await assert.rejects(createMineShaft({ bot, wait: async () => {} }).mineShaft(61), error => error.code === 'MINE_SHAFT_HAZARD');
});
