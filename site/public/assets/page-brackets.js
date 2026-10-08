import { api, listOf, names, Outage, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  BEFORE_START,
  ELIMINATION,
  LIVE,
  OPEN,
  eliminationLayout,
  fill,
  memberMoves,
  moved,
  myEntrant,
  organiserMoves,
  placeWords,
  resultsGrid,
  roundsLayout,
  scoreChoices,
  setMoves,
  sortedStandings,
} from './bracket-layout.js';
import { logsTable } from './logs.js';
import { clockTime, dayLabel, viewerZone } from './timezone.js';
import {
  ask,
  badge,
  bar,
  boldParts,
  button,
  closeDrawer,
  el,
  field,
  foldout,
  idsIn,
  listFilter,
  linkAction,
  memberPicker,
  modeSwitch,
  notice,
  openDrawer,
  run,
  sayNothing,
  section,
  sentenceFor,
  settingsPanel,
  table,
} from './ui.js';

const POLL_MS = 15000;
const TAB = 'brackets';
const LENGTHS = [1, 3, 5, 7, 9, 11, 13, 15];
const FORMATS = ['double', 'single', 'round_robin', 'swiss'];
const STATE_TONES = { signups: 'info', check_in: 'info', seeding: 'warn', running: 'ok', cancelled: 'danger' };
const SET_TONES = { ready: 'info', called: 'warn', reported: 'info', disputed: 'danger', complete: 'ok' };
const OUT_WORDS = { removed: 'removed', left: 'left', no_show: 'no-show', dropped: 'dropped' };

const ORGANISER = {
  open_signups: 'Open sign-ups',
  close_signups: 'Close sign-ups',
  open_check_in: 'Open check-in',
  close_check_in: 'Close check-in',
  start: 'Start',
  unstart: 'Back to seeding',
  complete: 'Complete',
  reopen: 'Reopen',
  cancel: 'Cancel',
  restore: 'Restore',
  call_ready: 'Call ready sets',
  move: 'Move to #knuck-up',
  edit: 'Edit…',
};
const PATHS = {
  open_signups: 'signups/open',
  close_signups: 'signups/close',
  open_check_in: 'checkin/open',
  close_check_in: 'checkin/close',
  start: 'start',
  unstart: 'unstart',
  complete: 'complete',
  reopen: 'reopen',
  cancel: 'cancel',
  restore: 'restore',
  move: 'move',
};
const ASKS = {
  unstart: ['Back to seeding? Every set and result is cleared.', 'Back to seeding'],
  cancel: ['Cancel {name}?', 'Cancel it'],
  move: ['Move {name} into #knuck-up? Its cards are posted there and its players are pinged.', 'Move it'],
};
const TONES = { cancel: 'danger', unstart: 'warn', move: 'warn', start: null };
const WORDS = {
  newTournament: 'New tournament',
  editTitle: 'Edit {name}',
  create: 'Create',
  save: 'Save',
  name: 'Name',
  game: 'Game',
  format: 'Format',
  starts: 'Starts',
  third: 'Third-place set',
  reset: 'Grand-final reset',
  rounds: 'Swiss rounds',
  roundsAuto: 'auto',
  bestOf: 'Best of',
  late: 'Late best of',
  lateFrom: 'Late from top',
  finals: 'Finals best of',
  cap: 'Entrant cap',
  checkIn: 'Check-in minutes',
  rules: 'Rules',
  noName: 'A tournament needs a name.',
  search: 'Search tournaments…',
  searchLabel: 'Search tournaments',
  none: 'No tournaments yet.',
  noMatch: 'No tournament matches this.',
  complete: 'Complete',
  cancelled: 'Cancelled',
  all: 'All',
  live: 'Live',
  back: 'All tournaments',
  missing: 'There is no tournament {id} here.',
  bracket: 'Bracket',
  entrants: 'Entrants',
  standings: 'Standings',
  logs: 'Logs',
  settings: 'Settings',
  wording: 'Wording',
  noLogs: 'Nothing logged for this yet.',
  randomise: 'Randomise',
  saveSeeding: 'Save seeding',
  discard: 'Discard',
  remove: 'Remove…',
  dq: 'DQ…',
  drop: 'Drop…',
  restore: 'Restore',
  checkInTo: 'Check in',
  checkOutTo: 'Check out',
  reason: 'Reason (they are told)',
  keep: 'Keep',
  add: 'Add',
  addGuest: 'Add guest',
  guestName: 'Guest name',
  addEntrant: 'Add entrant',
  guest: 'guest',
  checkedIn: 'checked in',
  notCheckedIn: 'not checked in',
  dqWord: 'DQ',
  call: 'Call',
  accept: 'Let it stand',
  decide: 'Decide',
  forfeit: '{name} by forfeit',
  resetSet: 'Reset',
  organiser: 'Organiser',
  sendDispute: 'Send',
  updated: 'updated {when}',
  failed: 'Could not update: {why}',
  outage: 'Black Bloc did not answer',
  place: 'Place',
  player: 'Player',
  sets: 'Sets',
  games: 'Games',
  opponents: 'Opp. win %',
  byes: 'Byes',
  bye: 'bye',
  seedLabel: 'Seed',
  bracketEmpty: 'The bracket is drawn when the tournament starts.',
  move: 'Drag to reorder',
};

const view = {
  me: null,
  index: null,
  t: null,
  zone: 'UTC',
  shape: null,
  parts: new Map(),
  holders: {},
  say: null,
  seedOrder: null,
  readAt: 0,
  failed: null,
  timer: null,
  clock: null,
  filter: { query: '', filter: 'all' },
  pending: null,
};
let refresh = () => {};

function w(key, fields = {}) {
  const words = (view.index && view.index.words) || {};
  return fill(words[key] ?? '', fields);
}

function said(text, fields = {}) {
  return fill(text, fields);
}

function sig(value) {
  return JSON.stringify(value);
}

function stamp(iso) {
  if (!iso) return '';
  return `${dayLabel(iso, view.zone)} · ${clockTime(iso, view.zone)}`;
}

function formatWords(format) {
  return w(`brackets_format_${format}_words`) || format;
}

function stateBadge(state) {
  return badge(w(`brackets_state_${state}`) || state, STATE_TONES[state] || null);
}

function wantedId() {
  const found = /^#(\d+)$/.exec(location.hash || '');
  return found ? found[1] : null;
}

function base(id) {
  return `/api/brackets/${encodeURIComponent(id)}`;
}

function staff() {
  return Boolean(view.me && view.me.staff && view.index && view.index.may_run);
}

function mode() {
  return (view.index && view.index.mode) || 'shadow';
}

function typing(node) {
  const active = document.activeElement;
  return Boolean(node && active && node.contains(active) && active.matches('input, select, textarea'));
}

