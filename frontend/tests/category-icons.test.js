import test from 'node:test';
import assert from 'node:assert/strict';
import { categoryIconConfig, categoryIconPaths, resolveCategoryIcon } from '../src/categoryIcons.js';
import { locale, setLocale } from '../src/i18n/index.js';
import { get } from 'svelte/store';
import { renderComponent } from './render-svelte.js';

test('all icon mappings refer to existing artwork', () => {
  for (const name of [categoryIconConfig.fallback, ...Object.values(categoryIconConfig.groups), ...Object.values(categoryIconConfig.categories)]) {
    assert.ok(categoryIconPaths[name]?.length, name);
  }
});

test('specific categories override their group icon and other children inherit the group', () => {
  const groups = [
    { name: 'Food and drinks', categories: ['Food and drinks', 'Food delivery', 'Eating out'] },
    { name: 'Travel', categories: ['Travel', 'Accommodation', 'Mileage programs'] },
  ];
  assert.equal(resolveCategoryIcon('Groceries', groups), 'basket');
  assert.equal(resolveCategoryIcon('Food delivery', groups), 'delivery');
  assert.equal(resolveCategoryIcon('Eating out', groups), 'utensils');
  assert.equal(resolveCategoryIcon('Accommodation', groups), 'bed');
  assert.equal(resolveCategoryIcon('Mileage programs', groups), 'plane');
  assert.equal(resolveCategoryIcon('Travel', groups), 'plane');
});

test('unknown or disabled category icons keep the generic mark', () => {
  assert.equal(resolveCategoryIcon('New category'), 'default');
  assert.equal(resolveCategoryIcon('Uncategorized'), 'default');
  assert.equal(resolveCategoryIcon('Other'), 'default');
  assert.equal(resolveCategoryIcon('Groceries', [], false), 'default');
});

test('the shared icon renders vector paths and a localized tooltip without changing category IDs', async () => {
  const previous = get(locale);
  try {
    for (const language of ['pt-BR', 'en-US']) {
      setLocale(language);
      const icon = (await renderComponent('CategoryIcon.svelte', { category: 'Groceries' })).body;
      assert.ok(icon.includes(categoryIconPaths.basket[0]));
      assert.match(icon, /<svg[^>]*aria-hidden="true"/);
      assert.match(icon, /stroke="currentColor"/);
      assert.ok(icon.includes(language === 'pt-BR' ? 'title="Supermercado"' : 'title="Groceries"'));
      assert.doesNotMatch(icon, /◒|⌂|🛒|🛍/);
    }
    const fallback = (await renderComponent('CategoryIcon.svelte', { category: 'Groceries', enabled: false, income: true })).body;
    assert.ok(fallback.includes(categoryIconPaths.default[0]));
    assert.match(fallback, /class="merchant-icon income"/);
  } finally {
    setLocale(previous);
  }
});
