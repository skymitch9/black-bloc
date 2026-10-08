// The Brackets page's drawing maths (site/public/assets/bracket-layout.js) and the mock's engine
// stand-in (site/mock/brackets.mjs) it is drawn from.
//   node site/mock/brackets.test.mjs
// Exits 0 when every fixture matched, 1 with a list of what did not.

import {
  eliminationLayout,
  memberMoves,
  moved,
  organiserMoves,
  placeWords,
  resultsGrid,
  scoreChoices,
  setMoves,
  sortedStandings,
  treeRows,
} from '../public/assets/bracket-layout.js';
import { build, decide, playOut, settle, standardOrder, standings, tableRows } from './brackets.mjs';

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

if (failures.length) {
  console.error('brackets: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log('brackets: ok - layout for single and double elimination at 4, 8 and 16, the reset, byes, round robin, Swiss, standings, scores, seeding and the moves');
