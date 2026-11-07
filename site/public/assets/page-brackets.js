import { api, listOf, names, Outage, refSports, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import {
  BEFORE_START,
  ELIMINATION,
  LIVE,
  OPEN,
  PLAYING,
  allSets,
  eliminationLayout,
  feedState,
  fill,
  isList,
  memberMoves,
  moved,
  myEntrant,
  organiserMoves,
  placeWords,
  poolLetter,
  poolTable,
  resultsGrid,
  roundsLayout,
  scoreChoices,
  scoreLine,
  seedOrderWith,
  setMoves,
  sortedStandings,
  tieOrder,
  TREE,
  treeSize,
} from './bracket-layout.js';
import { logsTable } from './logs.js';
import { clockTime, dayLabel, viewerZone } from './timezone.js';
import {
  ago,
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
  remoteSearch,
  run,
  sayNothing,
  section,
  segment,
  sentenceFor,
  settingsPanel,
  table,
} from './ui.js';

const POLL_MS = 15000;
const TAB = 'brackets';
const LENGTHS = [1, 3, 5, 7, 9, 11, 13, 15];
const FORMATS = ['double', 'single', 'round_robin', 'swiss'];
const POOL_FORMATS = ['none', 'round_robin', 'swiss'];
const KINDS = ['fighters', 'sports', 'list'];
const DECIDERS = ['votes', 'organiser'];
const STATE_TONES = { signups: 'info', check_in: 'info', seeding: 'warn', pools: 'ok', running: 'ok', cancelled: 'danger' };
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
  advance: 'Advance to the final',
  unadvance: 'Back to pools',
};
const SPORTS_MOVES = { import: 'brackets_import_label', build: 'brackets_build_label', sync: 'brackets_sync_label' };
const SOURCE_NAMES = { espn: 'ESPN', ncaa: 'NCAA (ncaa-api)', nhl: 'NHL', nba: 'NBA', mlb: 'MLB' };
const LIVE_STATUSES = ['scheduled', 'live', 'final'];
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
  advance: 'advance',
  unadvance: 'unadvance',
  import: 'import',
  build: 'build',
  sync: 'sync',
};
const ASKS = {
  advance: ["Build {name}'s final from the pools?", 'Advance'],
  unadvance: ["Send {name} back to its pools? The final's sets are cleared.", 'Back to pools'],
  unstart: ['Back to seeding? Every set and result is cleared.', 'Back to seeding'],
  cancel: ['Cancel {name}?', 'Cancel it'],
  move: ['Move {name} into #knuck-up? Its cards are posted there and its players are pinged.', 'Move it'],
};
const TONES = { cancel: 'danger', unstart: 'warn', move: 'warn', start: null, advance: 'warn', unadvance: 'warn' };
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
  seedNote: 'seed {seed}',
  gamesNote: 'games {games}',
  opponentsNote: 'opp. {rate}',
  byesNote: '{byes} bye(s)',
  bracketEmpty: 'The bracket is drawn when the tournament starts.',
  move: 'Drag to reorder',
  pools: 'Pools',
  final: 'Final',
  poolsFormat: 'Pools',
  noPools: 'None',
  poolCountLabel: 'How many pools',
  advancePer: 'Through from each',
  losersFrom: 'Losers from place',
  poolsBestOf: 'Pool best of',
  poolRounds: 'Pool Swiss rounds',
  kind: 'Kind',
  decideBy: 'Decided by',
  voteMinutes: 'Vote minutes',
  nameToAdd: 'Name',
  short: 'Short name',
  seed: 'Seed',
  match: 'Match',
  clearMatch: 'Clear match',
  findName: 'Team, school or player',
  teams: 'Teams',
  schools: 'Schools',
  players: 'Players',
  sportsNames: 'Sports names',
  refreshNames: 'Refresh now',
  namesList: 'List',
  namesCount: 'Names',
  namesUpdated: 'Updated',
  namesFailure: 'Last failure',
  namesTeams: '{league} teams',
  namesPlayers: '{league} players',
  pickFirst: 'Pick the score first.',
  league: 'League',
  season: 'Season',
  results: 'Results',
  feed: 'Feed',
  when: 'Starts',
  status: 'Status',
  statuses: { scheduled: 'Scheduled', live: 'Live', final: 'Final' },
  scoreOf: '{name} score',
  slotOf: 'Slot {slot}',
  empty: 'Nobody yet',
  held: 'held',
  rebuildAsks: 'Building again replaces every set in {name}, hand edits included.',
  wins: '{name} wins',
  votes: '{count} votes',
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
  ties: {},
  timer: null,
  clock: null,
  filter: { query: '', filter: 'all', kind: 'all' },
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

function kindWords(kind) {
  return w(`brackets_kind_${kind || 'fighters'}_words`) || kind;
}

function decideWords(decide) {
  return decide ? w(`brackets_decide_${decide}_words`) || decide : null;
}

function kindBadge(t) {
  return t.kind && t.kind !== 'fighters' ? badge(kindWords(t.kind), 'info') : null;
}

function poolsWords(format) {
  return format && format !== 'none' ? `${formatWords(format)} pools` : null;
}

function stateBadge(state) {
  return badge(w(`brackets_state_${state}`) || state, STATE_TONES[state] || null);
}

function wantedId() {
  const found = /^#(\d+)$/.exec(location.hash || '');
  return found ? found[1] : null;
}

const LEAGUES = ['nfl', 'nba', 'mlb', 'nhl', 'ncaam', 'ncaaw'];
const NAME_KINDS = [['team', WORDS.teams], ['school', WORDS.schools], ['player', WORDS.players]];

function isSports(t) {
  return Boolean(t) && t.kind === 'sports';
}

function leagueWord(code) {
  return code ? w(`brackets_league_${code}_words`) || code.toUpperCase() : '';
}

function matchWords(one) {
  return [one.short, leagueWord(one.league), one.team].filter(Boolean).join(' · ');
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
    poolsWords(t.pools_format),
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
    kindBadge(t),
    stateBadge(t.state),
  ]);
}

