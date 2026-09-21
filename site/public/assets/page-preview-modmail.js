import { start } from './app.js';
import { importantSwitch, logsTable } from './logs.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';
import {
  badge,
  bar,
  button,
  card,
  channelLabel,
  el,
  field,
  foldout,
  icon,
  nameNode,
  notice,
  openDrawer,
  sayNothing,
  searchField,
  section,
  segment,
  shortWhen,
  table,
  textAction,
  when,
} from './ui.js';

const minutesAgo = (m) => new Date(Date.now() - m * 60000).toISOString();

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null, position: 0 },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null, position: 1 },
  { id: '800000000000000003', name: 'blackbloc-logs', type: 'text', category_id: null, position: 2 },
  { id: '800000000000000004', name: 'bot-log', type: 'text', category_id: null, position: 3 },
  { id: '800000000000000005', name: 'staff-room', type: 'text', category_id: null, position: 4 },
  { id: '800000000000000006', name: 'announcements', type: 'text', category_id: null, position: 5 },
  { id: '800000000000000007', name: 'free-nitro-here', type: 'text', category_id: null, position: 6 },
  { id: '800000000000000008', name: 'Events', type: 'category', category_id: null, position: 7 },
  { id: '800000000000000009', name: 'Join to create', type: 'voice', category_id: null, position: 8 },
  { id: '800000000000000010', name: "casey's room", type: 'voice', category_id: null, position: 9 },
  { id: '800000000000000011', name: 'modmail', type: 'category', category_id: null, position: 10 },
  { id: '800000000000000012', name: 'modmail-log', type: 'text', category_id: '800000000000000011', position: 11 },
];

const TICKETS = [
  { id: 5, user_id: '700000000000000004', user_name: 'Moth', mode: 'thread', channel_id: '800000000000000005', thread_id: '830000000000000001', status: 'open', opened_at: minutesAgo(90), closed_at: null, closed_by_id: null, closed_by_name: null, close_reason: null, source: 'dm', opened_by_id: null },
  { id: 4, user_id: '700000000000000007', user_name: 'Dax', mode: 'thread', channel_id: '800000000000000005', thread_id: '830000000000000002', status: 'open', opened_at: minutesAgo(600), closed_at: null, closed_by_id: null, closed_by_name: null, close_reason: null, source: 'panel', opened_by_id: null },
  { id: 3, user_id: '700000000000000005', user_name: 'spamlord99', mode: 'channel', channel_id: '800000000000000011', thread_id: null, status: 'closed', opened_at: minutesAgo(4000), closed_at: minutesAgo(3800), closed_by_id: '700000000000000001', closed_by_name: 'Nick', close_reason: 'spam', source: 'staff', opened_by_id: '700000000000000001' },
];

const MESSAGES = {
  5: [
    { id: 21, at: minutesAgo(90), author_id: '700000000000000004', author_name: 'Moth', direction: 'in', anonymous: false, content: 'Someone is posting scam links in general.', delivered: true },
    { id: 22, at: minutesAgo(88), author_id: '700000000000000001', author_name: 'Nick', direction: 'note', anonymous: false, content: 'Same account as the honeypot hit this morning.', delivered: true },
    { id: 23, at: minutesAgo(85), author_id: '700000000000000001', author_name: 'Nick', direction: 'out', anonymous: true, content: 'Thanks for the report — we are on it.', delivered: true },
  ],
  4: [
    { id: 18, at: minutesAgo(600), author_id: '700000000000000007', author_name: 'Dax', direction: 'in', anonymous: false, content: 'Can I get the Live now role?', delivered: true },
  ],
  3: [
    { id: 9, at: minutesAgo(4000), author_id: '700000000000000005', author_name: 'spamlord99', direction: 'in', anonymous: false, content: 'free nitro', delivered: true },
  ],
};

const SNIPPETS = [
  { name: 'rules', content: 'Please read #welcome — the rules are pinned there.', by_id: '700000000000000001', by_name: 'Nick', at: minutesAgo(20000) },
  { name: 'closing', content: 'Closing this for now; reply again if it comes back.', by_id: '700000000000000001', by_name: 'Nick', at: minutesAgo(20000) },
];

const BLOCKS = [
  { user_id: '700000000000000005', user_name: 'spamlord99', by_id: '700000000000000001', by_name: 'Nick', reason: 'opened twelve tickets about nitro', at: minutesAgo(3000) },
];