function update(key, wanted, holder, build, { force = false } = {}) {
  if (!holder) return;
  if (!force && view.parts.get(key) === wanted) return;
  if (!force && typing(holder)) return;
  holder.replaceChildren(...[].concat(build()).filter(Boolean));
  view.parts.set(key, wanted);
}

/* ---------- the list ---------- */

function listRow(t) {
  const cap = t.entrant_cap ? `${t.entrant_count ?? 0}/${t.entrant_cap}` : String(t.entrant_count ?? 0);
  const bits = [
    t.game,
    formatWords(t.format),
    `${cap} ${cap === '1' ? 'entrant' : 'entrants'}`,
    t.starts_at && BEFORE_START.includes(t.state) ? stamp(t.starts_at) : null,
    t.to_name,
  ].filter(Boolean);
  return el('a', { class: 'rowlist-row bk-row', href: `#${t.id}`, 'data-state': t.state }, [
    el('span', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: t.name }),
      el('span', { class: 'rowlist-note', text: bits.join(' · ') }),
    ]),
    stateBadge(t.state),
  ]);
}

function ordered(rows) {
  const live = rows.filter((t) => LIVE.includes(t.state) || t.state === 'draft');
  const rank = { running: 0, check_in: 1, signups: 2, seeding: 3, draft: 4 };
  live.sort((a, b) => rank[a.state] - rank[b.state] || String(a.starts_at || '9').localeCompare(String(b.starts_at || '9')) || a.id - b.id);
  const done = rows.filter((t) => t.state === 'complete').sort((a, b) => String(b.starts_at || '').localeCompare(String(a.starts_at || '')) || b.id - a.id);
  const gone = rows.filter((t) => t.state === 'cancelled').sort((a, b) => b.id - a.id);
  return { live, done, gone };
}

function listBody() {
  const idx = view.index;
  const runs = Boolean(idx.may_run);
  const rows = listOf(idx, 'tournaments').filter((t) => runs || !['draft', 'cancelled'].includes(t.state));
  const { live, done, gone } = ordered(rows);
  const items = [...live, ...done, ...gone].map((t) => ({ t, node: listRow(t) }));
  const node = (t) => items.find((one) => one.t === t).node;
  const folds = [];
  const filters = [
    ['all', WORDS.all, null],
    ['live', WORDS.live, (t) => LIVE.includes(t.state) || t.state === 'draft'],
    ['complete', WORDS.complete, (t) => t.state === 'complete'],
  ];
  if (runs) filters.push(['cancelled', WORDS.cancelled, (t) => t.state === 'cancelled']);
  const filter = listFilter({
    items,
    value: (item) => item.t,
    text: (t) => [t.name, t.game, formatWords(t.format), w(`brackets_state_${t.state}`), t.to_name].join(' '),
    filters,
    filter: view.filter.filter,
    query: view.filter.query,
    label: WORDS.searchLabel,
    placeholder: WORDS.search,
    empty: WORDS.noMatch,
    onChange: ({ query, filter: key }) => {
      view.filter = { query, filter: key };
      for (const fold of folds) if (query || key !== 'all') fold.open = true;
    },
  });
  const newButton = runs && mode() !== 'off'
    ? button(WORDS.newTournament, () => optionsDrawer(null), { tone: 'warn' })
    : null;
  if (newButton) newButton.style.marginLeft = 'auto';
  if (!rows.length) return [bar([newButton].filter(Boolean)), sayNothing(WORDS.none)];
  const doneFold = done.length ? foldout(WORDS.complete, [el('div', { class: 'rowlist' }, done.map(node))], { count: done.length }) : null;
  const goneFold = gone.length ? foldout(WORDS.cancelled, [el('div', { class: 'rowlist' }, gone.map(node))], { count: gone.length }) : null;
  folds.push(...[doneFold, goneFold].filter(Boolean));
  filter.apply();
  return [
    el('div', { class: 'table-tools' }, [...filter.parts, newButton].filter(Boolean)),
    live.length ? el('div', { class: 'rowlist' }, live.map(node)) : null,
    filter.none,
    doneFold,
    goneFold,
  ];
}

/* ---------- moves ---------- */

function take(found) {
  if (found && found.tournament) view.t = found.tournament;
}

async function act(path, body = {}, method = 'POST', say = view.say) {
  const done = await run(say, () => send(path, method, body), (found) => found.message);
  if (done.ok) {
    take(done.found);
    view.readAt = Date.now();
    view.failed = null;
    paint();
  }
  return done;
}

async function memberMove(move) {
  const t = view.t;
  const me = myEntrant(t);
  if (move === 'join') return act(`${base(t.id)}/join`);
  if (move === 'check_in') return act(`${base(t.id)}/entrants/${me.id}/checkin`, { checked_in: true });
  if (move === 'leave') return act(`${base(t.id)}/entrants/${me.id}/drop`);
  if (move === 'drop_out') {
    const yes = await ask({ title: w('brackets_drop_confirm', { name: t.name }).replace(/\*\*/g, ''), body: [], confirmLabel: w('brackets_drop_label'), tone: 'danger' });
    if (yes) await act(`${base(t.id)}/entrants/${me.id}/drop`);
  }
  return null;
}

async function organiserMove(move) {
  const t = view.t;
  if (move === 'edit') return optionsDrawer(t);
  if (move === 'call_ready') {
    const ready = t.sets.filter((one) => one.state === 'ready');
    for (const one of ready) {
      const done = await act(`${base(t.id)}/sets/${encodeURIComponent(one.key)}/call`);
      if (!done.ok) break;
    }
    return null;
  }
  if (ASKS[move]) {
    const [title, confirmLabel] = ASKS[move];
    const yes = await ask({ title: said(title, { name: t.name }), body: [], confirmLabel, tone: TONES[move] || 'danger' });
    if (!yes) return null;
  }
  return act(`${base(t.id)}/${PATHS[move]}`, move === 'complete' ? {} : {});
}

const MEMBER_LABELS = {
  join: 'brackets_sign_up_label',
  check_in: 'brackets_check_in_label',
  leave: 'brackets_leave_label',
  drop_out: 'brackets_drop_label',
};

function moveBar(t) {
  const members = memberMoves(t, mode()).map((move) => button(w(MEMBER_LABELS[move]), () => memberMove(move), { tone: move === 'join' || move === 'check_in' ? 'warn' : 'quiet', small: false }));
  const organisers = organiserMoves(t, { mode: mode(), staff: staff() }).map((move) => button(ORGANISER[move], () => organiserMove(move), { tone: move === 'cancel' ? 'danger' : ['start', 'complete', 'open_signups', 'open_check_in', 'move', 'restore', 'reopen'].includes(move) ? 'warn' : 'quiet' }));
  if (!members.length && !organisers.length) return null;
  return el('div', { class: 'bk-moves' }, [
    members.length ? bar(members) : null,
    organisers.length ? bar(organisers) : null,
  ]);
}

/* ---------- the head ---------- */

