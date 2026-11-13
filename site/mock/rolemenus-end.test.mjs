// The Role menus page's end rules (site/public/assets/rolemenus-end.js), proved without a browser.
//   node site/mock/rolemenus-end.test.mjs
// Exits 0 when every case matched, 1 with a list of what did not.

import {
  END_FIELDS,
  drawerItems,
  endBody,
  endLine,
  filled,
  grantEndsWithMenu,
  menuFromHash,
  menuHash,
  resolvedMoment,
  resultLines,
  wordsBody,
} from '../public/assets/rolemenus-end.js';

const failures = [];
const is = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

const following = { ends_source: 'marathon', ends_marathon_id: '24', buffer_days: null };
const dated = { ends_source: 'date', ends_marathon_id: null, buffer_days: null };
const none = { ends_source: 'none', ends_marathon_id: null, buffer_days: null };

is('an untouched marathon end sends nothing', endBody(following, { how: 'marathon', marathonId: '24', buffer: '' }), null);
is('a new buffer on the same marathon is sent', endBody(following, { how: 'marathon', marathonId: '24', buffer: '2' }),
  { ends_source: 'marathon', ends_marathon_id: '24', buffer_days: '2' });
is('a blank buffer is the server default', endBody(dated, { how: 'marathon', marathonId: '24', buffer: ' ' }),
  { ends_source: 'marathon', ends_marathon_id: '24', buffer_days: null });
is('another marathon is sent', endBody(following, { how: 'marathon', marathonId: '3', buffer: '' }),
  { ends_source: 'marathon', ends_marathon_id: '3', buffer_days: null });
is('no marathon picked sends nothing', endBody(none, { how: 'marathon', marathonId: '', buffer: '' }), null);
is('a blank date sends nothing', endBody(dated, { how: 'date', date: '', time: '13:00' }), null);
is('a date alone is the day', endBody(none, { how: 'date', date: '2027-02-28', time: '' }),
  { ends_source: 'date', ends_at: '2027-02-28' });
is('a date and a time travel as typed, never as a browser Date', endBody(none, { how: 'date', date: '2027-02-28', time: '18:00' }),
  { ends_source: 'date', ends_at: '2027-02-28 18:00' });
is('No end on a menu with no end sends nothing', endBody(none, { how: 'none' }), null);
is('No end on a menu with one clears it', endBody(dated, { how: 'none' }), { ends_source: 'none' });

const words = wordsBody({ title: 'Back to Black', description: '', options: [], ends_source: 'date', buffer_days: 3, mode: 'single' });
is('a words save carries no end field', END_FIELDS.filter((key) => key in words), []);
is('a words save carries no retired field', 'mode' in words, false);
is('a words save keeps its words', words, { title: 'Back to Black', description: '', options: [] });

is('a menu name in the hash', menuFromHash('#btb-2027'), 'btb-2027');
is('an encoded name comes back whole', menuFromHash(menuHash('back to black')), 'back to black');
is('a section hash is not a menu', menuFromHash('#sect-timed-roles'), null);
is('no hash is no menu', menuFromHash(''), null);
is('a broken escape is no menu', menuFromHash('#%E0%A4%A'), null);

is('a menu with no end says only that', endLine({ ends_source: 'none', end_label: 'no end set', wearing: 4 }), 'no end set');
is('a menu with an end says who wears it', endLine({ ends_source: 'date', end_label: 'ends 2027-02-28 23:59', wearing: 23 }),
  'ends 2027-02-28 23:59 · 23 wearing');
is('an unknown count is a question mark', endLine({ ends_source: 'date', end_label: 'ends x', wearing: null }), 'ends x · ? wearing');

is('a typed day resolves to 23:59', resolvedMoment('2027-02-28', '', 'America/Phoenix'), '2027-02-28 23:59 · America/Phoenix');
is('a typed time is kept', resolvedMoment('2027-02-28', '18:00', 'America/Phoenix'), '2027-02-28 18:00 · America/Phoenix');
is('no day resolves to nothing', resolvedMoment('', '18:00', 'UTC'), '');

const fill = (template, values) => (template.includes('{broken') ? null : template.replace(/\{(\w+)\}/g, (all, key) => values[key] ?? all));
is('a staff sentence is filled', filled('Set by {who}', 'x', { who: 'Nick' }, fill), 'Set by Nick');
is('a broken staff sentence falls back to the shipped one', filled('{broken', 'Set by {who}', { who: 'Nick' }, fill), 'Set by Nick');

is('the result names who still wears what', resultLines({
  message: '**btb** ended — 2 role(s) taken off 3 people. 1 failure(s).',
  pass: { left: ['Ada still wears **Runner**'] },
}), ['**btb** ended — 2 role(s) taken off 3 people. 1 failure(s).', 'Ada still wears **Runner**']);
is('a clean result is one line', resultLines({ message: 'done', pass: { left: [] } }), ['done']);

is('the drawer line counts roles and people', drawerItems([{ name: 'btb-2027', roles: 7, wearing: 23 }]),
  [{ name: 'btb-2027', text: 'btb-2027 (7 roles · 23 people)' }]);
is('no bound menu draws nothing', drawerItems([]), []);
is('a count Discord has not sent reads ?', drawerItems([{ name: 'x', roles: 1, wearing: null }])[0].text, 'x (1 roles · ? people)');

is('an open grant on a menu with an end ends with it', grantEndsWithMenu({ open: true, ends_with_menu: 'btb' }), true);
is('an ended grant does not', grantEndsWithMenu({ open: false, ends_with_menu: 'btb' }), false);
is('a grant on no menu does not', grantEndsWithMenu({ open: true, ends_with_menu: null }), false);

if (failures.length) {
  console.error('rolemenus-end: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log('rolemenus-end: ok - an untouched End card sends no end field, a words save never does, typed dates travel as text, and the hash, lines and drawer read right');
