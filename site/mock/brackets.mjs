// The mock's stand-in for black_bloc/brackets/ (docs/info/brackets-design.md §A): enough of the
// engine for the Brackets page to be played locally — builds, byes, drops, the reset set,
// round robin, Swiss pairing, resets and standings. The bot's engine is the truth; where the
// two differ, this file changes.

export const OPEN = ['ready', 'called', 'reported', 'disputed'];
export const DONE = ['complete', 'bye', 'void'];
const LETTER = { winners: 'W', losers: 'L', grand: 'G', third: 'T', rr: 'R', swiss: 'S' };

export function standardOrder(size) {
  let order = [1];
  while (order.length < size) {
    const width = order.length * 2;
    order = order.flatMap((seed) => [seed, width + 1 - seed]);
  }
  return order;
}

export function bracketSize(count) {
  let size = 2;
  while (size < count) size *= 2;
  return size;
}

export function blankSet(key, side, round, position, extra = {}) {
  return {
    key, side, round, position, best_of: 3, state: 'waiting', slot_a: null, slot_b: null,
    score_a: null, score_b: null, winner: null, loser: null, forfeit: null, winner_to: null,
    loser_to: null, called_at: null, reported_by: null, reported_side: null, reported_at: null,
    confirms_at: null, confirmed_by: null, confirmed_how: null, disputed_by: null,
    dispute_note: null, placement_winner: null, placement_loser: null, rematch: false,
    message_id: null, card_at: null, _feed: {}, _place: {}, ...extra,
  };
}

function keyOf(side, round, position) {
  return `${LETTER[side]}${round}-${position}`;
}

function link(sets, fromKey, take, toKey, slot) {
  const from = sets.get(fromKey);
  if (take === 'winner') from.winner_to = toKey;
  else from.loser_to = toKey;
  sets.get(toKey)._feed[slot] = { from: fromKey, take };
}

function seedFirstRound(sets, ids, size) {
  const order = standardOrder(size);
  for (let p = 1; p <= size / 2; p += 1) {
    const one = sets.get(keyOf('winners', 1, p));
    one._feed.a = { seed: ids[order[2 * p - 2] - 1] ?? null };
    one._feed.b = { seed: ids[order[2 * p - 1] - 1] ?? null };
  }
}

function winnersSide(sets, size) {
  const rounds = Math.log2(size);
  for (let r = 1; r <= rounds; r += 1) {
    for (let p = 1; p <= size / 2 ** r; p += 1) sets.set(keyOf('winners', r, p), blankSet(keyOf('winners', r, p), 'winners', r, p));
  }
  for (let r = 1; r < rounds; r += 1) {
    for (let p = 1; p <= size / 2 ** r; p += 1) {
      link(sets, keyOf('winners', r, p), 'winner', keyOf('winners', r + 1, Math.ceil(p / 2)), p % 2 ? 'a' : 'b');
    }
  }
  return rounds;
}

export function buildSingle(ids, options = {}) {
  const size = bracketSize(ids.length);
  const sets = new Map();
  const rounds = winnersSide(sets, size);
  seedFirstRound(sets, ids, size);
  for (let r = 1; r <= rounds; r += 1) {
    for (let p = 1; p <= size / 2 ** r; p += 1) sets.get(keyOf('winners', r, p))._place.loser = size / 2 ** r + 1;
  }
  const last = sets.get(keyOf('winners', rounds, 1));
  last._place = { winner: 1, loser: 2 };
  if (options.third_place && rounds >= 2) {
    sets.set('T1-1', blankSet('T1-1', 'third', 1, 1, { _place: { winner: 3, loser: 4 } }));
    link(sets, keyOf('winners', rounds - 1, 1), 'loser', 'T1-1', 'a');
    link(sets, keyOf('winners', rounds - 1, 2), 'loser', 'T1-1', 'b');
    for (let p = 1; p <= 2; p += 1) sets.get(keyOf('winners', rounds - 1, p))._place.loser = null;
  }
  return pace([...sets.values()], options, rounds);
}

