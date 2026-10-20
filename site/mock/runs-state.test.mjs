// The BaF runs page's paging, hash and demo rules (site/public/assets/runs-state.js and the paging
// helpers in listfilter.js), proved without a browser.
//   node site/mock/runs-state.test.mjs
// Exits 0 when every case matched, 1 with a list of what did not.

import { readFileSync } from 'node:fs';

import { genreFamilies, genreQualifiers, pageOf, pageWords, runsCsv, runsGames, runsMatches } from '../public/assets/listfilter.js';
import {
  DemoRefused,
  REAL_PAGE,
  demoPayload,
  filterKey,
  freshState,
  readRunsHash,
  runsHashText,
  settledPage,
  writeGuard,
} from '../public/assets/runs-state.js';

const failures = [];
const is = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

is('487 rows at 100 a page: page 1 of 5', pageOf(487, 100, 1), { page: 1, pages: 5, from: 0, to: 100, total: 487 });
is('487 rows: the last page holds 87', pageOf(487, 100, 5), { page: 5, pages: 5, from: 400, to: 487, total: 487 });
is('a page past the end is the last page', pageOf(487, 100, 9).page, 5);
is('a page below 1 is page 1', pageOf(487, 100, 0).page, 1);
is('no rows is one empty page', pageOf(0, 100, 3), { page: 1, pages: 1, from: 0, to: 0, total: 0 });
is('exactly one page of rows is one page', pageOf(100, 100, 1).pages, 1);
is('the count on a paged view', pageWords(pageOf(487, 100, 1), 500), '1–100 of 487');
is('the count on page 3', pageWords(pageOf(487, 100, 3), 500), '201–300 of 487');
is('the count on one page stays N of M', pageWords(pageOf(9, 100, 1), 9), '9 of 9');
is('the count on a filtered single page', pageWords(pageOf(40, 100, 1), 500), '40 of 500');

const linked = readRunsHash('#demo&q=celeste&view=games&gq=metroid&year=2024&runner=MossyLantern&genre=Racing&removed=1&page=3');
is('the hash reads every filter, the demo flag and the page', [linked.demo, linked.query, linked.view, linked.gamesQuery, linked.year, linked.runner, linked.genre, linked.removed, linked.page],
  [true, 'celeste', 'games', 'metroid', '2024', 'MossyLantern', 'racing', true, 3]);
is('the hash writes what it read', readRunsHash(`#${runsHashText(linked)}`), linked);
is('the demo flag leads the hash', runsHashText(freshState({ demo: true, page: 2 })), 'demo&page=2');
is('page 1 is not written', runsHashText(freshState({ page: 1, query: 'dkc2' })), 'q=dkc2');
is('a bare demo hash is demo mode on page 1', [readRunsHash('#demo').demo, readRunsHash('#demo').page], [true, 1]);
is('no demo flag is the real sheet', readRunsHash('#q=x&page=2').demo, false);
is('a junk page number is page 1', readRunsHash('#page=abc').page, 1);

const at3 = freshState({ page: 3 });
const key = filterKey(at3);
is('nothing changed keeps the page', settledPage(at3, key).page, 3);
for (const [name, change] of [
  ['search', { query: 'sonic' }], ['games search', { gamesQuery: 'zelda' }], ['year', { year: '2023' }],
  ['event', { event: 'AGDQ 2024' }], ['runner', { runner: 'x' }], ['series', { series: 'Metroid' }],
  ['genre', { genre: 'racing' }], ['developer', { developer: 'Nintendo' }], ['removed', { removed: true }],
  ['view', { view: 'games' }], ['sort', { sort: { key: 'game', dir: 1 } }],
]) {
  is(`a ${name} change resets to page 1`, settledPage({ ...at3, ...change }, key).page, 1);
}
is('the demo flag is not a filter', filterKey(freshState({ demo: true })), filterKey(freshState()));
is('the page is not a filter', filterKey(freshState({ page: 4 })), filterKey(freshState()));

const file = JSON.parse(readFileSync(new URL('../../black_bloc/runs_demo.json', import.meta.url), 'utf8'));
const families = genreFamilies('racing: racer, kart racer\nplatformer: platform, 2d platformer\nadventure: action adventure');
const rule = { qualifiers: genreQualifiers('action, 2d, 3d'), families, developers: genreFamilies('FromSoftware: fromsoft') };
const { found, grouped } = demoPayload(file, rule);
is('the demo carries every row of the file', found.rows.length, file.rows.length);
is('the demo carries the payload keys the real one does', Object.keys(found).sort(),
  ['developer_names', 'events', 'genre_families', 'genre_names', 'parts', 'rows', 'series_names', 'sources']);
