import { api, listOf, names, send } from './api.js';
import { start } from './app.js';
import { shellStatus } from './shell.js';
import {
  ask,
  badge,
  bar,
  button,
  card,
  duration,
  el,
  field,
  icon,
  idsIn,
  memberPicker,
  nameNode,
  notice,
  pager,
  run,
  searchField,
  section,
  shortWhen,
  when,
} from './ui.js';

const KINDS = ['warn', 'timeout', 'kick', 'ban', 'unban'];
const DESTRUCTIVE = ['kick', 'ban', 'unban'];
const PILL_FEATURES = [['automod', 'Automod'], ['honeypot', 'Honeypot']];

const FILTERS = [
  ['all', 'All', null],
  ['warn', 'Warns', ['warn']],
  ['timeout', 'Timeouts', ['timeout']],
  ['ban', 'Bans', ['ban', 'unban']],
  ['note', 'Notes', ['note']],
];

const STATS = [
  ['Cases', null],
  ['Warns', 'warn'],
  ['Timeouts', 'timeout'],
  ['Bans', 'ban'],
];

const COLUMNS = ['Case', 'Member', 'Type', 'Reason', 'By', 'When', ''];

const state = { page: 1, userFilter: null, userName: null, openCase: null, kind: 'all', query: '' };

let refresh = () => {};

function modePills(status) {
  const modes = new Map();
  for (const row of (status && status.features) || []) modes.set(row.feature, row.mode);
  const nodes = [];
  for (const [feature, label] of PILL_FEATURES) {
    if (!modes.has(feature)) continue;
    const mode = modes.get(feature);
    const blank = mode === null || mode === undefined || mode === '';
    nodes.push(el('span', { class: 'pill-label', text: label }));
    nodes.push(el('span', {
      class: 'pill',
      'data-mode': blank ? 'off' : String(mode),
      text: blank ? 'not set' : String(mode),
    }));
  }
  return nodes;
}

function statStrip(payload, rows) {
  const tiles = STATS.map(([label, kind]) => {
    const value = kind === null
      ? (payload && payload.total !== undefined && payload.total !== null ? payload.total : rows.length)
      : rows.filter((row) => String(row.kind) === kind).length;
    return el('div', { class: 'stat' }, [
      el('span', { class: 'stat-value', 'data-blank': Number(value) === 0 ? 'true' : undefined, text: String(value) }),
      el('span', { class: 'stat-label', text: label }),
    ]);
  });
  return el('div', { class: 'statgrid' }, tiles);
}

function cell(value, className) {
  if (value === null || value === undefined || value === '') {
    return el('span', { class: 'cell-quiet', text: '—' });
  }
  return el('span', { class: className, text: String(value) });
}

function caseRow(row) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    'data-search': `${row.id} ${row.kind} ${row.user_name || row.user_id || ''} ${row.reason || ''} ${row.moderator_name || ''}`.toLowerCase(),
    on: {
      click: () => {
        state.openCase = row.id;
        refresh();
      },
    },
  }, [
    el('span', { class: 'cell-id', text: `#${row.id}` }),
    el('span', { class: 'cell-name' }, [nameNode(row.user_id, row.user_name)]),
    el('span', { class: 'cell-kind' }, [
      el('span', { class: 'kind-dot', 'data-kind': String(row.kind) }),
      el('span', { text: String(row.kind) }),
      row.applied === false ? el('span', { class: 'pill small', 'data-mode': 'shadow', text: 'shadow' }) : null,
    ]),
    cell(row.reason, 'cell-reason'),
    el('span', { class: 'cell-quiet' }, [nameNode(row.moderator_id, row.moderator_name)]),
    el('span', { class: 'cell-quiet', text: shortWhen(row.at).text, title: shortWhen(row.at).title }),
    icon('chevronRight', 16),
  ]);
}

function toolbar(rows, onPaint) {
  const said = el('span', { class: 'table-count' });
  const chips = FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key,
    'aria-pressed': state.kind === key ? 'true' : 'false',
    text: label,
    on: {
      click: (event) => {
        state.kind = key;
        for (const chip of event.currentTarget.parentElement.children) {
          chip.setAttribute('aria-pressed', chip.getAttribute('data-kind') === key ? 'true' : 'false');
        }
        onPaint();
      },
    },
  }));
  const search = searchField({
    label: 'Search cases',
    placeholder: 'Search cases…',
    onQuery: (query) => {
      state.query = query;
      onPaint();
    },
  });
  const node = el('div', { class: 'card-head' }, [
    search,
    el('div', { class: 'chipbar' }, chips),
    el('span', { class: 'topbar-gap' }),
    said,
  ]);
  node.say = (shown) => {
    said.textContent = `${shown} case${shown === 1 ? '' : 's'}`;
  };
  node.say(rows.length);
  return node;
}

function casesCard(payload, rows) {
  const head = el('div', { class: 'grid-row head' }, COLUMNS.map((label) => el('span', { text: label })));
  const lines = rows.map(caseRow);
  const foot = el('div', { class: 'grid-foot' });
  const body = el('div', { class: 'grid-table' }, [head, ...lines, foot]);

  let tools = null;
  const paint = () => {
    const wanted = FILTERS.find(([key]) => key === state.kind);
    const kinds = wanted ? wanted[2] : null;
    let shown = 0;
    lines.forEach((line, at) => {
      const row = rows[at];
      const kindHit = kinds === null || kinds.includes(String(row.kind));
      const textHit = state.query === '' || (line.getAttribute('data-search') || '').includes(state.query);
      const hit = kindHit && textHit;
      line.hidden = !hit;
      if (hit) shown += 1;
    });
    foot.textContent = `Showing ${shown} of ${rows.length} case${rows.length === 1 ? '' : 's'}`;
    if (tools) tools.say(shown);
  };
  tools = toolbar(rows, paint);
  paint();

  const hasMore = payload && payload.pages ? state.page < payload.pages : rows.length >= 10;
  return el('div', { class: 'card' }, [
    tools,
    rows.length === 0
      ? el('div', {
        class: 'grid-foot',
        text: state.userFilter ? 'That member has no cases.' : 'No cases have been written yet.',
      })
      : el('div', { class: 'table-scroll' }, [body]),
    pager({
      page: state.page,
      hasMore,
      count: rows.length,
      onPage: (to) => {
        state.page = Math.max(1, to);
        refresh();
      },
    }),
  ]);
}

