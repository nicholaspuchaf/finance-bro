<script>
  import { t, categoryLabel } from '../i18n/index.js';
  let { categories = [], limit = 5, formatMoney, dashboardHref = '#dashboards' } = $props();
  const colors = ['#d87f65', '#8b80c9', '#58a58b', '#d7a64f', '#6293bb'];
  let expenses = $derived(categories.filter((item) => Number(item.amount) > 0));
  let total = $derived(expenses.reduce((sum, item) => sum + Number(item.amount), 0));
</script>

<article class="panel categories-panel">
  <div class="panel-heading compact"><div><h2>{$t('categories.byCategory')}</h2><p>{$t('categories.spending')}</p></div></div>
  {#if expenses.length}
    <div class="category-breakdown">
      {#each expenses.slice(0, limit) as item, index}
        <div class="category-line">
          <div class="category-line-top"><span><i class="category-bullet" style={`--bullet:${colors[index % colors.length]}`}></i>{$categoryLabel(item.category)}</span><strong>{formatMoney(item.amount)}</strong></div>
          <div class="progress-track"><div class="progress-fill" style={`width:${Math.min(100, Number(item.amount) / total * 100)}%;--fill:${colors[index % colors.length]}`}></div></div>
        </div>
      {/each}
    </div>
  {:else}<div class="mini-empty"><span class="mini-empty-icon">◫</span><span>{$t('categories.empty')}<br />{$t('categories.emptyDetail')}</span></div>{/if}
  <a class="panel-link" href={dashboardHref}>{$t('categories.explore')} <span>→</span></a>
</article>
