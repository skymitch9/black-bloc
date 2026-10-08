// The Brackets page's drawing maths (site/public/assets/bracket-layout.js) and the mock's engine
// stand-in (site/mock/brackets.mjs) it is drawn from.
//   node site/mock/brackets.test.mjs
// Exits 0 when every fixture matched, 1 with a list of what did not.

import {
  TREE,
  allSets,
  drawnInTree,
  finalUntouched,
  poolTable,
  reorderedRows,
  tieOrder,
  eliminationLayout,
  memberMoves,
  moved,
  organiserMoves,
  placeWords,
  resultsGrid,
  scoreChoices,
  seedOrderWith,
  setMoves,
  sortedStandings,
  treeRows,
  treeSize,
  unplayedSets,
} from '../public/assets/bracket-layout.js';
import { advance, build, buildPools, decide, playOut, poolPlacements, poolTableRows, settle, snake, standardOrder, standings, tableRows } from './brackets.mjs';

const failures = [];
const is = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

const ids = (count) => Array.from({ length: count }, (_, at) => at + 1);
const tournament = (format, count, options = {}) => ({
  format,
  options: { best_of: 3, best_of_finals: 5, ...options },
  entrants: ids(count).map((id) => ({ id, name: `P${id}`, seed: id, dropped: false, dq: false })),
  sets: build(format, ids(count), options),
});
const where = (layout, key) => {
  const found = layout.nodes.find((one) => one.key === key);
  return found ? [found.col, found.y] : null;
};
const column = (layout, side, col) => layout.nodes.filter((one) => one.side === side && one.col === col).map((one) => one.y);

is('the standard order pairs 1v8, 4v5, 2v7, 3v6', standardOrder(8), [1, 8, 4, 5, 2, 7, 3, 6]);
is('rows halve between feeders', treeRows([4, 2, 1]), [[0.5, 1.5, 2.5, 3.5], [1, 3], [2]]);
is('a drop round keeps its rows', treeRows([2, 2, 1, 1]), [[0.5, 1.5], [0.5, 1.5], [1], [1]]);

for (const [count, rounds] of [[4, [[0.5, 1.5], [1]]], [8, [[0.5, 1.5, 2.5, 3.5], [1, 3], [2]]], [16, [[0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5], [1, 3, 5, 7], [2, 6], [4]]]]) {
  const t = tournament('single', count);
  const drawn = eliminationLayout(settle(t).sets);
  is(`single elimination of ${count}: every round's rows`, rounds.map((_, col) => column(drawn, 'winners', col)), rounds);
  is(`single elimination of ${count}: one line per set into the next round`, drawn.links.length, count - 2);
  is(`single elimination of ${count}: height`, drawn.height, count / 2);
}

const third = eliminationLayout(settle(tournament('single', 8, { third_place: true })).sets);
is('the third-place set sits under the final', where(third, 'T1-1'), [2, 4.75]);

for (const [count, winners, losers, grandCol] of [
  [4, [[0.5, 1.5], [1]], [[3.25], [3.25]], 2],
  [8, [[0.5, 1.5, 2.5, 3.5], [1, 3], [2]], [[5.25, 6.25], [5.25, 6.25], [5.75], [5.75]], 4],
  [16, [[0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5], [1, 3, 5, 7], [2, 6], [4]], [[9.25, 10.25, 11.25, 12.25], [9.25, 10.25, 11.25, 12.25], [9.75, 11.75], [9.75, 11.75], [10.75], [10.75]], 6],
]) {
  const t = settle(tournament('double', count));
  const drawn = eliminationLayout(t.sets);
  is(`double elimination of ${count}: winners rows`, winners.map((_, col) => column(drawn, 'winners', col)), winners);
  is(`double elimination of ${count}: losers rows under the winners`, losers.map((_, col) => column(drawn, 'losers', col)), losers);
  is(`double elimination of ${count}: the grand final after the longer side, level with the winners final`, where(drawn, 'G1-1'), [grandCol, winners[winners.length - 1][0]]);
  is(`double elimination of ${count}: the reset is drawn while it may be played`, where(drawn, 'G2-1'), [grandCol + 1, winners[winners.length - 1][0]]);
}

