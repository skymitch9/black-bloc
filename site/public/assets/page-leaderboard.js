import { api, listOf, Outage, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { syncSubnav } from './layout.js';
import {
  amountRules,
  fill,
  gamesOf,
  pageOf,
  pageWith,
  pinned,
  runLine,
  sortedBounties,
  ticketHref,
  wallIn,
  zonedIso,
} from './leaderboard-layout.js';
import {
  HERE_ZONE,
  ago,
  ask,
  avatar,
  badge,
  bar,
  boldParts,
  button,
  closeDrawer,
  el,
  field,
  foldout,
  listFilter,
  memberPicker,
  modeChip,
  modeSwitch,
  nameNode,
  notice,
  openDrawer,
  run,
  sayNothing,
  section,
  segment,
  sentenceFor,
  settingsPanel,
  whenField,
} from './ui.js';

const POLL_MS = 15000;
const TAB = 'leaderboard';
const STATE_TONES = { pending: 'warn', approved: 'ok', rejected: 'danger', removed: null };
const BOUNTY_TONES = { live: 'ok', upcoming: 'info', idle: null, ended: null };
const EVENT_STATUSES = 'approved,live,done';

const WORDS = {
  board: 'Board',
  yourRuns: 'Your runs',
  pending: 'Pending',
  runs: 'Runs',
  settings: 'Settings',
  wording: 'Wording',
  approve: 'Approve',
  reject: 'Reject…',
  rejectGo: 'Reject',
  remove: 'Remove…',
  removeGo: 'Remove',
  edit: 'Edit…',
  save: 'Save',
  create: 'Create',
  keep: 'Keep',
  reason: 'Reason (they are told)',
  proof: 'Proof',
  openTicket: 'Open the ticket',
  recompute: 'Recompute',
  recomputeAsk: 'Score every approved run again under today’s tiers, points and bounties?',
  editRun: 'Edit run #{id}',
  forMember: 'For',
  scored: '{xp} XP · {points} speedpoints',
  decidedBy: 'by {name}',
  newBounty: 'New bounty',
  editBounty: 'Edit {name}',
  name: 'Name',
  games: 'Games',
  kind: 'Bonus',
  multiplier: 'Multiplier',
  extra: 'Extra speedpoints',
  amount: 'Amount',
  window: 'When',
  event: 'Event',
  dates: 'Dates',
  starts: 'Starts',
  ends: 'Ends',
  noEvents: 'No approved events',
  end: 'End…',
  endAsk: 'End {name}?',
  endGo: 'End it',
  bringBack: 'Bring back',
  live: 'live',
  upcoming: 'upcoming',
  idle: 'not live',
  ended: 'ended',
  noBounties: 'No bounties yet.',
  noPending: 'Nothing waiting.',
  noRuns: 'No runs yet.',
  noMatch: 'No run matches this.',
  search: 'Search runs…',
  searchLabel: 'Search runs',
  all: 'All',
  approvedChip: 'Approved',
  pendingChip: 'Waiting',
  rejectedChip: 'Rejected',
  removedChip: 'Removed',
  updated: 'updated {when}',
  failed: 'Could not update: {why}',
  outage: 'Black Bloc did not answer',
};

const view = {
  me: null,
  index: null,
  by: null,
  all: null,
  full: false,
  page: 1,
  mine: [],
  pending: [],
  runs: [],
  bounties: [],
  parts: new Map(),
  holders: {},
  says: {},
  filter: { query: '', filter: 'all' },
  readAt: 0,
  failed: null,
  status: null,
  timer: null,
};
let refresh = () => {};

function w(key, fields = {}) {
  const words = (view.index && view.index.words) || {};
  return fill(words[key] ?? '', fields);
}

function sig(value) {
  return JSON.stringify(value);
}

function mode() {
  return (view.index && view.index.mode) || 'shadow';
}

function staff() {
  return Boolean(view.index && view.index.staff);
}

function verifies() {
  return Boolean(view.index && view.index.may_verify);
}

function myId() {
  return view.me && view.me.user ? String(view.me.user.id) : null;
}

function guildId() {
  return view.me && view.me.guild ? view.me.guild.id : null;
}

function typing(node) {
  const active = document.activeElement;
  return Boolean(node && active && node.contains(active) && active.matches('input, select, textarea'));
}

function update(key, wanted, build, { force = false } = {}) {
  const holder = view.holders[key];
  if (!holder) return;
  if (!force && view.parts.get(key) === wanted) return;
  if (!force && typing(holder)) return;
  holder.replaceChildren(...[].concat(build()).filter(Boolean));
  view.parts.set(key, wanted);
}

function outLink(label, href) {
  return el('a', { class: 'lb-link', href, target: '_blank', rel: 'noopener noreferrer', text: label });
}

/* ---------- reading ---------- */

async function readIndex() {
  view.index = await api(`/api/points?by=${encodeURIComponent(view.by || '')}`);
  view.by = view.index.by;
  const me = view.index.me || {};
  const below = me.kind === 'climb' && me.place > view.index.board.length;
  view.all = view.full || below ? listOf(await api(`/api/points/board?by=${view.by}`), 'rows') : null;
}

async function readRuns() {
  const id = myId();
  const reads = [
    id ? api(`/api/points/runs?user_id=${encodeURIComponent(id)}`) : null,
    verifies() ? api('/api/points/runs?state=pending') : null,
    staff() ? api('/api/points/runs') : null,
    staff() ? api('/api/points/bounties') : null,
  ];
  const [mine, pending, runs, bounties] = await Promise.all(reads);
  view.mine = mine ? listOf(mine, 'runs') : [];
  view.pending = pending ? listOf(pending, 'runs') : [];
  view.runs = runs ? listOf(runs, 'runs') : [];
  view.bounties = bounties ? listOf(bounties, 'bounties') : [];
}

async function reread() {
  await readIndex();
  await readRuns();
  view.readAt = Date.now();
  view.failed = null;
  paint({ force: true });
}

async function act(say, work) {
  const done = await run(say, work, (found) => found.message);
  if (done.ok) {
    try {
      await reread();
    } catch (error) {
      view.failed = error instanceof Outage ? WORDS.outage : String(error.message || WORDS.outage);
      paintStatus();
    }
  }
  return done;
}

/* ---------- the board ---------- */

function orderSwitch() {
  const choices = [
    { value: 'points', label: w('points_points_label') || 'By speedpoints' },
    { value: 'xp', label: w('points_xp_label') || 'By XP' },
  ];
  const node = segment(choices, view.by, {
    onChange: async () => {
      const wanted = node.readValue();
      if (wanted === view.by) return;
      view.by = wanted;
      view.page = 1;
      await quietly(readIndex);
      paint();
    },
  });
  node.classList.add('lb-order');
  return node;
}

async function quietly(work) {
  try {
    await work();
    view.readAt = Date.now();
    view.failed = null;
  } catch (error) {
    view.failed = error instanceof Outage ? WORDS.outage : String(error.message || WORDS.outage);
  }
}

function boardHead() {
  return el('div', { class: 'lb-row lb-head', 'aria-hidden': 'true' }, [
    el('span', { class: 'lb-place' }),
    el('span', { class: 'lb-who', text: w('points_column_player') }),
    el('span', { class: 'lb-num lb-runs', text: w('points_column_runs') }),
    el('span', { class: 'lb-num lb-xp', text: w('points_column_xp') }),
    el('span', { class: 'lb-num lb-sp', text: w('points_column_points') }),
  ]);
}

function boardRow(row) {
  const mine = row.user_id === myId();
  const other = view.by === 'xp'
    ? `${w('points_column_points')} ${row.speedpoints}`
    : `${w('points_column_xp')} ${row.xp}`;
  const sub = `${w('points_column_runs')} ${row.runs} · ${other}`;
  return el('div', {
    class: 'lb-row',
    'data-mine': mine ? 'true' : undefined,
    'data-top': row.place <= 3 ? String(row.place) : undefined,
  }, [
    el('span', { class: 'lb-place mono', text: `#${row.place}` }),
    el('span', { class: 'lb-who' }, [
      avatar(row.name || '?', row.avatar_url),
      el('span', { class: 'lb-name-wrap' }, [
        nameNode(row.user_id, row.name),
        el('span', { class: 'lb-sub', text: sub }),
      ]),
    ]),
    el('span', { class: 'lb-num lb-runs mono', text: String(row.runs) }),
    el('span', { class: 'lb-num lb-xp mono', text: String(row.xp) }),
    el('span', { class: 'lb-num lb-sp mono', text: String(row.speedpoints) }),
  ]);
}

function boardPager(found) {
  if (found.pages <= 1) return null;
  const go = (page) => {
    view.page = page;
    update('board', null, boardBody, { force: true });
  };
  return el('div', { class: 'pager lb-pager' }, [
    button(w('points_previous_label') || 'Previous', () => go(found.page - 1), { tone: 'quiet', disabled: found.page <= 1 }),
    el('span', { class: 'pager-at', text: w('points_page_words', { page: found.page, pages: found.pages }) }),
    button(w('points_next_label') || 'Next', () => go(found.page + 1), { tone: 'quiet', disabled: found.page >= found.pages }),
  ]);
}

function boardBody() {
  const idx = view.index;
  const me = idx.me || {};
  const found = view.full ? pageOf(view.all || [], view.page) : { rows: idx.board, page: 1, pages: 1 };
  const own = pinned(found.rows, view.all || idx.board, myId());
  const tools = el('div', { class: 'lb-tools' }, [
    orderSwitch(),
    idx.members > idx.board.length || view.full
      ? button(view.full ? w('points_back_label') || 'Back' : w('points_full_board_label') || 'Full board', async () => {
        view.full = !view.full;
        if (view.full && !view.all) await quietly(readIndex);
        view.page = view.full ? pageWith(view.all || [], myId()) : 1;
        update('board', null, boardBody, { force: true });
      }, { tone: 'quiet' })
      : null,
    mode() !== 'off' ? button(w('points_submit_label') || 'Submit a run', () => submitDrawer(), { tone: 'warn', small: false }) : null,
  ]);
  const rows = found.rows.length
    ? el('div', { class: 'lb-board', 'data-by': view.by }, [
      boardHead(),
      ...found.rows.map(boardRow),
      own ? el('div', { class: 'lb-gap', 'aria-hidden': 'true', text: '⋯' }) : null,
      own ? boardRow(own) : null,
    ])
    : sayNothing(w('points_board_empty'));
  return [
    tools,
    me.line ? el('p', { class: 'lb-me', 'data-kind': me.kind }, boldParts(me.line)) : null,
    rows,
    view.full ? boardPager(found) : null,
    bountyLines(),
  ];
}

function bountyLines() {
  const live = listOf(view.index, 'bounties');
  return el('div', { class: 'lb-bounties' }, [
    el('h3', { class: 'lb-subhead', text: w('points_bounties_heading') }),
    live.length
      ? el('ul', { class: 'lb-bounty-lines' }, live.map((one) => el('li', { 'data-live': one.live ? 'true' : undefined }, boldParts(one.line))))
      : el('p', { class: 'lb-quiet', text: w('points_bounty_none') }),
  ]);
}

/* ---------- submitting ---------- */

function textBox(id, { value = '', max = 100, placeholder = '', type = 'text' } = {}) {
  return el('input', { class: 'input', type, id, maxlength: String(max), value: value || undefined, placeholder: placeholder || undefined, autocomplete: 'off' });
}

function runFields(runRow = null) {
  const game = textBox('lb-game', { value: runRow ? runRow.game : '' });
  const category = textBox('lb-category', { value: runRow ? runRow.category : '' });
  const time = textBox('lb-time', { value: runRow ? runRow.time : '', max: 40, placeholder: w('points_time_hint') });
  const proof = textBox('lb-proof', { value: runRow ? runRow.proof_url : '', max: 500, placeholder: w('points_proof_hint'), type: 'url' });
  const note = el('textarea', { class: 'input', id: 'lb-note', rows: '3', maxlength: '300', text: runRow ? runRow.note || '' : '' });
  return {
    nodes: [
      field(w('points_game_label') || 'Game', game),
      field(w('points_category_label') || 'Category', category),
      field(w('points_time_label') || 'Time', time),
      field(w('points_proof_label') || 'Proof link', proof),
      field(w('points_note_label') || 'Note', note),
    ],
    read: () => ({
      game: game.value.trim(),
      category: category.value.trim(),
      time: time.value.trim(),
      proof_url: proof.value.trim(),
      note: note.value.trim(),
    }),
    focus: () => game.focus(),
  };
}

function submitDrawer() {
  const fields = runFields();
  const picker = staff() ? memberPicker({ label: WORDS.forMember }) : null;
  const say = notice();
  const go = button(w('points_submit_label') || 'Submit a run', async () => {
    const body = fields.read();
    if (picker && picker.id && picker.id !== myId()) body.user_id = picker.id;
    go.disabled = true;
    const done = await run(say, () => send('/api/points/runs', 'POST', body), (found) => found.message);
    go.disabled = false;
    if (!done.ok) return;
    closeDrawer();
    view.says.board.say(done.found.message, 'ok');
    await quietly(async () => {
      await readIndex();
      await readRuns();
    });
    paint({ force: true });
    if (view.sections.mine) view.sections.mine.details.open = true;
  }, { tone: 'warn', small: false });
  openDrawer(w('points_submit_title') || 'Submit a run', [
    picker ? picker.node : null,
    ...fields.nodes,
    say,
    bar([go]),
  ]);
  fields.focus();
}

/* ---------- your runs ---------- */

function decidedWords(one) {
  if (one.state === 'approved') return fill(WORDS.scored, { xp: one.xp, points: one.speedpoints });
  if (one.reason) return one.reason;
  return null;
}

function mineBody() {
  if (!view.mine.length) return sayNothing(WORDS.noRuns);
  return el('div', { class: 'rowlist' }, view.mine.map((one) => el('div', { class: 'rowlist-row lb-run', 'data-state': one.state }, [
    el('span', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: runLine(one) }),
      el('span', { class: 'rowlist-note', text: [decidedWords(one), ago(one.submitted_at).text].filter(Boolean).join(' · ') }),
    ]),
    badge(one.state_words || one.state, STATE_TONES[one.state]),
  ])));
}

