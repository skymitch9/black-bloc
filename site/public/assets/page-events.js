import { api, listOf, names, send } from './api.js';
import { start } from './app.js';
import {
  ask,
  badge,
  bar,
  button,
  el,
  field,
  idsIn,
  nameNode,
  namespaceSettings,
  notice,
  run,
  section,
  table,
  when,
} from './ui.js';

const state = { status: 'pending' };

let refresh = () => {};

const TONE = { pending: 'warn', approved: 'ok', denied: null, cancelled: null };

function decide(row, say) {
  const buttons = [];
  if (row.status === 'pending') {
    buttons.push(button('Approve', async () => {
      const sure = await ask({
        title: `Approve “${row.title}”?`,
        body: ['The review channel is updated, the announcement goes out at the configured time, and a Discord scheduled event is made if that setting is on.'],
        confirmLabel: 'Approve it',
        tone: 'warn',
      });
      if (!sure) return;
      const done = await run(say, () => send(`/api/events/${encodeURIComponent(row.id)}/approve`, 'POST', {}), `Approved “${row.title}”.`);
      if (done.ok) refresh();
    }));
    buttons.push(button('Deny', async () => {
      const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — they are told this' });
      const sure = await ask({
        title: `Deny “${row.title}”?`,
        body: [
          'The person who asked is told, and is shown the reason you type here.',
          field('Reason', reason),
        ],
        confirmLabel: 'Deny it',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => send(`/api/events/${encodeURIComponent(row.id)}/deny`, 'POST', { reason: reason.value.trim() }),
        `Denied “${row.title}”.`,
      );
      if (done.ok) refresh();
    }, { tone: 'danger' }));
  }
  if (row.status !== 'cancelled' && row.status !== 'denied') {
    buttons.push(button('Cancel', async () => {
      const sure = await ask({
        title: `Cancel “${row.title}”?`,
        body: ['Anyone who was told about it is told it is off, and the scheduled event is removed.'],
        confirmLabel: 'Cancel it',
      });
      if (!sure) return;
      const done = await run(say, () => send(`/api/events/${encodeURIComponent(row.id)}/cancel`, 'POST', {}), `Cancelled “${row.title}”.`);
      if (done.ok) refresh();
    }, { tone: 'quiet' }));
  }
  return el('div', { class: 'bar' }, buttons);
}

async function load() {
  const query = state.status ? `?status=${encodeURIComponent(state.status)}` : '';
  const payload = await api(`/api/events${query}`);
  const rows = listOf(payload, 'events');
  await names(idsIn(rows, ['requester_id', 'decided_by_id']));

  const say = notice();
  const status = el('select', { class: 'input' });
  for (const one of [['pending', 'waiting for a decision'], ['approved', 'approved'], ['denied', 'denied'], ['cancelled', 'cancelled'], ['', 'every event']]) {
    status.append(el('option', { value: one[0], text: one[1], selected: state.status === one[0] ? true : undefined }));
  }
  status.addEventListener('change', () => {
    state.status = status.value;
    refresh();
  });

  const queue = table([
    { label: 'Event', cell: (row) => String(row.id), className: 'mono' },
    { label: 'Title', cell: (row) => row.title, className: 'wrap' },
    { label: 'Asked by', cell: (row) => nameNode(row.requester_id, row.requester_name) },
    { label: 'Starts', cell: (row) => when(row.starts_at), className: 'mono' },
    { label: 'Status', cell: (row) => badge(row.status, TONE[row.status] || null) },
    { label: 'Decided by', cell: (row) => nameNode(row.decided_by_id, row.decided_by_name) },
    { label: 'Why not', cell: (row) => row.deny_reason, className: 'wrap' },
    { label: '', cell: (row) => decide(row, say) },
  ], rows, { empty: 'Nothing matches that.' });

  const one = section('Queue', 'Approve, deny and cancel go through the same lock and the same allowed-transition check as the buttons in Discord.');
  one.body.append(field('Show', status), queue, say);

  document.getElementById('dash').replaceChildren(one.node, await namespaceSettings('events'));
}

refresh = start({
  tab: 'events',
  subtitle: 'The approval queue and what happens to an approved event.',
  load,
});
