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

const byName = (a, b) => String(a).localeCompare(String(b), undefined, { sensitivity: 'base' });

export function countedChoices(items, valuesOf, { order = byName, label = (value) => value } = {}) {
  const counts = new Map();
  for (const item of items || []) {
    for (const value of new Set((valuesOf(item) || []).filter(Boolean))) counts.set(value, (counts.get(value) || 0) + 1);
  }
  return [...counts.keys()].sort(order).map((value) => [value, `${label(value)} (${counts.get(value)})`]);
}

export function genreNormal(text) {
  return String(text ?? '').toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean).join(' ');
}

export function genreQualifiers(text) {
  const found = [];
  for (const part of String(text ?? '').split(/[,\n]/)) {
    const word = genreNormal(part);
    if (word && !found.includes(word)) found.push(word);
  }
  const size = (one) => one.split(' ').length;
  return found.sort((a, b) => size(b) - size(a) || b.length - a.length);
}

export function familyLines(text) {
  const families = [];
  const bad = [];
  String(text ?? '').split(/\r?\n/).forEach((line, at) => {
    if (!line.trim()) return;
    const colon = line.indexOf(':');
    const name = colon < 0 ? '' : genreNormal(line.slice(0, colon));
    if (!name) {
      bad.push([at + 1, line.trim()]);
      return;
    }
    const aliases = [...new Set(line.slice(colon + 1).split(',').map(genreNormal).filter(Boolean))];
    families.push([name, aliases]);
  });
  return { families, bad };
}

export function genreFamilies(text) {
  return familyLines(text).families;
}

function withoutQualifiers(text, qualifiers) {
  let words = text.split(' ').filter(Boolean);
  for (const qualifier of qualifiers) {
    const cut = qualifier.split(' ');
    const kept = [];
    for (let at = 0; at < words.length;) {
      if (cut.every((word, step) => words[at + step] === word)) {
        at += cut.length;
      } else {
        kept.push(words[at]);
        at += 1;
      }
    }
    words = kept;
  }
  return words.join(' ');
}

export function genreFamily(text, qualifiers = [], families = []) {
  const full = genreNormal(text);
  if (!full) return '';
  const stripped = withoutQualifiers(full, qualifiers) || full;
  for (const candidate of [full, stripped]) {
    for (const [name, aliases] of families) {
      if (candidate === name || aliases.includes(candidate)) return name;
    }
  }
  return stripped;
}

export function familyLabel(family) {
  const text = String(family ?? '');
  return text.slice(0, 1).toUpperCase() + text.slice(1);
}

export function familyTerms(family, families = []) {
  const found = families.find(([name]) => name === family);
  return found ? [found[0], ...found[1]].join(' ') : String(family ?? '');
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
