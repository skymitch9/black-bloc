// The Discord mock, proved without a browser. `site/public/assets/discordmock.js` draws the
// payload `black_bloc/preview.py` answers, so the fixtures below ARE that payload's shape:
// a plain message with a role mention, a go-live embed, and a request card with buttons.
// `messageTree` is pure, so nothing here needs a DOM; `mountTree` is checked against a
// six-line element shim so the one thing that touches nodes is not left unproven.
//
//   node site/mock/discordmock.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.
// scripts/deploy.ps1 and .github/workflows/ci.yml run it beside check.mjs.

import {
  BOT_TAG,
  CAPTION,
  colourOf,
  embedTree,
  fileName,
  messageTree,
  mountTree,
  timeWords,
} from '../public/assets/discordmock.js';

const failures = [];
const fail = (where, said) => failures.push(`${where}: ${said}`);

function is(where, found, wanted) {
  if (found !== wanted) fail(where, `is ${JSON.stringify(found)}, not ${JSON.stringify(wanted)}`);
}

function ok(where, said, truth) {
  if (!truth) fail(where, said);
}

/** Every node of a tree, flat, so a fixture can ask "is there a X anywhere in here". */
function flat(spec, found = []) {
  if (!spec) return found;
  found.push(spec);
  for (const child of spec.children || []) flat(child, found);
  return found;
}

const withClass = (spec, name) => flat(spec).filter((one) => one.class === name);
const oneWithClass = (spec, name) => withClass(spec, name)[0] || null;
const allHtml = (spec) => flat(spec).map((one) => one.html || '').join('\n');
const allText = (spec) => flat(spec).map((one) => one.text || '').join('\n');

// --- the small pure pieces ------------------------------------------------------------------

is('colourOf blurple', colourOf(0x5865f2), '#5865f2');
is('colourOf black', colourOf(0), '#000000');
is('colourOf nothing', colourOf(null), null);
is('colourOf a number Discord could not have sent', colourOf(0x1000000), null);

is('fileName of a Twitch preview', fileName('https://static-cdn.jtvnw.net/x/live_user_a-1280x720.jpg'), 'live_user_a-1280x720.jpg');
is('fileName past a query string', fileName('https://example.com/art.png?size=512'), 'art.png');
is('fileName of nothing', fileName(''), '');

is('timeWords of nothing', timeWords(null), '');
is('timeWords of a bad stamp', timeWords('not a date'), '');
ok('timeWords of now', 'says Today', timeWords(new Date()).startsWith('Today at '));

// --- fixture 1: a plain message that mentions a role ----------------------------------------
{
  const where = 'a plain message with a role mention';
  const tree = messageTree({
    content: '<@&4242> **Casey** is now live! https://twitch.tv/caseyfast',
    embeds: [],
    components: [],
    mentions: { roles: [{ id: '4242', name: 'Stream pings' }], channels: [] },
  }, { when: new Date('2026-09-20T20:03:00Z') });

  is('the caption', oneWithClass(tree, 'dcmock-cap').text, CAPTION);
  is('the BOT tag', oneWithClass(tree, 'dcmock-tag').text, BOT_TAG);
  is('the bot name', oneWithClass(tree, 'dcmock-name').text, 'Black Bloc');
  is('the avatar letter', oneWithClass(tree, 'dcmock-avatar').text, 'B');
  ok(where, 'has no time on the head', oneWithClass(tree, 'dcmock-when').text.length > 0);

  const html = allHtml(tree);
  ok(where, `draws the role as a raw id — got ${html}`, html.includes('@Stream pings'));
  ok(where, 'did not make the mention a pill', html.includes('class="md-mention"'));
  ok(where, 'lost the bold', html.includes('<strong>Casey</strong>'));
  ok(where, 'left the id in the text', !html.includes('&lt;@&amp;4242&gt;'));
  is('no embed is drawn', withClass(tree, 'dcmock-embed').length, 0);
  is('no button row is drawn', withClass(tree, 'dcmock-actions').length, 0);

  // Every style this component ever sets must be a declaration `ui.js:el` can put on the
  // CSSOM — a bare colour or a missing colon would be dropped silently under style-src 'self'.
  for (const one of flat(tree)) {
    if (one.style) ok(where, `style ${JSON.stringify(one.style)} has no property`, one.style.includes(':'));
  }
}

