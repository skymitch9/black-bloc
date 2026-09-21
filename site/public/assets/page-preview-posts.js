import { start } from './app.js';
import {
  ago,
  badge,
  bar,
  button,
  card,
  channelLabel,
  el,
  field,
  foldout,
  icon,
  notice,
  openDrawer,
  sayNothing,
  searchField,
  section,
  table,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

const DATA = {
  "posts": [
    {
      "id": "1",
      "slug": "welcome",
      "title": "Welcome and rules",
      "body": "Welcome to** Black in a Flash**, a dedicated space for Black gamers!  While we appreciate and see multiple teams around the content creation space we don't see one that is just for us, and that is what this Discord hopes to alleviate: the creation of a space where we can authentically and openly be ourselves.\n# Familiarize yourselves with the rules before you join the discord.\n**Failure to comply with the rules may lead to moderator action.**\n\n***1. The moderation team reserve the right to remove anyone from the space.***\n> If you cannot abide the rules or plainly speaking are not a good fit for the space, the moderators can remove you at will.\n\n***2. Be respectful of others.***\n> We will not tolerate any forms of harassment or bigotry, such as- but not limited to- harassment about race, gender/identity expression, sexual orientation, religion, disability, physical appearances. There's a line between a friendly roast and being a jerk.\n\n***3. First and foremost, this space is to adapt, learn, and grow.***\n> Let's try to keep that as the primary focus. It's okay to have off topic conversations or to be upset about things, but this is a space to empower ourselves. If you are going to detract from the experience of others, there may be moderator intervention.\n\nYou can head to the landing channel and type a message so you gain access to the rest of the discord. If you are unsure of something, you are welcome to ping the Aunties / Uncles role.",
      "style": "plain",
      "cap": 2000,
      "title_cap": 256,
      "pin": true,
      "channel_id": "800000000000000001",
      "channel_name": "welcome",
      "posted": false,
      "posted_where": null,
      "pinned": false,
      "changes_pending": false,
      "status": [
        "not posted"
      ],
      "move": "Post it",
      "message_id": null,
      "shadow_message_id": null,
      "posted_at": null,
      "posted_by": null,
      "posted_by_name": null,
      "seeded": true,
      "updated_at": "2026-09-20T15:35:42.365Z",
      "updated_by": null,
      "updated_by_name": null
    },
    {
      "id": "2",
      "slug": "opening-hours",
      "title": "When staff are around",
      "body": "**Staff hours**\n> Somebody is usually around between 6pm and 11pm Phoenix time.\n> Outside that, open a modmail and it is answered in the morning.",
      "style": "embed",
      "cap": 4096,
      "title_cap": 256,
      "pin": false,
      "channel_id": "800000000000000003",
      "channel_name": "blackbloc-logs",
      "posted": true,
      "posted_where": "channel",
      "pinned": false,
      "changes_pending": true,
      "status": [
        "posted",
        "changes not yet posted"
      ],
      "move": "Update the post",
      "message_id": "810000000000000004",
      "shadow_message_id": null,
      "posted_at": "2026-09-20T18:55:42.365Z",
      "posted_by": "700000000000000001",
      "posted_by_name": "Nick",
      "seeded": false,
      "updated_at": "2026-09-20T22:25:42.365Z",
      "updated_by": "700000000000000001",
      "updated_by_name": "Nick"
    },
    {
      "id": "3",
      "slug": "scratch-post",
      "title": "A post staff wrote here",
      "body": "",
      "style": "plain",
      "cap": 2000,
      "title_cap": 256,
      "pin": true,
      "channel_id": null,
      "channel_name": null,
      "posted": false,
      "posted_where": null,
      "pinned": false,
      "changes_pending": false,
      "status": [
        "not posted"
      ],
      "move": "Post it",
      "message_id": null,
      "shadow_message_id": null,
      "posted_at": null,
      "posted_by": null,
      "posted_by_name": null,
      "seeded": false,
      "updated_at": "2026-09-20T23:35:42.365Z",
      "updated_by": "700000000000000001",
      "updated_by_name": "Nick"
    }
  ],
  "mode": "shadow",
  "styles": [
    {
      "style": "plain",
      "cap": 2000,
      "label": "a plain message"
    },
    {
      "style": "embed",
      "cap": 4096,
      "label": "an embed"
    }
  ],
  "guard": {
    "test_mode": true,
    "test_channel": "blackbloc-logs",
    "said": "Black Bloc is in test mode, so a post only reaches #blackbloc-logs or a channel it made itself. **Post it** on anything else writes down what it would have sent and sends nothing."
  },
  "shadow": {
    "channel_id": "800000000000000003",
    "channel_name": "blackbloc-logs"
  },
  "notes": [
    "Posts are in **shadow**: **Post it** sends the real message to #blackbloc-logs and keeps it edited there, whatever channel a post names, so nothing reaches members yet. Turning posts **on** is the go-live — the next **Post it** goes to the post’s own channel and the shadow copy is removed."
  ],
  "settings": [
    {
      "key": "posts_log_level",
      "type": "enum",
      "value": "important",
      "default": "important",
      "help": "which posts log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/posts logs` either way",
      "choices": [
        "off",
        "important",
        "all"
      ]
    },
    {
      "key": "posts_mode",
      "type": "enum",
      "value": "shadow",
      "default": "shadow",
      "help": "off, shadow (Post it sends the real message into the shadow channel — the test channel while test mode is on, otherwise the log channel — and keeps it edited there, whatever channel the post names) or on (Post it goes to the post's own channel, and the first real post removes the shadow copy). Shadow is the default, so nothing reaches members until a Lead turns posts on. Off hides `/posts` and refuses both doors in words; every word already written is kept in all three",
      "choices": [
        "off",
        "shadow",
        "on"
      ]
    },
    {
      "key": "posts_panel_minutes",
      "type": "int",
      "value": 10,
      "default": 10,
      "help": "minutes the /posts panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it",
      "max": 1440,
      "min": 1
    }
  ],
  "logs": [],
  "channels": [
    {
      "id": "800000000000000001",
      "name": "welcome",
      "type": "text",
      "category_id": null,
      "position": 0
    },
    {
      "id": "800000000000000002",
      "name": "general",
      "type": "text",
      "category_id": null,
      "position": 1
    },
    {
      "id": "800000000000000003",
      "name": "blackbloc-logs",
      "type": "text",
      "category_id": null,
      "position": 2
    },
    {
      "id": "800000000000000004",
      "name": "bot-log",
      "type": "text",
      "category_id": null,
      "position": 3
    },
    {
      "id": "800000000000000005",
      "name": "staff-room",
      "type": "text",
      "category_id": null,
      "position": 4
    },
    {
      "id": "800000000000000006",
      "name": "announcements",
      "type": "text",
      "category_id": null,
      "position": 5
    },
    {
      "id": "800000000000000007",
      "name": "free-nitro-here",
      "type": "text",
      "category_id": null,
      "position": 6
    },
    {
      "id": "800000000000000008",
      "name": "Events",
      "type": "category",
      "category_id": null,
      "position": 7
    },
    {
      "id": "800000000000000009",
      "name": "Join to create",
      "type": "voice",
      "category_id": null,
      "position": 8
    },
    {
      "id": "800000000000000010",
      "name": "casey's room",
      "type": "voice",
      "category_id": null,
      "position": 9
    },
    {
      "id": "800000000000000011",
      "name": "modmail",
      "type": "category",
      "category_id": null,
      "position": 10
    },
    {
      "id": "800000000000000012",
      "name": "modmail-log",
      "type": "text",
      "category_id": "800000000000000011",
      "position": 11
    }
  ]
};

const LIST_NOTE = 'One message per post. Black Bloc sends it once and edits that same message '
  + 'every time after — it never posts a second copy.';
const NOTHING_YET = 'There are no posts yet.';
const NO_CHANNEL = 'no channel yet';
const NEED_A_TITLE = 'A post needs a title. Type one and press Make it again.';
const POSTED_HERE = 'Posted in {where}.';
const POSTED_IN_SHADOW = 'The shadow copy is in {where}.';
const NOT_POSTED_ANYWHERE = 'Not posted anywhere yet.';
const PINNED_TOO = ' It is pinned.';
const NOT_PINNED = ' It is not pinned.';
const WILL_POST = 'Post it sends this to {where} as {style} and {pin}.';
const WILL_UPDATE = 'Update the post edits the message already in {where}, as {style} and {pin}.';
const NEEDS_A_CHANNEL = 'Pick a channel before this can be posted anywhere.';
const WILL_SHADOW = 'shadow — this goes to {shadow}, not {where}, until posts are on.';
const WILL_SHADOW_NOWHERE = 'shadow — this goes to {shadow}. It has no channel of its own yet, '
  + 'and nothing reaches one until posts are on.';
const WILL_SHADOW_SAME = 'shadow — this goes to {shadow}, which is where it was going anyway.';
const NO_SHADOW_CHANNEL = 'no shadow channel yet';
const SHADOW = 'shadow';
const PIN_WORDS = { true: 'pins it', false: 'leaves it unpinned' };
const STYLE_WORDS = { plain: 'a plain message', embed: 'an embed' };
const SETTINGS_NOTE = 'Whether staff may post at all, how long the /posts panel stays live, and '
  + 'how much of it is repeated into the Discord log.';
const LOGS_NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in '
  + 'Discord. Important means it acted on a member or failed.';
const NOTHING_LOGGED = 'Posts has logged nothing at all yet.';

const WAS_LIST = 'Replaces three blocks: The posts, the loose A new post card that was never a '
  + 'section, and the whole separate post page you reached through the title.';
const WAS_MACHINERY = 'Replaces the Settings section and the Logs section — two shut headers '
  + 'become one, with a fold each.';

const TONES = {
  posted: 'ok',
  'posted (shadow)': 'info',
  pinned: null,
  'changes not yet posted': 'warn',
  'not posted': 'danger',
};

const STATE_OF = {
  posted: 'ok',
  'posted (shadow)': 'info',
  'changes not yet posted': 'warn',
  'not posted': 'danger',
};

const FILTERS = [
  ['all', 'All', null],
  ['posted', 'Posted', (row) => row.posted],
  ['pending', 'Changed since posted', (row) => row.changes_pending],
  ['unposted', 'Not posted', (row) => !row.posted],
];

const state = { filter: 'all', query: '' };
let refresh = () => {};

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

function whereWords(row) {
  return row.channel_name ? `#${row.channel_name}` : NO_CHANNEL;
}

function shadowWords(shadow) {
  return shadow && shadow.channel_name ? `#${shadow.channel_name}` : NO_SHADOW_CHANNEL;
}

function postedLine(row, shadow) {
  if (!row.posted) return NOT_POSTED_ANYWHERE;
  const rehearsal = row.posted_where === SHADOW;
  const line = rehearsal ? POSTED_IN_SHADOW : POSTED_HERE;
  const where = rehearsal ? shadowWords(shadow) : whereWords(row);
  return line.replace('{where}', where) + (row.pin ? PINNED_TOO : NOT_PINNED);
}

/** The one word that decides the dot: what the row's own status list leads with. */
function leadState(row) {
  if (row.changes_pending) return 'warn';
  const head = (row.status || []).find((word) => word in STATE_OF);
  return head ? STATE_OF[head] : 'danger';
}

function statusPills(row) {
  return (row.status || []).map((word) => badge(word, TONES[word] === undefined ? null : TONES[word]));
}

function channelPicker(value, id) {
  const select = el('select', { class: 'input', id: id || undefined });
  select.append(el('option', { value: '', text: 'not set', selected: value ? undefined : true }));
  for (const channel of DATA.channels) {
    select.append(el('option', {
      value: String(channel.id),
      text: channelLabel(channel, DATA.channels),
      selected: String(channel.id) === String(value) || undefined,
    }));
  }
  return select;
}

function willPost(draft, post) {
  if (DATA.mode === SHADOW) {
    const where = shadowWords(DATA.shadow);
    if (!draft.channel_id) return WILL_SHADOW_NOWHERE.replace('{shadow}', where);
    if (DATA.shadow && String(draft.channel_id) === String(DATA.shadow.channel_id)) {
      return WILL_SHADOW_SAME.replace('{shadow}', where);
    }
    return WILL_SHADOW
      .replace('{shadow}', where)
      .replace('{where}', `#${draft.channel_name || post.channel_name || ''}`);
  }
  if (!draft.channel_id) return NEEDS_A_CHANNEL;
  const template = post.posted ? WILL_UPDATE : WILL_POST;
  return template
    .replace('{where}', `#${draft.channel_name || post.channel_name || ''}`)
    .replace('{style}', STYLE_WORDS[draft.style] || STYLE_WORDS.plain)
    .replace('{pin}', PIN_WORDS[String(Boolean(draft.pin))]);
}

/**
 * The whole post, in the drawer the row opens — what used to be a page of its
 * own behind an unstyled title button.
 */
function postDrawer(post) {
  const say = notice();
  const draft = {
    title: post.title || '',
    body: post.body || '',
    style: post.style,
    pin: Boolean(post.pin),
    channel_id: post.channel_id || '',
    channel_name: post.channel_name || '',
  };

  const title = el('input', { class: 'input', type: 'text', value: draft.title });
  const channel = channelPicker(draft.channel_id, 'preview-post-channel');
  const style = el('select', { class: 'input', id: 'preview-post-style' }, (DATA.styles || []).map((one) =>
    el('option', {
      value: one.style,
      text: `${one.label} — ${one.cap.toLocaleString()} characters`,
      selected: one.style === draft.style || undefined,
    })));
  const pin = el('input', { class: 'switch', type: 'checkbox', id: 'preview-post-pin' });
  pin.checked = draft.pin;
  const box = el('textarea', { class: 'input area postbox', id: 'preview-post-body', rows: '12' });
  box.value = draft.body;
  const howLine = el('p', { class: 'field-help', text: willPost(draft, post) });

  const repaint = () => { howLine.textContent = willPost(draft, post); };
  title.addEventListener('input', () => { draft.title = title.value; });
  box.addEventListener('input', () => { draft.body = box.value; });
  style.addEventListener('change', () => { draft.style = style.value; repaint(); });
  pin.addEventListener('change', () => { draft.pin = pin.checked; repaint(); });
  channel.addEventListener('change', () => {
    draft.channel_id = channel.value;
    const picked = DATA.channels.find((one) => String(one.id) === String(draft.channel_id));
    draft.channel_name = picked ? picked.name : '';
    repaint();
  });

  const moves = [
    button(post.move, () => wouldDo(say, `POST /api/posts/${post.slug}/publish — ${willPost(draft, post).replace(/\.$/, '')}`), { tone: 'warn' }),
  ];
  if (post.posted) {
    moves.push(button('Take it down', () => wouldDo(say, `POST /api/posts/${post.slug}/takedown — delete the message in ${whereWords(post)} and leave every word written here`), { tone: 'quiet' }));
  }
  if (post.seeded) {
    moves.push(button('Put the original back', () => wouldDo(say, `POST /api/posts/${post.slug}/reset — put every word back to the message Black Bloc ships with, keeping the channel, the style and the pin`), { tone: 'quiet' }));
  } else {
    moves.push(button('Delete this post', () => wouldDo(say, `DELETE /api/posts/${post.slug} — remove the post and every word in it`), { tone: 'danger' }));
  }

  return [
    el('div', { class: 'postmarks' }, statusPills(post)),
    el('p', { class: 'row-detail', text: postedLine(post, DATA.shadow) }),
    el('div', { class: 'formrow' }, [
      field('Title', title, 'Staff see this here; an embed shows it at the top of the message.'),
      field('Channel', channel, 'Where the message lives. Black Bloc edits that one message.'),
    ]),
    el('div', { class: 'formrow' }, [
      field('Style', style, 'A plain message renders # headers; an embed holds more but does not.'),
      field('Pin it', pin, 'Black Bloc pins the message once it is posted, and re-pins it if '
        + 'somebody unpins it.'),
    ]),
    field('The message', box),
    howLine,
    bar([
      button('Save Changes', () => wouldDo(say, `PUT /api/posts/${post.slug} — save the title, the message, the channel, the style and the pin`), { tone: 'warn', small: false }),
      ...moves,
    ]),
    say,
  ];
}

/**
 * The row IS the control — `button.grid-row`, the construct `page-moderation.js:144`
 * already uses, with the hover, focus and cursor rules `site.css:910` gives it.
 */
function postRow(post) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: 'grid-template-columns: 12px minmax(0, 1.4fr) 260px 150px 140px 24px',
    'data-search': `${post.title} ${post.channel_name || ''} ${(post.status || []).join(' ')} ${post.body || ''}`.toLowerCase(),
    on: { click: () => openDrawer(post.title, postDrawer(post)) },
  }, [
    el('span', { class: 'dot-sm', 'data-tone': leadState(post) }),
    el('span', { class: 'cell-name', text: post.title }),
    el('span', { class: 'cell-kind' }, [
      ...statusPills(post),
      post.seeded ? badge('ships with the bot') : null,
    ]),
    el('span', { class: 'cell-quiet', text: postedLine(post, DATA.shadow) }),
    el('span', {
      class: 'cell-quiet',
      title: ago(post.updated_at).title,
      text: `Last saved ${ago(post.updated_at).text}`,
    }),
    icon('chevronRight', 16),
  ]);
}

