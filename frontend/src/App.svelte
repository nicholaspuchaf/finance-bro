<script>
  import { onMount, tick } from 'svelte';
  import { PluggyConnect } from 'pluggy-connect-sdk';
  import AnalyticsPage from './AnalyticsPage.svelte';

  let transactions = $state([]);
  let connections = $state([]);
  let tags = $state([]);
  let summary = $state({ month: '', categories: [], transaction_count: 0 });
  let recurring = $state([]);
  let config = $state({ pluggy_configured: false, ai_configured: false, categories: [], category_groups: [] });
  let search = $state('');
  let categoryFilter = $state('');
  let showAllFilterCategories = $state(false);
  let showAllDraftCategories = $state(false);
  let expandedCategoryIds = $state({});
  let tagFilter = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let itemId = $state('');
  let hasMore = $state(false);
  let listLoading = $state(false);
  let requestNumber = 0;
  const pageSize = 50;
  let loading = $state(true);
  let busy = $state(false);
  let error = $state('');
  let notice = $state('');
  let showAdd = $state(false);
  let pendingCategoryRule = $state(null);
  let ruleBusy = $state(false);
  let activePage = $state('overview');
  let currentHash = $state('');
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
    try { return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: code }).format(Number(value)); }
    catch { return `${value} ${code}`; }
  }
  const dateFormat = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' });
  const categoryIcons = { 'Food and drinks': '◒', 'Groceries': '◒', 'Transportation': '↗', 'Housing': '⌂', 'Healthcare': '+', 'Education': '▤', 'Leisure': '✳', 'Shopping': '◇', 'Services': '▣', 'Transfers': '⇄', 'Income': '↙', 'Investments': '⌁', 'Other': '·', 'Uncategorized': '?' };
  const commonCategoryNames = [
    'Uncategorized', 'Groceries', 'Food and drinks', 'Eating out', 'Shopping',
    'Transportation', 'Housing', 'Utilities', 'Healthcare', 'Education',
    'Travel', 'Transfers', 'Income', 'Investments', 'Other',
  ];
  const commonCategories = $derived(commonCategoryNames.filter((category) => config.categories.includes(category)));

  async function api(path, options = {}) {
    const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = Array.isArray(body.detail) ? body.detail.map((item) => item.msg).join('; ') : body.detail;
      throw new Error(detail || `Falha ao acessar a API (${response.status})`);
    }
    return response.status === 204 ? null : response.json();
  }

  function transactionQuery(offset = 0) {
    const query = new URLSearchParams({ limit: String(pageSize), offset: String(offset) });
    if (search.trim()) query.set('search', search.trim());
    if (categoryFilter) query.set('category', categoryFilter);
    if (tagFilter) query.set('tag_id', tagFilter);
    if (dateFrom) query.set('date_from', dateFrom);
    if (dateTo) query.set('date_to', dateTo);
    return query;
  }

  async function loadTransactions(more = false) {
    const current = ++requestNumber;
    listLoading = true;
    try {
      const rows = await api(`/api/transactions?${transactionQuery(more ? transactions.length : 0)}`);
      if (current !== requestNumber) return;
      transactions = more ? [...transactions, ...rows] : rows;
      hasMore = rows.length === pageSize;
    } catch (e) { error = e.message; }
    finally { if (current === requestNumber) listLoading = false; }
  }

  async function refresh(clearError = true) {
    loading = true;
    if (clearError) error = '';
    try {
      await Promise.all([loadTransactions(), (async () => {
        [connections, summary, config, recurring, tags] = await Promise.all([
          api('/api/connections'), api('/api/summary'), api('/api/config'), api('/api/recurring'), api('/api/tags'),
        ]);
      })()]);
    } catch (e) {
      error = `${e.message}. Confirme se o backend está rodando.`;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    try {
      const savedScale = Number(localStorage.getItem('finance-bro-font-scale'));
      if (fontScaleOptions.includes(savedScale)) fontScale = savedScale;
    } catch { /* Keep the default scale when storage is unavailable. */ }
    document.documentElement.style.setProperty('--interface-scale', String(fontScale / 100));
    refresh();
    async function syncPage() {
      currentHash = window.location.hash;
      activePage = currentHash === '#tags' ? 'tags' : currentHash === '#categorias' ? 'categories' : 'overview';
      if (activePage === 'overview' && window.location.hash === '#transacoes') {
        await tick();
        document.querySelector(window.location.hash)?.scrollIntoView();
      } else if (activePage !== 'overview') {
        await tick();
        window.scrollTo(0, 0);
      }
    }
    syncPage();
    window.addEventListener('hashchange', syncPage);
    return () => window.removeEventListener('hashchange', syncPage);
  });

  let searchTimer;
  let filtersInitialized = false;
  $effect(() => {
    search;
    categoryFilter;
    tagFilter;
    dateFrom;
    dateTo;
    if (!filtersInitialized) { filtersInitialized = true; return; }
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadTransactions(), 250);
    return () => clearTimeout(searchTimer);
  });

  const totalSpent = $derived(summary.categories.filter((item) => Number(item.amount) > 0).reduce((sum, item) => sum + Number(item.amount), 0));
  const uncategorized = $derived(summary.uncategorized_count || 0);

  async function connectBank() {
    error = '';
    notice = '';
    try {
      const { accessToken } = await api('/api/pluggy/connect-token', { method: 'POST' });
      const widget = new PluggyConnect({
        connectToken: accessToken,
        includeSandbox: false,
        onSuccess: async (data) => {
          busy = true;
          try {
            const itemId = data.item?.id || data.id;
            if (!itemId) throw new Error('O Widget não retornou um Item ID. Copie o ID no Dashboard e importe pelo campo acima.');
            const result = await api(`/api/pluggy/items/${itemId}/sync`, { method: 'POST' });
            notice = `Conexão atualizada: ${result.accounts_synced} conta(s), ${result.transactions_added} nova(s) transação(ões).`;
            await refresh();
          } catch (e) { error = e.message; }
          finally { busy = false; }
        },
        onError: (e) => { error = e?.message || 'Não foi possível conectar ao banco.'; },
      });
      await widget.init();
    } catch (e) { error = e.message; }
  }

  async function syncAll() {
    busy = true;
    error = '';
    try {
      const result = await api('/api/connections/sync', { method: 'POST' });
      notice = `Sincronização concluída: ${result.connections_synced} banco(s), ${result.transactions_added} nova(s) transação(ões).`;
      if (result.errors?.length) error = result.errors.map((item) => `${item.item_id}: ${item.error}`).join(' | ');
      await refresh(false);
    } catch (e) { error = e.message; }
    finally { busy = false; }
  }

  async function syncItemId(event) {
    event.preventDefault();
    if (!itemId.trim()) return;
    busy = true; error = '';
    try {
      const result = await api(`/api/pluggy/items/${encodeURIComponent(itemId.trim())}/sync`, { method: 'POST' });
      notice = `${result.transactions_added} nova(s) transação(ões) importada(s).`;
      itemId = '';
      await refresh(false);
    } catch (e) { error = e.message; }
    finally { busy = false; }
  }

  async function classifyBatch() {
    busy = true; error = '';
    try {
      const result = await api('/api/transactions/classify-batch', { method: 'POST' });
      notice = `${result.classified} de ${result.attempted} transação(ões) classificadas (até 10 por vez).`;
      if (result.errors?.length) error = result.errors.map((item) => `#${item.id}: ${item.error}`).join(' | ');
      await refresh(false);
    } catch (e) { error = e.message; }
    finally { busy = false; }
  }

  async function classify(transaction) {
    busy = true;
    error = '';
    try {
      await api(`/api/transactions/${transaction.id}/classify`, { method: 'POST' });
      notice = 'Transação classificada pela IA.';
      await refresh();
    } catch (e) { error = e.message; }
    finally { busy = false; }
  }

  async function saveTransaction(event) {
    event.preventDefault();
    try {
      await api('/api/transactions', { method: 'POST', body: JSON.stringify(draft) });
      showAdd = false;
      draft = { date: new Date().toISOString().slice(0, 10), description: '', amount: '', category: 'Uncategorized', tag_ids: [] };
      await refresh();
    } catch (e) { error = e.message; }
  }

  async function setCategory(transaction, value) {
    try {
      await api(`/api/transactions/${transaction.id}`, { method: 'PATCH', body: JSON.stringify({ category: value }) });
      pendingCategoryRule = { id: transaction.id, name: transaction.merchant || transaction.description, category: value };
      await refresh();
    } catch (e) { error = e.message; }
  }

  async function applyCategoryRule() {
    if (!pendingCategoryRule || ruleBusy) return;
    ruleBusy = true;
    const { id, category } = pendingCategoryRule;
    try {
      const result = await api(`/api/transactions/${id}/category-rule`, { method: 'POST', body: JSON.stringify({ category }) });
      pendingCategoryRule = null;
      notice = `Regra salva. ${result.transactions_updated} transação(ões) com esse nome atualizada(s).`;
      await refresh(false);
    } catch (e) { error = e.message; }
    finally { ruleBusy = false; }
  }

  async function toggleTag(transaction, tagId) {
    const current = transaction.tags.map((tag) => tag.id);
    const tag_ids = current.includes(tagId) ? current.filter((id) => id !== tagId) : [...current, tagId];
    try {
      await api(`/api/transactions/${transaction.id}`, { method: 'PATCH', body: JSON.stringify({ tag_ids }) });
      await Promise.all([loadTransactions(), loadTags()]);
    } catch (e) { error = e.message; }
  }

  async function loadTags() { tags = await api('/api/tags'); }

  async function createTag(event) {
    event.preventDefault();
    try {
      await api('/api/tags', { method: 'POST', body: JSON.stringify({ name: newTagName }) });
      newTagName = '';
      await loadTags();
      notice = 'Tag criada.';
    } catch (e) { error = e.message; }
  }

  async function renameTag(event) {
    event.preventDefault();
    try {
      await api(`/api/tags/${editingTagId}`, { method: 'PATCH', body: JSON.stringify({ name: editingTagName }) });
      editingTagId = null;
      await Promise.all([loadTags(), loadTransactions()]);
      notice = 'Tag atualizada.';
    } catch (e) { error = e.message; }
  }

  async function deleteTag(tag) {
    if (!window.confirm(`Excluir a tag "${tag.name}"? Ela será removida de ${tag.transaction_count} transação(ões).`)) return;
    try {
      await api(`/api/tags/${tag.id}`, { method: 'DELETE' });
      if (String(tagFilter) === String(tag.id)) tagFilter = '';
      await Promise.all([loadTags(), loadTransactions()]);
      notice = 'Tag excluída.';
    } catch (e) { error = e.message; }
  }

  function monthLabel(month) {
    if (!month) return 'este mês';
    return new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' }).format(new Date(`${month}-02T12:00:00`));
  }
