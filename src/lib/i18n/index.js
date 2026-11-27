// Minimal i18n lookup. Only English exists today, but every string in the
// app is routed through here so adding a locale later just means adding a
// sibling file (e.g. `de.js`) with the same shape and registering it below.
import en from './en.js';

const locales = { en };

const DEFAULT_LOCALE = 'en';

// No locale switcher UI yet, so this always resolves to English.
let currentLocale = DEFAULT_LOCALE;

export function setLocale(locale) {
  if (locales[locale]) currentLocale = locale;
}

export function getLocale() {
  return currentLocale;
}

/**
 * Look up a dotted message path (e.g. "app.title") in the active locale,
 * falling back to English. If the resolved value is a function, it is
 * called with `args` (spread) and the result returned; otherwise the string
 * is returned as-is.
 */
export function t(path, ...args) {
  const messages = locales[currentLocale] || locales[DEFAULT_LOCALE];
  const value = resolve(messages, path) ?? resolve(locales[DEFAULT_LOCALE], path);
  if (value === undefined) return path;
  return typeof value === 'function' ? value(...args) : value;
}

function resolve(messages, path) {
  return path.split('.').reduce((node, key) => (node == null ? undefined : node[key]), messages);
}
