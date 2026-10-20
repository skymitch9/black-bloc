import { api, apiHref, listOf, names, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  ask,
  bar,
  button,
  card,
  chipBar,
  closeDrawer,
  el,
  field,
  idsIn,
  keepSaying,
  memberPicker,
  notice,
  openDrawer,
  passes,
  run,
  sayAgain,
  sayNothing,
  searchField,
  section,
  settingsPanel,
  table,
  textAction,
  whenField,
} from './ui.js';

const KEY_PREFIX = 'runs_';
const LOG_ROWS = 50;
const NO_LOGS = 'Nothing has happened to the BaF runs yet.';
const NO_RUNS = 'No BaF runs in GDQ events yet.';
const NO_MATCH = 'Nothing here matches.';
const OTHER = '__other';
const ALL = 'all';
const NO_SERIES = '__none';
const VIEWS = [['runs', 'Runs'], ['games', 'Games']];
const HOW_CHIPS = [
  [ALL, 'All', (row) => !row.removed],
  ['tracked', 'Tracked', (row) => !row.removed && row.how === 'tracked'],
  ['imported', 'Imported', (row) => !row.removed && row.how === 'imported'],
  ['hand', 'By hand', (row) => !row.removed && row.how === 'hand'],
  ['removed', 'Removed', (row) => row.removed],
];
const FIELD_WORDS = { date: 'Date', event: 'Event', game: 'Game', category: 'Category', runners: 'Runner(s)', note: 'Note' };

const state = {
  view: 'runs',
  query: '',
  how: ALL,
  year: ALL,
  event: ALL,
  series: ALL,
  runner: ALL,
  sort: { key: 'date', dir: -1 },
};
let payload = { rows: [], events: [], series_names: [] };
let games = [];
let refresh = () => {};

const rowPath = (key, tail = '') => `/api/runs/${encodeURIComponent(key)}${tail}`;

function readHash() {
  const raw = String(location.hash || '').replace(/^#/, '');
  const found = new URLSearchParams(raw);
  if (found.has('q')) {
    state.query = String(found.get('q') || '').trim().toLowerCase();
    state.view = 'runs';
  }
  if (found.get('view') === 'games') state.view = 'games';
}

function writeHash() {
  const parts = new URLSearchParams();
  if (state.query) parts.set('q', state.query);
  if (state.view === 'games') parts.set('view', 'games');
  const text = parts.toString().replace(/\+/g, '%20');
  history.replaceState(null, '', text ? `#${text}` : location.pathname);
}

function dateWord(iso) {
  const at = new Date(iso || '');
  if (!iso || Number.isNaN(at.getTime())) return '';
  return at.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
}

function eventCell(row) {
  const word = row.event_word ? ` · ${row.event_word}` : '';
  if (row.marathon_id) {
    return el('a', { href: `/schedule.html#marathon-${row.marathon_id}`, text: `${row.event}${word}` });
  }
  return `${row.event || '—'}${word}`;
}

function runnersCell(row) {
  return el('span', {}, row.runners.flatMap((one, at) => [
    at ? ', ' : null,
    el('span', {
      class: one.linked ? undefined : 'cell-quiet',
      title: one.linked ? undefined : 'not linked to a member',
      text: one.linked && one.name && one.name.toLowerCase() !== one.display.toLowerCase()
        ? `${one.display} (${one.name})`
        : one.display,
    }),
  ]).filter(Boolean));
}

function chipsFrom(values, allLabel = 'All') {
  return [[ALL, allLabel, null], ...values.map((value) => [value, value, null])];
}

function distinct(list) {
  return [...new Set(list.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b)));
}

function dimensionRules() {
  return [
    { filters: HOW_CHIPS, filter: state.how },
    { filters: [[ALL, 'All', null], [state.year, state.year, (row) => String(row.date || '').startsWith(state.year)]], filter: state.year },
    { filters: [[ALL, 'All', null], [state.event, state.event, (row) => row.event === state.event]], filter: state.event },
    {
      filters: [[ALL, 'All', null], [state.series, state.series, (row) => (state.series === NO_SERIES ? !row.series : row.series === state.series)]],
      filter: state.series,
    },
    {
      filters: [[ALL, 'All', null], [state.runner, state.runner, (row) => row.runners.some((one) => one.display === state.runner)]],
      filter: state.runner,
    },
  ];
}