const eight = tournament('double', 8);
is('double elimination of 8: W2-1 and W2-2 drop across (the pair flip)', ['W2-1', 'W2-2'].map((key) => eight.sets.find((one) => one.key === key).loser_to), ['L2-2', 'L2-1']);
playOut(eight);
is('double elimination of 8 with the higher seed winning: places', standings(eight).map((one) => one.place), [1, 2, 3, 4, 5, 5, 7, 7]);
is('the reset set is void when the winners side won', eight.sets.find((one) => one.key === 'G2-1').state, 'void');
is('a played-out bracket draws no void reset', eliminationLayout(eight.sets).nodes.some((one) => one.key === 'G2-1'), false);

const resetting = settle(tournament('double', 4));
playOut(resetting, { until: (one) => one.key === 'G1-1' });
decide(resetting.sets.find((one) => one.key === 'G1-1'), 'b', { score_a: 1, score_b: 3 });
settle(resetting);
is('the losers side winning the grand final opens the reset', resetting.sets.find((one) => one.key === 'G2-1').state, 'ready');

const byes = settle(tournament('single', 5));
is('five entrants: three byes to the top seeds', byes.sets.filter((one) => one.state === 'bye').map((one) => one.winner), [1, 2, 3]);

const probe = (label, sets) => {
  const drawn = eliminationLayout(sets);
  const keys = new Set(drawn.nodes.map((one) => one.key));
  const byKey = new Map(sets.map((one) => [one.key, one]));
  is(`${label}: no bye or void set is drawn`, drawn.nodes.filter((one) => !drawnInTree(byKey.get(one.key))).map((one) => one.key), []);
  const unplayed = unplayedSets(sets);
  is(`${label}: every set that will be played is drawn`, sets.filter((one) => !unplayed.has(one.key) && !keys.has(one.key)).map((one) => one.key), []);
  is(`${label}: a waiting set left out is one that can only ever hold one player or none`, sets.filter((one) => unplayed.has(one.key) && one.state === 'waiting' && [one.slot_a, one.slot_b].filter((id) => id !== null).length > 1).map((one) => one.key), []);
  is(`${label}: no empty column`, Array.from({ length: drawn.cols }, (_, col) => drawn.nodes.some((one) => one.col === col)).every(Boolean), true);
  const spots = drawn.nodes.map((one) => `${one.col}:${one.y}`);
  is(`${label}: no two sets on one spot`, new Set(spots).size, spots.length);
  is(`${label}: lines join drawn sets only`, drawn.links.every((one) => keys.has(one.from) && keys.has(one.to)), true);
  is(`${label}: the top set sits on the first row`, Math.min(...drawn.nodes.filter((one) => one.side === 'winners').map((one) => one.y)), 0.5);
};
for (const format of ['single', 'double']) {
  for (const count of [5, 6, 7, 12]) {
    const t = settle(tournament(format, count));
    probe(`${format} elimination of ${count} at the start`, t.sets);
    playOut(t, { until: (one) => one.side === 'winners' && one.round === 3 });
    probe(`${format} elimination of ${count} part played`, t.sets);
    playOut(t);
    probe(`${format} elimination of ${count} played out`, t.sets);
  }
}
const five = settle(tournament('single', 5));
is('five entrants: a bye is not a card, its player is already in round two', [eliminationLayout(five.sets).nodes.some((one) => one.key === 'W1-1'), five.sets.find((one) => one.key === 'W2-1').slot_a], [false, 1]);
const fiveDouble = settle(tournament('double', 5));
is('double elimination of 5: L1-2 is void, L1-1 can only ever be a bye; neither is drawn and L1 gives up its column', [fiveDouble.sets.find((one) => one.key === 'L1-2').state, fiveDouble.sets.find((one) => one.key === 'L1-1').state, eliminationLayout(fiveDouble.sets).nodes.filter((one) => one.side === 'losers').map((one) => [one.key, one.col])[0]], ['void', 'waiting', ['L2-1', 0]]);
playOut(fiveDouble);
is('double elimination of 5 played out: L1-1 turned out a bye, as the drawing said', fiveDouble.sets.find((one) => one.key === 'L1-1').state, 'bye');
const predicted = (format, count) => {
  const t = settle(tournament(format, count));
  const said = unplayedSets(t.sets);
  playOut(t);
  return t.sets.filter((one) => said.has(one.key) !== !drawnInTree(one) && one.side !== 'grand').map((one) => one.key);
};
for (const format of ['single', 'double']) {
  for (const count of [3, 5, 6, 7, 9, 12, 13]) is(`${format} elimination of ${count}: what the start leaves out is exactly what turns out a bye or void`, predicted(format, count), []);
}