const LOG_ROWS = [
  { id: 36, at: minutesAgo(88), kind: 'modmail.note_added', feature: 'modmail', important: false, via: 'discord', actor_id: '700000000000000001', actor_name: 'Nick', target_id: '700000000000000004', target_name: 'Moth', reason: null, summary: '' },
];

const DOOR = {
  mode: 'on',
  channel_id: null,
  shadow_channel_id: '800000000000000004',
  message_id: null,
  title: 'Need something?',
  text: 'Pick the one that fits and Black Bloc takes it from there. Staff only see what you write.',
  ticket_label: 'Ask staff privately',
  request_label: 'Request something',
  event_label: 'Propose an event',
};

const BUTTON_WORDS = {
  channel_id: null,
  title: 'Need a moderator?',
  text: 'Press the button and tell us what is happening. Only staff see it.',
};

const FORUM_CHANNEL_ID = null;

const SETTING_SPECS = [
  { key: 'modmail_enabled', type: 'bool', value: true, label: 'Modmail on', help: 'true when Black Bloc answers DMs' },
  { key: 'modmail_mode', type: 'enum', value: 'thread', choices: ['channel', 'thread', 'forum'], label: 'Ticket mode', help: 'channel (one channel per ticket), thread (private threads in the staff channel) or forum (one post per ticket in the forum channel — the list never grows past the forum’s own archive)' },
  { key: 'modmail_category_id', type: 'channel', value: '800000000000000011', label: 'Ticket category', help: 'the category ticket channels are made in, in channel mode' },
  { key: 'modmail_staff_channel_id', type: 'channel', value: '800000000000000005', label: 'Staff channel', help: 'the channel ticket threads are made in, in thread mode' },
  { key: 'modmail_log_channel_id', type: 'channel', value: '800000000000000004', label: 'Transcript channel', help: 'where a closed ticket’s transcript is posted' },
  { key: 'modmail_member_command', type: 'bool', value: true, label: 'Members may run /modmail', help: 'true when anybody running /modmail gets the Open a ticket panel; false leaves /modmail to staff, as it was before, and a member’s only door is a DM' },
  { key: 'modmail_open_with_button', type: 'bool', value: false, label: 'Open a ticket for somebody else', help: 'true draws Open a ticket with… on the staff row of /modmail, so staff can start a ticket for somebody else' },
  { key: 'modmail_forum_tags', type: 'bool', value: true, label: 'Forum tags', help: 'true keeps the open / closed tags on each ticket post in forum mode' },
  { key: 'modmail_log_on_open', type: 'bool', value: true, label: 'Log when a ticket opens', help: "true posts a New-ticket card to the transcripts channel the moment a ticket opens" },
  { key: 'modmail_panel_follows_post', type: 'text', value: 'welcome', label: 'Button follows post', help: 'the slug of the post the Open a ticket button sits under — welcome by default' },
  { key: 'modmail_panel_minutes', type: 'int', value: 10, label: 'Panel minutes', help: 'minutes the /modmail panel stays live before its buttons disable themselves' },
  { key: 'modmail_reply_style', type: 'enum', value: 'both', choices: ['buttons', 'typing', 'both'], label: 'Reply style', help: 'how staff answer a ticket. typing: a plain message in the ticket is relayed to the member. buttons: it is not — only the ticket card’s Reply and /reply reach them' },
  { key: 'frontdoor_follows_post', type: 'text', value: 'welcome', label: 'Door follows post', help: 'the slug of the post the front door sits directly under — welcome by default' },
  { key: 'frontdoor_replaces_ticket_button', type: 'bool', value: true, label: 'Door replaces the ticket button', help: 'true takes the posted Open-a-ticket message down while the front door is up in the same channel — one door per channel' },
  { key: 'frontdoor_panel_minutes', type: 'int', value: 10, label: 'Ask panel minutes', help: 'minutes the /ask panel stays live before its buttons disable themselves' },
];

const DIRECTION_LABEL = { in: 'from the member', out: 'from staff', note: 'staff note — the member never sees this' };
const SOURCE_LABEL = {
  dm: 'a DM to the bot',
  command: '/modmail',
  panel: 'the ticket button',
  staff: 'staff',
  practice: 'practice',
};

const BUTTON_HELP = 'One message with an Open a ticket button under it. Pressing it asks what is '
  + 'happening and opens a ticket — the same one a DM opens.';
const DOOR_HELP = 'One message with three buttons: Ask staff privately opens a ticket, Request '
  + 'something files a request, and Propose an event starts an event proposal. Each press opens '
  + 'the flow that already exists, so each one answers with its own words when it is switched '
  + 'off.';
