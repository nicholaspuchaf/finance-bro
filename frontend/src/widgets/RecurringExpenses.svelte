<script>
  import { t } from '../i18n/index.js';
  let { items = [], limit = 5, formatMoney } = $props();
</script>

<article class="panel recurring-panel">
  <div class="panel-heading"><div><h2>{$t('recurring.title')}</h2><p>{$t('recurring.description')}</p></div></div>
  {#if items.length}
    <div class="recurring-list">{#each items.slice(0, limit) as item}<div><strong>{item.description}</strong><span>{$t('recurring.last', { count: item.months, amount: formatMoney(item.last_amount, item.currency) })}</span></div>{/each}</div>
  {:else}<div class="mini-empty">{$t('recurring.empty')}</div>{/if}
</article>