const rr = settle(tournament('round_robin', 3));
is('round robin of 3: three sets over three rounds', rr.sets.map((one) => one.key), ['R1-1', 'R2-1', 'R3-1']);
const r1 = rr.sets.find((one) => one.slot_a === 1 && one.slot_b === 2) || rr.sets.find((one) => one.slot_a === 2 && one.slot_b === 1);
decide(r1, r1.slot_a === 1 ? 'a' : 'b', r1.slot_a === 1 ? { score_a: 2, score_b: 1 } : { score_a: 1, score_b: 2 });
const grid = resultsGrid(rr.entrants, rr.sets);
is('the results grid: one row per player in seed order', grid.players.map((one) => one.id), [1, 2, 3]);
is('the results grid: the diagonal is empty', [grid.cells[0][0], grid.cells[1][1]], [null, null]);
is('the results grid: P1 beat P2 2–1, read from each row', [grid.cells[0][1].own, grid.cells[0][1].theirs, grid.cells[0][1].won, grid.cells[1][0].own, grid.cells[1][0].won], [2, 1, true, 1, false]);
is('the results grid: an unplayed pair is open', grid.cells[0][2].won, null);

const table = settle(tournament('round_robin', 4));
playOut(table, { scores: (one) => (one.slot_a < one.slot_b ? [2, 0] : [0, 2]) });
is('round robin of 4, the lower seed always winning: set wins', tableRows(table).map((one) => [one.entrant, one.set_wins, one.place]), [[1, 3, 1], [2, 2, 2], [3, 1, 3], [4, 0, 4]]);

const swiss = settle(tournament('swiss', 6));
is('Swiss of 6: round one is the top half against the bottom half', swiss.sets.map((one) => [one.slot_a, one.slot_b]), [[1, 4], [2, 5], [3, 6]]);
playOut(swiss, { until: (one) => one.round === 2 });
is('Swiss of 6: round two is paired when round one is final, without a rematch', swiss.sets.filter((one) => one.round === 2).every((one) => !one.rematch), true);

is('standings: placed by place with ties kept, unplaced last', sortedStandings([
  { name: 'e', place: null }, { name: 'c', place: 5 }, { name: 'a', place: 1 }, { name: 'd', place: 5 }, { name: 'b', place: 3 },
]).map((one) => one.name), ['a', 'b', 'c', 'd', 'e']);
is('standings: a table ranks before it places', sortedStandings([{ name: 'b', rank: 2, place: null }, { name: 'a', rank: 1, place: null }]).map((one) => one.name), ['a', 'b']);
is('places read as ordinals', [1, 2, 3, 4, 5, 11, 13, 21, 22, null].map(placeWords), ['1st', '2nd', '3rd', '4th', '5th', '11th', '13th', '21st', '22nd', '']);

is('a best of 3 offers only the scores that finish it', scoreChoices(3), [[2, 0], [2, 1], [1, 2], [0, 2]]);
is('a best of 1', scoreChoices(1), [[1, 0], [0, 1]]);
is('a best of 5', scoreChoices(5).length, 6);
is('an even best-of offers nothing', scoreChoices(4), []);

is('a seeding drag moves one entrant and keeps the rest in order', moved([1, 2, 3, 4], 3, 0), [4, 1, 2, 3]);
is('a drag past the end lands last', moved([1, 2, 3], 0, 9), [2, 3, 1]);
is('an unsaved order keeps its moves and puts a new entrant last', seedOrderWith([3, 1, 2], [1, 2, 3, 4]), [3, 1, 2, 4]);
is('an unsaved order drops whoever left', seedOrderWith([3, 1, 2], [1, 3]), [3, 1]);
is('an unsaved order with joiners and leavers names everyone in exactly once', seedOrderWith([6, 2, 5, 1], [1, 2, 3, 4, 5]).slice().sort(), [1, 2, 3, 4, 5]);

