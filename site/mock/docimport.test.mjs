// The owner's acceptance test for Import from a Google Doc: the real export of the Doc the live
// welcome post was written from must convert to that post's exact text.
//
//   node site/mock/docimport.test.mjs
//
// Exits 0 on an exact match, 1 with the first differing line. scripts/deploy.ps1 runs it.

import { readFileSync } from 'node:fs';
import { htmlToDiscordMarkdown, mentionChannels } from '../public/assets/clipmd.js';

const here = (name) => new URL(`./fixtures/${name}`, import.meta.url);
const EXPORT = readFileSync(here('rules-export.html'), 'utf8');
const LIVE = readFileSync(here('welcome-live.md'), 'utf8');

const CHANNELS = { 'off-topic': '1073710703518683143', 'recipes-and-food-pics': '1413700333796069419' };
const FROM = '# Suggestions for Revamped Rules';
const UNTIL = '# General Comments/Notes';

const UNDERLINE_SETTLED = {
  id: 'banworthy-underline-settled-by-owner-2026-09-28',
  doc: '__**Banworthy Offenses**__',
  live: '**Banworthy Offenses**',
};

function section(markdown) {
  const lines = markdown.split('\n');
  const from = lines.indexOf(FROM);
  const until = lines.indexOf(UNTIL);
  if (from < 0 || until < from) return null;
  return lines.slice(from + 1, until).join('\n');
}

const failures = [];
const whole = htmlToDiscordMarkdown(EXPORT);
const cut = section(whole);
if (cut === null) {
  failures.push(`the section headings were not found as headings:\n${whole}`);
} else {
  const found = mentionChannels(cut, CHANNELS).trim();
  const lines = found.split('\n');
  const at = lines.indexOf(UNDERLINE_SETTLED.doc);
  if (at < 0) failures.push(`${UNDERLINE_SETTLED.id}: the Doc's underlined line ${JSON.stringify(UNDERLINE_SETTLED.doc)} is missing`);
  else lines[at] = UNDERLINE_SETTLED.live;
  const wanted = LIVE.replace(/\r\n/g, '\n').trim();
  const said = lines.join('\n');
  if (said !== wanted) {
    const a = said.split('\n');
    const b = wanted.split('\n');
    let line = 0;
    while (line < Math.max(a.length, b.length) && a[line] === b[line]) line += 1;
    failures.push(`line ${line + 1} differs:\n      got:  ${JSON.stringify(a[line])}\n      live: ${JSON.stringify(b[line])}\n--- got ---\n${said}`);
  }
}

process.stdout.write('docimport: the welcome post against the Doc it was written from\n');
if (failures.length) {
  process.stdout.write(`docimport: ${failures.length} problem(s)\n`);
  for (const said of failures) process.stdout.write(`  - ${said}\n`);
  process.exit(1);
}
process.stdout.write(
  `docimport: ok - the export's rules section converts to the live welcome post byte for byte, `
    + `apart from ${UNDERLINE_SETTLED.id}\n`,
);