/* ---------- pending ---------- */

function reasonRow(holder, label, onGo) {
  const input = el('input', { class: 'input lb-reason', type: 'text', maxlength: '300', placeholder: WORDS.reason, 'aria-label': WORDS.reason });
  const was = [...holder.childNodes];
  holder.replaceChildren(
    input,
    button(label, () => onGo(input.value.trim()), { tone: 'danger' }),
    button(WORDS.keep, () => holder.replaceChildren(...was), { tone: 'quiet' }),
  );
  input.focus();
}

function runLinks(one) {
  const ticket = ticketHref(guildId(), one.ticket_place_id);
  return el('span', { class: 'lb-links' }, [
    one.proof_url ? outLink(WORDS.proof, one.proof_url) : null,
    ticket ? outLink(WORDS.openTicket, ticket) : null,
  ]);
}

function pendingRow(one) {
  const holder = el('span', { class: 'bar lb-acts' });
  const say = view.says.pending;
  const own = !staff() && one.user_id === myId();
  const base = `/api/points/runs/${encodeURIComponent(one.id)}`;
  if (!own && mode() !== 'off') {
    holder.append(
      button(WORDS.approve, () => act(say, () => send(`${base}/approve`, 'POST', {})), { tone: 'warn' }),
      button(WORDS.reject, () => reasonRow(holder, WORDS.rejectGo, (reason) => act(say, () => send(`${base}/reject`, 'POST', { reason }))), { tone: 'quiet' }),
    );
  }
  return el('div', { class: 'rowlist-row lb-run', 'data-id': String(one.id) }, [
    avatar(one.name || '?', null),
    el('span', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name' }, [nameNode(one.user_id, one.name)]),
      el('span', { class: 'lb-runline', text: runLine(one) }),
      el('span', { class: 'rowlist-note', text: ago(one.submitted_at).text }),
      one.note ? el('span', { class: 'lb-note', text: one.note }) : null,
      runLinks(one),
    ]),
    holder.childNodes.length ? holder : null,
  ]);
}

