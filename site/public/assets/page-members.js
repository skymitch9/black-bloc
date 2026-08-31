import { api, listOf } from './api.js';
import { start, tabHref } from './app.js';
import {
  avatar,
  el,
  icon,
  pager,
  roleChip,
  sayNothing,
  searchField,
  shortWhen,
  textAction,
  untilWhen,
} from './ui.js';

const FILTERS = [
  ['all', 'All'],
  ['staff', 'Staff'],
  ['bots', 'Bots'],
  ['new', 'New this week'],
];

const STATS = [
  ['Members', 'total'],
  ['Humans', 'humans'],
  ['Bots', 'bots'],
  ['Staff', 'staff'],
  ['Joined this week', 'new_7d'],
];

const COLUMNS = [
  ['Member', null],
  ['Joined', 'When they joined the server. Hover for the date.'],
  ['Roles', 'Every role they wear. A role Black Bloc is holding a clock on says how long is left.'],
  ['Cases', 'How many moderation cases have their name on them.'],
  ['', null],
];
const ROLES_SHOWN = 3;

/** A Logs row links here by name, so the box starts filled in with what it asked for. */
const asked = new URLSearchParams(location.search).get('q');

const state = { page: 1, filter: 'all', query: (asked || '').trim().toLowerCase() };

let refresh = () => {};

function statStrip(payload) {
  return el('div', { class: 'statgrid' }, STATS.map(([label, key]) => {
    const value = payload && typeof payload[key] === 'number' ? payload[key] : null;
    return el('div', { class: 'stat' }, [
      el('span', {
        class: 'stat-value',
        'data-blank': value === null || value === 0 ? 'true' : undefined,
        text: value === null ? '—' : String(value),
      }),
      el('span', { class: 'stat-label', text: label }),
    ]);
  }));
}

/**
 * A role Black Bloc is holding a clock on wears the days it has left, so the
 * list says which of somebody's roles is temporary without opening anything.
 */
function roleChips(roles) {
  const found = Array.isArray(roles) ? roles : [];
  const nodes = found.slice(0, ROLES_SHOWN).map((role) => {
    const until = role.expires_at ? untilWhen(role.expires_at) : null;
    const left = until && until.days >= 0 ? `${until.days} d` : null;
    return roleChip(role.name, {
      color: role.color,
      note: until ? (left || 'due') : null,
      title: until ? `${role.name} — runs out ${until.text} (${until.title})` : role.name,
    });
  });
  if (found.length > ROLES_SHOWN) {
    nodes.push(el('span', { class: 'role-more', text: `+${found.length - ROLES_SHOWN}` }));
  }
  if (nodes.length === 0) nodes.push(el('span', { class: 'cell-quiet', text: '—' }));
  return el('span', { class: 'cell-roles' }, nodes);
}

function joinedCell(iso) {
  if (!iso) return el('span', { class: 'cell-quiet', title: 'Discord never told the bot when they joined', text: '—' });
  const stamp = shortWhen(iso);
  return el('span', { class: 'cell-quiet', title: stamp.title, text: stamp.text });
}

/**
 * The row carries two links, so it is a div: the name goes to their cases and
 * the chevron to their role requests and timed roles. An anchor inside an
 * anchor is invalid HTML and every click would land on the outer one.
 */
function memberRow(row) {
  const who = String(row.name || row.username || row.id);
  return el('div', { class: 'grid-row rowlink', title: `Discord id ${row.id}` }, [
    el('a', {
      class: 'cell-member',
      href: `${tabHref('moderation')}?member=${encodeURIComponent(row.id)}`,
      title: `${who}'s cases`,
    }, [
      avatar(who, row.avatar),
      el('span', { class: 'cell-member-text' }, [
        el('span', { class: 'cell-member-name', text: who }),
        el('span', { class: 'cell-member-tag', text: String(row.username || row.id) }),
      ]),
    ]),
    joinedCell(row.joined_at),
    roleChips(row.roles),
    row.cases
      ? el('span', { class: 'count', text: String(row.cases) })
      : el('span', { class: 'cell-quiet', text: '—' }),
    el('a', {
      class: 'chip-go',
      href: `${tabHref('rolemenus')}?member=${encodeURIComponent(row.id)}`,
      title: `${who}'s role requests and timed roles`,
    }, [icon('chevronRight', 16)]),
  ]);
}

