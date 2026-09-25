import { api, listOf, names, refChannels, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import { marathonHref, marathonsSection } from './marathons-section.js';
import {
  ask,
  badge,
  bar,
  boldParts,
  button,
  card,
  channelLabel,
  el,
  field,
  idsIn,
  keepSaying,
  localWhen,
  nameNode,
  namespaceSettings,
  notice,
  run,
  sayAgain,
  sayNothing,
  section,
  table,
  when,
  whenField,
} from './ui.js';

const state = { status: 'pending', open: null };

let refresh = () => {};

const TONE = { pending: 'warn', approved: 'ok', denied: null, cancelled: null };

const SETTLED = 'This one is settled, so its details cannot be changed — only an event waiting ' +
  'for a decision or already approved can be edited.';
const PLACE_WORD = { room: 'Review channel', post: 'Review post' };
const START_HELP = 'When it begins.';
const OPEN_STATUSES = ['pending', 'approved', 'live'];
const MOVE_BUTTON = 'Move to the forum';
const MOVE_BODY = 'A post goes up in the events forum carrying the same card and the same buttons, '
  + 'the room is told where it went, and then the room is removed. The event is NOT called off, '
  + 'and the messages already in the room are not carried over — Discord cannot move those.';
const MARATHON_SETTINGS_NOTE = 'Whether marathon posts go out, where, how often a schedule is '
  + 'read, when the reminders go and which one pings, whether adding one makes an event, and '
  + 'every word the board, the reminders and the shoutouts say.';
const NOT_RESENT = 'Saving does not rewrite an announcement that is already up or a Discord ' +
  'scheduled event that already exists; the answer says when that applies.';

/** The forum and the mode as they stand, read from the same place Settings does. */
async function forumState() {
  const specs = settingsNamespace(await settings(true), 'events');
  const held = (key) => ((specs.find((one) => one.key === key) || {}).value ?? null);
  return { id: held('events_forum_channel_id'), mode: held('events_review_mode') };
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
    line('Where', row.where_label),
    line('Starts', when(row.starts_at)),
    line('Ends', when(row.ends_at)),
    line('How long', row.duration),
    line('Status', badge(row.status, TONE[row.status] || null)),
    line('Asked by', nameNode(row.requester_id, row.requester_name)),
    line('Decided by', nameNode(row.decided_by_id, row.decided_by_name)),
    line('Decided', when(row.decided_at)),
    line('Why not', row.deny_reason),
    line('Now', row.moved_word),
    line(PLACE_WORD[row.review_kind] || PLACE_WORD.room, nameNode(row.review_channel_id)),
    line('Announced', row.announced ? 'yes' : 'no'),
    line('Scheduled event', row.scheduled ? 'yes' : 'no'),
    line('Proposed', when(row.created_at)),
    row.marathon
      ? line(row.marathon.run ? 'Marathon run' : 'Marathon', el('a', { href: marathonHref(row.marathon.id) }, boldParts(row.marathon.line)))
      : null,
  ]);
}

/** A marathon's drawer opens its event here: every status, so a settled one is still found. */
function openEvent(eventId) {
  state.status = '';
  state.open = eventId;
  refresh();
}

const NOWHERE = '— nowhere in particular —';
const SOMEWHERE_ELSE = '— somewhere else —';
const ELSEWHERE = '__other__';
const WHERE_HELP = 'A voice or stage channel gives everybody a Join button on the Discord '
  + 'event; anything else is written on it as words.';
const BESIDE_HELP = 'Optional beside a channel — a Twitch link, say.';
const INSTEAD_HELP = 'Only used when it is somewhere else.';

/** A channel from the server, a typed place, or both — the box is never taken away. */
function whereControl(row, channels) {
  const select = el('select', { class: 'input' });
  select.append(el('option', { value: '', text: NOWHERE }));
  select.append(el('option', { value: ELSEWHERE, text: SOMEWHERE_ELSE }));
  for (const [kind, label] of [['voice', 'Voice channels'], ['text', 'Text channels']]) {
    const group = el('optgroup', { label });
    for (const channel of channels.filter((one) => one.type === kind)) {
      group.append(el('option', {
        value: String(channel.id),
        text: channelLabel(channel, channels),
        selected: String(row.where_channel_id || '') === String(channel.id) ? true : undefined,
      }));
    }
    if (group.childElementCount) select.append(group);
  }
  if (row.where_kind === 'other') select.value = ELSEWHERE;
  else if (!row.where_channel_id) select.value = '';

  const typed = el('input', { class: 'input', type: 'text', value: row.location || '', placeholder: 'twitch.tv/blackbloc' });
  const typedField = field('Where, or a link', typed, INSTEAD_HELP);
  const hint = typedField.querySelector('.field-help');
  const sayHint = () => {
    const beside = select.value !== '' && select.value !== ELSEWHERE;
    hint.textContent = beside ? BESIDE_HELP : INSTEAD_HELP;
  };
  select.addEventListener('change', sayHint);
  sayHint();

  return {
    nodes: [field('Where', select, WHERE_HELP), typedField],
    payload: () => {
      const location = typed.value.trim();
      if (select.value === '') return { where_kind: null, where_channel_id: null, location };
      if (select.value === ELSEWHERE) {
        return { where_kind: 'other', where_channel_id: null, location };
      }
      const picked = channels.find((one) => String(one.id) === select.value);
      return {
        where_kind: picked && picked.type === 'voice' ? 'voice' : 'text',
        where_channel_id: select.value,
        location,
      };
    },
  };
}

