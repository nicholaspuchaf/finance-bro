<script>
  let { label, value, icon, tone = 'lavender', highlighted = false, footer } = $props();
</script>

<article class="summary-card" class:balance-card={highlighted}>
  <div class="card-top"><span class="card-label">{label}</span><span class={`card-icon ${tone}`}>{icon}</span></div>
  <div class="card-value">{value}</div>
  {#if footer}<div class="card-foot">{@render footer()}</div>{/if}
  {#if highlighted}<div class="card-decoration"></div>{/if}
</article>
