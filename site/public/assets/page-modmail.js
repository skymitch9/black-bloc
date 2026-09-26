import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ask,
  badge,
  bar,
  button,
  card,
  channelSelect,
  el,
  field,
  idsIn,
  keepSaying,
  memberPicker,
  nameNode,
  namespaceSettings,
  notice,
  readSelect,
  run,
  sayNothing,
  section,
  table,
  when,
} from './ui.js';

const state = { status: 'open', open: null };

let refresh = () => {};

const DIRECTION_LABEL = { in: 'from the member', out: 'from staff', note: 'staff note — the member never sees this' };
const SOURCE_LABEL = {
  dm: 'a DM to the bot',
  command: '/modmail',
  panel: 'the ticket button',
  staff: 'staff',
  practice: 'practice',
};
const BUTTON_HELP = 'One message with an Open a ticket button under it. Pressing it asks what is '
  + 'happening and opens a ticket — the same one a DM opens. Its heading and wording are the '
  + 'modmail_panel_title and modmail_panel_text settings below.';
const DOOR_HELP = 'One message with three buttons: Ask staff privately opens a ticket, Request '
  + 'something files a request, and Propose an event starts an event proposal. Each press opens '
  + 'the flow that already exists, so each one answers with its own words when it is switched '
  + 'off. Its heading, wording and the three button labels are the frontdoor_ settings below.';
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

async function ticketView(id) {
  const payload = await api(`/api/modmail/tickets/${encodeURIComponent(id)}`);
  const ticket = payload && payload.ticket ? payload.ticket : payload;
  const messages = listOf(payload, 'messages');
  await names(idsIn([ticket], ['user_id', 'closed_by_id']).concat(idsIn(messages, ['author_id'])));

  const say = notice();
  const text = el('textarea', { class: 'input area', rows: '4', placeholder: 'what to send back' });
  const anonymous = el('input', { class: 'input switch', type: 'checkbox' });

  const reply = button('Send reply', async () => {
    if (!text.value.trim()) {
      say.say('An empty reply would tell them nothing.', 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/modmail/tickets/${encodeURIComponent(id)}/reply`, 'POST', { text: text.value, anonymous: anonymous.checked }),
      anonymous.checked ? 'Sent, without your name on it.' : 'Sent.',
    );
    if (done.ok) refresh();
  }, { small: false });

  const reasonBox = el('input', { class: 'input', type: 'text', placeholder: 'why it is being closed' });
  const silent = el('input', { class: 'input switch', type: 'checkbox' });
  const close = button('Close ticket', async () => {
    const sure = await ask({
      title: `Close ticket ${id}?`,
      body: [
        `${ticket.user_name || ticket.user_id} ${silent.checked ? 'will not be told' : 'is told it was closed'}, and the transcript goes to the modmail log channel.`,
      ],
      confirmLabel: 'Close it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/modmail/tickets/${encodeURIComponent(id)}/close`, 'POST', { reason: reasonBox.value.trim(), silent: silent.checked }),
      'Closed.',
    );
    if (done.ok) {
      state.open = null;
      refresh();
    }
  }, { tone: 'danger' });

  return card(`Ticket ${ticket.id}`, [
    el('p', {}, ['Opened by ', nameNode(ticket.user_id, ticket.user_name), ` · ${when(ticket.opened_at)} · ${ticket.status}`]),
    messages.length ? el('ul', { class: 'msglist' }, messages.map(messageNode)) : sayNothing('This ticket has no messages on file.'),
    ticket.status === 'open' ? field('Reply', text) : null,
    ticket.status === 'open' ? el('div', { class: 'formrow' }, [field('Send without your name', anonymous), bar([reply])]) : null,
    ticket.status === 'open' ? el('div', { class: 'formrow' }, [field('Close reason', reasonBox), field('Close quietly', silent), bar([close])]) : null,
    say,
  ]);
}