const wantedFields = ['key', 'how', 'how_word', 'date', 'event', 'event_source', 'event_word', 'event_ref', 'marathon_id', 'game', 'game_key',
  'series', 'genre', 'genre_family', 'genre_families', 'developer', 'search', 'category', 'runners', 'runners_text', 'note', 'removed',
  'edited', 'tracked', 'state', 'folded', 'carried'];
is('every demo row has the fields the page reads', found.rows.filter((row) => wantedFields.some((one) => !(one in row))).length, 0);
is('demo rows are newest first', found.rows.every((row, at) => !at || String(found.rows[at - 1].date) >= String(row.date)), true);
const racing = found.rows.find((row) => /racing|racer/i.test(row.genre));
if (racing) is('a demo row is indexed by its genre family', racing.genre_families.includes('racing'), true);
const first = found.rows[0];
is('a demo row is found by its game through the shared search', runsMatches(first.game, first.search), true);
is('a demo row is found by its runner', runsMatches(first.runners[0].name, first.search), true);
is('the games view comes from the shared builder', grouped.games, runsGames(found.rows));
is('times featured adds up to the runs', grouped.games.reduce((sum, one) => sum + one.times, 0), found.rows.length);
is('the series names are the rows own', found.series_names.every((name) => found.rows.some((row) => row.series === name)), true);
is('the events are the file events', found.events.map((one) => one.name), file.events.map((one) => one.name));
const csv = runsCsv(found.rows).trimEnd().split('\n');
is('Export CSV writes one line per demo row and a header', csv.length, found.rows.length + 1);

const WRITES = [
  ['Add a run', 'send', '/api/runs', 'POST'],
  ['Save', 'send', '/api/runs/d001', 'PUT'],
  ['Clear edits', 'send', '/api/runs/d001', 'PUT'],
  ['Restore', 'send', '/api/runs/d001/restore', 'POST'],
  ['Remove', 'remove', '/api/runs/d001', 'DELETE'],
  ['Series box', 'send', '/api/runs/series/celeste', 'PUT'],
  ['Genre box', 'send', '/api/runs/genre/celeste', 'PUT'],
  ['Developer box', 'send', '/api/runs/developer/celeste', 'PUT'],
  ['CSV import', 'send', '/api/runs/import', 'POST'],
  ['GDQ import', 'send', '/api/runs/import', 'POST'],
];
const SAID = 'This is test data, so nothing is saved. Open the real sheet to change a run.';
let reached = [];
const real = {
  send: async (path, method) => { reached.push([path, method]); return { ok: true }; },
  api: async (path, options) => { reached.push([path, options.method]); return { ok: true }; },
};
const demo = writeGuard({ isDemo: () => true, refusal: () => SAID, ...real });
for (const [name, how, path, method] of WRITES) {
  try {
    await (how === 'remove' ? demo.remove(path) : demo.send(path, method, {}));
    failures.push(`demo ${name}: was not refused`);
  } catch (error) {
    is(`demo ${name}: refused in the key's words, linking to the real sheet`, [error instanceof DemoRefused, error.message, error.href, error.tone], [true, SAID, REAL_PAGE, 'warn']);
  }
}
is('demo: no write reached the server', reached, []);
const live = writeGuard({ isDemo: () => false, refusal: () => SAID, ...real });
for (const [, how, path, method] of WRITES) await (how === 'remove' ? live.remove(path) : live.send(path, method, {}));
is('the real sheet: every write goes through', reached.length, WRITES.length);

const page = readFileSync(new URL('../public/assets/page-runs.js', import.meta.url), 'utf8');
is('page-runs: every send goes through the guard', [...page.matchAll(/(^|[^.\w])send\(/g)].length, 0);
is('page-runs: no DELETE outside the guard', /method:\s*'DELETE'/.test(page), false);
is('page-runs: the guard is built from the real send', /writeGuard\(\{[^}]*\bsend\b/.test(page), true);

if (failures.length) {
  console.error('runs-state: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log('runs-state: ok - paging (page N of M, the counted range), the hash round-trip with the demo flag and page, every filter resets the page, the demo payload through the shared builders, every write refused in demo mode');
