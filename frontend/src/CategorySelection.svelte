<script>
  import { t, categoryLabel } from './i18n/index.js';
  let {
    categories = [], macros = [], label = '', inset = false,
    onremovecategory = () => {}, onremovemacro = () => {}, onclear = () => {},
  } = $props();
</script>

{#if categories.length || macros.length}
  <div class="category-selection" class:inset aria-label={$t('categories.selected')}>
    <span>{label || $t('categories.selectionLabel')}</span>
    {#each categories as category}<button type="button" aria-label={$t('categories.remove', { category: $categoryLabel(category) })} onclick={() => onremovecategory(category)}>{$categoryLabel(category)} <b aria-hidden="true">×</b></button>{/each}
    {#each macros as macro}<button type="button" aria-label={$t('categories.removeMacro', { category: $categoryLabel(macro) })} onclick={() => onremovemacro(macro)}>{$categoryLabel(macro)} ({$t('categories.macroSuffix')}) <b aria-hidden="true">×</b></button>{/each}
    <button type="button" class="clear-selected" onclick={onclear}>{$t('categories.clear')}</button>
  </div>
{/if}

<style>
  .category-selection{display:flex;align-items:center;flex-wrap:wrap;gap:7px;margin:-5px 0 18px}
  .category-selection.inset{margin:0;padding:0 17px 12px}
  .category-selection>span{font-size:10px;font-weight:800;color:#8b8794;margin-right:3px}
  button{display:inline-flex;align-items:center;gap:7px;padding:6px 9px;border:1px solid #e5dced;border-radius:18px;background:#f6f2fa;color:#5f5375;font-size:10px;font-weight:700}
  button:hover{background:#eee6f5}
  button b{font-size:14px;line-height:10px}
  .clear-selected{border-color:transparent;background:transparent;color:#a29ba9}
  :global(:root[data-theme="dark"]) .category-selection>span{color:#b2bdce}
  :global(:root[data-theme="dark"]) button{background:#38314a;border-color:#5d4c72;color:#e1d1ff}
  :global(:root[data-theme="dark"]) button:hover{background:#473958}
  :global(:root[data-theme="dark"]) .clear-selected{background:transparent;border-color:transparent;color:#b8c2d1}
</style>
