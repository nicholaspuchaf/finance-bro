<script>
  import { t } from '../i18n/index.js';
  let { configured = false, busy = false, onimport = async () => false } = $props();
  let itemId = $state('');

  async function submit(event) {
    event.preventDefault();
    if (!itemId.trim() || busy || !configured) return;
    if (await onimport(itemId.trim())) itemId = '';
  }
</script>

<section class="setup-banner">
  <div class="setup-icon">↗</div><div class="setup-copy"><strong>{$t('pluggy.title')}</strong><span>{$t('pluggy.description')}</span></div>
  <form class="item-form" onsubmit={submit}><input aria-label={$t('pluggy.item')} placeholder={$t('pluggy.itemPlaceholder')} bind:value={itemId} disabled={busy} required /><button class="button button-secondary" disabled={busy || !configured}>{$t('pluggy.import')}</button></form>
</section>
