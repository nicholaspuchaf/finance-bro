<script>
  import { locale, t, toggleLocale } from './i18n/index.js';
</script>

<button type="button" class="locale-toggle" onclick={toggleLocale}
  title={$t($locale === 'pt-BR' ? 'language.english' : 'language.portuguese')}
  aria-label={$t($locale === 'pt-BR' ? 'language.english' : 'language.portuguese')}>
  <img src={$locale === 'pt-BR' ? '/flags/br.svg' : '/flags/us.svg'} alt="" width="24" height="16" />
</button>

<style>
  .locale-toggle{display:grid;place-items:center;flex:none;width:32px;height:32px;padding:0;border:0;border-radius:0;background:transparent;line-height:1;cursor:pointer}
  .locale-toggle:focus-visible{outline:2px solid var(--coral);outline-offset:3px}
  img{display:block;width:24px;height:16px;border-radius:2px}
</style>