function pendingBody() {
  if (!view.pending.length) return sayNothing(WORDS.noPending);
  return el('div', { class: 'rowlist' }, view.pending.map(pendingRow));
}

/* ---------- runs (staff) ---------- */

function editDrawer(one) {
  const fields = runFields(one);
  const say = notice();
  const go = button(WORDS.save, async () => {
    const typed = fields.read();
    const was = { game: one.game, category: one.category || '', time: one.time, proof_url: one.proof_url, note: one.note || '' };
    const body = Object.fromEntries(Object.entries(typed).filter(([key, value]) => value !== was[key]));
    if (!Object.keys(body).length) body.game = typed.game;
    const done = await act(say, () => send(`/api/points/runs/${encodeURIComponent(one.id)}`, 'PATCH', body));
    if (!done.ok) return;
    closeDrawer();
    view.says.runs.say(done.found.message, 'ok');
  }, { tone: 'warn', small: false });
  openDrawer(fill(WORDS.editRun, { id: one.id }), [
    el('p', { class: 'lb-drawer-who' }, [avatar(one.name || '?', null), nameNode(one.user_id, one.name), badge(one.state_words || one.state, STATE_TONES[one.state])]),
    ...fields.nodes,
    say,
    bar([go]),
  ]);
  fields.focus();
}