is('a tree that fits keeps full-size cards', treeSize(6, 1400), { width: TREE.width, gap: TREE.gap, fits: true });
is('eight in double elimination at 1280 (943 px of room, measured) squeezes to fit', [treeSize(6, 943).fits, treeSize(6, 943).width < TREE.width], [true, true]);
is('a phone never squeezes a card under its floor', treeSize(6, 335), { width: TREE.tight, gap: TREE.tightGap, fits: false });

const base = { state: 'signups', options: { entrant_cap: null }, entrant_count: 1, entrants: [{ id: 5, dropped: false, dq: false, checked_in: false }], sets: [], may_run: false };
is('a member who is not in sees Sign up', memberMoves({ ...base, mine: null }, 'shadow'), ['join']);
is('a full field shows no Sign up', memberMoves({ ...base, mine: null, options: { entrant_cap: 1 } }, 'shadow'), []);
is('an entrant sees Leave', memberMoves({ ...base, mine: 5 }, 'shadow'), ['leave']);
is('removed by an organiser: no Sign up', memberMoves({ ...base, mine: 5, entrants: [{ id: 5, dropped: true, dropped_why: 'removed' }] }, 'shadow'), []);
is('check-in offers Check in, then Leave', memberMoves({ ...base, state: 'check_in', mine: 5 }, 'shadow'), ['check_in', 'leave']);
is('nothing while brackets are off', memberMoves({ ...base, mine: null }, 'off'), []);

const run = { state: 'running', may_run: true, finished: false, shadow: true, sets: [{ state: 'ready' }] };
is('a running bracket: call, back to seeding, cancel', organiserMoves(run, { mode: 'shadow' }), ['call_ready', 'unstart', 'cancel']);
is('Move to #knuck-up only for staff, only while on', [organiserMoves(run, { mode: 'on', staff: true }).includes('move'), organiserMoves(run, { mode: 'on' }).includes('move'), organiserMoves(run, { mode: 'shadow', staff: true }).includes('move')], [true, false, false]);
is('a member has no organiser moves', organiserMoves({ ...run, may_run: false }), []);

const set = { slot_a: 5, slot_b: 6, state: 'reported', reported_side: 'a' };
is('the reporter may report again, the opponent confirms or disputes', [setMoves({ state: 'running', mine: 5, may_run: false }, set), setMoves({ state: 'running', mine: 6, may_run: false }, set)], [['report'], ['confirm', 'dispute']]);
is('an organiser outside the set lets it stand, decides or resets', setMoves({ state: 'running', mine: null, may_run: true }, set), ['accept', 'decide', 'forfeit', 'reset']);
is('a stranger gets nothing', setMoves({ state: 'running', mine: 9, may_run: false }, set), []);
is('nothing once the tournament is complete', setMoves({ state: 'complete', mine: 5, may_run: true }, set), []);