</script>

<svelte:head>
  <meta name="description" content="Organize suas finanças pessoais com clareza." />
</svelte:head>

<div class="app-shell">
  <aside class="sidebar">
    <a class="brand" href="/" aria-label="Finance Bro início"><span class="brand-mark">f</span><span>finance<span class="brand-light">bro</span></span></a>
    <div class="side-label">VISÃO GERAL</div>
    <nav>
      <a class="nav-item" class:active={activePage === 'overview' && currentHash !== '#transacoes'} href="#inicio"><span class="nav-icon">▦</span> Início</a>
      <a class="nav-item" class:active={currentHash === '#transacoes'} href="#transacoes"><span class="nav-icon">↕</span> Transações <span class="nav-count">{transactions.length}</span></a>
      <a class="nav-item" class:active={activePage === 'categories'} href="#categorias"><span class="nav-icon">◫</span> Categorias</a>
      <a class="nav-item" class:active={activePage === 'tags'} href="#tags"><span class="nav-icon">◇</span> Tags <span class="nav-count">{tags.length}</span></a>
    </nav>
    <div class="side-label bank-label">CONTAS</div>
    {#each connections as connection}
      <div class="bank-item"><span class="bank-dot"></span><span class="bank-name">{connection.institution_name}{connection.status !== 'UPDATED' && connection.status !== 'SUCCESS' ? ` · ${connection.status}` : ''}</span><span class="bank-status" title={connection.status}></span></div>
      {#each connection.accounts as account}
        <div class="account-item">{account.name}<span>{account.balance == null ? '—' : formatMoney(account.balance, account.currency || 'BRL')}</span></div>
      {/each}
    {:else}
      <p class="sidebar-empty">Nenhuma conta conectada</p>
    {/each}
    <div class="sidebar-bottom">
      <div class="sync-note"><span class="sync-dot"></span><span>SQLite local; sincronização e IA usam serviços externos</span></div>
      <div class="profile"><div class="avatar">N</div><div><strong>Meu espaço</strong><small>Uso pessoal</small></div><span class="profile-more">···</span></div>
    </div>
  </aside>

  <main id="inicio" class="main-content">
    <header class="topbar">
      <div class="breadcrumb">Finanças <span>/</span> <strong>{activePage === 'tags' ? 'Tags' : activePage === 'categories' ? 'Categorias' : 'Visão geral'}</strong></div>
      <div class="top-actions"><span class="local-badge"><i></i> Ambiente local</span><button type="button" class="privacy-toggle" class:active={hideAmounts} aria-label={hideAmounts ? 'Mostrar valores' : 'Ocultar valores'} aria-pressed={hideAmounts} title={hideAmounts ? 'Mostrar valores' : 'Ocultar valores'} onclick={togglePrivacyMode}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6-10-6-10-6Z"/><circle cx="12" cy="12" r="3"/>{#if hideAmounts}<path d="M3 3 21 21" class="eye-slash"/>{/if}</svg></button><div class="font-size-control" role="group" aria-label={`Tamanho da fonte: ${fontScale}%`}><button type="button" aria-label="Diminuir fonte" title="Diminuir fonte" disabled={fontScale === fontScaleOptions[0]} onclick={() => changeFontScale(-1)}>A−</button><button type="button" aria-label="Aumentar fonte" title="Aumentar fonte" disabled={fontScale === fontScaleOptions[fontScaleOptions.length - 1]} onclick={() => changeFontScale(1)}>A+</button></div><div class="avatar small">N</div></div>
    </header>

    {#if activePage === 'categories'}
      <AnalyticsPage {hideAmounts} />
    {:else if activePage === 'tags'}
    <div class="page-content tag-page">
      <section class="welcome-row">
        <div><div class="eyebrow">ORGANIZAÇÃO PESSOAL</div><h1>Tags</h1><p class="subtitle">Crie etiquetas para organizar transações além das categorias da Pluggy.</p></div>
        <a class="button button-secondary" href="#transacoes">Ver transações →</a>
      </section>
      {#if error}<div class="flash flash-error" role="alert">{error}<button onclick={() => error = ''}>×</button></div>{/if}
      {#if notice}<div class="flash flash-success" role="status">{notice}<button onclick={() => notice = ''}>×</button></div>{/if}
      <section class="panel tag-management">
        <div class="panel-heading"><div><h2>Suas tags</h2><p>{tags.length} tag(s) · cada transação pode ter várias.</p></div></div>
        <form class="tag-create-form" onsubmit={createTag}><label for="new-tag-name">Nova tag</label><div><input id="new-tag-name" bind:value={newTagName} maxlength="40" placeholder="Ex.: Viagem, Família, Reembolsável" required /><button class="button button-primary">Criar tag</button></div></form>
        {#if tags.length}
          <div class="tag-list">
            {#each tags as tag (tag.id)}
              <div class="tag-list-row">
                {#if editingTagId === tag.id}
                  <form class="tag-rename-form" onsubmit={renameTag}><input aria-label={`Novo nome da tag ${tag.name}`} bind:value={editingTagName} maxlength="40" required /><button class="button button-primary">Salvar</button><button type="button" class="button button-secondary" onclick={() => editingTagId = null}>Cancelar</button></form>
                {:else}
                  <span class="tag-pill">◇ {tag.name}</span><span class="tag-count">{tag.transaction_count} {tag.transaction_count === 1 ? 'transação' : 'transações'}</span>
                  <div class="tag-actions"><button class="text-button" onclick={() => { editingTagId = tag.id; editingTagName = tag.name; }}>Renomear</button><button class="text-button tag-delete" onclick={() => deleteTag(tag)}>Excluir</button></div>
                {/if}
              </div>
            {/each}
          </div>
        {:else}<div class="empty-state"><div class="empty-illustration">◇</div><strong>Nenhuma tag criada</strong><span>Crie sua primeira tag para começar a organizar as transações.</span></div>{/if}
      </section>
    </div>
    {:else}
    <div class="page-content">
      <section class="welcome-row">
        <div><div class="eyebrow">SEU DINHEIRO, EM FOCO</div><h1>Visão geral</h1><p class="subtitle">Aqui está o resumo das suas finanças para {monthLabel(summary.month)}.</p></div>
        <div class="welcome-actions">{#if connections.length}<button class="button button-secondary" onclick={syncAll} disabled={busy}>↻ <span>Sincronizar</span></button>{/if}<button class="button button-secondary" onclick={connectBank} disabled={busy || !config.pluggy_configured}>↗ <span>Conectar banco</span></button><button class="button button-primary" onclick={() => showAdd = true}>＋ <span>Nova transação</span></button></div>
      </section>

      {#if !config.pluggy_configured || !config.ai_configured}
        <section class="setup-banner">
          <div class="setup-icon">✳</div><div class="setup-copy"><strong>Quase pronto para começar</strong><span>Configure as chaves de integração no arquivo <code>.env</code> na raiz do projeto.</span></div>
          <div class="setup-steps"><span class:ready={config.pluggy_configured}><b>{config.pluggy_configured ? '✓' : '1'}</b> Pluggy</span><span class:ready={config.ai_configured}><b>{config.ai_configured ? '✓' : '2'}</b> IA</span></div>
        </section>
      {/if}

      <section class="setup-banner"><div class="setup-icon">↗</div><div class="setup-copy"><strong>Meu Pluggy pessoal</strong><span>Conecte o banco no Meu Pluggy. No Dashboard da mesma conta, abra Aplicações → Demo, conecte o conector MeuPluggy e copie o Item ID completo em Itens Conectados.</span></div><form class="item-form" onsubmit={syncItemId}><input aria-label="Item ID do Meu Pluggy" placeholder="Item ID completo (UUID)" bind:value={itemId} required /><button class="button button-secondary" disabled={busy || !config.pluggy_configured}>Importar</button></form></section>

      {#if error}<div class="flash flash-error" role="alert">{error}<button onclick={() => error = ''}>×</button></div>{/if}
      {#if notice}<div class="flash flash-success" role="status">{notice}<button onclick={() => notice = ''}>×</button></div>{/if}

      <section class="summary-grid" aria-label="Resumo financeiro">
        <article class="summary-card balance-card"><div class="card-top"><span class="card-label">Gastos no mês</span><span class="card-icon coral">↗</span></div><div class="card-value">{formatMoney(totalSpent)}</div><div class="card-foot"><span class="period-pill">● {monthLabel(summary.month)}</span><span class="muted">Transações confirmadas</span></div><div class="card-decoration"></div></article>
        <article class="summary-card"><div class="card-top"><span class="card-label">Transações</span><span class="card-icon lavender">↕</span></div><div class="card-value">{summary.transaction_count}</div><div class="card-foot"><span class="tiny-dot green"></span><span class="muted">neste mês</span></div></article>
        <article class="summary-card"><div class="card-top"><span class="card-label">Contas conectadas</span><span class="card-icon mint">▤</span></div><div class="card-value">{connections.length}</div><div class="card-foot"><span class="tiny-dot" class:green={connections.length > 0}></span><span class="muted">{connections.length ? 'Sincronização manual' : 'Conecte seu primeiro banco'}</span></div></article>
        <article class="summary-card"><div class="card-top"><span class="card-label">Para revisar</span><span class="card-icon amber">✳</span></div><div class="card-value">{uncategorized}</div><div class="card-foot"><span class="muted">sem categoria</span>{#if uncategorized}<a href="#transacoes" class="review-link">Revisar →</a>{/if}</div></article>
      </section>

      <section class="content-grid">
        <article class="panel transactions-panel" id="transacoes">
          <div class="panel-heading"><div><h2>Transações recentes</h2><p>Seus movimentos financeiros em um só lugar.</p></div><div><button class="text-button" onclick={classifyBatch} disabled={busy || !config.ai_configured || !uncategorized}>Classificar até 10 com IA ✳</button><button class="text-button" onclick={refresh}>Atualizar <span>↻</span></button></div></div>
          <div class="table-tools">
            <label class="search-field"><span>⌕</span><input aria-label="Buscar transações" placeholder="Buscar transações..." bind:value={search} /></label>
            <div class="category-filter-control"><label class="select-wrap"><span>Categoria:</span><select bind:value={categoryFilter}>
              <option value="">Qualquer categoria</option>
              {#if !showAllFilterCategories && categoryFilter && !commonCategories.includes(categoryFilter)}<option value={categoryFilter}>{categoryFilter}</option>{/if}
              {#if showAllFilterCategories}
                {#each config.category_groups as group}<optgroup label={group.name}>{#each group.categories as category}<option value={category}>{category}</option>{/each}</optgroup>{/each}
              {:else}
                {#each commonCategories as category}<option value={category}>{category}</option>{/each}
              {/if}
            </select><span class="select-arrow">⌄</span></label>
            <label class="category-all-toggle"><input type="checkbox" bind:checked={showAllFilterCategories} /> Todas</label></div>
            <label class="select-wrap"><span>Tag:</span><select bind:value={tagFilter}><option value="">Todas</option>{#each tags as tag}<option value={tag.id}>{tag.name}</option>{/each}</select><span class="select-arrow">⌄</span></label>
            <label class="date-filter">De <input aria-label="Data inicial" type="date" bind:value={dateFrom} /></label><label class="date-filter">Até <input aria-label="Data final" type="date" bind:value={dateTo} /></label>
          </div>
          {#if loading}<div class="empty-state"><div class="loader"></div><span>Carregando suas transações…</span></div>
          {:else if transactions.length === 0}<div class="empty-state"><div class="empty-illustration">↕</div><strong>Ainda não há transações</strong><span>Conecte uma conta ou adicione uma transação manualmente para começar.</span><button class="button button-secondary" onclick={() => showAdd = true}>＋ Adicionar transação</button></div>
          {:else}<div class="transaction-list">
            {#each transactions as transaction}
              <article class="transaction-row">
                <div class="merchant-icon" class:income={Number(transaction.amount) < 0}>{categoryIcons[transaction.category] || '·'}</div>
                <div class="transaction-info"><strong>{transaction.merchant || transaction.description}</strong><span>{transaction.description} <i>·</i> {dateFormat.format(new Date(`${transaction.date}T12:00:00`))}{transaction.classification_reason ? ` · IA: ${transaction.classification_reason}` : ''}</span><div class="transaction-tags">{#each transaction.tags as tag}<span class="tag-pill small">◇ {tag.name}</span>{/each}<details class="tag-picker"><summary>＋ Tags</summary><div class="tag-picker-menu">{#each tags as tag}<label><input type="checkbox" checked={transaction.tags.some((assigned) => assigned.id === tag.id)} onchange={() => toggleTag(transaction, tag.id)} />{tag.name}</label>{:else}<span>Crie uma tag para começar.</span>{/each}<a href="#tags">Gerenciar tags →</a></div></details></div></div>
                <div class="transaction-category"><div class="category-select-line"><select aria-label={`Categoria de ${transaction.description}`} value={transaction.category} onchange={(event) => setCategory(transaction, event.currentTarget.value)}>
                  {#if !expandedCategoryIds[transaction.id] && !commonCategories.includes(transaction.category)}<option value={transaction.category}>{transaction.category}</option>{/if}
                  {#if expandedCategoryIds[transaction.id] && !config.categories.includes(transaction.category)}<option value={transaction.category}>{transaction.category}</option>{/if}
                  {#if expandedCategoryIds[transaction.id]}
                    {#each config.category_groups as group}<optgroup label={group.name}>{#each group.categories as category}<option value={category}>{category}</option>{/each}</optgroup>{/each}
                  {:else}
                    {#each commonCategories as category}<option value={category}>{category}</option>{/each}
                  {/if}
                </select><label class="category-all-toggle"><input type="checkbox" checked={Boolean(expandedCategoryIds[transaction.id])} onchange={(event) => expandedCategoryIds[transaction.id] = event.currentTarget.checked} /> Todas</label></div><small class="source-label" class:ai-source={transaction.category_source === 'ai'}>{transaction.category_source === 'pluggy' ? 'Classificada pela Pluggy' : transaction.category_source === 'rule' ? 'Regra por nome' : transaction.category_source === 'ai' ? `IA · ${Math.round((transaction.category_confidence || 0) * 100)}%` : transaction.category_source === 'manual' ? 'Editada por você' : transaction.pending ? 'Pendente' : ''}</small></div>
                <div class="transaction-amount" class:income-amount={Number(transaction.amount) < 0}>{formatMoney(Math.abs(Number(transaction.amount)), transaction.currency)}</div>
                <button class="classify-button" title={transaction.category_source === 'pluggy' ? 'Já classificada pela Pluggy' : transaction.category_source === 'rule' ? 'Classificada por regra' : 'Classificar com IA'} onclick={() => classify(transaction)} disabled={busy || !config.ai_configured || ['pluggy', 'rule'].includes(transaction.category_source)}>✳</button>
              </article>
            {/each}
          </div>{/if}
          <div class="panel-footer"><span>Mostrando {transactions.length} transações</span>{#if hasMore}<button class="text-button" onclick={() => loadTransactions(true)} disabled={listLoading}>Carregar mais <span>→</span></button>{/if}</div>
        </article>

        <div class="right-column">
          <article class="panel categories-panel"><div class="panel-heading compact"><div><h2>Por categoria</h2><p>Gastos confirmados este mês</p></div></div>
            {#if summary.categories.length}<div class="category-breakdown">{#each summary.categories.filter((item) => Number(item.amount) > 0).slice(0, 5) as item}<div class="category-line"><div class="category-line-top"><span><i class="category-bullet" style={`--bullet:${['#d87f65','#8b80c9','#58a58b','#d7a64f','#6293bb'][summary.categories.indexOf(item) % 5]}`}></i>{item.category}</span><strong>{formatMoney(Number(item.amount))}</strong></div><div class="progress-track"><div class="progress-fill" style={`width:${Math.min(100, totalSpent ? Number(item.amount) / totalSpent * 100 : 0)}%;--fill:${['#d87f65','#8b80c9','#58a58b','#d7a64f','#6293bb'][summary.categories.indexOf(item) % 5]}`}></div></div></div>{/each}</div>
            {:else}<div class="mini-empty"><span class="mini-empty-icon">◫</span><span>Suas categorias aparecerão aqui<br />quando houver transações.</span></div>{/if}
            <a class="panel-link" href="#transacoes">Explorar categorias <span>→</span></a>
          </article>
          <article class="panel recurring-panel"><div class="panel-heading"><div><h2>Possíveis recorrências</h2><p>Mesmo estabelecimento em pelo menos 2 meses; confirme manualmente.</p></div></div>{#if recurring.length}<div class="recurring-list">{#each recurring.slice(0, 5) as item}<div><strong>{item.description}</strong><span>{item.months} meses · último {formatMoney(item.last_amount, item.currency)}</span></div>{/each}</div>{:else}<div class="mini-empty">Nenhuma recorrência provável ainda.</div>{/if}</article>
          <article class="ai-card"><div class="ai-card-top"><span class="ai-spark">✳</span><span class="ai-tag">FINANCE BRO AI</span><span class="ai-status"><i></i> {config.ai_configured ? 'PRONTO' : 'AGUARDANDO CHAVE'}</span></div><h3>Menos planilhas.<br />Mais clareza.</h3><p>A IA ajuda a categorizar seus gastos. A descrição e o valor são enviados ao serviço de IA configurado para análise.</p><button class="ai-action" onclick={() => document.querySelector('#transacoes')?.scrollIntoView({ behavior: 'smooth' })}>Revisar transações <span>→</span></button><div class="ai-orbit orbit-one"></div><div class="ai-orbit orbit-two"></div></article>
        </div>
      </section>

      <footer class="page-footer"><span>Finance Bro <i>·</i> dados no SQLite local; Pluggy e IA recebem dados durante o uso</span><span>Feito para dar clareza às suas finanças <b>✳</b></span></footer>
    </div>
    {/if}
  </main>
</div>

{#if pendingCategoryRule}
  <div class="rule-prompt" role="region" aria-label="Aplicar categoria a transações com o mesmo nome" aria-live="polite">
    <strong>Aplicar a todas?</strong>
    <p>Usar <b>{pendingCategoryRule.category}</b> nas transações com o nome <b>{pendingCategoryRule.name}</b>, inclusive nas próximas importações?</p>
    <div class="rule-prompt-actions"><button type="button" class="button button-secondary" disabled={ruleBusy} onclick={() => pendingCategoryRule = null}>Só esta</button><button type="button" class="button button-primary" disabled={ruleBusy} onclick={applyCategoryRule}>{ruleBusy ? 'Aplicando…' : 'Sim, aplicar'}</button></div>
  </div>
{/if}

{#if showAdd}
  <div class="modal-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && (showAdd = false)}>
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1"><div class="modal-heading"><div><div class="eyebrow">REGISTRO MANUAL</div><h2 id="modal-title">Nova transação</h2></div><button class="icon-button" onclick={() => showAdd = false} aria-label="Fechar">×</button></div>
      <form onsubmit={saveTransaction}>
        <label>Descrição<input required bind:value={draft.description} placeholder="Ex.: Mercado da esquina" /></label>
        <div class="form-row"><label>Valor (R$){#if hideAmounts}<input required type="password" inputmode="decimal" autocomplete="off" bind:value={draft.amount} placeholder="•••••" />{:else}<input required type="number" step="0.01" bind:value={draft.amount} placeholder="0,00" />{/if}</label><label>Data<input required type="date" bind:value={draft.date} /></label></div>
        <div class="draft-category-field"><label>Categoria<select bind:value={draft.category}>
          {#if !showAllDraftCategories && !commonCategories.includes(draft.category)}<option value={draft.category}>{draft.category}</option>{/if}
          {#if showAllDraftCategories}
            {#each config.category_groups as group}<optgroup label={group.name}>{#each group.categories as category}<option value={category}>{category}</option>{/each}</optgroup>{/each}
          {:else}
            {#each commonCategories as category}<option value={category}>{category}</option>{/each}
          {/if}
        </select></label><label class="category-all-toggle"><input type="checkbox" bind:checked={showAllDraftCategories} /> Todas</label></div>
        {#if tags.length}<fieldset class="draft-tags"><legend>Tags</legend><div>{#each tags as tag}<label><input type="checkbox" checked={draft.tag_ids.includes(tag.id)} onchange={() => draft.tag_ids = draft.tag_ids.includes(tag.id) ? draft.tag_ids.filter((id) => id !== tag.id) : [...draft.tag_ids, tag.id]} />{tag.name}</label>{/each}</div></fieldset>{/if}
        <div class="modal-actions"><button type="button" class="button button-secondary" onclick={() => showAdd = false}>Cancelar</button><button class="button button-primary">Salvar transação</button></div>
      </form>
    </div>
  </div>
{/if}