function ordered(rows) {
  const live = rows.filter((t) => LIVE.includes(t.state) || t.state === 'draft');
  const rank = { running: 0, pools: 0, check_in: 1, signups: 2, seeding: 3, draft: 4 };
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
  const kinds = [['all', WORDS.all, null], ...KINDS.map((kind) => [kind, kindWords(kind), (t) => (t.kind || 'fighters') === kind])];
  const filter = listFilter({
    items,
    value: (item) => item.t,
    text: (t) => [t.name, t.game, formatWords(t.format), kindWords(t.kind), w(`brackets_state_${t.state}`), t.to_name].join(' '),
    filters,
    filter: view.filter.filter,
    groups: [{ filters: kinds, filter: view.filter.kind }],
    query: view.filter.query,
    label: WORDS.searchLabel,
    placeholder: WORDS.search,
    empty: WORDS.noMatch,
    onChange: ({ query, filter: key, groups }) => {
      const kind = (groups && groups[0]) || 'all';
      view.filter = { query, filter: key, kind };
      for (const fold of folds) if (query || key !== 'all' || kind !== 'all') fold.open = true;
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
    const ready = allSets(t).filter((one) => one.state === 'ready');
    for (const one of ready) {
      const done = await act(`${base(t.id)}/sets/${encodeURIComponent(one.key)}/call`);
      if (!done.ok) break;
    }
    return null;
  }
  if (move === 'import' || move === 'build') {
    const has = move === 'import' ? (t.entrants || []).length || t.sets.length : t.sets.length;
    if (has) {
      const title = move === 'import' ? w('brackets_reimport_asks', { name: t.name }).replace(/\*\*/g, '') : said(WORDS.rebuildAsks, { name: t.name });
      const yes = await ask({ title, body: [], confirmLabel: w(SPORTS_MOVES[move]), tone: 'warn' });
      if (!yes) return null;
    }
    return act(`${base(t.id)}/${PATHS[move]}`, { replace: Boolean(has) });
  }
  if (ASKS[move]) {
    const [title, confirmLabel] = ASKS[move];
    const yes = await ask({ title: said(title, { name: t.name }), body: [], confirmLabel, tone: TONES[move] || 'danger' });
    if (!yes) return null;
  }
  if (move === 'advance') {
    const order = (t.pools || []).flatMap((pool) => (pool.tied && pool.tied.length ? tieOrder(pool, view.ties[pool.pool]) : []));
    const done = await act(`${base(t.id)}/advance`, order.length ? { order } : {});
    if (done.ok) view.ties = {};
    return done;
  }
  return act(`${base(t.id)}/${PATHS[move]}`, {});
}

const MEMBER_LABELS = {
  join: 'brackets_sign_up_label',
  check_in: 'brackets_check_in_label',
  leave: 'brackets_leave_label',
  drop_out: 'brackets_drop_label',
};

function moveBar(t) {
  const members = memberMoves(t, mode()).map((move) => button(w(MEMBER_LABELS[move]), () => memberMove(move), { tone: move === 'join' || move === 'check_in' ? 'warn' : 'quiet', small: false }));
  const organisers = organiserMoves(t, { mode: mode(), staff: staff() }).map((move) => button(ORGANISER[move] || w(SPORTS_MOVES[move]), () => organiserMove(move), { tone: move === 'cancel' ? 'danger' : ['start', 'complete', 'open_signups', 'open_check_in', 'move', 'restore', 'reopen', 'advance', 'import'].includes(move) ? 'warn' : 'quiet' }));
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
  if (o.pools_format && o.pools_format !== 'none') {
    found.unshift(w('brackets_card_pools_words', { count: o.pool_count, format: formatWords(o.pools_format), advance: o.advance_per_pool }));
    if (t.format === 'double' && o.advance_losers_from) found.push(w('brackets_card_losers_words', { place: o.advance_losers_from }));
  }
  if (t.format === 'double' && o.grand_final_reset) found.push(w('brackets_card_reset_words'));
  if (t.format === 'single' && o.third_place) found.push(w('brackets_card_third_words'));
  if (t.format === 'swiss' && t.rounds_to_play) found.push(w('brackets_card_rounds_words', { rounds: t.rounds_to_play }));
  if (ELIMINATION.includes(t.format)) {
    if (o.best_of_from_round) found.push(w('brackets_card_late_words', { best_of: o.best_of_late, top: o.best_of_from_round }));
    if (o.best_of_finals !== o.best_of) found.push(w('brackets_card_finals_words', { best_of: o.best_of_finals }));
  }
  return found.filter(Boolean);
}

function waitingLine(t) {
  if (!PLAYING.includes(t.state) || t.mine === null || t.mine === undefined) return null;
  const mine = (t.waiting_on || []).find((one) => one.entrant === t.mine);
  if (!mine) return null;
  const opponent = (t.entrants.find((one) => one.id === mine.opponent) || {}).name || '';
  const text = w(`brackets_waiting_${mine.what}`, { set: mine.set || '', opponent });
  if (!text) return null;
  const set = mine.set ? allSets(t).find((one) => one.key === mine.set) : null;
  const tone = ['play', 'called', 'confirm'].includes(mine.what) ? 'warn' : null;
  return el('div', { class: 'bk-you', 'data-tone': tone || undefined }, [
    set && setMoves(t, set, { mode: mode() }).length
      ? el('button', { class: 'bk-you-go', type: 'button', text, on: { click: () => setDrawer(set.key) } })
      : el('span', { text }),
  ]);
}

function sourceName(t) {
  return SOURCE_NAMES[t.source] || w('brackets_source_own_words');
}

function feedLine(t) {
  const found = feedState(t);
  if (found === 'own') return el('p', { class: 'bk-meta bk-feed', text: w('brackets_source_own_words') });
  if (found === 'down') return el('p', { class: 'bk-meta bk-feed', 'data-tone': 'danger', text: w('brackets_feed_down_line', { when: stamp(t.feed_failed_at) }) });
  if (found === 'via') {
    const when = ago(t.feed_ok_at);
    return el('p', { class: 'bk-meta bk-feed', title: when.title, text: w('brackets_feed_via_line', { source: sourceName(t), ago: when.text }) });
  }
  return null;
}

function headBody(t) {
  const cap = t.options && t.options.entrant_cap ? `${t.entrant_count}/${t.options.entrant_cap}` : String(t.entrant_count);
  const listed = isList(t);
  const sports = isSports(t);
  const meta = [
    t.game,
    listed ? kindWords(t.kind) : null,
    sports ? t.season : null,
    formatWords(t.format),
    ...(listed ? [decideWords(t.decide_by)] : sports ? [] : optionWords(t)),
    `${cap} ${t.entrant_count === 1 && !t.options.entrant_cap ? 'entrant' : 'entrants'}`,
    t.to_name,
  ].filter(Boolean);
  const times = [];
  if (t.starts_at && BEFORE_START.includes(t.state)) times.push(stamp(t.starts_at));
  if (t.state === 'check_in' && t.check_in_closes_at) times.push(`check-in closes ${clockTime(t.check_in_closes_at, view.zone)}`);
  if (PLAYING.includes(t.state) && t.started_at) times.push(`started ${stamp(t.started_at)}`);
  if (t.state === 'complete' && t.completed_at) times.push(stamp(t.completed_at));
  return [
    el('div', { class: 'bk-title' }, [el('h2', { class: 'bk-name', text: t.name }), kindBadge(t), sports && t.league ? badge(leagueWord(t.league), 'info') : null, stateBadge(t.state), t.shadow && view.index.may_run ? badge('rehearsal', 'warn') : null]),
    el('p', { class: 'bk-meta', text: meta.join(' · ') }),
    sports ? feedLine(t) : null,
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

async function entrantMove(path, body = {}, method = 'POST') {
  const done = await act(path, body, method);
  if (done.ok) paintEntrants(true);
  return done;
}

function sportsNotes(t, one) {
  if (!isSports(t)) return [];
  if (!one.ext_id) return [one.short, w('brackets_typed_entrant_note')].filter(Boolean);
  const matched = [leagueWord(one.ext_league), one.ext_name !== one.name ? one.ext_name : null];
  return [one.short, ...matched].filter(Boolean);
}

function editRow(t, one, holder) {
  const say = notice();
  const name = el('input', { class: 'input', type: 'text', maxlength: '100', value: one.name, 'aria-label': WORDS.name });
  const short = el('input', { class: 'input bk-short', type: 'text', maxlength: '20', value: one.short || '', 'aria-label': WORDS.short });
  const seed = el('input', { class: 'input bk-seedbox', type: 'number', min: '1', max: '1024', value: one.seed ?? '', 'aria-label': WORDS.seed });
  const ext = { source: one.ext_source || null, id: one.ext_id || null, words: one.ext_id ? [leagueWord(one.ext_league), one.ext_name].filter(Boolean).join(' · ') : '' };
  const matchLine = el('span', { class: 'rowlist-note bk-match' });
  const paintMatch = () => {
    matchLine.replaceChildren(...[
      el('span', { text: ext.id ? ext.words || `${ext.source} ${ext.id}` : w('brackets_typed_entrant_note') }),
      ext.id ? button(WORDS.clearMatch, () => {
        Object.assign(ext, { source: null, id: null, words: '' });
        paintMatch();
      }, { tone: 'quiet' }) : null,
    ].filter(Boolean));
  };
  paintMatch();
  const finder = isSports(t) ? sportsFinder({
    onPick: (found) => {
      if (!found) return;
      Object.assign(ext, { source: found.source, id: found.ext_id, words: [leagueWord(found.league), found.name].filter(Boolean).join(' · ') });
      if (!short.value.trim() && found.short) short.value = found.short;
      paintMatch();
      finder.clear();
    },
  }) : null;
  const saveIt = async () => {
    const body = {};
    if (name.value.trim() !== one.name) body.name = name.value.trim();
    if (short.value.trim() !== (one.short || '')) body.short = short.value.trim();
    const wanted = seed.value === '' ? null : Number(seed.value);
    if (wanted !== (one.seed ?? null)) body.seed = wanted;
    if (ext.id !== (one.ext_id || null)) Object.assign(body, { ext_source: ext.source, ext_id: ext.id });
    const done = await act(`${base(t.id)}/entrants/${one.id}`, body, 'PATCH', say);
    if (done.ok) {
      view.say.say(done.found.message, 'ok');
      paintEntrants(true);
    }
  };
  const was = [...holder.childNodes];
  holder.replaceChildren(el('div', { class: 'bk-edit' }, [
    field(WORDS.name, name),
    field(WORDS.short, short),
    field(WORDS.seed, seed),
    isSports(t) ? field(WORDS.match, matchLine) : null,
    finder ? finder.node : null,
    bar([button(WORDS.save, saveIt, { tone: 'warn' }), button(WORDS.keep, () => holder.replaceChildren(...was), { tone: 'quiet' })]),
    say,
  ]));
  name.focus();
}

function entrantActions(t, one) {
  if (!t.may_run || mode() === 'off') return null;
  const holder = el('span', { class: 'bar bk-acts' });
  const path = `${base(t.id)}/entrants/${one.id}`;
  const out = one.dropped || one.dq;
  const parts = [];
  if (isSports(t) || isList(t)) parts.push(button(w('brackets_edit_entrant_label'), () => editRow(t, one, holder), { tone: 'quiet' }));
  if (out) {
    const back = BEFORE_START.includes(t.state) || (PLAYING.includes(t.state) && (one.dq || one.dropped_why === 'dropped'));
    if (back && t.state !== 'complete') parts.push(button(WORDS.restore, () => entrantMove(`${path}/restore`), { tone: 'quiet' }));
  } else if (BEFORE_START.includes(t.state)) {
    if (t.state === 'check_in') {
      parts.push(button(one.checked_in ? WORDS.checkOutTo : WORDS.checkInTo, () => entrantMove(`${path}/checkin`, { checked_in: !one.checked_in }), { tone: 'quiet' }));
    }
    parts.push(button(WORDS.remove, () => reasonRow(holder, 'Remove', (reason) => entrantMove(path, { reason }, 'DELETE')), { tone: 'quiet' }));
  } else if (PLAYING.includes(t.state)) {
    parts.push(button(WORDS.dq, () => reasonRow(holder, 'DQ', (reason) => entrantMove(`${path}/dq`, { reason })), { tone: 'quiet' }));
    parts.push(button(WORDS.drop, () => reasonRow(holder, 'Drop', (reason) => entrantMove(`${path}/drop`, { reason })), { tone: 'quiet' }));
  }
  if (!parts.length) return null;
  holder.append(...parts);
  return holder;
}

function entrantLine(t, one, { handle = null, seed = null, placed = false } = {}) {
  const waiting = PLAYING.includes(t.state) ? (t.waiting_on || []).find((row) => row.entrant === one.id) : null;
  const opponent = waiting && waiting.opponent ? (t.entrants.find((row) => row.id === waiting.opponent) || {}).name : '';
  const lead = placed ? placeWords(one.placement) || '—' : seed ?? (one.seed ?? '—');
  const notes = [
    placed && one.seed ? said(WORDS.seedNote, { seed: one.seed }) : null,
    one.guest && !isList(t) && !isSports(t) ? WORDS.guest : null,
    ...sportsNotes(t, one),
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
    el('span', { class: 'bk-seed mono', 'data-place': placed ? 'true' : undefined, text: String(lead) }),
    el('span', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: one.name }),
      notes.length ? el('span', { class: 'rowlist-note', text: notes.join(' · ') }) : null,
    ]),
    one.placement && !placed ? badge(placeWords(one.placement), one.placement <= 3 ? 'ok' : null) : null,
    out ? badge(out, one.dq ? 'danger' : null) : null,
    entrantActions(t, one),
  ]);
}