function rowText(row) {
  return [row.game, row.category, row.runners_text, row.event, row.series, row.note].join(' ');
}

function shownRows() {
  const rules = dimensionRules();
  return payload.rows.filter((row) => rules.every((rule) => passes(row, rule))
    && passes(row, { text: rowText, query: state.query }));
}

const SORTERS = {
  date: (row) => String(row.date || ''),
  event: (row) => String(row.event || '').toLowerCase(),
  game: (row) => row.game_key,
  series: (row) => String(row.series || '').toLowerCase(),
  category: (row) => String(row.category || '').toLowerCase(),
  runners: (row) => String(row.runners_text || '').toLowerCase(),
  how: (row) => row.how,
};

function sorted(rows) {
  const by = SORTERS[state.sort.key] || SORTERS.date;
  return [...rows].sort((a, b) => {
    const left = by(a);
    const right = by(b);
    if (left === right) return 0;
    return (left < right ? -1 : 1) * state.sort.dir;
  });
}

function sortable(node, columns) {
  const heads = node.querySelectorAll('thead th');
  columns.forEach((column, at) => {
    const th = heads[at];
    if (!th || !column.sort) return;
    const on = state.sort.key === column.sort;
    th.setAttribute('aria-sort', on ? (state.sort.dir > 0 ? 'ascending' : 'descending') : 'none');
    th.classList.add('th-sort');
    th.tabIndex = 0;
    const flip = () => {
      state.sort = { key: column.sort, dir: on ? -state.sort.dir : (column.sort === 'date' ? -1 : 1) };
      paint();
    };
    th.addEventListener('click', flip);
    th.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        flip();
      }
    });
    if (on) th.firstChild.textContent = `${column.label} ${state.sort.dir > 0 ? '▲' : '▼'}`;
  });
  return node;
}

function runColumns() {
  return [
    { label: 'Date', sort: 'date', cell: (row) => dateWord(row.date), className: 'mono' },
    { label: 'Event', sort: 'event', cell: eventCell },
    { label: 'Game', sort: 'game', cell: (row) => row.game },
    { label: 'Series', sort: 'series', cell: (row) => row.series },
    { label: 'Category', sort: 'category', cell: (row) => row.category },
    { label: 'Runner(s)', sort: 'runners', cell: runnersCell },
    {
      label: 'How',
      sort: 'how',
      cell: (row) => el('span', { class: 'runs-how' }, [
        el('span', { text: row.removed ? 'removed' : row.edited.length ? `${row.how_word} · edited` : row.how_word }),
        el('button', {
          class: 'btn small quiet',
          type: 'button',
          title: 'Edit this run',
          'aria-label': `Edit ${row.game}`,
          text: '✎',
          on: { click: () => openEditor(row) },
        }),
      ]),
    },
  ];
}

let grid = null;
let counter = null;
let chipHolder = null;

function paintChips() {
  const rows = payload.rows;
  const pick = (name) => (key) => {
    state[name] = key;
    paint();
  };
  const groups = [
    ['How', HOW_CHIPS.map(([key, label]) => [key, label]), 'how'],
    ['Year', chipsFrom(distinct(rows.map((row) => String(row.date || '').slice(0, 4))).reverse()), 'year'],
    ['Event', chipsFrom(distinct(rows.map((row) => row.event))), 'event'],
    ['Series', [...chipsFrom(distinct(rows.map((row) => row.series))), [NO_SERIES, 'No series', null]], 'series'],
    ['Runner', chipsFrom(distinct(rows.flatMap((row) => row.runners.map((one) => one.display)))), 'runner'],
  ];
  chipHolder.replaceChildren(...groups
    .filter(([, choices, name]) => name === 'how' || choices.length > 2 || state[name] !== ALL)
    .map(([label, choices, name]) => el('div', { class: 'runs-chiprow' }, [
      el('span', { class: 'runs-chiplabel', text: label }),
      chipBar(choices, state[name], pick(name)),
    ])));
}