function losersCount(size, round) {
  return size / 2 ** (Math.ceil(round / 2) + 1);
}

function flipped(position) {
  return position % 2 ? position + 1 : position - 1;
}

export function buildDouble(ids, options = {}) {
  const size = bracketSize(ids.length);
  const sets = new Map();
  const rounds = winnersSide(sets, size);
  seedFirstRound(sets, ids, size);
  const losers = 2 * rounds - 2;
  for (let l = 1; l <= losers; l += 1) {
    for (let p = 1; p <= losersCount(size, l); p += 1) sets.set(keyOf('losers', l, p), blankSet(keyOf('losers', l, p), 'losers', l, p));
  }
  sets.set('G1-1', blankSet('G1-1', 'grand', 1, 1, { _place: { winner: 1, loser: 2 } }));
  if (options.grand_final_reset !== false) {
    sets.set('G2-1', blankSet('G2-1', 'grand', 2, 1, { reset_of: 'G1-1', _place: { winner: 1, loser: 2 } }));
  }
  link(sets, keyOf('winners', rounds, 1), 'winner', 'G1-1', 'a');
  if (losers === 0) {
    link(sets, 'W1-1', 'loser', 'G1-1', 'b');
  } else {
    for (let p = 1; p <= size / 2; p += 1) link(sets, keyOf('winners', 1, p), 'loser', keyOf('losers', 1, Math.ceil(p / 2)), p % 2 ? 'a' : 'b');
    for (let r = 2; r <= rounds; r += 1) {
      const into = 2 * r - 2;
      for (let p = 1; p <= size / 2 ** r; p += 1) {
        const at = losersCount(size, into) === 1 ? 1 : flipped(p);
        link(sets, keyOf('winners', r, p), 'loser', keyOf('losers', into, at), 'b');
      }
    }
    for (let l = 1; l <= losers; l += 1) {
      const later = Array.from({ length: losers - l }, (_, at) => losersCount(size, l + at + 1)).reduce((a, b) => a + b, 0);
      for (let p = 1; p <= losersCount(size, l); p += 1) {
        const one = keyOf('losers', l, p);
        sets.get(one)._place.loser = 3 + later;
        if (l === losers) link(sets, one, 'winner', 'G1-1', 'b');
        else if ((l + 1) % 2 === 0) link(sets, one, 'winner', keyOf('losers', l + 1, p), 'a');
        else link(sets, one, 'winner', keyOf('losers', l + 1, Math.ceil(p / 2)), p % 2 ? 'a' : 'b');
      }
    }
  }
  return pace([...sets.values()], options, rounds);
}

function pace(sets, options, rounds) {
  const grand = sets.some((one) => one.side === 'grand');
  for (const one of sets) {
    const final = grand ? one.side === 'grand' : one.side === 'winners' && one.round === rounds;
    one.best_of = Number(final ? options.best_of_finals ?? 5 : options.best_of ?? 3);
  }
  return sets;
}

export function buildRoundRobin(ids, options = {}) {
  const players = ids.slice();
  if (players.length % 2) players.push(null);
  const width = players.length;
  const sets = [];
  let ring = players.slice();
  for (let r = 1; r < width; r += 1) {
    let position = 0;
    for (let at = 0; at < width / 2; at += 1) {
      const a = ring[at];
      const b = ring[width - 1 - at];
      if (a === null || b === null) continue;
      position += 1;
      sets.push(blankSet(keyOf('rr', r, position), 'rr', r, position, { _feed: { a: { seed: a }, b: { seed: b } }, best_of: Number(options.best_of ?? 3) }));
    }
    ring = [ring[0], ring[width - 1], ...ring.slice(1, width - 1)];
  }
  return sets;
}

export function swissRounds(count, options = {}) {
  return Number(options.swiss_rounds) || Math.max(1, Math.ceil(Math.log2(Math.max(count, 2))));
}