function optionWords(t) {
  const o = t.options || {};
  const found = [`Bo${o.best_of}`];
  if (ELIMINATION.includes(t.format)) {
    if (o.best_of_from_round) found.push(`top ${o.best_of_from_round} Bo${o.best_of_late}`);
    found.push(`finals Bo${o.best_of_finals}`);
  }
  if (t.format === 'double' && o.grand_final_reset) found.push(WORDS.reset.toLowerCase());
  if (t.format === 'single' && o.third_place) found.push(WORDS.third.toLowerCase());
  if (t.format === 'swiss') found.push(`${o.swiss_rounds || WORDS.roundsAuto} ${WORDS.rounds.split(' ')[1].toLowerCase()}`);
  return found;
}

function waitingLine(t) {
  if (t.state !== 'running' || t.mine === null || t.mine === undefined) return null;
  const mine = (t.waiting_on || []).find((one) => one.entrant === t.mine);
  if (!mine) return null;
  const opponent = (t.entrants.find((one) => one.id === mine.opponent) || {}).name || '';
  const text = w(`brackets_waiting_${mine.what}`, { set: mine.set || '', opponent });
  if (!text) return null;
  const set = mine.set ? t.sets.find((one) => one.key === mine.set) : null;
  const tone = ['play', 'called', 'confirm'].includes(mine.what) ? 'warn' : null;
  return el('div', { class: 'bk-you', 'data-tone': tone || undefined }, [
    set && setMoves(t, set, { mode: mode() }).length
      ? el('button', { class: 'bk-you-go', type: 'button', text, on: { click: () => setDrawer(set.key) } })
      : el('span', { text }),
  ]);
}

function headBody(t) {
  const cap = t.options && t.options.entrant_cap ? `${t.entrant_count}/${t.options.entrant_cap}` : String(t.entrant_count);
  const meta = [
    t.game,
    formatWords(t.format),
    ...optionWords(t),
    `${cap} ${t.entrant_count === 1 && !t.options.entrant_cap ? 'entrant' : 'entrants'}`,
    t.to_name,
  ].filter(Boolean);
  const times = [];
  if (t.starts_at && BEFORE_START.includes(t.state)) times.push(stamp(t.starts_at));
  if (t.state === 'check_in' && t.check_in_closes_at) times.push(`check-in closes ${clockTime(t.check_in_closes_at, view.zone)}`);
  if (t.state === 'running' && t.started_at) times.push(`started ${stamp(t.started_at)}`);
  if (t.state === 'complete' && t.completed_at) times.push(stamp(t.completed_at));
  return [
    el('div', { class: 'bk-title' }, [el('h2', { class: 'bk-name', text: t.name }), stateBadge(t.state), t.shadow && view.index.may_run ? badge('rehearsal', 'warn') : null]),
    el('p', { class: 'bk-meta', text: meta.join(' · ') }),
    times.length ? el('p', { class: 'bk-meta mono', text: times.join(' · ') }) : null,
    waitingLine(t),
    moveBar(t),
    t.rules_text ? foldout(WORDS.rules, [el('p', { class: 'bk-rules', text: t.rules_text })]) : null,
  ];
}

/* ---------- entrants ---------- */

function outWords(one) {
  if (one.dq) return WORDS.dqWord;
  if (one.dropped) return OUT_WORDS[one.dropped_why] || 'out';
  return null;
}

function reasonRow(holder, label, onGo) {
  const input = el('input', { class: 'input bk-reason', type: 'text', maxlength: '300', placeholder: WORDS.reason, 'aria-label': WORDS.reason });
  const was = [...holder.childNodes];
  holder.replaceChildren(
    input,
    button(label, () => onGo(input.value.trim()), { tone: 'danger' }),
    button(WORDS.keep, () => holder.replaceChildren(...was), { tone: 'quiet' }),
  );
  input.focus();
}

function entrantActions(t, one) {
  if (!t.may_run || mode() === 'off') return null;
  const holder = el('span', { class: 'bar bk-acts' });
  const path = `${base(t.id)}/entrants/${one.id}`;
  const out = one.dropped || one.dq;
  const parts = [];
  if (out) {
    const back = BEFORE_START.includes(t.state) || (t.state === 'running' && (one.dq || one.dropped_why === 'dropped'));
    if (back && t.state !== 'complete') parts.push(button(WORDS.restore, () => act(`${path}/restore`), { tone: 'quiet' }));
  } else if (BEFORE_START.includes(t.state)) {
    if (t.state === 'check_in') {
      parts.push(button(one.checked_in ? WORDS.checkOutTo : WORDS.checkInTo, () => act(`${path}/checkin`, { checked_in: !one.checked_in }), { tone: 'quiet' }));
    }
    parts.push(button(WORDS.remove, () => reasonRow(holder, 'Remove', (reason) => act(path, { reason }, 'DELETE')), { tone: 'quiet' }));
  } else if (t.state === 'running') {
    parts.push(button(WORDS.dq, () => reasonRow(holder, 'DQ', (reason) => act(`${path}/dq`, { reason })), { tone: 'quiet' }));
    parts.push(button(WORDS.drop, () => reasonRow(holder, 'Drop', (reason) => act(`${path}/drop`, { reason })), { tone: 'quiet' }));
  }
  if (!parts.length) return null;
  holder.append(...parts);
  return holder;
}

function entrantLine(t, one, { handle = null, seed = null } = {}) {
  const waiting = t.state === 'running' ? (t.waiting_on || []).find((row) => row.entrant === one.id) : null;
  const opponent = waiting && waiting.opponent ? (t.entrants.find((row) => row.id === waiting.opponent) || {}).name : '';
  const notes = [
    one.guest ? WORDS.guest : null,
    t.state === 'check_in' && !one.dropped ? (one.checked_in ? WORDS.checkedIn : WORDS.notCheckedIn) : null,
    waiting && t.may_run ? w(`brackets_waiting_${waiting.what}`, { set: waiting.set || '', opponent: opponent || '' }) : null,
  ].filter(Boolean);
  const out = outWords(one);
  return el('div', {
    class: 'rowlist-row bk-entrant',
    'data-id': String(one.id),
    'data-out': out ? 'true' : undefined,
    'data-mine': one.id === t.mine ? 'true' : undefined,
    'data-checked': t.state === 'check_in' && one.checked_in ? 'true' : undefined,
  }, [
    handle,
    el('span', { class: 'bk-seed mono', text: seed ?? (one.seed ?? '—') }),
    el('span', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: one.name }),
      notes.length ? el('span', { class: 'rowlist-note', text: notes.join(' · ') }) : null,
    ]),
    one.placement ? badge(placeWords(one.placement), one.placement <= 3 ? 'ok' : null) : null,
    out ? badge(out, one.dq ? 'danger' : null) : null,
    entrantActions(t, one),
  ]);
}

