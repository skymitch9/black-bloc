import { api, listOf, nameRecord, names } from './api.js';
import { tabHref } from './app.js';
import { syncSubnav } from './layout.js';
import {
  ago,
  el,
  idsIn,
  nameNode,
  pager,
  sayNothing,
  searchField,
  section,
  segment,
  sentenceFor,
  table,
} from './ui.js';

export const LOG_FEATURES = [
  { feature: 'core', label: 'Dashboard', tab: 'settings' },
  { feature: 'mod', label: 'Moderation', tab: 'moderation' },
  { feature: 'automod', label: 'Automod', tab: 'automod' },
  { feature: 'honeypot', label: 'Honeypot', tab: 'honeypot' },
  { feature: 'modmail', label: 'Modmail', tab: 'modmail' },
  { feature: 'golive', label: 'Go-live', tab: 'golive' },
  { feature: 'events', label: 'Events', tab: 'events' },
  { feature: 'birthday', label: 'Birthdays', tab: 'birthdays' },
  { feature: 'tempvoice', label: 'Temp voice', tab: 'tempvoice' },
  { feature: 'rolemenu', label: 'Role menus', tab: 'rolemenus' },
  { feature: 'poll', label: 'Polls', tab: 'polls' },
  { feature: 'chat', label: 'Chat', tab: 'chat' },
];

const LABELS = new Map(LOG_FEATURES.map((one) => [one.feature, one.label]));

export function featureLabel(feature) {
  return LABELS.get(feature) || String(feature || 'Black Bloc');
}

const PER_PAGE = 10;
const PROBE = 200;

const NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in Discord. ' +
  'Important means it acted on a member or failed.';

const ROUTINE = {
  core: 'Settings changes are routine, so nothing here is marked important.',
  chat: 'Chat replies are routine, so nothing here is marked important.',
  tempvoice: 'Rooms opening and closing are routine.',
  poll: 'Creating a poll and reminding people about it are routine.',
};

export function kindPill(row) {
  return el('span', {
    class: 'pill kindpill',
    'data-important': row.important ? 'true' : 'false',
    title: row.important
      ? `${row.kind} — important: it acted on a member, or it failed`
      : `${row.kind} — routine`,
    text: String(row.kind || '—'),
  });
}

function whenCell(iso) {
  const said = ago(iso);
  return el('span', { class: 'cell-quiet', title: said.title, text: said.text });
}

/**
 * A member gets a link to Members; a role or a channel is a name and nothing
 * more, because Members has nothing to say about either.
 */
function whoCell(id, given) {
  if (id === null || id === undefined || id === '') return null;
  const node = nameNode(id, given);
  const record = nameRecord(String(id));
  if (record && record.kind !== 'member') return node;
  const who = given || (record && (record.display_name || record.name)) || String(id);
  return el('a', {
    class: 'celllink',
    href: `${tabHref('members')}?q=${encodeURIComponent(who)}`,
    title: `Find ${who} on Members`,
  }, [node]);
}

export function logsTable(rows, empty) {
  return table([
    { label: 'When', cell: (row) => whenCell(row.at) },
    { label: 'Kind', cell: (row) => kindPill(row) },
    { label: 'Actor', cell: (row) => whoCell(row.actor_id, row.actor_name) },
    { label: 'Target', cell: (row) => whoCell(row.target_id, row.target_name) },
    { label: 'Summary', cell: (row) => row.summary || row.reason, className: 'wrap' },
  ], rows, { empty, search: false });
}

/** The importance switch every logs surface wears, in the site's own segments. */
export function importantSwitch(current, onChange) {
  const node = segment(
    [{ value: 'important', label: 'Important' }, { value: 'all', label: 'All' }],
    current ? 'important' : 'all',
    { onChange: () => onChange(node.readValue() === 'important') },
  );
  node.setAttribute('aria-label', 'Which log lines to show');
  return node;
}

const kindsOnce = new Map();

/**
 * The chips are the kinds this feature has actually logged, read once from a
 * wide unfiltered page. The route carries no list of them, so this is the only
 * way to offer chips that are never a dead end.
 */
