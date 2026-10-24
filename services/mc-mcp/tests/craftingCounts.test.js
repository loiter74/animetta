import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import minecraftData from 'minecraft-data';
import injectCraft from 'mineflayer/lib/plugins/craft.js';

import { availableMaterialCount, craftOperations, WOOD_PLANK_RECIPES } from '../src/crafting/counts.js';

test('observed spruce planks bootstrap locally from eight logs without a crafting table', () => {
  const recipe = WOOD_PLANK_RECIPES.spruce_planks;
  assert.equal(recipe?.requiresTable, false);
  assert.deepEqual(recipe.ingredients, { spruce_log: 1 });
  assert.equal(craftOperations({ result: { count: 1 } }, 32, recipe.result), 8);
});

test('craftOperations prefers the known vanilla yield over an unreliable recipe yield', () => {
  const recipe = { result: { count: 1 } };

  assert.equal(craftOperations(recipe, 8, 4), 2);
});

test('craftOperations falls back to the recipe yield when no known yield exists', () => {
  const recipe = { result: { count: 4 } };

  assert.equal(craftOperations(recipe, 8), 2);
});

test('fallback material counts treat every plank type as interchangeable', () => {
  const planks = new Set(['oak_planks', 'spruce_planks', 'birch_planks']);
  const inventory = { spruce_planks: 2, birch_planks: 3 };

  assert.equal(availableMaterialCount(inventory, 'oak_planks', planks), 5);
  assert.equal(availableMaterialCount(inventory, 'stick', planks), 0);
});

function nativeCraftFixture(inventory, existingTable = null) {
  const registry = minecraftData('1.21.1');
  const stock = new Map(Object.entries(inventory).map(([name, count]) => [registry.itemsByName[name].id, count]));
  const bot = { registry, inventory: { count: id => stock.get(id) || 0 } };
  injectCraft(bot);
  const crafts = [];
  bot.craft = async (recipe, operations, table) => {
    assert.ok(!recipe.requiresTable || table);
    for (const delta of recipe.delta) {
      const count = (stock.get(delta.id) || 0) + delta.count * operations;
      assert.ok(count >= 0);
      stock.set(delta.id, count);
    }
    crafts.push({ requiresTable: recipe.requiresTable, table });
  };
  let tableLookups = 0;
  const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  const start = source.indexOf('async function _craft(');
  const end = source.indexOf('\nfunction _getRecipeIngredientNames(', start);
  assert.ok(start >= 0 && end > start);
  const craft = runInNewContext(`(${source.slice(start, end)})`, {
    bot, process: { env: {} }, FALLBACK_RECIPES: {}, craftOperations,
    getMcData: async () => registry,
    craftError: (message, code) => Object.assign(new Error(message), { code }),
    _ensureCraftingTable: async () => {
      tableLookups++;
      if (!existingTable) throw Object.assign(new Error('No local table; zero block budget'), { code: 'NO_CRAFTING_TABLE' });
      return existingTable;
    },
    presentBlockTarget: async () => null,
    _inventoryCount: name => stock.get(registry.itemsByName[name].id) || 0,
    _waitForInventoryIncrease: async (name, before, gain) => {
      assert.ok((stock.get(registry.itemsByName[name].id) || 0) - before >= gain);
    },
    _checkCraftMaterials: (recipe, count) => recipe.delta.filter(delta => (
      delta.count < 0 && (stock.get(delta.id) || 0) < -delta.count * craftOperations(recipe, count)
    )).map(delta => String(delta.id)),
    _orderRecipesForInventory: recipes => recipes,
    _reclaimCraftingTable: async () => {},
  });
  return { bot, registry, craft, crafts, get tableLookups() { return tableLookups; } };
}

test('native craft uses the installed SDK inventory recipe for flint and steel with zero block budget', async () => {
  const fixture = nativeCraftFixture({ iron_ingot: 1, flint: 1 });
  const result = await fixture.craft('flint_and_steel', 1, { budget: { max_blocks_changed: 0 } });
  assert.match(result, /Crafted 1 flint_and_steel/);
  assert.equal(fixture.tableLookups, 0);
  assert.deepEqual(fixture.crafts, [{ requiresTable: false, table: null }]);
  assert.equal(fixture.bot.inventory.count(fixture.registry.itemsByName.flint_and_steel.id), 1);
});

test('native craft keeps the workstation alternative when only its ingredients are available', async () => {
  const table = { name: 'crafting_table', position: { x: 1, y: 64, z: 0 } };
  const fixture = nativeCraftFixture({ iron_nugget: 9 }, table);
  const item = fixture.registry.itemsByName.iron_ingot.id;
  assert.ok(fixture.bot.recipesAll(item, null, null).length > 0, 'block decompression exists without its ingredient');
  assert.equal(fixture.bot.recipesFor(item, null, 1, null).length, 0);
  await fixture.craft('iron_ingot', 1, { budget: { max_blocks_changed: 0 } });
  assert.equal(fixture.tableLookups, 1);
  assert.deepEqual(fixture.crafts, [{ requiresTable: true, table }]);
  assert.equal(fixture.bot.inventory.count(item), 1);
});