function activeOf(t) {
  return t.entrants.filter((one) => !one.dropped && !one.dq).sort((a, b) => (a.seed ?? 1e9) - (b.seed ?? 1e9) || a.id - b.id);
}

function seedingList(t) {
  const active = activeOf(t);
  const order = view.seedOrder || active.map((one) => one.id);
  const byId = new Map(active.map((one) => [one.id, one]));
  const list = el('div', { class: 'rowlist bk-seeds' });
  const rows = order.filter((id) => byId.has(id)).map((id, at) => {
    const handle = el('button', { class: 'bk-handle', type: 'button', title: WORDS.move, 'aria-label': `${WORDS.move}: ${byId.get(id).name}`, text: '⠿' });
    const row = entrantLine(t, byId.get(id), { handle, seed: at + 1 });
    dragRow(list, row, handle);
    return row;
  });
  list.append(...rows);
  return list;
}

function orderIn(list) {
  return [...list.querySelectorAll('.bk-entrant')].map((row) => Number(row.getAttribute('data-id')));
}

function dirty(list) {
  view.seedOrder = orderIn(list);
  paintEntrants(true);
}

function dragRow(list, row, handle) {
  handle.addEventListener('keydown', (event) => {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return;
    event.preventDefault();
    const order = orderIn(list);
    const from = order.indexOf(Number(row.getAttribute('data-id')));
    view.seedOrder = moved(order, from, from + (event.key === 'ArrowUp' ? -1 : 1));
    paintEntrants(true);
    const again = view.holders.entrants.querySelector(`.bk-entrant[data-id="${row.getAttribute('data-id')}"] .bk-handle`);
    if (again) again.focus();
  });
  handle.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    row.setAttribute('data-dragging', 'true');
    const moveTo = (y) => {
      const others = [...list.querySelectorAll('.bk-entrant')].filter((one) => one !== row);
      const before = others.find((one) => {
        const box = one.getBoundingClientRect();
        return y < box.top + box.height / 2;
      });
      if (before) list.insertBefore(row, before);
      else list.append(row);
    };
    const onMove = (next) => moveTo(next.clientY);
    const onUp = (last) => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
      if (last.type === 'pointerup') moveTo(last.clientY);
      row.removeAttribute('data-dragging');
      dirty(list);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
  });
}

function shuffled(ids) {
  const found = ids.slice();
  for (let at = found.length - 1; at > 0; at -= 1) {
    const other = Math.floor(Math.random() * (at + 1));
    [found[at], found[other]] = [found[other], found[at]];
  }
  return found;
}

function addEntrant(t) {
  const say = notice();
  const guest = el('input', { class: 'input', type: 'text', maxlength: '100', id: 'bk-guest' });
  const picker = staff() ? memberPicker({ label: 'Member' }) : null;
  const added = async (body) => {
    const done = await act(`${base(t.id)}/entrants`, body, 'POST', say);
    if (done.ok) view.say.say(done.found.message, 'ok');
  };
  return foldout(WORDS.addEntrant, [
    picker ? el('div', { class: 'bk-add' }, [picker.node, button(WORDS.add, () => (picker.id ? added({ user_id: picker.id }) : null), { tone: 'warn' })]) : null,
    el('div', { class: 'bk-add' }, [field(WORDS.guestName, guest), button(WORDS.addGuest, () => (guest.value.trim() ? added({ name: guest.value.trim() }) : null), { tone: 'warn' })]),
    say,
  ]);
}

function entrantsBody(t) {
  const runs = t.may_run && mode() !== 'off';
  const seeding = runs && BEFORE_START.includes(t.state);
  const out = t.entrants.filter((one) => one.dropped || one.dq);
  const parts = [];
  if (seeding) {
    const active = activeOf(t);
    const say = notice();
    const tools = [
      active.length > 1 ? button(WORDS.randomise, () => {
        view.seedOrder = shuffled(view.seedOrder || active.map((one) => one.id));
        paintEntrants(true);
      }, { tone: 'quiet' }) : null,
      view.seedOrder ? button(WORDS.saveSeeding, async () => {
        const done = await act(`${base(t.id)}/seed`, { order: view.seedOrder }, 'POST', say);
        if (done.ok) {
          view.seedOrder = null;
          paintEntrants(true);
          view.say.say(done.found.message, 'ok');
        }
      }, { tone: 'warn' }) : null,
      view.seedOrder ? button(WORDS.discard, () => {
        view.seedOrder = null;
        paintEntrants(true);
      }, { tone: 'quiet' }) : null,
    ].filter(Boolean);
    parts.push(tools.length ? bar(tools) : null, say, seedingList(t));
  } else {
    const playing = new Set(t.sets.flatMap((one) => [one.slot_a, one.slot_b]).filter((id) => id !== null));
    const pool = t.sets.length ? t.entrants.filter((one) => playing.has(one.id)) : activeOf(t);
    const list = t.state === 'complete'
      ? sortedStandings(pool.map((one) => ({ ...one, place: one.placement })))
      : pool.sort((a, b) => (a.seed ?? 1e9) - (b.seed ?? 1e9) || a.id - b.id);
    parts.push(list.length ? el('div', { class: 'rowlist' }, list.map((one, at) => entrantLine(t, one, BEFORE_START.includes(t.state) ? { seed: at + 1 } : {}))) : sayNothing('Nobody yet.'));
  }
  const outBefore = BEFORE_START.includes(t.state) && t.may_run ? out : [];
  if (outBefore.length) parts.push(foldout('Out', [el('div', { class: 'rowlist' }, outBefore.map((one) => entrantLine(t, one)))], { count: outBefore.length }));
  if (seeding) parts.push(addEntrant(t));
  return parts;
}

function paintEntrants(force = false) {
  const t = view.t;
  if (!view.holders.entrants) return;
  update('entrants', sig([t.entrants, t.state, t.may_run, t.mine, t.waiting_on, mode(), view.seedOrder]), view.holders.entrants, () => entrantsBody(t), { force });
  if (view.sections.entrants) view.sections.entrants.count(t.entrant_count);
}

/* ---------- the bracket ---------- */

const W = 188;
const H = 62;
const GAP = 44;
const U = 78;
const HEAD = 26;

function roundWords(set) {
  if (set.side === 'winners') return w('brackets_round_winners', { round: set.round });
  if (set.side === 'losers') return w('brackets_round_losers', { round: set.round });
  if (set.side === 'grand') return w(set.round > 1 ? 'brackets_round_reset' : 'brackets_round_grand');
  if (set.side === 'third') return w('brackets_round_third');
  return w('brackets_round_plain', { round: set.round });
}