function paint() {
  writeHash();
  if (!grid) return;
  const rows = sorted(shownRows());
  const columns = runColumns();
  const built = rows.length
    ? sortable(table(columns, rows, { search: false }), columns)
    : sayNothing(payload.rows.length ? NO_MATCH : NO_RUNS);
  grid.replaceChildren(built);
  counter.textContent = `${rows.length} of ${payload.rows.filter((row) => !row.removed).length}`;
  paintChips();
}

function runsView() {
  grid = el('div', { class: 'runs-grid' });
  counter = el('span', { class: 'table-count' });
  chipHolder = el('div', { class: 'runs-chips' });
  const search = searchField({
    label: 'Search runs',
    placeholder: 'game, category, runner, event',
    value: state.query,
    onQuery: (value) => {
      state.query = value;
      paint();
    },
  });
  const tools = el('div', { class: 'table-tools' }, [search, el('span', { class: 'table-gap' }), counter]);
  const node = card(null, [tools, chipHolder, grid], { flush: false });
  paint();
  return node;
}

function seriesBox(game, say) {
  const input = el('input', { class: 'input', list: 'runs-series-names', value: game.series || undefined, 'aria-label': `Series of ${game.game}` });
  input.addEventListener('change', async () => {
    const done = await run(
      say,
      () => send(`/api/runs/series/${encodeURIComponent(game.game_key)}`, 'PUT', { series: input.value }),
      (found) => found?.message || 'Saved.',
    );
    if (done.ok) {
      keepSaying('runs.games', say);
      refresh();
    }
  });
  return input;
}

function gamesView() {
  const say = sayAgain('runs.games', notice());
  const columns = [
    {
      label: 'Game',
      cell: (game) => textAction(game.game, () => {
        Object.assign(state, { how: ALL, year: ALL, event: ALL, series: ALL, runner: ALL });
        location.hash = `#q=${encodeURIComponent(game.game_key)}`;
      }),
    },
    { label: 'Series', cell: (game) => seriesBox(game, say) },
    { label: 'Times featured', cell: (game) => String(game.times) },
    { label: 'Last seen', cell: (game) => `${dateWord(game.last_date)} · ${game.last_event || '—'}` },
    { label: 'Runners', cell: (game) => game.runners.join(', ') },
    { label: 'Categories', cell: (game) => game.categories.join(', ') },
  ];
  const list = el('datalist', { id: 'runs-series-names' }, payload.series_names.map((name) => el('option', { value: name })));
  return card(null, [list, table(columns, games, { empty: NO_RUNS, search: true, searchLabel: 'Search games' }), say]);
}

function localValue(iso) {
  if (!iso) return '';
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return '';
  const pad = (value) => String(value).padStart(2, '0');
  return `${when.getFullYear()}-${pad(when.getMonth() + 1)}-${pad(when.getDate())} ${pad(when.getHours())}:${pad(when.getMinutes())}`;
}

function isoOf(local) {
  if (!local) return '';
  const when = new Date(local.replace(' ', 'T'));
  return Number.isNaN(when.getTime()) ? '' : when.toISOString();
}

function was(row, name) {
  if (!row || !row.tracked || !(name in row.tracked)) return null;
  const value = row.tracked[name];
  const shown = name === 'date' ? dateWord(value) : value;
  return el('span', { text: `tracked value: ${shown || '—'}` });
}