function runRow(one) {
  const holder = el('span', { class: 'bar lb-acts' });
  const say = view.says.runs;
  if (mode() !== 'off') {
    holder.append(button(WORDS.edit, () => editDrawer(one), { tone: 'quiet' }));
    if (one.state === 'approved') {
      holder.append(button(WORDS.remove, () => reasonRow(holder, WORDS.removeGo, (reason) => act(say, () => send(`/api/points/runs/${encodeURIComponent(one.id)}/remove`, 'POST', { reason }))), { tone: 'quiet' }));
    }
  }
  const decided = [decidedWords(one), one.decided_by_name ? fill(WORDS.decidedBy, { name: one.decided_by_name }) : null, ago(one.decided_at || one.submitted_at).text];
  return el('div', { class: 'rowlist-row lb-run', 'data-id': String(one.id), 'data-state': one.state }, [
    el('span', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name' }, [nameNode(one.user_id, one.name)]),
      el('span', { class: 'lb-runline', text: runLine(one) }),
      el('span', { class: 'rowlist-note', text: decided.filter(Boolean).join(' · ') }),
      runLinks(one),
    ]),
    badge(one.state_words || one.state, STATE_TONES[one.state]),
    holder.childNodes.length ? holder : null,
  ]);
}

function runsBody() {
  const rows = view.runs;
  const items = rows.map((one) => ({ one, node: runRow(one) }));
  const filter = listFilter({
    items,
    value: (item) => item.one,
    text: (one) => [one.name, one.game, one.category, one.time, one.reason, one.note, one.state_words, `#${one.id}`].join(' '),
    filters: [
      ['all', WORDS.all, null],
      ['approved', WORDS.approvedChip, (one) => one.state === 'approved'],
      ['pending', WORDS.pendingChip, (one) => one.state === 'pending'],
      ['rejected', WORDS.rejectedChip, (one) => one.state === 'rejected'],
      ['removed', WORDS.removedChip, (one) => one.state === 'removed'],
    ],
    filter: view.filter.filter,
    query: view.filter.query,
    label: WORDS.searchLabel,
    placeholder: WORDS.search,
    empty: WORDS.noMatch,
    onChange: ({ query, filter: key }) => {
      view.filter = { query, filter: key };
    },
  });
  const recompute = mode() !== 'off'
    ? button(WORDS.recompute, async () => {
      const yes = await ask({ title: WORDS.recomputeAsk, body: [], confirmLabel: WORDS.recompute, tone: 'warn' });
      if (yes) await act(view.says.runs, () => send('/api/points/recompute', 'POST', {}));
    }, { tone: 'quiet' })
    : null;
  if (recompute) recompute.classList.add('lb-push');
  if (!rows.length) return [bar([recompute].filter(Boolean)), sayNothing(WORDS.noRuns)];
  filter.apply();
  return [
    el('div', { class: 'table-tools' }, [...filter.parts, recompute].filter(Boolean)),
    el('div', { class: 'rowlist' }, items.map((item) => item.node)),
    filter.none,
  ];
}