function slotLine(t, set, side) {
  const id = side === 'a' ? set.slot_a : set.slot_b;
  const name = side === 'a' ? set.a_name : set.b_name;
  const score = side === 'a' ? set.score_a : set.score_b;
  const won = set.state === 'complete' && set.winner !== null && set.winner === id;
  const lost = set.state === 'complete' && set.winner !== null && id !== null && set.winner !== id;
  const shownScore = set.state === 'complete' && set.forfeit ? (won ? 'W' : 'FF') : score ?? '';
  return el('span', {
    class: 'bk-slot',
    'data-won': won ? 'true' : undefined,
    'data-lost': lost ? 'true' : undefined,
    'data-mine': id !== null && id === t.mine ? 'true' : undefined,
  }, [
    el('span', { class: 'bk-slot-name', text: name || (set.state === 'bye' && id === null ? WORDS.bye : '') }),
    el('span', { class: 'bk-slot-score mono', text: String(shownScore) }),
  ]);
}

function needsYou(t, set, moves) {
  return moves.some((one) => ['report', 'confirm', 'dispute'].includes(one)) || (t.may_run && ['reported', 'disputed'].includes(set.state));
}

function setCard(t, set, style = null) {
  const moves = setMoves(t, set, { mode: mode() });
  const mine = t.mine !== null && (set.slot_a === t.mine || set.slot_b === t.mine);
  const quiet = ['waiting', 'void'].includes(set.state);
  const top = [set.key, `Bo${set.best_of}`, set.rematch ? w('brackets_set_card_rematch') : null].filter(Boolean).join(' · ');
  const stateWord = { called: 'called', reported: 'reported', disputed: 'disputed' }[set.state];
  return el(quiet ? 'div' : 'button', {
    class: 'bk-set',
    type: quiet ? undefined : 'button',
    style: style || undefined,
    'data-key': set.key,
    'data-state': set.state,
    'data-mine': mine ? 'true' : undefined,
    'data-act': needsYou(t, set, moves) ? 'true' : undefined,
    title: `${set.key} · ${roundWords(set)}`,
    on: quiet ? undefined : { click: () => setDrawer(set.key) },
  }, [
    el('span', { class: 'bk-set-top' }, [
      el('span', { class: 'mono', text: top }),
      stateWord ? el('span', { class: 'bk-set-state', 'data-tone': SET_TONES[set.state], text: stateWord }) : null,
    ]),
    slotLine(t, set, 'a'),
    slotLine(t, set, 'b'),
  ]);
}

function treeNode(t) {
  const drawn = eliminationLayout(t.sets);
  const byKey = new Map(t.sets.map((one) => [one.key, one]));
  const at = new Map(drawn.nodes.map((one) => [one.key, one]));
  const width = drawn.cols * (W + GAP) - GAP;
  const height = HEAD + drawn.height * U + 8;
  const x = (node) => node.col * (W + GAP);
  const y = (node) => HEAD + node.y * U;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'bk-lines');
  svg.setAttribute('width', String(width));
  svg.setAttribute('height', String(height));
  svg.setAttribute('aria-hidden', 'true');
  for (const line of drawn.links) {
    const from = at.get(line.from);
    const to = at.get(line.to);
    const x1 = x(from) + W;
    const y1 = y(from);
    const x2 = x(to);
    const y2 = y(to);
    const mid = x1 + Math.min(GAP / 2, (x2 - x1) / 2);
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M${x1} ${y1} H${mid} V${y2} H${x2}`);
    const done = byKey.get(line.from).state === 'complete';
    if (done) path.setAttribute('data-done', 'true');
    svg.append(path);
  }
  const labels = [];
  const seen = new Set();
  for (const node of drawn.nodes) {
    const label = `${node.side}:${node.col}`;
    if (seen.has(label)) continue;
    seen.add(label);
    const topOf = node.side === 'losers' ? drawn.losersTop : node.side === 'third' ? node.y - 0.5 : 0;
    const set = byKey.get(node.key);
    const firstY = node.side === 'grand' ? node.y - 0.5 : topOf;
    labels.push(el('span', { class: 'bk-round', style: `left:${x(node)}px;top:${HEAD + firstY * U - 22}px;width:${W}px`, text: roundWords(set) }));
  }
  const cards = drawn.nodes.map((node) => setCard(t, byKey.get(node.key), `left:${x(node)}px;top:${y(node) - H / 2}px;width:${W}px;height:${H}px`));
  return el('div', { class: 'bk-scroll' }, [
    el('div', { class: 'bk-tree', style: `width:${width}px;height:${height}px` }, [svg, ...labels, ...cards]),
  ]);
}

function roundsNode(t) {
  return el('div', { class: 'bk-scroll' }, [
    el('div', { class: 'bk-rounds' }, roundsLayout(t.sets).map((round) => el('div', { class: 'bk-col' }, [
      el('span', { class: 'bk-round bk-round-flow', text: w('brackets_round_plain', { round: round.round }) }),
      ...round.sets.map((set) => setCard(t, set)),
    ]))),
  ]);
}

function gridNode(t) {
  const { players, cells } = resultsGrid(t.entrants, t.sets);
  return el('div', { class: 'bk-scroll' }, [
    el('table', { class: 'bk-grid' }, [
      el('thead', {}, [el('tr', {}, [el('th', {}), ...players.map((one) => el('th', { scope: 'col', text: one.name }))])]),
      el('tbody', {}, players.map((row, i) => el('tr', { 'data-mine': row.id === t.mine ? 'true' : undefined }, [
        el('th', { scope: 'row', text: row.name }),
        ...cells[i].map((cell) => {
          if (!cell) return el('td', { class: 'bk-cell-self' });
          const set = t.sets.find((one) => one.key === cell.key);
          const text = cell.state === 'complete' ? (cell.forfeit ? (cell.won ? 'W' : 'FF') : `${cell.own}–${cell.theirs}`) : cell.state === 'reported' || cell.state === 'disputed' ? `${cell.own ?? ''}–${cell.theirs ?? ''}?` : '·';
          return el('td', {}, [el('button', {
            class: 'bk-cell',
            type: 'button',
            'data-won': cell.won === true ? 'true' : cell.won === false ? 'false' : undefined,
            'data-state': cell.state,
            'data-act': needsYou(t, set, setMoves(t, set, { mode: mode() })) ? 'true' : undefined,
            title: `${cell.key} · ${roundWords(set)}`,
            text,
            on: { click: () => setDrawer(cell.key) },
          })]);
        }),
      ]))),
    ]),
  ]);
}

function bracketBody(t) {
  if (!t.sets.length) return [sayNothing(WORDS.bracketEmpty)];
  if (ELIMINATION.includes(t.format)) return [treeNode(t)];
  if (t.format === 'round_robin') return [gridNode(t)];
  return [roundsNode(t)];
}

/* ---------- standings ---------- */

function standingsBody(t) {
  const rows = sortedStandings(t.standings || []);
  if (ELIMINATION.includes(t.format)) {
    return [table([
      { label: WORDS.place, cell: (row) => placeWords(row.place), className: 'mono' },
      { label: WORDS.player, key: 'name' },
    ], rows.filter((row) => row.place), { search: false, empty: 'No placings yet.' })];
  }
  const columns = [
    { label: WORDS.place, cell: (row) => placeWords(row.place ?? row.rank), className: 'mono' },
    { label: WORDS.player, key: 'name' },
    { label: WORDS.sets, cell: (row) => `${row.set_wins}–${row.set_losses}`, className: 'mono' },
    { label: WORDS.games, cell: (row) => `${row.game_wins}–${row.game_losses}`, className: 'mono' },
  ];
  if (t.format === 'swiss') {
    columns.push({ label: WORDS.opponents, cell: (row) => (row.opponents_rate === null || row.opponents_rate === undefined ? '—' : `${Math.round(row.opponents_rate * 100)}%`), className: 'mono' });
    columns.push({ label: WORDS.byes, key: 'byes', className: 'mono' });
  }
  return [table(columns, rows, { search: false, empty: 'No results yet.' })];
}

/* ---------- a set ---------- */

function scorePicker(set, onPick) {
  const choices = scoreChoices(set.best_of);
  const node = el('div', { class: 'bk-scores', role: 'group', 'aria-label': `${set.a_name} – ${set.b_name}` });
  let picked = null;
  for (const [a, b] of choices) {
    const one = el('button', {
      class: 'bk-score mono',
      type: 'button',
      'aria-pressed': 'false',
      text: `${a}–${b}`,
      title: `${set.a_name} ${a} – ${b} ${set.b_name}`,
      on: {
        click: () => {
          picked = [a, b];
          for (const other of node.children) other.setAttribute('aria-pressed', other === one ? 'true' : 'false');
          if (onPick) onPick(picked);
        },
      },
    });
    node.append(one);
  }
  return { node, get value() { return picked; } };
}

function stateLine(t, set) {
  const names = { a: set.a_name, b: set.b_name };
  if (set.state === 'ready') return w('brackets_set_card_ready');
  if (set.state === 'called') return w('brackets_set_card_called');
  if (set.state === 'reported') {
    const reporter = names[set.reported_side] || '';
    const opponent = names[set.reported_side === 'a' ? 'b' : 'a'] || '';
    return w('brackets_set_card_reported', { reporter, opponent, score: `${set.score_a}–${set.score_b}`, when: set.confirms_at ? `at ${clockTime(set.confirms_at, view.zone)}` : '' });
  }
  if (set.state === 'disputed') {
    const by = (t.entrants.find((one) => one.user_id && one.user_id === set.disputed_by) || {}).name || '';
    return w('brackets_set_card_disputed', { who: by });
  }
  return null;
}

function discordLink(t, set) {
  const guild = view.me && view.me.guild ? view.me.guild.id : null;
  if (!guild || !t.thread_id || !set.message_id) return null;
  return linkAction(w('brackets_discord_label'), `https://discord.com/channels/${guild}/${t.thread_id}/${set.message_id}`);
}

