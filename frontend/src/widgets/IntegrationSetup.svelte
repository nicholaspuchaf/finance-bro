<script>
  import { t } from '../i18n/index.js';
  let { pluggyConfigured = false, aiConfigured = false } = $props();
</script>

{#if !pluggyConfigured || !aiConfigured}
  <section class="setup-banner">
    <div class="setup-icon">✳</div><div class="setup-copy"><strong>{$t('setup.title')}</strong><span>{$t('setup.before')} <code>.env</code> {$t('setup.after')}</span></div>
    <div class="setup-steps"><span class:ready={pluggyConfigured}><b>{pluggyConfigured ? '✓' : '1'}</b> Pluggy</span><span class:ready={aiConfigured}><b>{aiConfigured ? '✓' : '2'}</b> {$t('ai.short')}</span></div>
  </section>
{/if}