/* ---------- bounties (staff) ---------- */

async function eventOptions(select, chosen) {
  let rows = [];
  try {
    rows = await api(`/api/events?status=${EVENT_STATUSES}`);
  } catch (error) {
    select.replaceChildren(el('option', { value: chosen || '', text: sentenceFor(error).text }));
    return;
  }
  const list = (Array.isArray(rows) ? rows : []).slice().sort((a, b) => String(a.starts_at).localeCompare(String(b.starts_at)));
  select.replaceChildren(...list.map((one) => el('option', {
    value: String(one.id),
    text: `${one.title} · ${new Date(one.starts_at).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}`,
    selected: String(one.id) === String(chosen) || undefined,
  })));
  if (chosen && !list.some((one) => String(one.id) === String(chosen))) {
    select.append(el('option', { value: String(chosen), text: `#${chosen}`, selected: true }));
  }
  if (!select.options.length) select.append(el('option', { value: '', text: WORDS.noEvents }));
}

function bountyDrawer(b = null) {
  const name = textBox('lb-b-name', { value: b ? b.name : '' });
  const games = el('textarea', { class: 'input', id: 'lb-b-games', rows: '4', text: b ? b.games.join('\n') : '' });
  const kind = el('select', { class: 'input', id: 'lb-b-kind' }, [
    el('option', { value: 'multiplier', text: WORDS.multiplier, selected: (b ? b.kind : 'multiplier') === 'multiplier' || undefined }),
    el('option', { value: 'extra', text: WORDS.extra, selected: b && b.kind === 'extra' ? true : undefined }),
  ]);
  const amount = el('input', { class: 'input', type: 'number', id: 'lb-b-amount', inputmode: 'decimal' });
  const bounds = () => {
    const rules = amountRules(kind.value);
    amount.min = rules.min;
    amount.max = rules.max;
    amount.step = rules.step;
    return rules;
  };
  amount.value = b ? String(b.amount) : bounds().value;
  bounds();
  kind.addEventListener('change', () => {
    const rules = bounds();
    if (!b) amount.value = rules.value;
  });
  const how = segment([{ value: 'event', label: WORDS.event }, { value: 'dates', label: WORDS.dates }], b && b.event_id ? 'event' : 'dates', { onChange: () => shape() });
  const eventSelect = el('select', { class: 'input', id: 'lb-b-event' });
  eventOptions(eventSelect, b ? b.event_id : null);
  const starts = whenField({ label: WORDS.starts, value: b && !b.event_id ? wallIn(b.starts_at, HERE_ZONE) : '' });
  const ends = whenField({ label: WORDS.ends, value: b && !b.event_id ? wallIn(b.ends_at, HERE_ZONE) : '', zoned: false, zoneWord: '' });
  const eventPart = el('div', { class: 'lb-window' }, [field(WORDS.event, eventSelect)]);
  const datesPart = el('div', { class: 'formrow lb-window' }, [starts.node, ends.node]);
  const shape = () => {
    const byEvent = how.readValue() === 'event';
    eventPart.hidden = !byEvent;
    datesPart.hidden = byEvent;
  };
  shape();
  const say = notice();
  const go = button(b ? WORDS.save : WORDS.create, async () => {
    const zone = starts.tz() || HERE_ZONE;
    const body = { name: name.value.trim(), games: gamesOf(games.value), kind: kind.value, amount: amount.value === '' ? '' : Number(amount.value) };
    if (how.readValue() === 'event') Object.assign(body, { event_id: eventSelect.value || '', starts_at: '', ends_at: '' });
    else Object.assign(body, { event_id: null, starts_at: zonedIso(starts.value(), zone) || '', ends_at: zonedIso(ends.value(), zone) || '' });
    const path = b ? `/api/points/bounties/${encodeURIComponent(b.id)}` : '/api/points/bounties';
    const done = await act(say, () => send(path, b ? 'PATCH' : 'POST', body));
    if (!done.ok) return;
    closeDrawer();
    view.says.bounties.say(done.found.message, 'ok');
  }, { tone: 'warn', small: false });
  openDrawer(b ? fill(WORDS.editBounty, { name: b.name }) : WORDS.newBounty, [
    field(WORDS.name, name),
    field(WORDS.games, games),
    el('div', { class: 'formrow' }, [field(WORDS.kind, kind), field(WORDS.amount, amount)]),
    field(WORDS.window, how),
    eventPart,
    datesPart,
    say,
    bar([go]),
  ]);
  name.focus();
}