function headRow() {
  return el('div', {
    class: 'grid-row head',
    style: 'grid-template-columns: 12px minmax(0, 1.4fr) 260px 150px 140px 24px',
  }, [
    el('span'),
    el('span', { text: 'Post' }),
    el('span', { text: 'How it stands' }),
    el('span', { text: 'Where it is' }),
    el('span', { text: 'Last saved' }),
    el('span'),
  ]);
}

function newPostDrawer() {
  const say = notice();
  const title = el('input', { class: 'input', type: 'text', placeholder: 'Welcome and rules' });
  const make = button('Make it', () => {
    if (!title.value.trim()) {
      say.say(NEED_A_TITLE, 'warn');
      return;
    }
    wouldDo(say, `POST /api/posts — make a post called “${title.value.trim()}” and open it`);
  }, { tone: 'warn', small: false });
  return [
    el('div', { class: 'formrow' }, [
      field('What is it called?', title, 'The title staff see here, and the embed title if you '
        + 'set the style to an embed.'),
    ]),
    bar([make]),
    say,
  ];
}

function postsSection() {
  const rows = DATA.posts.map((post) => ({ post, node: postRow(post) }));
  const list = section('The posts', LIST_NOTE, { count: DATA.posts.length, open: true });
  const foot = el('div', { class: 'grid-foot' });
  const grid = el('div', { class: 'grid-table', style: 'min-width: 760px' }, [
    headRow(),
    ...rows.map((one) => one.node),
    foot,
  ]);

  const paint = () => {
    const rule = (FILTERS.find(([key]) => key === state.filter) || FILTERS[0])[2];
    let shown = 0;
    for (const one of rows) {
      const hit = (rule === null || rule(one.post))
        && (state.query === '' || (one.node.getAttribute('data-search') || '').includes(state.query));
      one.node.hidden = !hit;
      if (hit) shown += 1;
    }
    foot.textContent = shown === rows.length
      ? `Showing ${rows.length} of ${rows.length} post${rows.length === 1 ? '' : 's'}`
      : `Showing ${shown} of the ${rows.length} post${rows.length === 1 ? '' : 's'} on this page`;
  };

  const chips = el('div', { class: 'chipbar' }, FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key,
    'aria-pressed': state.filter === key ? 'true' : 'false',
    text: label,
    on: {
      click: (event) => {
        state.filter = key;
        for (const chip of event.currentTarget.parentElement.children) {
          chip.setAttribute('aria-pressed', chip.getAttribute('data-kind') === key ? 'true' : 'false');
        }
        paint();
      },
    },
  })));
  const search = searchField({
    label: 'Search the posts',
    placeholder: 'Search the posts…',
    onQuery: (query) => {
      state.query = query;
      paint();
    },
  });

  const say = notice();
  const mode = el('span', { class: 'mode-chip', 'data-mode': DATA.mode, text: DATA.mode });
  paint();

  list.body.append(
    previewWas(WAS_LIST),
    el('p', { class: 'field-help' }, [
      el('span', { text: 'Posts are ' }),
      mode,
      el('span', { text: '. ' }),
      el('span', { text: (DATA.notes || [])[0] ? (DATA.notes || [])[0].replace(/\*\*/g, '') : '' }),
    ]),
    DATA.guard && DATA.guard.said
      ? el('p', { class: 'field-help', text: DATA.guard.said.replace(/\*\*/g, '') })
      : null,
    card(null, [
      el('div', { class: 'card-head' }, [search, chips]),
      DATA.posts.length === 0
        ? sayNothing(NOTHING_YET)
        : el('div', { class: 'table-scroll' }, [grid]),
    ]),
    say,
  );
  return list.node;
}