// --- fixture 2: the go-live embed -----------------------------------------------------------
{
  const where = 'the go-live embed';
  const embed = {
    title: 'late night runs',
    url: 'https://twitch.tv/caseyfast',
    color: 0x9146ff,
    description: 'Come and watch',
    author: { name: 'Casey is now live on Twitch!' },
    fields: [{ name: 'Game', value: 'Lethal Company', inline: false }],
    image: { url: 'https://static-cdn.jtvnw.net/previews-ttv/live_user_caseyfast-1280x720.jpg' },
    thumbnail: { url: 'https://example.com/box-art.png' },
    footer: { text: 'Black Bloc · via Twitch' },
    timestamp: '2026-09-20T20:03:00.000Z',
  };
  const tree = embedTree(embed, { roles: [], channels: [], members: [] });

  is('the colour bar', oneWithClass(tree, 'dcmock-embed-bar').style, 'background: #9146ff');
  is('the author line', oneWithClass(tree, 'dcmock-embed-author').children[0].text, 'Casey is now live on Twitch!');
  is('the title', oneWithClass(tree, 'dcmock-embed-title').text, 'late night runs');
  is('a titled embed with a url reads as a link', oneWithClass(tree, 'dcmock-embed-title')['data-link'], 'true');
  is('the field name', oneWithClass(tree, 'dcmock-field-name').text, 'Game');
  is('a non-inline field spans the grid', oneWithClass(tree, 'dcmock-field')['data-inline'], 'false');

  const media = withClass(tree, 'dcmock-media');
  is('both the image and the thumbnail are placed', media.length, 2);
  is('the image placeholder names the file', media[0].children[1].text, 'live_user_caseyfast-1280x720.jpg');
  is('the thumbnail is marked as one', media[1]['data-kind'], 'thumbnail');
  ok(where, 'drops the footer', allText(tree).includes('Black Bloc · via Twitch'));
  ok(where, 'drops the embed stamp', /(Today|Yesterday) at |\//.test(allText(tree)));

  // An embed description renders no `#` headers, the way Discord does not.
  const headed = embedTree({ description: '# not a header', color: null }, { roles: [], channels: [] });
  ok('an embed description', 'turned a # into a header', !allHtml(headed).includes('<h2'));
  is('an embed with no colour gets no bar style', oneWithClass(headed, 'dcmock-embed-bar').style, null);
}

// --- fixture 3: a request card with its buttons ---------------------------------------------
{
  const where = 'a request card with buttons';
  const tree = messageTree({
    content: '',
    embeds: [{ title: 'Request #14', color: 0x5865f2, fields: [] }],
    components: [[
      { label: 'Pick up', style: 'primary', url: null, disabled: false, emoji: null },
      { label: 'Hold', style: 'secondary', url: null, disabled: false, emoji: null },
      { label: 'Decline', style: 'danger', url: null, disabled: false, emoji: null },
    ], [
      { label: 'Open it on the site', style: 'link', url: 'https://example.com/requests#14', disabled: false, emoji: null },
    ]],
    mentions: { roles: [], channels: [] },
  });

  is('two rows of buttons', withClass(tree, 'dcmock-row').length, 2);
  const buttons = withClass(tree, 'dcmock-btn');
  is('four buttons in all', buttons.length, 4);
  is('Pick up is blurple', buttons[0]['data-style'], 'primary');
  is('Hold is grey', buttons[1]['data-style'], 'secondary');
  is('Decline is red', buttons[2]['data-style'], 'danger');
  is('the site button is a link', buttons[3]['data-style'], 'link');
  ok(where, 'the link button has no ↗ mark', allText(buttons[3]).includes('↗'));
  ok(where, 'the link button lost its url', buttons[3].title === 'https://example.com/requests#14');

  const odd = messageTree({ components: [[{ label: 'X', style: 'made-up' }]] });
  is('a style Discord does not have reads as secondary', withClass(odd, 'dcmock-btn')[0]['data-style'], 'secondary');
}

// --- a message with nothing in it says so rather than drawing an empty box -------------------
{
  const tree = messageTree({ content: '', embeds: [], components: [] });
  ok('an empty message', 'draws nothing at all and does not say so', withClass(tree, 'dcmock-nothing').length === 1);
}

// --- mountTree, against a shim, because it is the one part that makes nodes ------------------
{
  const where = 'mountTree';
  const make = (tag, props, children) => {
    const node = {
      tag,
      attrs: {},
      style: {},
      text: '',
      innerHTML: undefined,
      children: children || [],
    };
    for (const [key, value] of Object.entries(props || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === 'text') node.text = String(value);
      else if (key === 'style') {
        for (const rule of String(value).split(';')) {
          const at = rule.indexOf(':');
          if (at > 0) node.style[rule.slice(0, at).trim()] = rule.slice(at + 1).trim();
        }
      } else node.attrs[key] = value;
    }
    return node;
  };

  const node = mountTree(messageTree({
    content: 'hello',
    embeds: [{ color: 0x9146ff, title: 'A card' }],
    components: [[{ label: 'Press me', style: 'primary' }]],
  }), make);

  is('the root', node.attrs.class, 'dcmock');
  const found = [];
  (function walk(one) { found.push(one); (one.children || []).forEach(walk); }(node));
  const bar = found.find((one) => one.attrs.class === 'dcmock-embed-bar');
  is('the bar colour reached the CSSOM and not an attribute', bar.style.background, '#9146ff');
  is('and never became a style attribute', bar.attrs.style, undefined);
  const content = found.find((one) => one.attrs.class === 'dcmock-content');
  ok(where, 'the content html never landed', String(content.innerHTML).includes('hello'));
  is('nothing mounts from nothing', mountTree(null, make), null);
}

if (failures.length) {
  console.error(`discordmock.test.mjs — ${failures.length} failure(s):`);
  for (const one of failures) console.error(`  ${one}`);
  process.exit(1);
}
console.log('discordmock.test.mjs — all fixtures matched.');