function swissRound(round, order, met, byes, options) {
  const sets = [];
  const left = order.slice();
  let bye = null;
  if (left.length % 2) {
    const at = [...left].reverse().find((id) => !byes.has(id));
    bye = at ?? left[left.length - 1];
    left.splice(left.indexOf(bye), 1);
  }
  const pairs = [];
  if (round === 1) {
    const half = left.length / 2;
    for (let at = 0; at < half; at += 1) pairs.push([left[at], left[at + half]]);
  } else {
    const pool = left.slice();
    while (pool.length) {
      const a = pool.shift();
      let at = pool.findIndex((b) => !met.has(`${Math.min(a, b)}:${Math.max(a, b)}`));
      if (at < 0) at = 0;
      pairs.push([a, pool.splice(at, 1)[0]]);
    }
  }
  pairs.forEach(([a, b], at) => {
    const rematch = met.has(`${Math.min(a, b)}:${Math.max(a, b)}`);
    sets.push(blankSet(keyOf('swiss', round, at + 1), 'swiss', round, at + 1, { _feed: { a: { seed: a }, b: { seed: b } }, best_of: Number(options.best_of ?? 3), rematch }));
  });
  if (bye !== null) sets.push(blankSet(keyOf('swiss', round, pairs.length + 1), 'swiss', round, pairs.length + 1, { _feed: { a: { seed: bye }, b: { seed: null } }, best_of: Number(options.best_of ?? 3) }));
  return sets;
}

export function buildSwiss(ids, options = {}) {
  return swissRound(1, ids, new Set(), new Set(), options);
}

export function build(format, ids, options = {}) {
  if (format === 'single') return buildSingle(ids, options);
  if (format === 'round_robin') return buildRoundRobin(ids, options);
  if (format === 'swiss') return buildSwiss(ids, options);
  return buildDouble(ids, options);
}

function byKey(t) {
  return new Map(t.sets.map((one) => [one.key, one]));
}

function withdrawn(t, id) {
  const one = t.entrants.find((person) => person.id === id);
  return Boolean(one && (one.dq || (one.dropped && one.dropped_why === 'dropped')));
}

function slotOf(sets, one, slot) {
  const feed = one._feed && one._feed[slot];
  if (!feed) return { known: true, id: one[`slot_${slot}`] };
  if ('seed' in feed) return { known: true, id: feed.seed };
  const from = sets.get(feed.from);
  if (!from || !DONE.includes(from.state)) return { known: false, id: null };
  return { known: true, id: feed.take === 'winner' ? from.winner : from.loser };
}

export function decide(one, side, { score_a = null, score_b = null, how = 'to', forfeit = null, by = null, at = null } = {}) {
  const winner = side === 'a' ? one.slot_a : one.slot_b;
  const loser = side === 'a' ? one.slot_b : one.slot_a;
  Object.assign(one, {
    state: 'complete', score_a, score_b, winner, loser, forfeit, confirmed_how: how,
    confirmed_by: by, confirmed_at: at, placement_winner: one._place.winner ?? null,
    placement_loser: one._place.loser ?? null,
  });
  if (one.side === 'grand' && one.round === 1 && one.reset_of === undefined) {
    one.placement_winner = null;
    one.placement_loser = null;
  }
}

