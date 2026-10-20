import { api } from './api.js';

// Fetch one extra row to identify the last page without an empty "load more" click.
// Large refreshes are split to respect the API's limit of 500 rows per request.
export async function fetchTransactionPage(filters = {}, { limit = 50, offset = 0, lookAhead = true, signal } = {}) {
  const rows = [];
  const requested = limit + (lookAhead ? 1 : 0);
  while (rows.length < requested) {
    const batchSize = Math.min(500, requested - rows.length);
    const query = new URLSearchParams({ limit: String(batchSize), offset: String(offset + rows.length) });
    if (filters.search?.trim()) query.set('search', filters.search.trim());
    if (filters.category) query.set('category', filters.category);
    for (const category of new Set(filters.categories || [])) query.append('categories', category);
    for (const macro of new Set(filters.macroCategories || [])) query.append('macro_categories', macro);
    if (filters.tagId) query.set('tag_id', String(filters.tagId));
    if (filters.dateFrom) query.set('date_from', filters.dateFrom);
    if (filters.dateTo) query.set('date_to', filters.dateTo);
    const batch = await api(`/api/transactions?${query}`, { signal });
    rows.push(...batch);
    if (batch.length < batchSize) break;
  }
  return { rows: rows.slice(0, limit), hasMore: lookAhead && rows.length > limit };
}