function runnersEditor(row) {
  const chosen = (row ? row.runners : []).map((one) => ({ user_id: one.user_id, name: one.name, display: one.display }));
  const chips = el('div', { class: 'chipbar' });
  const paintRunners = () => {
    chips.replaceChildren(...chosen.map((one, at) => el('button', {
      class: 'chip-filter',
      type: 'button',
      'aria-pressed': 'true',
      title: 'Take this runner off',
      text: `${one.display || one.name} ✕`,
      on: {
        click: () => {
          chosen.splice(at, 1);
          paintRunners();
        },
      },
    })));
  };
  const picker = memberPicker({
    label: 'Add a member',
    onPick: (member) => {
      if (!member) return;
      if (!chosen.some((one) => one.user_id === member.id)) chosen.push({ user_id: member.id, name: member.name, display: member.name });
      paintRunners();
      picker.clear();
    },
  });
  const loose = el('input', { class: 'input', placeholder: 'a name as the schedule writes it' });
  const addLoose = button('Add', () => {
    const name = loose.value.trim();
    if (!name) return;
    chosen.push({ user_id: null, name, display: name });
    loose.value = '';
    paintRunners();
  }, { tone: 'quiet' });
  paintRunners();
  const before = JSON.stringify(chosen.map((one) => [one.user_id, one.name]));
  return {
    node: el('div', {}, [field('Runner(s)', chips, was(row, 'runners')), picker.node, field('Add a name', el('div', { class: 'bar' }, [loose, addLoose]))]),
    changed: () => JSON.stringify(chosen.map((one) => [one.user_id, one.name])) !== before,
    payload: () => ({
      runners: chosen.filter((one) => one.user_id).map((one) => ({ user_id: one.user_id, name: one.name })),
      runner_names: chosen.filter((one) => !one.user_id).map((one) => one.name).join('; '),
    }),
  };
}

function eventEditor(row) {
  const tracked = row && row.how === 'tracked';
  const typed = el('input', { class: 'input', value: row ? row.event || undefined : undefined, placeholder: 'BtB 2025' });
  if (tracked) return { node: field('Event', typed, was(row, 'event')), read: () => ({ event: typed.value.trim() }), changed: () => typed.value.trim() !== row.event };
  const select = el('select', { class: 'input' }, [
    el('option', { value: '', text: '—' }),
    ...payload.events.map((one) => el('option', {
      value: String(one.marathon_id),
      text: `${one.name} · ${one.word}${one.archived ? ' · archived' : ''}`,
      selected: row && row.marathon_id === one.marathon_id ? true : undefined,
    })),
    el('option', { value: OTHER, text: 'Other…' }),
  ]);
  if (row && row.event && !row.marathon_id) select.value = OTHER;
  const holder = field('Other event', typed);
  const show = () => { holder.hidden = select.value !== OTHER; };
  select.addEventListener('change', show);
  show();
  const read = () => (select.value === OTHER
    ? { event: typed.value.trim(), marathon_id: null }
    : select.value ? { marathon_id: Number(select.value) } : { event: '', marathon_id: null });
  const start = JSON.stringify(read());
  return { node: el('div', {}, [field('Event', select), holder]), read, changed: () => JSON.stringify(read()) !== start };
}

