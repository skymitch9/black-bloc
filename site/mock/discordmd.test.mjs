// The preview renderer, proved without a browser. `site/public/assets/discordmd.js` is the
// only markdown this site has, and it draws text staff typed — so the first fixture below is
// an injection, and the rest are the shapes Carl's welcome post is actually made of.
//
//   node site/mock/discordmd.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.
// scripts/deploy.ps1 and .github/workflows/ci.yml run it beside check.mjs.

import { readFile } from 'node:fs/promises';
import { escapeHtml, renderDiscord, renderPreview } from '../public/assets/discordmd.js';

const failures = [];
const fail = (where, said) => failures.push(`${where}: ${said}`);

function has(where, html, wanted) {
  if (!html.includes(wanted)) fail(where, `is missing ${JSON.stringify(wanted)}\n      got: ${html}`);
}

function hasNot(where, html, unwanted) {
  if (html.includes(unwanted)) fail(where, `still holds ${JSON.stringify(unwanted)}\n      got: ${html}`);
}

function is(where, found, wanted) {
  if (found !== wanted) fail(where, `is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
}

// --- the injection fixture. This is the reason the file escapes before it does anything ----
{
  const where = 'injection';
  const html = renderDiscord('<img src=x onerror=alert(1)> and **bold**');
  // The words survive as WORDS; what must not survive is the tag they were wrapped in.
  hasNot(where, html, '<img');
  has(where, html, '&lt;img src=x onerror=alert(1)&gt;');
  has(where, html, '<strong>bold</strong>');
}

{
  const where = 'injection in a masked link';
  const html = renderDiscord('[<script>x</script>](https://example.com/"onmouseover="y)');
  hasNot(where, html, '<script>');
  hasNot(where, html, '"onmouseover="');
  has(where, html, '&lt;script&gt;');
}

{
  const where = 'injection in a title and a quote';
  const html = renderDiscord('> </blockquote><img src=x onerror=1>');
  hasNot(where, html, '<img');
  has(where, html, '&lt;/blockquote&gt;');
}

is('escapeHtml', escapeHtml(`<&>"'`), '&lt;&amp;&gt;&quot;&#39;');
is('escapeHtml of nothing', escapeHtml(null), '');

// --- Carl's own welcome text, read from the seed the bot ships ------------------------------
{
  const where = 'the seed';
  const seed = JSON.parse(await readFile(new URL('../../black_bloc/posts_seed.json', import.meta.url), 'utf8'));
  const post = seed.posts[0];
  const html = renderDiscord(post.body, { style: post.style });
  has(where, html, '<h2 class="md-h1">Familiarize yourselves with the rules before you join the discord.</h2>');
  has(where, html, '<blockquote class="md-quote">');
  has(where, html, '<strong><em>1. The moderation team reserve the right to remove anyone from the space.</em></strong>');
  has(where, html, '<strong>Failure to comply with the rules may lead to moderator action.</strong>');
  // Carl's own `Welcome to** Black` spacing is kept, and Discord bolds it — so this does too.
  has(where, html, '<strong> Black in a Flash</strong>');
  hasNot(where, html, '<script');
  if ((html.match(/<blockquote/g) || []).length !== 3) {
    fail(where, `drew ${(html.match(/<blockquote/g) || []).length} quotes, not the seed's 3`);
  }

  // The same text as an EMBED renders no `#` header — Discord does not draw one there.
  const embed = renderDiscord(post.body, { style: 'embed' });
  hasNot(where, embed, '<h2 class="md-h1">');
  has(where, embed, '# Familiarize yourselves with the rules');
  has(where, embed, '<blockquote class="md-quote">');
}

// --- mentions resolve through the cached /api/ref/* lists -----------------------------------
{
  const where = 'mentions';
  const refs = {
    channels: [{ id: '800000000000000001', name: 'welcome' }],
    roles: [{ id: '900000000000000001', name: 'Aunties / Uncles' }],
    members: [{ id: '700000000000000002', name: 'caseyfast', display_name: 'Casey' }],
  };
  const html = renderDiscord(
    'Head to <#800000000000000001>, ping <@&900000000000000001>, ask <@700000000000000002>.',
    refs,
  );
  has(where, html, '<span class="md-mention">#welcome</span>');
  has(where, html, '<span class="md-mention">@Aunties / Uncles</span>');
  has(where, html, '<span class="md-mention">@Casey</span>');

  const gone = renderDiscord('<#111> <@&222> <@333>', refs);
  has(where, gone, '<span class="md-mention">#deleted-channel</span>');
  if ((gone.match(/@unknown/g) || []).length !== 2) {
    fail(where, `an unknown role and an unknown member did not both read @unknown: ${gone}`);
  }

  const emoji = renderDiscord('<:blackbloc:123> <a:spin:456>', refs);
  has(where, emoji, '<span class="md-emoji">:blackbloc:</span>');
  has(where, emoji, '<span class="md-emoji">:spin:</span>');
}

// --- a link is never clickable --------------------------------------------------------------
{
  const where = 'links';
  const html = renderDiscord('See [the rules](https://example.com/rules) and https://example.com/x');
  hasNot(where, html, '<a ');
  hasNot(where, html, 'href=');
  has(where, html, '<span class="md-link" title="https://example.com/rules">the rules</span>');
  has(where, html, '<span class="md-link">https://example.com/x</span>');
}

// --- the rest of the syntax ------------------------------------------------------------------
{
  const where = 'spans';
  const html = renderDiscord('||secret|| __under__ ~~gone~~ *lean* `code`');
  has(where, html, '<span class="md-spoiler">secret</span>');
  has(where, html, '<u>under</u>');
  has(where, html, '<s>gone</s>');
  has(where, html, '<em>lean</em>');
  has(where, html, '<code class="md-inline">code</code>');
}

{
  const where = 'blocks';
  const html = renderDiscord('# One\n## Two\n### Three\n-# small\n- a\n- b\n1. first\n2. second');
  has(where, html, '<h2 class="md-h1">One</h2>');
  has(where, html, '<h3 class="md-h2">Two</h3>');
  has(where, html, '<h4 class="md-h3">Three</h4>');
  has(where, html, '<p class="md-subtext">small</p>');
  has(where, html, '<ul class="md-list"><li>a</li><li>b</li></ul>');
  has(where, html, '<ol class="md-list"><li>first</li><li>second</li></ol>');
}

{
  const where = 'fenced code';
  const html = renderDiscord('```js\nconst x = "<b>";\n```');
  has(where, html, '<pre class="md-code">const x = &quot;&lt;b&gt;&quot;;\n</pre>');
  hasNot(where, html, '<b>');
}

{
  const where = 'a >>> quote takes the rest';
  const html = renderDiscord('before\n>>> one\ntwo');
  has(where, html, '<p>before</p>');
  has(where, html, '<blockquote class="md-quote"><p>one<br>two</p></blockquote>');
}

{
  const where = 'unknown syntax stays literal';
  const html = renderDiscord('2 * 3 * 4 and a_b_c and <not a tag>');
  has(where, html, '&lt;not a tag&gt;');
  has(where, html, 'a_b_c');
}

{
  const where = 'the embed box';
  const plain = renderPreview('hello', { style: 'plain' });
  has(where, plain, '<div class="md-plain">');
  hasNot(where, plain, 'md-embed');
  const embed = renderPreview('hello', { style: 'embed', title: 'A <title>' });
  has(where, embed, '<div class="md-embed">');
  has(where, embed, '<div class="md-embed-title">A &lt;title&gt;</div>');
  hasNot(where, embed, '<title>');
}

process.stdout.write('discordmd: the preview renderer against its fixtures\n');
if (failures.length) {
  process.stdout.write(`discordmd: ${failures.length} problem(s)\n`);
  for (const said of failures) process.stdout.write(`  - ${said}\n`);
  process.exit(1);
}
process.stdout.write(
  'discordmd: ok - injection renders as text, links are never anchors, the seed draws its '
    + 'header and 3 quotes, and an embed draws no header\n',
);