const DOOR_MODE_HELP = 'off hides /ask and takes the door down; shadow posts the rehearsal copy '
  + 'into shadow_channel_id with the rehearsal note and nothing into the real channel; on posts '
  + 'it where it is pointed. /ask answers in both shadow and on, and the three flows behind it '
  + '(modmail, requests, events) keep their own modes whatever this says.';
const DOOR_OFF_LINE = 'frontdoor_mode is off, so /ask is hidden and no front door stays posted.';
const DOOR_SHADOW_HOMELESS = 'shadow — the door has nowhere to rehearse, so it is posted nowhere '
  + 'at all. Set shadow_channel_id on the Settings page.';
const DOOR_SHADOW_NOWHERE_END = '. It has no channel of its own yet, and nothing reaches members '
  + 'until the door is on.';
const DOOR_SHADOW_FOLLOWS = 'The Open a ticket button follows the door while it is rehearsing, so '
  + 'it comes down too — frontdoor_replaces_ticket_button below is what switches that off.';
const DOOR_ONE_PER_CHANNEL = 'While the front door is up in the ticket button’s channel, that '
  + 'button is taken down — one door per channel. Moving the front door elsewhere, or taking it '
  + 'down, puts the ticket button back within five minutes. frontdoor_replaces_ticket_button '
  + 'below is what switches that off.';
const FORUM_HELP = 'In forum mode every ticket is a post of its own, tagged open while it is '
  + 'running and closed when it ends, so the list never grows without end. Make the forum puts '
  + 'one under the ticket category with that category’s own permissions; modmail_mode below is '
  + 'what starts using it.';

const TICKETS_NOTE = 'Every ticket, newest first. Open one to read it and answer it — the page ' +
  'under the drawer does not move.';
const DOOR_NOTE = 'The one message that owns three flows — a ticket, a request and an event ' +
  'proposal — and the words on all three of its buttons.';
const SNIPPETS_NOTE = 'Canned replies staff can send without retyping them.';
const BLOCKS_NOTE = 'A blocked member’s DMs stop opening tickets, and they are not told.';
const SETTINGS_NOTE = 'Where a ticket is made, who can open one, and how long the panels stay live.';
const LOGS_NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in ' +
  'Discord. Important means it acted on a member or failed.';
const DOORS_FOLD = 'How a ticket gets opened';
const DOORS_FOLD_NOTE = 'The two things that put an Open a ticket button in a channel. Both are ' +
  'about tickets, which is why they live here rather than in a folder of their own.';

const NO_MATCH = 'Nothing here matches what you typed.';
const NO_TICKETS = 'No tickets match that.';
const EMPTY_REPLY = 'An empty reply would tell them nothing.';

const FILTERS = [
  ['open', 'Open'],
  ['closed', 'Closed'],
  ['', 'Every ticket'],
];

const COLUMNS = [
  ['Ticket', 'The ticket’s own number.'],
  ['Member', null],
  ['Status', null],
  ['Last message', 'The most recent line on the ticket, whoever wrote it.'],
  ['Came in by', 'Which door this ticket came through.'],
  ['Opened', 'Hover for the exact time.'],
  ['', null],
];

const state = { status: 'open', query: '', important: true };

let refresh = () => {};

function channelName(id) {
  const found = CHANNELS.find((one) => String(one.id) === String(id));
  return found ? `#${found.name}` : null;
}

function messagesFor(id) {
  return MESSAGES[id] || [];
}

function lastLine(row) {
  const found = messagesFor(row.id);
  return found.length ? found[found.length - 1].content : '';
}

function messageNode(message) {
  const direction = message.direction === 'note' ? 'note' : message.direction === 'out' ? 'out' : 'in';
  return el('li', { class: 'msg', 'data-direction': direction }, [
    el('div', { class: 'msg-head' }, [
      nameNode(message.author_id, message.author_name),
      el('span', { text: when(message.at) }),
      el('span', { text: DIRECTION_LABEL[direction] }),
      message.anonymous ? badge('anonymous', 'warn') : null,
      message.delivered === false ? badge('not delivered', 'danger') : null,
    ]),
    el('p', { class: 'msg-body', text: message.content || '(no text)' }),
  ]);
}