function bountyRow({ bounty: b, status }) {
  const say = view.says.bounties;
  const base = `/api/points/bounties/${encodeURIComponent(b.id)}`;
  const moves = [];
  if (mode() !== 'off') {
    moves.push(button(WORDS.edit, () => bountyDrawer(b), { tone: 'quiet' }));
    if (b.active) {
      moves.push(button(WORDS.end, async () => {
        const yes = await ask({ title: fill(WORDS.endAsk, { name: b.name }), body: [], confirmLabel: WORDS.endGo, tone: 'danger' });
        if (yes) await act(say, () => send(`${base}/end`, 'POST', {}));
      }, { tone: 'quiet' }));
    } else {
      moves.push(button(WORDS.bringBack, () => act(say, () => send(base, 'PATCH', { active: true })), { tone: 'quiet' }));
    }
  }
  return el('div', { class: 'rowlist-row lb-bounty', 'data-status': status }, [
    el('span', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: b.name }),
      el('span', { class: 'lb-runline' }, boldParts(b.line)),
    ]),
    badge(WORDS[status], BOUNTY_TONES[status]),
    moves.length ? el('span', { class: 'bar lb-acts' }, moves) : null,
  ]);
}

function bountiesBody() {
  const sorted = sortedBounties(view.bounties);
  const current = sorted.filter((one) => one.status !== 'ended');
  const ended = sorted.filter((one) => one.status === 'ended');
  const make = mode() !== 'off' ? button(WORDS.newBounty, () => bountyDrawer(null), { tone: 'warn' }) : null;
  if (make) make.classList.add('lb-push');
  return [
    make ? bar([make]) : null,
    current.length ? el('div', { class: 'rowlist' }, current.map(bountyRow)) : sayNothing(WORDS.noBounties),
    ended.length ? foldout(WORDS.ended, [el('div', { class: 'rowlist' }, ended.map(bountyRow))], { count: ended.length }) : null,
  ];
}