export function settle(t) {
  const sets = byKey(t);
  let changed = true;
  while (changed) {
    changed = false;
    for (const one of t.sets) {
      if (one.state !== 'waiting') continue;
      if (one.reset_of) {
        const first = sets.get(one.reset_of);
        if (first.state !== 'complete') continue;
        if (first.winner === first.slot_b && !first.forfeit) Object.assign(one, { slot_a: first.slot_a, slot_b: first.slot_b, state: 'ready' });
        else one.state = 'void';
        changed = true;
        continue;
      }
      const a = slotOf(sets, one, 'a');
      const b = slotOf(sets, one, 'b');
      if (a.known) one.slot_a = a.id;
      if (b.known) one.slot_b = b.id;
      if (!a.known || !b.known) continue;
      changed = true;
      if (a.id !== null && b.id !== null) {
        one.state = 'ready';
        const outA = withdrawn(t, a.id);
        const outB = withdrawn(t, b.id);
        if (outA || outB) decide(one, outA ? 'b' : 'a', { forfeit: 'dq' });
      } else if (a.id !== null || b.id !== null) {
        Object.assign(one, { state: 'bye', winner: a.id ?? b.id, loser: null });
      } else {
        one.state = 'void';
      }
    }
    if (t.format === 'swiss') changed = nextSwissRound(t) || changed;
  }
  const grand = sets.get('G1-1');
  if (grand && grand.state === 'complete') {
    const reset = sets.get('G2-1');
    const decides = !reset || reset.state === 'void';
    grand.placement_winner = decides ? 1 : null;
    grand.placement_loser = decides ? 2 : null;
  }
  return t;
}

function points(t) {
  const found = new Map();
  for (const one of t.sets) {
    if (one.state === 'bye') found.set(one.winner, (found.get(one.winner) || 0) + 1);
    if (one.state === 'complete' && one.winner !== null) found.set(one.winner, (found.get(one.winner) || 0) + 1);
  }
  return found;
}

function nextSwissRound(t) {
  const last = t.sets.reduce((most, one) => Math.max(most, one.round), 0);
  if (!last || last >= swissRounds(t.entrants.filter((one) => one.seed && !one.dropped).length, t.options)) return false;
  if (t.sets.some((one) => one.round === last && !DONE.includes(one.state))) return false;
  const seeds = new Map(t.entrants.map((one) => [one.id, one.seed ?? 1e9]));
  const players = [...new Set(t.sets.flatMap((one) => [one.slot_a, one.slot_b]).filter((id) => id !== null))]
    .filter((id) => !withdrawn(t, id));
  const scored = points(t);
  const order = players.sort((a, b) => (scored.get(b) || 0) - (scored.get(a) || 0) || seeds.get(a) - seeds.get(b));
  const met = new Set(t.sets.filter((one) => one.slot_a !== null && one.slot_b !== null).map((one) => `${Math.min(one.slot_a, one.slot_b)}:${Math.max(one.slot_a, one.slot_b)}`));
  const byes = new Set(t.sets.filter((one) => one.state === 'bye').map((one) => one.winner));
  t.sets.push(...swissRound(last + 1, order, met, byes, t.options));
  return true;
}

function clearResult(one) {
  Object.assign(one, {
    score_a: null, score_b: null, winner: null, loser: null, forfeit: null, called_at: null,
    reported_by: null, reported_side: null, reported_at: null, confirms_at: null,
    confirmed_by: null, confirmed_how: null, confirmed_at: null, disputed_by: null,
    dispute_note: null, placement_winner: null, placement_loser: null,
  });
}

function emptied(t, key) {
  const sets = byKey(t);
  const one = sets.get(key);
  if (!one) return;
  const after = [one.winner_to, one.loser_to, ...t.sets.filter((other) => other.reset_of === key).map((other) => other.key)].filter(Boolean);
  for (const next of after) {
    const target = sets.get(next);
    if (!target) continue;
    if (target.state === 'complete') emptied(t, next);
    clearResult(target);
    if (target._feed && (target._feed.a || target._feed.b)) {
      if (target._feed.a && target._feed.a.from === key) target.slot_a = null;
      if (target._feed.b && target._feed.b.from === key) target.slot_b = null;
    }
    if (target.reset_of === key) {
      target.slot_a = null;
      target.slot_b = null;
    }
    target.state = 'waiting';
  }
}

export function reset(t, key) {
  const one = byKey(t).get(key);
  if (one.state === 'complete') {
    if (t.format === 'swiss') t.sets = t.sets.filter((other) => other.round <= one.round);
    else emptied(t, key);
  }
  clearResult(one);
  one.state = 'ready';
  return settle(t);
}