function ticketDetail(row) {
  const say = notice();
  const messages = messagesFor(row.id);
  const text = el('textarea', { class: 'input area', rows: '4', placeholder: 'what to send back' });
  const anonymous = el('input', { class: 'input switch', type: 'checkbox' });
  const reasonBox = el('input', { class: 'input', type: 'text', placeholder: 'why it is being closed' });
  const silent = el('input', { class: 'input switch', type: 'checkbox' });

  const reply = button('Send reply', () => {
    if (!text.value.trim()) {
      say.say(EMPTY_REPLY, 'warn');
      return;
    }
    wouldDo(say, `POST /api/modmail/tickets/${row.id}/reply — send ${row.user_name} exactly what ` +
      `you typed${anonymous.checked ? ', without your name on it' : ''}`);
  }, { small: false });

  const close = button('Close ticket', () => {
    wouldDo(say, `POST /api/modmail/tickets/${row.id}/close — ${row.user_name} ` +
      `${silent.checked ? 'will not be told' : 'is told it was closed'}, and the transcript goes ` +
      'to the modmail log channel');
  }, { tone: 'danger' });

  const snippetPicker = el('select', { class: 'input' });
  snippetPicker.append(el('option', { value: '', text: 'a saved snippet…', selected: true }));
  for (const one of SNIPPETS) snippetPicker.append(el('option', { value: one.name, text: one.name }));
  snippetPicker.addEventListener('change', () => {
    const found = SNIPPETS.find((one) => one.name === snippetPicker.value);
    if (!found) return;
    text.value = found.content;
    say.say(`The ${found.name} snippet is in the box — nothing has been sent.`, 'info');
  });

  return [
    el('p', {}, [
      'Opened by ',
      nameNode(row.user_id, row.user_name),
      ` · ${when(row.opened_at)} · ${row.status} · came in by ${SOURCE_LABEL[row.source] || row.source}`,
    ]),
    messages.length
      ? el('ul', { class: 'msglist' }, messages.map(messageNode))
      : sayNothing('This ticket has no messages on file.'),
    row.status === 'open' ? field('Reply', text) : null,
    row.status === 'open'
      ? el('div', { class: 'formrow' }, [
        field('Use a snippet', snippetPicker, 'It fills the box; you still press Send reply.'),
        field('Send without your name', anonymous),
        bar([reply]),
      ])
      : null,
    row.status === 'open'
      ? el('div', { class: 'formrow' }, [
        field('Close reason', reasonBox),
        field('Close quietly', silent),
        bar([close]),
      ])
      : null,
    row.status === 'closed' && row.close_reason
      ? el('p', { class: 'section-note', text: `Closed by ${row.closed_by_name} — ${row.close_reason}` })
      : null,
    say,
  ].filter(Boolean);
}

function ticketRow(row) {
  const opened = shortWhen(row.opened_at);
  const searchable = `${row.id} ${row.user_name} ${row.status} ${lastLine(row)} ${SOURCE_LABEL[row.source] || ''}`;
  return el('button', {
    class: 'grid-row',
    type: 'button',
    'data-search': searchable.toLowerCase(),
    'data-status': row.status,
    on: { click: () => openDrawer(`Ticket ${row.id}`, ticketDetail(row)) },
  }, [
    el('span', { class: 'cell-id', text: `#${row.id}` }),
    el('span', { class: 'cell-name' }, [nameNode(row.user_id, row.user_name)]),
    el('span', { class: 'cell-kind' }, [badge(row.status, row.status === 'open' ? 'ok' : null)]),
    el('span', { class: 'cell-reason', text: lastLine(row), title: lastLine(row) }),
    el('span', { class: 'cell-quiet', text: SOURCE_LABEL[row.source] || row.source || 'a DM to the bot' }),
    el('span', { class: 'cell-quiet', text: opened.text, title: opened.title }),
    icon('chevronRight', 16),
  ]);
}

function ticketGrid() {
  const head = el('div', { class: 'grid-row head' }, COLUMNS.map(([label, help]) => el('span', {
    title: help || undefined,
  }, [
    el('span', { text: label }),
    help ? el('span', { class: 'th-mark', 'aria-hidden': 'true', text: 'ⓘ' }) : null,
  ])));
  const lines = TICKETS.map(ticketRow);
  const foot = el('div', { class: 'grid-foot' });
  const body = el('div', { class: 'grid-table' }, [head, ...lines, foot]);
  const none = sayNothing(NO_MATCH, textAction('Clear the search', () => {
    state.query = '';
    refresh();
  }));
  none.hidden = true;

  const paint = () => {
    let shown = 0;
    lines.forEach((line, at) => {
      const row = TICKETS[at];
      const statusHit = state.status === '' || row.status === state.status;
      const textHit = state.query === '' || (line.getAttribute('data-search') || '').includes(state.query);
      const hit = statusHit && textHit;
      line.hidden = !hit;
      if (hit) shown += 1;
    });
    foot.textContent = `Showing ${shown} of ${TICKETS.length} ticket${TICKETS.length === 1 ? '' : 's'}`;
    none.hidden = shown > 0;
    body.hidden = shown === 0;
    if (shown === 0) none.querySelector('.say-nothing-text').textContent = NO_TICKETS;
  };
  return { node: el('div', {}, [el('div', { class: 'table-scroll' }, [body]), none]), paint };
}

