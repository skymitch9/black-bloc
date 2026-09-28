// The Blocks section's search + filter matcher, proved without a browser.
// `site/public/assets/blockmatch.js` is the one home for it — page-posts.js's Blocks
// section calls it, nothing re-implements the matching there.
//
//   node site/mock/blockmatch.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.
// scripts/deploy.ps1 and .github/workflows/ci.yml run it beside check.mjs.

import { blockMatches } from '../public/assets/blockmatch.js';

const failures = [];
const is = (where, found, wanted) => {
  if (found !== wanted) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

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

is('empty query, all filter — everything matches', blockMatches(doorKind, '', 'all'), true);
is('name substring', blockMatches(doorKind, 'front door', 'all'), true);
is('where text', blockMatches(doorKind, 'welcome', 'all'), true);
is('a word inside a key', blockMatches(doorKind, 'ticket', 'all'), true);
is('no match', blockMatches(doorKind, 'birthday', 'all'), false);
is('query is case-sensitive-proof (already lowercased by callers)', blockMatches(doorKind, 'front', 'all'), true);

is('on_post filter keeps a block with a post', blockMatches(doorKind, '', 'on_post'), true);
is('on_post filter drops a block with none', blockMatches(eventsKind, '', 'on_post'), false);
is('no_post filter keeps a block with none', blockMatches(eventsKind, '', 'no_post'), true);
is('no_post filter drops a block with a post', blockMatches(doorKind, '', 'no_post'), false);
is('exclusive filter keeps one-at-a-time', blockMatches(doorKind, '', 'exclusive'), true);
is('exclusive filter drops any-number', blockMatches(eventsKind, '', 'exclusive'), false);
is('filter and query combine', blockMatches(doorKind, 'birthday', 'on_post'), false);
is('unknown filter key falls back to all', blockMatches(doorKind, '', 'nonsense'), true);

if (failures.length) {
  console.error('blockmatch: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log(
  'blockmatch: ok - search matches a kind\'s name, where text and key words; the four ' +
  'filter chips and the search box combine',
);
