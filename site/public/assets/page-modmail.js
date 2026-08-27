import { api, listOf, names, send } from './api.js';
import { start } from './app.js';
import {
  ask,
  badge,
  bar,
  button,
  card,
  el,
  field,
  idsIn,
  memberPicker,
  nameNode,
  namespaceSettings,
  notice,
  run,
  sayNothing,
  section,
  table,
  when,
} from './ui.js';

const state = { status: 'open', open: null };

let refresh = () => {};

const DIRECTION_LABEL = { in: 'from the member', out: 'from staff', note: 'staff note — the member never sees this' };

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
    {
      label: '',
      cell: (row) => button('Open', () => {
        state.open = row.id;
        refresh();
      }, { tone: 'quiet' }),
    },
  ], tickets, { empty: 'No tickets match that.' });

  const one = section('Tickets');
  one.body.append(field('Show', status), list);
  if (state.open !== null) one.body.append(await ticketView(state.open));

  const two = section('Snippets and blocks');
  two.body.append(snippetsCard(snippets), blocksCard(blocks));

  document.getElementById('dash').replaceChildren(
    one.node,
    two.node,
    await namespaceSettings('modmail'),
  );
}

refresh = start({
  tab: 'modmail',
  subtitle: 'Tickets, replies, snippets and blocks.',
  load,
});
