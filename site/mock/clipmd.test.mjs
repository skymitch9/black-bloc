// The paste converter, proved without a browser. `site/public/assets/clipmd.js` takes the
// rich-clipboard HTML a Google Doc puts on the clipboard and answers with the Discord
// markdown the post editor's body box holds — so the first fixture below is a real Docs
// fragment, wrapper `<b style="font-weight:normal">` and all, and the last is an injection.
//
//   node site/mock/clipmd.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.
// scripts/deploy.ps1 and .github/workflows/ci.yml run it beside check.mjs.

import { htmlToDiscordMarkdown } from '../public/assets/clipmd.js';

const failures = [];
const fail = (where, said) => failures.push(`${where}: ${said}`);

function is(where, found, wanted) {
  if (found !== wanted) fail(where, `is\n${JSON.stringify(found)}\n      not\n${JSON.stringify(wanted)}`);
}

function has(where, found, wanted) {
  if (!found.includes(wanted)) fail(where, `is missing ${JSON.stringify(wanted)}\n      got: ${JSON.stringify(found)}`);
}

function hasNot(where, found, unwanted) {
  if (found.includes(unwanted)) fail(where, `still holds ${JSON.stringify(unwanted)}\n      got: ${JSON.stringify(found)}`);
}

// --- a Google Docs fragment: a heading, bold, italic, a link, a nested bullet, numbers -----
// Docs wraps the whole selection in <b style="font-weight:normal" id="docs-internal-guid-…">,
// puts font-weight:400 on ordinary words, styles its own links with text-decoration:underline,
// and wraps every <li>'s words in a <p>. All four are the reason this fixture is verbatim.
const DOCS = '<meta charset="utf-8">'
  + '<b style="font-weight:normal;" id="docs-internal-guid-9f3c1a20-7fff-0000-abcd">'
  + '<h1 dir="ltr" style="line-height:1.38;margin-top:20pt;margin-bottom:6pt;">'
  + '<span style="font-size:20pt;font-family:Arial;color:#000000;font-weight:400;">'
  + 'Welcome to Black in a Flash</span></h1>'
  + '<p dir="ltr" style="line-height:1.38;"><span style="font-size:11pt;font-weight:400;">'
  + 'Read the </span><span style="font-size:11pt;font-weight:700;">rules</span>'
  + '<span style="font-size:11pt;font-weight:400;"> before you post, and </span>'
  + '<span style="font-size:11pt;font-style:italic;font-weight:400;">be kind</span>'
  + '<span style="font-size:11pt;font-weight:400;">.</span></p>'
  + '<p dir="ltr"><span style="font-size:11pt;font-weight:400;">Questions?&nbsp;</span>'
  + '<a href="https://blackbloc.heygabi.ai/guides">'
  + '<span style="font-size:11pt;text-decoration:underline;color:#1155cc;font-weight:400;">'
  + 'Read the guides</span></a><span style="font-size:11pt;font-weight:400;">.</span></p>'
  + '<ul style="margin-top:0;margin-bottom:0;padding-inline-start:48px;">'
  + '<li dir="ltr" style="list-style-type:disc;font-size:11pt;">'
  + '<p dir="ltr" style="line-height:1.38;margin-top:0;margin-bottom:0;">'
  + '<span style="font-size:11pt;font-weight:400;">Be excellent</span></p>'
  + '<ul style="margin-top:0;margin-bottom:0;"><li dir="ltr" style="list-style-type:circle;">'
  + '<p dir="ltr"><span style="font-size:11pt;font-weight:400;">to each other</span></p>'
  + '</li></ul></li>'
  + '<li dir="ltr" style="list-style-type:disc;"><p dir="ltr">'
  + '<span style="font-size:11pt;font-weight:400;">No spoilers</span></p></li></ul>'
  + '<ol style="margin-top:0;margin-bottom:0;"><li dir="ltr"><p dir="ltr">'
  + '<span style="font-size:11pt;font-weight:400;">First</span></p></li>'
  + '<li dir="ltr"><p dir="ltr">'
  + '<span style="font-size:11pt;font-weight:400;">Second</span></p></li></ol></b>';

const DOCS_WANTED = [
  '# Welcome to Black in a Flash',
  '',
  'Read the **rules** before you post, and *be kind*.',
  '',
  'Questions? [Read the guides](https://blackbloc.heygabi.ai/guides).',
  '',
  '- Be excellent',
  '  - to each other',
  '- No spoilers',
  '',
  '1. First',
  '2. Second',
].join('\n');

{
  const where = 'a Google Docs fragment';
  const found = htmlToDiscordMarkdown(DOCS);
  is(where, found, DOCS_WANTED);
  // The wrapper <b> must not bold the document, and the link's own underline is not the
  // author's underline. Both are asserted by the exact match above; these name them.
  hasNot(where, found, '**Welcome');
  hasNot(where, found, '__');
}