function wordingRow(label, value, help, onType) {
  const box = el('input', { class: 'input', type: 'text', value });
  box.addEventListener('input', () => onType(box.value));
  return field(label, box, help);
}

function doorPreview(door) {
  const buttons = [door.ticket_label, door.request_label, door.event_label];
  return el('div', { class: 'door-preview' }, [
    el('p', { class: 'door-preview-title', text: door.title }),
    el('p', { text: door.text }),
    bar(buttons.map((label) => button(label, () => {}, { tone: 'quiet', disabled: true }))),
  ]);
}

function doorWhere(door) {
  if (door.mode === 'off') return sayNothing(DOOR_OFF_LINE);
  if (door.mode === 'shadow') {
    const home = door.shadow_channel_id;
    if (!home) return sayNothing(DOOR_SHADOW_HOMELESS);
    if (!door.channel_id) {
      return el('p', { class: 'muted' }, [
        'shadow — the door is rehearsing in ',
        nameNode(home, channelName(home)),
        DOOR_SHADOW_NOWHERE_END,
      ]);
    }
    return el('p', { class: 'muted' }, [
      'shadow — the door is rehearsing in ',
      nameNode(home, channelName(home)),
      '; nothing is in ',
      nameNode(door.channel_id, channelName(door.channel_id)),
      '.',
    ]);
  }
  return door.channel_id
    ? el('p', {}, ['It is in ', nameNode(door.channel_id, channelName(door.channel_id)), '.'])
    : sayNothing('No front door is posted anywhere. /ask still opens the same three buttons.');
}

function channelPicker(value) {
  const node = el('select', { class: 'input' });
  node.append(el('option', { value: '', text: 'not set', selected: !value }));
  for (const channel of CHANNELS) {
    node.append(el('option', {
      value: channel.id,
      text: channelLabel(channel, CHANNELS),
      selected: String(value) === String(channel.id) || undefined,
    }));
  }
  return node;
}

function frontDoorCard() {
  const say = notice();
  const door = { ...DOOR };
  const preview = el('div');
  const whereLine = el('div');
  const rule = el('p', { class: 'muted' });
  const redraw = () => {
    preview.replaceChildren(doorPreview(door));
    whereLine.replaceChildren(doorWhere(door));
    rule.textContent = door.mode === 'shadow' ? DOOR_SHADOW_FOLLOWS : DOOR_ONE_PER_CHANNEL;
  };

  const mode = segment(
    [{ value: 'on', label: 'on' }, { value: 'shadow', label: 'shadow' }, { value: 'off', label: 'off' }],
    door.mode,
    {
      onChange: () => {
        door.mode = mode.readValue();
        redraw();
        wouldDo(say, `PUT /api/settings/frontdoor_mode — store ${door.mode}, which is what the ` +
          'line under the preview has just changed to describe');
      },
    },
  );

  const where = channelPicker(door.channel_id);
  const post = button(door.channel_id ? 'Move the front door' : 'Post the front door', () => {
    if (!where.value) {
      say.say('Pick the channel the front door goes in first.', 'warn');
      return;
    }
    wouldDo(say, 'POST /api/frontdoor/panel — post the front door in ' +
      `${channelName(where.value)} and keep it there`);
  }, { tone: 'warn' });
  const down = button('Take it down', () => {
    wouldDo(say, 'DELETE /api/frontdoor/panel — take the message down, so nobody can reach those ' +
      'three flows from that channel. /ask still works, and the ticket button comes back where it was');
  }, { tone: 'danger' });

  const words = [
    ['Heading', 'title', 'frontdoor_title'],
    ['What it says', 'text', 'frontdoor_text'],
    ['Ticket button label', 'ticket_label', 'frontdoor_ticket_label'],
    ['Request button label', 'request_label', 'frontdoor_request_label'],
    ['Event button label', 'event_label', 'frontdoor_event_label'],
  ].map(([label, name, key]) => wordingRow(label, door[name], key, (value) => {
    door[name] = value;
    redraw();
  }));

  redraw();

  return card('Front door', [
    el('p', { text: DOOR_HELP }),
    el('div', { class: 'formrow' }, [field('Now', mode, DOOR_MODE_HELP)]),
    whereLine,
    preview,
    rule,
    foldout('Its words', [
      el('p', { class: 'section-note', text: 'Every line the door posts is a setting. Change one and the preview above changes with it.' }),
      el('div', { class: 'formrow' }, words),
      bar([button('Save the wording', () => wouldDo(say, 'PUT /api/settings/frontdoor_* — store the five ' +
        'lines above, and edit the posted message so it says them within five minutes'), { tone: 'warn' })]),
    ]),
    el('div', { class: 'formrow' }, [field('Put it in', where), bar(door.channel_id ? [post, down] : [post])]),
    say,
  ]);
}