function activeOf(t) {
  return t.entrants.filter((one) => !one.dropped && !one.dq).sort((a, b) => (a.seed ?? 1e9) - (b.seed ?? 1e9) || a.id - b.id);
}

function unsaved(order) {
  return seedOrderWith(order, activeOf(view.t).map((one) => one.id));
}

function seedingList(t) {
  const active = activeOf(t);
  const order = view.seedOrder ? unsaved(view.seedOrder) : active.map((one) => one.id);
  const byId = new Map(active.map((one) => [one.id, one]));
  const list = el('div', { class: 'rowlist bk-seeds' });
  const rows = order.map((id, at) => {
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
  view.seedOrder = unsaved(orderIn(list));
  paintEntrants(true);
}

function dragRow(list, row, handle) {
  handle.addEventListener('keydown', (event) => {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return;
    event.preventDefault();
    const order = orderIn(list);
    const from = order.indexOf(Number(row.getAttribute('data-id')));
    view.seedOrder = unsaved(moved(order, from, from + (event.key === 'ArrowUp' ? -1 : 1)));
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

function addName(t) {
  const say = notice();
  const box = el('input', { class: 'input', type: 'text', maxlength: '100', id: 'bk-guest' });
  const added = async () => {
    if (!box.value.trim()) return;
    const done = await act(`${base(t.id)}/entrants`, { name: box.value.trim() }, 'POST', say);
    if (done.ok) view.say.say(done.found.message, 'ok');
  };
  box.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') added();
  });
  return foldout(WORDS.addEntrant, [
    el('div', { class: 'bk-add' }, [field(WORDS.nameToAdd, box), button(WORDS.add, added, { tone: 'warn' })]),
    say,
  ], { open: true });
}

function sportsFinder({ onPick, typed = false }) {
  const leagues = [['', WORDS.all], ...LEAGUES.map((code) => [code, leagueWord(code)])];
  return remoteSearch({
    label: WORDS.findName,
    placeholder: WORDS.findName,
    className: 'bk-sports-add',
    groups: [
      { choices: NAME_KINDS, current: 'team', chipClass: 'bk-kinds' },
      { choices: leagues, current: '', chipClass: 'bk-leagues' },
    ],
    fetch: (query, [kind, league]) => refSports(kind, kind === 'school' ? '' : league, query),
    row: (one) => [
      el('span', { class: 'remote-name', text: one.name }),
      el('span', { class: 'remote-note', text: matchWords(one) }),
    ],
    typedRow: typed ? (text) => [
      el('span', { class: 'remote-name', text: w('brackets_use_typed_label', { typed: text }) }),
      el('span', { class: 'remote-note', text: w('brackets_typed_entrant_note') }),
    ] : null,
    onPick,
  });
}

function addSports(t) {
  const say = notice();
  const finder = sportsFinder({
    typed: true,
    onPick: async (one, text) => {
      const body = one ? { name: one.name, ext_source: one.source, ext_id: one.ext_id, short: one.short } : { name: text };
      const done = await act(`${base(t.id)}/entrants`, body, 'POST', say);
      if (!done.ok) return;
      view.say.say(done.found.message, 'ok');
      paintEntrants(true);
      const again = view.holders.entrants && view.holders.entrants.querySelector('.bk-sports-add input');
      if (again) again.focus();
    },
  });
  return foldout(WORDS.addEntrant, [finder.node, say], { open: true });
}

function addEntrant(t) {
  if (isSports(t)) return addSports(t);
  if (isList(t)) return addName(t);
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
        view.seedOrder = shuffled(view.seedOrder ? unsaved(view.seedOrder) : active.map((one) => one.id));
        paintEntrants(true);
      }, { tone: 'quiet' }) : null,
      view.seedOrder ? button(WORDS.saveSeeding, async () => {
        const done = await act(`${base(t.id)}/seed`, { order: unsaved(view.seedOrder) }, 'POST', say);
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
    const sets = allSets(t);
    const playing = new Set(sets.flatMap((one) => [one.slot_a, one.slot_b]).filter((id) => id !== null));
    const pool = sets.length ? t.entrants.filter((one) => playing.has(one.id)) : activeOf(t);
    const list = t.state === 'complete'
      ? sortedStandings(pool.map((one) => ({ ...one, place: one.placement })))
      : pool.sort((a, b) => (a.seed ?? 1e9) - (b.seed ?? 1e9) || a.id - b.id);
    const shape = (at) => (BEFORE_START.includes(t.state) ? { seed: at + 1 } : { placed: t.state === 'complete' });
    parts.push(list.length ? el('div', { class: 'rowlist' }, list.map((one, at) => entrantLine(t, one, shape(at)))) : sayNothing('Nobody yet.'));
  }
  const outBefore = BEFORE_START.includes(t.state) && t.may_run ? out : [];
  if (outBefore.length) parts.push(foldout('Out', [el('div', { class: 'rowlist' }, outBefore.map((one) => entrantLine(t, one)))], { count: outBefore.length }));
  if (seeding) parts.push(addEntrant(t));
  return parts;
}

function paintEntrants(force = false) {
  const t = view.t;
  if (!view.holders.entrants) return;
  if (view.seedOrder) view.seedOrder = unsaved(view.seedOrder);
  if (!force && view.holders.entrants.querySelector('[data-dragging]')) return;
  update('entrants', sig([t.entrants, t.state, t.may_run, t.mine, t.waiting_on, mode(), view.seedOrder]), view.holders.entrants, () => entrantsBody(t), { force });
  if (view.sections.entrants) view.sections.entrants.count(t.entrant_count);
}

/* ---------- the bracket ---------- */

const H = 62;
const U = 78;
const HEAD = 26;
const SIDE_PAD = 40;

function roundWords(set) {
  if (set.pool) return w('brackets_round_pool', { pool: poolLetter(set.pool), round: set.round });
  if (set.side === 'winners') return w('brackets_round_winners', { round: set.round });
  if (set.side === 'losers') return w('brackets_round_losers', { round: set.round });
  if (set.side === 'grand') return w(set.round > 1 ? 'brackets_round_reset' : 'brackets_round_grand');
  if (set.side === 'third') return w('brackets_round_third');
  return w('brackets_round_plain', { round: set.round });
}

function slotLine(t, set, side) {
  const id = side === 'a' ? set.slot_a : set.slot_b;
  const name = side === 'a' ? set.a_name : set.b_name;
  const counted = set.vote_open ? (side === 'a' ? set.votes_a : set.votes_b) : null;
  const score = counted ?? (side === 'a' ? set.score_a : set.score_b);
  const won = set.state === 'complete' && set.winner !== null && set.winner === id;
  const lost = set.state === 'complete' && set.winner !== null && id !== null && set.winner !== id;
  const shownScore = set.state === 'complete' && set.forfeit ? (won ? 'W' : 'FF') : score ?? '';
  return el('span', {
    class: 'bk-slot',
    'data-won': won ? 'true' : undefined,
    'data-lost': lost ? 'true' : undefined,
    'data-mine': id !== null && id === t.mine ? 'true' : undefined,
  }, [
    el('span', { class: 'bk-slot-name', text: name || '' }),
    el('span', { class: 'bk-slot-score mono', text: String(shownScore) }),
  ]);
}

function sportsLine(set) {
  const words = { final: w('brackets_score_final_line'), live: w('brackets_score_live_line'), scheduled: w('brackets_score_scheduled_line') };
  return scoreLine(set, words, (iso) => stamp(iso));
}

function needsYou(t, set, moves) {
  return moves.some((one) => ['report', 'confirm', 'dispute'].includes(one)) || (t.may_run && ['reported', 'disputed'].includes(set.state));
}

function setCard(t, set, style = null) {
  const moves = setMoves(t, set, { mode: mode() });
  const mine = t.mine !== null && (set.slot_a === t.mine || set.slot_b === t.mine);
  const quiet = ['waiting', 'void', 'bye'].includes(set.state);
  const sports = isSports(t);
  const best = isList(t) ? null : sports ? sportsLine(set) || null : `Bo${set.best_of}`;
  const top = [set.key, best, set.rematch ? w('brackets_set_card_rematch') : null].filter(Boolean).join(' · ');
  const stateWord = sports ? (set.held ? w('brackets_held_note') : null) : isList(t) && set.state === 'reported' ? 'tied' : { called: 'called', reported: 'reported', disputed: 'disputed' }[set.state];
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

function treeRoom() {
  const holder = view.holders.bracket;
  if (holder && holder.isConnected && holder.clientWidth) {
    const pad = getComputedStyle(holder);
    return Math.max(0, holder.clientWidth - parseFloat(pad.paddingLeft) - parseFloat(pad.paddingRight));
  }
  const dash = document.getElementById('dash');
  return Math.max(0, (dash ? dash.clientWidth : window.innerWidth) - SIDE_PAD);
}

function scrollHints(box) {
  const mark = () => {
    const left = box.scrollLeft > 2;
    const right = box.scrollLeft + box.clientWidth < box.scrollWidth - 2;
    if (left || right) box.setAttribute('data-more', left && right ? 'both' : left ? 'left' : 'right');
    else box.removeAttribute('data-more');
  };
  box.addEventListener('scroll', mark, { passive: true });
  if (typeof ResizeObserver === 'function') new ResizeObserver(mark).observe(box);
  else requestAnimationFrame(mark);
  return box;
}

function treeNode(t) {
  const drawn = eliminationLayout(t.sets);
  const byKey = new Map(t.sets.map((one) => [one.key, one]));
  const at = new Map(drawn.nodes.map((one) => [one.key, one]));
  const size = treeSize(drawn.cols, treeRoom());
  view.treeSize = sig(size);
  const W = size.width;
  const GAP = size.gap;
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
  return scrollHints(el('div', { class: 'bk-scroll' }, [
    el('div', { class: 'bk-tree', 'data-tight': size.width < TREE.width ? 'true' : undefined, style: `width:${width}px;height:${height}px` }, [svg, ...labels, ...cards]),
  ]));
}

function byeLine(t, set) {
  const id = set.slot_a ?? set.slot_b;
  const name = set.a_name || set.b_name || '';
  return el('p', { class: 'bk-bye', 'data-key': set.key, 'data-mine': id !== null && id === t.mine ? 'true' : undefined }, [
    el('span', { class: 'bk-slot-name', text: name }),
    el('span', { class: 'mono', text: WORDS.bye }),
  ]);
}

function roundsNode(t, sets = t.sets) {
  return scrollHints(el('div', { class: 'bk-scroll' }, [
    el('div', { class: 'bk-rounds' }, roundsLayout(sets).map((round) => el('div', { class: 'bk-col' }, [
      el('span', { class: 'bk-round bk-round-flow', text: w('brackets_round_plain', { round: round.round }) }),
      ...round.sets.filter((set) => set.state !== 'void').map((set) => (set.state === 'bye' ? byeLine(t, set) : setCard(t, set))),
    ]))),
  ]));
}

function gridNode(t, sets = t.sets) {
  const { players, cells } = resultsGrid(t.entrants, sets);
  return scrollHints(el('div', { class: 'bk-scroll' }, [
    el('table', { class: 'bk-grid' }, [
      el('thead', {}, [el('tr', {}, [el('th', {}), ...players.map((one) => el('th', { scope: 'col', text: one.name }))])]),
      el('tbody', {}, players.map((row, i) => el('tr', { 'data-mine': row.id === t.mine ? 'true' : undefined }, [
        el('th', { scope: 'row', text: row.name }),
        ...cells[i].map((cell) => {
          if (!cell) return el('td', { class: 'bk-cell-self' });
          const set = sets.find((one) => one.key === cell.key);
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
  ]));
}

function bracketBody(t) {
  if (!t.sets.length) return [sayNothing(WORDS.bracketEmpty)];
  if (ELIMINATION.includes(t.format)) return [treeNode(t)];
  if (t.format === 'round_robin') return [gridNode(t)];
  return [roundsNode(t)];
}

/* ---------- pools ---------- */

function raiseTied(pool, id) {
  const order = tieOrder(pool, view.ties[pool.pool]);
  const at = order.indexOf(id);
  if (at > 0) view.ties[pool.pool] = moved(order, at, at - 1);
  update('pools', null, view.holders.pools, () => poolsBody(view.t), { force: true });
}

function poolTableNode(t, pool) {
  const runs = t.may_run && mode() !== 'off' && t.phase === 'pools';
  const order = pool.finished && pool.tied && pool.tied.length ? tieOrder(pool, view.ties[pool.pool]) : null;
  const { rows, line } = poolTable(pool, order);
  return el('div', { class: 'rowlist bk-pool-table' }, rows.map((row, at) => el('div', {
    class: 'rowlist-row bk-standing',
    'data-mine': row.entrant === t.mine ? 'true' : undefined,
    'data-through': row.through ? 'true' : undefined,
    'data-cut': at === line - 1 && line < rows.length ? 'true' : undefined,
    'data-tied': row.tied ? 'true' : undefined,
  }, [
    el('span', { class: 'bk-seed mono', 'data-place': 'true', text: placeWords(row.place ?? row.rank) || '—' }),
    el('span', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: row.name || '' }),
      el('span', { class: 'rowlist-note', text: [said(WORDS.gamesNote, { games: `${row.game_wins}–${row.game_losses}` }), row.tied ? w('brackets_pool_tied') : null].filter(Boolean).join(' · ') }),
    ]),
    el('span', { class: 'mono bk-record', text: `${row.set_wins}–${row.set_losses}` }),
    runs && row.tied && order.indexOf(row.entrant) > 0
      ? el('button', { class: 'bk-raise', type: 'button', title: w('brackets_pool_raise_label'), 'aria-label': `${w('brackets_pool_raise_label')}: ${row.name}`, text: '↑', on: { click: () => raiseTied(pool, row.entrant) } })
      : null,
  ])));
}

function poolNode(t, pool) {
  const draw = (t.options || {}).pools_format === 'swiss' ? roundsNode(t, pool.sets) : gridNode(t, pool.sets);
  return el('div', { class: 'bk-pool', 'data-pool': pool.letter }, [
    el('h3', { class: 'bk-pool-name', text: w('brackets_pool_title', { pool: pool.letter }) }),
    draw,
    poolTableNode(t, pool),
  ]);
}

function poolsBody(t) {
  return [el('div', { class: 'bk-pools' }, (t.pools || []).map((pool) => poolNode(t, pool)))];
}

/* ---------- standings ---------- */

function rate(row) {
  return row.opponents_rate === null || row.opponents_rate === undefined ? '—' : `${Math.round(row.opponents_rate * 100)}%`;
}

function compactStandings(t, rows) {
  const table_ = !ELIMINATION.includes(t.format);
  return el('div', { class: 'rowlist bk-standings-compact' }, rows.map((row) => {
    const more = table_ ? [
      said(WORDS.gamesNote, { games: `${row.game_wins}–${row.game_losses}` }),
      t.format === 'swiss' ? said(WORDS.opponentsNote, { rate: rate(row) }) : null,
      t.format === 'swiss' && row.byes ? said(WORDS.byesNote, { byes: row.byes }) : null,
    ].filter(Boolean) : [];
    return el('div', { class: 'rowlist-row bk-standing', 'data-mine': row.entrant === t.mine ? 'true' : undefined }, [
      el('span', { class: 'bk-seed mono', 'data-place': 'true', text: placeWords(row.place ?? row.rank) || '—' }),
      el('span', { class: 'rowlist-main' }, [
        el('span', { class: 'rowlist-name', text: row.name || '' }),
        more.length ? el('span', { class: 'rowlist-note', text: more.join(' · ') }) : null,
      ]),
      table_ ? el('span', { class: 'mono bk-record', text: `${row.set_wins}–${row.set_losses}` }) : null,
    ]);
  }));
}

function standingsBody(t) {
  const rows = sortedStandings(t.standings || []);
  if (ELIMINATION.includes(t.format)) {
    const placed = rows.filter((row) => row.place);
    return [el('div', { class: 'bk-standings-wide' }, [table([
      { label: WORDS.place, cell: (row) => placeWords(row.place), className: 'mono' },
      { label: WORDS.player, key: 'name' },
    ], placed, { search: false, empty: 'No placings yet.' })]), placed.length ? compactStandings(t, placed) : null];
  }
  const columns = [
    { label: WORDS.place, cell: (row) => placeWords(row.place ?? row.rank), className: 'mono' },
    { label: WORDS.player, key: 'name' },
    { label: WORDS.sets, cell: (row) => `${row.set_wins}–${row.set_losses}`, className: 'mono' },
    { label: WORDS.games, cell: (row) => `${row.game_wins}–${row.game_losses}`, className: 'mono' },
  ];
  if (t.format === 'swiss') {
    columns.push({ label: WORDS.opponents, cell: rate, className: 'mono' });
    columns.push({ label: WORDS.byes, key: 'byes', className: 'mono' });
  }
  return [el('div', { class: 'bk-standings-wide' }, [table(columns, rows, { search: false, empty: 'No results yet.' })]), rows.length ? compactStandings(t, rows) : null];
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

function closesIn(iso) {
  const left = new Date(iso).getTime() - Date.now();
  if (!Number.isFinite(left)) return '';
  const minutes = Math.max(0, Math.round(left / 60000));
  if (minutes < 60) return `in ${minutes} min`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `in ${hours} h` : `${dayLabel(iso, view.zone)} · ${clockTime(iso, view.zone)}`;
}

function voteLine(set) {
  const counts = { a: set.a_name || '', b: set.b_name || '', votes_a: set.votes_a ?? 0, votes_b: set.votes_b ?? 0 };
  if (set.vote_open) {
    const closes = set.vote_closes_at ? closesIn(set.vote_closes_at) : '';
    if (set.votes_a === null || set.votes_a === undefined) return w('brackets_vote_hidden_line', { count: set.vote_count ?? 0, closes });
    return w('brackets_vote_open_line', { ...counts, closes });
  }
  if (set.state === 'reported') return w('brackets_vote_tied_line', counts);
  if (set.state === 'complete' && set.vote_closes_at) return w('brackets_vote_closed_line', counts);
  return null;
}

function voteButton(t, set, side, go) {
  const name = side === 'a' ? set.a_name : set.b_name;
  const count = side === 'a' ? set.votes_a : set.votes_b;
  const mine = set.my_vote === side;
  const other = set.my_vote && !mine;
  return el('button', {
    class: 'bk-vote',
    type: 'button',
    'aria-pressed': mine ? 'true' : 'false',
    title: other ? w('brackets_vote_button_change') : undefined,
    on: { click: () => go('vote', { slot: side }) },
  }, [
    el('span', { class: 'bk-vote-name', text: name || '' }),
    count === null || count === undefined ? null : el('span', { class: 'bk-vote-count mono', text: String(count) }),
  ]);
}

function listDrawer(t, set) {
  const moves = setMoves(t, set, { mode: mode() });
  const say = notice();
  const path = `${base(t.id)}/sets/${encodeURIComponent(set.key)}`;
  const go = async (tail, body = {}) => {
    const done = await act(`${path}/${tail}`, body, 'POST', say);
    if (!done.ok) return;
    if (tail === 'vote') {
      say.say(done.found.message, 'ok');
      const fresh = allSets(view.t).find((one) => one.key === set.key);
      if (fresh && fresh.vote_open) {
        listDrawer(view.t, fresh);
        return;
      }
    }
    closeDrawer();
    view.say.say(done.found.message, 'ok');
  };
  const body = [el('div', { class: 'bk-drawer-set' }, [setCard(t, set)]), el('p', { class: 'bk-meta', text: roundWords(set) })];
  const line = voteLine(set);
  if (line) body.push(el('p', { class: 'bk-state' }, boldParts(line)));
  const link = discordLink(t, set);
  if (link) body.push(link);
  if (moves.includes('vote')) body.push(el('div', { class: 'bk-votes', role: 'group', 'aria-label': `${set.a_name} – ${set.b_name}` }, [voteButton(t, set, 'a', go), voteButton(t, set, 'b', go)]));
  const organiser = [];
  const reason = el('input', { class: 'input', type: 'text', maxlength: '300', id: 'bk-set-reason' });
  if (moves.includes('close_vote')) organiser.push(button(w('brackets_close_vote_label'), () => go('close-vote'), { tone: 'warn' }));
  if (moves.includes('pick')) {
    for (const side of ['a', 'b']) {
      const name = side === 'a' ? set.a_name : set.b_name;
      if (name) organiser.push(button(said(WORDS.wins, { name }), () => go('override', { winner: side, reason: reason.value.trim() }), { tone: 'quiet' }));
    }
  }
  if (moves.includes('reset')) organiser.push(button(WORDS.resetSet, () => go('reset', { reason: reason.value.trim() }), { tone: 'danger' }));
  if (organiser.length) {
    body.push(el('div', { class: 'bk-organiser' }, [el('p', { class: 'bk-label', text: WORDS.organiser }), bar(organiser)]));
  }
  body.push(say);
  openDrawer(`${set.key} · ${roundWords(set)}`, body);
}

function scoreBox(id, value, label) {
  return el('input', { class: 'input bk-scorebox', type: 'number', id, min: '0', max: '999', value: value ?? '', 'aria-label': label });
}

function slotSelect(t, id, value) {
  const select = el('select', { class: 'input', id });
  select.append(el('option', { value: '', text: WORDS.empty, selected: value === null || value === undefined || undefined }));
  for (const one of (t.entrants || []).filter((row) => !row.dropped && !row.dq)) {
    select.append(el('option', { value: String(one.id), text: one.name, selected: one.id === value || undefined }));
  }
  return select;
}

function editSetForm(t, set, go) {
  const when = el('input', { class: 'input', type: 'datetime-local', id: 'bk-set-when', value: localValue(set.scheduled_at) || undefined });
  const status = segment(LIVE_STATUSES.map((one) => ({ value: one, label: WORDS.statuses[one] })), set.live_status || 'scheduled');
  const a = scoreBox('bk-set-a', set.score_a, said(WORDS.scoreOf, { name: set.a_name || 'a' }));
  const b = scoreBox('bk-set-b', set.score_b, said(WORDS.scoreOf, { name: set.b_name || 'b' }));
  const slots = set.state !== 'complete' ? { a: slotSelect(t, 'bk-slot-a', set.slot_a), b: slotSelect(t, 'bk-slot-b', set.slot_b) } : null;
  const reason = el('input', { class: 'input', type: 'text', maxlength: '300', id: 'bk-edit-reason' });
  const number = (box) => (box.value.trim() === '' ? null : Number(box.value));
  const save = () => {
    const body = { reason: reason.value.trim() };
    const at = when.value ? new Date(when.value).toISOString() : null;
    if (at !== (set.scheduled_at ? new Date(set.scheduled_at).toISOString() : null)) body.scheduled_at = at;
    if (status.readValue() !== (set.live_status || 'scheduled')) body.live_status = status.readValue();
    if (number(a) !== (set.score_a ?? null) || number(b) !== (set.score_b ?? null)) Object.assign(body, { score_a: number(a), score_b: number(b) });
    if (slots) {
      for (const side of ['a', 'b']) {
        const wanted = slots[side].value === '' ? null : Number(slots[side].value);
        if (wanted !== (set[`slot_${side}`] ?? null)) body[`slot_${side}`] = wanted;
      }
    }
    return go('', body, 'PATCH');
  };
  return el('div', { class: 'bk-fields bk-edit-set' }, [
    el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.when, when), field(WORDS.status, status)]),
    el('div', { class: 'bk-fields bk-fields-row' }, [field(said(WORDS.scoreOf, { name: set.a_name || said(WORDS.slotOf, { slot: 'a' }) }), a), field(said(WORDS.scoreOf, { name: set.b_name || said(WORDS.slotOf, { slot: 'b' }) }), b)]),
    slots ? el('div', { class: 'bk-fields bk-fields-row' }, [field(said(WORDS.slotOf, { slot: 'a' }), slots.a), field(said(WORDS.slotOf, { slot: 'b' }), slots.b)]) : null,
    field(WORDS.reason, reason),
    bar([button(WORDS.save, save, { tone: 'warn' })]),
  ]);
}

function sportsDrawer(t, set) {
  const moves = setMoves(t, set, { mode: mode() });
  const say = notice();
  const path = `${base(t.id)}/sets/${encodeURIComponent(set.key)}`;
  const go = async (tail, body = {}, method = 'POST') => {
    const done = await act(tail ? `${path}/${tail}` : path, body, method, say);
    if (done.ok) {
      closeDrawer();
      view.say.say(done.found.message, 'ok');
    }
  };
  const line = sportsLine(set);
  const body = [
    el('div', { class: 'bk-drawer-set' }, [setCard(t, set)]),
    el('p', { class: 'bk-meta', text: [roundWords(set), set.best_of > 1 ? w('brackets_set_card_best_of', { best_of: set.best_of }) : null, line].filter(Boolean).join(' · ') }),
  ];
  const decided = set.decided_by ? w(`brackets_decided_by_${set.decided_by}_words`) : '';
  const notes = [decided, set.held ? w('brackets_held_note') : null].filter(Boolean);
  if (notes.length) body.push(el('p', { class: 'bk-state', text: notes.join(' · ') }));
  const link = discordLink(t, set);
  if (link) body.push(link);
  const organiser = [];
  const a = scoreBox('bk-pick-a', null, said(WORDS.scoreOf, { name: set.a_name || 'a' }));
  const b = scoreBox('bk-pick-b', null, said(WORDS.scoreOf, { name: set.b_name || 'b' }));
  const reason = el('input', { class: 'input', type: 'text', maxlength: '300', id: 'bk-set-reason' });
  const number = (box) => (box.value.trim() === '' ? null : Number(box.value));
  if (moves.includes('pick')) {
    for (const side of ['a', 'b']) {
      const name = side === 'a' ? set.a_name : set.b_name;
      if (name) organiser.push(button(said(WORDS.wins, { name }), () => go('override', { winner: side, score_a: number(a), score_b: number(b), reason: reason.value.trim() }), { tone: 'quiet' }));
    }
  }
  if (moves.includes('reset')) organiser.push(button(WORDS.resetSet, () => go('reset', { reason: reason.value.trim() }), { tone: 'danger' }));
  if (moves.includes('release')) organiser.push(button(w('brackets_release_hold_label'), () => go('release'), { tone: 'warn' }));
  if (organiser.length) {
    body.push(el('div', { class: 'bk-organiser' }, [
      el('p', { class: 'bk-label', text: WORDS.organiser }),
      moves.includes('pick') ? el('div', { class: 'bk-fields bk-fields-row' }, [field(said(WORDS.scoreOf, { name: set.a_name || 'a' }), a), field(said(WORDS.scoreOf, { name: set.b_name || 'b' }), b)]) : null,
      bar(organiser),
      moves.some((one) => ['pick', 'reset'].includes(one)) ? field(WORDS.reason, reason) : null,
    ]));
  }
  if (moves.includes('edit_set')) body.push(foldout(w('brackets_edit_set_label'), [editSetForm(t, set, go)], { open: !organiser.length }));
  body.push(say);
  openDrawer(`${set.key} · ${roundWords(set)}`, body);
}

function setDrawer(key) {
  const t = view.t;
  const set = allSets(t).find((one) => one.key === key);
  if (!set) return;
  if (isList(t)) {
    listDrawer(t, set);
    return;
  }
  if (isSports(t)) {
    sportsDrawer(t, set);
    return;
  }
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
  const o = t ? { ...t.options } : { ...((view.index && view.index.defaults) || {}) };
  const kinds = (view.index && view.index.kind_defaults) || {};
  const kind = segment(KINDS.map((one) => ({ value: one, label: kindWords(one) })), t ? t.kind || 'fighters' : kinds.kind || 'fighters', { onChange: () => shapeFor() });
  if (t) for (const one of kind.children) one.disabled = true;
  const decide = segment(DECIDERS.map((one) => ({ value: one, label: decideWords(one) })), (t && t.decide_by) || kinds.decide_by || 'votes', { onChange: () => shapeFor() });
  const voteMinutes = numberBox('bk-vote-minutes', (t && t.vote_minutes) || kinds.vote_minutes || 1440, { max: 20160 });
  const league = segment(LEAGUES.map((one) => ({ value: one, label: leagueWord(one) })), (t && t.league) || 'ncaam');
  const season = el('input', { class: 'input', type: 'text', id: 'bk-season', maxlength: '20', value: (t && t.season) || undefined, placeholder: '2025-26' });
  const fedNow = !t || t.source !== 'own';
  const source = segment([{ value: 'feed', label: WORDS.feed }, { value: 'own', label: w('brackets_source_own_words') }], fedNow ? 'feed' : 'own');
  const name = el('input', { class: 'input', type: 'text', id: 'bk-name', maxlength: '100', value: t ? t.name : undefined });
  const game = el('input', { class: 'input', type: 'text', id: 'bk-game', maxlength: '100', value: t ? t.game || undefined : undefined });
  const format = el('select', { class: 'input', id: 'bk-format' });
  for (const one of FORMATS) format.append(el('option', { value: one, text: formatWords(one), selected: o.format === one || undefined }));
  const startsAt = el('input', { class: 'input', type: 'datetime-local', id: 'bk-starts', value: t ? localValue(t.starts_at) || undefined : undefined });
  const third = el('input', { type: 'checkbox', id: 'bk-third', checked: Boolean(o.third_place) || undefined });
  const reset = el('input', { type: 'checkbox', id: 'bk-reset', checked: Boolean(o.grand_final_reset) || undefined });
  const rounds = numberBox('bk-rounds', o.swiss_rounds, { max: 20, blank: WORDS.roundsAuto });
  const bestOf = lengthSelect('bk-bo', o.best_of);
  const late = lengthSelect('bk-late', o.best_of_late);
  const lateFrom = numberBox('bk-late-from', o.best_of_from_round, { min: 2, blank: '—' });
  const finals = lengthSelect('bk-finals', o.best_of_finals);
  const cap = numberBox('bk-cap', o.entrant_cap, { min: 2, blank: '—' });
  const checkIn = numberBox('bk-checkin', o.check_in_minutes, { min: 5, max: 1440 });
  const rules = el('textarea', { class: 'input', id: 'bk-rules', rows: '4', maxlength: '2000', text: t ? t.rules_text || '' : '' });
  const poolsFormat = el('select', { class: 'input', id: 'bk-pools' });
  for (const one of POOL_FORMATS) poolsFormat.append(el('option', { value: one, text: one === 'none' ? WORDS.noPools : formatWords(one), selected: (o.pools_format || 'none') === one || undefined }));
  const poolCount = numberBox('bk-pool-count', o.pool_count, { max: 16 });
  const advancePer = numberBox('bk-advance', o.advance_per_pool, { max: 16 });
  const losersFrom = numberBox('bk-losers-from', o.advance_losers_from, { min: 2, max: 16, blank: '—' });
  const poolsBestOf = lengthSelect('bk-pools-bo', o.pools_best_of ?? 3);
  const poolRounds = numberBox('bk-pool-rounds', o.pools_swiss_rounds, { max: 20, blank: WORDS.roundsAuto });
  const say = notice();
  const tick = (box, label) => el('label', { class: 'bk-tick' }, [box, el('span', { text: label })]);
  const only = {
    single: el('div', { class: 'bk-fields' }, [tick(third, WORDS.third)]),
    double: el('div', { class: 'bk-fields' }, [tick(reset, WORDS.reset)]),
    swiss: el('div', { class: 'bk-fields' }, [field(WORDS.rounds, rounds)]),
    elimination: el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.lateFrom, lateFrom), field(WORDS.late, late), field(WORDS.finals, finals)]),
    pools: el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.poolsFormat, poolsFormat)]),
    pooled: el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.poolCountLabel, poolCount), field(WORDS.advancePer, advancePer), field(WORDS.poolsBestOf, poolsBestOf)]),
    losers: el('div', { class: 'bk-fields' }, [field(WORDS.losersFrom, losersFrom)]),
    poolRounds: el('div', { class: 'bk-fields' }, [field(WORDS.poolRounds, poolRounds)]),
  };
  only.listed = el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.decideBy, decide), field(WORDS.voteMinutes, voteMinutes)]);
  only.fighting = el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.bestOf, bestOf), field(WORDS.cap, cap), field(WORDS.checkIn, checkIn)]);
  only.game = field(WORDS.game, game);
  only.sports = el('div', { class: 'bk-fields' }, [
    field(WORDS.league, league),
    el('div', { class: 'bk-fields bk-fields-row' }, [field(WORDS.season, season), field(WORDS.results, source)]),
  ]);
  only.format = field(WORDS.format, format);
  const shapeFor = () => {
    const listed = kind.readValue() === 'list';
    const sports = kind.readValue() === 'sports';
    const plain = listed || sports;
    only.sports.hidden = !sports;
    only.format.hidden = sports;
    only.listed.hidden = !listed;
    only.listed.lastChild.hidden = decide.readValue() !== 'votes';
    only.fighting.hidden = plain;
    only.game.hidden = plain;
    const pooled = !plain && ELIMINATION.includes(format.value) && poolsFormat.value !== 'none';
    only.pools.hidden = plain || !ELIMINATION.includes(format.value);
    only.pooled.hidden = !pooled;
    only.losers.hidden = !pooled || format.value !== 'double';
    only.poolRounds.hidden = !pooled || poolsFormat.value !== 'swiss';
    only.single.hidden = sports || format.value !== 'single';
    only.double.hidden = sports || format.value !== 'double';
    only.swiss.hidden = sports || format.value !== 'swiss';
    only.elimination.hidden = plain || !ELIMINATION.includes(format.value);
  };
  format.addEventListener('change', shapeFor);
  poolsFormat.addEventListener('change', shapeFor);
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
      rules_text: rules.value.trim(),
      starts_at: startsAt.value ? new Date(startsAt.value).toISOString() : null,
    };
    if (number(checkIn) !== null) body.check_in_minutes = number(checkIn);
    if (format.value === 'single') body.third_place = third.checked;
    if (format.value === 'double') body.grand_final_reset = reset.checked;
    if (format.value === 'swiss') body.swiss_rounds = number(rounds);
    if (ELIMINATION.includes(format.value)) {
      body.best_of_late = Number(late.value);
      body.best_of_finals = Number(finals.value);
      body.best_of_from_round = number(lateFrom);
      body.pools_format = poolsFormat.value;
      if (poolsFormat.value !== 'none') {
        if (number(poolCount) !== null) body.pool_count = number(poolCount);
        if (number(advancePer) !== null) body.advance_per_pool = number(advancePer);
        body.pools_best_of = Number(poolsBestOf.value);
        if (format.value === 'double') body.advance_losers_from = number(losersFrom);
        if (poolsFormat.value === 'swiss') body.pools_swiss_rounds = number(poolRounds);
      }
    } else {
      body.pools_format = 'none';
    }
    if (kind.readValue() === 'list') {
      for (const field of ['game', 'best_of', 'entrant_cap', 'check_in_minutes', 'best_of_late', 'best_of_finals', 'best_of_from_round', 'pools_format', 'pool_count', 'advance_per_pool', 'pools_best_of', 'advance_losers_from', 'pools_swiss_rounds']) delete body[field];
      body.decide_by = decide.readValue();
      if (number(voteMinutes) !== null) body.vote_minutes = number(voteMinutes);
    }
    if (kind.readValue() === 'sports') {
      for (const field of ['game', 'format', 'best_of', 'entrant_cap', 'check_in_minutes', 'best_of_late', 'best_of_finals', 'best_of_from_round', 'pools_format', 'pool_count', 'advance_per_pool', 'pools_best_of', 'advance_losers_from', 'pools_swiss_rounds', 'third_place', 'grand_final_reset', 'swiss_rounds']) delete body[field];
      Object.assign(body, { league: league.readValue(), season: season.value.trim(), source: source.readValue() });
    }
    if (!t) body.kind = kind.readValue();
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
    field(WORDS.kind, kind),
    field(WORDS.name, name),
    only.game,
    only.sports,
    el('div', { class: 'bk-fields bk-fields-row' }, [only.format, field(WORDS.starts, startsAt)]),
    only.listed,
    only.single,
    only.double,
    only.swiss,
    only.fighting,
    only.elimination,
    only.pools,
    only.pooled,
    only.losers,
    only.poolRounds,
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