// --- nothing rich in it: the words come back as they went in -------------------------------
{
  const where = 'a plain fragment';
  is(where, htmlToDiscordMarkdown('Just some plain words.'), 'Just some plain words.');
  is(where, htmlToDiscordMarkdown('<span>Just some plain words.</span>'), 'Just some plain words.');
  is(where, htmlToDiscordMarkdown(''), '');
  is(where, htmlToDiscordMarkdown(null), '');
  is(where, htmlToDiscordMarkdown('<p>One.</p><p>Two.</p>'), 'One.\n\nTwo.');
}

// --- a <script> or a <style> in the fragment goes, and takes its contents with it ----------
{
  const where = 'script and style';
  const found = htmlToDiscordMarkdown(
    '<style>p{color:red}</style><p>Before<script>alert(1)</script> and after</p>'
      + '<style type="text/css">.c1 { font-weight: 700 }</style>',
  );
  is(where, found, 'Before and after');
  hasNot(where, found, 'alert');
  hasNot(where, found, 'color:red');
  hasNot(where, found, 'font-weight');
}

{
  const where = 'markup that is not a tag';
  const found = htmlToDiscordMarkdown('<p>2 &lt; 3 &amp; 4 &gt; 1</p>');
  is(where, found, '2 < 3 & 4 > 1');
}

// --- the rest of the marks -----------------------------------------------------------------
{
  const where = 'the marks';
  is(where, htmlToDiscordMarkdown('<p><u>up</u> <s>gone</s> <code>x=1</code></p>'),
    '__up__ ~~gone~~ `x=1`');
  is(where, htmlToDiscordMarkdown('<p><span style="text-decoration:line-through">gone</span></p>'),
    '~~gone~~');
  is(where, htmlToDiscordMarkdown('<p><span style="font-family:Consolas,monospace">x=1</span></p>'),
    '`x=1`');
  is(where, htmlToDiscordMarkdown('<p><b><i>both</i></b></p>'), '***both***');
  is(where, htmlToDiscordMarkdown('<p>a<br>b</p>'), 'a\nb');
}

// --- links ----------------------------------------------------------------------------------
{
  const where = 'links';
  is(where, htmlToDiscordMarkdown('<p><a href="https://example.com/x">https://example.com/x</a></p>'),
    'https://example.com/x');
  is(where, htmlToDiscordMarkdown('<p><a href="https://example.com/x">example.com/x</a></p>'),
    'https://example.com/x');
  is(where, htmlToDiscordMarkdown('<p><a href="https://example.com/x">the page</a></p>'),
    '[the page](https://example.com/x)');
  is(where, htmlToDiscordMarkdown('<p>See <a href="javascript:alert(1)">this</a>.</p>'), 'See this.');
}

// --- a heading Docs wrote as a styled paragraph rather than an <h1> --------------------------
{
  const where = 'a styled paragraph heading';
  is(where, htmlToDiscordMarkdown('<p><span style="font-size:20pt">Big</span></p>'), '# Big');
  is(where, htmlToDiscordMarkdown('<p><span style="font-size:16pt;font-weight:700">Mid</span></p>'),
    '## Mid');
  is(where, htmlToDiscordMarkdown('<p><span style="font-size:14pt">Small</span></p>'), '### Small');
  is(where, htmlToDiscordMarkdown('<p><span style="font-size:11pt">Body</span></p>'), 'Body');
  is(where, htmlToDiscordMarkdown('<p class="MsoHeading2">Worded</p>'), '## Worded');
  is(where, htmlToDiscordMarkdown('<div role="heading" aria-level="1">Roled</div>'), '# Roled');
}

// --- whitespace: collapsed, never trailing, never three newlines in a row --------------------
{
  const where = 'whitespace';
  const found = htmlToDiscordMarkdown(
    '<p>  lots    of\n\n   space   </p><p>&nbsp;</p><p></p><p>then this</p>',
  );
  is(where, found, 'lots of space\n\nthen this');
  hasNot(where, found, '\n\n\n');
  has(where, htmlToDiscordMarkdown('<div><div><p>nested</p></div></div>'), 'nested');
}

process.stdout.write('clipmd: the paste converter against its fixtures\n');
if (failures.length) {
  process.stdout.write(`clipmd: ${failures.length} problem(s)\n`);
  for (const said of failures) process.stdout.write(`  - ${said}\n`);
  process.exit(1);
}
process.stdout.write(
  "clipmd: ok - a Google Docs fragment arrives as headings, bold, italic, nested bullets, "
    + 'numbers and a masked link; a plain fragment is unchanged; script and style are dropped\n',
);