function toolbar() {
  const chips = FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key,
    'aria-pressed': state.filter === key ? 'true' : 'false',
    text: label,
    on: {
      click: () => {
        state.filter = key;
        state.page = 1;
        refresh();
      },
    },
  }));
  return el('div', { class: 'card-head' }, [
    searchField({
      label: 'Search members',
      placeholder: 'Search members…',
      value: state.query,
      onQuery: (query) => {
        if (query === state.query) return;
        state.query = query;
        state.page = 1;
        refresh();
      },
    }),
    el('div', { class: 'chipbar' }, chips),
  ]);
}

function nothingSaid() {
  if (state.query) return `No member's name or username has “${state.query}” in it.`;
  if (state.filter === 'new') return 'Nobody has joined in the last seven days.';
  if (state.filter === 'bots') return 'There are no bots in the server.';
  if (state.filter === 'staff') return 'No role can see the staff channel yet, so Black Bloc counts nobody as staff.';
  return 'Black Bloc cannot see any members yet. That is a cache it fills on connect, not a fault with your access.';
}

/** Nothing to show and a filter on means the filter is the thing to undo. */
function nothingToDo() {
  if (!state.query && state.filter === 'all') return null;
  return textAction('Show every member', () => {
    state.query = '';
    state.filter = 'all';
    state.page = 1;
    refresh();
  });
}

function membersCard(payload, rows) {
  const head = el('div', { class: 'grid-row head' }, COLUMNS.map(([label, help]) => el('span', {
    title: help || undefined,
  }, [el('span', { text: label }), help ? el('span', { class: 'th-mark', 'aria-hidden': 'true', text: 'ⓘ' }) : null])));
  const body = el('div', { class: 'grid-table members' }, [head, ...rows.map(memberRow)]);
  const perPage = payload && payload.per_page ? Number(payload.per_page) : rows.length;
  const total = payload && typeof payload.total === 'number' ? payload.total : rows.length;
  const from = (state.page - 1) * (perPage || rows.length) + 1;
  return el('div', { class: 'card' }, [
    toolbar(),
    rows.length === 0
      ? sayNothing(nothingSaid(), nothingToDo())
      : el('div', { class: 'table-scroll' }, [body]),
    rows.length === 0
      ? null
      : el('div', {
        class: 'grid-foot',
        text: `Showing ${from}–${from + rows.length - 1} of ${total} member${total === 1 ? '' : 's'}`,
      }),
    pager({
      page: state.page,
      hasMore: rows.length > 0 && rows.length >= perPage,
      count: rows.length,
      onPage: (to) => {
        state.page = Math.max(1, to);
        return refresh();
      },
    }),
  ]);
}

/**
 * Every search keystroke rebuilds the card, which throws away the box being
 * typed in — so the caret is put back where it was rather than the page
 * stealing focus mid-word.
 */
function keepTyping(typed) {
  if (typed === null) return;
  const box = document.querySelector('.searchfield .input.search');
  if (!box) return;
  box.value = typed;
  box.focus();
  box.setSelectionRange(typed.length, typed.length);
}

async function load() {
  const query = new URLSearchParams({
    filter: state.filter,
    page: String(state.page),
    sort: 'joined_desc',
  });
  if (state.query) query.set('q', state.query);
  const active = document.activeElement;
  const typed = active && active.classList.contains('search') ? active.value : null;
  const payload = await api(`/api/members?${query.toString()}`);
  const rows = listOf(payload, 'members');
  document.getElementById('dash').replaceChildren(statStrip(payload), membersCard(payload, rows));
  keepTyping(typed);
}

refresh = start({ tab: 'members', load });
