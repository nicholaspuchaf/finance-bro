<script>
  import { t, locale, categoryLabel, currency, number, describeError } from './i18n/index.js';
  import TrendChart from './TrendChart.svelte';
  import CategorySelector from './CategorySelector.svelte';
  import CategorySelection from './CategorySelection.svelte';
  import './analytics.css';
  import { api } from './api.js';

  let { hideAmounts = false, tags = [], categories = [], categoryGroups = [] } = $props();
  let mode = $state('expenses');
  let months = $state(1);
  let selectedMonth = $state('');
  let selectedCategories = $state([]);
  let selectedMacros = $state([]);
  let selectedTagIds = $state([]);
  let showAllCategories = $state(false);
  let showMacroCategories = $state(false);
  let monthlyChart = $state('area');
  let dailyChart = $state('bar');
  let dailyView = $state('daily');
  let analysis = $state(null);
  let loading = $state(true);
  let error = $state('');
  let requestNumber = 0;
  const palette = ['#df826c', '#8d81cb', '#5fae91', '#e2af61', '#72a5cb', '#b4a7bd'];

  async function loadAnalysis() {
    const current = ++requestNumber;
    const query = new URLSearchParams({ mode, months: String(months) });
    if (selectedMonth) query.set('month', selectedMonth);
    for (const category of selectedCategories) query.append('categories', category);
    for (const category of selectedMacros) query.append('macro_categories', category);
    for (const tagId of selectedTagIds) query.append('tag_ids', String(tagId));
    loading = true;
    error = '';
    try {
      const result = await api(`/api/analytics?${query}`, { cache: 'no-store' });
      if (current === requestNumber) analysis = result;
    } catch (cause) {
      if (current === requestNumber) error = describeError(cause);
    } finally {
      if (current === requestNumber) loading = false;
    }
  }

  $effect(() => {
    mode; months; selectedMonth; selectedCategories; selectedMacros; selectedTagIds;
    loadAnalysis();
  });

  function chooseMode(next) {
    mode = next;
    selectedCategories = [];
    selectedMacros = [];
    showAllCategories = false;
  }

  function toggleCategory(category) {
    selectedCategories = selectedCategories.includes(category)
      ? selectedCategories.filter((item) => item !== category)
      : [...selectedCategories, category];
  }

  function toggleMacro(category) {
    selectedMacros = selectedMacros.includes(category)
      ? selectedMacros.filter((item) => item !== category)
      : [...selectedMacros, category];
  }

  function addCategory(category, kind) {
    if (!category) return;
    if (kind === 'macro') {
      if (!selectedMacros.includes(category)) selectedMacros = [...selectedMacros, category];
    } else if (!selectedCategories.includes(category)) {
      selectedCategories = [...selectedCategories, category];
    }
  }

  function toggleTag(tagId) {
    selectedTagIds = selectedTagIds.includes(tagId)
      ? selectedTagIds.filter((id) => id !== tagId)
      : [...selectedTagIds, tagId];
  }

  function chooseMonths(value) {
    if (months === value) return;
    selectedMonth = analysis?.monthly?.at(-1)?.month || '';
    months = value;
  }

  function money(value) {
    return $currency(value, { hidden: hideAmounts });
  }

  function monthName(value, year = false) {
    if (!value) return '—';
    return new Intl.DateTimeFormat($locale, { month: 'short', ...(year ? { year: 'numeric' } : {}) }).format(new Date(`${value.slice(0, 7)}-02T12:00:00`));
  }

  let monthlyPoints = $derived((analysis?.monthly || []).map((item) => ({ label: monthName(item.month), value: Number(item.amount) })));
  let dailyPoints = $derived.by(() => {
    let running = 0;
    return (analysis?.daily || []).map((item) => {
      running += Number(item.amount);
      return { label: item.date.slice(-2), value: dailyView === 'cumulative' ? running : Number(item.amount) };
    });
  });
  let total = $derived(Number(analysis?.total || 0));
  let overallTotal = $derived((analysis?.categories || []).reduce((sum, item) => sum + Number(item.amount), 0));
  let selectedMonthTotal = $derived((analysis?.daily || []).reduce((sum, item) => sum + Number(item.amount), 0));
  let peakMonth = $derived((analysis?.monthly || []).reduce((best, item) => Number(item.amount) > Number(best?.amount || 0) ? item : best, null));
  let peakDay = $derived((analysis?.daily || []).reduce((best, item) => Number(item.amount) > Number(best?.amount || 0) ? item : best, null));
  let topCategories = $derived((analysis?.categories || []).slice(0, 5));
  let categorySelectionCount = $derived(selectedCategories.length + selectedMacros.length);
  let categorySelectionLabel = $derived(categorySelectionCount === 0 ? $t('categories.all') : categorySelectionCount === 1 ? $categoryLabel(selectedMacros[0] || selectedCategories[0]) : $t('categories.combined', { count: categorySelectionCount }));
  let selectedTags = $derived(tags.filter((tag) => selectedTagIds.includes(tag.id)));
  let tagSelectionLabel = $derived(selectedTags.length === 0 ? $t('tags.all') : selectedTags.length === 1 ? selectedTags[0].name : $t('tags.combined', { count: selectedTags.length }));
  let donutGradient = $derived.by(() => {
    if (!overallTotal) return 'conic-gradient(#edeaf0 0 100%)';
    let progress = 0;
    const stops = topCategories.map((item, index) => {
      const start = progress;
      progress += Number(item.amount) / overallTotal * 100;
      return `${palette[index]} ${start}% ${progress}%`;
    });
    if (progress < 100) stops.push(`${palette[5]} ${progress}% 100%`);
    return `conic-gradient(${stops.join(',')})`;
  });