function snippetsCard(rows) {
  const say = notice();
  const name = el('input', { class: 'input', type: 'text', placeholder: 'rules' });
  const content = el('textarea', { class: 'input area', rows: '3', placeholder: 'what it says' });
  const add = button('Save snippet', async () => {
    const done = await run(
      say,
      () => send('/api/modmail/snippets', 'POST', { name: name.value.trim(), content: content.value }),
      (found) => `Saved the ${found?.name || name.value.trim()} snippet.`,
    );
    if (done.ok) refresh();
  });

  const list = table([
    { label: 'Name', cell: (row) => el('span', { class: 'mono', text: row.name }) },
    { label: 'Says', cell: (row) => row.content, className: 'wrap' },
    { label: 'By', cell: (row) => nameNode(row.by_id, row.by_name) },
    {
      label: '',
      cell: (row) => button('Delete', async () => {
        const sure = await ask({
          title: `Delete the ${row.name} snippet?`,
          body: ['Staff will not be able to send it any more. Nothing already sent changes.'],
          confirmLabel: 'Delete it',
        });
        if (!sure) return;
        const done = await run(say, () => api(`/api/modmail/snippets/${encodeURIComponent(row.name)}`, { method: 'DELETE' }), 'Deleted.');
        if (done.ok) refresh();
      }, { tone: 'danger' }),
    },
  ], rows, { empty: 'No snippets are saved.' });

  return card('Snippets', [
    list,
    el('div', { class: 'formrow' }, [field('Name', name), field('Says', content), bar([add])]),
    say,
  ]);
}

