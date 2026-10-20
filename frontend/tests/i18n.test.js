import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { get } from 'svelte/store';
import { catalogs, categoryName, currencyText, describeError, message, resolveLocale, storageKey, translate } from '../src/i18n/core.js';
import { categoryLabel, date, initializeI18n, locale, setLocale, t, toggleLocale } from '../src/i18n/index.js';
import { fetchTransactionPage } from '../src/transactions.js';
import { renderComponent } from './render-svelte.js';

test('catalogs have matching keys, plural forms and interpolation parameters', () => {
  assert.deepEqual(Object.keys(catalogs['pt-BR']).sort(), Object.keys(catalogs['en-US']).sort());
  function placeholders(value) { return [...value.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort(); }
  for (const [key, portuguese] of Object.entries(catalogs['pt-BR'])) {
    if (key === 'categoryNames') continue;
    const english = catalogs['en-US'][key];
    if (typeof portuguese === 'object') {
      assert.deepEqual(Object.keys(portuguese), Object.keys(english), key);
      for (const form of Object.keys(portuguese)) assert.deepEqual(placeholders(portuguese[form]), placeholders(english[form]), `${key}.${form}`);
    } else assert.deepEqual(placeholders(portuguese), placeholders(english), key);
  }
});

test('all Pluggy categories and group names have both translations', () => {
  const source = readFileSync(new URL('../../backend/app/categories.py', import.meta.url), 'utf8').split('CATEGORY_GROUPS:')[1].split('\nCATEGORIES =')[0];
  const canonical = [...new Set([...source.matchAll(/"([^"]+)"/g)].map((match) => match[1]))].sort();
  assert.equal(canonical.length, 134);
  for (const language of ['pt-BR', 'en-US']) {
    assert.deepEqual(Object.keys(catalogs[language].categoryNames).sort(), canonical);
    for (const name of canonical) assert.ok(categoryName(language, name).length, name);
  }
  assert.equal(categoryName('pt-BR', 'Food delivery'), 'Entrega de refeições');
  assert.equal(categoryName('en-US', 'Food delivery'), 'Food delivery');
  assert.equal(categoryName('pt-BR', 'Future provider category'), 'Future provider category');
});

test('every literal UI translation key exists in both catalogs', () => {
  function files(directory) {
    return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => entry.isDirectory() ? files(new URL(`${entry.name}/`, directory)) : entry.name.endsWith('.svelte') ? [new URL(entry.name, directory)] : []);
  }
  for (const file of files(new URL('../src/', import.meta.url))) {
    for (const [, key] of readFileSync(file, 'utf8').matchAll(/\$t\('([^']+)'(?=\s*[,\)])/g)) {
      for (const language of ['pt-BR', 'en-US']) assert.ok(key in catalogs[language], `${file}: ${key}`);
    }
  }
});

test('locale resolution respects saved choices and safely falls back', () => {
  assert.equal(resolveLocale('pt-BR', 'en-US'), 'pt-BR');
  assert.equal(resolveLocale('en-US', 'pt-BR'), 'en-US');
  assert.equal(resolveLocale('invalid', 'en-GB'), 'en-US');
  assert.equal(resolveLocale(null, 'fr-FR'), 'pt-BR');
});

test('the language toggle persists the choice and updates reactive labels and document language', () => {
  const originals = Object.fromEntries(['document', 'localStorage'].map((name) => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  const storage = new Map();
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { setItem: (key, value) => storage.set(key, value) } });
  Object.defineProperty(globalThis, 'document', { configurable: true, value: { documentElement: { lang: '' } } });
  const unsubscribe = initializeI18n();
  try {
    setLocale('pt-BR');
    toggleLocale();
    assert.equal(get(locale), 'en-US');
    assert.equal(storage.get(storageKey), 'en-US');
    assert.equal(document.documentElement.lang, 'en-US');
    assert.equal(get(t)('nav.home'), 'Home');
    assert.equal(get(categoryLabel)('Groceries'), 'Groceries');
    toggleLocale();
    assert.equal(document.documentElement.lang, 'pt-BR');
    assert.equal(get(t)('nav.home'), 'Início');
    assert.equal(get(categoryLabel)('Groceries'), 'Supermercado');
    setLocale('unsupported');
    assert.equal(get(locale), 'pt-BR');
  } finally {
    unsubscribe();
    for (const [name, descriptor] of Object.entries(originals)) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor); else delete globalThis[name];
    }
  }
});