export function withdraw(t, id, forfeit) {
  for (const one of t.sets) {
    if ([one.slot_a, one.slot_b].includes(id) && OPEN.includes(one.state)) decide(one, one.slot_a === id ? 'b' : 'a', { forfeit });
  }
  return settle(t);
}

export function finished(t) {
  return t.sets.length > 0 && t.sets.every((one) => DONE.includes(one.state));
}

export function tableRows(t) {
  const seeds = new Map(t.entrants.map((one) => [one.id, one.seed ?? 1e9]));
  const names = new Map(t.entrants.map((one) => [one.id, one.name]));
  const rows = new Map();
  const row = (id) => {
    if (!rows.has(id)) rows.set(id, { entrant: id, name: names.get(id) ?? null, set_wins: 0, set_losses: 0, game_wins: 0, game_losses: 0, byes: 0, opponents: [] });
    return rows.get(id);
  };
  for (const one of t.sets) {
    if (one.slot_a !== null) row(one.slot_a);
    if (one.slot_b !== null) row(one.slot_b);
    if (one.state === 'bye') {
      row(one.winner).byes += 1;
      row(one.winner).set_wins += t.format === 'swiss' ? 1 : 0;
      continue;
    }
    if (one.state !== 'complete') continue;
    const win = row(one.winner);
    const lose = row(one.loser);
    win.set_wins += 1;
    lose.set_losses += 1;
    win.opponents.push(one.loser);
    lose.opponents.push(one.winner);
    const [w, l] = one.winner === one.slot_a ? [one.score_a, one.score_b] : [one.score_b, one.score_a];
    win.game_wins += w || 0;
    win.game_losses += l || 0;
    lose.game_wins += l || 0;
    lose.game_losses += w || 0;
  }
  const rate = (id) => {
    const found = rows.get(id);
    const played = found.set_wins + found.set_losses - (t.format === 'swiss' ? found.byes : 0);
    return played > 0 ? (found.set_wins - (t.format === 'swiss' ? found.byes : 0)) / played : 0;
  };
  const list = [...rows.values()].map((one) => ({
    ...one,
    opponents_rate: t.format === 'swiss' && one.opponents.length ? Math.round((one.opponents.reduce((sum, id) => sum + rate(id), 0) / one.opponents.length) * 1000) / 1000 : null,
  }));
  const tie = (one) => [one.set_wins, t.format === 'swiss' ? one.opponents_rate : one.game_wins];
  list.sort((a, b) => b.set_wins - a.set_wins || (tie(b)[1] ?? 0) - (tie(a)[1] ?? 0) || seeds.get(a.entrant) - seeds.get(b.entrant));
  const done = finished(t);
  list.forEach((one, at) => {
    const before = list[at - 1];
    one.rank = before && JSON.stringify(tie(before)) === JSON.stringify(tie(one)) ? before.rank : at + 1;
    one.place = done ? one.rank : null;
    delete one.opponents;
  });
  return list;
}

export function standings(t) {
  if (!t.sets.length) return [];
  if (!['single', 'double'].includes(t.format)) return tableRows(t);
  const placed = new Map();
  for (const one of t.sets) {
    if (one.state !== 'complete') continue;
    if (one.placement_winner) placed.set(one.winner, one.placement_winner);
    if (one.placement_loser) placed.set(one.loser, one.placement_loser);
  }
  const names = new Map(t.entrants.map((one) => [one.id, one.name]));
  const players = [...new Set(t.sets.flatMap((one) => [one.slot_a, one.slot_b]).filter((id) => id !== null && id !== undefined))];
  return players
    .map((id) => ({ entrant: id, name: names.get(id) ?? null, place: placed.get(id) ?? null }))
    .sort((a, b) => (a.place ?? 1e6) - (b.place ?? 1e6));
}