function settingControl(spec, say) {
  if (spec.type === 'enum') {
    const select = el('select', { class: 'input' }, (spec.choices || []).map((choice) =>
      el('option', { value: choice, text: choice, selected: String(spec.value) === String(choice) || undefined })));
    select.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${select.value}`));
    return select;
  }
  if (spec.type === 'int') {
    const input = el('input', { class: 'input', type: 'number', step: '1', value: String(spec.value) });
    input.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${input.value}`));
    return input;
  }
  const input = el('input', { class: 'input', type: 'text', value: spec.value === null ? '' : String(spec.value) });
  input.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${input.value}`));
  return input;
}

function machinerySection() {
  const say = notice();
  const one = section('Settings and logs', 'The reference half of the page: three keys, and '
    + 'everything posts has done. Both are shut until you want them.', { id: 'machinery' });
  one.body.append(
    previewWas(WAS_MACHINERY),
    foldout('Settings', [
      el('p', { class: 'field-help', text: SETTINGS_NOTE }),
      ...DATA.settings.map((spec) => field(spec.key, settingControl(spec, say), spec.help)),
      say,
    ], { count: DATA.settings.length }),
    foldout('Logs', [
      el('p', { class: 'field-help', text: LOGS_NOTE }),
      DATA.logs.length === 0
        ? sayNothing(NOTHING_LOGGED)
        : table([
          { label: 'When', cell: (row) => ago(row.at).text },
          { label: 'Kind', cell: (row) => row.kind },
          { label: 'Summary', cell: (row) => row.summary, className: 'wrap' },
        ], DATA.logs),
    ], { count: DATA.logs.length }),
  );
  return one.node;
}

async function load() {
  const aside = document.getElementById('page-aside');
  if (aside) {
    aside.replaceChildren(button('Make it', () => openDrawer('A new post', newPostDrawer()), {
      tone: 'warn',
      small: false,
    }));
  }
  document.getElementById('dash').replaceChildren(
    full(previewBanner({
      today: 3,
      preview: 2,
      note: 'Today’s three are joined by a loose card and a separate post page; here a post is '
        + 'a row you press, and the row says whether it went out.',
    })),
    full(postsSection()),
    full(machinerySection()),
  );
}

refresh = start({ tab: 'posts', load });