function actionBar() {
  const say = notice();
  const picker = memberPicker({ label: 'Member' });
  const kind = el('select', { class: 'input' });
  for (const one of KINDS) kind.append(el('option', { value: one, text: one }));
  const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — the member is told this' });
  const length = el('input', { class: 'input', type: 'number', min: '60', step: '60', value: '300' });
  const lengthField = field('Timeout length, seconds', length, 'Discord refuses anything over 28 days.');
  const paintLength = () => { lengthField.hidden = kind.value !== 'timeout'; };
  kind.addEventListener('change', paintLength);
  paintLength();

  const go = button('Do it', async () => {
    if (!picker.id) {
      say.say('Pick the member this is about first.', 'warn');
      return;
    }
    const what = kind.value;
    if (DESTRUCTIVE.includes(what)) {
      const sure = await ask({
        title: `${what} ${picker.name}?`,
        body: [
          `This goes through the same path the slash command uses: a case is written, the mod log gets a line and ${picker.name} is told, depending on mod_dm_on_action.`,
          `Reason: ${reason.value.trim() || '(none yet — the bot will refuse without one)'}`,
        ],
        confirmLabel: `Yes, ${what}`,
      });
      if (!sure) return;
    }
    const body = { user_id: picker.id, reason: reason.value.trim() };
    if (what === 'timeout') body.duration = Number(length.value);
    const done = await run(say, () => send(`/api/mod/${what}`, 'POST', body), (found) =>
      found?.message || `Done — ${what} for ${picker.name}.`);
    if (done.ok) refresh();
  }, { tone: 'warn', small: false });

  return card(null, [
    picker.node,
    el('div', { class: 'formrow' }, [field('What', kind), field('Reason', reason)]),
    lengthField,
    bar([go]),
    say,
  ]);
}

async function caseDetail(id) {
  const found = await api(`/api/mod/cases/${encodeURIComponent(id)}`);
  const row = found && found.case ? found.case : found;
  await names([row.user_id, row.moderator_id]);
  const say = notice();
  const apply = button('Apply now', async () => {
    const sure = await ask({
      title: `Apply case ${row.id}?`,
      body: [
        `This carries out what the shadow run only logged: ${(row.actions || [row.kind]).join(', ')} against ${row.user_name || row.user_id}.`,
      ],
      confirmLabel: 'Apply it',
    });
    if (!sure) return;
    const done = await run(say, () => send(`/api/mod/cases/${encodeURIComponent(row.id)}/apply`, 'POST', {}),
      'Applied. The case now says it was carried out.');
    if (done.ok) refresh();
  });

  return card(null, [
    el('div', { class: 'formrow' }, [
      el('p', {}, ['Member: ', nameNode(row.user_id, row.user_name)]),
      el('p', {}, ['Moderator: ', nameNode(row.moderator_id, row.moderator_name)]),
    ]),
    el('p', { text: `${row.kind}${row.duration_s ? ` for ${duration(row.duration_s)}` : ''} · ${when(row.at)} · mode ${row.mode}` }),
    el('p', { text: `Reason: ${row.reason || 'none given'}` }),
    el('p', {}, [
      'Carried out: ',
      row.applied ? badge('yes', 'ok') : badge('no — shadow only', 'warn'),
      ...(Array.isArray(row.failed) && row.failed.length ? [' ', badge(`failed: ${row.failed.join(', ')}`, 'danger')] : []),
    ]),
    row.applied ? null : bar([apply]),
    say,
  ]);
}

async function load() {
  const query = new URLSearchParams({ page: String(state.page) });
  if (state.userFilter) query.set('user_id', state.userFilter);
  const [status, payload] = await Promise.all([
    shellStatus(),
    api(`/api/mod/cases?${query.toString()}`),
  ]);
  const rows = listOf(payload, 'cases');
  await names(idsIn(rows, ['user_id', 'moderator_id']));

  const aside = document.getElementById('page-aside');
  if (aside) aside.replaceChildren(...modePills(status));

  const picker = memberPicker({
    label: 'Only this member',
    onPick: (member) => {
      state.userFilter = member ? member.id : null;
      state.userName = member ? member.name : null;
      state.page = 1;
      state.openCase = null;
      refresh();
    },
  });

  const act = section('Take an action', 'Every one of these is the same code path as the slash command, and lands in the same case table.');
  act.body.append(actionBar());

  const only = section(
    'Only one member',
    state.userName ? `Filtered to ${state.userName}.` : 'Ask the bot for one member’s cases instead of the whole page.',
  );
  only.body.append(picker.node);

  const nodes = [statStrip(payload, rows), casesCard(payload, rows), act.node, only.node];
  if (state.openCase !== null) {
    const detail = section(`Case ${state.openCase}`, null, { id: 'case', open: true });
    detail.body.append(await caseDetail(state.openCase));
    nodes.push(detail.node);
  }

  document.getElementById('dash').replaceChildren(...nodes);
}

refresh = start({ tab: 'moderation', load });