function setDrawer(key) {
  const t = view.t;
  const set = t.sets.find((one) => one.key === key);
  if (!set) return;
  const moves = setMoves(t, set, { mode: mode() });
  const say = notice();
  const path = `${base(t.id)}/sets/${encodeURIComponent(set.key)}`;
  const go = async (tail, body = {}) => {
    const done = await act(`${path}/${tail}`, body, 'POST', say);
    if (done.ok) {
      closeDrawer();
      view.say.say(done.found.message, 'ok');
    }
  };
  const body = [
    el('div', { class: 'bk-drawer-set' }, [setCard(t, set)]),
    el('p', { class: 'bk-meta', text: [roundWords(set), w('brackets_set_card_best_of', { best_of: set.best_of }), set.rematch ? w('brackets_set_card_rematch') : null].filter(Boolean).join(' · ') }),
  ];
  const line = stateLine(t, set);
  if (line) body.push(el('p', { class: 'bk-state' }, boldParts(line)));
  if (set.state === 'disputed' && set.dispute_note) body.push(el('blockquote', { class: 'bk-note', text: set.dispute_note }));
  const link = discordLink(t, set);
  if (link) body.push(link);

  const picker = moves.includes('report') || moves.includes('decide') ? scorePicker(set) : null;
  const player = [];
  if (moves.includes('report')) {
    player.push(button(w('brackets_report_label'), () => (picker.value ? go('report', { score_a: picker.value[0], score_b: picker.value[1] }) : say.say('Pick the score first.', 'warn')), { tone: 'warn', small: false }));
  }
  if (moves.includes('confirm')) player.push(button(w('brackets_confirm_label'), () => go('confirm'), { tone: 'warn', small: false }));
  let disputeBox = null;
  if (moves.includes('dispute')) {
    const note = el('textarea', { class: 'input', rows: '2', maxlength: '300', id: 'bk-dispute' });
    disputeBox = el('div', { class: 'bk-dispute', hidden: true }, [field(w('brackets_dispute_note_label'), note), button(w('brackets_dispute_label'), () => go('dispute', { note: note.value.trim() }), { tone: 'danger' })]);
    player.push(button(w('brackets_dispute_label'), () => {
      disputeBox.hidden = false;
      note.focus();
    }, { tone: 'quiet', small: false }));
  }
  const organiser = [];
  const reason = el('input', { class: 'input', type: 'text', maxlength: '300', id: 'bk-set-reason' });
  if (moves.includes('call')) organiser.push(button(WORDS.call, () => go('call'), { tone: 'quiet' }));
  if (moves.includes('accept')) organiser.push(button(WORDS.accept, () => go('confirm'), { tone: 'quiet' }));
  if (moves.includes('decide')) organiser.push(button(WORDS.decide, () => (picker.value ? go('override', { score_a: picker.value[0], score_b: picker.value[1], reason: reason.value.trim() }) : say.say('Pick the score first.', 'warn')), { tone: 'warn' }));
  if (moves.includes('forfeit')) {
    for (const side of ['a', 'b']) {
      const name = side === 'a' ? set.a_name : set.b_name;
      if (name) organiser.push(button(said(WORDS.forfeit, { name }), () => go('override', { winner: side, forfeit: true, reason: reason.value.trim() }), { tone: 'quiet' }));
    }
  }
  if (moves.includes('reset')) organiser.push(button(WORDS.resetSet, () => go('reset', { reason: reason.value.trim() }), { tone: 'danger' }));
  if (picker) body.push(picker.node);
  if (player.length) body.push(bar(player));
  if (disputeBox) body.push(disputeBox);
  if (organiser.length) {
    body.push(el('div', { class: 'bk-organiser' }, [
      el('p', { class: 'bk-label', text: WORDS.organiser }),
      bar(organiser),
      moves.some((one) => ['decide', 'forfeit', 'reset'].includes(one)) ? field(WORDS.reason, reason) : null,
    ]));
  }
  body.push(say);
  openDrawer(`${set.key} · ${roundWords(set)}`, body);
}