export function waitingOn(t) {
  if (!t.sets.length) return [];
  const names = new Map(t.entrants.map((one) => [one.id, one.name]));
  const players = [...new Set(t.sets.flatMap((one) => [one.slot_a, one.slot_b]).filter((id) => id !== null && id !== undefined))];
  const ordered = t.sets.slice().sort((a, b) => a.round - b.round || a.position - b.position);
  const placed = new Set(standings(t).filter((one) => one.place).map((one) => one.entrant));
  return players.map((id) => {
    const base = { entrant: id, name: names.get(id) ?? null, set: null, opponent: null, open: 0 };
    if (withdrawn(t, id)) return { ...base, what: 'out' };
    const mine = ordered.filter((one) => one.slot_a === id || one.slot_b === id);
    const live = mine.filter((one) => OPEN.includes(one.state));
    if (live.length) {
      const one = live[0];
      const side = one.slot_a === id ? 'a' : 'b';
      const what = { ready: 'play', called: 'called', disputed: 'to_decides' }[one.state] || (one.reported_side === side ? 'opponent_confirms' : 'confirm');
      return { ...base, what, set: one.key, opponent: side === 'a' ? one.slot_b : one.slot_a, open: live.length };
    }
    const waiting = t.sets.find((one) => one.state === 'waiting' && (one.slot_a === id || one.slot_b === id));
    if (waiting) return { ...base, what: 'waits', set: waiting.key };
    if (placed.has(id) || finished(t)) return { ...base, what: 'done' };
    return { ...base, what: 'next_round' };
  });
}

export function placements(t) {
  const found = new Map(standings(t).map((one) => [one.entrant, one.place]));
  for (const one of t.entrants) one.placement = found.get(one.id) ?? null;
}

/** A finished bracket played with slot a always winning, for seeding the mock's tournaments. */
export function playOut(t, { until = () => false, scores = () => null } = {}) {
  settle(t);
  for (let guard = 0; guard < 500; guard += 1) {
    const one = t.sets
      .filter((set) => set.state === 'ready')
      .sort((a, b) => a.round - b.round || ['winners', 'losers', 'third', 'grand', 'rr', 'swiss'].indexOf(a.side) - ['winners', 'losers', 'third', 'grand', 'rr', 'swiss'].indexOf(b.side) || a.position - b.position)[0];
    if (!one || until(one)) return t;
    const wins = Math.floor(one.best_of / 2) + 1;
    const [a, b] = scores(one) || [wins, Math.min(1, wins - 1)];
    decide(one, a > b ? 'a' : 'b', { score_a: a, score_b: b, how: 'opponent' });
    settle(t);
  }
  return t;
}

// Pools into a bracket (brackets-design.md, "Pools into a bracket 2026-10-07"): each pool is a
// part of its own — a round robin or Swiss over its members, its keys carrying the pool letter —
// and the final is the tournament's own sets, built by advance().
export const POOL_FORMATS = ['round_robin', 'swiss'];
const PLAYED = ['reported', 'disputed', 'complete'];

export function letter(pool) {
  return String.fromCharCode(64 + pool);
}

export function snake(ids, count) {
  const found = Array.from({ length: count }, () => []);
  ids.forEach((id, at) => {
    const row = Math.floor(at / count);
    const column = at % count;
    found[row % 2 ? count - 1 - column : column].push(id);
  });
  return found;
}

export function tagPool(part, pool) {
  for (const one of part.sets) {
    if (!String(one.key).includes('.')) one.key = `${letter(pool)}.${one.key}`;
    one.phase = 'pools';
    one.pool = pool;
  }
  return part;
}

