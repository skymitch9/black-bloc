import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ask,
  badge,
  bar,
  boldParts,
  button,
  card,
  closeDrawer,
  el,
  field,
  foldout,
  icon,
  idsIn,
  keepSaying,
  modeChip,
  nameNode,
  notice,
  openDrawer,
  run,
  sayAgain,
  sayNothing,
  searchField,
  section,
  segment,
  sentenceFor,
  settingsPanel,
  table,
  when,
} from './ui.js';

const state = { scope: 'upcoming', query: '' };
const shown = { id: null };
let refresh = () => {};
let deepLinked = false;

const HERE = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

const TONE = { open: 'ok', locked: 'warn', live: 'warn', done: null, cancelled: null };
const STATE_OF = { open: 'ok', locked: 'warn', live: 'info', done: null, cancelled: 'danger' };
const EVENT_TONE = { pending: 'warn', approved: 'ok', live: 'ok', denied: null, cancelled: null };

const LIST_NOTE = 'Every raid train, the hours on it and who holds them. A row opens the '
  + 'lineup: claim or free an hour, change two round, lock it, call it off, or give it an event.';
const MACHINERY_NOTE = 'The reference half of the page: the raid-train settings, and everything '
  + 'raid trains have done. Both are shut until you want them.';
const SETTINGS_NOTE = 'Whether raid trains are on, where the lineup post goes, who may build '
  + 'one, and whether a new train also makes an event.';
const NOTHING_YET = 'No raid train matches that. Start a raid train above, or run /raidtrain in '
  + 'Discord.';
const GETTING_IT = 'Getting the lineup…';
const SHOWING_ALL = '{n} train{s}.';
const SHOWING_SOME = '{shown} of {n} train{s}.';

const TRAIN_OFF = 'Raid trains are {mode} at the moment, so nothing is posted and no reminder '
  + 'is sent. **Settings and logs** below turns them on.';
const NO_EVENT = 'no event';
const NO_EVENT_YET = 'No event is tied to this train yet. **Make an event for it** raises one '
  + 'and sends it to the events review, where a Lead approves or denies it the same way they '
  + 'would a proposal.';
const EVENT_HERE = 'Event **#{id}** carries this train. It is **{status}**, and the Events page '
  + 'is where it is decided.';
const MAKE_EVENT_BODY = 'An event is raised from this train — its title, its start, its finish '
  + 'and the first streamer on the lineup — and goes to the events review like any proposal. '
  + 'Calling the train off afterwards calls the event off too.';
const SETTLED = 'This train is settled, so its lineup cannot be changed any more.';
const NO_SLOTS = 'This train has no slots, which should not be possible — tell a Lead.';
const SWAP_NOTE = 'The people move; the times belong to the position and stay put.';
const NEW_NOTE = 'Times are read in {tz}. The lineup is posted once and edited in place after '
  + 'that.';
const ALSO_EVENT_HELP = 'The event goes to the events review, where a Lead approves or denies '
  + 'it. Its starting position is the raid_train_event_default setting below.';
const PUT_IN_BODY = 'They need a Twitch channel linked, because the lineup carries the name the '
  + 'streamer before them raids.';

const SCOPES = [
  ['upcoming', 'Coming up'],
  ['past', 'Finished and cancelled'],
  ['all', 'Every train'],
];

const COLUMNS = 'grid-template-columns: 12px minmax(0, 1.5fr) minmax(0, 1fr) 72px '
  + 'minmax(110px, 0.7fr) minmax(110px, 0.8fr) 24px';

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

function plural(count) {
  return count === 1 ? '' : 's';
}

function said(text, values) {
  let out = String(text);
  for (const [key, value] of Object.entries(values)) out = out.replaceAll(`{${key}}`, String(value));
  return out;
}

