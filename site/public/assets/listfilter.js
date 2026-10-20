export function matches(text, query, { match = 'text' } = {}) {
  const wanted = String(query ?? '').trim().toLowerCase();
  if (!wanted) return true;
  return match === 'words' ? runsMatches(wanted, text) : String(text ?? '').toLowerCase().includes(wanted);
}

export function ruleOf(filters, key) {
  const list = filters || [];
  const found = list.find(([one]) => one === key) || list[0];
  return found ? found[2] || null : null;
}

export function passes(item, { text = () => '', filters = null, filter = null, query = '', match = 'text' } = {}) {
  const rule = ruleOf(filters, filter);
  return (!rule || Boolean(rule(item))) && matches(text(item), query, { match });
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

export const UPPER_WORDS = ['2d', '3d', 'fps', 'tps', 'rpg', 'jrpg', 'mmo', 'rts'];

export function genreEntries(text) {
  return String(text ?? '').split(',').map((part) => part.split(/\s+/).filter(Boolean).join(' ')).filter(Boolean);
}

export function genreUpper(text) {
  return [...new Set(String(text ?? '').split(/[,\n]/).map(genreNormal).filter(Boolean))];
}

function formatEntry(entry, upper) {
  const text = entry.replace(/[-_]/g, ' ').split(/\s+/).filter(Boolean).join(' ').toLowerCase();
  if (!text) return '';
  const wanted = new Set(upper);
  return (text.slice(0, 1).toUpperCase() + text.slice(1)).split(' ')
    .map((word) => (wanted.has(word.toLowerCase()) ? word.toUpperCase() : word)).join(' ');
}

export function genreFormat(text, qualifiers = [], families = [], upper = UPPER_WORDS) {
  const kept = [];
  const seen = new Set();
  for (const entry of genreEntries(text)) {
    const shown = formatEntry(entry, upper);
    const family = genreFamily(shown, qualifiers, families) || genreNormal(shown);
    if (shown && !seen.has(family)) {
      seen.add(family);
      kept.push(shown);
    }
  }
  return kept.join(', ');
}

export function genreFamiliesOf(text, qualifiers = [], families = []) {
  return [...new Set(genreEntries(text).map((entry) => genreFamily(entry, qualifiers, families)).filter(Boolean))];
}

export function aliasWords(name, aliases = []) {
  const wanted = genreNormal(name);
  if (!wanted) return [];
  const found = aliases.find(([key, more]) => wanted === key || more.includes(wanted));
  return found ? [found[0], ...found[1]] : [];
}

export function familyLabel(family) {
  const text = String(family ?? '');
  return text.slice(0, 1).toUpperCase() + text.slice(1);
}

export function familyTerms(family, families = []) {
  const found = families.find(([name]) => name === family);
  return found ? [found[0], ...found[1]].join(' ') : String(family ?? '');
}

const LETTERS_THEN_DIGITS = /^(\p{L}+)(\p{N}*)$/u;
const FUZZY_LETTERS = 5;
const INITIALS_LETTERS = 2;
const preparedHaystacks = new Map();

function preparedHaystack(haystack) {
  const text = String(haystack ?? '');
  let lines = preparedHaystacks.get(text);
  if (lines) return lines;
  lines = text.split(/\r?\n/).map((line) => genreNormal(line).split(' ').filter(Boolean))
    .filter((words) => words.length)
    .map((words) => ({ words, initials: words.map((word) => word[0]).join('') }));
  if (preparedHaystacks.size > 8192) preparedHaystacks.clear();
  preparedHaystacks.set(text, lines);
  return lines;
}

export function oneEdit(a, b) {
  if (a === b) return true;
  if (Math.abs(a.length - b.length) > 1) return false;
  if (a.length === b.length) {
    const diff = [];
    for (let at = 0; at < a.length; at += 1) if (a[at] !== b[at]) diff.push(at);
    if (diff.length === 1) return true;
    return diff.length === 2 && diff[1] === diff[0] + 1 && a[diff[0]] === b[diff[1]] && a[diff[1]] === b[diff[0]];
  }
  const [short, long] = a.length < b.length ? [a, b] : [b, a];
  let at = 0;
  while (at < short.length && short[at] === long[at]) at += 1;
  return short.slice(at) === long.slice(at + 1);
}

function initialsHit(word, words, initials) {
  const found = LETTERS_THEN_DIGITS.exec(word);
  if (!found || found[1].length < INITIALS_LETTERS) return false;
  const [, letters, digits] = found;
  let start = initials.indexOf(letters);
  while (start >= 0) {
    const after = start + letters.length;
    if (!digits || (after < words.length && words[after] === digits)) return true;
    start = initials.indexOf(letters, start + 1);
  }
  return false;
}

function wordHits(word, lines) {
  if (/^\p{N}+$/u.test(word)) return lines.some(({ words }) => words.includes(word));
  const fuzzy = (word.match(/\p{L}/gu) || []).length >= FUZZY_LETTERS;
  return lines.some(({ words, initials }) => words.some((one) => one.startsWith(word) || (fuzzy && oneEdit(word, one)))
    || initialsHit(word, words, initials));
}

export function runsMatches(query, haystack) {
  const wanted = genreNormal(query).split(' ').filter(Boolean);
  if (!wanted.length) return false;
  const lines = preparedHaystack(haystack);
  return wanted.every((word) => wordHits(word, lines));
}

export function runsSearchText(row, families = [], developers = []) {
  const familyWords = (row.genre_families || []).flatMap((family) => {
    const found = families.find(([name]) => name === family);
    return found ? [found[0], ...found[1]] : [family];
  });
  const lines = [
    row.game, row.series, row.genre, ...familyWords, row.developer, ...aliasWords(row.developer, developers), row.category,
    ...row.runners.map((one) => one.display), ...row.runners.map((one) => one.name), row.event, row.note,
  ];
  return [...new Set(lines.filter(Boolean).map(String))].join('\n');
}

export function runsGames(rows) {
  const grouped = new Map();
  for (const row of rows.filter((one) => !one.removed)) {
    if (!grouped.has(row.game_key)) grouped.set(row.game_key, []);
    grouped.get(row.game_key).push(row);
  }
  return [...grouped.entries()].map(([key, runs]) => {
    const newest = [...runs].sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')) || String(b.key).localeCompare(String(a.key)));
    const last = newest[0];
    return {
      game: last.game,
      game_key: key,
      series: last.series,
      genre: last.genre,
      genre_family: last.genre_family,
      genre_families: last.genre_families,
      developer: last.developer,
      times: runs.length,
      last_date: last.date,
      last_event: last.event,
      runners: [...new Set(newest.flatMap((run) => run.runners.map((one) => one.display)).filter(Boolean))],
      categories: [...new Set(newest.map((run) => run.category).filter(Boolean))],
      keys: newest.map((run) => run.key),
    };
  }).sort((a, b) => String(b.last_date || '').localeCompare(String(a.last_date || '')) || b.game_key.localeCompare(a.game_key));
}

export const RUNS_CSV_COLUMNS = ['key', 'date', 'event', 'event_source', 'event_ref', 'game', 'series', 'genre', 'developer', 'category', 'runners', 'runner_names', 'runner_ids', 'how', 'note'];

export function runsCsv(rows) {
  const cell = (value) => {
    const text = value === null || value === undefined ? '' : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const lines = [RUNS_CSV_COLUMNS.join(',')];
  for (const row of rows.filter((one) => !one.removed)) {
    lines.push([
      row.key, row.date || '', row.event, row.event_source || '', row.event_ref || '', row.game, row.series, row.genre, row.developer, row.category,
      row.runners_text, row.runners.map((one) => one.name).join('; '), row.runners.map((one) => one.user_id || '').join('; '), row.how, row.note,
    ].map(cell).join(','));
  }
  return `${lines.join('\n')}\n`;
}

export function pageOf(total, size, page) {
  const per = Math.max(1, Math.floor(Number(size)) || 1);
  const pages = Math.max(1, Math.ceil(Math.max(0, total) / per));
  const at = Math.min(pages, Math.max(1, Math.floor(Number(page)) || 1));
  const from = total ? (at - 1) * per : 0;
  return { page: at, pages, from, to: Math.min(total, from + per), total };
}

export function pageWords({ pages, from, to, total }, whole = total) {
  if (pages > 1) return `${from + 1}–${to} of ${total}`;
  return `${total} of ${whole}`;
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