function namesListWords(row) {
  if (row.kind === 'school') return WORDS.schools;
  return said(row.kind === 'player' ? WORDS.namesPlayers : WORDS.namesTeams, { league: leagueWord(row.league) });
}

function namesTable(found) {
  return table([
    { key: 'list', label: WORDS.namesList, cell: (row) => namesListWords(row) },
    { key: 'rows', label: WORDS.namesCount, className: 'mono' },
    { key: 'updated_at', label: WORDS.namesUpdated, cell: (row) => (row.updated_at ? ago(row.updated_at).text : null) },
    { key: 'why', label: WORDS.namesFailure, cell: (row) => (row.why ? `${row.why} · ${ago(row.failed_at).text}` : null) },
  ], found.lists || [], { search: false });
}

async function sportsNode() {
  const one = section(WORDS.sportsNames, null, { id: 'sports-names' });
  const say = notice();
  const holder = el('div');
  const shown = (found) => {
    one.count((found.lists || []).reduce((total, row) => total + (row.rows || 0), 0));
    holder.replaceChildren(namesTable(found));
  };
  const refreshIt = async () => {
    const done = await run(say, () => send('/api/sports/refresh', 'POST', {}), (found) => found.message);
    if (done.ok) shown(done.found);
  };
  one.body.append(bar([button(WORDS.refreshNames, refreshIt, { tone: 'warn' })]), say, holder);
  try {
    shown(await api('/api/sports'));
  } catch (error) {
    const found = sentenceFor(error);
    say.say(found.text, found.tone);
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
  const shape = sig([t.id, t.state, t.sets.length > 0, t.format, t.phase || null]);
  if (shape !== view.shape) {
    refresh();
    return;
  }
  update('head', sig([t, mode()]), view.holders.head, () => headBody(t));
  paintEntrants();
  if (view.holders.pools) update('pools', sig([t.pools, t.mine, t.may_run, t.state, t.phase, mode(), view.ties]), view.holders.pools, () => poolsBody(t));
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
  view.shape = sig([t.id, t.state, t.sets.length > 0, t.format, t.phase || null]);
  view.ties = {};
  view.parts = new Map();
  view.say = notice();
  view.say.setAttribute('data-span', 'full');
  view.status = el('p', { class: 'bk-status', role: 'status' });
  view.holders = { head: el('div', { class: 'card-body bk-head' }) };
  view.sections = {};
  const started = allSets(t).length > 0;
  const blocks = [el('div', { class: 'card bk-headcard', 'data-span': 'full' }, [view.holders.head, el('div', { class: 'bk-statusrow' }, [view.status])]), view.say];
  if (t.pools && t.pools.length) {
    const one = section(WORDS.pools, null, { id: 'pools', open: t.phase === 'pools' });
    one.node.setAttribute('data-span', 'full');
    one.count(t.pools.length);
    view.holders.pools = one.body;
    blocks.push(one.node);
  } else {
    view.holders.pools = null;
  }
  if (t.sets.length > 0) {
    const one = section(t.pools && t.pools.length ? WORDS.final : WORDS.bracket, null, { id: 'bracket', open: true });
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
  if (staff()) blocks.push(await logsNode(null), await sportsNode(), await settingsNode());
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

function resized() {
  const t = view.t;
  if (!t || !view.holders.bracket || !ELIMINATION.includes(t.format) || !t.sets.length) return;
  if (sig(treeSize(eliminationLayout(t.sets).cols, treeRoom())) === view.treeSize) return;
  update('bracket', view.parts.get('bracket'), view.holders.bracket, () => bracketBody(t), { force: true });
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
  resized();
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
    let settling = null;
    window.addEventListener('resize', () => {
      clearTimeout(settling);
      settling = setTimeout(resized, 150);
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
