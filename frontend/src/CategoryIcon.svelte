<script>
  import { categoryLabel } from './i18n/index.js';
  import { categoryIconConfig, categoryIconPaths, resolveCategoryIcon } from './categoryIcons.js';

  let { category, categoryGroups = [], income = false, enabled = categoryIconConfig.enabled } = $props();
  let icon = $derived(resolveCategoryIcon(category, categoryGroups, enabled));
</script>

<div class="merchant-icon" class:income title={$categoryLabel(category)}>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    {#each categoryIconPaths[icon] as path, index}
      <path d={path} fill={icon === 'default' && index === 1 ? 'currentColor' : 'none'} />
    {/each}
  </svg>
</div>

<style>
  svg{display:block;width:19px;height:19px}
</style>