function ticketButtonCard() {
  const say = notice();
  const words = { ...BUTTON_WORDS };
  const preview = el('div', { class: 'door-preview' });
  const redraw = () => {
    preview.replaceChildren(
      el('p', { class: 'door-preview-title', text: words.title }),
      el('p', { text: words.text }),
      bar([button('Open a ticket', () => {}, { tone: 'quiet', disabled: true })]),
    );
  };
  redraw();

  const where = channelPicker(words.channel_id);
  const post = button(words.channel_id ? 'Move the ticket button' : 'Post the ticket button', () => {
    if (!where.value) {
      say.say('Pick the channel the button goes in first.', 'warn');
      return;
    }
    wouldDo(say, `POST /api/modmail/panel — put the Open a ticket message in ${channelName(where.value)}`);
  }, { tone: 'warn' });
  const down = button('Take it down', () => {
    wouldDo(say, 'DELETE /api/modmail/panel — take the message down, so nobody can open a ticket ' +
      'from that channel. Tickets already open are untouched, and a DM still opens one');
  }, { tone: 'danger' });

  const rows = [
    ['Heading', 'title', 'modmail_panel_title'],
    ['What it says', 'text', 'modmail_panel_text'],
  ].map(([label, name, key]) => wordingRow(label, words[name], key, (value) => {
    words[name] = value;
    redraw();
  }));

  return card('Ticket button', [
    el('p', { text: BUTTON_HELP }),
    words.channel_id
      ? el('p', {}, ['It is in ', nameNode(words.channel_id, channelName(words.channel_id)), '.'])
      : sayNothing('No ticket button is posted anywhere.'),
    preview,
    el('div', { class: 'formrow' }, rows),
    el('div', { class: 'formrow' }, [field('Put it in', where), bar(words.channel_id ? [post, down] : [post])]),
    say,
  ]);
}

function ticketForumCard() {
  const say = notice();
  const make = button('Make the forum', () => {
    wouldDo(say, 'POST /api/modmail/forum — make a forum under the ticket category with that ' +
      'category’s own permissions');
  }, { tone: 'warn' });
  return card('Ticket forum', [
    el('p', { text: FORUM_HELP }),
    FORUM_CHANNEL_ID
      ? el('p', {}, ['Ticket posts go in ', nameNode(FORUM_CHANNEL_ID, channelName(FORUM_CHANNEL_ID)), '.'])
      : sayNothing('There is no ticket forum yet, so forum mode would have nowhere to post.'),
    FORUM_CHANNEL_ID
      ? sayNothing('Clear modmail_forum_channel_id below to let go of it.')
      : bar([make]),
    say,
  ]);
}

