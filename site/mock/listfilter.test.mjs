// The shared list filter's pure matcher (site/public/assets/listfilter.js), proved without a browser.
//   node site/mock/listfilter.test.mjs
// Exits 0 when every fixture matched, 1 with a list of what did not.

import { readFileSync } from 'node:fs';

import {
  BLOCK_FILTERS,
  applyFilters,
  blockText,
  countedChoices,
  familyLabel,
  familyLines,
  familyTerms,
  genreFamilies,
  genreFamily,
  genreNormal,
  genreQualifiers,
  matches,
  passes,
  ruleOf,
  oneEdit,
  runsMatches,
} from '../public/assets/listfilter.js';

const failures = [];
const is = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

is('empty query matches anything', matches('abc', ''), true);
is('blank query matches anything', matches('abc', '   '), true);
is('null query matches anything', matches('abc', null), true);
is('substring', matches('Welcome and rules', 'and ru'), true);
is('case-insensitive both ways', matches('Welcome', 'WELC'), true);
is('query is trimmed', matches('welcome', '  welc  '), true);
is('no match', matches('welcome', 'birthday'), false);
is('null text with a query', matches(null, 'x'), false);

const FILTERS = [
  ['all', 'All', null],
  ['odd', 'Odd', (n) => n.v % 2 === 1],
  ['big', 'Big', (n) => n.v > 2],
];
const nums = [{ v: 1, t: 'one' }, { v: 2, t: 'two' }, { v: 3, t: 'three' }];
const text = (n) => n.t;
is('ruleOf unknown key falls back to the first', ruleOf(FILTERS, 'nope'), null);
is('ruleOf no filters', ruleOf(null, 'odd'), null);
is('passes: chip only', passes(nums[1], { text, filters: FILTERS, filter: 'odd' }), false);
is('passes: chip and search combine (AND)', passes(nums[2], { text, filters: FILTERS, filter: 'odd', query: 'thr' }), true);
is('passes: chip passes, search fails', passes(nums[0], { text, filters: FILTERS, filter: 'odd', query: 'thr' }), false);
is('applyFilters counts', applyFilters(nums, { text, filters: FILTERS, filter: 'big', query: 't' }),
  { hits: [false, false, true], shown: 1, total: 3 });
is('applyFilters with no filters is search only', applyFilters(nums, { text, query: 'T' }).shown, 2);
is('applyFilters on nothing', applyFilters([], { text }), { hits: [], shown: 0, total: 0 });

const doorKind = {
  kind: 'frontdoor',
  name: 'Front door',
  where: 'on Welcome',
  exclusive: true,
  keys: ['frontdoor_title', 'frontdoor_ticket_label'],
  on: [{ slug: 'welcome', title: 'Welcome' }],
};
const eventsKind = {
  kind: 'events_upcoming',
  name: 'Upcoming events',
  where: 'on no post yet',
  exclusive: false,
  keys: ['events_upcoming_title', 'events_upcoming_line'],
  on: [],
};
const block = (kind, query, filter) => passes(kind, { text: blockText, filters: BLOCK_FILTERS, filter, query });

is('blocks: empty query, all filter', block(doorKind, '', 'all'), true);
is('blocks: name substring', block(doorKind, 'front door', 'all'), true);
is('blocks: where text', block(doorKind, 'welcome', 'all'), true);
is('blocks: a word inside a key', block(doorKind, 'ticket', 'all'), true);
is('blocks: no match', block(doorKind, 'birthday', 'all'), false);
is('blocks: upper-case query', block(doorKind, 'FRONT', 'all'), true);
is('blocks: on_post keeps a block with a post', block(doorKind, '', 'on_post'), true);
is('blocks: on_post drops a block with none', block(eventsKind, '', 'on_post'), false);
is('blocks: no_post keeps a block with none', block(eventsKind, '', 'no_post'), true);
is('blocks: no_post drops a block with a post', block(doorKind, '', 'no_post'), false);
is('blocks: exclusive keeps one-at-a-time', block(doorKind, '', 'exclusive'), true);
is('blocks: exclusive drops any-number', block(eventsKind, '', 'exclusive'), false);
is('blocks: filter and query combine', block(doorKind, 'birthday', 'on_post'), false);
is('blocks: unknown filter key falls back to all', block(doorKind, '', 'nonsense'), true);