</script>

<div class="page-content analytics-page">
  <div class="analytics-heading">
    <div><span class="analytics-eyebrow">✳ &nbsp; {$t('analytics.eyebrow')}</span><h1>{$t('analytics.title')}</h1><p>{$t('analytics.subtitle')}</p></div>
    <a class="analytics-back" href="#transacoes">{$t('transactions.view')} <span>↗</span></a>
  </div>

  <div class="analytics-toolbar">
    <div class="analytics-segment" role="group" aria-label={$t('analytics.mode')}>
      <button type="button" class:active={mode === 'expenses'} aria-pressed={mode === 'expenses'} onclick={() => chooseMode('expenses')}>↗ &nbsp; {$t('analytics.expenses')}</button>
      <button type="button" class:active={mode === 'investments'} aria-pressed={mode === 'investments'} onclick={() => chooseMode('investments')}>◈ &nbsp; {$t('analytics.investments')}</button>
    </div>
    <div class="analytics-filters">
      <CategorySelector {categories} {categoryGroups} value="" all={showAllCategories} macro={showMacroCategories} allowMacro resetOnSelect label={$t('categories.filterLabel')} placeholder={$t('categories.any')} ariaLabel={$t('categories.addAnalysis')} onselect={addCategory} onallchange={(checked) => { showAllCategories = checked; if (checked) showMacroCategories = false; }} onmacrochange={(checked) => { showMacroCategories = checked; if (checked) showAllCategories = false; }} />
      <details class="analytics-category-picker analytics-tag-picker"><summary><span>{$t('nav.tags')}</span><strong>{tagSelectionLabel}</strong><i aria-hidden="true">⌄</i></summary><div class="analytics-category-menu"><div class="analytics-category-menu-head"><strong>{$t('tags.filter')}</strong></div><p>{$t('tags.filterHelp')}</p><div class="analytics-category-options" role="group" aria-label={$t('tags.aggregate')}>{#each tags as tag}<label><input type="checkbox" checked={selectedTagIds.includes(tag.id)} onchange={() => toggleTag(tag.id)} /><span>{tag.name}</span><small>{tag.transaction_count}</small></label>{:else}<span class="analytics-no-categories">{$t('tags.filterEmpty')}</span>{/each}</div><div class="analytics-category-menu-foot"><button type="button" onclick={() => selectedTagIds = []} disabled={!selectedTagIds.length}>{$t('common.clear')}</button><button type="button" onclick={(event) => event.currentTarget.closest('details').open = false}>{$t('common.done')}</button></div></div></details>
      <div class="analytics-period-control"><div class="analytics-period-heading"><span>{$t('common.period')}</span><output aria-live="polite">{months === 1 ? $t('common.currentMonth') : $t('analytics.lastMonths', { count: months })}</output></div><div class="analytics-period-options" role="group" aria-label={$t('analytics.period')}>{#each [1, 3, 6, 12, 24] as option}<button type="button" class:active={months === option} aria-pressed={months === option} onclick={() => chooseMonths(option)}>{months === option ? '✓ ' : ''}{option} {option === 1 ? $t('common.month') : $t('common.months')}</button>{/each}</div></div>
    </div>
  </div>
  <CategorySelection categories={selectedCategories} macros={selectedMacros} label={$t('analytics.aggregating')} onremovecategory={toggleCategory} onremovemacro={toggleMacro} onclear={() => { selectedCategories = []; selectedMacros = []; }} />
  {#if selectedTags.length}<div class="analytics-selected-categories analytics-tag-selection" aria-label={$t('tags.selected')}><span>{$t('nav.tags')}</span>{#each selectedTags as tag}<button type="button" aria-label={$t('tags.remove', { name: tag.name })} onclick={() => toggleTag(tag.id)}>{tag.name} <b aria-hidden="true">×</b></button>{/each}<button type="button" class="clear-selected" onclick={() => selectedTagIds = []}>{$t('tags.clear')}</button></div>{/if}

  {#if error}<div class="analytics-error" role="alert">{$t(error)} <button type="button" onclick={loadAnalysis}>{$t('common.retry')}</button></div>{/if}
  {#if loading && !analysis}<div class="analytics-loading" role="status"><div class="loader"></div> {$t('analytics.preparing')}</div>
  {:else if analysis}
    {#if loading}<div class="analytics-updating" role="status"><div class="loader"></div> {$t('analytics.updating')}</div>{/if}
    <div class="analytics-hero">
      <div class="analytics-hero-copy"><span class="analytics-kicker">{mode === 'expenses' ? $t('analytics.totalExpenses') : $t('analytics.totalInvestments')} · {categorySelectionLabel.toUpperCase()}{selectedTags.length ? ` · ${tagSelectionLabel.toUpperCase()}` : ''}</span><strong>{money(total)}</strong><span class="analytics-hero-period">{analysis.months === 1 ? $t('common.currentMonth') : $t('analytics.lastMonths', { count: analysis.months })} <i>·</i> {monthName(analysis.period_start, true)} — {monthName(analysis.period_end, true)} <i>·</i> {$t('counts.entries', { count: analysis.count })}</span></div>
      <div class="analytics-hero-mark" aria-hidden="true">{mode === 'expenses' ? '↗' : '◈'}</div>
    </div>

    <div class="analytics-stat-grid">
      <article class="analytics-stat"><span>{$t('analytics.average')}</span><strong>{money(total / months)}</strong><small>{$t('analytics.monthsAverage', { count: months })}</small></article>
      <article class="analytics-stat"><span>{$t('analytics.peakMonth')}</span><strong>{peakMonth && Number(peakMonth.amount) ? money(peakMonth.amount) : '—'}</strong><small>{peakMonth && Number(peakMonth.amount) ? monthName(peakMonth.month, true) : $t('analytics.noEntries')}</small></article>
      <article class="analytics-stat"><span>{mode === 'expenses' ? $t('analytics.activeCategories') : $t('analytics.inflows')}</span><strong>{mode === 'expenses' ? $number(analysis.categories.length) : money(analysis.inflows)}</strong><small>{mode === 'expenses' ? $t('analytics.currentSelection') : $t('analytics.withdrawals')}</small></article>
      <article class="analytics-stat"><span>{$t('analytics.transactions')}</span><strong>{$number(analysis.count)}</strong><small>{$t('analytics.confirmed')}</small></article>
    </div>

    <div class="analytics-main-grid">
      <section class="analytics-card analytics-trend-panel" aria-labelledby="monthly-title">
        <div class="analytics-card-top"><div><span class="analytics-section-kicker">{$t('analytics.wide')}</span><h2 id="monthly-title">{$t('analytics.monthly')}</h2><p>{mode === 'expenses' ? $t('analytics.monthlySpending') : $t('analytics.monthlyInvesting')}{categorySelectionCount ? ` · ${categorySelectionLabel}` : ''}</p></div><div class="chart-switch" role="group" aria-label={$t('analytics.monthlyChart')}><button type="button" class:active={monthlyChart === 'bar'} aria-label={$t('analytics.bar')} aria-pressed={monthlyChart === 'bar'} title={$t('analytics.bar')} onclick={() => monthlyChart = 'bar'}>▥</button><button type="button" class:active={monthlyChart === 'line'} aria-label={$t('analytics.line')} aria-pressed={monthlyChart === 'line'} title={$t('analytics.line')} onclick={() => monthlyChart = 'line'}>⌁</button><button type="button" class:active={monthlyChart === 'area'} aria-label={$t('analytics.area')} aria-pressed={monthlyChart === 'area'} title={$t('analytics.area')} onclick={() => monthlyChart = 'area'}>◢</button></div></div>
        {#if total}<div class="analytics-chart-scroll"><TrendChart points={monthlyPoints} type={monthlyChart} accent={mode === 'expenses' ? '#db806a' : '#8877c6'} id="monthly-fill" {hideAmounts} label={$t('analytics.monthlyLabel')} /></div>{:else}<div class="analytics-empty">{$t(mode === 'expenses' ? 'analytics.noExpenses' : 'analytics.noInvestments')}<span>{$t('analytics.tryPeriod')}</span></div>{/if}
        <div class="analytics-chart-foot"><span>◌ &nbsp; {$t('analytics.monthsAnalyzed', { count: months })}</span><span>{$t('analytics.ongoing')}</span></div>
      </section>

      <section class="analytics-card analytics-composition" aria-labelledby="composition-title">
        <div class="analytics-card-top"><div><span class="analytics-section-kicker">{$t('analytics.composition')}</span><h2 id="composition-title">{$t('categories.byCategory')}</h2><p>{categorySelectionCount || selectedTags.length ? $t('analytics.filtered') : $t('analytics.unfiltered')}</p></div></div>
        {#if overallTotal}
          <div class="analytics-donut-wrap"><div class="analytics-donut" style={`background:${donutGradient}`} role="img" aria-label={$t('analytics.distribution')}><div><small>{$t('common.total')}</small><strong>{money(overallTotal)}</strong></div></div></div>
          <div class="analytics-legend"><button type="button" class:chosen={!categorySelectionCount} onclick={() => { selectedCategories = []; selectedMacros = []; }}><span class="legend-name"><i class="legend-dot all"></i>{$t('common.all')}</span><b>100%</b></button>{#each topCategories as item, index}<button type="button" class:chosen={selectedCategories.includes(item.category)} onclick={() => toggleCategory(item.category)}><span class="legend-name"><i class="legend-dot" style={`background:${palette[index]}`}></i>{$categoryLabel(item.category)}</span><span class="legend-metric"><b>{money(item.amount)}</b><small>{Math.round(Number(item.amount) / overallTotal * 100)}%</small></span></button>{/each}</div>
        {:else}<div class="analytics-empty small">{$t('analytics.categoriesEmpty')}</div>{/if}
      </section>
    </div>

    <section class="analytics-card analytics-daily-panel" aria-labelledby="daily-title">
      <div class="analytics-card-top"><div><span class="analytics-section-kicker">{$t('analytics.dailySection')}</span><h2 id="daily-title">{$t('analytics.withinMonth')}</h2><p>{dailyView === 'daily' ? $t('analytics.dailyMovement') : $t('analytics.cumulativeMovement')} · {monthName(analysis.selected_month, true)}</p></div><div class="analytics-daily-controls">{#if analysis.monthly.length > 1}<label>{$t('common.monthLabel')} <select value={selectedMonth || analysis.selected_month} onchange={(event) => selectedMonth = event.currentTarget.value}>{#each analysis.monthly as item}<option value={item.month}>{monthName(item.month, true)}</option>{/each}</select></label>{:else}<span class="analytics-month-label">{monthName(analysis.selected_month, true)}</span>{/if}<div class="chart-switch" role="group" aria-label={$t('analytics.dailyChart')}><button type="button" class:active={dailyChart === 'bar'} aria-label={$t('analytics.bar')} aria-pressed={dailyChart === 'bar'} title={$t('analytics.bar')} onclick={() => dailyChart = 'bar'}>▥</button><button type="button" class:active={dailyChart === 'line'} aria-label={$t('analytics.line')} aria-pressed={dailyChart === 'line'} title={$t('analytics.line')} onclick={() => dailyChart = 'line'}>⌁</button><button type="button" class:active={dailyChart === 'area'} aria-label={$t('analytics.area')} aria-pressed={dailyChart === 'area'} title={$t('analytics.area')} onclick={() => dailyChart = 'area'}>◢</button></div></div></div>
      <div class="analytics-daily-view" role="group" aria-label={$t('analytics.dailyMode')}><button type="button" class:active={dailyView === 'daily'} aria-pressed={dailyView === 'daily'} onclick={() => dailyView = 'daily'}>{$t('analytics.perDay')}</button><button type="button" class:active={dailyView === 'cumulative'} aria-pressed={dailyView === 'cumulative'} onclick={() => dailyView = 'cumulative'}>{$t('analytics.cumulative')}</button></div>
      <div class="analytics-daily-body"><div class="analytics-daily-chart">{#if selectedMonthTotal}<div class="analytics-chart-scroll"><TrendChart points={dailyPoints} type={dailyChart} accent={mode === 'expenses' ? '#8b7ec9' : '#65aa93'} id="daily-fill" {hideAmounts} label={$t('analytics.dailyLabel')} /></div>{:else}<div class="analytics-empty">{$t('analytics.noDaily')}<span>{$t('analytics.chooseMonth')}</span></div>{/if}</div><aside class="analytics-daily-insight"><span>{$t('analytics.inMonth', { month: monthName(analysis.selected_month, true).toUpperCase() })}</span><strong>{money(selectedMonthTotal)}</strong><small>{mode === 'expenses' ? $t('analytics.monthSpending') : $t('analytics.monthContributions')}</small><div class="insight-divider"></div><span>{$t('analytics.peakDay')}</span><b>{peakDay && Number(peakDay.amount) ? new Intl.DateTimeFormat($locale, { day: 'numeric', month: 'short' }).format(new Date(`${peakDay.date}T12:00:00`)) : '—'}</b><small>{peakDay && Number(peakDay.amount) ? money(peakDay.amount) : $t('analytics.noMovement')}</small></aside></div>
    </section>
    <p class="analytics-method">{mode === 'expenses' ? $t('analytics.expenseMethod') : $t('analytics.investmentMethod')}</p>
  {/if}
</div>
