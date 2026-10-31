import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import BlockLoader from 'prismarine-block';
import pathfinder from 'mineflayer-pathfinder';
import { configureDryNavigation } from '../src/collection.js';

function fixture(landing = 'stone') {
  const registry = minecraftData('1.21'), Block = BlockLoader(registry), bot = new EventEmitter();
  Object.assign(bot, { registry, game: { minY: -64, height: 384 },
    entity: { position: new Vec3(.5, 64, .5), effects: {} },
    inventory: { items: () => [] }, entities: {},
    blockAt(position) {
      const p = position.floored(), diagonal = p.x === 1 && p.z === 1;
      const name = diagonal && p.y === 62 ? landing
        : diagonal && p.y === 63 ? landing === 'water' ? 'water' : 'air'
          : p.y < 64 ? 'stone' : 'air';
      if (name === null) return null;
      const block = Block.fromStateId(registry.blocksByName[name].defaultState, 0);
      block.position = p;
      return block;
    },
  });
  pathfinder.pathfinder(bot);
  const movements = configureDryNavigation(new pathfinder.Movements(bot), bot);
  const admitted = () => movements.getNeighbors({ x: 0, y: 64, z: 0, remainingBlocks: 0 })
    .some(move => move.x === 1 && move.y === 63 && move.z === 1);
  return { bot, movements, admitted, Block };
}

for (const landing of ['oak_leaves', 'water', null]) {
  test(`native diagonal descent rejects the actual unsafe landing: ${landing}`, () => {
    const { bot, movements, admitted } = fixture(landing);
    if (landing !== null) assert.equal(movements.exclusionStep(bot.blockAt(new Vec3(1, 63, 1))), Infinity);
    assert.equal(admitted(), false);
    assert.equal(movements.maxDropDown, 2);
  });
}

test('native diagonal descent retains a safe solid one-block landing', () => {
  const { movements, admitted } = fixture('stone');
  assert.equal(admitted(), true);
  assert.equal(movements.allowParkour, false);
  assert.equal(movements.allowSprinting, false);
});

test('a caller landing exclusion also applies to native diagonal descent', () => {
  const { movements, admitted } = fixture();
  assert.equal(admitted(), true);
  movements.exclusionAreasStep.push(block => block.position.equals(new Vec3(1, 63, 1)) ? Infinity : 0);
  assert.equal(admitted(), false);
});

test('installed SDK keeps a complete supported canopy descent to ordinary ground', () => {
  const { bot, Block } = fixture();
  bot.entity.position = new Vec3(.5, 68, .5);
  bot.blockAt = position => {
    const p = position.floored();
    const step = p.x === p.z && p.x >= 0 && p.x <= 4 && p.y === 67 - p.x;
    const name = p.y <= 62 || step && p.x === 4 ? 'stone' : step ? 'oak_leaves' : 'air';
    const block = step && p.x < 4
      ? Block.fromProperties(bot.registry.blocksByName.oak_leaves.id, { distance: 1, persistent: false }, 0)
      : Block.fromStateId(bot.registry.blocksByName[name].defaultState, 0);
    block.position = p;
    return block;
  };
  const movements = configureDryNavigation(new pathfinder.Movements(bot), bot);
  movements.canDig = false;
  movements.allow1by1towers = false;
  let result;
  for (const planned of bot.pathfinder.getPathFromTo(movements, bot.entity.position,
    new pathfinder.goals.GoalBlock(4, 64, 4))) {
    result = planned.result;
    if (result.status !== 'partial') break;
  }
  assert.equal(result.status, 'success');
  assert.ok(result.path.length >= 4);
  let previousY = 68;
  for (const move of result.path) {
    assert.ok(previousY - move.y <= 1);
    assert.deepEqual(move.toBreak, []);
    assert.deepEqual(move.toPlace, []);
    previousY = move.y;
  }
});
