<script>
  import { t, locale, describeError } from './i18n/index.js';
  import { onMount } from 'svelte';
  import CategorySelector from './CategorySelector.svelte';
  import CategorySelection from './CategorySelection.svelte';
  import CategoryIcon from './CategoryIcon.svelte';
  import { fetchTransactionPage } from './transactions.js';

  let {
    compact = false,
    previewLimit = 20,
    pageSize = 50,
    config,
    tags = [],
    busy = false,
    uncategorized = 0,
    formatMoney,
    onrefresh = () => refresh(),
    onclassifybatch = () => {},
    onclassify = () => {},
    onsetcategory = () => {},
    ontoggletag = () => {},
    onadd = () => {},
  } = $props();

  let transactions = $state([]);
  let search = $state('');
  let selectedCategories = $state([]);
  let selectedMacros = $state([]);
  let showAllFilterCategories = $state(false);
  let showMacroCategories = $state(false);
  let expandedCategoryIds = $state({});
  let tagFilter = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let hasMore = $state(false);
  let listLoading = $state(true);
  let error = $state('');
  let requestNumber = 0;
  let controller;
  let searchTimer;
  let filtersInitialized = false;
  let hasFilters = $derived(Boolean(search.trim() || selectedCategories.length || selectedMacros.length || tagFilter || dateFrom || dateTo));
  let dateFormat = $derived(new Intl.DateTimeFormat($locale, { day: '2-digit', month: 'short' }));

  async function loadTransactions(more = false, preserveLoaded = false) {
    if (more && listLoading) return;
    clearTimeout(searchTimer);
    controller?.abort();
    controller = new AbortController();
    const current = ++requestNumber;
    const limit = compact ? previewLimit : preserveLoaded ? Math.max(pageSize, transactions.length) : pageSize;
    listLoading = true;
    error = '';
    try {
      const result = await fetchTransactionPage(
        compact ? {} : { search, categories: selectedCategories, macroCategories: selectedMacros, tagId: tagFilter, dateFrom, dateTo },
        { limit, offset: more ? transactions.length : 0, lookAhead: !compact, signal: controller.signal },
      );
      if (current !== requestNumber) return;
      transactions = more ? [...transactions, ...result.rows] : result.rows;
      hasMore = result.hasMore;
    } catch (cause) {
      if (current === requestNumber && cause.name !== 'AbortError') error = describeError(cause);
    } finally {
      if (current === requestNumber) listLoading = false;
    }
  }

  // Keep the loaded rows visible after edits, including when several pages are open.
  export async function refresh() {
    await loadTransactions(false, true);
  }

  function clearFilters() {
    search = ''; selectedCategories = []; selectedMacros = []; tagFilter = ''; dateFrom = ''; dateTo = '';
  }

  function addCategory(category, kind) {
    if (!category) return;
    if (kind === 'macro') {
      if (!selectedMacros.includes(category)) selectedMacros = [...selectedMacros, category];
    } else if (!selectedCategories.includes(category)) {
      selectedCategories = [...selectedCategories, category];
    }
  }

  $effect(() => {
    search; selectedCategories; selectedMacros; tagFilter; dateFrom; dateTo;
    if (!filtersInitialized) { filtersInitialized = true; return; }
    controller?.abort();
    requestNumber++;
    transactions = [];
    hasMore = false;
    listLoading = true;
    error = '';
    searchTimer = setTimeout(() => loadTransactions(), 250);
    return () => clearTimeout(searchTimer);
  });

  $effect(() => {
    if (tagFilter && !tags.some((tag) => String(tag.id) === String(tagFilter))) tagFilter = '';
  });

  onMount(() => {
    loadTransactions();
    return () => { requestNumber++; controller?.abort(); clearTimeout(searchTimer); };
  });
</script>

