export function matches(text, query) {
  const wanted = String(query ?? '').trim().toLowerCase();
  return !wanted || String(text ?? '').toLowerCase().includes(wanted);
}

export function ruleOf(filters, key) {
  const list = filters || [];
  const found = list.find(([one]) => one === key) || list[0];
  return found ? found[2] || null : null;
}

export function passes(item, { text = () => '', filters = null, filter = null, query = '' } = {}) {
  const rule = ruleOf(filters, filter);
  return (!rule || Boolean(rule(item))) && matches(text(item), query);
}

export function applyFilters(items, options = {}) {
  const hits = (items || []).map((item) => passes(item, options));
  return { hits, shown: hits.filter(Boolean).length, total: hits.length };
}

export const BLOCK_FILTERS = [
  ['all', 'All', null],
  ['on_post', 'On a post', (kind) => (kind.on || []).length > 0],
  ['no_post', 'On no post', (kind) => (kind.on || []).length === 0],
  ['exclusive', 'One at a time', (kind) => Boolean(kind.exclusive)],
];

export function blockText(kind) {
  return [kind.name, kind.where, ...(kind.keys || []).map((key) => key.replace(/_/g, ' '))].join(' ');
}