export function buildPools(t, ids) {
  const o = t.options;
  const format = o.pools_format;
  const options = { best_of: Number(o.pools_best_of ?? 3), swiss_rounds: o.pools_swiss_rounds ?? null };
  t.pools = snake(ids, Number(o.pool_count)).map((members, at) => {
    const part = {
      id: t.id, format, options,
      entrants: t.entrants.filter((one) => members.includes(one.id)).sort((a, b) => a.seed - b.seed),
      sets: build(format, members, options),
    };
    settle(part);
    return tagPool(part, at + 1);
  });
  t.sets = [];
  return t;
}

export function ownerOf(t, set) {
  return set && set.pool ? t.pools[set.pool - 1] : t;
}

export function allSets(t) {
  return [...(t.pools || []).flatMap((part) => part.sets), ...t.sets];
}

export function poolsFinished(t) {
  return Boolean(t.pools && t.pools.length && t.pools.every((part) => finished(part)));
}

function outOf(t, id) {
  const one = t.entrants.find((person) => person.id === id);
  return Boolean(one && (one.dq || one.dropped));
}

export function cut(t, part) {
  const advance = Number(t.options.advance_per_pool);
  const rows = tableRows(part).filter((one) => !outOf(t, one.entrant));
  const ranks = new Map(t.entrants.map((one) => [one.id, one.final_rank]));
  if (rows.length > advance && rows[advance - 1].rank === rows[advance].rank) {
    const tied = rows.filter((one) => one.rank === rows[advance].rank).map((one) => one.entrant);
    if (!tied.every((id) => ranks.get(id))) return { going: [], tied };
    const head = rows.filter((one) => one.rank < rows[advance].rank).map((one) => one.entrant);
    tied.sort((a, b) => ranks.get(a) - ranks.get(b));
    return { going: [...head, ...tied].slice(0, advance), tied: [] };
  }
  return { going: rows.slice(0, advance).map((one) => one.entrant), tied: [] };
}

function seated(order, size) {
  const spots = standardOrder(size).map((seed) => order[seed - 1] ?? null);
  return Array.from({ length: size / 2 }, (_, at) => [spots[2 * at], spots[2 * at + 1]]);
}

function clashes(order, size, home) {
  return seated(order, size).filter(([a, b]) => a !== null && b !== null && home.get(a) === home.get(b)).length;
}

export function apart(order, size, home, tier) {
  let found = order.slice();
  for (let now = clashes(found, size, home); now; now = clashes(found, size, home)) {
    const pair = seated(found, size).find(([a, b]) => a !== null && b !== null && home.get(a) === home.get(b));
    const lower = found.indexOf(pair[0]) > found.indexOf(pair[1]) ? pair[0] : pair[1];
    const at = found.indexOf(lower);
    const others = found.filter((one) => tier.get(one) === tier.get(lower) && !pair.includes(one))
      .sort((a, b) => Math.abs(found.indexOf(a) - at) - Math.abs(found.indexOf(b) - at));
    const better = others.map((other) => {
      const trial = found.slice();
      trial[at] = other;
      trial[found.indexOf(other)] = lower;
      return trial;
    }).find((trial) => clashes(trial, size, home) < now);
    if (!better) return found;
    found = better;
  }
  return found;
}

function entered(winners, losers, options) {
  const size = Math.max(bracketSize(winners.length), bracketSize(losers.length));
  const sets = buildDouble(Array.from({ length: 2 * size }, (_, at) => -1 - at), options)
    .filter((one) => !(one.side === 'winners' && one.round === 1));
  for (const [side, round, people] of [['winners', 2, winners], ['losers', 1, losers]]) {
    seated(people, size).forEach(([a, b], at) => {
      const one = sets.find((set) => set.side === side && set.round === round && set.position === at + 1);
      one._feed = { a: { seed: a }, b: { seed: b } };
    });
  }
  return sets;
}