// Pools into a bracket: the mock's stand-in agrees with black_bloc/brackets/pools.py on the
// worked examples, and the page's helpers draw the cut and order a tie.
is('seeds are dealt in snake order', snake(ids(16), 4), [[1, 8, 9, 16], [2, 7, 10, 15], [3, 6, 11, 14], [4, 5, 12, 13]]);
const pooledT = (count, pools, options = {}) => {
  const t = { id: 1, format: options.format || 'double', options: { pools_format: 'round_robin', pool_count: pools, advance_per_pool: 2, best_of: 3, best_of_finals: 3, ...options }, entrants: ids(count).map((id) => ({ id, name: `P${id}`, seed: id, dropped: false, dq: false })), sets: [] };
  buildPools(t, ids(count));
  for (const part of t.pools) playOut(part, { scores: (one) => (one.slot_a < one.slot_b ? [2, 0] : [0, 2]) });
  return t;
};
const higher = { scores: (one) => (one.slot_a < one.slot_b ? [2, 0] : [0, 2]) };
const sixteen = pooledT(16, 4, { advance_losers_from: 2 });
advance(sixteen);
const seat = (t, key) => { const one = t.sets.find((set) => set.key === key); return [one.slot_a, one.slot_b]; };
is('16 in 4 pools: the firsts start in winners round 2', [seat(sixteen, 'W2-1'), seat(sixteen, 'W2-2')], [[1, 4], [2, 3]]);
is('16 in 4 pools: the seconds start in losers round 1', [seat(sixteen, 'L1-1'), seat(sixteen, 'L1-2')], [[8, 5], [7, 6]]);
playOut(sixteen, higher);
is('16 in 4 pools: everyone is placed', [...poolPlacements(sixteen).values()].sort((a, b) => a - b), [1, 2, 3, 4, 5, 5, 7, 7, 9, 9, 9, 9, 13, 13, 13, 13]);
const twelve = pooledT(12, 3);
advance(twelve);
is('12 in 3 pools: no pool meets itself in the first round', [seat(twelve, 'W1-2'), seat(twelve, 'W1-4')], [[6, 4], [3, 5]]);
const eightPooled = pooledT(8, 2);
advance(eightPooled);
is('8 in 2 pools into a 4-player double', [seat(eightPooled, 'W1-1'), seat(eightPooled, 'W1-2')], [[1, 3], [2, 4]]);

const cycled = { id: 2, format: 'single', options: { pools_format: 'round_robin', pool_count: 2, advance_per_pool: 1, best_of: 3 }, entrants: ids(6).map((id) => ({ id, name: `P${id}`, seed: id, dropped: false, dq: false, final_rank: null })), sets: [] };
buildPools(cycled, ids(6));
const beats = new Set(['1>4', '4>5', '5>1']);
playOut(cycled.pools[0], { scores: (one) => (beats.has(`${one.slot_a}>${one.slot_b}`) ? [2, 0] : [0, 2]) });
is('a tie in the mock table shares a rank before Advance', poolTableRows(cycled, cycled.pools[0]).map((one) => one.rank), [1, 1, 1]);
[5, 1, 4].forEach((id, at) => { cycled.entrants.find((one) => one.id === id).final_rank = at + 1; });
is('the stored order splits the tie as the engine does', poolTableRows(cycled, cycled.pools[0]).map((one) => [one.entrant, one.rank]), [[5, 1], [1, 2], [4, 3]]);
cycled.entrants.find((one) => one.id === 4).dq = true;
is('a pool row says who is out', poolTableRows(cycled, cycled.pools[0]).map((one) => one.withdrawn), [false, false, true]);