function openEditor(row = null) {
  const say = notice();
  const when = whenField({ label: 'Date', value: localValue(row ? row.date : ''), zoned: false });
  const wasDate = was(row, 'date');
  if (wasDate) when.node.append(el('p', { class: 'field-help' }, [wasDate]));
  const game = el('input', { class: 'input', value: row ? row.game : undefined });
  const category = el('input', { class: 'input', value: row ? row.category || undefined : undefined });
  const series = el('input', { class: 'input', list: 'runs-editor-series', value: row ? row.series || undefined : undefined });
  const note = el('textarea', { class: 'input', rows: '2' });
  note.value = row ? row.note || '' : '';
  const event = eventEditor(row);
  const runners = runnersEditor(row);

  const changes = () => {
    const found = {};
    const date = isoOf(when.value());
    if (!row || localValue(row.date) !== when.value()) found.date = date;
    if (!row || event.changed()) Object.assign(found, event.read());
    if (!row || game.value.trim() !== row.game) found.game = game.value.trim();
    if (!row || category.value.trim() !== (row.category || '')) found.category = category.value.trim();
    if (!row || runners.changed()) Object.assign(found, runners.payload());
    if (!row || series.value.trim() !== (row.series || '')) found.series = series.value.trim();
    if (!row || note.value.trim() !== (row.note || '')) found.note = note.value.trim();
    return found;
  };

  const after = async (work) => {
    const done = await run(say, work, (found) => found?.message || 'Saved.');
    if (done.ok) {
      closeDrawer();
      keepSaying('runs.page', say);
      refresh();
    }
  };

  const save = button(row ? 'Save' : 'Add the run', () => {
    const wanted = changes();
    if (row && !Object.keys(wanted).length) {
      say.say('Nothing changed, so there is nothing to save.', 'warn');
      return;
    }
    return after(() => (row ? send(rowPath(row.key), 'PUT', wanted) : send('/api/runs', 'POST', wanted)));
  }, { small: false });
  const moves = [save];
  if (row && row.how === 'tracked' && row.edited.length) {
    moves.push(button('Clear edits', () => after(() => send(rowPath(row.key), 'PUT', { clear: true })), { tone: 'quiet' }));
  }
  if (row && row.removed) moves.push(button('Restore', () => after(() => send(rowPath(row.key, '/restore'), 'POST', {})), { tone: 'quiet' }));
  if (row && !row.removed) {
    const word = row.how === 'tracked' ? 'Remove' : 'Delete';
    moves.push(button(word, async () => {
      if (row.how !== 'tracked') {
        const sure = await ask({ title: `Delete ${row.game}?`, body: [`${dateWord(row.date)} · ${row.event || '—'}`], confirmLabel: 'Delete' });
        if (!sure) return;
      }
      await after(() => api(rowPath(row.key), { method: 'DELETE' }));
    }, { tone: 'danger' }));
  }

  openDrawer(row ? row.game : 'Add a run', [
    el('datalist', { id: 'runs-editor-series' }, payload.series_names.map((name) => el('option', { value: name }))),
    when.node,
    event.node,
    field('Game', game, was(row, 'game')),
    field('Category', category, was(row, 'category')),
    runners.node,
    field('Series', series),
    field('Note', note, was(row, 'note')),
    say,
    bar(moves),
  ]);
}

function summaryOf(found) {
  const value = found?.value || {};
  const rows = listOf(value, 'rows');
  return el('div', {}, [
    rows.length ? table([
      { label: 'Date', cell: (one) => dateWord(one.date), className: 'mono' },
      { label: 'Event', cell: (one) => one.event },
      { label: 'Game', cell: (one) => one.game },
      { label: 'Category', cell: (one) => one.category },
      { label: 'Runner(s)', cell: (one) => one.runners_text },
    ], rows, { search: false }) : null,
  ]);
}

function openCsvImport() {
  const say = notice();
  const file = el('input', { class: 'input', type: 'file', accept: '.csv,text/csv' });
  const preview = el('div');
  let text = '';
  const go = el('div', { class: 'bar' });
  const check = async () => {
    preview.replaceChildren();
    go.replaceChildren();
    const done = await run(say, () => send('/api/runs/import', 'POST', { csv: text, dry_run: true }), (found) => found?.message || '');
    if (!done.ok) return;
    preview.replaceChildren(summaryOf(done.found));
    if (done.found.value.would_add) {
      go.replaceChildren(button(`Import ${done.found.value.would_add} row(s)`, async () => {
        const real = await run(say, () => send('/api/runs/import', 'POST', { csv: text, dry_run: false }), (found) => found?.message || 'Imported.');
        if (real.ok) {
          closeDrawer();
          keepSaying('runs.page', say);
          refresh();
        }
      }, { small: false }));
    }
  };
  file.addEventListener('change', async () => {
    const picked = file.files && file.files[0];
    if (!picked) return;
    text = await picked.text();
    check();
  });
  openDrawer('Import CSV', [field('CSV file', file), say, go, preview]);
}