/* ---------- create / edit ---------- */

function lengthSelect(id, value) {
  const select = el('select', { class: 'input', id });
  for (const one of LENGTHS) select.append(el('option', { value: String(one), text: `Bo${one}`, selected: Number(value) === one || undefined }));
  return select;
}

function numberBox(id, value, { min = 1, max = 1024, blank = '' } = {}) {
  return el('input', { class: 'input', type: 'number', id, min: String(min), max: String(max), value: value ?? undefined, placeholder: blank || undefined });
}

function localValue(iso) {
  if (!iso) return '';
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

async function optionsDrawer(t) {
  let defaults = {};
  if (!t && staff()) {
    try {
      const specs = settingsNamespace(await settings(), 'core');
      const value = (key) => {
        const spec = specs.find((one) => one.key === key);
        return spec ? spec.value ?? spec.default : null;
      };
      defaults = {
        format: value('brackets_format_default'),
        best_of: value('brackets_best_of'),
        best_of_late: value('brackets_best_of_late'),
        best_of_finals: value('brackets_best_of_finals'),
        best_of_from_round: value('brackets_best_of_from_round'),
        grand_final_reset: value('brackets_grand_final_reset_default'),
        third_place: value('brackets_third_place_default'),
        check_in_minutes: value('brackets_check_in_minutes'),
        entrant_cap: value('brackets_entrant_cap_default'),
        swiss_rounds: value('brackets_swiss_rounds_default'),
      };
    } catch (error) {
      defaults = {};
    }
  }
  const o = t ? { ...t.options } : { format: 'double', best_of: 3, best_of_late: 5, best_of_finals: 5, grand_final_reset: true, third_place: false, check_in_minutes: 30, ...Object.fromEntries(Object.entries(defaults).filter(([, v]) => v !== null && v !== undefined)) };
  const name = el('input', { class: 'input', type: 'text', id: 'bk-name', maxlength: '100', value: t ? t.name : undefined });
  const game = el('input', { class: 'input', type: 'text', id: 'bk-game', maxlength: '100', value: t ? t.game || undefined : undefined });
  const format = el('select', { class: 'input', id: 'bk-format' });
  for (const one of FORMATS) format.append(el('option', { value: one, text: formatWords(one), selected: o.format === one || undefined }));
  const startsAt = el('input', { class: 'input', type: 'datetime-local', id: 'bk-starts', value: t ? localValue(t.starts_at) || undefined : undefined });
  const third = el('input', { type: 'checkbox', id: 'bk-third', checked: Boolean(o.third_place) || undefined });
  const reset = el('input', { type: 'checkbox', id: 'bk-reset', checked: o.grand_final_reset !== false || undefined });
  const rounds = numberBox('bk-rounds', o.swiss_rounds, { max: 20, blank: WORDS.roundsAuto });
  const bestOf = lengthSelect('bk-bo', o.best_of);
  const late = lengthSelect('bk-late', o.best_of_late);
  const lateFrom = numberBox('bk-late-from', o.best_of_from_round, { min: 2, blank: '—' });
  const finals = lengthSelect('bk-finals', o.best_of_finals);
  const cap = numberBox('bk-cap', o.entrant_cap, { min: 2, blank: '—' });
  const checkIn = numberBox('bk-checkin', o.check_in_minutes, { min: 5, max: 1440 });
  const rules = el('textarea', { class: 'input', id: 'bk-rules', rows: '4', maxlength: '2000', text: t ? t.rules_text || '' : '' });
  const say = notice();
  const tick = (box, label) => el('label', { class: 'bk-tick' }, [box, el('span', { text: label })]);
  const only = {
    single: el('div', { class: 'bk-fields' }, [tick(third, WORDS.third)]),
    double: el('div', { class: 'bk-fields' }, [tick(reset, WORDS.reset)]),
    swiss: el('div', { class: 'bk-fields' }, [field(WORDS.rounds, rounds)]),
    elimination: el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.lateFrom, lateFrom), field(WORDS.late, late), field(WORDS.finals, finals)]),
  };
  const shapeFor = () => {
    only.single.hidden = format.value !== 'single';
    only.double.hidden = format.value !== 'double';
    only.swiss.hidden = format.value !== 'swiss';
    only.elimination.hidden = !ELIMINATION.includes(format.value);
  };
  format.addEventListener('change', shapeFor);
  shapeFor();
  const number = (box) => (box.value.trim() === '' ? null : Number(box.value));
  const save = async () => {
    if (!name.value.trim()) {
      say.say(WORDS.noName, 'warn');
      return;
    }
    const body = {
      name: name.value.trim(),
      game: game.value.trim(),
      format: format.value,
      best_of: Number(bestOf.value),
      entrant_cap: number(cap),
      check_in_minutes: number(checkIn) ?? 30,
      rules_text: rules.value.trim(),
      starts_at: startsAt.value ? new Date(startsAt.value).toISOString() : null,
    };
    if (format.value === 'single') body.third_place = third.checked;
    if (format.value === 'double') body.grand_final_reset = reset.checked;
    if (format.value === 'swiss') body.swiss_rounds = number(rounds);
    if (ELIMINATION.includes(format.value)) {
      body.best_of_late = Number(late.value);
      body.best_of_finals = Number(finals.value);
      body.best_of_from_round = number(lateFrom);
    }
    const done = await run(say, () => (t ? send(base(t.id), 'PATCH', body) : send('/api/brackets', 'POST', body)), (found) => found.message);
    if (!done.ok) return;
    closeDrawer();
    if (t) {
      take(done.found);
      paint();
      view.say.say(done.found.message, 'ok');
    } else {
      view.pending = done.found.message;
      location.hash = `#${done.found.tournament.id}`;
    }
  };
  openDrawer(t ? said(WORDS.editTitle, { name: t.name }) : WORDS.newTournament, [
    field(WORDS.name, name),
    field(WORDS.game, game),
    el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.format, format), field(WORDS.starts, startsAt)]),
    only.single,
    only.double,
    only.swiss,
    el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.bestOf, bestOf), field(WORDS.cap, cap), field(WORDS.checkIn, checkIn)]),
    only.elimination,
    field(WORDS.rules, rules),
    say,
    bar([button(t ? WORDS.save : WORDS.create, save, { tone: 'warn', small: false })]),
  ]);
  name.focus();
}

/* ---------- logs and settings ---------- */

async function logsNode(tournamentId) {
  const one = section(WORDS.logs, null, { id: 'logs' });
  try {
    const payload = await api('/api/actions?feature=core&q=brackets&details=1&per_page=200');
    const rows = listOf(payload, 'actions')
      .filter((row) => /^(web\.)?brackets\./.test(String(row.kind)))
      .filter((row) => tournamentId === null || String((row.details || {}).tournament) === String(tournamentId));
    await names(idsIn(rows, ['actor_id', 'target_id']));
    one.count(rows.length);
    one.body.append(logsTable(rows.slice(0, 50), WORDS.noLogs));
  } catch (error) {
    const found = sentenceFor(error);
    one.body.append(notice(found.text, found.tone));
  }
  return one.node;
}