export function advance(t) {
  const going = t.pools.map((part) => cut(t, part));
  const tiedAt = going.findIndex((one) => one.tied.length);
  if (tiedAt >= 0) return { tied: going[tiedAt].tied, pool: letter(tiedAt + 1) };
  const advanceN = Number(t.options.advance_per_pool);
  const from = t.format === 'double' ? Number(t.options.advance_losers_from) || null : null;
  const winners = [];
  const losers = [];
  const home = new Map();
  const tier = new Map();
  for (let place = 1; place <= advanceN; place += 1) {
    going.forEach((one, pool) => {
      const id = one.going[place - 1];
      if (id === undefined) return;
      home.set(id, pool);
      tier.set(id, place);
      (from && place >= from ? losers : winners).push(id);
    });
  }
  if (!winners.length) winners.push(...losers.splice(0));
  if (losers.length) {
    const size = Math.max(bracketSize(winners.length), bracketSize(losers.length));
    t.sets = entered(apart(winners, size, home, tier), apart(losers, size, home, tier), t.options);
  } else {
    t.sets = build(t.format, apart(winners, bracketSize(winners.length), home, tier), t.options);
  }
  for (const one of t.sets) one.phase = 'final';
  settle(t);
  return { tied: [], entrants: [...winners, ...losers] };
}

function forfeitedOut(t, one) {
  return ['dq', 'drop'].includes(one.forfeit) && outOf(t, one.loser);
}

export function finalPlayed(t) {
  return t.sets.filter((one) => PLAYED.includes(one.state) && !forfeitedOut(t, one)).map((one) => one.key);
}

export function poolTableRows(t, part) {
  const ranks = new Map(t.entrants.map((one) => [one.id, one.final_rank]));
  const rows = tableRows(part).map((one) => ({ ...one, withdrawn: outOf(t, one.entrant) }));
  const found = [];
  for (let at = 0; at < rows.length;) {
    const group = rows.filter((one) => one.rank === rows[at].rank);
    if (group.length > 1 && group.every((one) => ranks.get(one.entrant))) {
      group.sort((a, b) => ranks.get(a.entrant) - ranks.get(b.entrant));
      group.forEach((one, offset) => found.push({ ...one, rank: one.rank + offset, place: one.place === null ? null : one.place + offset }));
    } else found.push(...group);
    at += group.length;
  }
  return found;
}

export function inFinal(t) {
  const found = new Set();
  for (const one of t.sets) {
    for (const id of [one.slot_a, one.slot_b]) if (id !== null && id !== undefined && id > 0) found.add(id);
    for (const feed of Object.values(one._feed || {})) {
      if (feed && 'seed' in feed && feed.seed !== null && feed.seed > 0) found.add(feed.seed);
    }
  }
  return found;
}

export function poolPlacements(t) {
  const placed = new Map(standings(t).map((one) => [one.entrant, one.place]));
  const through = inFinal(t);
  const ranks = new Map();
  for (const part of t.pools) for (const one of tableRows(part)) ranks.set(one.entrant, one.rank);
  const rest = t.entrants.filter((one) => ranks.has(one.id) && !through.has(one.id));
  const group = (one) => [outOf(t, one.id) ? 1 : 0, ranks.get(one.id)];
  const before = (a, b) => group(a)[0] - group(b)[0] || group(a)[1] - group(b)[1];
  for (const one of rest) placed.set(one.id, through.size + 1 + rest.filter((other) => before(other, one) < 0).length);
  return placed;
}

export function poolWaiting(t) {
  if (!t.sets.length) {
    return t.pools.flatMap((part) => {
      const done = finished(part);
      return waitingOn(part).map((one) => (done && one.what === 'done' ? { ...one, what: 'final' } : one));
    });
  }
  const through = inFinal(t);
  const finalRows = new Map(waitingOn(t).map((one) => [one.entrant, one]));
  const names = new Map(t.entrants.map((one) => [one.id, one.name]));
  return t.pools.flatMap((part) => part.entrants.map((person) => (through.has(person.id) && finalRows.get(person.id)) || {
    entrant: person.id, name: names.get(person.id) ?? null, what: outOf(t, person.id) ? 'out' : 'done',
    set: null, opponent: null, open: 0,
  }));
}