function wantedId() {
  const hash = String(location.hash || '').replace(/^#/, '').trim();
  return /^\d+$/.test(hash) ? hash : null;
}

/** `close` is dispatched a task late, so a drawer replaced in the meantime keeps its hash. */
function forgetHash() {
  const drawer = document.querySelector('dialog.drawer');
  if (drawer && drawer.open) return;
  shown.id = null;
  if (location.hash) history.replaceState(null, '', location.pathname + location.search);
}

function eventCell(row) {
  if (!row.event_id) return el('span', { class: 'cell-quiet', text: NO_EVENT });
  return el('span', { class: 'cell-kind' }, [
    badge(`#${row.event_id}`, null),
    badge(row.event_status || 'gone', EVENT_TONE[row.event_status] || null),
  ]);
}

/** The row IS the control — `button.grid-row`, the construct `page-posts.js:postRow` uses. */
function trainRow(row) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: COLUMNS,
    'data-search': `${row.title} ${row.status} ${row.organizer_name || ''}`.toLowerCase(),
    on: { click: () => openTrain(row.id, row.title) },
  }, [
    el('span', { class: 'dot-sm', 'data-tone': STATE_OF[row.status] || null }),
    el('span', { class: 'cell-name', text: row.title }),
    el('span', { class: 'cell-quiet', text: when(row.starts_at) }),
    el('span', { class: 'cell-quiet', text: `${row.filled}/${row.slots_total}` }),
    el('span', { class: 'cell-kind' }, [badge(row.status, TONE[row.status] || null)]),
    eventCell(row),
    icon('chevronRight', 16),
  ]);
}

function headRow() {
  return el('div', { class: 'grid-row head', style: COLUMNS }, [
    el('span'),
    el('span', { text: 'Train' }),
    el('span', { text: 'Starts' }),
    el('span', { text: 'Hours' }),
    el('span', { text: 'Status' }),
    el('span', { text: 'Event' }),
    el('span'),
  ]);
}

function healthLine(status) {
  if (!status) return null;
  const bits = [
    status.running ? `sweeping every ${status.every_minutes} min` : 'the sweep is not running',
    `last good sweep ${when(status.last_ok_at)}`,
    `${status.claimed}/${status.slots} slot(s) claimed`,
  ];
  if (status.last_error) bits.push(`last error: ${status.last_error}`);
  return el('p', { class: 'field-help', text: bits.join(' · ') });
}

