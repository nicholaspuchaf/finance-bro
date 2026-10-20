<script>
  import { t, locale, categoryLabel, describeError, message } from './i18n/index.js';
  import { onMount, tick } from 'svelte';
  import { PluggyConnect } from 'pluggy-connect-sdk';
  import AnalyticsPage from './AnalyticsPage.svelte';
  import HomePage from './HomePage.svelte';
  import LocaleToggle from './LocaleToggle.svelte';
  import TransactionsTable from './TransactionsTable.svelte';
  import { api } from './api.js';
  import { COMMON_CATEGORY_NAMES } from './categoryOptions.js';

  let transactionTable = $state(null);
  let connections = $state([]);
  let tags = $state([]);
  let summary = $state({ month: '', categories: [], transaction_count: 0 });
  let recurring = $state([]);
  let config = $state({ pluggy_configured: false, ai_configured: false, categories: [], category_groups: [] });
  let showAllDraftCategories = $state(false);
  let busy = $state(false);
  let error = $state('');
  let notice = $state('');
  let showAdd = $state(false);
  let pendingCategoryRule = $state(null);
  let ruleBusy = $state(false);
  function pageFromHash(hash) {
    if (hash === '#tags') return 'tags';
    if (hash === '#dashboards' || hash === '#categorias') return 'dashboards';
    return hash === '#transacoes' ? 'transactions' : 'overview';
  }
  let activePage = $state(pageFromHash(typeof window === 'undefined' ? '' : window.location.hash));
  let newTagName = $state('');
  let editingTagId = $state(null);
  let editingTagName = $state('');
  let draft = $state({ date: new Date().toISOString().slice(0, 10), description: '', amount: '', category: 'Uncategorized', tag_ids: [] });
  const fontScaleOptions = [80, 90, 100, 110, 125, 150];
  let fontScale = $state(100);
  function savedPrivacyMode() {
    try { return typeof localStorage !== 'undefined' && localStorage.getItem('finance-bro-hide-amounts') === 'true'; }
    catch { return false; }
  }
  let hideAmounts = $state(savedPrivacyMode());
  let theme = $state(typeof document !== 'undefined' && document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');

  function toggleTheme() {
    theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#10131b' : '#f8f8f6');
    try { localStorage.setItem('finance-bro-theme', theme); } catch { /* Storage may be disabled. */ }
  }

  function togglePrivacyMode() {
    hideAmounts = !hideAmounts;
    try { localStorage.setItem('finance-bro-hide-amounts', String(hideAmounts)); } catch { /* Storage may be disabled. */ }
  }

  function changeFontScale(direction) {
    const nextIndex = fontScaleOptions.indexOf(fontScale) + direction;
    if (nextIndex < 0 || nextIndex >= fontScaleOptions.length) return;
    fontScale = fontScaleOptions[nextIndex];
    document.documentElement.style.setProperty('--interface-scale', String(fontScale / 100));
    try { localStorage.setItem('finance-bro-font-scale', String(fontScale)); } catch { /* Storage may be disabled. */ }
  }

  function formatMoney(value, code = 'BRL') {
    if (hideAmounts) return `${code === 'BRL' ? 'R$' : code} •••••`;
    try { return new Intl.NumberFormat($locale, { style: 'currency', currency: code }).format(Number(value)); }
    catch { return `${value} ${code}`; }
  }
  const commonCategories = $derived(COMMON_CATEGORY_NAMES.filter((category) => config.categories.includes(category)));

  async function refresh(clearError = true, refreshTransactions = true) {
    if (clearError) error = '';
    try {
      await Promise.all([refreshTransactions ? transactionTable?.refresh() : Promise.resolve(), (async () => {
        [connections, summary, config, recurring, tags] = await Promise.all([
          api('/api/connections'), api('/api/summary'), api('/api/config'), api('/api/recurring'), api('/api/tags'),
        ]);
      })()]);
    } catch (e) {
      error = message('errors.backend', { detail: describeError(e) });
    }
  }

  onMount(() => {
    try {
      const savedScale = Number(localStorage.getItem('finance-bro-font-scale'));
      if (fontScaleOptions.includes(savedScale)) fontScale = savedScale;
    } catch { /* Keep the default scale when storage is unavailable. */ }
    document.documentElement.style.setProperty('--interface-scale', String(fontScale / 100));
    refresh(true, false);
    async function syncPage() {
      if (window.location.hash === '#categorias') {
        window.history.replaceState(null, '', '#dashboards');
      }
      activePage = pageFromHash(window.location.hash);
      await tick();
      window.scrollTo(0, 0);
    }
    syncPage();
    window.addEventListener('hashchange', syncPage);
    return () => window.removeEventListener('hashchange', syncPage);
  });

  const uncategorized = $derived(summary.uncategorized_count || 0);

  async function connectBank() {
    error = '';
    notice = '';
    try {
      const { accessToken } = await api('/api/pluggy/connect-token', { method: 'POST' });
      const widget = new PluggyConnect({
        connectToken: accessToken,
        language: $locale === 'en-US' ? 'en' : 'pt',
        includeSandbox: false,
        onSuccess: async (data) => {
          busy = true;
          try {
            const itemId = data.item?.id || data.id;
            if (!itemId) { error = message('errors.noItem'); return; }
            const result = await api(`/api/pluggy/items/${itemId}/sync`, { method: 'POST' });
            notice = message('notice.connected', { accounts: result.accounts_synced, count: result.transactions_added });
            await refresh();
          } catch (e) { error = describeError(e); }
          finally { busy = false; }
        },
        onError: (e) => { error = e?.message ? describeError(e) : message('errors.connect'); },
      });
      await widget.init();
    } catch (e) { error = describeError(e); }
  }

  async function syncAll() {
    busy = true;
    error = '';
    try {
      const result = await api('/api/connections/sync', { method: 'POST' });
      notice = message('notice.synced', { banks: result.connections_synced, count: result.transactions_added });
      if (result.errors?.length) error = result.errors.map((item) => message('errors.item', { id: item.item_id, detail: describeError(item.error) }));
      await refresh(false);
    } catch (e) { error = describeError(e); }
    finally { busy = false; }
  }

  async function syncItemId(itemId) {
    if (!itemId.trim() || busy) return false;
    busy = true; error = '';
    try {
      const result = await api(`/api/pluggy/items/${encodeURIComponent(itemId.trim())}/sync`, { method: 'POST' });
      notice = message('notice.imported', { count: result.transactions_added });
      await refresh(false);
      return true;
    } catch (e) { error = describeError(e); return false; }
    finally { busy = false; }
  }

  async function classifyBatch() {
    busy = true; error = '';
    try {
      const result = await api('/api/transactions/classify-batch', { method: 'POST' });
      notice = message('notice.batch', { classified: result.classified, attempted: result.attempted });
      if (result.errors?.length) error = result.errors.map((item) => message('errors.item', { id: `#${item.id}`, detail: describeError(item.error) }));
      await refresh(false);
    } catch (e) { error = describeError(e); }
    finally { busy = false; }
  }

  async function classify(transaction) {
    busy = true;
    error = '';
    try {
      await api(`/api/transactions/${transaction.id}/classify`, { method: 'POST' });
      notice = message('notice.classified');
      await refresh();
    } catch (e) { error = describeError(e); }
    finally { busy = false; }
  }

  async function saveTransaction(event) {
    event.preventDefault();
    try {
      await api('/api/transactions', { method: 'POST', body: JSON.stringify(draft) });
      showAdd = false;
      draft = { date: new Date().toISOString().slice(0, 10), description: '', amount: '', category: 'Uncategorized', tag_ids: [] };
      await refresh();
    } catch (e) { error = describeError(e); }
  }

  async function setCategory(transaction, value) {
    try {
      await api(`/api/transactions/${transaction.id}`, { method: 'PATCH', body: JSON.stringify({ category: value }) });
      pendingCategoryRule = { id: transaction.id, name: transaction.merchant || transaction.description, category: value };
      await refresh();
    } catch (e) { error = describeError(e); }
  }

  async function applyCategoryRule() {
    if (!pendingCategoryRule || ruleBusy) return;
    ruleBusy = true;
    const { id, category } = pendingCategoryRule;
    try {
      const result = await api(`/api/transactions/${id}/category-rule`, { method: 'POST', body: JSON.stringify({ category }) });
      pendingCategoryRule = null;
      notice = message('notice.rule', { count: result.transactions_updated });
      await refresh(false);
    } catch (e) { error = describeError(e); }
    finally { ruleBusy = false; }
  }

  async function toggleTag(transaction, tagId) {
    const current = transaction.tags.map((tag) => tag.id);
    const tag_ids = current.includes(tagId) ? current.filter((id) => id !== tagId) : [...current, tagId];
    try {
      await api(`/api/transactions/${transaction.id}`, { method: 'PATCH', body: JSON.stringify({ tag_ids }) });
      await Promise.all([transactionTable?.refresh(), loadTags()]);
    } catch (e) { error = describeError(e); }
  }

  async function loadTags() { tags = await api('/api/tags'); }

  async function createTag(event) {
    event.preventDefault();
    try {
      await api('/api/tags', { method: 'POST', body: JSON.stringify({ name: newTagName }) });
      newTagName = '';
      await loadTags();
      notice = message('notice.tagCreated');
    } catch (e) { error = describeError(e); }
  }

  async function renameTag(event) {
    event.preventDefault();
    try {
      await api(`/api/tags/${editingTagId}`, { method: 'PATCH', body: JSON.stringify({ name: editingTagName }) });
      editingTagId = null;
      await Promise.all([loadTags(), transactionTable?.refresh()]);
      notice = message('notice.tagUpdated');
    } catch (e) { error = describeError(e); }
  }

  async function deleteTag(tag) {
    if (!window.confirm($t('tags.deleteConfirm', { name: tag.name, count: tag.transaction_count }))) return;
    try {
      await api(`/api/tags/${tag.id}`, { method: 'DELETE' });
      await Promise.all([loadTags(), transactionTable?.refresh()]);
      notice = message('notice.tagDeleted');
    } catch (e) { error = describeError(e); }
  }


</script>

<svelte:head>
  <title>{$t('app.title')}</title>
  <meta name="description" content={$t('app.description')} />
</svelte:head>

<div class="app-shell">
  <aside class="sidebar">
    <a class="brand" href="/" aria-label={$t('nav.brand')}><span class="brand-mark">f</span><span>finance<span class="brand-light">bro</span></span></a>
    <div class="side-label">{$t('nav.overview')}</div>
    <nav>
      <a class="nav-item" class:active={activePage === 'overview'} href="#inicio"><span class="nav-icon">▦</span> {$t('nav.home')}</a>
      <a class="nav-item" class:active={activePage === 'transactions'} href="#transacoes"><span class="nav-icon">↕</span> {$t('nav.transactions')}</a>
      <a class="nav-item" class:active={activePage === 'dashboards'} href="#dashboards"><span class="nav-icon">◫</span> {$t('nav.dashboards')}</a>
      <a class="nav-item" class:active={activePage === 'tags'} href="#tags"><span class="nav-icon">◇</span> {$t('nav.tags')} <span class="nav-count">{tags.length}</span></a>
    </nav>
    <div class="side-label bank-label">{$t('nav.accounts')}</div>
    {#each connections as connection}
      <div class="bank-item"><span class="bank-dot"></span><span class="bank-name">{connection.institution_name}{connection.status !== 'UPDATED' && connection.status !== 'SUCCESS' ? ` · ${$t('status.' + connection.status)}` : ''}</span><span class="bank-status" title={$t('status.' + connection.status)}></span></div>
      {#each connection.accounts as account}
        <div class="account-item">{account.name}<span>{account.balance == null ? '—' : formatMoney(account.balance, account.currency || 'BRL')}</span></div>
      {/each}
    {:else}
      <p class="sidebar-empty">{$t('nav.emptyAccounts')}</p>
    {/each}
    <div class="sidebar-bottom">
      <div class="sync-note"><span class="sync-dot"></span><span>{$t('nav.syncNote')}</span></div>
      <div class="profile"><div class="avatar">N</div><div><strong>{$t('nav.workspace')}</strong><small>{$t('nav.personal')}</small></div><span class="profile-more">···</span></div>
    </div>
  </aside>

  <main id="inicio" class="main-content">
    <header class="topbar">
      <div class="topbar-heading">
        <a class="header-brand" href="#inicio" aria-label={$t('nav.brandHeader')}><span class="brand-mark" aria-hidden="true">f</span></a>
        <div class="breadcrumb">{$t('nav.finances')} <span>/</span> <strong>{activePage === 'tags' ? $t('nav.tags') : activePage === 'dashboards' ? $t('nav.dashboards') : activePage === 'transactions' ? $t('nav.transactions') : $t('nav.home')}</strong></div>
      </div>
      <div class="top-actions">
        <span class="local-badge"><i></i> {$t('header.local')}</span>
        <LocaleToggle />
        <button type="button" class="theme-toggle" class:active={theme === 'dark'} aria-label={theme === 'dark' ? $t('header.light') : $t('header.dark')} aria-pressed={theme === 'dark'} title={theme === 'dark' ? $t('header.light') : $t('header.dark')} onclick={toggleTheme}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            {#if theme === 'dark'}<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>
            {:else}<path d="M20.2 15.1A8.5 8.5 0 0 1 8.9 3.8 8.5 8.5 0 1 0 20.2 15.1Z"/>{/if}
          </svg>
        </button>
        <button type="button" class="privacy-toggle" class:active={hideAmounts} aria-label={hideAmounts ? $t('header.show') : $t('header.hide')} aria-pressed={hideAmounts} title={hideAmounts ? $t('header.show') : $t('header.hide')} onclick={togglePrivacyMode}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6-10-6-10-6Z"/><circle cx="12" cy="12" r="3"/>{#if hideAmounts}<path d="M3 3 21 21" class="eye-slash"/>{/if}</svg></button>
        <div class="font-size-control" role="group" aria-label={$t('header.font', { scale: fontScale })}><button type="button" aria-label={$t('header.smaller')} title={$t('header.smaller')} disabled={fontScale === fontScaleOptions[0]} onclick={() => changeFontScale(-1)}>A−</button><button type="button" aria-label={$t('header.larger')} title={$t('header.larger')} disabled={fontScale === fontScaleOptions[fontScaleOptions.length - 1]} onclick={() => changeFontScale(1)}>A+</button></div>
        <div class="avatar small">N</div>
      </div>
    </header>

    {#if activePage === 'dashboards'}
      <AnalyticsPage {hideAmounts} {tags} categories={config.categories} categoryGroups={config.category_groups} />
    {:else if activePage === 'transactions'}
    <div class="page-content transactions-page">
      <section class="welcome-row">
        <div><div class="eyebrow">{$t('transactions.eyebrow')}</div><h1>{$t('nav.transactions')}</h1><p class="subtitle">{$t('transactions.description')}</p></div>
        <button class="button button-primary" onclick={() => showAdd = true}>＋ <span>{$t('transactions.new')}</span></button>
      </section>
      {#if error}<div class="flash flash-error" role="alert">{$t(error)}<button onclick={() => error = ''}>×</button></div>{/if}
      {#if notice}<div class="flash flash-success" role="status">{$t(notice)}<button onclick={() => notice = ''}>×</button></div>{/if}
      <TransactionsTable bind:this={transactionTable} {config} {tags} {busy} {uncategorized} {formatMoney}
        onrefresh={refresh} onclassifybatch={classifyBatch} onclassify={classify} onsetcategory={setCategory} ontoggletag={toggleTag} onadd={() => showAdd = true} />
    </div>
    {:else if activePage === 'tags'}
    <div class="page-content tag-page">
      <section class="welcome-row">
        <div><div class="eyebrow">{$t('tags.eyebrow')}</div><h1>{$t('nav.tags')}</h1><p class="subtitle">{$t('tags.description')}</p></div>
        <a class="button button-secondary" href="#transacoes">{$t('transactions.view')} →</a>
      </section>
      {#if error}<div class="flash flash-error" role="alert">{$t(error)}<button onclick={() => error = ''}>×</button></div>{/if}
      {#if notice}<div class="flash flash-success" role="status">{$t(notice)}<button onclick={() => notice = ''}>×</button></div>{/if}
      <section class="panel tag-management">
        <div class="panel-heading"><div><h2>{$t('tags.title')}</h2><p>{$t('tags.count', { count: tags.length })}</p></div></div>
        <form class="tag-create-form" onsubmit={createTag}><label for="new-tag-name">{$t('tags.new')}</label><div><input id="new-tag-name" bind:value={newTagName} maxlength="40" placeholder={$t('tags.placeholder')} required /><button class="button button-primary">{$t('tags.create')}</button></div></form>
        {#if tags.length}
          <div class="tag-list">
            {#each tags as tag (tag.id)}
              <div class="tag-list-row">
                {#if editingTagId === tag.id}
                  <form class="tag-rename-form" onsubmit={renameTag}><input aria-label={$t('tags.renameLabel', { name: tag.name })} bind:value={editingTagName} maxlength="40" required /><button class="button button-primary">{$t('common.save')}</button><button type="button" class="button button-secondary" onclick={() => editingTagId = null}>{$t('common.cancel')}</button></form>
                {:else}
                  <span class="tag-pill">◇ {tag.name}</span><span class="tag-count">{$t('counts.transactions', { count: tag.transaction_count })}</span>
                  <div class="tag-actions"><button class="text-button" onclick={() => { editingTagId = tag.id; editingTagName = tag.name; }}>{$t('common.rename')}</button><button class="text-button tag-delete" onclick={() => deleteTag(tag)}>{$t('common.delete')}</button></div>
                {/if}
              </div>
            {/each}
          </div>
        {:else}<div class="empty-state"><div class="empty-illustration">◇</div><strong>{$t('tags.empty')}</strong><span>{$t('tags.emptyHelp')}</span></div>{/if}
      </section>
    </div>
    {:else}
      <HomePage bind:this={transactionTable} {config} {connections} {summary} {recurring} {tags} {formatMoney} {busy} {error} {notice}
        onrefresh={refresh} onsync={syncAll} onconnect={connectBank} onadd={() => showAdd = true} onimport={syncItemId}
        onclassifybatch={classifyBatch} onclassify={classify} onsetcategory={setCategory} ontoggletag={toggleTag}
        ondismisserror={() => error = ''} ondismissnotice={() => notice = ''} />
    {/if}
  </main>
</div>

{#if pendingCategoryRule}
  <div class="rule-prompt" role="region" aria-label={$t('rules.region')} aria-live="polite">
    <strong>{$t('rules.title')}</strong>
    <p>{$t('rules.before')} <b>{$categoryLabel(pendingCategoryRule.category)}</b> {$t('rules.middle')} <b>{pendingCategoryRule.name}</b>{$t('rules.after')}</p>
    <div class="rule-prompt-actions"><button type="button" class="button button-secondary" disabled={ruleBusy} onclick={() => pendingCategoryRule = null}>{$t('rules.only')}</button><button type="button" class="button button-primary" disabled={ruleBusy} onclick={applyCategoryRule}>{ruleBusy ? $t('rules.applying') : $t('rules.confirm')}</button></div>
  </div>
{/if}

{#if showAdd}
  <div class="modal-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && (showAdd = false)}>
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1"><div class="modal-heading"><div><div class="eyebrow">{$t('form.eyebrow')}</div><h2 id="modal-title">{$t('transactions.new')}</h2></div><button class="icon-button" onclick={() => showAdd = false} aria-label={$t('common.close')}>×</button></div>
      <form onsubmit={saveTransaction}>
        <label>{$t('form.description')}<input required bind:value={draft.description} placeholder={$t('form.descriptionPlaceholder')} /></label>
        <div class="form-row"><label>{$t('form.amount')}{#if hideAmounts}<input required type="password" inputmode="decimal" autocomplete="off" bind:value={draft.amount} placeholder="•••••" />{:else}<input required type="number" step="0.01" bind:value={draft.amount} placeholder={$t('form.amountPlaceholder')} />{/if}</label><label>{$t('form.date')}<input required type="date" bind:value={draft.date} /></label></div>
        <div class="draft-category-field"><label>{$t('categories.label')}<select bind:value={draft.category}>
          {#if !showAllDraftCategories && !commonCategories.includes(draft.category)}<option value={draft.category}>{$categoryLabel(draft.category)}</option>{/if}
          {#if showAllDraftCategories}
            {#each config.category_groups as group}<optgroup label={$categoryLabel(group.name)}>{#each group.categories as category}<option value={category}>{$categoryLabel(category)}</option>{/each}</optgroup>{/each}
          {:else}
            {#each commonCategories as category}<option value={category}>{$categoryLabel(category)}</option>{/each}
          {/if}
        </select></label><label class="category-all-toggle"><input type="checkbox" bind:checked={showAllDraftCategories} /> {$t('common.all')}</label></div>
        {#if tags.length}<fieldset class="draft-tags"><legend>{$t('nav.tags')}</legend><div>{#each tags as tag}<label><input type="checkbox" checked={draft.tag_ids.includes(tag.id)} onchange={() => draft.tag_ids = draft.tag_ids.includes(tag.id) ? draft.tag_ids.filter((id) => id !== tag.id) : [...draft.tag_ids, tag.id]} />{tag.name}</label>{/each}</div></fieldset>{/if}
        <div class="modal-actions"><button type="button" class="button button-secondary" onclick={() => showAdd = false}>{$t('common.cancel')}</button><button class="button button-primary">{$t('form.save')}</button></div>
      </form>
    </div>
  </div>
{/if}
