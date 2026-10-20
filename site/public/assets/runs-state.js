import { genreFamiliesOf, runsGames, runsSearchText } from './listfilter.js';

export const ALL = 'all';
export const NO_TAG = '__none';
export const PICKS = ['event', 'runner', 'series', 'genre', 'developer'];
export const DEMO_FLAG = 'demo';
export const REAL_PAGE = '/runs.html';
export const DEMO_SOURCES = ['gdq', 'gdq_hotfix'];
export const DEMO_PARTS = ['runner'];
const EVENT_WORDS = { gdq: 'GDQ', gdq_hotfix: 'GDQ Hotfix' };

export function freshState(given = {}) {
  return {
    view: 'runs',
    query: '',
    gamesQuery: '',
    year: ALL,
    event: '',
    runner: '',
    series: '',
    genre: '',
    developer: '',
    removed: false,
    demo: false,
    page: 1,
    sort: { key: 'date', dir: -1 },
    ...given,
  };
}

export function readRunsHash(text) {
  const found = new URLSearchParams(String(text || '').replace(/^#/, ''));
  const state = freshState({
    query: String(found.get('q') || '').trim().toLowerCase(),
    gamesQuery: String(found.get('gq') || '').trim().toLowerCase(),
    view: found.get('view') === 'games' ? 'games' : 'runs',
    year: found.get('year') || ALL,
    removed: found.get('removed') === '1',
    demo: found.has(DEMO_FLAG),
    page: Math.max(1, Math.floor(Number(found.get('page'))) || 1),
  });
  for (const name of PICKS) state[name] = found.get(name) || '';
  if (state.genre !== NO_TAG) state.genre = state.genre.toLowerCase();
  return state;
}

export function runsHashText(state) {
  const parts = new URLSearchParams();
  if (state.query) parts.set('q', state.query);
  if (state.view === 'games') parts.set('view', 'games');
  if (state.gamesQuery) parts.set('gq', state.gamesQuery);
  if (state.year !== ALL) parts.set('year', state.year);
  for (const name of PICKS) if (state[name]) parts.set(name, state[name]);
  if (state.removed) parts.set('removed', '1');
  if (state.page > 1) parts.set('page', String(state.page));
  const text = parts.toString().replace(/\+/g, '%20');
  return [state.demo ? DEMO_FLAG : '', text].filter(Boolean).join('&');
}

export function filterKey(state) {
  return JSON.stringify([
    state.view, state.query, state.gamesQuery, state.year, state.removed, state.sort.key, state.sort.dir,
    ...PICKS.map((name) => state[name]),
  ]);
}

export function settledPage(state, lastKey) {
  const key = filterKey(state);
  return { page: key === lastKey ? state.page : 1, key };
}

const byName = (a, b) => String(a).localeCompare(String(b), undefined, { sensitivity: 'base' });

export function demoPayload(file, { qualifiers = [], families = [], developers = [] } = {}) {
  const rows = (file?.rows || []).map((given) => {
    const genreFamilies = genreFamiliesOf(given.genre, qualifiers, families);
    const row = {
      event_ref: null,
      marathon_id: null,
      tracked: {},
      carried: [],
      folded: [],
      edited: [],
      removed: false,
      note: '',
      ...given,
      genre_family: genreFamilies[0] || '',
      genre_families: genreFamilies,
    };
    row.search = runsSearchText(row, families, developers);
    return row;
  }).sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')) || String(b.key).localeCompare(String(a.key)));
  const names = (tag) => [...new Set(rows.map((row) => row[tag]).filter(Boolean))].sort(byName);
  const events = (file?.events || []).map((one, at) => ({
    marathon_id: at + 1,
    name: one.name,
    source: one.source,
    word: EVENT_WORDS[one.source] || one.source,
    starts_at: one.starts_at,
    archived: true,
  }));
  return {
    found: {
      rows,
      events,
      series_names: names('series'),
      genre_names: names('genre'),
      developer_names: names('developer'),
      genre_families: families.map(([family, aliases]) => ({ family, aliases })),
      sources: DEMO_SOURCES,
      parts: DEMO_PARTS,
    },
    grouped: { games: runsGames(rows) },
  };
}

export class DemoRefused extends Error {
  constructor(text, href = REAL_PAGE) {
    super(text);
    this.href = href;
    this.tone = 'warn';
    this.code = 'demo';
  }
}

export function writeGuard({ isDemo, refusal, send, api }) {
  const refuse = () => Promise.reject(new DemoRefused(refusal()));
  return {
    send: (path, method, body) => (isDemo() ? refuse() : send(path, method, body)),
    remove: (path) => (isDemo() ? refuse() : api(path, { method: 'DELETE' })),
  };
}
