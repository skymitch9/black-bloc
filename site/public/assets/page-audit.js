import { api, apiHref, listOf, names, notesOf } from './api.js';
import { start } from './app.js';
import { syncSubnav } from './layout.js';
import { LOG_FEATURES, featureLabel, importantSwitch, logsTable, viaCell } from './logs.js';
import {
  bar,
  button,
  el,
  field,
  idsIn,
  looksLikeId,
  memberPicker,
  nameNode,
  pager,
  sayNothing,
  searchField,
  section,
  sentenceFor,
  table,
  textAction,
  valueNode,
  when,
} from './ui.js';

const PER_PAGE = 25;

const LOGS_NOTE = 'Every line Black Bloc has written, whether or not it said so in Discord. ' +
  'Important means it acted on a member or something failed; everything else is routine.';
const AUDIT_NOTE = 'Every settings change, whoever made it and however they made it.';

function paramsFor(state, { paged = true } = {}) {
  const found = new URLSearchParams();
  if (paged) {
    found.set('page', String(state.page));
    found.set('per_page', String(PER_PAGE));
  }
  if (state.feature) found.set('feature', state.feature);
  if (state.kind) found.set('kind', state.kind);
  if (state.query) found.set('q', state.query);
  if (state.important) found.set('important', '1');
  if (state.since) found.set('since', state.since);
  if (state.until) found.set('until', state.until);
  if (state.actor) found.set('actor_id', state.actor.id);
  if (state.target) found.set('target_id', state.target.id);
  return found;
}

function nothingSaid(state) {
  const bits = [];
  if (state.feature) bits.push(featureLabel(state.feature));
  if (state.kind) bits.push(`kind ${state.kind}`);
  if (state.query) bits.push(`“${state.query}”`);
  if (state.actor) bits.push(`done by ${state.actor.name}`);
  if (state.target) bits.push(`done to ${state.target.name}`);
  if (state.since || state.until) bits.push(`${state.since || 'the beginning'} to ${state.until || 'now'}`);
  const said = bits.length ? ` for ${bits.join(', ')}` : '';
  return state.important
    ? `Nothing important has been logged${said}. Switch to All to see the routine lines too.`
    : `Nothing has been logged${said}.`;
}

function dateBox(value, onSet) {
  const input = el('input', { class: 'input', type: 'date', value: value || undefined });
  input.addEventListener('change', () => onSet(input.value));
  return input;
}

function settingsTable(rows) {
  return table([
    { label: 'When', cell: (row) => when(row.updated_at || row.at), className: 'mono' },
    { label: 'Key', help: 'The registry key, the name the bot knows the setting by.', cell: (row) => el('span', { class: 'mono', text: row.key }) },
    { label: 'Value', help: 'What it was set TO. An empty value means it was put back to its default.', cell: (row) => valueNode(row.value), className: 'wrap' },
    { label: 'By', cell: (row) => nameNode(row.updated_by_id, row.updated_by_name) },
    { label: 'Via', help: 'Where the change was made: in Discord, or on this dashboard.', cell: (row) => viaCell(row.via) },
  ], rows, { empty: 'No setting has been changed yet.', foot: { noun: 'change', total: rows.length } });
}

function idsInValues(rows) {
  const found = [];
  for (const row of rows) {
    const value = row?.value;
    for (const item of Array.isArray(value) ? value : [value]) {
      if (looksLikeId(String(item ?? ''))) found.push(String(item));
    }
  }
  return found;
}

async function auditSection() {
  const payload = await api('/api/settings/audit?limit=100');
  const rows = listOf(payload, 'audit');
  await names(idsIn(rows, ['updated_by_id']).concat(idsInValues(rows)));
  const one = section('Settings audit', AUDIT_NOTE, { count: rows.length, id: 'settings-audit' });
  one.body.append(settingsTable(rows));
  return { node: one.node, notes: notesOf(payload) };
}

/**
 * The whole log, every filter the route takes. It reloads only its own results
 * so a date change does not rebuild the settings audit under it.
 */
