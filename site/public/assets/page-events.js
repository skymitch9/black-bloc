import { api, listOf, names, refChannels, send } from './api.js';
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

const state = { status: 'pending', open: null, trainScope: 'upcoming', train: null };

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
    line('Where', row.where_label),
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
  for (const [kind, label, mark] of [['voice', 'Voice channels', '🔊 '], ['text', 'Text channels', '#']]) {
    const group = el('optgroup', { label });
    for (const channel of channels.filter((one) => one.type === kind)) {
      group.append(el('option', {
        value: String(channel.id),
        text: `${mark}${channel.name}`,
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
  const start = el('input', { class: 'input', type: 'text', value: localStart(row.starts_at), placeholder: '2026-09-14 19:30' });
  const duration = el('input', { class: 'input', type: 'text', value: row.duration || '', placeholder: '2h' });

  const save = button('Save', async () => {
    const done = await run(
      say,
      () => send(`/api/events/${encodeURIComponent(row.id)}`, 'PUT', {
        title: title.value.trim(),
        description: description.value.trim(),
        start: start.value.trim(),
        duration: duration.value.trim(),
        tz: HERE,
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
    el('p', { class: 'field-help', text: `Times are read in ${HERE}. ${NOT_RESENT}` }),
    field('Title', title),
    field('What it is', description),
    ...where.nodes,
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

const TRAIN_TONE = { open: 'ok', locked: 'warn', live: 'warn', done: null, cancelled: null };
const NO_TRAINS = 'No raid train matches that. Staff start one below, or with /raidtrain in Discord.';
const TRAIN_OFF = 'Raid trains are {mode} at the moment, so nothing is posted and no reminder is sent. The Settings below turn them on.';

function trainHealth(status) {
  if (!status) return null;
  const bits = [
    `mode ${status.mode}`,
    status.running ? `sweeping every ${status.every_minutes} min` : 'the sweep is not running',
    `last good sweep ${when(status.last_ok_at)}`,
    `${status.claimed}/${status.slots} slot(s) claimed`,
  ];
  if (status.last_error) bits.push(`last error: ${status.last_error}`);
  return el('p', { class: 'field-help', text: bits.join(' · ') });
}

/** One slot, with the two staff controls that act on it. Never a control nobody may use. */
function slotRow(train, slot, say, mayEdit) {
  const who = slot.user_id === null
    ? el('span', { class: 'muted', text: 'open' })
    : nameNode(slot.user_id, slot.user_name);
  const buttons = [];
  if (mayEdit && slot.user_id !== null) {
    buttons.push(button('Take off', async () => {
      const sure = await ask({
        title: `Take ${slot.user_name || 'them'} off slot #${slot.position}?`,
        body: ['The hour goes back on the lineup for somebody else to claim, and the lineup post is redrawn.'],
        confirmLabel: 'Take them off',
      });
      if (!sure) return;
      const done = await run(say, () => send(`/api/raidtrains/${train.id}/slots/${slot.position}`, 'POST', { member_id: null }), (found) => found?.message);
      if (done.ok) refresh();
    }, { tone: 'quiet' }));
  }
  if (mayEdit && slot.user_id === null) {
    buttons.push(button('Put somebody in', async () => {
      const memberId = el('input', { class: 'input', type: 'text', placeholder: 'their Discord id' });
      const sure = await ask({
        title: `Who takes slot #${slot.position}?`,
        body: [
          'They need a Twitch channel linked, because the lineup carries the name the streamer before them raids.',
          field('Member id', memberId),
        ],
        confirmLabel: 'Put them in',
        tone: 'warn',
      });
      if (!sure || !memberId.value.trim()) return;
      const done = await run(say, () => send(`/api/raidtrains/${train.id}/slots/${slot.position}`, 'POST', { member_id: memberId.value.trim() }), (found) => found?.message);
      if (done.ok) refresh();
    }));
  }
  return {
    position: `#${slot.position}`,
    starts: when(slot.starts_at),
    who,
    login: slot.twitch_login ? el('a', { href: `https://twitch.tv/${slot.twitch_login}`, text: slot.twitch_login, rel: 'noreferrer' }) : null,
    checked: slot.checked_in_at ? badge('live', 'ok') : null,
    tools: el('div', { class: 'bar' }, buttons),
  };
}

function trainTools(train, say) {
  const buttons = [button(state.train === train.id ? 'Close' : 'Open', () => {
    state.train = state.train === train.id ? null : train.id;
    refresh();
  }, { tone: 'quiet' })];
  if (train.status === 'open' || train.status === 'locked') {
    const to = train.status === 'open' ? 'locked' : 'open';
    buttons.push(button(to === 'locked' ? 'Lock' : 'Unlock', async () => {
      const done = await run(say, () => send(`/api/raidtrains/${train.id}/status`, 'POST', { status: to }), (found) => found?.message);
      if (done.ok) refresh();
    }));
    buttons.push(button('Cancel', async () => {
      const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — everybody who signed up is told this' });
      const sure = await ask({
        title: `Cancel “${train.title}”?`,
        body: ['Everybody holding a slot is DMed, and the lineup post says it is off.', field('Reason', reason)],
        confirmLabel: 'Cancel it',
      });
      if (!sure) return;
      const done = await run(say, () => send(`/api/raidtrains/${train.id}/status`, 'POST', { status: 'cancelled', reason: reason.value.trim() }), (found) => found?.message);
      if (done.ok) refresh();
    }, { tone: 'danger' }));
  }
  return el('div', { class: 'bar' }, buttons);
}

function newTrainCard(say) {
  const title = el('input', { class: 'input', type: 'text', placeholder: 'Saturday raid train' });
  const description = el('textarea', { class: 'input area', rows: '2' });
  const start = el('input', { class: 'input', type: 'text', placeholder: '2026-09-14 19:30' });
  const minutes = el('input', { class: 'input', type: 'text', value: '60' });
  const count = el('input', { class: 'input', type: 'text', value: '8' });

  const make = button('Start it', async () => {
    const done = await run(say, () => send('/api/raidtrains', 'POST', {
      title: title.value.trim(),
      description: description.value.trim(),
      start: start.value.trim(),
      tz: HERE,
      slot_minutes: Number(minutes.value.trim() || 60),
      slot_count: Number(count.value.trim() || 0),
    }), (found) => found?.message);
    if (done.ok) refresh();
  }, { tone: 'warn', small: false });

  return card('Start a raid train', [
    el('p', { class: 'field-help', text: `Times are read in ${HERE}. The lineup is posted once and edited in place after that.` }),
    field('Title', title),
    field('What it is', description),
    field('Starts', start, 'YYYY-MM-DD HH:MM on a 24-hour clock.'),
    field('Minutes per slot', minutes, '15 to 720.'),
    field('How many slots', count, '1 to 24 — Discord will not carry a longer lineup in one message.'),
    bar([make]),
  ]);
}

async function raidTrainsSection() {
  const query = `?scope=${encodeURIComponent(state.trainScope)}`;
  const [rows, status] = await Promise.all([
    api(`/api/raidtrains${query}`).then((payload) => listOf(payload, 'raidtrains')),
    api('/api/raidtrains/status').catch(() => null),
  ]);
  await names(idsIn(rows, ['organizer_id']));

  const say = notice();
  const scope = el('select', { class: 'input' });
  for (const one of [['upcoming', 'coming up'], ['past', 'finished and cancelled'], ['all', 'every train']]) {
    scope.append(el('option', { value: one[0], text: one[1], selected: state.trainScope === one[0] ? true : undefined }));
  }
  scope.addEventListener('change', () => {
    state.trainScope = scope.value;
    state.train = null;
    refresh();
  });

  const trains = table([
    { label: 'Train', cell: (row) => String(row.id), className: 'mono' },
    { label: 'Title', cell: (row) => row.title, className: 'wrap' },
    { label: 'Starts', cell: (row) => when(row.starts_at), className: 'mono' },
    { label: 'Slots', cell: (row) => `${row.filled}/${row.slots_total}`, className: 'mono' },
    { label: 'How long each', cell: (row) => `${row.slot_minutes} min`, className: 'mono' },
    { label: 'Status', cell: (row) => badge(row.status, TRAIN_TONE[row.status] || null) },
    { label: 'Organizer', cell: (row) => nameNode(row.organizer_id, row.organizer_name) },
    { label: '', cell: (row) => trainTools(row, say) },
  ], rows, { empty: NO_TRAINS });

  const group = section(
    'Raid trains',
    'Sign-ups by the hour, and a DM to each streamer before their slot.',
    { count: rows.length, id: 'raidtrains' },
  );
  if (status && status.mode !== 'on') {
    group.body.append(notice(TRAIN_OFF.replace('{mode}', status.mode), 'warn'));
  }
  const health = trainHealth(status);
  if (health) group.body.append(health);
  group.body.append(bar([field('Show', scope)], { sticky: true }), trains, sayAgain('raidtrains', say));

  const newSay = notice();
  group.body.append(newTrainCard(newSay), newSay);

  const open = state.train === null ? null : rows.find((row) => row.id === state.train);
  if (open) {
    const detail = await api(`/api/raidtrains/${encodeURIComponent(open.id)}`);
    const slotSay = notice();
    await names(idsIn(detail.slots || [], ['user_id']));
    const grid = table([
      { label: 'Slot', cell: (row) => row.position, className: 'mono' },
      { label: 'Starts', cell: (row) => row.starts, className: 'mono' },
      { label: 'Who', cell: (row) => row.who },
      { label: 'Twitch', cell: (row) => row.login },
      { label: '', cell: (row) => row.checked },
      { label: '', cell: (row) => row.tools },
    ], (detail.slots || []).map((slot) => slotRow(detail, slot, slotSay, detail.editable)), {
      empty: 'This train has no slots, which should not be possible — tell a Lead.',
    });
    const swapSay = notice();
    const first = el('input', { class: 'input', type: 'text', placeholder: '1' });
    const second = el('input', { class: 'input', type: 'text', placeholder: '2' });
    const swap = button('Change them round', async () => {
      const done = await run(swapSay, () => send(`/api/raidtrains/${detail.id}/swap`, 'POST', {
        a: Number(first.value.trim()),
        b: Number(second.value.trim()),
      }), (found) => found?.message);
      if (done.ok) refresh();
    });
    const inside = section(`Train #${detail.id} — ${detail.title}`, detail.status_word, { id: 'raidtrain-detail', open: true });
    inside.body.append(
      grid,
      slotSay,
      detail.editable
        ? card('Change two slots round', [
          el('p', { class: 'field-help', text: 'The people move; the times belong to the position and stay put.' }),
          field('One slot', first),
          field('The other', second),
          bar([swap]),
          swapSay,
        ])
        : sayNothing('This train is settled, so its lineup cannot be changed any more.'),
    );
    return [group.node, inside.node];
  }
  return [group.node];
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
    detail.body.append(detailCard(open), await editCard(open, editSay), editSay);
    nodes.push(detail.node);
  }

  document.getElementById('dash').replaceChildren(
    ...nodes,
    await namespaceSettings('events'),
    await logsSection('events'),
    ...(await raidTrainsSection()),
    await namespaceSettings('raidtrain', { title: 'Raid train settings' }),
    await logsSection('raidtrain', { title: 'Raid train logs' }),
  );
}

refresh = start({
  tab: 'events',
  load,
});