/* ---------- settings ---------- */

async function settingsNode() {
  const one = section(WORDS.settings, null, { id: 'settings' });
  try {
    const specs = settingsNamespace(await settings(true), 'core').filter((spec) => spec.key.startsWith('points_'));
    const modeSpec = specs.find((spec) => spec.key === 'points_mode');
    const operational = specs.filter((spec) => spec.key !== 'points_mode' && spec.type !== 'text');
    const wording = specs.filter((spec) => spec.type === 'text');
    one.count(specs.length);
    one.body.append(...[
      modeSpec ? el('div', { class: 'bar' }, [modeSwitch(modeSpec, { label: 'Leaderboard', onSaved: () => refresh() }).node]) : null,
      await settingsPanel(operational, { where: WORDS.settings, onSaved: () => refresh() }),
      foldout(WORDS.wording, [await settingsPanel(wording, { where: WORDS.wording, onSaved: () => refresh() })], { count: wording.length }),
    ].filter(Boolean));
  } catch (error) {
    const found = sentenceFor(error);
    one.body.append(notice(found.text, found.tone));
  }
  return one.node;
}

/* ---------- painting ---------- */

function statusText() {
  if (view.failed) return fill(WORDS.failed, { why: view.failed });
  if (!view.readAt) return '';
  const seconds = Math.max(0, Math.round((Date.now() - view.readAt) / 1000));
  return fill(WORDS.updated, { when: seconds < 5 ? 'just now' : `${seconds} s ago` });
}

