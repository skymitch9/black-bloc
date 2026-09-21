// Which blocks go in which dashboard column, proved without a browser.
// `site/public/assets/columns.js` is the placement decision `layout.js:balance` makes; the
// greedy shortest-column version it replaced reordered the page (measured 2026-09-20: the
// Requests page put Open, its main list, at the top of the RIGHT column under In progress /
// Ready to check / On hold). The rule now: document order, one break.
//
//   node site/mock/layout.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.
// scripts/deploy.ps1 and .github/workflows/ci.yml run it beside check.mjs.
// The heights below are SYNTHETIC — the shapes are taken from real pages, the numbers are not.

import { columnSplit } from '../public/assets/columns.js';

const failures = [];
const is = (where, found, wanted) => {
  if (found !== wanted) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

const columns = (heights, titles) => {
  const at = columnSplit(heights);
  return [titles.slice(0, at), titles.slice(at)];
};
const same = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

is('two equal blocks break in the middle', columnSplit([10, 10]), 1);
is('two blocks, the first much taller', columnSplit([100, 5]), 1);
is('four equal blocks', columnSplit([5, 5, 5, 5]), 2);
is('one tall block and two short ones', columnSplit([100, 5, 5]), 1);
is('two short blocks and one tall one', columnSplit([5, 5, 100]), 2);
is('a run of one is never split', columnSplit([40]), 1);
is('an empty run', columnSplit([]), 0);
is('the ladder', columnSplit([10, 20, 30, 40]), 3);

// The Requests page's run, in the order page-requests.js renders it.
const REQUESTS = ['Open', 'In progress', 'Ready to check', 'On hold', 'Done', 'Declined', 'File a request', 'Settings'];
same(
  'the Requests page keeps Open first',
  columns([620, 240, 180, 160, 300, 220, 200, 160], REQUESTS),
  [['Open', 'In progress', 'Ready to check'], ['On hold', 'Done', 'Declined', 'File a request', 'Settings']],
);
is('Open is in the left column whatever the heights', columnSplit([90, 900, 5, 5]) >= 1, true);

// Every fixture, whatever the heights: order is kept and neither column is empty.
const RUNS = [
  [10, 10],
  [100, 5],
  [5, 100],
  [5, 5, 5, 5],
  [620, 240, 180, 160, 300, 220, 200, 160],
  [1, 1, 1, 1, 1, 1, 1, 1, 1],
  [300, 1, 1],
];
for (const heights of RUNS) {
  const at = columnSplit(heights);
  const where = `run ${JSON.stringify(heights)}`;
  is(`${where}: the first block is on the left`, at >= 1, true);
  is(`${where}: the right column has something`, at <= heights.length - 1, true);
}

if (failures.length) {
  console.error('layout: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log(
  'layout: ok - a run breaks at one point, the left column holds what the page rendered first, ' +
  'and neither column comes back empty',
);
