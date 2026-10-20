<script>
  import { COMMON_CATEGORY_NAMES } from './categoryOptions.js';
  import './category-selector.css';

  let {
    categories = [],
    categoryGroups = [],
    value = '',
    all = false,
    macro = false,
    allowMacro = false,
    label = '',
    placeholder = '',
    ariaLabel = 'Categoria',
    resetOnSelect = false,
    onselect = () => {},
    onallchange = () => {},
    onmacrochange = () => {},
    variant = 'filter',
  } = $props();

  let commonCategories = $derived(COMMON_CATEGORY_NAMES.filter((name) => categories.includes(name)));
  let selectedOutsideCommon = $derived(Boolean(value) && (!all && !macro ? !commonCategories.includes(value) : all && !categories.includes(value)));

  function choose(event) {
    const selected = event.currentTarget.value;
    onselect(selected, macro ? 'macro' : 'category');
    if (resetOnSelect) event.currentTarget.value = '';
  }
</script>

<div class={`category-selector category-selector-${variant}`}>
  <label class="category-selector-main">
    {#if label}<span>{label}</span>{/if}
    <select aria-label={ariaLabel} {value} onchange={choose}>
      {#if placeholder}<option value="">{placeholder}</option>{/if}
      {#if selectedOutsideCommon}<option value={value}>{value}</option>{/if}
      {#if macro}
        {#each categoryGroups as group}<option value={group.name}>{group.name}</option>{/each}
      {:else if all}
        {#each categoryGroups as group}
          <optgroup label={group.name}>
            {#each group.categories as category}<option value={category}>{category}</option>{/each}
          </optgroup>
        {/each}
      {:else}
        {#each commonCategories as category}<option value={category}>{category}</option>{/each}
      {/if}
    </select>
    <span class="category-selector-arrow" aria-hidden="true">⌄</span>
  </label>
  <div class="category-selector-toggles">
    <label class="category-all-toggle"><input type="checkbox" checked={all} onchange={(event) => onallchange(event.currentTarget.checked)} /> Todas</label>
    {#if allowMacro}<label class="category-all-toggle"><input type="checkbox" checked={macro} onchange={(event) => onmacrochange(event.currentTarget.checked)} /> Macro-categorias</label>{/if}
  </div>
</div>