function openEventImport() {
  const say = notice();
  const link = el('input', { class: 'input', type: 'url', placeholder: 'https://tracker.gamesdonequick.com/tracker/event/50' });
  const pairs = {};
  const pairing = el('div');
  const preview = el('div');
  const go = el('div', { class: 'bar' });
  const body = () => ({ event_url: link.value.trim(), pairs });

  const paintUnmatched = (names) => {
    if (!names.length) {
      pairing.replaceChildren();
      return;
    }
    pairing.replaceChildren(el('h3', { text: `Names that match no member (${names.length})` }), ...names.map((one) => {
      const picker = memberPicker({
        label: one.suggest ? `${one.name} — looks like @${one.suggest.username}` : one.name,
        onPick: (member) => {
          if (member) pairs[one.name] = member.id;
          else delete pairs[one.name];
        },
      });
      if (pairs[one.name]) picker.set({ id: pairs[one.name], name: pairs[one.name] });
      return el('details', { class: 'foldout' }, [
        el('summary', { class: 'foldout-head', text: `Pair… ${one.name}` }),
        el('div', { class: 'foldout-body' }, [picker.node]),
      ]);
    }));
  };

  const check = async () => {
    go.replaceChildren();
    const done = await run(say, () => send('/api/runs/import', 'POST', { ...body(), dry_run: true }), (found) => found?.message || '');
    if (!done.ok) return;
    preview.replaceChildren(summaryOf(done.found));
    paintUnmatched(listOf(done.found.value, 'unmatched'));
    go.replaceChildren(
      button('Check again', check, { tone: 'quiet' }),
      done.found.value.would_add || Object.keys(pairs).length
        ? button('Import', async () => {
          const real = await run(say, () => send('/api/runs/import', 'POST', { ...body(), dry_run: false }), (found) => found?.message || 'Imported.');
          if (real.ok) {
            closeDrawer();
            keepSaying('runs.page', say);
            refresh();
          }
        }, { small: false })
        : null,
    );
  };
  openDrawer('Import a GDQ event', [
    field('Tracker event link', link),
    bar([button('Check', check, { small: false })]),
    say,
    go,
    preview,
    pairing,
  ]);
}

async function settingsSection() {
  const all = await settings();
  const specs = settingsNamespace(all, 'marathon').filter((spec) => spec.key.startsWith(KEY_PREFIX));
  const group = section('Settings', null, { count: specs.length || null });
  if (!specs.length) {
    group.body.append(sayNothing('The bot reported no runs_ settings.'));
    return group.node;
  }
  group.body.append(await settingsPanel(specs, { where: 'Settings', onSaved: () => refresh() }));
  return group.node;
}

async function logsSectionNode() {
  const found = await api(`/api/actions?feature=marathon&q=runs.&per_page=${LOG_ROWS}`);
  const rows = listOf(found, 'actions').filter((row) => /^(web\.)?runs\./.test(String(row.kind)));
  await names(idsIn(rows, ['actor_id', 'target_id']));
  const one = section('Logs', null, { count: rows.length });
  one.body.append(logsTable(rows, NO_LOGS));
  return one.node;
}

function asideButtons() {
  return [
    button('Add a run…', () => openEditor(null), { tone: 'warn' }),
    button('Import CSV…', openCsvImport, { tone: 'quiet' }),
    button('Import a GDQ event…', openEventImport, { tone: 'quiet' }),
    el('a', { class: 'btn small quiet', href: apiHref('/api/runs/export.csv'), download: 'baf-runs.csv', text: 'Export CSV' }),
  ];
}

async function load() {
  const [found, grouped] = await Promise.all([api('/api/runs'), api('/api/runs/games')]);
  payload = {
    rows: listOf(found, 'rows'),
    events: listOf(found, 'events'),
    series_names: listOf(found, 'series_names'),
  };
  games = listOf(grouped, 'games');
  const aside = document.getElementById('page-aside');
  if (aside) aside.replaceChildren(bar(asideButtons()));
  const say = sayAgain('runs.page', notice());
  const holder = el('div');
  const showView = () => {
    writeHash();
    holder.replaceChildren(state.view === 'games' ? gamesView() : runsView());
  };
  const views = chipBar(VIEWS, state.view, (key) => {
    state.view = key;
    showView();
  }, { className: 'runs-views' });
  showView();
  document.getElementById('dash').replaceChildren(
    el('div', { class: 'runs-page' }, [views, say, holder]),
    await settingsSection(),
    await logsSectionNode(),
  );
}

readHash();
refresh = start({ tab: 'runs', load });

window.addEventListener('hashchange', () => {
  const before = `${state.view}|${state.query}`;
  readHash();
  if (`${state.view}|${state.query}` !== before) refresh();
});
