// Which Posts-page hashes open a post and which open a section (site/public/assets/posts-hash.js).
//   node site/mock/posts-hash.test.mjs
// Exits 0 when every fixture matched, 1 with a list of what did not.

import { SECTION_HASHES, postSlugOf } from '../public/assets/posts-hash.js';

const failures = [];
const is = (where, found, wanted) => {
  if (JSON.stringify(found) !== JSON.stringify(wanted)) {
    failures.push(`${where}: is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
  }
};

is('a post slug opens the post', postSlugOf('#rules'), 'rules');
is('a post whose slug starts with sect- opens the post', postSlugOf('#sect-rules'), 'sect-rules');
is('the sticky section is a section', postSlugOf('#sect-sticky'), null);
is(
  'every section of the page is a section',
  SECTION_HASHES.map((one) => postSlugOf(`#${one}`)),
  [null, null, null, null],
);
is('no hash is no post', [postSlugOf(''), postSlugOf('#'), postSlugOf(null)], [null, null, null]);
is('a hash without its mark still reads', postSlugOf('sect-rules'), 'sect-rules');

if (failures.length) {
  console.error('posts-hash: not ok');
  for (const said of failures) console.error(`  - ${said}`);
  process.exit(1);
}
console.log('posts-hash: ok - section hashes open sections, every other hash opens a post');
