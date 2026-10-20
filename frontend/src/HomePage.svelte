<script>
  import { t, locale } from './i18n/index.js';
  import TransactionsTable from './TransactionsTable.svelte';
  import FinancialSummary from './widgets/FinancialSummary.svelte';
  import SpendingByCategory from './widgets/SpendingByCategory.svelte';
  import RecurringExpenses from './widgets/RecurringExpenses.svelte';
  import AiAssistantCard from './widgets/AiAssistantCard.svelte';
  import PluggyImport from './widgets/PluggyImport.svelte';
  import IntegrationSetup from './widgets/IntegrationSetup.svelte';

  let {
    config, connections, summary, recurring, tags, formatMoney,
    busy = false, error = '', notice = '',
    onrefresh, onsync, onconnect, onadd, onimport,
    onclassifybatch, onclassify, onsetcategory, ontoggletag,
    ondismisserror, ondismissnotice,
  } = $props();
  let table = $state(null);
  let uncategorized = $derived(summary.uncategorized_count || 0);
  let month = $derived(summary.month
    ? new Intl.DateTimeFormat($locale, { month: 'long', year: 'numeric' }).format(new Date(`${summary.month}-02T12:00:00`))
    : $t('common.thisMonth'));

  export async function refresh() {
    await table?.refresh();
  }
</script>

<div class="page-content">
  <section class="welcome-row">
    <div><div class="eyebrow">{$t('home.eyebrow')}</div><h1>{$t('home.title')}</h1><p class="subtitle">{$t('home.subtitle', { month })}</p></div>
    <div class="welcome-actions">{#if connections.length}<button class="button button-secondary" onclick={onsync} disabled={busy}>↻ <span>{$t('home.sync')}</span></button>{/if}<button class="button button-secondary" onclick={onconnect} disabled={busy || !config.pluggy_configured}>↗ <span>{$t('home.connect')}</span></button><button class="button button-primary" onclick={onadd}>＋ <span>{$t('transactions.new')}</span></button></div>
  </section>

  <IntegrationSetup pluggyConfigured={config.pluggy_configured} aiConfigured={config.ai_configured} />
  <PluggyImport configured={config.pluggy_configured} {busy} {onimport} />
  {#if error}<div class="flash flash-error" role="alert">{$t(error)}<button onclick={ondismisserror}>×</button></div>{/if}
  {#if notice}<div class="flash flash-success" role="status">{$t(notice)}<button onclick={ondismissnotice}>×</button></div>{/if}

  <FinancialSummary {summary} connectionCount={connections.length} {formatMoney} />
  <section class="content-grid">
    <TransactionsTable bind:this={table} compact {config} {tags} {busy} {uncategorized} {formatMoney}
      {onrefresh} {onclassifybatch} {onclassify} {onsetcategory} {ontoggletag} {onadd} />
    <div class="right-column">
      <SpendingByCategory categories={summary.categories} {formatMoney} />
      <RecurringExpenses items={recurring} {formatMoney} />
      <AiAssistantCard configured={config.ai_configured} />
    </div>
  </section>
  <footer class="page-footer"><span>Finance Bro <i>·</i> {$t('home.footer')}</span><span>{$t('home.motto')} <b>✳</b></span></footer>
</div>
