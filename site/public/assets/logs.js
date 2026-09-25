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
  textAction,
} from './ui.js';

export const LOG_FEATURES = [
  { feature: 'core', label: 'Dashboard', tab: 'settings' },
  { feature: 'mod', label: 'Moderation', tab: 'moderation' },
  { feature: 'automod', label: 'Automod', tab: 'automod' },
  { feature: 'honeypot', label: 'Honeypot', tab: 'honeypot' },
  { feature: 'modmail', label: 'Modmail', tab: 'modmail' },
  { feature: 'golive', label: 'Go-live', tab: 'golive' },
  { feature: 'youtube', label: 'YouTube', tab: 'golive' },
  { feature: 'pings', label: 'Ping roles', tab: 'golive' },
  { feature: 'events', label: 'Events', tab: 'events' },
  { feature: 'birthday', label: 'Birthdays', tab: 'birthdays' },
  { feature: 'tempvoice', label: 'Temp voice', tab: 'tempvoice' },
  { feature: 'rolemenu', label: 'Role menus', tab: 'rolemenus' },
  { feature: 'poll', label: 'Polls', tab: 'polls' },
  { feature: 'chat', label: 'Chat', tab: 'chat' },
  { feature: 'request', label: 'Requests', tab: 'requests' },
  { feature: 'minutes', label: 'Meeting minutes', tab: 'minutes' },
  { feature: 'raidtrain', label: 'Raid trains', tab: 'events' },
  { feature: 'marathon', label: 'Marathons', tab: 'marathons' },
  { feature: 'applications', label: 'Applications', tab: 'requests' },
  { feature: 'guides', label: 'Guides', tab: 'guides' },
  { feature: 'posts', label: 'Posts', tab: 'posts' },
  // Left out of the unfiltered view by the API itself, so this chip is the only way to it.
  { feature: 'selftest', label: 'Test', tab: 'health' },
  // Every command, panel, modal and button failure is an `error.*` row, headed `core`. This one
  // entry narrows by KIND rather than by feature, so staff can open just the failures without a
  // second filter mechanism on the page (docs/info/errors-design.md §A).
  { kind: 'error', label: 'Errors', tab: 'settings' },
];

const LABELS = new Map(
  LOG_FEATURES.filter((one) => one.feature).map((one) => [one.feature, one.label]),
);

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
  request: 'Filing a request and moving it along are routine; a decision is not.',
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

const VIA_WORDS = { discord: 'Discord', website: 'Website', operator: 'Operator token', forum: 'A forum post' };
const VIA_TITLES = {
  discord: 'Done in Discord — a slash command or a button on one of the bot’s own messages',
  website: 'Done on this dashboard',
  operator: 'Read by a Claude session holding the operator token — it can look, never change',
  forum: 'Started by hand as a post in the requests forum, and taken up from there',
};

/**
 * Owner, 2026-08-27: "add how someone has set a setting, if they set it in
 * discord or on the website". The API sends `via` on every row and derives it
 * from the kind's `web.` head when an older row never recorded it, so a row
 * written before this landed still says something rather than nothing.
 */
export function viaCell(via) {
  const found = VIA_WORDS[via] ? via : null;
  if (!found) return el('span', { class: 'cell-quiet', text: '—' });
  return el('span', {
    class: 'pill viapill',
    'data-via': found,
    title: VIA_TITLES[found],
    text: VIA_WORDS[found],
  });
}

export const LOG_COLUMNS = [
  { label: 'When', help: 'When the bot wrote the line. Hover for the exact time.', cell: (row) => whenCell(row.at) },
  {
    label: 'Kind',
    help: 'The bot’s own name for what happened. Highlighted means important — it acted on ' +
      'a member, or it failed.',
    cell: (row) => kindPill(row),
  },
  { label: 'Via', help: 'Where the thing was done: in Discord, or on this dashboard.', cell: (row) => viaCell(row.via) },
  { label: 'Actor', help: 'Who did it. The bot itself when nobody asked.', cell: (row) => whoCell(row.actor_id, row.actor_name) },
  { label: 'Target', help: 'Who or what it was done to.', cell: (row) => whoCell(row.target_id, row.target_name) },
  { label: 'Summary', cell: (row) => row.summary || row.reason, className: 'wrap' },
];

export function logsTable(rows, empty, emptyAction = null, foot = null) {
  return table(LOG_COLUMNS, rows, { empty, emptyAction, search: false, foot });
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

const SWITCH = 'Switch to All to see the routine lines too.';

function nothingSaid(feature, state) {
  const named = featureLabel(feature);
  const bits = [];
  if (state.query) bits.push(`Nothing ${named} has logged has “${state.query}” in it.`);
  else if (state.kind) bits.push(`${named} has logged nothing of kind ${state.kind}${state.important ? ' that was important' : ''}.`);
  else if (state.important) bits.push(`${named} has logged nothing important.`, ROUTINE[feature]);
  else bits.push(`${named} has logged nothing at all yet.`);
  if (state.important) bits.push(SWITCH);
  return bits.filter(Boolean).join(' ');
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

  const kinds = await kindsFor(feature);
  const chips = el('div', { class: 'chipbar logs-chips' });
  const only = importantSwitch(state.important, (wanted) => {
    state.important = wanted;
    state.page = 1;
    load();
  });

  /** The one thing to do about an empty log: widen whatever narrowed it. */
  const wayOut = () => {
    if (state.important) {
      return textAction('Show every line', () => {
        state.important = false;
        state.page = 1;
        only.setValue('all');
        load();
      });
    }
    if (state.kind || state.query) {
      return textAction('Clear the filters', () => {
        state.kind = '';
        state.query = '';
        state.page = 1;
        const box = tools.querySelector('input');
        if (box) box.value = '';
        paintChips();
        load();
      });
    }
    return null;
  };

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
      return;
    }
    const rows = listOf(payload, 'actions');
    await names(idsIn(rows, ['actor_id', 'target_id']));
    const total = typeof payload.total === 'number' ? payload.total : rows.length;
    group.count(total);
    results.replaceChildren(
      logsTable(rows, nothingSaid(feature, state), rows.length === 0 ? wayOut() : null, {
        noun: 'line',
        total,
        from: (state.page - 1) * perPage + 1,
      }),
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

  const tools = el('div', { class: 'table-tools logs-tools' }, [
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
    only,
  ]);

  paintChips();
  group.body.append(...[
    tools,
    kinds.length > 1 ? chips : null,
    results,
  ].filter(Boolean));
  await load();
  return group.node;
}
