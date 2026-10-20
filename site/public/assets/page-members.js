import { api, listOf, send } from './api.js';
import { start, tabHref } from './app.js';
import {
  askReason,
  avatar,
  button,
  card,
  chipBar,
  el,
  icon,
  keepSaying,
  listFilter,
  notice,
  pager,
  roleChip,
  run,
  sayAgain,
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
  ['optouts', 'Opted out'],
  ['counted', 'Counted in'],
];

const OPTOUTS = 'optouts';
const COUNTED = 'counted';
const SOURCE_WORDS = {
  marathon_role: 'Marathons',
  marathon_posts: 'Marathons',
  announce: 'Announcements',
  golive_ignore_role: 'Go-live',
  chat_memory: 'Chat memory',
  birthday: 'Birthdays',
  pbs: 'Personal bests',
  streamer_list: 'Streamer list',
};
const SOURCE_CHIPS = [
  ['marathon_role', 'Not BaF'],
  ['marathon_posts', 'Out of marathon posts'],
  ['announce', 'Announcements'],
  ['golive_ignore_role', 'Ignored by role'],
  ['chat_memory', 'Chat memory'],
  ['birthday', 'Birthdays'],
  ['pbs', 'Personal bests'],
  ['streamer_list', 'Streamer list'],
];
const SOURCE_FILTERS = [
  ['all', 'Every source', null],
  ...SOURCE_CHIPS.map(([key, label]) => [key, label, (row) => row.chips.some((one) => one.source === key)]),
];
const OPTOUT_COLUMNS = ['Member', 'Opted out of'];
const NO_OPTOUTS = 'Nobody is opted out of anything.';
const NO_OPTOUT_HIT = 'Nobody opted out matches that.';
const CHANNELS_TITLE = 'Channels out of marathons';
const OPTOUTS_SAID = 'members.optouts';
const COUNTED_TITLE = 'Counted in';
const COUNTED_COLUMNS = ['Member', 'Why', 'By', ''];
const NO_COUNTED = 'Staff count nobody in.';

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

function homeOf(source) {
  if (source === 'marathon_role') return `${tabHref('settings')}#marathon_optout_role_ids`;
  const pages = {
    announce: 'golive',
    golive_ignore_role: 'golive',
    streamer_list: 'golive',
    chat_memory: 'chat',
    birthday: 'birthdays',
    pbs: 'pbs',
  };
  return tabHref(pages[source] || 'members');
}

function sourceLink(text, href) {
  return el('a', { class: 'badge', 'data-tone': 'warn', href, text });
}

function ruleMove(rule, say) {
  return button(rule.move_label, async () => {
    const path = `/api/marathons/baf-override/${encodeURIComponent(rule.user_id)}`;
    if (rule.move === 'set') {
      const found = await askReason({
        title: rule.reason_title,
        label: rule.reason_label,
        confirmLabel: rule.move_label,
        sendIt: (reason) => send(path, 'POST', { reason }),
      });
      if (!found) return;
      say.say(found.message || '', 'ok');
    } else {
      const done = await run(say, () => send(path, 'DELETE'), (found) => found?.message);
      if (!done.ok) return;
    }
    keepSaying(OPTOUTS_SAID, say);
    refresh();
  }, { tone: 'quiet' });
}

function optoutChips(row, say) {
  return el('span', { class: 'cell-roles' }, row.chips.flatMap((chip) => {
    const head = SOURCE_WORDS[chip.source] || chip.source;
    if (chip.source === 'marathon_posts') {
      return chip.marathons.map((one) => sourceLink(`${head} · ${chip.said} · ${one.name}`, `${tabHref('events')}#marathon-${one.id}`));
    }
    const link = sourceLink(chip.said ? `${head} · ${chip.said}` : head, homeOf(chip.source));
    return chip.rule ? [link, ruleMove(chip.rule, say)] : [link];
  }));
}

function optoutRow(row, say) {
  const who = String(row.name || row.username || row.user_id);
  return el('tr', { title: `Discord id ${row.user_id}` }, [
    el('td', { 'data-label': OPTOUT_COLUMNS[0] }, [
      el('span', { class: 'cell-member' }, [
        avatar(who, row.avatar),
        el('span', { class: 'cell-member-text' }, [
          el('span', { class: 'cell-member-name', text: who }),
          el('span', { class: 'cell-member-tag', text: row.here ? String(row.username || row.user_id) : 'left the server' }),
        ]),
      ]),
    ]),
    el('td', { class: 'wrap', 'data-label': OPTOUT_COLUMNS[1] }, [optoutChips(row, say)]),
  ]);
}

