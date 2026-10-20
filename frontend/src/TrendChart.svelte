<script>
  import { t, currency } from './i18n/index.js';
  let { points = [], type = 'bar', accent = '#d97861', id = 'trend', hideAmounts = false, label = '' } = $props();

  const left = 66;
  const right = 882;
  const top = 22;
  const bottom = 218;
  let maximum = $derived(Math.max(1, ...points.map((point) => Number(point.value))));
  let coordinates = $derived(points.map((point, index) => ({
    ...point,
    x: points.length === 1 ? (left + right) / 2 : left + (right - left) * index / (points.length - 1),
    y: bottom - Number(point.value) / maximum * (bottom - top),
  })));
  let path = $derived(coordinates.map((point, index) => `${index ? 'L' : 'M'} ${point.x} ${point.y}`).join(' '));
  let areaPath = $derived(coordinates.length ? `${path} L ${coordinates[coordinates.length - 1].x} ${bottom} L ${coordinates[0].x} ${bottom} Z` : '');
  let barWidth = $derived(Math.min(36, (right - left) / Math.max(points.length, 1) * 0.66));
  let labelStep = $derived(Math.max(1, Math.ceil(points.length / 7)));

  function compactMoney(value) {
    return $currency(value, { hidden: hideAmounts, notation: 'compact', maximumFractionDigits: 1 });
  }
</script>

<svg class="trend-chart" viewBox="0 0 900 270" role="img" aria-label={label || $t('analytics.trend')}>
  <defs>
    <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color={accent} stop-opacity="0.24" />
      <stop offset="100%" stop-color={accent} stop-opacity="0.015" />
    </linearGradient>
  </defs>
  {#each [0, 0.5, 1] as fraction}
    {@const y = bottom - fraction * (bottom - top)}
    <line x1={left} x2={right} y1={y} y2={y} class="chart-grid-line" />
    <text x="0" y={y + 4} class="chart-axis-label">{compactMoney(maximum * fraction)}</text>
  {/each}
  {#if type === 'bar'}
    {#each coordinates as point}
      <rect x={point.x - barWidth / 2} y={point.y} width={barWidth} height={Math.max(1, bottom - point.y)} rx={Math.min(5, barWidth / 4)} fill={accent} opacity={point.value ? 0.88 : 0.28}>
        <title>{point.label}: {compactMoney(Number(point.value))}</title>
      </rect>
    {/each}
  {:else}
    {#if type === 'area'}<path d={areaPath} fill={`url(#${id})`} />{/if}
    <path d={path} fill="none" stroke={accent} stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
    {#each coordinates as point}
      <circle cx={point.x} cy={point.y} r={points.length > 20 ? 3 : 4} fill="var(--chart-point-fill, #fff)" stroke={accent} stroke-width="2">
        <title>{point.label}: {compactMoney(Number(point.value))}</title>
      </circle>
    {/each}
  {/if}
  {#each coordinates as point, index}
    {#if index % labelStep === 0 || index === points.length - 1}
      <text x={point.x} y="253" text-anchor="middle" class="chart-axis-label chart-x-label">{point.label}</text>
    {/if}
  {/each}
</svg>

<style>
  .trend-chart{display:block;width:100%;height:auto;overflow:visible}
  .chart-grid-line{stroke:var(--chart-grid, #e9e8ee);stroke-width:1;stroke-dasharray:4 6}
  .chart-axis-label{fill:var(--chart-label, #9a99a4);font-size:14px;font-family:ui-sans-serif,system-ui,sans-serif}
  .chart-x-label{font-size:14px}
</style>
