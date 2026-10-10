// The Leaderboard page's pure helpers (site/public/assets/leaderboard-layout.js).
//   node site/mock/leaderboard.test.mjs
// Exits 0 when every fixture matched, 1 with a list of what did not.

import {
  amountRules,
  bountyStatus,
  gamesOf,
  pageOf,
  pageWith,
  pinned,
  runLine,
  sortedBounties,
  ticketHref,
  wallIn,
  zonedIso,
} from '../public/assets/leaderboard-layout.js';

const failures = [];
const is = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

const board = Array.from({ length: 53 }, (_, at) => ({ place: at + 1, user_id: String(100 + at) }));

is('page 1', pageOf(board, 1).rows.map((row) => row.place).slice(0, 2), [1, 2]);
is('page 1 size', pageOf(board, 1).rows.length, 25);
is('pages', pageOf(board, 1).pages, 3);
is('last page', pageOf(board, 3).rows.map((row) => row.place), [51, 52, 53]);
is('past the end', pageOf(board, 9).page, 3);
is('before the start', pageOf(board, 0).page, 1);
is('junk page', pageOf(board, 'x').page, 1);
is('empty board', pageOf([], 1), { rows: [], page: 1, pages: 1 });
is('page with #26', pageWith(board, '125'), 2);
is('page with #25', pageWith(board, '124'), 1);
is('page with nobody', pageWith(board, '999'), 1);

const top = board.slice(0, 10);
is('in the top: nothing pinned', pinned(top, board, '103'), null);
is('below the top: pinned', pinned(top, board, 111), { place: 12, user_id: '111' });
is('not on the board', pinned(top, board, '999'), null);
is('signed out', pinned(top, board, null), null);

is('games one per line', gamesOf(' Celeste \n\nHollow   Knight\ncELESTE\r\nHades '), ['Celeste', 'Hollow Knight', 'Hades']);
is('games none', gamesOf('  \n '), []);
is('a comma stays inside a name', gamesOf('Hello, World'), ['Hello, World']);

is('run line', runLine({ game: 'Celeste', category: 'Any%', time: '29:59.50' }), 'Celeste · Any% · 29:59.50');
is('run line, no category', runLine({ game: 'Celeste', category: null, time: '1:00' }), 'Celeste · 1:00');
is('ticket link', ticketHref('600', '850'), 'https://discord.com/channels/600/850');
is('ticket link, none', ticketHref('600', null), null);

// Phoenix has no daylight saving: always -07:00.
is('phoenix', zonedIso('2026-10-31 19:30', 'America/Phoenix'), '2026-10-31T19:30:00-07:00');
is('phoenix, T form', zonedIso('2026-01-05T08:05', 'America/Phoenix'), '2026-01-05T08:05:00-07:00');
// New York: EDT (-04:00) in October, EST (-05:00) in December.
is('new york summer', zonedIso('2026-10-09 12:00', 'America/New_York'), '2026-10-09T12:00:00-04:00');
is('new york winter', zonedIso('2026-12-01 12:00', 'America/New_York'), '2026-12-01T12:00:00-05:00');
is('utc', zonedIso('2026-12-01 00:00', 'UTC'), '2026-12-01T00:00:00+00:00');
is('kolkata half hour', zonedIso('2026-12-01 09:00', 'Asia/Kolkata'), '2026-12-01T09:00:00+05:30');
is('unreadable', zonedIso('31/10/2026', 'UTC'), null);
is('bad zone', zonedIso('2026-12-01 00:00', 'Not/AZone'), null);
is('wall back', wallIn('2026-10-31T19:30:00-07:00', 'America/Phoenix'), '2026-10-31 19:30');
is('wall in utc', wallIn('2026-11-01T02:30:00+00:00', 'UTC'), '2026-11-01 02:30');
is('wall round trip', wallIn(zonedIso('2026-03-08 03:30', 'America/New_York'), 'America/New_York'), '2026-03-08 03:30');
is('wall of nothing', wallIn(null, 'UTC'), '');

const now = '2026-10-09T12:00:00+00:00';
const bounty = (extra) => ({ id: 1, active: true, live: false, starts_at: null, ends_at: null, ...extra });
is('live', bountyStatus(bounty({ live: true }), now), 'live');
is('ended by hand', bountyStatus(bounty({ active: false, live: true }), now), 'ended');
is('ended by date', bountyStatus(bounty({ starts_at: '2026-09-01T00:00:00+00:00', ends_at: '2026-10-01T00:00:00+00:00' }), now), 'ended');
is('upcoming', bountyStatus(bounty({ starts_at: '2026-10-20T00:00:00+00:00', ends_at: '2026-10-31T00:00:00+00:00' }), now), 'upcoming');
is('event with no window', bountyStatus(bounty({ event_id: 4 }), now), 'idle');
is('sorted', sortedBounties([
  bounty({ id: 1, active: false }),
  bounty({ id: 2, starts_at: '2026-10-20T00:00:00+00:00', ends_at: '2026-10-31T00:00:00+00:00' }),
  bounty({ id: 3, live: true }),
  bounty({ id: 4, event_id: 9 }),
], now).map((one) => [one.bounty.id, one.status]), [[3, 'live'], [2, 'upcoming'], [4, 'idle'], [1, 'ended']]);

is('multiplier bounds', amountRules('multiplier'), { min: '1.01', max: '10', step: '0.01', value: '2' });
is('extra bounds', amountRules('extra'), { min: '1', max: '100000', step: '1', value: '10' });

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('leaderboard: ok');
