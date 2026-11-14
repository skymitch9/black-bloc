// The Timed roles page's pure rules (site/public/assets/rolemenus-end.js), proved without a browser.
//   node site/mock/rolemenus-end.test.mjs
// Exits 0 when every case matched, 1 with a list of what did not.

import {
  END_FIELDS,
  GIVE,
  TAKE,
  drawerItems,
  endBody,
  fillLine,
  fillUnmatched,
  filled,
  freeMarathons,
  grantEndsWithMenu,
  heldRoles,
  menuFromHash,
  menuHash,
  noteKey,
  notTimed,
  previewBody,
  resolvedMoment,
  resultLines,
  saveBody,
  splitEvents,
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
is('no marathon picked sends nothing', endBody(none, { how: 'marathon', marathonId: '', buffer: '' }), null);
is('a date alone is the day', endBody(none, { how: 'date', date: '2027-02-28', time: '' }),
  { ends_source: 'date', ends_at: '2027-02-28' });
is('a date and a time travel as typed, never as a browser Date', endBody(none, { how: 'date', date: '2027-02-28', time: '18:00' }),
  { ends_source: 'date', ends_at: '2027-02-28 18:00' });
is('No end on an event with no end sends nothing', endBody(none, { how: 'none' }), null);
is('No end on an event with one clears it', endBody(dated, { how: 'none' }), { ends_source: 'none' });
is('an end body only ever names end fields', Object.keys(endBody(dated, { how: 'marathon', marathonId: '3', buffer: '1' })).every((key) => END_FIELDS.includes(key)), true);

is('an event name in the hash', menuFromHash('#btb-2027'), 'btb-2027');
is('an encoded name comes back whole', menuFromHash(menuHash('back to black')), 'back to black');
is('a section hash is not an event', menuFromHash('#sect-events'), null);
is('a broken escape is no event', menuFromHash('#%E0%A4%A'), null);

is('a typed day resolves to 23:59', resolvedMoment('2027-02-28', '', 'America/Phoenix'), '2027-02-28 23:59 · America/Phoenix');
is('no day resolves to nothing', resolvedMoment('', '18:00', 'UTC'), '');

const fill = (template, values) => (template.includes('{broken') ? null : template.replace(/\{(\w+)\}/g, (all, key) => values[key] ?? all));
is('a staff sentence is filled', filled('Set by {who}', 'x', { who: 'Nick' }, fill), 'Set by Nick');
is('a broken staff sentence falls back to the shipped one', filled('{broken', 'Set by {who}', { who: 'Nick' }, fill), 'Set by Nick');

is('the result names who still wears what', resultLines({ message: 'ended', pass: { left: ['Ada still wears **Runner**'] } }),
  ['ended', 'Ada still wears **Runner**']);

is('the drawer line names the EVENT, not its key', drawerItems([{ name: 'btb-2027', title: 'Back to Black 2027', roles: 7, assigned: 23 }]),
  [{ name: 'btb-2027', text: 'Back to Black 2027 (23 people)' }]);
is('no bound event draws nothing', drawerItems([]), []);

is('an open assignment ends with its event', grantEndsWithMenu({ open: true, ends_with_menu: 'Back to Black' }), true);
is('an ended one does not', grantEndsWithMenu({ open: false, ends_with_menu: 'Back to Black' }), false);

const events = [{ name: 'a', open: true }, { name: 'b', open: false }, { name: 'c', open: true }];
is('open events keep the API order and ended ones fold apart', splitEvents(events),
  { open: [events[0], events[2]], ended: [events[1]] });
is('a role nobody is assigned is no fact', heldRoles({ assigned_by_role: [{ role_id: '1', count: 0 }, { role_id: '2', count: 3 }] }),
  [{ role_id: '2', count: 3 }]);

const marathons = [{ id: '1', event: null }, { id: '2', event: 'btb' }, { id: '3', event: 'other' }];
is('New event offers only marathons no open event follows', freeMarathons(marathons).map((one) => one.id), ['1']);
is('Change the end also offers the one the event follows itself', freeMarathons(marathons, 'btb').map((one) => one.id), ['1', '2']);
is('the ad-hoc grant form never offers a timed role', notTimed([{ id: '1' }, { id: '2' }], [{ role_id: '2' }]), [{ id: '1' }]);

is('Check the list sends the pasted text and the ticked ids once', previewBody({
  roleId: 13, text: 'ada\n<@9>', ticked: [{ id: '7' }, { id: '7' }, { id: 8 }], mode: GIVE,
}), { role_id: '13', lines: 'ada\n<@9>', user_ids: ['7', '8'], remove: false });
is('Take off says so', previewBody({ roleId: '13', text: '', ticked: [], mode: TAKE }).remove, true);
is('the save sends exactly who the preview said, nobody it only matched', saveBody({
  role_id: '13', remove: false, matched: [{ user_id: '1' }, { user_id: '2', note: 'already' }], to_save: ['1'],
}), { role_id: '13', user_ids: ['1'], remove: false });
is('every reason a line was not saved has a key', ['already', 'not_assigned', 'ambiguous', 'unknown'].map(noteKey).every(Boolean), true);
is('a person the save changes has no note', noteKey(null), null);

const line = { part: 'runner', part_label: 'runs', setting: 'rolemenu_fill_runner_role_id', role_id: '13', role_name: 'Runner', timed: true, matched: 2, missing: 1, unmatched: ['Ryan', 'Gelly'], unmatched_count: 5 };
is('a Fill line counts with the role by name, never a Discord token', fillLine(line),
  { key: 'rolemenu_site_fill_line', values: { part: 'runs', matched: 2, missing: 1, role: 'Runner' } });
is('a part with no role says which setting', fillLine({ ...line, role_id: null }).key, 'rolemenu_fill_no_role_line');
is('a part whose role left the list says so', fillLine({ ...line, timed: false }).key, 'rolemenu_site_fill_not_timed_line');
is('the unmatched names carry the count past the ones shown', fillUnmatched(line).values.names, 'Ryan, Gelly +3');
is('nobody unmatched draws no line', fillUnmatched({ ...line, unmatched: [], unmatched_count: 0 }), null);

if (failures.length) {
  console.error('rolemenus-end: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log('rolemenus-end: ok - ends send only end fields, marathons are offered one event each, a list saves only what its preview showed, and Fill and the drawer read in words');
