<script>
  import { t, locale, number } from '../i18n/index.js';
  import SummaryCard from './SummaryCard.svelte';

  let { summary, connectionCount = 0, formatMoney, reviewHref = '#transacoes' } = $props();
  let totalSpent = $derived(summary.categories.reduce((sum, item) => sum + Math.max(0, Number(item.amount)), 0));
  let uncategorized = $derived(summary.uncategorized_count || 0);
  let month = $derived(summary.month
    ? new Intl.DateTimeFormat($locale, { month: 'long', year: 'numeric' }).format(new Date(`${summary.month}-02T12:00:00`))
    : $t('common.thisMonth'));
</script>

<section class="summary-grid" aria-label={$t('summary.label')}>
  <SummaryCard label={$t('summary.spent')} value={formatMoney(totalSpent)} icon="↗" tone="coral" highlighted>
    {#snippet footer()}<span class="period-pill">● {month}</span><span class="muted">{$t('summary.confirmed')}</span>{/snippet}
  </SummaryCard>
  <SummaryCard label={$t('nav.transactions')} value={$number(summary.transaction_count)} icon="↕">
    {#snippet footer()}<span class="tiny-dot green"></span><span class="muted">{$t('common.inThisMonth')}</span>{/snippet}
  </SummaryCard>
  <SummaryCard label={$t('summary.connected')} value={$number(connectionCount)} icon="▤" tone="mint">
    {#snippet footer()}<span class="tiny-dot" class:green={connectionCount > 0}></span><span class="muted">{connectionCount ? $t('summary.manual') : $t('summary.firstBank')}</span>{/snippet}
  </SummaryCard>
  <SummaryCard label={$t('summary.review')} value={$number(uncategorized)} icon="✳" tone="amber">
    {#snippet footer()}<span class="muted">{$t('summary.uncategorized')}</span>{#if uncategorized}<a href={reviewHref} class="review-link">{$t('summary.reviewAction')} →</a>{/if}{/snippet}
  </SummaryCard>
</section>
