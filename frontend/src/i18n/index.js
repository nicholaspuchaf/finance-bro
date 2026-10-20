import { derived, get, writable } from 'svelte/store';
import { categoryName, currencyText, resolveLocale, storageKey, supportedLocales, translate } from './core.js';
export { describeError, message } from './core.js';

function initialLocale() {
  let saved;
  try { saved = globalThis.localStorage?.getItem(storageKey); } catch { /* Storage may be unavailable. */ }
  return resolveLocale(saved, globalThis.navigator?.language);
}

export const locale = writable(initialLocale());
export const t = derived(locale, (language) => (key, values) => translate(language, key, values));
export const categoryLabel = derived(locale, (language) => (name) => categoryName(language, name));
export const currency = derived(locale, (language) => (value, options) => currencyText(language, value, options));
export const number = derived(locale, (language) => (value, options) => new Intl.NumberFormat(language, options).format(Number(value)));
export const date = derived(locale, (language) => (value, options) => new Intl.DateTimeFormat(language, options).format(value));

export function setLocale(language) {
  if (!supportedLocales.includes(language)) return;
  locale.set(language);
  try { globalThis.localStorage?.setItem(storageKey, language); } catch { /* Storage may be unavailable. */ }
  if (typeof document !== 'undefined') document.documentElement.lang = language;
}

export function toggleLocale() {
  setLocale(get(locale) === 'pt-BR' ? 'en-US' : 'pt-BR');
}

export function initializeI18n() {
  return locale.subscribe((language) => {
    if (typeof document !== 'undefined') document.documentElement.lang = language;
  });
}