const runs = [
  { event: 'BtB 2025', runners: ['Kat', 'PT'] },
  { event: 'SGDQ 2025', runners: ['kat'] },
  { event: 'BtB 2025', runners: ['Kat', 'Kat'] },
  { event: '', runners: [] },
];
is('choices: counted per item, blanks dropped, a repeat in one item counted once',
  countedChoices(runs, (run) => run.runners), [['Kat', 'Kat (2)'], ['kat', 'kat (1)'], ['PT', 'PT (1)']]);
is('choices: sorted by name, case-insensitive', countedChoices(runs, (run) => [run.event]).map(([key]) => key), ['BtB 2025', 'SGDQ 2025']);
is('choices: a given order wins',
  countedChoices(runs, (run) => [run.event], { order: (a, b) => b.localeCompare(a) }).map(([, label]) => label),
  ['SGDQ 2025 (1)', 'BtB 2025 (2)']);
is('choices: nothing to choose', countedChoices([], (run) => [run.event]), []);
is('choices: a label shapes the words, not the value',
  countedChoices([{ g: 'racing' }, { g: 'racing' }], (one) => [one.g], { label: familyLabel }), [['racing', 'Racing (2)']]);

const genres = JSON.parse(readFileSync(new URL('../../tests/fixtures/runs/genre_families.json', import.meta.url), 'utf8'));
const qualifiers = genreQualifiers(genres.qualifiers);
const families = genreFamilies(genres.families);
for (const [text, family] of genres.cases) is(`genres: ${JSON.stringify(text)} is in ${JSON.stringify(family)}`, genreFamily(text, qualifiers, families), family);
is('genres: punctuation and spacing are one space', genreNormal('  Third-person/Shooter!! '), 'third person shooter');
is('genres: qualifiers longest first, each once', genreQualifiers('kart,\nthird-person , KART, '), ['third person', 'kart']);
is('genres: the full text is tried before the stripped one',
  genreFamily('Action adventure', ['action'], genreFamilies('adventure:\naction adventure game: action adventure')), 'action adventure game');
is('genres: a bad line is skipped and named by number',
  familyLines('racing: racer\nnot a family\n\n: orphan\npuzzle:'),
  { families: [['racing', ['racer']], ['puzzle', []]], bad: [[2, 'not a family'], [4, ': orphan']] });
is('genres: terms carry every alias', familyTerms('racing', families), 'racing racer racers race kart racer kart racing');
is('genres: a family no line names is its own term', familyTerms('puzzle', families), 'puzzle');
is('genres: a label is capitalised', familyLabel('survival horror'), 'Survival horror');

const search = JSON.parse(readFileSync(new URL('../../tests/fixtures/runs/search.json', import.meta.url), 'utf8'));
for (const [query, wanted] of search.cases) {
  const found = Object.entries(search.haystacks).filter(([, haystack]) => runsMatches(query, haystack)).map(([name]) => name);
  is(`runs search: ${JSON.stringify(query)}`, found, wanted);
}
is('runs search: one edit is a swap, an insert, a delete or a replace', ['ab|ba', 'abc|abxc', 'abc|ac', 'abc|abd', 'abcd|badc'].map((pair) => oneEdit(...pair.split('|'))), [true, true, true, true, false]);
is('runs search: the words option is the runs rule', matches('Donkey Kong Country 2', 'dkc2', { match: 'words' }), true);
is('runs search: the words option still lets a blank query through', matches('anything', '  ', { match: 'words' }), true);
is('runs search: without the option a search stays a substring', matches('Donkey Kong Country 2', 'dkc2'), false);
is('runs search: passes carries the option', passes({ t: 'Jet Force Gemini' }, { text: (one) => one.t, query: 'jfg', match: 'words' }), true);
is('runs search: applyFilters without it is unchanged', applyFilters([{ t: 'Jet Force Gemini' }], { text: (one) => one.t, query: 'jfg' }).shown, 0);

if (failures.length) {
  console.error('listfilter: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log('listfilter: ok - substring search (trimmed, case-insensitive), chips AND search, the Blocks filters, counted select choices, the genre family rule on the shared fixture, the runs search rule on its shared fixture');
