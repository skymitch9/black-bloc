import { api, listOf, names, send } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ask,
  badge,
  bar,
  button,
  card,
  el,
  field,
  idsIn,
  keepSaying,
  nameNode,
  namespaceSettings,
  notice,
  run,
  sayAgain,
  sayNothing,
  section,
  table,
  when,
} from './ui.js';

const state = { status: 'pending', open: null };

let refresh = () => {};

const TONE = { pending: 'warn', approved: 'ok', denied: null, cancelled: null };

const HERE = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
const SETTLED = 'This one is settled, so its details cannot be changed — only an event waiting ' +
  'for a decision or already approved can be edited.';
const NOT_RESENT = 'Saving does not rewrite an announcement that is already up or a Discord ' +
  'scheduled event that already exists; the answer says when that applies.';

/** The `YYYY-MM-DD HH:MM` the API reads, in this browser's own zone. */
function localStart(iso) {
  const when = iso ? new Date(iso) : null;
  if (when === null || Number.isNaN(when.getTime())) return '';
  const pad = (value) => String(value).padStart(2, '0');
  return `${when.getFullYear()}-${pad(when.getMonth() + 1)}-${pad(when.getDate())} `
    + `${pad(when.getHours())}:${pad(when.getMinutes())}`;
}

function line(label, value) {
  return el('div', { class: 'field' }, [
    el('span', { class: 'field-label', text: label }),
    value instanceof Node ? value : el('span', { text: value === null || value === undefined || value === '' ? '—' : String(value) }),
  ]);
}

function detailCard(row) {
  return card(`What #${row.id} says`, [
    line('Title', row.title),
    line('What it is', row.description),
    line('Where', row.location),
    line('Starts', when(row.starts_at)),
    line('Ends', when(row.ends_at)),
    line('How long', row.duration),
    line('Status', badge(row.status, TONE[row.status] || null)),
    line('Asked by', nameNode(row.requester_id, row.requester_name)),
    line('Decided by', nameNode(row.decided_by_id, row.decided_by_name)),
    line('Decided', when(row.decided_at)),
    line('Why not', row.deny_reason),
    line('Review channel', nameNode(row.review_channel_id)),
    line('Announced', row.announced ? 'yes' : 'no'),
    line('Scheduled event', row.scheduled ? 'yes' : 'no'),
    line('Proposed', when(row.created_at)),
  ]);
}

function editCard(row, say) {
  if (!row.editable) return sayNothing(SETTLED);
  const title = el('input', { class: 'input', type: 'text', value: row.title || '' });
  const description = el('textarea', { class: 'input area', rows: '3' });
  description.value = row.description || '';
  const location = el('input', { class: 'input', type: 'text', value: row.location || '' });
  const start = el('input', { class: 'input', type: 'text', value: localStart(row.starts_at), placeholder: '2026-09-14 19:30' });
  const duration = el('input', { class: 'input', type: 'text', value: row.duration || '', placeholder: '2h' });

  const save = button('Save', async () => {
    const done = await run(
      say,
      () => send(`/api/events/${encodeURIComponent(row.id)}`, 'PUT', {
        title: title.value.trim(),
        description: description.value.trim(),
        location: location.value.trim(),
        start: start.value.trim(),
        duration: duration.value.trim(),
        tz: HERE,
      }),
      (found) => [found?.message, ...(found?.notes || [])].filter(Boolean).join(' '),
    );
    if (done.ok) {
      keepSaying('events', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  return card('Change it', [
    el('p', { class: 'field-help', text: `Times are read in ${HERE}. ${NOT_RESENT}` }),
    field('Title', title),
    field('What it is', description),
    field('Where', location),
    field('Starts', start, 'YYYY-MM-DD HH:MM on a 24-hour clock.'),
    field('How long', duration, 'Like 1h30m, 2h or 45m; blank means two hours.'),
    bar([save]),
  ]);
}

function decide(row, say) {
  const buttons = [button(state.open === row.id ? 'Close' : 'Open', () => {
    state.open = state.open === row.id ? null : row.id;
    refresh();
  }, { tone: 'quiet' })];
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
  await names(idsIn(rows, ['requester_id', 'decided_by_id', 'review_channel_id']));

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

  const one = section(
    'Queue',
    'The same lock and the same allowed-transition check as the buttons in Discord.',
    { count: rows.length },
  );
  one.body.append(bar([field('Show', status)], { sticky: true }), queue, sayAgain('events', say));

  const nodes = [one.node];
  const open = state.open === null ? null : rows.find((row) => row.id === state.open);
  if (open) {
    const detail = section(`Event #${open.id} — ${open.title}`, null, { id: 'detail', open: true });
    const editSay = notice();
    detail.body.append(detailCard(open), editCard(open, editSay), editSay);
    nodes.push(detail.node);
  }

  document.getElementById('dash').replaceChildren(
    ...nodes,
    await namespaceSettings('events'),
    await logsSection('events'),
  );
}

refresh = start({
  tab: 'events',
  load,
});
