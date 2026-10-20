import portuguese from './locales/pt-BR.json' with { type: 'json' };
import english from './locales/en-US.json' with { type: 'json' };
import serverMessages from './server-messages.json' with { type: 'json' };

export const catalogs = { 'pt-BR': portuguese, 'en-US': english };
export const supportedLocales = Object.keys(catalogs);
export const storageKey = 'finance-bro-locale';
export const message = (key, values = {}) => ({ key, values });

export function resolveLocale(saved, browserLanguage = 'pt-BR') {
  if (supportedLocales.includes(saved)) return saved;
  return browserLanguage.toLowerCase().startsWith('en') ? 'en-US' : 'pt-BR';
}

export function translate(language, key, values = {}) {
  if (!key) return '';
  if (Array.isArray(key)) return key.map((part) => translate(language, part)).join(' | ');
  if (typeof key === 'object') return translate(language, key.key, key.values);
  const current = catalogs[language] ? language : 'pt-BR';
  let text = catalogs[current][key] ?? portuguese[key] ?? key;
  if (typeof text === 'object') {
    const count = Number(values.count);
    text = (count === 0 ? text.zero : undefined) ?? text[new Intl.PluralRules(current).select(count)] ?? text.other;
  }
  return text.replace(/\{(\w+)\}/g, (placeholder, name) => {
    const value = values[name];
    if (value === undefined) return placeholder;
    return typeof value === 'object' ? translate(current, value) : String(value);
  });
}

export function categoryName(language, canonicalName) {
  return catalogs[language]?.categoryNames[canonicalName] ?? canonicalName;
}

export function currencyText(language, value, { currency = 'BRL', hidden = false, ...options } = {}) {
  if (hidden) return `${new Intl.NumberFormat(language, { style: 'currency', currency }).formatToParts(0).find((part) => part.type === 'currency')?.value || currency} •••••`;
  return new Intl.NumberFormat(language, { style: 'currency', currency, ...options }).format(Number(value));
}

export function describeError(error, status) {
  if (error?.translation) return error.translation;
  if (Array.isArray(error)) return error.map((item) => describeError(item.msg || item, status));
  const text = String(error?.message || error || '').replace(/^Value error, /, '');
  if (serverMessages[text]) return message(serverMessages[text]);
  const patterns = [
    [/^A Pluggy recusou as credenciais ou o acesso \(HTTP (\d+)\)\./, 'server.credentials', ['status']],
    [/^A Pluggy falhou ao consultar (.+) \(HTTP (\d+)\)\.$/, 'server.query', ['stage', 'status']],
    [/^Tempo esgotado ao consultar (.+) na Pluggy\.$/, 'server.timeout', ['stage']],
    [/^Falha de comunicação com a Pluggy ao consultar (.+)\.$/, 'server.communication', ['stage']],
    [/^Conexão (.+)\. Verifique a conexão no Meu Pluggy e tente novamente\.$/, 'server.connection', ['status']],
  ];
  for (const [pattern, key, names] of patterns) {
    const match = text.match(pattern);
    if (match) return message(key, Object.fromEntries(names.map((name, index) => [name, match[index + 1]])));
  }
  if (error instanceof TypeError && /fetch|network|load failed/i.test(text)) return message('errors.network');
  if (status === 422) return message('errors.validation');
  return text || message('errors.api', { status });
}