const onePool = { pool: 1, letter: 'A', cut: 2, tied: [], standings: [{ entrant: 3, rank: 2, set_wins: 2 }, { entrant: 1, rank: 1, set_wins: 3 }, { entrant: 2, rank: 3, set_wins: 1 }] };
is('a pool table is in rank order with the line under the cut', poolTable(onePool).rows.map((one) => [one.entrant, one.through]), [[1, true], [3, true], [2, false]]);
is('the line falls after the cut', poolTable(onePool).line, 2);
const tiedPool = { ...onePool, finished: true, cut: 1, tied: [1, 3], standings: [{ entrant: 1, rank: 1 }, { entrant: 3, rank: 1 }, { entrant: 2, rank: 3 }] };
is('a tie across the cut is marked', poolTable(tiedPool).rows.map((one) => one.tied), [true, true, false]);
is('the tie keeps the table order until the organiser picks one', tieOrder(tiedPool), [1, 3]);
is('a picked order that is not the tie is ignored', tieOrder(tiedPool, [3, 2]), [1, 3]);
is('the picked order moves the tied rows only', poolTable(tiedPool, [3, 1]).rows.map((one) => [one.entrant, one.through]), [[3, true], [1, false], [2, false]]);
is('a tie while the pool still plays is not marked', poolTable({ ...tiedPool, finished: false }).rows.map((one) => one.tied), [false, false, false]);
const dqLeader = { pool: 1, letter: 'A', cut: 2, finished: true, tied: [], advancing: [4, 5], standings: [{ entrant: 1, rank: 1, withdrawn: true }, { entrant: 4, rank: 2 }, { entrant: 5, rank: 3 }, { entrant: 8, rank: 4 }] };
is('a disqualified leader is not through: the advancing are', poolTable(dqLeader).rows.map((one) => [one.entrant, one.through]), [[1, false], [4, true], [5, true], [8, false]]);
is('the line falls under the last one through', poolTable(dqLeader).line, 3);
is('without advancing the cut skips the withdrawn', poolTable({ ...dqLeader, advancing: undefined }).rows.map((one) => one.through), [false, true, true, false]);
is('an empty advancing means nobody is drawn through', poolTable({ ...dqLeader, advancing: [] }).rows.map((one) => one.through), [false, false, false, false]);
is('a finished tie is drawn in the order shown', poolTable({ ...dqLeader, cut: 1, advancing: [], tied: [4, 5], standings: [{ entrant: 4, rank: 1 }, { entrant: 5, rank: 1 }, { entrant: 8, rank: 3 }] }, [5, 4]).rows.map((one) => [one.entrant, one.through]), [[5, true], [4, false], [8, false]]);
is('reordering leaves rows outside the order alone', reorderedRows([{ entrant: 1 }, { entrant: 2 }, { entrant: 3 }], [3, 1]).map((one) => one.entrant), [3, 2, 1]);
is('every set: the pools then the final', allSets({ pools: [{ sets: [{ key: 'A.R1-1' }] }, { sets: [{ key: 'B.R1-1' }] }], sets: [{ key: 'W1-1' }] }).map((one) => one.key), ['A.R1-1', 'B.R1-1', 'W1-1']);
const inPools = { state: 'pools', phase: 'pools', may_run: true, finished: false, pools_finished: false, pools: [{ sets: [{ state: 'ready' }] }], sets: [] };
is('pools: call, back to seeding, cancel', organiserMoves(inPools, { mode: 'shadow' }), ['call_ready', 'unstart', 'cancel']);
is('pools finished: advance', organiserMoves({ ...inPools, pools_finished: true, pools: [{ sets: [{ state: 'complete' }] }] }, { mode: 'shadow' }), ['advance', 'unstart', 'cancel']);
const inFinal = { state: 'running', phase: 'final', may_run: true, finished: false, pools: [{ sets: [{ state: 'complete', pool: 1 }] }], sets: [{ state: 'ready' }, { state: 'waiting' }] };
is('a final with nothing played: back to pools', organiserMoves(inFinal, { mode: 'shadow' }), ['call_ready', 'unadvance', 'unstart', 'cancel']);
is('a final with a result: no back to pools', [finalUntouched({ ...inFinal, sets: [{ state: 'reported' }] }), finalUntouched({ ...inFinal, phase: null })], [false, false]);
const dqForfeit = { ...inFinal, entrants: [{ id: 3, dq: true }, { id: 1, dq: false }], sets: [{ state: 'complete', forfeit: 'dq', winner: 1, loser: 3 }, { state: 'ready' }] };
is('a final whose only result is a DQ forfeit: back to pools', finalUntouched(dqForfeit), true);
is('a forfeit the organiser gave still counts', finalUntouched({ ...dqForfeit, sets: [{ state: 'complete', forfeit: 'to', winner: 1, loser: 3 }] }), false);
is('a forfeit of a player put back counts', finalUntouched({ ...dqForfeit, entrants: [{ id: 3, dq: false }] }), false);
is('a pool set goes quiet once the final is built', [setMoves({ ...inFinal, mine: null }, { pool: 1, state: 'complete' }), setMoves({ ...inPools, mine: null }, { pool: 1, state: 'complete', slot_a: 1, slot_b: 2 })], [[], ['decide', 'forfeit', 'reset']]);
is('a player in pools may drop out', memberMoves({ ...inPools, mine: 5, entrants: [{ id: 5, dropped: false, dq: false }], pools: [{ sets: [{ slot_a: 5, slot_b: 6, state: 'ready' }] }] }, 'shadow'), ['drop_out']);

if (failures.length) {
  console.error('brackets: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log('brackets: ok - layout for single and double elimination at 4, 8 and 16, byes and void sets at 5, 6, 7 and 12, the reset, round robin, Swiss, standings, scores, seeding, the tree size, the moves, and pools into a bracket');