function logsSurface() {
  const state = {
    page: 1,
    feature: '',
    kind: '',
    query: '',
    important: true,
    since: '',
    until: '',
    actor: null,
    target: null,
  };
  const group = section('Logs', LOGS_NOTE, { id: 'logs' });
  const results = el('div', { class: 'logs-results' });
  const chips = el('div', { class: 'chipbar logs-chips' });
  const csv = el('a', {
    class: 'btn small quiet',
    href: '#',
    title: 'The same filters, as a file',
    text: 'Export CSV',
  });

  const again = () => {
    state.page = 1;
    load();
  };

  const paintChips = () => {
    const one = (label, value, title) => el('button', {
      class: 'chip-filter',
      type: 'button',
      'aria-pressed': state.feature === value ? 'true' : 'false',
      title,
      text: label,
      on: {
        click: () => {
          state.feature = state.feature === value ? '' : value;
          paintChips();
          again();
        },
      },
    });
    chips.replaceChildren(
      one('Everything', '', 'Every part of Black Bloc'),
      ...LOG_FEATURES.map((entry) => one(entry.label, entry.feature, `Only ${entry.label}`)),
    );
  };

  const load = async () => {
    csv.setAttribute('href', apiHref(`/api/actions/export.csv?${paramsFor(state, { paged: false })}`));
    let payload;
    try {
      payload = await api(`/api/actions?${paramsFor(state).toString()}`);
    } catch (error) {
      results.replaceChildren(sayNothing(sentenceFor(error).text));
      return;
    }
    const rows = listOf(payload, 'actions');
    await names(idsIn(rows, ['actor_id', 'target_id']));
    const total = typeof payload.total === 'number' ? payload.total : rows.length;
    group.count(total);
    const notes = notesOf(payload);
    results.replaceChildren(
      ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
      logsTable(rows, nothingSaid(state), rows.length === 0 ? wayOut() : null, {
        noun: 'line',
        total,
        from: (state.page - 1) * PER_PAGE + 1,
      }),
      pager({
        page: state.page,
        hasMore: state.page * PER_PAGE < total,
        count: rows.length,
        onPage: (to) => {
          state.page = Math.max(1, to);
          return load();
        },
      }),
    );
    syncSubnav();
  };

  const actor = memberPicker({
    label: 'Done by',
    onPick: (member) => {
      state.actor = member;
      again();
    },
  });
  const target = memberPicker({
    label: 'Done to',
    onPick: (member) => {
      state.target = member;
      again();
    },
  });

  const kind = searchField({
    label: 'Filter by kind',
    placeholder: 'automod. or mod.ban',
    onQuery: (value) => {
      if (value === state.kind) return;
      state.kind = value;
      again();
    },
  });

  const from = dateBox(state.since, (value) => {
    state.since = value;
    again();
  });
  const to = dateBox(state.until, (value) => {
    state.until = value;
    again();
  });

  const search = searchField({
    label: 'Search the log',
    placeholder: 'Search every line…',
    onQuery: (value) => {
      if (value === state.query) return;
      state.query = value;
      again();
    },
  });

  const only = importantSwitch(state.important, (wanted) => {
    state.important = wanted;
    again();
  });

  /** The one thing to do about an empty log: widen whatever narrowed it. */
  const wayOut = () => {
    if (state.important) {
      return textAction('Show every line', () => {
        state.important = false;
        only.setValue('all');
        again();
      });
    }
    const filtered = state.feature || state.kind || state.query || state.since
      || state.until || state.actor || state.target;
    return filtered ? textAction('Clear the filters', () => clear.click()) : null;
  };

  const clear = button('Clear filters', () => {
    Object.assign(state, {
      feature: '', kind: '', query: '', since: '', until: '', actor: null, target: null,
    });
    actor.clear();
    target.clear();
    from.value = '';
    to.value = '';
    for (const box of [search, kind]) box.querySelector('.input.search').value = '';
    paintChips();
    again();
  }, { tone: 'quiet' });

  paintChips();
  group.body.append(
    el('div', { class: 'table-tools logs-tools' }, [
      search,
      only,
      el('span', { class: 'table-gap' }),
      csv,
    ]),
    chips,
    el('div', { class: 'formrow' }, [
      field('From', from, 'The first day to include.'),
      field('To', to, 'The last day to include.'),
      field('Kind', kind, 'The start of a kind, like automod.'),
    ]),
    el('div', { class: 'pickerrow' }, [actor.node, target.node]),
    bar([clear]),
    results,
  );
  return { node: group.node, load };
}

async function load() {
  const surface = logsSurface();
  const audit = await auditSection();
  document.getElementById('dash').replaceChildren(
    ...(audit.notes.length ? [el('p', { class: 'section-note', text: audit.notes.join(' ') })] : []),
    surface.node,
    audit.node,
  );
  await surface.load();
}

start({ tab: 'audit', load });