function ticketsSection() {
  const open = TICKETS.filter((row) => row.status === 'open').length;
  const one = section('Tickets', TICKETS_NOTE, { count: open, id: 'preview-tickets', open: true });
  const made = ticketGrid();

  const chips = FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key || 'any',
    'aria-pressed': state.status === key ? 'true' : 'false',
    text: label,
    on: {
      click: (event) => {
        state.status = key;
        for (const chip of event.currentTarget.parentElement.children) {
          chip.setAttribute('aria-pressed', chip.getAttribute('data-kind') === (key || 'any') ? 'true' : 'false');
        }
        made.paint();
      },
    },
  }));

  const search = searchField({
    label: 'Search tickets',
    placeholder: 'Search the member, the last line, or how it came in…',
    value: state.query,
    onQuery: (query) => {
      state.query = query;
      made.paint();
    },
  });

  one.body.append(
    previewWas('Replaces Tickets and the whole Ticket N section a click used to add below it — ' +
      'the ticket opens in the drawer Moderation already uses, so the page under it does not move.'),
    el('div', { class: 'card' }, [
      el('div', { class: 'card-head' }, [
        search,
        el('div', { class: 'chipbar' }, chips),
        el('span', { class: 'topbar-gap' }),
        el('span', { class: 'table-count', text: `${open} open` }),
      ]),
      el('div', { class: 'card-body' }, [made.node]),
    ]),
    foldout(DOORS_FOLD, [
      el('p', { class: 'section-note', text: DOORS_FOLD_NOTE }),
      ticketButtonCard(),
      ticketForumCard(),
    ]),
  );
  made.paint();
  return one.node;
}

function frontDoorSection() {
  const one = section('Front door', DOOR_NOTE, { id: 'preview-front-door' });
  one.body.append(
    previewWas('Half of what Doors used to hold. The front door owns three flows and three ' +
      'labels, so it is a subject of its own; the ticket button and the ticket forum are about ' +
      'tickets, so they moved up into Tickets.'),
    frontDoorCard(),
  );
  return one.node;
}

function snippetsSection() {
  const say = notice();
  const name = el('input', { class: 'input', type: 'text', placeholder: 'rules' });
  const content = el('textarea', { class: 'input area', rows: '3', placeholder: 'what it says' });
  const add = button('Save snippet', () => {
    if (!name.value.trim()) {
      say.say('A snippet needs a name staff can type.', 'warn');
      return;
    }
    wouldDo(say, `POST /api/modmail/snippets — save the ${name.value.trim()} snippet`);
  });

  const list = table([
    { label: 'Name', cell: (row) => el('span', { class: 'mono', text: row.name }) },
    { label: 'Says', cell: (row) => row.content, className: 'wrap' },
    { label: 'By', cell: (row) => nameNode(row.by_id, row.by_name) },
    {
      label: '',
      cell: (row) => button('Delete', () => wouldDo(say, `DELETE /api/modmail/snippets/${row.name} — ` +
        'staff will not be able to send it any more. Nothing already sent changes'), { tone: 'danger' }),
    },
  ], SNIPPETS, { empty: 'No snippets are saved.' });

  const one = section('Snippets', SNIPPETS_NOTE, { count: SNIPPETS.length, id: 'preview-snippets' });
  one.body.append(
    previewWas('Unchanged, except that a snippet can now be picked from inside a ticket.'),
    card('Snippets', [
      list,
      el('div', { class: 'formrow' }, [field('Name', name), field('Says', content), bar([add])]),
      say,
    ]),
  );
  return one.node;
}

function blocksSection() {
  const say = notice();
  const who = el('input', { class: 'input', type: 'search', placeholder: 'type part of a name' });
  const reason = el('input', { class: 'input', type: 'text', placeholder: 'why' });
  const add = button('Block', () => {
    if (!who.value.trim()) {
      say.say('Pick the member to block first.', 'warn');
      return;
    }
    wouldDo(say, `POST /api/modmail/blocks — stop ${who.value.trim()}'s DMs opening tickets. They ` +
      'are not told, and it is undone from this same table');
  });

  const list = table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Since', cell: (row) => when(row.at), className: 'mono' },
    { label: 'By', cell: (row) => nameNode(row.by_id, row.by_name) },
    { label: 'Why', cell: (row) => row.reason, className: 'wrap' },
    {
      label: '',
      cell: (row) => button('Unblock', () => wouldDo(say, `DELETE /api/modmail/blocks/${row.user_id} — ` +
        `let ${row.user_name} open tickets again`), { tone: 'quiet' }),
    },
  ], BLOCKS, { empty: 'Nobody is blocked.' });

  const one = section('Blocks', BLOCKS_NOTE, { count: BLOCKS.length, id: 'preview-blocks' });
  one.body.append(
    previewWas('Unchanged — the member picker is a plain box here because a preview never asks ' +
      'the bot who is in the server.'),
    card('Blocks', [list, field('Block a member', who), field('Why', reason), bar([add]), say]),
  );
  return one.node;
}