test('pluralization, numbers, dates and BRL formatting follow the selected language', () => {
  assert.equal(translate('pt-BR', 'counts.transactions', { count: 0 }), '0 transações');
  assert.equal(translate('pt-BR', 'counts.transactions', { count: 1 }), '1 transação');
  assert.equal(translate('en-US', 'counts.transactions', { count: 2 }), '2 transactions');
  assert.match(currencyText('pt-BR', 1234.56), /1\.234,56/);
  assert.match(currencyText('en-US', 1234.56), /1,234\.56/);
  assert.match(currencyText('en-US', 1234.56), /R\$/);
  for (const language of ['pt-BR', 'en-US']) assert.doesNotMatch(currencyText(language, 1234.56, { hidden: true }), /1234|1[.,]234/);
  setLocale('pt-BR');
  assert.match(get(date)(new Date('2026-10-20T12:00:00'), { month: 'long' }), /outubro/);
  setLocale('en-US');
  assert.match(get(date)(new Date('2026-10-20T12:00:00'), { month: 'long' }), /October/);
});

test('notices and known API errors can be translated after they were received', () => {
  const notice = message('notice.imported', { count: 1 });
  assert.equal(translate('pt-BR', notice), '1 nova transação importada.');
  assert.equal(translate('en-US', notice), '1 new transaction imported.');
  const error = describeError('A Pluggy falhou ao consultar transactions (HTTP 410).');
  assert.equal(translate('en-US', error), 'Pluggy failed to fetch transactions (HTTP 410).');
  assert.equal(translate('en-US', describeError('Já existe uma tag com esse nome.')), 'A tag with this name already exists.');
  assert.equal(translate('en-US', describeError([{ msg: 'Field required' }], 422)), 'Check the entered data and try again.');
});

test('localized category labels never replace canonical IDs in API queries', async (context) => {
  const requests = [];
  context.mock.method(globalThis, 'fetch', async (path) => { requests.push(new URL(path, 'http://localhost')); return Response.json([]); });
  for (const language of ['pt-BR', 'en-US']) {
    setLocale(language);
    await fetchTransactionPage({ categories: ['Food delivery'], macroCategories: ['Travel'] });
  }
  for (const request of requests) {
    assert.deepEqual(request.searchParams.getAll('categories'), ['Food delivery']);
    assert.deepEqual(request.searchParams.getAll('macro_categories'), ['Travel']);
  }
});

test('real selectors, chips, home widgets and dashboards render in both languages', async () => {
  const config = { categories: ['Groceries', 'Food delivery', 'Eating out'], category_groups: [{ name: 'Food and drinks', categories: ['Food delivery', 'Eating out'] }], ai_configured: false, pluggy_configured: true };
  const formatMoney = (value) => currencyText(get(locale), value);
  for (const language of ['pt-BR', 'en-US']) {
    setLocale(language);
    const selector = (await renderComponent('CategorySelector.svelte', { categories: config.categories, categoryGroups: config.category_groups, all: true })).body;
    const category = categoryName(language, 'Food delivery');
    assert.match(selector, new RegExp(`value="Food delivery"[^>]*>${category}`));
    assert.match(selector, new RegExp(`label="${categoryName(language, 'Food and drinks')}"`));
    const chips = (await renderComponent('CategorySelection.svelte', { categories: ['Food delivery'], macros: ['Food and drinks'] })).body;
    assert.ok(chips.includes(category));
    assert.ok(chips.includes(translate(language, 'categories.clear')));
    const home = (await renderComponent('HomePage.svelte', { config, connections: [], summary: { month: '2026-10', categories: [{ category: 'Groceries', amount: '100' }], transaction_count: 1 }, recurring: [], tags: [], formatMoney })).body;
    assert.ok(home.includes(translate(language, 'home.title')));
    assert.ok(home.includes(translate(language, 'transactions.preview', { count: 20 })));
    assert.ok(home.includes(categoryName(language, 'Groceries')));
    const table = (await renderComponent('TransactionsTable.svelte', { config, formatMoney })).body;
    assert.ok(table.includes(translate(language, 'transactions.searchPlaceholder')));
    const dashboard = (await renderComponent('AnalyticsPage.svelte')).body;
    assert.ok(dashboard.includes(translate(language, 'analytics.title')));
    const toggle = (await renderComponent('LocaleToggle.svelte')).body;
    assert.ok(toggle.includes(language === 'pt-BR' ? '/flags/br.svg' : '/flags/us.svg'));
    assert.doesNotMatch(toggle, /🇧🇷|🇺🇸/);
  }
});
