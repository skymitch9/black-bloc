// The shared field aids' pure half (site/public/assets/fieldaids.js), proved without a browser.
//   node site/mock/fieldaids.test.mjs
// Exits 0 when every fixture matched, 1 with a list of what did not.

import { capState, counterState, insertAt, placeholdersFor, tokensIn } from '../public/assets/fieldaids.js';

const failures = [];
const is = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

is('tokens come out in first-seen order, once each',
  tokensIn('{name} is live with {game}', 'takes {name}, {game}, {title} and {url}'),
  ['{name}', '{game}', '{title}', '{url}']);
is('no tokens in plain words', tokensIn('nothing here', null, undefined), []);
is('an escaped brace pair is not a token', tokensIn('{{name}} and {}'), ['{name}']);
is('a JSON-looking brace is not a token', tokensIn('{"a": 1} {Name} {1st}'), []);
is('underscores and digits ride along', tokensIn('{their_time} {slot2}'), ['{their_time}', '{slot2}']);

is('the chips of a wording are the fields of its default plus the ones its help names',
  placeholdersFor({ default: '{name} is live: {url}', help: 'It takes {name} {game} {title} {url} {platform}' }),
  ['{name}', '{url}', '{game}', '{title}', '{platform}']);
is('a field only the help mentions belongs to another wording, so no chips',
  placeholdersFor({ default: 'runs', help: '{part} for a runner' }), []);
is('the fields of a stored value count', placeholdersFor({ default: 'plain', value: 'hi {user}', help: '' }), ['{user}']);
is('no spec, no chips', placeholdersFor(null), []);

is('a chip lands at the cursor', insertAt('hello world', 6, 6, '{name} '), { value: 'hello {name} world', start: 13, end: 13 });
is('a chip replaces the selection', insertAt('hello world', 6, 11, '{name}'), { value: 'hello {name}', start: 12, end: 12 });
is('a chip at the very start', insertAt('live', 0, 0, '{name}'), { value: '{name}live', start: 6, end: 6 });
is('no cursor means the end', insertAt('live ', null, null, '{url}'), { value: 'live {url}', start: 10, end: 10 });
is('a cursor past the end is the end', insertAt('ab', 99, 99, '{x}'), { value: 'ab{x}', start: 5, end: 5 });
is('an empty box', insertAt('', 0, 0, '{game}'), { value: '{game}', start: 6, end: 6 });

is('far from the limit the counter is not drawn', counterState(10, 80).shown, false);
is('one short of near is not drawn', counterState(63, 80).shown, false);
is('at near it appears', counterState(64, 80), { shown: true, tone: null, text: '64 / 80', left: 16 });
is('at the limit it warns', counterState(80, 80), { shown: true, tone: 'warn', text: '80 / 80', left: 0 });
is('over the limit it is a refusal', counterState(81, 80), { shown: true, tone: 'danger', text: '81 / 80', left: -1 });
is('no limit, no counter', counterState(5, 0).shown, false);

is('room left under the cap', capState(3, 10), { full: false, text: '3 of 10' });
is('at the cap it is full', capState(10, 10), { full: true, text: '10 of 10' });
is('over the cap is still full', capState(11, 10).full, true);
is('an empty list', capState(0, 5), { full: false, text: '0 of 5' });

if (failures.length) {
  process.stdout.write(`fieldaids: ${failures.length} problem(s)\n`);
  for (const line of failures) process.stdout.write(`  ${line}\n`);
  process.exit(1);
}
process.stdout.write('fieldaids: ok - tokens, insertion at the cursor, the counter and the cap\n');
