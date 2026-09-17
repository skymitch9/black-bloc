// What a settings key and a channel are CALLED, proved without a browser.
// `site/public/assets/labels.js` is the one home for both, and `channelLabel` is what every
// channel dropdown on the site draws (owner, 2026-09-17: "All channel drop-selects should
// include a category for less confusion" — he had just saved the wrong of two modmail-logs).
//
//   node site/mock/labels.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.
// scripts/deploy.ps1 and .github/workflows/ci.yml run it beside check.mjs.

import { channelLabel, humanLabel } from '../public/assets/labels.js';

const failures = [];
const is = (where, found, wanted) => {
  if (found !== wanted) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

const CHANNELS = [
  { id: '1', name: 'BlackMail', type: 'category', category_id: null },
  { id: '2', name: 'modmail-log', type: 'text', category_id: '1' },
  { id: '3', name: 'modmail-log', type: 'text', category_id: null },
  { id: '4', name: "casey's room", type: 'voice', category_id: '1' },
  { id: '5', name: 'tickets', type: 'forum', category_id: '9000' },
];
const by = (id) => CHANNELS.find((one) => one.id === id);

is('a channel in a category', channelLabel(by('2'), CHANNELS), '# modmail-log · BlackMail');
is('the same name at the top level', channelLabel(by('3'), CHANNELS), '# modmail-log');
is('a voice channel', channelLabel(by('4'), CHANNELS), "🔊 casey's room · BlackMail");
is('a forum whose category is gone', channelLabel(by('5'), CHANNELS), '# tickets');
is('the category row itself', channelLabel(by('1'), CHANNELS), '▸ BlackMail');
is('no list at all', channelLabel(by('2')), '# modmail-log');

is('a key with a label', humanLabel('staff_channel_id'), 'Which channel decides who counts as staff');
is('a key with none', humanLabel('modmail_never_heard_of_it'), 'Never heard of it');

if (failures.length) {
  console.error('labels: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log(
  'labels: ok - a channel in a category reads "# name · Category", one at the top level reads ' +
  'the name alone, and a category row is unchanged',
);