/** A write in the drawer redraws the list under it, then the drawer over the fresh row. */
async function after(train, done) {
  if (!done.ok) return;
  await refresh();
  await openTrain(train.id, train.title, (done.found || {}).message || '');
}

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
      await after(train, done);
    }, { tone: 'quiet' }));
  }
  if (mayEdit && slot.user_id === null) {
    buttons.push(button('Put somebody in', async () => {
      const memberId = el('input', { class: 'input', type: 'text', placeholder: 'their Discord id' });
      const sure = await ask({
        title: `Who takes slot #${slot.position}?`,
        body: [PUT_IN_BODY, field('Member id', memberId)],
        confirmLabel: 'Put them in',
        tone: 'warn',
      });
      if (!sure || !memberId.value.trim()) return;
      const done = await run(say, () => send(`/api/raidtrains/${train.id}/slots/${slot.position}`, 'POST', { member_id: memberId.value.trim() }), (found) => found?.message);
      await after(train, done);
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

function eventCard(train, say) {
  const line = train.event_id
    ? said(EVENT_HERE, { id: train.event_id, status: train.event_status || 'gone' })
    : NO_EVENT_YET;
  const actions = [];
  if (train.event_id) {
    actions.push(el('a', { class: 'btn quiet small', href: '/events.html', text: 'Open it on the Events page' }));
  } else if (train.editable) {
    actions.push(button('Make an event for it', async () => {
      const sure = await ask({
        title: `Make an event for “${train.title}”?`,
        body: [MAKE_EVENT_BODY],
        confirmLabel: 'Make it',
        tone: 'warn',
      });
      if (!sure) return;
      const done = await run(say, () => send(`/api/raidtrains/${train.id}/event`, 'POST', {}), (found) => found?.message);
      await after(train, done);
    }, { tone: 'warn' }));
  }
  return card('The event', [
    el('p', { class: 'field-help' }, boldParts(line)),
    actions.length ? bar(actions) : null,
  ]);
}

function moveBar(train, say) {
  const buttons = [];
  if (train.status === 'open' || train.status === 'locked') {
    const to = train.status === 'open' ? 'locked' : 'open';
    buttons.push(button(to === 'locked' ? 'Lock the lineup' : 'Open it for sign-ups', async () => {
      const done = await run(say, () => send(`/api/raidtrains/${train.id}/status`, 'POST', { status: to }), (found) => found?.message);
      await after(train, done);
    }));
    buttons.push(button('Call it off', async () => {
      const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — everybody who signed up is told this' });
      const sure = await ask({
        title: `Call off “${train.title}”?`,
        body: [
          'Everybody holding a slot is DMed, the lineup post says it is off, and any event this train carries is cancelled too.',
          field('Reason', reason),
        ],
        confirmLabel: 'Call it off',
      });
      if (!sure) return;
      const done = await run(say, () => send(`/api/raidtrains/${train.id}/status`, 'POST', { status: 'cancelled', reason: reason.value.trim() }), (found) => found?.message);
      await after(train, done);
    }, { tone: 'danger' }));
  }
  return buttons.length ? bar(buttons) : null;
}

function swapCard(train, say) {
  const first = el('input', { class: 'input', type: 'text', placeholder: '1' });
  const second = el('input', { class: 'input', type: 'text', placeholder: '2' });
  const swap = button('Change them round', async () => {
    const done = await run(say, () => send(`/api/raidtrains/${train.id}/swap`, 'POST', {
      a: Number(first.value.trim()),
      b: Number(second.value.trim()),
    }), (found) => found?.message);
    await after(train, done);
  });
  return card('Change two slots round', [
    el('p', { class: 'field-help', text: SWAP_NOTE }),
    field('One slot', first),
    field('The other', second),
    bar([swap]),
  ]);
}

function trainDrawer(train, say, message) {
  if (message) say.say(message, 'ok');
  const grid = table([
    { label: 'Slot', cell: (row) => row.position, className: 'mono' },
    { label: 'Starts', cell: (row) => row.starts, className: 'mono' },
    { label: 'Who', cell: (row) => row.who },
    { label: 'Twitch', cell: (row) => row.login },
    { label: '', cell: (row) => row.checked },
    { label: '', cell: (row) => row.tools },
  ], (train.slots || []).map((slot) => slotRow(train, slot, say, train.editable)), {
    empty: NO_SLOTS,
  });
  return [
    say,
    el('p', { class: 'field-help' }, [
      el('span', { text: `${train.status_word} · ` }),
      el('span', { text: `starts ${when(train.starts_at)} · ` }),
      el('span', { text: `${train.filled}/${train.slots_total} hour(s) taken` }),
    ]),
    moveBar(train, say),
    eventCard(train, say),
    grid,
    train.editable ? swapCard(train, say) : sayNothing(SETTLED),
  ];
}

async function openTrain(trainId, title, message = '') {
  shown.id = String(trainId);
  if (String(location.hash).replace(/^#/, '') !== shown.id) {
    history.replaceState(null, '', `${location.pathname}#${shown.id}`);
  }
  openDrawer(title || `Train #${trainId}`, sayNothing(GETTING_IT), { onClose: forgetHash });
  try {
    const train = await api(`/api/raidtrains/${encodeURIComponent(trainId)}`);
    await names(idsIn(train.slots || [], ['user_id']));
    openDrawer(
      `#${train.id} — ${train.title}`,
      trainDrawer(train, notice(), message),
      { onClose: forgetHash },
    );
  } catch (error) {
    const line = sentenceFor(error);
    openDrawer(title || `Train #${trainId}`, [notice(line.text, line.tone)], { onClose: forgetHash });
  }
}

function newTrainDrawer(eventDefault) {
  const say = notice();
  const title = el('input', { class: 'input', type: 'text', placeholder: 'Saturday raid train' });
  const description = el('textarea', { class: 'input area', rows: '2' });
  const startsAt = el('input', { class: 'input', type: 'text', placeholder: '2026-09-14 19:30' });
  const minutes = el('input', { class: 'input', type: 'text', value: '60' });
  const count = el('input', { class: 'input', type: 'text', value: '8' });
  const alsoEvent = segment(
    [{ value: 'true', label: 'Yes' }, { value: 'false', label: 'No' }],
    eventDefault === true ? 'true' : 'false',
  );

  const make = button('Start it', async () => {
    const done = await run(say, () => send('/api/raidtrains', 'POST', {
      title: title.value.trim(),
      description: description.value.trim(),
      start: startsAt.value.trim(),
      tz: HERE,
      slot_minutes: Number(minutes.value.trim() || 60),
      slot_count: Number(count.value.trim() || 0),
      make_event: alsoEvent.readValue() === 'true',
    }), (found) => found?.message);
    if (!done.ok) return;
    keepSaying('raidtrains', say);
    closeDrawer();
    await refresh();
  }, { tone: 'warn', small: false });

  return [
    el('p', { class: 'field-help', text: said(NEW_NOTE, { tz: HERE }) }),
    field('Title', title),
    field('What it is', description),
    field('Starts', startsAt, 'YYYY-MM-DD HH:MM on a 24-hour clock.'),
    field('Minutes per slot', minutes, '15 to 720.'),
    field('How many slots', count, '1 to 24 — Discord will not carry a longer lineup in one message.'),
    field('Also make an event', alsoEvent, ALSO_EVENT_HELP),
    bar([make]),
    say,
  ];
}

function trainsSection(rows, status, eventDefault, say) {
  const list = section('Raid trains', LIST_NOTE, { count: rows.length, id: 'raidtrains', open: true });
  const built = rows.map((row) => ({ row, node: trainRow(row) }));
  const foot = el('div', { class: 'grid-foot' });
  const grid = el('div', { class: 'grid-table', style: 'min-width: 760px' }, [
    headRow(),
    ...built.map((one) => one.node),
    foot,
  ]);

  const paint = () => {
    let hits = 0;
    for (const one of built) {
      const hit = state.query === ''
        || (one.node.getAttribute('data-search') || '').includes(state.query);
      one.node.hidden = !hit;
      if (hit) hits += 1;
    }
    foot.textContent = hits === built.length
      ? said(SHOWING_ALL, { n: built.length, s: plural(built.length) })
      : said(SHOWING_SOME, { shown: hits, n: built.length, s: plural(built.length) });
  };

  const chips = el('div', { class: 'chipbar' }, SCOPES.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key,
    'aria-pressed': state.scope === key ? 'true' : 'false',
    text: label,
    on: {
      click: () => {
        state.scope = key;
        refresh();
      },
    },
  })));
  const search = searchField({
    label: 'Search the trains',
    placeholder: 'Search the trains…',
    value: state.query,
    onQuery: (query) => {
      state.query = query;
      paint();
    },
  });
  const startIt = button('Start a raid train', () => {
    openDrawer('Start a raid train', newTrainDrawer(eventDefault));
  }, { tone: 'warn' });
  startIt.style.marginLeft = 'auto';
  paint();

  list.body.append(
    el('p', { class: 'field-help' }, [
      el('span', { text: 'Raid trains are ' }),
      modeChip(status ? status.mode : null),
      el('span', { text: '.' }),
    ]),
    status && status.mode !== 'on'
      ? el('p', { class: 'field-help' }, boldParts(said(TRAIN_OFF, { mode: status.mode })))
      : null,
    healthLine(status),
    card(null, [
      el('div', { class: 'card-head' }, [search, chips, startIt]),
      built.length === 0
        ? sayNothing(NOTHING_YET)
        : el('div', { class: 'table-scroll' }, [grid]),
    ]),
    say,
  );
  return full(list.node);
}

/** A shared block demoted out of the "On this page" rail so a fold is not a place. */
function unsectioned(node) {
  const inner = node.querySelector('.sect-inner');
  return inner ? [...inner.childNodes] : [node];
}

async function machinerySection(specs) {
  const one = section('Settings and logs', MACHINERY_NOTE, { id: 'machinery' });
  one.body.append(
    foldout('Settings', [
      el('p', { class: 'field-help', text: SETTINGS_NOTE }),
      await settingsPanel(specs, { where: 'Raid trains', onSaved: () => refresh() }),
    ], { count: specs.length }),
    foldout('Logs', unsectioned(await logsSection('raidtrain'))),
  );
  return full(one.node);
}

async function load() {
  const query = `?scope=${encodeURIComponent(state.scope)}`;
  const [rows, status] = await Promise.all([
    api(`/api/raidtrains${query}`).then((payload) => listOf(payload, 'raidtrains')),
    api('/api/raidtrains/status').catch(() => null),
  ]);
  await names(idsIn(rows, ['organizer_id']));
  const specs = settingsNamespace(await settings(), 'raidtrain');
  const held = specs.find((spec) => spec.key === 'raidtrain_event_default');
  const say = sayAgain('raidtrains', notice());

  document.getElementById('dash').replaceChildren(
    trainsSection(rows, status, held ? held.value : false, say),
    await machinerySection(specs),
  );

  const wanted = wantedId();
  if (wanted && !deepLinked) {
    deepLinked = true;
    const found = rows.find((one) => String(one.id) === wanted);
    openTrain(wanted, found ? found.title : `Train #${wanted}`);
  }
}

window.addEventListener('hashchange', () => {
  const wanted = wantedId();
  if (!wanted) {
    if (shown.id) closeDrawer();
    return;
  }
  if (wanted === shown.id) return;
  openTrain(wanted, `Train #${wanted}`);
});

refresh = start({ tab: 'raidtrain', load });
