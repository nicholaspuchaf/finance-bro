<script>
  import TrendChart from './TrendChart.svelte';
  import CategorySelector from './CategorySelector.svelte';
  import './analytics.css';

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
      const response = await fetch(`/api/analytics?${query}`, { cache: 'no-store' });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Falha ao carregar a análise (${response.status}).`);
      }
      const result = await response.json();
      if (current === requestNumber) analysis = result;
    } catch (cause) {
      if (current === requestNumber) error = cause.message;
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
    if (hideAmounts) return 'R$ •••••';
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value));
  }

  function monthName(value, year = false) {
    if (!value) return '—';
    return new Intl.DateTimeFormat('pt-BR', { month: 'short', ...(year ? { year: 'numeric' } : {}) }).format(new Date(`${value.slice(0, 7)}-02T12:00:00`));
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
  let categorySelectionLabel = $derived(categorySelectionCount === 0 ? 'Todas as categorias' : categorySelectionCount === 1 ? (selectedMacros[0] || selectedCategories[0]) : `${categorySelectionCount} categorias agregadas`);
  let selectedTags = $derived(tags.filter((tag) => selectedTagIds.includes(tag.id)));
  let tagSelectionLabel = $derived(selectedTags.length === 0 ? 'Todas as tags' : selectedTags.length === 1 ? selectedTags[0].name : `${selectedTags.length} tags agregadas`);
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
    <div><span class="analytics-eyebrow">✳ &nbsp; CENTRO DE ANÁLISE</span><h1>Seus números, com perspectiva.</h1><p>Entenda o ritmo do seu dinheiro e encontre o que merece atenção.</p></div>
    <a class="analytics-back" href="#transacoes">Ver transações <span>↗</span></a>
  </div>

  <div class="analytics-toolbar">
    <div class="analytics-segment" role="group" aria-label="Tipo de análise">
      <button type="button" class:active={mode === 'expenses'} aria-pressed={mode === 'expenses'} onclick={() => chooseMode('expenses')}>↗ &nbsp; Gastos</button>
      <button type="button" class:active={mode === 'investments'} aria-pressed={mode === 'investments'} onclick={() => chooseMode('investments')}>◈ &nbsp; Investimentos</button>
    </div>
    <div class="analytics-filters">
      <CategorySelector {categories} {categoryGroups} value="" all={showAllCategories} macro={showMacroCategories} allowMacro resetOnSelect label="Categoria:" placeholder="Qualquer categoria" ariaLabel="Adicionar categoria à análise" onselect={addCategory} onallchange={(checked) => { showAllCategories = checked; if (checked) showMacroCategories = false; }} onmacrochange={(checked) => { showMacroCategories = checked; if (checked) showAllCategories = false; }} />
      <details class="analytics-category-picker analytics-tag-picker"><summary><span>Tags</span><strong>{tagSelectionLabel}</strong><i aria-hidden="true">⌄</i></summary><div class="analytics-category-menu"><div class="analytics-category-menu-head"><strong>Filtrar por tags</strong></div><p>Selecione uma ou mais tags. Uma transação com várias tags conta uma vez.</p><div class="analytics-category-options" role="group" aria-label="Tags para agregar">{#each tags as tag}<label><input type="checkbox" checked={selectedTagIds.includes(tag.id)} onchange={() => toggleTag(tag.id)} /><span>{tag.name}</span><small>{tag.transaction_count}</small></label>{:else}<span class="analytics-no-categories">Nenhuma tag criada. Use a página Tags para adicionar.</span>{/each}</div><div class="analytics-category-menu-foot"><button type="button" onclick={() => selectedTagIds = []} disabled={!selectedTagIds.length}>Limpar</button><button type="button" onclick={(event) => event.currentTarget.closest('details').open = false}>Concluir</button></div></div></details>
      <div class="analytics-period-control"><div class="analytics-period-heading"><span>Período</span><output aria-live="polite">{months === 1 ? 'Mês atual' : `Últimos ${months} meses`}</output></div><div class="analytics-period-options" role="group" aria-label="Período da análise">{#each [1, 3, 6, 12, 24] as option}<button type="button" class:active={months === option} aria-pressed={months === option} onclick={() => chooseMonths(option)}>{months === option ? '✓ ' : ''}{option} {option === 1 ? 'mês' : 'meses'}</button>{/each}</div></div>
    </div>
  </div>
  {#if categorySelectionCount}<div class="analytics-selected-categories" aria-label="Categorias agregadas"><span>Agregando</span>{#each selectedCategories as item}<button type="button" aria-label={`Remover categoria ${item}`} onclick={() => toggleCategory(item)}>{item} <b aria-hidden="true">×</b></button>{/each}{#each selectedMacros as item}<button type="button" aria-label={`Remover macro-categoria ${item}`} onclick={() => toggleMacro(item)}>{item} (macro) <b aria-hidden="true">×</b></button>{/each}<button type="button" class="clear-selected" onclick={() => { selectedCategories = []; selectedMacros = []; }}>Limpar seleção</button></div>{/if}
  {#if selectedTags.length}<div class="analytics-selected-categories analytics-tag-selection" aria-label="Tags selecionadas"><span>Tags</span>{#each selectedTags as tag}<button type="button" aria-label={`Remover tag ${tag.name}`} onclick={() => toggleTag(tag.id)}>{tag.name} <b aria-hidden="true">×</b></button>{/each}<button type="button" class="clear-selected" onclick={() => selectedTagIds = []}>Limpar tags</button></div>{/if}

  {#if error}<div class="analytics-error" role="alert">{error} <button type="button" onclick={loadAnalysis}>Tentar novamente</button></div>{/if}
  {#if loading && !analysis}<div class="analytics-loading" role="status"><div class="loader"></div> Preparando sua análise…</div>
  {:else if analysis}
    {#if loading}<div class="analytics-updating" role="status"><div class="loader"></div> Atualizando análise…</div>{/if}
    <div class="analytics-hero">
      <div class="analytics-hero-copy"><span class="analytics-kicker">{mode === 'expenses' ? 'TOTAL DE GASTOS' : 'APORTES IDENTIFICADOS'} · {categorySelectionLabel.toUpperCase()}{selectedTags.length ? ` · ${tagSelectionLabel.toUpperCase()}` : ''}</span><strong>{money(total)}</strong><span class="analytics-hero-period">{analysis.months === 1 ? 'Mês atual' : `Últimos ${analysis.months} meses`} <i>·</i> {monthName(analysis.period_start, true)} — {monthName(analysis.period_end, true)} <i>·</i> {analysis.count} {analysis.count === 1 ? 'lançamento' : 'lançamentos'}</span></div>
      <div class="analytics-hero-mark" aria-hidden="true">{mode === 'expenses' ? '↗' : '◈'}</div>
    </div>

    <div class="analytics-stat-grid">
      <article class="analytics-stat"><span>Média por mês</span><strong>{money(total / months)}</strong><small>Nos {months} {months === 1 ? 'mês' : 'meses'} da análise</small></article>
      <article class="analytics-stat"><span>Mês de maior movimento</span><strong>{peakMonth && Number(peakMonth.amount) ? money(peakMonth.amount) : '—'}</strong><small>{peakMonth && Number(peakMonth.amount) ? monthName(peakMonth.month, true) : 'Sem lançamentos no período'}</small></article>
      <article class="analytics-stat"><span>{mode === 'expenses' ? 'Categorias com movimento' : 'Entradas relacionadas'}</span><strong>{mode === 'expenses' ? analysis.categories.length : money(analysis.inflows)}</strong><small>{mode === 'expenses' ? 'Na seleção atual' : 'Resgates ou proventos classificados'}</small></article>
      <article class="analytics-stat"><span>Transações analisadas</span><strong>{analysis.count}</strong><small>Confirmadas em BRL</small></article>
    </div>

    <div class="analytics-main-grid">
      <section class="analytics-card analytics-trend-panel" aria-labelledby="monthly-title">
        <div class="analytics-card-top"><div><span class="analytics-section-kicker">01 / VISÃO AMPLA</span><h2 id="monthly-title">Evolução mensal</h2><p>{mode === 'expenses' ? 'Quanto saiu em cada mês' : 'Aportes identificados em cada mês'}{categorySelectionCount ? ` · ${categorySelectionLabel}` : ''}</p></div><div class="chart-switch" role="group" aria-label="Tipo do gráfico mensal"><button type="button" class:active={monthlyChart === 'bar'} aria-label="Colunas" aria-pressed={monthlyChart === 'bar'} title="Colunas" onclick={() => monthlyChart = 'bar'}>▥</button><button type="button" class:active={monthlyChart === 'line'} aria-label="Linha" aria-pressed={monthlyChart === 'line'} title="Linha" onclick={() => monthlyChart = 'line'}>⌁</button><button type="button" class:active={monthlyChart === 'area'} aria-label="Área" aria-pressed={monthlyChart === 'area'} title="Área" onclick={() => monthlyChart = 'area'}>◢</button></div></div>
        {#if total}<div class="analytics-chart-scroll"><TrendChart points={monthlyPoints} type={monthlyChart} accent={mode === 'expenses' ? '#db806a' : '#8877c6'} id="monthly-fill" {hideAmounts} label="Evolução mensal em reais" /></div>{:else}<div class="analytics-empty">Nenhum {mode === 'expenses' ? 'gasto' : 'aporte'} encontrado para esta seleção.<span>Experimente outro período ou categoria.</span></div>{/if}
        <div class="analytics-chart-foot"><span>◌ &nbsp; {months} {months === 1 ? 'mês' : 'meses'} de análise</span><span>O mês atual está em andamento</span></div>
      </section>

      <section class="analytics-card analytics-composition" aria-labelledby="composition-title">
        <div class="analytics-card-top"><div><span class="analytics-section-kicker">02 / COMPOSIÇÃO</span><h2 id="composition-title">Por categoria</h2><p>{categorySelectionCount || selectedTags.length ? 'Distribuição dentro dos filtros selecionados' : 'Distribuição geral do período'}</p></div></div>
        {#if overallTotal}
          <div class="analytics-donut-wrap"><div class="analytics-donut" style={`background:${donutGradient}`} role="img" aria-label="Distribuição por categoria"><div><small>TOTAL</small><strong>{money(overallTotal)}</strong></div></div></div>
          <div class="analytics-legend"><button type="button" class:chosen={!categorySelectionCount} onclick={() => { selectedCategories = []; selectedMacros = []; }}><span class="legend-name"><i class="legend-dot all"></i>Todas</span><b>100%</b></button>{#each topCategories as item, index}<button type="button" class:chosen={selectedCategories.includes(item.category)} onclick={() => toggleCategory(item.category)}><span class="legend-name"><i class="legend-dot" style={`background:${palette[index]}`}></i>{item.category}</span><span class="legend-metric"><b>{money(item.amount)}</b><small>{Math.round(Number(item.amount) / overallTotal * 100)}%</small></span></button>{/each}</div>
        {:else}<div class="analytics-empty small">As categorias aparecem quando houver lançamentos.</div>{/if}
      </section>
    </div>

    <section class="analytics-card analytics-daily-panel" aria-labelledby="daily-title">
      <div class="analytics-card-top"><div><span class="analytics-section-kicker">03 / DIA A DIA</span><h2 id="daily-title">Dentro do mês</h2><p>{dailyView === 'daily' ? 'Movimento em cada dia' : 'Total acumulado ao longo dos dias'} · {monthName(analysis.selected_month, true)}</p></div><div class="analytics-daily-controls">{#if analysis.monthly.length > 1}<label>Mês <select value={selectedMonth || analysis.selected_month} onchange={(event) => selectedMonth = event.currentTarget.value}>{#each analysis.monthly as item}<option value={item.month}>{monthName(item.month, true)}</option>{/each}</select></label>{:else}<span class="analytics-month-label">{monthName(analysis.selected_month, true)}</span>{/if}<div class="chart-switch" role="group" aria-label="Tipo do gráfico diário"><button type="button" class:active={dailyChart === 'bar'} aria-label="Colunas" aria-pressed={dailyChart === 'bar'} title="Colunas" onclick={() => dailyChart = 'bar'}>▥</button><button type="button" class:active={dailyChart === 'line'} aria-label="Linha" aria-pressed={dailyChart === 'line'} title="Linha" onclick={() => dailyChart = 'line'}>⌁</button><button type="button" class:active={dailyChart === 'area'} aria-label="Área" aria-pressed={dailyChart === 'area'} title="Área" onclick={() => dailyChart = 'area'}>◢</button></div></div></div>
      <div class="analytics-daily-view" role="group" aria-label="Forma de acompanhar os dias"><button type="button" class:active={dailyView === 'daily'} aria-pressed={dailyView === 'daily'} onclick={() => dailyView = 'daily'}>Por dia</button><button type="button" class:active={dailyView === 'cumulative'} aria-pressed={dailyView === 'cumulative'} onclick={() => dailyView = 'cumulative'}>Acumulado</button></div>
      <div class="analytics-daily-body"><div class="analytics-daily-chart">{#if selectedMonthTotal}<div class="analytics-chart-scroll"><TrendChart points={dailyPoints} type={dailyChart} accent={mode === 'expenses' ? '#8b7ec9' : '#65aa93'} id="daily-fill" {hideAmounts} label="Evolução diária em reais" /></div>{:else}<div class="analytics-empty">Sem movimentos neste mês.<span>Escolha outro mês para explorar.</span></div>{/if}</div><aside class="analytics-daily-insight"><span>EM {monthName(analysis.selected_month, true).toUpperCase()}</span><strong>{money(selectedMonthTotal)}</strong><small>{mode === 'expenses' ? 'Gastos do mês' : 'Aportes do mês'}</small><div class="insight-divider"></div><span>DIA DE MAIOR MOVIMENTO</span><b>{peakDay && Number(peakDay.amount) ? `${peakDay.date.slice(-2)} de ${monthName(analysis.selected_month)}` : '—'}</b><small>{peakDay && Number(peakDay.amount) ? money(peakDay.amount) : 'Nenhum movimento'}</small></aside></div>
    </section>
    <p class="analytics-method">{mode === 'expenses' ? 'Gastos confirmados em BRL. Transferências, investimentos e pagamentos de fatura ficam fora do cálculo.' : 'Aportes = saídas positivas classificadas como investimentos. Entradas relacionadas incluem resgates e proventos; estes gráficos não representam saldo ou rentabilidade da carteira.'}</p>
  {/if}
</div>
