<script>
  import { t } from '../i18n/index.js';
  let { configured = false, transactionsHref = '#transacoes' } = $props();
</script>

<article class="ai-card">
  <div class="ai-card-top"><span class="ai-spark">✳</span><span class="ai-tag">FINANCE BRO AI</span><span class="ai-status"><i></i> {configured ? $t('ai.ready') : $t('ai.waiting')}</span></div>
  <h3>{$t('ai.headline')}<br />{$t('ai.clarity')}</h3>
  <p>{$t('ai.description')}</p>
  <a class="ai-action" href={transactionsHref}>{$t('ai.review')} <span>→</span></a>
  <div class="ai-orbit orbit-one"></div><div class="ai-orbit orbit-two"></div>
</article>

<style>
  .ai-action { display: inline-block; }
</style>
