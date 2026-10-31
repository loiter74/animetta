import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import Vec3 from 'vec3';
import minecraftData from 'minecraft-data';
import BlockLoader from 'prismarine-block';
import pathfinder from 'mineflayer-pathfinder';
import { configureDryNavigation } from '../src/collection.js';

function fixture({ below = 'jungle_log', footing = 'jungle_log', fluid = false, grounded = true } = {}) {
  const registry = minecraftData('1.21.1'), Block = BlockLoader(registry), bot = new EventEmitter();
  let canopy = true;
  Object.assign(bot, { registry, game: { minY: -64, height: 384 }, entities: {},
    entity: { position: new Vec3(.5, 73, .5), onGround: grounded, effects: {} },
    inventory: { items: () => [] },
    blockAt(position) {
      const p = position.floored(), center = p.x === 0 && p.z === 0;
      let name = canopy && center && p.y === 72 ? 'jungle_leaves'
        : canopy && p.x === 1 && p.z === 0 && p.y === 72 ? 'jungle_log'
          : center && p.y === 71 ? footing : center && p.y === 70 ? below
            : fluid && p.x === 1 && p.z === 0 && p.y === 71 ? 'water' : 'air';
      if (name === null) return null;
      const block = name.endsWith('_leaves')
        ? Block.fromProperties(registry.blocksByName[name].id, { distance: 1, persistent: false }, 0)
        : Block.fromStateId(registry.blocksByName[name].defaultState, 0);
      block.position = p;
      return block;
    },
  });
  pathfinder.pathfinder(bot);
  const movements = configureDryNavigation(new pathfinder.Movements(bot), bot);
  // Match R72's transition from an observed canopy onto a two-log column.
  canopy = false;
  bot.entity.position = new Vec3(.5, 72, .5);
  const route = () => {
    let result;
    for (const planned of bot.pathfinder.getPathFromTo(movements, bot.entity.position,
      new pathfinder.goals.GoalBlock(0, 71, 0))) {
      result = planned.result;
      if (result.status !== 'partial') break;
    }
    return result;
  };
  return { bot, movements, route };
}

test('a canopy-origin navigation can lower solid footing onto one known full stable block', () => {
  for (const below of ['jungle_log', 'stone', 'dirt']) {
    const f = fixture({ below }), result = f.route();
    assert.equal(result.status, 'success', below);
    assert.equal(result.path.length, 1);
    assert.equal(result.path[0].y, 71);
    assert.deepEqual(result.path[0].toBreak.map(p => [p.x, p.y, p.z]), [[0, 71, 0]]);
    assert.deepEqual(result.path[0].toPlace, []);
    assert.equal(f.movements.maxDropDown, 2);
  }
});

test('footing descent still rejects a hole, fluids, temporary or partial support', () => {
  for (const below of [null, 'air', 'water', 'lava', 'jungle_leaves', 'sand', 'gravel',
    'white_concrete_powder', 'suspicious_sand', 'magma_block', 'stone_slab']) {
    assert.equal(fixture({ below }).route().status, 'noPath', String(below));
  }
});

test('canopy leaf footing remains protected even above known solid ground', () => {
  assert.equal(fixture({ footing: 'jungle_leaves', below: 'stone' }).route().status, 'noPath');
});

test('footing planning survives a transient falling tick and does not open adjacent fluid', () => {
  assert.equal(fixture({ grounded: false }).route().status, 'success');
  assert.equal(fixture({ fluid: true }).route().status, 'noPath');
});
