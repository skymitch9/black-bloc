// The paste converter, proved without a browser. `site/public/assets/clipmd.js` takes the
// rich-clipboard HTML a Google Doc puts on the clipboard and answers with the Discord
// markdown the post editor's body box holds — so the first fixture below is a real Docs
// fragment, wrapper `<b style="font-weight:normal">` and all, and the last is an injection.
//
//   node site/mock/clipmd.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.
// scripts/deploy.ps1 and .github/workflows/ci.yml run it beside check.mjs.

import { readFileSync } from 'node:fs';
import { docTitle, htmlToDiscordMarkdown, mentionChannels } from '../public/assets/clipmd.js';

const failures = [];
const fail = (where, said) => failures.push(`${where}: ${said}`);

function is(where, found, wanted) {
  if (found !== wanted) fail(where, `is\n${JSON.stringify(found)}\n      not\n${JSON.stringify(wanted)}`);
}

function has(where, found, wanted) {
  if (!found.includes(wanted)) fail(where, `is missing ${JSON.stringify(wanted)}\n      got: ${JSON.stringify(found)}`);
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

// Changed 2026-09-28 (doc-import-fidelity): this pin used to put a blank line between every
// block. A Doc's blank lines are its own EMPTY paragraphs (posts-doc-import-design.md
// section Fidelity), and this fragment has none, so its blocks now join with one newline.
const DOCS_WANTED = [
  '# Welcome to Black in a Flash',
  'Read the **rules** before you post, and *be kind*.',
  'Questions? [Read the guides](https://blackbloc.heygabi.ai/guides).',
  '- Be excellent',
  '  - to each other',
  '- No spoilers',
  '1. First',
  '2. Second',
].join('\n');

{
  const where = 'a Google Docs fragment';
  const found = htmlToDiscordMarkdown(DOCS);
  is(where, found, DOCS_WANTED);
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
  has(where, htmlToDiscordMarkdown('<div><div><p>nested</p></div></div>'), 'nested');
}

// --- Google Docs' HTML EXPORT (File → Download → Web page; what Import from a Google Doc gets) --
// Hand-built in the export's shape, not captured: marks live in a <style> block of classes and
// `class="c1 c13"` on spans; links are wrapped `https://www.google.com/url?q=<real>&sa=…`; a
// nested bullet is NOT nested — it is a sibling <ul class="lst-kix_…-1">, and a list that is
// interrupted resumes as a new <ol start="3">; the doc's name sits in <head><title>.
const EXPORT_HEAD = '<html><head><meta content="text/html; charset=UTF-8" http-equiv="content-type">'
  + '<style type="text/css">@import url(https://themes.googleusercontent.com/fonts/css?kit=abc);'
  + 'ul.lst-kix_q1w2e3r4t5y6-1{list-style-type:none}.lst-kix_q1w2e3r4t5y6-0 > li:before'
  + '{content:"\\0025cf   "}ol.lst-kix_z9x8c7v6b5n4-0.start{counter-reset:lst-ctn-kix_z9x8c7v6b5n4-0 0}'
  + 'ol{margin:0;padding:0}table td,table th{padding:0}'
  + '.c1{color:#000000;font-weight:400;text-decoration:none;vertical-align:baseline;font-size:11pt;'
  + 'font-family:"Arial";font-style:normal}'
  + '.c2{padding-top:0pt;padding-bottom:0pt;line-height:1.15;orphans:2;widows:2;text-align:left}'
  + '.c3{color:#000000;font-weight:700;text-decoration:none;vertical-align:baseline;font-size:11pt;'
  + 'font-family:"Arial";font-style:normal}'
  + '.c4{color:#000000;font-weight:400;text-decoration:none;vertical-align:baseline;font-size:11pt;'
  + 'font-family:"Arial";font-style:italic}'
  + '.c5{color:#1155cc;font-weight:400;text-decoration:underline;vertical-align:baseline;'
  + 'font-size:11pt;font-family:"Arial";font-style:normal}'
  + '.c6{color:inherit;text-decoration:inherit}.c7{margin-left:36pt;padding-left:0pt}'
  + '.c8{margin-left:72pt;padding-left:0pt}.c9{padding-top:20pt;padding-bottom:6pt;line-height:1.15}'
  + '.c10{color:#000000;font-weight:400;text-decoration:none;font-size:20pt;font-family:"Arial"}'
  + '.c11{background-color:#ffffff;max-width:468pt;padding:72pt 72pt 72pt 72pt}.c12{padding:0;margin:0}'
  + '.c13{font-weight:700}.c14{text-decoration:line-through}.c15{text-decoration:underline}'
  + '.c16{font-family:"Courier New"}.c17{height:11pt}'
  + '.c18{color:#000000;font-weight:400;font-size:26pt;font-family:"Arial"}'
  + '.c19{color:#000000;font-weight:400;font-size:16pt;font-family:"Arial"}'
  + '.c20{color:#434343;font-weight:400;font-size:14pt;font-family:"Arial"}'
  + '.title{padding-top:0pt;color:#000000;font-size:26pt;padding-bottom:3pt;font-family:"Arial"}'
  + '.subtitle{padding-top:0pt;color:#666666;font-size:15pt;padding-bottom:16pt;font-family:"Arial"}'
  + 'li{color:#000000;font-size:11pt;font-family:"Arial"}'
  + 'p{margin:0;color:#000000;font-size:11pt;font-family:"Arial"}'
  + 'h1{padding-top:20pt;color:#000000;font-size:20pt;padding-bottom:6pt;font-family:"Arial"}'
  + '</style><title>Secret head title</title></head><body class="c11 doc-content">';
const EXPORT_FOOT = '</body></html>';
const GURL = (real) => `https://www.google.com/url?q=${real}&amp;sa=D&amp;source=editors`
  + '&amp;ust=1759100000000000&amp;usg=AOvVaw0abcdefghijklmnop';

// The SAME document as DOCS above, as the export writes it.
const EXPORT_DOCS = EXPORT_HEAD
  + '<h1 class="c9" id="h.abc123"><span class="c10">Welcome to Black in a Flash</span></h1>'
  + '<p class="c2"><span class="c1">Read the </span><span class="c3">rules</span>'
  + '<span class="c1"> before you post, and </span><span class="c4">be kind</span>'
  + '<span class="c1">.</span></p>'
  + '<p class="c2"><span class="c1">Questions?&nbsp;</span><span class="c5">'
  + `<a class="c6" href="${GURL('https://blackbloc.heygabi.ai/guides')}">Read the guides</a>`
  + '</span><span class="c1">.</span></p>'
  + '<ul class="c12 lst-kix_q1w2e3r4t5y6-0 start"><li class="c2 c7 li-bullet-0">'
  + '<span class="c1">Be excellent</span></li></ul>'
  + '<ul class="c12 lst-kix_q1w2e3r4t5y6-1 start"><li class="c2 c8 li-bullet-1">'
  + '<span class="c1">to each other</span></li></ul>'
  + '<ul class="c12 lst-kix_q1w2e3r4t5y6-0"><li class="c2 c7 li-bullet-0">'
  + '<span class="c1">No spoilers</span></li></ul>'
  + '<ol class="c12 lst-kix_z9x8c7v6b5n4-0 start" start="1">'
  + '<li class="c2 c7 li-bullet-0"><span class="c1">First</span></li>'
  + '<li class="c2 c7 li-bullet-0"><span class="c1">Second</span></li></ol>'
  + EXPORT_FOOT;

{
  const where = 'one document, pasted and exported';
  is(where, htmlToDiscordMarkdown(EXPORT_DOCS), DOCS_WANTED);
  is(where, htmlToDiscordMarkdown(EXPORT_DOCS), htmlToDiscordMarkdown(DOCS));
}

// Everything else the export does: title and subtitle paragraphs, h2/h3, marks by class where
// the LATER rule wins (CSS order, not attribute order), <br>, empty paragraphs, a wrapped link
// whose real address is percent-encoded, a wrapper hiding a javascript: link, and a numbered
// list that resumes at start="3" after a nested bullet.
const EXPORT_MORE = EXPORT_HEAD
  + '<p class="c2 title" id="h.t1"><span class="c18">Welcome</span></p>'
  + '<p class="c2 subtitle" id="h.s1"><span class="c1">A short subtitle</span></p>'
  + '<p class="c2 c17"><span class="c1"></span></p>'
  + '<h2 class="c9" id="h.h2"><span class="c19">Section</span></h2>'
  + '<h3 class="c9" id="h.h3"><span class="c20">Smaller</span></h3>'
  + '<p class="c2"><span class="c1 c13">bold</span><span class="c1"> and </span>'
  + '<span class="c1 c14">gone</span><span class="c1"> and </span>'
  + '<span class="c15 c1">under</span><span class="c1"> and </span>'
  + '<span class="c1 c16">code</span></p>'
  + '<p class="c2 c17"><span class="c1"></span></p><p class="c2 c17"><span class="c1"></span></p>'
  + '<p class="c2"><span class="c1">line one<br>line two</span></p>'
  + '<p class="c2"><span class="c5">'
  + `<a class="c6" href="${GURL('https://example.com/a?b%3D1%26c%3D2')}">the page</a></span>`
  + '<span class="c1"> and </span><span class="c5">'
  + '<a class="c6" href="https://www.google.com/url?q=javascript:void0&amp;sa=D">odd</a></span></p>'
  + '<ol class="c12 lst-kix_z9x8c7v6b5n4-0 start" start="1">'
  + '<li class="c2 c7 li-bullet-0"><span class="c1">One</span></li>'
  + '<li class="c2 c7 li-bullet-0"><span class="c1">Two</span></li></ol>'
  + '<ul class="c12 lst-kix_z9x8c7v6b5n4-1 start"><li class="c2 c8 li-bullet-1">'
  + '<span class="c1">sub</span></li></ul>'
  + '<ol class="c12 lst-kix_z9x8c7v6b5n4-0" start="3">'
  + '<li class="c2 c7 li-bullet-0"><span class="c1">Three</span></li></ol>'
  + EXPORT_FOOT;

// Changed 2026-09-28 (doc-import-fidelity), three ways: blank lines now come only from the
// export's empty paragraphs (after the subtitle, after the marks line - two collapse to one);
// the subtitle's words are 11pt (class c1), so it reads as body text and is no longer `## `
// (a 15pt subtitle is pinned below); and `- sub` sits under `2. ` at column 3, not 2.
const EXPORT_MORE_WANTED = [
  '# Welcome',
  'A short subtitle',
  '',
  '## Section',
  '### Smaller',
  '**bold** and ~~gone~~ and __under__ and `code`',
  '',
  'line one',
  'line two',
  '[the page](https://example.com/a?b=1&c=2) and '
    + '[odd](https://www.google.com/url?q=javascript:void0&sa=D)',
  '1. One',
  '2. Two',
  '   - sub',
  '3. Three',
].join('\n');

{
  const where = 'a Google Docs export';
  const found = htmlToDiscordMarkdown(EXPORT_MORE);
  is(where, found, EXPORT_MORE_WANTED);
  if (found.includes('Secret head title')) fail(where, 'the <head> title leaked into the body');
  if (found.includes('lst-kix') || found.includes('font-weight')) fail(where, 'CSS leaked into the body');
}

// A class the stylesheet never defines is ignored; an inline style still beats a class.
{
  const where = 'classes against inline styles';
  const sheet = '<style>.b{font-weight:700}.n{font-weight:400}</style>';
  is(where, htmlToDiscordMarkdown(`${sheet}<p><span class="b">A</span> <span class="nope">B</span></p>`),
    '**A** B');
  is(where, htmlToDiscordMarkdown(`${sheet}<p><span class="b" style="font-weight:400">A</span></p>`), 'A');
  is(where, htmlToDiscordMarkdown(`${sheet}<p><span class="n b">A</span></p>`), 'A');
  is(where, htmlToDiscordMarkdown('<style>p.b{font-weight:700}</style><p class="b">A</p>'), 'A');
}

// A bullet nested under a number stays in the list: no blank line where the depth changes.
// Changed 2026-09-28 (doc-import-fidelity): the sub-list sits at the number's content column
// (3 spaces under `1. `), not 2 - Discord does not nest a 2-space item under a number.
{
  const where = 'a mixed nested list';
  is(where, htmlToDiscordMarkdown('<ol><li>One<ul><li>sub</li></ul></li><li>Two</li></ol>'),
    '1. One\n   - sub\n2. Two');
}

// --- doc-import-fidelity: one pin per rule the welcome post's Doc needed -------------------
const FID_SHEET = '<style>.s12{font-size:12pt}.s18{font-size:18pt}.s11{font-size:11pt}'
  + '.b{font-weight:700}.bu{font-weight:700;text-decoration:underline}.s15{font-size:15pt}</style>';
const FID = (body) => `<html><head>${FID_SHEET}</head><body class="doc-content">${body}</body></html>`;

{
  const where = 'fidelity 1: a body-sized heading is a paragraph';
  is(where, htmlToDiscordMarkdown(FID('<h1><span class="s12">Looks like body</span></h1>')),
    'Looks like body');
  is(where, htmlToDiscordMarkdown(FID('<h1><span class="b">Real heading</span></h1>')), '# Real heading');
  is(where, htmlToDiscordMarkdown(FID('<h2><span class="s18">Big enough</span></h2>')), '## Big enough');
  is(where, htmlToDiscordMarkdown(FID('<h1><span style="font-size:13pt">Inline small</span></h1>')),
    'Inline small');
  is(where, htmlToDiscordMarkdown(FID('<h1><span class="s12">half</span><span> not</span></h1>')),
    '# half not');
  is(where, htmlToDiscordMarkdown(FID('<p class="subtitle"><span class="s15">Sub</span></p>')), '## Sub');
  is(where, htmlToDiscordMarkdown(FID('<p class="title"><span class="s11">Plain</span></p>')), 'Plain');
}

{
  const where = 'fidelity 2: bold inside a demoted heading';
  is(where, htmlToDiscordMarkdown(FID('<h1><span class="s12">Welcome to</span>'
    + '<span class="b s12">&nbsp;Black in a Flash</span><span class="s12">, hi.</span></h1>')),
  'Welcome to **Black in a Flash**, hi.');
}

{
  const where = 'fidelity 3: nested lists at the parent content column';
  const ol = (level, start, words) => `<ol class="lst-kix_ab-${level}" start="${start}">`
    + words.map((one) => `<li><span>${one}</span></li>`).join('') + '</ol>';
  is(where, htmlToDiscordMarkdown(FID(ol(0, 9, ['nine', 'ten']) + ol(1, 1, ['sub']) + ol(2, 1, ['deep']))),
    '9. nine\n10. ten\n    1. sub\n       1. deep');
  is(where, htmlToDiscordMarkdown(FID('<ul class="lst-kix_cd-0"><li>a</li></ul>'
    + '<ul class="lst-kix_cd-1"><li>b</li></ul><ul class="lst-kix_cd-2"><li>c</li></ul>')),
  '- a\n  - b\n    - c');
  is(where, htmlToDiscordMarkdown('<ul><li>a<ul><li>b</li></ul></li></ul>'), '- a\n  - b');
}

{
  const where = 'fidelity 4: a heading inside a list item stays list text';
  is(where, htmlToDiscordMarkdown(FID('<ol class="lst-kix_ef-0" start="6"><li><span class="b">Six</span></li></ol>'
    + '<ol class="lst-kix_ef-1" start="1"><li><h1 style="display:inline">'
    + '<span class="s12">If you cannot abide</span></h1></li></ol>')),
  '6. **Six**\n   1. If you cannot abide');
  is(where, htmlToDiscordMarkdown(FID('<ul><li><h1 style="display:inline"><span class="s18">Big</span></h1></li></ul>')),
    '- Big');
}

{
  const where = 'fidelity 5: blank lines only from empty paragraphs';
  const empty = '<p class="c5"><span class="s11"></span></p>';
  is(where, htmlToDiscordMarkdown(FID(`<p>one</p><p>two</p>${empty}${empty}${empty}<p>three </p>`)),
    'one\ntwo\n\nthree');
  is(where, htmlToDiscordMarkdown(FID('<p><span class="b">Head </span></p><ul class="lst-kix_gh-0"><li>x</li></ul><p>after</p>')),
    '**Head**\n- x\n\nafter');
  is(where, htmlToDiscordMarkdown(FID('<h1><span><br></span></h1><p>first</p>')), 'first');
  is(where, htmlToDiscordMarkdown(FID('<div><p>a</p></div><div><p>b</p></div>')), 'a\nb');
  is(where, htmlToDiscordMarkdown('<b style="font-weight:normal" id="docs-internal-guid-1"><p>a</p><br><p>b</p><p>c</p></b>'),
    'a\n\nb\nc');
  is(where, htmlToDiscordMarkdown('<p>web</p><p>page</p>'), 'web\n\npage');
}

{
  const where = 'fidelity 6: bold AND underline stays faithful';
  is(where, htmlToDiscordMarkdown(FID('<p><span class="s12 bu">Banworthy Offenses </span></p>')),
    '__**Banworthy Offenses**__');
}

{
  const where = 'fidelity 7: channel names become mentions';
  const map = { 'off-topic': '11', general: '22' };
  is(where, mentionChannels('in #off-topic. and #general', map), 'in <#11>. and <#22>');
  is(where, mentionChannels('in #off-topic-2 and #nope', map), 'in #off-topic-2 and #nope');
  is(where, mentionChannels('see https://x.com/#general and a#general', map),
    'see https://x.com/#general and a#general');
  is(where, mentionChannels('`#general` and ```\n#general\n``` but #general', map),
    '`#general` and ```\n#general\n``` but <#22>');
  is(where, mentionChannels('# Heading and ## two', map), '# Heading and ## two');
  is(where, mentionChannels('(#general)', [{ id: '22', name: 'general' }]), '(<#22>)');
  is(where, mentionChannels('#General', map), '#General');
  is(where, mentionChannels('#general', []), '#general');
}

// The paste path gets the unwrapping too: a Docs link copied from a published page.
{
  const where = 'a wrapped link in a paste';
  is(where, htmlToDiscordMarkdown(
    `<p><a href="${GURL('https://example.com/x')}">https://example.com/x</a></p>`,
  ), 'https://example.com/x');
}

// docTitle: the export's <title>, else the first Title line, else the first real h1-h3, else ''.
{
  const where = 'docTitle';
  const RULES = readFileSync(new URL('./fixtures/rules-export.html', import.meta.url), 'utf8');
  const shell = (head, body) => `<html><head>${head}<style>.c1{font-size:11pt}.c2{font-size:20pt}</style>`
    + `</head><body class="doc-content">${body}</body></html>`;
  is(`${where} (the rules export: no title, its first real heading)`, docTitle(RULES),
    'Current Rules (Do Not Edit this page is reference)');
  is(`${where} (the export's own title wins)`, docTitle(shell(
    '<title> Server &amp; Rules </title>',
    '<p class="title"><span>A Title line</span></p><h1><span class="c2">A heading</span></h1>',
  )), 'Server & Rules');
  is(`${where} (an empty title, then the Title line before an earlier heading)`, docTitle(shell(
    '<title></title>',
    '<h1><span class="c2">A heading</span></h1><p class="c4 title"><span class="c1">The   Title</span></p>',
  )), 'The Title');
  is(`${where} (a body-sized heading is not a title)`, docTitle(shell(
    '<title></title>',
    '<h1><span class="c1">Body words set as a heading</span></h1><p><span>x</span></p>'
      + '<h2><span class="c2">The real one</span></h2>',
  )), 'The real one');
  is(`${where} (a subtitle and an h4 are not titles)`, docTitle(shell(
    '',
    '<p class="subtitle"><span class="c2">Sub</span></p><h4><span class="c2">Four</span></h4>',
  )), '');
  is(`${where} (no title and no heading)`, docTitle(shell(
    '<title>  </title>',
    '<p class="c5"><span class="c1"></span></p><p><span class="c1">Just words.</span></p>',
  )), '');
  is(`${where} (nothing at all)`, docTitle(''), '');
  is(`${where} (null)`, docTitle(null), '');
}

process.stdout.write('clipmd: the paste converter against its fixtures\n');
if (failures.length) {
  process.stdout.write(`clipmd: ${failures.length} problem(s)\n`);
  for (const said of failures) process.stdout.write(`  - ${said}\n`);
  process.exit(1);
}
process.stdout.write(
  "clipmd: ok - a Google Docs fragment arrives as headings, bold, italic, nested bullets, "
    + 'numbers and a masked link; the same doc from the export converts the same; a plain '
    + 'fragment is unchanged; script and style are dropped\n',
);
