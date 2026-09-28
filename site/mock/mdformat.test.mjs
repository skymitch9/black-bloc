// The post editor's formatting toolbar, proved without a browser. `site/public/assets/mdformat.js`
// takes the text box's value and selection and answers with the new value and selection, so every
// button and shortcut is one of these calls.
//
//   node site/mock/mdformat.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.

import {
  cleanUrl, codeBlock, heading, indent, link, linkedText, numberLines, outdent, prefixLines, unlink, wrap,
} from '../public/assets/mdformat.js';

const failures = [];

function is(where, found, wanted) {
  const a = JSON.stringify(found);
  const b = JSON.stringify(wanted);
  if (a !== b) failures.push(`${where}: is\n${a}\n      not\n${b}`);
}

const at = (text) => {
  const start = text.indexOf('«');
  const end = text.indexOf('»') - 1;
  return [text.replace('«', '').replace('»', ''), start, end];
};
const show = ({ value, start, end }) => `${value.slice(0, start)}«${value.slice(start, end)}»${value.slice(end)}`;
const run = (fn, text, ...rest) => show(fn(...at(text), ...rest));

is('bold wraps', run(wrap, 'a «word» b', '**'), 'a **«word»** b');
is('bold toggles off outside', run(wrap, 'a **«word»** b', '**'), 'a «word» b');
is('bold toggles off inside', run(wrap, 'a «**word**» b', '**'), 'a «word» b');
is('bold at caret', run(wrap, 'a «» b', '**'), 'a **«»** b');
is('bold twice at caret undoes', run(wrap, 'a **«»** b', '**'), 'a «» b');
is('italic on bold adds', run(wrap, '**«x»**', '*'), '***«x»***');
is('italic off bold-italic', run(wrap, '***«x»***', '*'), '**«x»**');
is('bold off bold-italic', run(wrap, '***«x»***', '**'), '*«x»*');
is('italic inside bold selection', run(wrap, '«**x**»', '*'), '*«**x**»*');
is('italic toggles off', run(wrap, '*«x»*', '*'), '«x»');
is('underline', run(wrap, '«u»', '__'), '__«u»__');
is('underline off', run(wrap, '__«u»__', '__'), '«u»');
is('strike', run(wrap, '«s»', '~~'), '~~«s»~~');
is('spoiler', run(wrap, '«s»', '||'), '||«s»||');
is('spoiler off', run(wrap, '||«s»||', '||'), '«s»');
is('inline code', run(wrap, '«c»', '`'), '`«c»`');
is('inline code off', run(wrap, '`«c»`', '`'), '«c»');
is('inline code inside a fence is not code', run(wrap, '```«c»```', '`'), '````«c»````');

is('code block mid-line', run(codeBlock, 'a «x» b'), 'a \n```\n«x»\n```\n b');
is('code block own line', run(codeBlock, '«x»'), '```\n«x»\n```');
is('code block off outside', run(codeBlock, '```\n«x»\n```'), '«x»');
is('code block off inside', run(codeBlock, '«```\nx\n```»'), '«x»');

is('bullets keep a mid-line selection', run(prefixLines, 'o«ne\ntw»o', '- '), '- o«ne\n- tw»o');
is('bullets skip blank lines', run(prefixLines, '«one\n\ntwo»', '- '), '«- one\n\n- two»');
is('bullets off', run(prefixLines, '«- one\n- two»', '- '), '«one\ntwo»');
is('bullets mixed adds', run(prefixLines, '«- one\ntwo»', '- '), '«- - one\n- two»');
is('bullet at caret moves caret', run(prefixLines, 'on«»e', '- '), '- on«»e');
is('bullet on empty line', run(prefixLines, 'a\n«»', '- '), 'a\n- «»');
is('quote', run(prefixLines, '«a\nb»', '> '), '«> a\n> b»');
is('quote caret off', run(prefixLines, '> a«»b', '> '), 'a«»b');
is('selection ending at newline keeps next line', run(prefixLines, '«a\n»b', '> '), '«> a\n»b');

is('numbers', run(numberLines, '«a\n\nb\nc»'), '«1. a\n\n2. b\n3. c»');
is('numbers off', run(numberLines, '«1. a\n2. b»'), '«a\nb»');

is('heading 1', run(heading, 'ti«»tle', 1), '# ti«»tle');
is('heading 2 replaces 1', run(heading, '# ti«»tle', 2), '## ti«»tle');
is('heading same level off', run(heading, '## ti«»tle', 2), 'ti«»tle');
is('heading 3 lines', run(heading, '«a\nb»', 3), '«### a\n### b»');
is('heading 1 over 2 is not off', run(heading, '«## a»', 1), '«# a»');

is('indent caret', run(indent, 'a«»b'), '  a«»b');
is('indent lines', run(indent, '«a\nb»'), '«  a\n  b»');
is('indent empty line', run(indent, '«»'), '  «»');
is('outdent', run(outdent, '«  a\n b\nc»'), '«a\nb\nc»');
is('outdent caret clamps at line start', run(outdent, '  «»a'), '«»a');
is('outdent keeps a mid-line selection', run(outdent, '  a«b» c'), 'a«b» c');
is('indent keeps a mid-line selection', run(indent, 'a«b» c'), '  a«b» c');
is('outdent tab', run(outdent, '\ta«»'), 'a«»');

is('link wraps selection', run(link, 'see «here» ok', 'https://x.org'), 'see [«here»](https://x.org) ok');
is('link at caret uses filler', run(link, '«»', 'https://x.org'), '[«link text»](https://x.org)');
is('linked text found', linkedText(...at('«[a](https://x.org)»')), 'a');
is('plain text is not a link', linkedText(...at('«a»')), null);
is('unlink', run(unlink, '«[a](https://x.org)»'), '«a»');

is('url kept', cleanUrl(' https://a.org/x?y=1 '), 'https://a.org/x?y=1');
is('bare domain gets https', cleanUrl('a.org/path'), 'https://a.org/path');
is('javascript refused', cleanUrl('javascript:alert(1)'), null);
is('spaces refused', cleanUrl('a b'), null);
is('empty refused', cleanUrl(''), null);

process.stdout.write('mdformat: the post editor toolbar moves against their fixtures\n');
if (failures.length) {
  process.stdout.write(`mdformat: ${failures.length} problem(s)\n`);
  for (const said of failures) process.stdout.write(`  - ${said}\n`);
  process.exit(1);
}
process.stdout.write('mdformat: ok - wrap and toggle, fences, line prefixes, numbers, headings, indent, links\n');
