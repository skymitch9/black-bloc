import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import { TONE, eventDrawerFor, eventMoves, forumMove, openEvent, ownChangeForm } from './event-drawer.js';
import { isMemberOnly } from './shell.js';
import { marathonsSection } from './marathons-section.js';
import {
  ask,
  badge,
  bar,
  button,
  closeDrawer,
  el,
  field,
  filterChip,
  foldout,
  idsIn,
  keepSaying,
  nameNode,
  notice,
  openDrawer,
  run,
  sayAgain,
  section,
  settingsPanel,
  table,
  when,
} from './ui.js';

const state = { status: 'pending' };

let refresh = () => {};

const QUEUE_TITLE = 'Events';
const MACHINERY_TITLE = 'Settings and logs';
const EVENTS_SETTINGS = 'Events';
const MARATHON_SETTINGS = 'Marathons';
const LOG_TITLE = 'Log';
const OWN_TITLE = 'Your events';
const NO_OWN = 'You have not proposed any events.';
const CANCEL_IT = 'Cancel it';
const CANCEL_ASK = 'Cancel this event?';
const CANCEL_BODY = 'It is called off for everyone, and staff see that you cancelled it.';
const LOG_CHIPS = [{ feature: 'events', label: 'Events' }, { feature: 'marathon', label: 'Marathons' }];
/** The forum and the mode as they stand, read from the same place Settings does. */
async function forumState() {
  const specs = settingsNamespace(await settings(true), 'events');
  const held = (key) => ((specs.find((one) => one.key === key) || {}).value ?? null);
  return { id: held('events_forum_channel_id'), mode: held('events_review_mode') };
}

/** A marathon's drawer opens its event here: every status, so a settled one is still found. */
function showEvent(eventId) {
  state.status = '';
  refresh();
  openEvent(eventId);
}

function rowMoves(row, say, forum) {
  const after = (done) => {
    if (done.ok) refresh();
  };
  return el('div', { class: 'bar' }, [
    button('Open', () => openEvent(row.id), { tone: 'quiet' }),
    ...eventMoves(row, say, after),
    forumMove(row, say, forum, after),
  ]);
}

/**
 * The one place the events forum is made from the website; the bot presses the same path.
 * `settingsPanel` draws the `events_forum_channel_id` row but gives no per-row action
 * slot, so this finds that row (by the `data-key` the shared code already stamps on it, in
 * the block `settingsFold('events')` returned) and appends the action beside it — shown
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

function ownFacts(row) {
  const line = (label, text) => (text ? el('p', { class: 'field-help' }, [el('strong', { text: `${label}: ` }), el('span', { text })]) : null);
  return [
    el('p', { class: 'field-help' }, [badge(row.status, TONE[row.status] || null)]),
    line('Starts', row.starts_at ? when(row.starts_at) : ''),
    line('How long', row.duration),
    line('Where', row.where_label),
    line('What it is', row.description),
    line('Why not', row.deny_reason),
  ].filter(Boolean);
}

function openOwn(row, message = '') {
  const say = notice();
  if (message) say.say(message, 'ok');
  const cancel = row.cancellable
    ? button(CANCEL_IT, async () => {
      const sure = await ask({ title: CANCEL_ASK, body: [CANCEL_BODY], confirmLabel: CANCEL_IT });
      if (!sure) return;
      const done = await run(
        say,
        () => send(`/api/mine/events/${encodeURIComponent(row.id)}/cancel`, 'POST', {}),
        (found) => found?.message || 'Cancelled.',
      );
      if (!done.ok) return;
      keepSaying('events', say);
      closeDrawer();
      refresh();
    }, { tone: 'quiet' })
    : null;
  const change = row.editable
    ? ownChangeForm(row, async (said, found) => {
      refresh();
      openOwn(found?.event || row, said);
    })
    : null;
  openDrawer(row.title || `Event #${row.id}`, [say, ...ownFacts(row), change, cancel ? bar([cancel]) : null].filter(Boolean));
}

async function loadOwn() {
  const rows = listOf(await api('/api/mine/events'), 'events');
  const say = notice();
  const queue = table([
    { label: 'Title', cell: (row) => row.title, className: 'wrap' },
    { label: 'Starts', cell: (row) => when(row.starts_at), className: 'mono' },
    { label: 'Where', cell: (row) => row.where_label || '', className: 'wrap' },
    { label: 'Status', cell: (row) => badge(row.status, TONE[row.status] || null) },
    { label: 'Why not', cell: (row) => row.deny_reason, className: 'wrap' },
    { label: '', cell: (row) => bar([button('Open', () => openOwn(row), { tone: 'quiet' })]) },
  ], rows, { empty: NO_OWN });
  const one = section(OWN_TITLE, null, { count: rows.length, id: 'queue' });
  one.body.append(queue, sayAgain('events', say));
  document.getElementById('dash').replaceChildren(one.node);
}

async function load(me) {
  if (isMemberOnly(me)) return loadOwn();
  return loadStaff();
}

async function loadStaff() {
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
    { label: '', cell: (row) => rowMoves(row, say, forum) },
  ], rows, { empty: 'Nothing matches that.' });

  const one = section(QUEUE_TITLE, null, { count: rows.length, id: 'queue' });
  one.body.append(bar([field('Show', status)], { sticky: true }), queue, sayAgain('events', say));

  const marathons = await marathonsSection({ reload: () => refresh(), openEvent: showEvent });
  document.getElementById('dash').replaceChildren(one.node, marathons, await machinerySection(forum));
  eventDrawerFor({ reload: () => refresh(), forum: forumState });
}

function unsectioned(node, id) {
  const inner = node.querySelector('.sect-inner');
  return el('div', { id }, inner ? [...inner.childNodes] : [node]);
}

async function settingsFold(namespace, title, extra = {}) {
  const specs = settingsNamespace(await settings(), namespace);
  const panel = await settingsPanel(specs, {
    where: title,
    empty: `The bot registers no settings under ${namespace}.`,
    ...extra,
  });
  return { panel, fold: foldout(title, [panel], { count: specs.length }) };
}

async function logFold() {
  const holders = await Promise.all(LOG_CHIPS.map(async (one) => ({
    feature: one.feature,
    node: unsectioned(await logsSection(one.feature, { title: one.label }), `sect-logs-${one.feature}`),
  })));
  const chips = el('div', { class: 'chipbar' });
  const state = { pick: LOG_CHIPS[0].feature };
  const paint = () => {
    chips.replaceChildren(...LOG_CHIPS.map((one) => filterChip(one.label, state.pick === one.feature, () => {
      state.pick = one.feature;
      paint();
    })));
    for (const holder of holders) holder.node.hidden = holder.feature !== state.pick;
  };
  paint();
  return foldout(LOG_TITLE, [chips, ...holders.map((one) => one.node)]);
}

async function machinerySection(forum) {
  const group = section(MACHINERY_TITLE, null, { id: 'settings' });
  const events = await settingsFold('events', EVENTS_SETTINGS);
  forumMakeAction(events.panel, forum.id);
  const marathons = await settingsFold('marathon', MARATHON_SETTINGS, { onSaved: () => refresh() });
  marathons.fold.id = 'sect-marathon-settings';
  group.body.append(events.fold, marathons.fold, await logFold());
  return group.node;
}

refresh = start({
  tab: 'events',
  load,
});