function channelsCard(channels) {
  if (!channels.length) return null;
  return card(CHANNELS_TITLE, [
    el('div', { class: 'cell-roles' }, channels.map((one) => sourceLink(one.name, tabHref('golive')))),
  ], { count: channels.length });
}

function memberCell(row) {
  const who = String(row.name || row.username || row.user_id);
  return el('span', { class: 'cell-member' }, [
    avatar(who, row.avatar),
    el('span', { class: 'cell-member-text' }, [
      el('span', { class: 'cell-member-name', text: who }),
      el('span', { class: 'cell-member-tag', text: row.here ? String(row.username || row.user_id) : 'left the server' }),
    ]),
  ]);
}

function countedRow(row, say) {
  const when = row.at ? shortWhen(row.at) : null;
  return el('tr', { title: `Discord id ${row.user_id}` }, [
    el('td', { 'data-label': COUNTED_COLUMNS[0] }, [memberCell(row)]),
    el('td', { class: 'wrap', 'data-label': COUNTED_COLUMNS[1] }, [
      el('span', { class: 'cell-roles' }, [
        sourceLink(row.said || SOURCE_WORDS.marathon_role, `${tabHref('settings')}#marathon_optout_role_ids`),
        el('span', { text: row.reason || '' }),
      ]),
    ]),
    el('td', { 'data-label': COUNTED_COLUMNS[2] }, [
      el('span', { class: 'cell-quiet', title: when ? when.title : '', text: [row.by_name || '', when ? when.text : ''].filter(Boolean).join(' · ') || '—' }),
    ]),
    el('td', { 'data-label': COUNTED_COLUMNS[3] }, [row.rule ? ruleMove(row.rule, say) : null]),
  ]);
}

function countedCard(payload) {
  const say = sayAgain(OPTOUTS_SAID, notice());
  const rows = listOf(payload, 'counted_in');
  const head = el('tr', {}, COUNTED_COLUMNS.map((label) => el('th', { text: label })));
  const body = rows.length
    ? el('div', { class: 'table-scroll' }, [el('table', { class: 'log-table' }, [el('thead', {}, [head]), el('tbody', {}, rows.map((row) => countedRow(row, say)))])])
    : sayNothing(NO_COUNTED);
  return card(COUNTED_TITLE, [say, body], { count: rows.length });
}

function optoutsCard(payload) {
  const say = sayAgain(OPTOUTS_SAID, notice());
  const people = listOf(payload, 'people');
  const items = people.map((row) => ({ row, node: optoutRow(row, say) }));
  const filter = listFilter({
    items,
    value: (one) => one.row,
    text: (row) => [row.name, row.username, row.user_id, ...row.chips.map((one) => one.said || SOURCE_WORDS[one.source])].join(' '),
    filters: SOURCE_FILTERS,
    label: 'Search the opted out',
    placeholder: 'Search the opted out…',
    empty: NO_OPTOUT_HIT,
  });
  const head = el('tr', {}, OPTOUT_COLUMNS.map((label) => el('th', { text: label })));
  const body = people.length
    ? el('div', { class: 'table-scroll' }, [el('table', { class: 'log-table' }, [el('thead', {}, [head]), el('tbody', {}, items.map((one) => one.node))])])
    : sayNothing(NO_OPTOUTS);
  return el('div', {}, [
    el('div', { class: 'card' }, [
      el('div', { class: 'card-head' }, [chipBar(FILTERS, state.filter, pickFilter)]),
      el('div', { class: 'card-head' }, filter.parts),
      say,
      body,
      filter.none,
    ]),
    countedCard(payload),
    channelsCard(listOf(payload, 'channels')),
  ]);
}

function countedOnly(payload) {
  return el('div', {}, [
    el('div', { class: 'card' }, [el('div', { class: 'card-head' }, [chipBar(FILTERS, state.filter, pickFilter)])]),
    countedCard(payload),
  ]);
}

function pickFilter(key) {
  state.filter = key;
  state.page = 1;
  refresh();
}

function toolbar() {
  const chips = chipBar(FILTERS, state.filter, pickFilter);
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
    chips,
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

async function loadOptouts() {
  const [stats, payload] = await Promise.all([
    api('/api/members?filter=all&page=1&per_page=1&sort=joined_desc'),
    api('/api/members/optouts'),
  ]);
  const shown = state.filter === COUNTED ? countedOnly(payload) : optoutsCard(payload);
  document.getElementById('dash').replaceChildren(statStrip(stats), shown);
}

async function load() {
  if (state.filter === OPTOUTS || state.filter === COUNTED) return loadOptouts();
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