<article class="panel transactions-panel" class:transactions-preview={compact} aria-label={compact ? $t('transactions.recent') : $t('transactions.history')}>
  <div class="panel-heading"><div><h2>{compact ? $t('transactions.recent') : $t('transactions.history')}</h2><p>{compact ? $t('transactions.preview', { count: previewLimit }) : $t('transactions.filterDescription')}</p></div><div><button class="text-button" onclick={onclassifybatch} disabled={busy || !config.ai_configured || !uncategorized}>{$t('transactions.classifyBatch')} ✳</button><button class="text-button" onclick={() => onrefresh()}>{$t('common.update')} <span>↻</span></button></div></div>
  {#if !compact}
  <div class="table-tools">
    <label class="search-field"><span>⌕</span><input aria-label={$t('transactions.search')} placeholder={$t('transactions.searchPlaceholder')} bind:value={search} /></label>
    <CategorySelector categories={config.categories} categoryGroups={config.category_groups} value="" all={showAllFilterCategories} macro={showMacroCategories} allowMacro resetOnSelect label={$t('categories.filterLabel')} placeholder={$t('categories.any')} ariaLabel={$t('categories.addFilter')} onselect={addCategory} onallchange={(checked) => { showAllFilterCategories = checked; if (checked) showMacroCategories = false; }} onmacrochange={(checked) => { showMacroCategories = checked; if (checked) showAllFilterCategories = false; }} />
    <label class="select-wrap"><span>{$t('tags.label')}</span><select bind:value={tagFilter}><option value="">{$t('common.all')}</option>{#each tags as tag}<option value={tag.id}>{tag.name}</option>{/each}</select><span class="select-arrow">⌄</span></label>
    <label class="date-filter">{$t('transactions.from')} <input aria-label={$t('transactions.start')} type="date" bind:value={dateFrom} /></label><label class="date-filter">{$t('transactions.to')} <input aria-label={$t('transactions.end')} type="date" bind:value={dateTo} /></label>
    {#if hasFilters}<button type="button" class="text-button" onclick={clearFilters}>{$t('transactions.clear')}</button>{/if}
  </div>
  <CategorySelection categories={selectedCategories} macros={selectedMacros} inset
    onremovecategory={(category) => selectedCategories = selectedCategories.filter((item) => item !== category)}
    onremovemacro={(macro) => selectedMacros = selectedMacros.filter((item) => item !== macro)}
    onclear={() => { selectedCategories = []; selectedMacros = []; }} />
  {/if}
  {#if error}<div class="flash flash-error" role="alert">{$t(error)}<button type="button" class="text-button" onclick={() => refresh()}>{$t('common.retry')}</button></div>{/if}
  {#if listLoading && !transactions.length}<div class="empty-state"><div class="loader"></div><span>{$t('transactions.loading')}</span></div>
  {:else if transactions.length === 0 && !error}<div class="empty-state"><div class="empty-illustration">↕</div><strong>{hasFilters ? $t('transactions.noResults') : $t('transactions.empty')}</strong><span>{hasFilters ? $t('transactions.adjust') : $t('transactions.getStarted')}</span>{#if hasFilters}<button class="button button-secondary" onclick={clearFilters}>{$t('transactions.clear')}</button>{:else}<button class="button button-secondary" onclick={onadd}>＋ {$t('transactions.add')}</button>{/if}</div>
  {:else if transactions.length}<div class="transaction-list" aria-busy={listLoading}>
    {#each transactions as transaction (transaction.id)}
      <article class="transaction-row">
        <CategoryIcon category={transaction.category} categoryGroups={config.category_groups} income={Number(transaction.amount) < 0} />
        <div class="transaction-info"><strong>{transaction.merchant || transaction.description}</strong><span>{transaction.description} <i>·</i> {dateFormat.format(new Date(`${transaction.date}T12:00:00`))}{transaction.classification_reason ? ` · ${$t('transactions.aiReason', { reason: transaction.classification_reason })}` : ''}</span><div class="transaction-tags">{#each transaction.tags as tag}<span class="tag-pill small">◇ {tag.name}</span>{/each}<details class="tag-picker"><summary>＋ {$t('nav.tags')}</summary><div class="tag-picker-menu">{#each tags as tag}<label><input type="checkbox" checked={transaction.tags.some((assigned) => assigned.id === tag.id)} onchange={() => ontoggletag(transaction, tag.id)} />{tag.name}</label>{:else}<span>{$t('tags.createFirst')}</span>{/each}<a href="#tags">{$t('tags.manage')} →</a></div></details></div></div>
        <div class="transaction-category"><CategorySelector categories={config.categories} categoryGroups={config.category_groups} value={transaction.category} all={Boolean(expandedCategoryIds[transaction.id])} variant="row" ariaLabel={$t('categories.transaction', { name: transaction.description })} onselect={(value) => onsetcategory(transaction, value)} onallchange={(checked) => expandedCategoryIds[transaction.id] = checked} /><small class="source-label" class:ai-source={transaction.category_source === 'ai'}>{transaction.category_source === 'pluggy' ? $t('transactions.pluggySource') : transaction.category_source === 'rule' ? $t('transactions.ruleSource') : transaction.category_source === 'ai' ? $t('transactions.aiSource', { confidence: Math.round((transaction.category_confidence || 0) * 100) }) : transaction.category_source === 'manual' ? $t('transactions.manualSource') : transaction.pending ? $t('transactions.pending') : ''}</small></div>
        <div class="transaction-amount" class:income-amount={Number(transaction.amount) < 0}>{formatMoney(Math.abs(Number(transaction.amount)), transaction.currency)}</div>
        <button class="classify-button" title={transaction.category_source === 'pluggy' ? $t('transactions.alreadyPluggy') : transaction.category_source === 'rule' ? $t('transactions.alreadyRule') : $t('transactions.classify')} onclick={() => onclassify(transaction)} disabled={busy || !config.ai_configured || ['pluggy', 'rule'].includes(transaction.category_source)}>✳</button>
      </article>
    {/each}
  </div>{/if}
  <div class="panel-footer"><span aria-live="polite">{listLoading && transactions.length ? $t('transactions.updating') : $t('transactions.showing', { count: transactions.length })}</span>{#if compact}<a class="text-button" href="#transacoes">{$t('transactions.viewAll')} <span>→</span></a>{:else if hasMore}<button class="text-button" onclick={() => loadTransactions(true)} disabled={listLoading}>{listLoading ? $t('transactions.loadingMore') : $t('transactions.loadMore')} <span>→</span></button>{:else if transactions.length}<span>{$t('transactions.listEnd')}</span>{/if}</div>
</article>