function paintStatus() {
  if (!view.status) return;
  view.status.textContent = statusText();
  if (view.failed) view.status.setAttribute('data-tone', 'warn');
  else view.status.removeAttribute('data-tone');
}

function paint({ force = false } = {}) {
  update('board', sig([view.index, view.all, view.full, view.page, view.by]), boardBody, { force });
  update('mine', sig(view.mine), mineBody, { force });
  update('pending', sig([view.pending, mode()]), pendingBody, { force });
  update('runs', sig([view.runs, mode()]), runsBody, { force });
  update('bounties', sig([view.bounties, mode()]), bountiesBody, { force });
  for (const [key, one] of Object.entries(view.sections)) {
    if (key === 'mine') {
      one.node.hidden = !view.mine.length;
      one.count(view.mine.length || null);
    }
    if (key === 'pending') one.count(view.pending.length);
    if (key === 'runs') one.count(view.runs.length);
    if (key === 'bounties') one.count(view.bounties.filter((b) => b.active).length);
  }
  syncSubnav();
  paintStatus();
}

function block(key, title, { open = false, full = false } = {}) {
  const one = section(title, null, { id: key, open });
  if (full) one.node.setAttribute('data-span', 'full');
  const say = notice();
  view.says[key] = say;
  view.holders[key] = el('div', { class: 'lb-part' });
  one.body.append(say, view.holders[key]);
  view.sections[key] = one;
  return one;
}

function aside() {
  const holder = document.getElementById('page-aside');
  if (!holder) return;
  holder.replaceChildren(...(verifies() ? [modeChip(mode())] : []));
}

async function poll() {
  if (document.hidden || !view.index) return;
  try {
    await readIndex();
    if (verifies()) view.pending = listOf(await api('/api/points/runs?state=pending'), 'runs');
    view.readAt = Date.now();
    view.failed = null;
    paint();
    aside();
  } catch (error) {
    view.failed = error instanceof Outage ? WORDS.outage : String(error.message || WORDS.outage);
    paintStatus();
  }
}

async function load(me) {
  view.me = me;
  view.parts = new Map();
  view.holders = {};
  view.says = {};
  view.sections = {};
  await readIndex();
  await readRuns();
  view.readAt = Date.now();
  view.failed = null;
  const board = block('board', WORDS.board, { open: true, full: true });
  view.status = el('p', { class: 'lb-status', role: 'status' });
  board.body.append(view.status);
  const blocks = [board.node];
  blocks.push(block('mine', WORDS.yourRuns, { open: view.mine.some((one) => one.state === 'pending') }).node);
  if (verifies()) blocks.push(block('pending', WORDS.pending, { open: true, full: true }).node);
  if (staff()) {
    blocks.push(block('runs', WORDS.runs, { full: true }).node);
    blocks.push(block('bounties', w('points_bounties_heading') || 'Bounties', { open: true, full: true }).node);
    blocks.push(await settingsNode());
  }
  paint();
  document.getElementById('dash').replaceChildren(...blocks);
  aside();
  if (view.timer === null) {
    view.timer = setInterval(poll, POLL_MS);
    setInterval(paintStatus, 1000);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) poll();
    });
  }
}

refresh = start({ tab: TAB, load });
