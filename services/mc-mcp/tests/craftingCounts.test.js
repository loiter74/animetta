import test from 'node:test';
import assert from 'node:assert/strict';

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