function settingControl(spec, say) {
  const fire = (value) => wouldDo(say, `PUT /api/settings/${spec.key} — store ${JSON.stringify(value)}`);
  if (spec.type === 'bool') {
    const node = segment(
      [{ value: 'true', label: 'On' }, { value: 'false', label: 'Off' }],
      spec.value === true ? 'true' : 'false',
      { onChange: () => fire(node.readValue() === 'true') },
    );
    return node;
  }
  if (spec.type === 'enum') {
    const node = segment(
      (spec.choices || []).map((choice) => ({ value: choice, label: choice })),
      spec.value,
      { onChange: () => fire(node.readValue()) },
    );
    return node;
  }
  if (spec.type === 'channel') {
    const node = channelPicker(spec.value);
    node.addEventListener('change', () => fire(node.value || null));
    return node;
  }
  if (spec.type === 'int') {
    const node = el('input', { class: 'input', type: 'number', step: '1', value: String(spec.value) });
    node.addEventListener('change', () => fire(Number(node.value)));
    return node;
  }
  const node = el('input', { class: 'input', type: 'text', value: spec.value === null ? '' : String(spec.value) });
  node.addEventListener('change', () => fire(node.value));
  return node;
}

function settingsSection() {
  const say = notice();
  const one = section('Settings', SETTINGS_NOTE, { count: SETTING_SPECS.length, id: 'preview-settings' });
  one.body.append(
    previewWas('The same one settings surface, still shut on arrival — with the five front-door ' +
      'lines and the two ticket-button lines taken out of it, because each is now editable where ' +
      'the message it belongs to is drawn.'),
    el('div', { class: 'settings-grid' }, SETTING_SPECS.map((spec) => el('div', { class: 'setrow', 'data-key': spec.key }, [
      el('div', { class: 'setrow-head' }, [
        el('span', { class: 'setrow-label', text: spec.label, title: spec.help }),
        el('span', { class: 'setrow-key', text: spec.key }),
      ]),
      el('div', { class: 'setrow-control' }, [settingControl(spec, say)]),
    ]))),
    say,
  );
  return one.node;
}

function logsSection() {
  const one = section('Logs', LOGS_NOTE, { id: 'preview-logs' });
  const holder = el('div');
  const paint = () => {
    const rows = state.important ? LOG_ROWS.filter((row) => row.important) : LOG_ROWS;
    holder.replaceChildren(logsTable(
      rows,
      state.important
        ? 'Modmail has logged nothing important. Switch to All to see the routine lines too.'
        : 'Modmail has logged nothing at all yet.',
      state.important
        ? textAction('Show every line', () => {
          state.important = false;
          only.setValue('all');
          paint();
        })
        : null,
      { noun: 'line', total: rows.length },
    ));
  };
  const only = importantSwitch(state.important, (wanted) => {
    state.important = wanted;
    paint();
  });
  paint();
  one.body.append(
    previewWas('The shared logs block, unchanged — one per page, shut on arrival.'),
    el('div', { class: 'card' }, [
      el('div', { class: 'card-head' }, [only, el('span', { class: 'topbar-gap' })]),
      el('div', { class: 'card-body' }, [holder]),
    ]),
  );
  return one.node;
}

/** Waiting on staff: an open ticket whose last line came from the member. */
function unanswered() {
  return TICKETS.filter((row) => {
    if (row.status !== 'open') return false;
    const found = messagesFor(row.id);
    return found.length > 0 && found[found.length - 1].direction === 'in';
  }).sort((a, b) => (a.opened_at < b.opened_at ? -1 : 1));
}

function pageHead() {
  const aside = document.getElementById('page-aside');
  if (!aside) return;
  const say = notice();
  const waiting = unanswered();
  const next = button(
    waiting.length ? `Next unanswered ticket · ${waiting.length}` : 'Every ticket is answered',
    () => {
      if (!waiting.length) return;
      openDrawer(`Ticket ${waiting[0].id}`, ticketDetail(waiting[0]));
    },
    { tone: 'warn', small: false, disabled: waiting.length === 0 },
  );
  next.title = 'The oldest open ticket whose last line came from the member.';
  aside.replaceChildren(next, say);
}

async function load() {
  pageHead();
  const banner = previewBanner({
    today: 6,
    preview: 6,
    note: 'Today it grows a seventh section when a ticket is open; here a ticket is a drawer.',
  });
  banner.setAttribute('data-span', 'full');
  document.getElementById('dash').replaceChildren(
    banner,
    ticketsSection(),
    frontDoorSection(),
    snippetsSection(),
    blocksSection(),
    settingsSection(),
    logsSection(),
  );
}

refresh = start({ tab: 'modmail', load });
