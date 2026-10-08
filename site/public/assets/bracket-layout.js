export const OPEN = ['ready', 'called', 'reported', 'disputed'];
export const LIVE = ['signups', 'check_in', 'seeding', 'running'];
export const BEFORE_START = ['draft', 'signups', 'check_in', 'seeding'];
export const ELIMINATION = ['single', 'double'];

/** `{name}` placeholders filled from `fields`; an unknown one stays as typed. */
export function fill(template, fields = {}) {
  return String(template ?? '').replace(/\{(\w+)\}/g, (all, name) => (name in fields && fields[name] !== null && fields[name] !== undefined ? String(fields[name]) : all));
}

/** Every score that finishes a best-of, slot a's wins first: Bo3 is 2–0, 2–1, 1–2, 0–2. */
export function scoreChoices(bestOf) {
  const length = Number(bestOf);
  if (!Number.isInteger(length) || length < 1 || length % 2 === 0) return [];
  const wins = Math.floor(length / 2) + 1;
  const found = [];
  for (let other = 0; other < wins; other += 1) found.push([wins, other]);
  for (let other = wins - 1; other >= 0; other -= 1) found.push([other, wins]);
  return found;
}

/** Centre of each set per round, in rows: a round half the size sits between its feeders. */
export function treeRows(counts) {
  const found = [];
  counts.forEach((count, at) => {
    if (at === 0) {
      found.push(Array.from({ length: count }, (_, p) => p + 0.5));
      return;
    }
    const before = found[at - 1];
    if (count === before.length) found.push(before.slice());
    else if (count * 2 === before.length) found.push(Array.from({ length: count }, (_, p) => (before[2 * p] + before[2 * p + 1]) / 2));
    else {
      const span = found[0].length;
      found.push(Array.from({ length: count }, (_, p) => (p + 0.5) * (span / Math.max(count, 1))));
    }
  });
  return found;
}

function bySide(sets, side) {
  const rounds = new Map();
  for (const one of sets) {
    if (one.side !== side) continue;
    if (!rounds.has(one.round)) rounds.set(one.round, []);
    rounds.get(one.round).push(one);
  }
  return [...rounds.keys()].sort((a, b) => a - b).map((round) => ({
    round,
    sets: rounds.get(round).sort((a, b) => a.position - b.position),
  }));
}

function placeSide(nodes, rounds, side, top, col0 = 0) {
  const rows = treeRows(rounds.map((one) => one.sets.length));
  rounds.forEach((one, at) => {
    one.sets.forEach((set, p) => nodes.push({ key: set.key, side, round: one.round, col: col0 + at, y: top + rows[at][p] }));
  });
  return rows.length ? rows[0].length : 0;
}

/**
 * Where every set of an elimination bracket is drawn: `col` is the column, `y` the centre in
 * rows. Winners on top, losers under them, the grand final after the longest side, the
 * third-place set under the final. A grand-final reset that is void is not drawn.
 */
export function eliminationLayout(sets) {
  const nodes = [];
  const shown = sets.filter((one) => !(one.side === 'grand' && one.round > 1 && one.state === 'void'));
  const winners = bySide(shown, 'winners');
  const losers = bySide(shown, 'losers');
  const grand = bySide(shown, 'grand');
  const third = bySide(shown, 'third');
  const high = placeSide(nodes, winners, 'winners', 0);
  const losersTop = losers.length ? high + 0.75 : high;
  const low = placeSide(nodes, losers, 'losers', losersTop);
  let height = losers.length ? losersTop + low : high;
  const last = nodes.filter((one) => one.side === 'winners' && one.col === winners.length - 1)[0];
  const finalY = last ? last.y : 0.5;
  const grandCol = Math.max(winners.length, losers.length);
  grand.forEach((one, at) => {
    one.sets.forEach((set) => nodes.push({ key: set.key, side: 'grand', round: one.round, col: grandCol + at, y: finalY }));
  });
  if (third.length) {
    const col = Math.max(winners.length - 1, 0);
    third[0].sets.forEach((set, p) => nodes.push({ key: set.key, side: 'third', round: third[0].round, col, y: height + 0.75 + p }));
    height += 0.75 + third[0].sets.length;
  }
  const cols = nodes.reduce((most, one) => Math.max(most, one.col + 1), 0);
  const keys = new Set(nodes.map((one) => one.key));
  const links = shown
    .filter((one) => one.winner_to && keys.has(one.key) && keys.has(one.winner_to))
    .map((one) => ({ from: one.key, to: one.winner_to }));
  return { nodes, links, cols, height: Math.max(height, 1), losersTop: losers.length ? losersTop : null };
}

/** Round robin and Swiss: one column per round, sets stacked in play order. */
export function roundsLayout(sets) {
  const rounds = new Map();
  for (const one of sets) {
    if (!rounds.has(one.round)) rounds.set(one.round, []);
    rounds.get(one.round).push(one);
  }
  return [...rounds.keys()].sort((a, b) => a - b).map((round) => ({
    round,
    sets: rounds.get(round).sort((a, b) => a.position - b.position),
  }));
}