async function editCard(row, say) {
  if (!row.editable) return sayNothing(SETTLED);
  const title = el('input', { class: 'input', type: 'text', value: row.title || '' });
  const description = el('textarea', { class: 'input area', rows: '3' });
  description.value = row.description || '';
  const where = whereControl(row, await refChannels());
  const start = whenField({ label: 'Starts', value: localWhen(row.starts_at), min: localWhen(), help: START_HELP });
  const duration = el('input', { class: 'input', type: 'text', value: row.duration || '', placeholder: '2h' });

  const save = button('Save', async () => {
    const done = await run(
      say,
      () => send(`/api/events/${encodeURIComponent(row.id)}`, 'PUT', {
        title: title.value.trim(),
        description: description.value.trim(),
        start: start.value(),
        duration: duration.value.trim(),
        tz: start.tz(),
        ...where.payload(),
      }),
      (found) => [found?.message, ...(found?.notes || [])].filter(Boolean).join(' '),
    );
    if (done.ok) {
      keepSaying('events', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  return card('Change it', [
    el('p', { class: 'field-help', text: NOT_RESENT }),
    field('Title', title),
    field('What it is', description),
    ...where.nodes,
    start.node,
    field('How long', duration, 'Like 1h30m, 2h or 45m; blank means two hours.'),
    bar([save]),
  ]);
}

function decide(row, say, forum) {
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
  const movable = row.review_channel_id && row.review_kind !== 'post'
    && OPEN_STATUSES.includes(row.status) && forum && forum.id && forum.mode === 'forum';
  if (movable) {
    buttons.push(button(MOVE_BUTTON, async () => {
      const sure = await ask({
        title: `Move “${row.title}” into the forum?`,
        body: [MOVE_BODY],
        confirmLabel: 'Move it',
        tone: 'warn',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => send(`/api/events/${encodeURIComponent(row.id)}/forum`, 'POST', {}),
        (found) => found?.message,
      );
      if (done.ok) refresh();
    }, { tone: 'warn' }));
  }
  return el('div', { class: 'bar' }, buttons);
}

/**
 * The one place the events forum is made from the website; the bot presses the same path.
 * `namespaceSettings` draws the `events_forum_channel_id` row but gives no per-row action
 * slot, so this finds that row (by the `data-key` the shared code already stamps on it, in
 * the block `namespaceSettings('events')` returned) and appends the action beside it — shown
 * only while the key is unset, gone the moment Make the forum succeeds and the page reloads.
 */
function forumMakeAction(settingsNode, forumId) {
  if (forumId) return;
  const row = settingsNode.querySelector('[data-key="events_forum_channel_id"]');
  if (!row) return;
  const say = notice();
  say.classList.add('setrow-say');
  const make = button('Make the forum', async () => {
    const done = await run(
      say,
      () => send('/api/events/forum', 'POST', {}),
      (found) => found?.message || 'The events forum is up.',
    );
    if (done.ok) {
      keepSaying('events', say);
      refresh();
    }
  }, { tone: 'warn' });
  row.append(bar([make]), say);
}

async function load() {
  const query = state.status ? `?status=${encodeURIComponent(state.status)}` : '';
  const payload = await api(`/api/events${query}`);
  const rows = listOf(payload, 'events');
  await names(idsIn(rows, ['requester_id', 'decided_by_id', 'review_channel_id']));
  const forum = await forumState();

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
    { label: 'Title', cell: (row) => el('span', {}, [el('span', { text: row.title }), row.marathon ? badge('marathon', 'ok') : null, row.marathon && row.marathon.run ? badge('marathon run', 'ok') : null]), className: 'wrap' },
    { label: 'Asked by', cell: (row) => nameNode(row.requester_id, row.requester_name) },
    { label: 'Starts', cell: (row) => when(row.starts_at), className: 'mono' },
    { label: 'Status', cell: (row) => badge(row.status, TONE[row.status] || null) },
    { label: 'Decided by', cell: (row) => nameNode(row.decided_by_id, row.decided_by_name) },
    { label: 'Why not', cell: (row) => row.deny_reason, className: 'wrap' },
    { label: '', cell: (row) => decide(row, say, forum) },
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
    detail.body.append(detailCard(open), await editCard(open, editSay), editSay);
    nodes.push(detail.node);
  }

  nodes.push(await marathonsSection({ reload: () => refresh(), openEvent }));

  const eventsSettings = await namespaceSettings('events');
  forumMakeAction(eventsSettings, forum.id);

  document.getElementById('dash').replaceChildren(
    ...nodes,
    eventsSettings,
    await namespaceSettings('marathon', { title: 'Marathon settings', note: MARATHON_SETTINGS_NOTE, onSaved: () => refresh() }),
    await logsSection('events', { title: 'Events log' }),
    await logsSection('marathon', { title: 'Marathons log' }),
  );
}

refresh = start({
  tab: 'events',
  load,
});