async function settingsNode() {
  const one = section(WORDS.settings, null, { id: 'settings' });
  try {
    const specs = settingsNamespace(await settings(true), 'core').filter((spec) => spec.key.startsWith('brackets_'));
    const modeSpec = specs.find((spec) => spec.key === 'brackets_mode');
    const operational = specs.filter((spec) => spec.key !== 'brackets_mode' && spec.type !== 'text');
    const wording = specs.filter((spec) => spec.type === 'text');
    one.count(specs.length);
    one.body.append(...[
      modeSpec ? el('div', { class: 'bar' }, [modeSwitch(modeSpec, { label: 'Tournament brackets', onSaved: () => refresh() }).node]) : null,
      await settingsPanel(operational, { where: WORDS.settings, onSaved: () => refresh() }),
      foldout(WORDS.wording, [await settingsPanel(wording, { where: WORDS.wording })], { count: wording.length }),
    ].filter(Boolean));
  } catch (error) {
    const found = sentenceFor(error);
    one.body.append(notice(found.text, found.tone));
  }
  return one.node;
}

/* ---------- painting ---------- */

function statusText() {
  if (view.failed) return said(WORDS.failed, { why: view.failed });
  if (!view.readAt) return '';
  const seconds = Math.max(0, Math.round((Date.now() - view.readAt) / 1000));
  return said(WORDS.updated, { when: seconds < 5 ? 'just now' : `${seconds} s ago` });
}

function paintStatus() {
  if (!view.status) return;
  view.status.textContent = statusText();
  if (view.failed) view.status.setAttribute('data-tone', 'warn');
  else view.status.removeAttribute('data-tone');
}

function paint() {
  const t = view.t;
  if (!t || !view.holders.head) return;
  const shape = sig([t.id, t.state, t.sets.length > 0, t.format]);
  if (shape !== view.shape) {
    refresh();
    return;
  }
  update('head', sig([t, mode()]), view.holders.head, () => headBody(t));
  paintEntrants();
  if (view.holders.bracket) update('bracket', sig([t.sets, t.mine, t.may_run, t.state, mode()]), view.holders.bracket, () => bracketBody(t));
  if (view.holders.standings) update('standings', sig(t.standings), view.holders.standings, () => standingsBody(t));
  paintStatus();
}

function hasStandings(t) {
  return t.sets.length > 0 && (t.state === 'complete' || !ELIMINATION.includes(t.format));
}

async function tournamentView(id) {
  let t;
  try {
    t = await api(base(id));
  } catch (error) {
    if (error.status !== 404 && error.status !== 400) throw error;
    return [notice(error.message, 'warn'), await listView()].flat();
  }
  view.t = t;
  view.seedOrder = null;
  view.shape = sig([t.id, t.state, t.sets.length > 0, t.format]);
  view.parts = new Map();
  view.say = notice();
  view.say.setAttribute('data-span', 'full');
  view.status = el('p', { class: 'bk-status', role: 'status' });
  view.holders = { head: el('div', { class: 'card-body bk-head' }) };
  view.sections = {};
  const started = t.sets.length > 0;
  const blocks = [el('div', { class: 'card bk-headcard', 'data-span': 'full' }, [view.holders.head, el('div', { class: 'bk-statusrow' }, [view.status])]), view.say];
  if (started) {
    const one = section(WORDS.bracket, null, { id: 'bracket', open: true });
    one.node.setAttribute('data-span', 'full');
    view.holders.bracket = one.body;
    view.sections.bracket = one;
    blocks.push(one.node);
  } else {
    view.holders.bracket = null;
  }
  if (hasStandings(t)) {
    const one = section(WORDS.standings, null, { id: 'standings', open: true });
    view.holders.standings = one.body;
    blocks.push(one.node);
  } else {
    view.holders.standings = null;
  }
  const entrants = section(WORDS.entrants, null, { id: 'entrants', open: !started });
  view.holders.entrants = entrants.body;
  view.sections.entrants = entrants;
  blocks.push(entrants.node);
  paint();
  if (staff()) blocks.push(await logsNode(t.id), await settingsNode());
  return blocks;
}

async function listView() {
  view.t = null;
  view.holders = { list: el('div', { class: 'section-body' }) };
  view.status = el('p', { class: 'bk-status', role: 'status' });
  const one = section('Tournaments', null, { id: 'tournaments', open: true });
  one.node.setAttribute('data-span', 'full');
  const list = el('div', { class: 'bk-list' }, listBody().filter(Boolean));
  one.body.append(list, view.status);
  view.holders.list = list;
  view.parts.set('list', sig(view.index.tournaments));
  const blocks = [one.node];
  if (staff()) blocks.push(await logsNode(null), await settingsNode());
  return blocks;
}

function aside() {
  const holder = document.getElementById('page-aside');
  if (!holder) return;
  holder.replaceChildren(...(view.t ? [linkAction(WORDS.back, '#')] : []));
}

async function poll() {
  if (document.hidden || !view.index) return;
  try {
    if (view.t) {
      const found = await api(base(view.t.id));
      view.t = found;
      view.readAt = Date.now();
      view.failed = null;
      paint();
    } else if (view.holders.list) {
      view.index = await api('/api/brackets');
      view.readAt = Date.now();
      view.failed = null;
      const wanted = sig(view.index.tournaments);
      if (view.parts.get('list') !== wanted && !typing(view.holders.list)) {
        view.holders.list.replaceChildren(...listBody().filter(Boolean));
        view.parts.set('list', wanted);
      }
      paintStatus();
    }
  } catch (error) {
    view.failed = error instanceof Outage ? WORDS.outage : String(error.message || WORDS.outage);
    paintStatus();
  }
}

async function load(me) {
  view.me = me;
  view.zone = viewerZone('UTC').zone;
  view.parts = new Map();
  view.index = await api('/api/brackets');
  view.readAt = Date.now();
  view.failed = null;
  const id = wantedId();
  const blocks = id ? await tournamentView(id) : await listView();
  document.getElementById('dash').replaceChildren(...blocks.filter(Boolean));
  if (view.pending && view.say) view.say.say(view.pending, 'ok');
  view.pending = null;
  aside();
  paintStatus();
  if (view.timer === null) {
    view.timer = setInterval(poll, POLL_MS);
    view.clock = setInterval(paintStatus, 1000);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) poll();
    });
  }
}

window.addEventListener('hashchange', () => {
  if (/^#?\d*$/.test(location.hash || '')) {
    closeDrawer();
    refresh();
  }
});

refresh = start({ tab: TAB, load });