/** The round robin results table: one row per player, each cell that pair's set from the row's side. */
export function resultsGrid(entrants, sets) {
  const playing = new Set();
  for (const one of sets) {
    if (one.slot_a !== null && one.slot_a !== undefined) playing.add(one.slot_a);
    if (one.slot_b !== null && one.slot_b !== undefined) playing.add(one.slot_b);
  }
  const players = entrants
    .filter((one) => playing.has(one.id))
    .sort((a, b) => (a.seed ?? 1e9) - (b.seed ?? 1e9) || a.id - b.id);
  const cells = players.map((row) => players.map((col) => {
    if (row.id === col.id) return null;
    const set = sets.find((one) => (one.slot_a === row.id && one.slot_b === col.id) || (one.slot_a === col.id && one.slot_b === row.id));
    if (!set) return null;
    const mineA = set.slot_a === row.id;
    const own = mineA ? set.score_a : set.score_b;
    const theirs = mineA ? set.score_b : set.score_a;
    const won = set.state === 'complete' && set.winner !== null && set.winner !== undefined ? set.winner === row.id : null;
    return { key: set.key, state: set.state, own, theirs, won, forfeit: Boolean(set.forfeit) };
  }));
  return { players, cells };
}

const ORDINAL = { one: 'st', two: 'nd', few: 'rd', other: 'th' };
const RULES = new Intl.PluralRules('en-US', { type: 'ordinal' });

export function placeWords(place) {
  if (place === null || place === undefined || place === '') return '';
  const found = Number(place);
  return Number.isFinite(found) ? `${found}${ORDINAL[RULES.select(found)]}` : '';
}

/** Placed first, by place (ties keep the order the bot sent), then the table's rank, then unplaced. */
export function sortedStandings(rows) {
  const at = (row) => (row.place ?? row.rank ?? Number.POSITIVE_INFINITY);
  return rows
    .map((row, index) => ({ row, index }))
    .sort((a, b) => at(a.row) - at(b.row) || a.index - b.index)
    .map((one) => one.row);
}

function entrantOf(t, id) {
  return (t.entrants || []).find((one) => one.id === id) || null;
}

export function myEntrant(t) {
  return t.mine === null || t.mine === undefined ? null : entrantOf(t, t.mine);
}

function isIn(person) {
  return Boolean(person) && !person.dropped && !person.dq;
}

/** The member moves the viewer can press now, as the panel offers them. */
export function memberMoves(t, mode) {
  if (mode === 'off') return [];
  const me = myEntrant(t);
  const found = [];
  const cap = t.options ? t.options.entrant_cap : null;
  const full = cap !== null && cap !== undefined && Number(t.entrant_count) >= Number(cap);
  if (t.state === 'signups' && !isIn(me) && !(me && me.dropped_why === 'removed') && !full) found.push('join');
  if (t.state === 'check_in' && isIn(me) && !me.checked_in) found.push('check_in');
  if (BEFORE_START.includes(t.state) && isIn(me)) found.push('leave');
  if (t.state === 'running' && isIn(me) && (t.sets || []).some((one) => one.slot_a === me.id || one.slot_b === me.id)) found.push('drop_out');
  return found;
}

/** The organiser moves on the tournament legal in its state, as the panel offers them. */
export function organiserMoves(t, { mode = 'shadow', staff = false } = {}) {
  if (!t.may_run || mode === 'off') return [];
  const ready = (t.sets || []).some((one) => one.state === 'ready');
  const byState = {
    draft: ['open_signups', 'edit', 'cancel'],
    signups: ['close_signups', 'open_check_in', 'edit', 'cancel'],
    check_in: ['close_check_in', 'edit', 'cancel'],
    seeding: ['open_signups', 'open_check_in', 'start', 'edit', 'cancel'],
    running: [ready ? 'call_ready' : null, t.finished ? 'complete' : null, 'unstart', 'cancel'],
    complete: ['reopen', 'cancel'],
    cancelled: ['restore'],
  };
  const found = (byState[t.state] || []).filter(Boolean);
  if (staff && t.shadow && mode === 'on' && t.state !== 'cancelled') found.push('move');
  return found;
}

/** What the viewer may do on one set: a player's moves and, for an organiser, the deciding ones. */
export function setMoves(t, set, { mode = 'shadow' } = {}) {
  if (mode === 'off' || t.state !== 'running') return [];
  const me = t.mine;
  const side = me !== null && me !== undefined ? (set.slot_a === me ? 'a' : set.slot_b === me ? 'b' : null) : null;
  const found = [];
  if (side && ['ready', 'called'].includes(set.state)) found.push('report');
  if (side && set.state === 'reported') {
    if (set.reported_side === side) found.push('report');
    else found.push('confirm', 'dispute');
  }
  if (t.may_run) {
    if (set.state === 'ready') found.push('call');
    if (['reported', 'disputed'].includes(set.state) && !side) found.push('accept');
    if (OPEN.includes(set.state) || set.state === 'complete') found.push('decide', 'forfeit');
    if (['called', 'reported', 'disputed', 'complete'].includes(set.state)) found.push('reset');
  }
  return found;
}

/** The order a seeding drag leaves behind: the item at `from` moved to `to`. */
export function moved(order, from, to) {
  const next = order.slice();
  if (from < 0 || from >= next.length) return next;
  const [one] = next.splice(from, 1);
  next.splice(Math.max(0, Math.min(to, next.length)), 0, one);
  return next;
}