function blocksCard(rows) {
  const say = notice();
  const picker = memberPicker({ label: 'Block a member' });
  const reason = el('input', { class: 'input', type: 'text', placeholder: 'why' });
  const add = button('Block', async () => {
    if (!picker.id) {
      say.say('Pick the member to block first.', 'warn');
      return;
    }
    const sure = await ask({
      title: `Block ${picker.name} from modmail?`,
      body: ['Their DMs stop opening tickets. They are not told, and it is undone from this same table.'],
      confirmLabel: 'Block them',
    });
    if (!sure) return;
    const done = await run(say, () => send('/api/modmail/blocks', 'POST', { user_id: picker.id, reason: reason.value.trim() }), 'Blocked.');
    if (done.ok) refresh();
  });

  const list = table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Since', cell: (row) => when(row.at), className: 'mono' },
    { label: 'By', cell: (row) => nameNode(row.by_id, row.by_name) },
    { label: 'Why', cell: (row) => row.reason, className: 'wrap' },
    {
      label: '',
      cell: (row) => button('Unblock', async () => {
        const done = await run(say, () => api(`/api/modmail/blocks/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }), 'Unblocked.');
        if (done.ok) refresh();
      }, { tone: 'quiet' }),
    },
  ], rows, { empty: 'Nobody is blocked.' });

  return card('Blocks', [list, picker.node, field('Why', reason), bar([add]), say]);
}

async function ticketButtonCard(placed) {
  const say = notice();
  const posted = placed.channel_id;
  const where = await channelSelect(posted || null);
  const post = button(posted ? 'Move the ticket button' : 'Post the ticket button', async () => {
    const channelId = readSelect(where, false);
    if (!channelId) {
      say.say('Pick the channel the button goes in first.', 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/modmail/panel', 'POST', { channel_id: channelId }),
      (found) => found?.message || 'The ticket button is up.',
    );
    if (done.ok) {
      keepSaying('modmail', say);
      refresh();
    }
  }, { tone: 'warn' });
  const down = button('Take it down', async () => {
    const sure = await ask({
      title: 'Take the ticket button down?',
      body: ['The message goes, and nobody can open a ticket from that channel. Tickets already open are untouched, and a DM still opens one.'],
      confirmLabel: 'Take it down',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => api('/api/modmail/panel', { method: 'DELETE' }),
      (found) => found?.message || 'The ticket button is down.',
    );
    if (done.ok) {
      keepSaying('modmail', say);
      refresh();
    }
  }, { tone: 'danger' });
  return card('Ticket button', [
    el('p', { text: BUTTON_HELP }),
    posted
      ? el('p', {}, ['It is in ', nameNode(posted), '.'])
      : sayNothing('No ticket button is posted anywhere.'),
    el('div', { class: 'formrow' }, [field('Put it in', where), bar(posted ? [post, down] : [post])]),
    say,
  ]);
}

function ticketForumCard(forumId) {
  const say = notice();
  const make = button('Make the forum', async () => {
    const done = await run(
      say,
      () => send('/api/modmail/forum', 'POST', {}),
      (found) => found?.message || 'The ticket forum is up.',
    );
    if (done.ok) {
      keepSaying('modmail', say);
      refresh();
    }
  }, { tone: 'warn' });
  return card('Ticket forum', [
    el('p', { text: FORUM_HELP }),
    forumId
      ? el('p', {}, ['Ticket posts go in ', nameNode(forumId), '.'])
      : sayNothing('There is no ticket forum yet, so forum mode would have nowhere to post.'),
    forumId
      ? sayNothing('Clear modmail_forum_channel_id below to let go of it.')
      : bar([make]),
    say,
  ]);
}

function doorShadowLine(door) {
  const home = door.shadow_channel_id;
  if (!home) return sayNothing(DOOR_SHADOW_HOMELESS);
  if (!door.channel_id) {
    return el('p', { class: 'muted' }, ['shadow — the door is rehearsing in ', nameNode(home), DOOR_SHADOW_NOWHERE_END]);
  }
  return el('p', { class: 'muted' }, [
    'shadow — the door is rehearsing in ', nameNode(home), '; nothing is in ', nameNode(door.channel_id), '.',
  ]);
}

function doorWhere(door) {
  if (door.mode === 'off') return sayNothing(DOOR_OFF_LINE);
  if (door.mode === 'shadow') return doorShadowLine(door);
  return door.channel_id
    ? el('p', {}, ['It is in ', nameNode(door.channel_id), '.'])
    : sayNothing('No front door is posted anywhere. /ask still opens the same three buttons.');
}

function doorPreview(door) {
  const buttons = [door.ticket_label, door.request_label, door.event_label];
  return el('div', { class: 'door-preview' }, [
    el('p', { class: 'door-preview-title', text: door.title }),
    el('p', { text: door.text }),
    bar(buttons.map((label) => button(label, () => {}, { tone: 'quiet', disabled: true }))),
  ]);
}

async function frontDoorCard(door) {
  const say = notice();
  const posted = door.channel_id;
  const where = await channelSelect(posted || null);
  const post = button(posted ? 'Move the front door' : 'Post the front door', async () => {
    const channelId = readSelect(where, false);
    if (!channelId) {
      say.say('Pick the channel the front door goes in first.', 'warn');
      return;
    }
    const done = await run(
      say,
      () => send('/api/frontdoor/panel', 'POST', { channel_id: channelId }),
      (found) => found?.message || 'The front door is up.',
    );
    if (done.ok) {
      keepSaying('modmail', say);
      refresh();
    }
  }, { tone: 'warn' });
  const down = button('Take it down', async () => {
    const sure = await ask({
      title: 'Take the front door down?',
      body: [
        'The message goes, and nobody can reach those three flows from that channel.',
        '/ask still works, and so does every other way in. The ticket button comes back where it was.',
      ],
      confirmLabel: 'Take it down',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => api('/api/frontdoor/panel', { method: 'DELETE' }),
      (found) => found?.message || 'The front door is down.',
    );
    if (done.ok) {
      keepSaying('modmail', say);
      refresh();
    }
  }, { tone: 'danger' });
  return card('Front door', [
    el('p', { text: DOOR_HELP }),
    doorWhere(door),
    doorPreview(door),
    el('p', { class: 'muted', text: door.mode === 'shadow' ? DOOR_SHADOW_FOLLOWS : DOOR_ONE_PER_CHANNEL }),
    el('div', { class: 'formrow' }, [field('Put it in', where), bar(posted ? [post, down] : [post])]),
    say,
  ].filter(Boolean));
}

async function panelSettings() {
  const payload = await settings(true);
  const specs = settingsNamespace(payload, 'modmail');
  const core = settingsNamespace(payload, 'core');
  const value = (key) => (specs.find((spec) => spec.key === key) || {}).value ?? null;
  const coreValue = (key) => (core.find((spec) => spec.key === key) || {}).value ?? null;
  const channelId = value('modmail_panel_channel_id');
  const forumId = value('modmail_forum_channel_id');
  const doorId = value('frontdoor_channel_id');
  const shadowId = value('frontdoor_shadow_channel_id') || coreValue('shadow_channel_id') || coreValue('log_channel_id');
  const known = [channelId, forumId, doorId, shadowId].filter(Boolean).map(String);
  if (known.length) await names(known);
  return {
    channel_id: channelId,
    message_id: value('modmail_panel_message_id'),
    forum_channel_id: forumId,
    door: {
      mode: value('frontdoor_mode'),
      channel_id: doorId,
      shadow_channel_id: shadowId,
      message_id: value('frontdoor_message_id'),
      title: value('frontdoor_title'),
      text: value('frontdoor_text'),
      ticket_label: value('frontdoor_ticket_label'),
      request_label: value('frontdoor_request_label'),
      event_label: value('frontdoor_event_label'),
    },
  };
}

async function load() {
  const query = state.status ? `?status=${encodeURIComponent(state.status)}` : '';
  const [ticketPayload, snippetPayload, blockPayload] = await Promise.all([
    api(`/api/modmail/tickets${query}`),
    api('/api/modmail/snippets'),
    api('/api/modmail/blocks'),
  ]);
  const tickets = listOf(ticketPayload, 'tickets');
  const snippets = listOf(snippetPayload, 'snippets');
  const blocks = listOf(blockPayload, 'blocks');
  await names(idsIn(tickets, ['user_id', 'closed_by_id']).concat(idsIn(snippets, ['by_id'])).concat(idsIn(blocks, ['user_id', 'by_id'])));

  const status = el('select', { class: 'input' });
  for (const one of [['open', 'open'], ['closed', 'closed'], ['', 'every ticket']]) {
    status.append(el('option', { value: one[0], text: one[1], selected: state.status === one[0] ? true : undefined }));
  }
  status.addEventListener('change', () => {
    state.status = status.value;
    state.open = null;
    refresh();
  });

  const list = table([
    { label: 'Ticket', cell: (row) => String(row.id), className: 'mono' },
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Opened', cell: (row) => when(row.opened_at), className: 'mono' },
    { label: 'Status', cell: (row) => badge(row.status, row.status === 'open' ? 'ok' : null) },
    { label: 'Came in by', cell: (row) => SOURCE_LABEL[row.source] || row.source || 'a DM to the bot' },
    {
      label: '',
      cell: (row) => button('Open', () => {
        state.open = row.id;
        refresh();
      }, { tone: 'quiet' }),
    },
  ], tickets, { empty: 'No tickets match that.' });

  const one = section('Tickets', null, { count: tickets.length });
  one.body.append(bar([field('Show', status)], { sticky: true }), list);

  const nodes = [one.node];
  if (state.open !== null) {
    const view = section(`Ticket ${state.open}`, null, { id: 'ticket', open: true });
    view.body.append(await ticketView(state.open));
    nodes.push(view.node);
  }

  const two = section('Snippets', 'Canned replies staff can send without retyping them.', {
    count: snippets.length,
  });
  two.body.append(snippetsCard(snippets));

  const three = section('Blocks', 'A blocked member’s DMs stop opening tickets, and they are not told.', {
    count: blocks.length,
  });
  three.body.append(blocksCard(blocks));

  const four = section('Doors', 'The messages Black Bloc keeps posted, and where they live.');
  const placed = await panelSettings();
  four.body.append(await frontDoorCard(placed.door));
  four.body.append(await ticketButtonCard(placed));
  four.body.append(ticketForumCard(placed.forum_channel_id));

  document.getElementById('dash').replaceChildren(
    ...nodes,
    two.node,
    three.node,
    four.node,
    await namespaceSettings('modmail'),
    await logsSection('modmail'),
  );
}

refresh = start({
  tab: 'modmail',
  load,
});