async function kindsFor(feature) {
  if (!kindsOnce.has(feature)) {
    const payload = await api(`/api/actions?feature=${encodeURIComponent(feature)}&per_page=${PROBE}`);
    const found = new Set(listOf(payload, 'actions').map((row) => String(row.kind)));
    kindsOnce.set(feature, [...found].sort());
  }
  return kindsOnce.get(feature);
}

export function forgetKinds() {
  kindsOnce.clear();
}

function chip(label, pressed, onPick, title = null) {
  return el('button', {
    class: 'chip-filter',
    type: 'button',
    'aria-pressed': pressed ? 'true' : 'false',
    title: title || undefined,
    text: label,
    on: { click: onPick },
  });
}

function nothingSaid(feature, state) {
  const named = featureLabel(feature);
  if (state.query) return `Nothing ${named} has logged has “${state.query}” in it.`;
  if (state.kind) return `${named} has logged nothing of kind ${state.kind}${state.important ? ' that was important' : ''}.`;
  if (state.important) {
    const said = ROUTINE[feature] || '';
    return `${named} has logged nothing important. ${said} Switch to All to see every line.`.replace('  ', ' ');
  }
  return `${named} has logged nothing at all yet.`;
}

/**
 * The Logs block every feature page carries at its foot. It fetches and pages
 * itself rather than going through the page's own reload, so nothing above it
 * is rebuilt when somebody changes a filter down here.
 */
export async function logsSection(feature, { title = 'Logs', note = NOTE, perPage = PER_PAGE } = {}) {
  const state = { page: 1, kind: '', query: '', important: true };
  const group = section(title, note, { id: `logs-${feature}` });
  const results = el('div', { class: 'logs-results' });
  const count = el('span', { class: 'table-count' });

  const kinds = await kindsFor(feature);
  const chips = el('div', { class: 'chipbar' });

  const paintChips = () => {
    chips.replaceChildren(
      chip('All kinds', state.kind === '', () => {
        state.kind = '';
        state.page = 1;
        paintChips();
        load();
      }),
      ...kinds.map((kind) => chip(kind, state.kind === kind, () => {
        state.kind = state.kind === kind ? '' : kind;
        state.page = 1;
        paintChips();
        load();
      }, `Only ${kind}`)),
    );
  };

  const load = async () => {
    const params = new URLSearchParams({
      feature,
      page: String(state.page),
      per_page: String(perPage),
    });
    if (state.important) params.set('important', '1');
    if (state.kind) params.set('kind', state.kind);
    if (state.query) params.set('q', state.query);

    let payload;
    try {
      payload = await api(`/api/actions?${params.toString()}`);
    } catch (error) {
      results.replaceChildren(sayNothing(sentenceFor(error).text));
      count.textContent = '';
      return;
    }
    const rows = listOf(payload, 'actions');
    await names(idsIn(rows, ['actor_id', 'target_id']));
    const total = typeof payload.total === 'number' ? payload.total : rows.length;
    count.textContent = `${rows.length} of ${total} line${total === 1 ? '' : 's'}`;
    group.count(total);
    results.replaceChildren(
      logsTable(rows, nothingSaid(feature, state)),
      pager({
        page: state.page,
        hasMore: state.page * perPage < total,
        count: rows.length,
        onPage: (to) => {
          state.page = Math.max(1, to);
          return load();
        },
      }),
    );
    syncSubnav();
  };

  paintChips();
  group.body.append(...[
    el('div', { class: 'table-tools' }, [
      searchField({
        label: `Search the ${featureLabel(feature)} log`,
        placeholder: 'Search these lines…',
        onQuery: (query) => {
          if (query === state.query) return;
          state.query = query;
          state.page = 1;
          load();
        },
      }),
      importantSwitch(state.important, (only) => {
        state.important = only;
        state.page = 1;
        load();
      }),
      count,
    ]),
    kinds.length > 1 ? chips : null,
    results,
  ].filter(Boolean));
  await load();
  return group.node;
}
