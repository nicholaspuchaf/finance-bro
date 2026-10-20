import test from 'node:test';
import assert from 'node:assert/strict';
import { fetchTransactionPage } from '../src/transactions.js';

function transactionSource(t, count) {
  const rows = Array.from({ length: count }, (_, id) => ({ id: id + 1 }));
  const requests = [];
  t.mock.method(globalThis, 'fetch', async (path, options) => {
    options.signal?.throwIfAborted();
    const query = new URL(path, 'http://localhost').searchParams;
    requests.push({ query, signal: options.signal });
    const offset = Number(query.get('offset'));
    const limit = Number(query.get('limit'));
    assert.ok(limit <= 500);
    return Response.json(rows.slice(offset, offset + limit));
  });
  return { rows, requests };
}

test('home fetches only the latest 20 rows without enabling pagination', async (t) => {
  const { requests } = transactionSource(t, 120);
  const page = await fetchTransactionPage({}, { limit: 20, lookAhead: false });
  assert.deepEqual(page.rows.map((row) => row.id), Array.from({ length: 20 }, (_, id) => id + 1));
  assert.equal(page.hasMore, false);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].query.get('limit'), '20');
  assert.equal(requests[0].query.get('offset'), '0');
});

for (const count of [0, 15, 50, 51, 100, 101]) {
  test(`pagination of ${count} transactions has no missing or duplicated rows`, async (t) => {
    const { rows, requests } = transactionSource(t, count);
    const loaded = [];
    let page;
    do {
      page = await fetchTransactionPage({}, { limit: 50, offset: loaded.length });
      loaded.push(...page.rows);
    } while (page.hasMore);
    assert.deepEqual(loaded, rows);
    assert.equal(requests.length, Math.max(1, Math.ceil(count / 50)));
  });
}

test('loading more keeps search, category, tag and date filters in the query', async (t) => {
  const { requests } = transactionSource(t, 140);
  const controller = new AbortController();
  const filters = { search: '  Mercado  ', categories: ['Food delivery', 'Eating out', 'Food delivery'], macroCategories: ['Travel'], tagId: 7, dateFrom: '2026-10-01', dateTo: '2026-10-20' };
  const first = await fetchTransactionPage(filters, { signal: controller.signal });
  await fetchTransactionPage(filters, { offset: first.rows.length, signal: controller.signal });
  assert.deepEqual(requests.map(({ query }) => query.get('offset')), ['0', '50']);
  for (const { query, signal } of requests) {
    assert.equal(query.get('search'), 'Mercado');
    assert.deepEqual(query.getAll('categories'), ['Food delivery', 'Eating out']);
    assert.deepEqual(query.getAll('macro_categories'), ['Travel']);
    assert.equal(query.get('tag_id'), '7');
    assert.equal(query.get('date_from'), '2026-10-01');
    assert.equal(query.get('date_to'), '2026-10-20');
    assert.equal(signal, controller.signal);
  }
});

test('clearing the selection omits category and macro filters from the next request', async (t) => {
  const { requests } = transactionSource(t, 100);
  await fetchTransactionPage({ categories: ['Food delivery'], macroCategories: ['Travel'] });
  await fetchTransactionPage({ categories: [], macroCategories: [] });
  assert.equal(requests[1].query.has('categories'), false);
  assert.equal(requests[1].query.has('macro_categories'), false);
  assert.equal(requests[1].query.get('offset'), '0');
});

test('refreshing a long list preserves all loaded rows and respects the API limit', async (t) => {
  const { requests, rows } = transactionSource(t, 1001);
  const refreshed = await fetchTransactionPage({ category: 'Groceries' }, { limit: 1000 });
  assert.deepEqual(refreshed.rows, rows.slice(0, 1000));
  assert.equal(refreshed.hasMore, true);
  assert.deepEqual(requests.map(({ query }) => [query.get('offset'), query.get('limit')]), [['0', '500'], ['500', '500'], ['1000', '1']]);
  assert.ok(requests.every(({ query }) => query.get('category') === 'Groceries'));
});

test('API errors are reported instead of appearing as an empty page', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'Período inválido.' }, { status: 422 }));
  await assert.rejects(fetchTransactionPage(), /Período inválido/);
});

test('requests can be cancelled when filters change or the table is unmounted', async (t) => {
  const { requests } = transactionSource(t, 100);
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(fetchTransactionPage({}, { signal: controller.signal }), { name: 'AbortError' });
  assert.equal(requests.length, 0);
});
