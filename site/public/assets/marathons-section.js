import { api, names, send, settings, settingsNamespace } from './api.js';
import {
  BAF,
  CARD_CHANNEL,
  CARD_EVENT,
  CARD_PEOPLE,
  CARD_POSTS,
  CARD_RUNS,
  CARD_SCHEDULE,
  countsLine,
  feedReading,
  postsLines,
  readingLine,
  said,
  scheduleCell,
  sourcesTitle,
} from './marathon-words.js';
import {
  ask,
  askForm,
  badge,
  bar,
  boldParts,
  button,
  card,
  closeDrawer,
  duration,
  el,
  field,
  foldout,
  keepSaying,
  memberPicker,
  modeChip,
  nameNode,
  notice,
  openDrawer,
  run,
  sayAgain,
  sayNothing,
  section,
  segment,
  sentenceFor,
  table,
  textAction,
  when,
} from './ui.js';

const shown = { id: null, filter: 'ours' };
const HASH = /^marathon-(\d+)$/;
let refresh = async () => {};
let showEvent = () => {};
let eventModeDefault = 'none';
let eventModes = [];
let cadence = { near: null, far: null };
let deepLinked = false;

const LIST_NOTE = 'Every marathon schedule Black Bloc reads; a row opens where it is read from, '
  + 'its runs, its event and its posts.';
const NOTHING_YET = 'Black Bloc follows no marathon yet. **Add a marathon** with its GDQ '
  + 'schedule link.';
const GETTING_IT = 'Reading the schedule…';
const MODE_OFF = 'Marathon posts are **{mode}**, so nothing is read or posted. **Marathons** '
  + 'under Settings and logs turns them on.';
const MODE_SHADOW = 'Marathon posts are in **shadow**: the board, the reminders and the '
  + 'shoutouts land where shadow_channel_id points, with the rehearsal note.';
const ADD_NOTE = 'Paste the GDQ schedule link (gamesdonequick.com/schedule/74) or the tracker '
  + 'event link. Black Bloc reads it at once and every half hour after that while it is near.';
const CHANNEL_HELP = 'The Twitch channel it airs on, from the Go-live page. With one, its '
  + 'ping window follows the marathon and its live title confirms which run is on.';
const NO_CHANNEL = 'No channel — each run links its runner';
const PAIR_NOTE = 'A name on the schedule with no Twitch link, or the wrong one: pair it with '
  + 'the member it is. A pairing beats the automatic match, and Unpair gives it back.';
const RUNS_NOTE = BAF + ' runs are highlighted. A moved run says where it was; a run the schedule '
  + 'dropped is kept as history.';
const NO_RUNS = 'No runs on this schedule yet — it may not be published. Black Bloc keeps '
  + 'reading it.';
const NO_BAF_RUNS = `No ${BAF} run on this schedule yet — pick All to see every run.`;
const NO_PAIRINGS = 'No pairings. The automatic match reads each runner’s Twitch link.';
const REMOVE_BODY = 'Its runs and pairings go with it and its ping window closes. Posts already '
  + 'made stay where they are.';
const WINDOW_LINE = 'Ping window on **{login}**: {start} – {end}.';
const NO_WINDOW = 'No ping window — the marathon has no channel, no dates yet, or is paused.';
const CHANNEL_GONE = 'Its channel row is gone from the Go-live page, so it has no window and '
  + 'no live title. Pick another channel, or none.';
const READ_FROM = 'Read from the ';
const SCHEDULE_LINK = 'the schedule ↗';
const FOUND_BY = ' · found by the **{feed}** feed';
const POLL_LABEL = 'Re-read every';
const POLL_UNIT = 'minutes';
const POLL_HELP = 'Blank = the default ({minutes}). 10 to 120; used while it is near.';
const NEXT_WHEN_ENDS = 'When this ends: ';
const NEXT_LINE = '{marathon} is over — the next GDQ event is **{next}**, {date} ({relative}).';
const NEXT_ADDED = 'Added — see **{name}** on the list.';
const NEXT_DISMISSED = 'Dismissed — **Look again** asks the tracker once more.';
const NEXT_NONE = '{marathon} is over and the GDQ tracker lists nothing ahead yet.';
const NEXT_NOT_YET = '{marathon} is over. Black Bloc has not looked up the next GDQ event yet.';
const NEXT_NOTE = 'Staff decide: nothing is added until someone presses **Add it**. It is read '
  + 'from the tracker link and airs on this marathon’s channel.';
const NEXT_WAITING = '{count} marathon{s} {have} a next event waiting: ';
const HELD_NOTE = 'held by staff';
const EVENT_SELECT = 'Event';
const EVENT_SELECT_HELP = 'No event by default. One event for the marathon goes into the events '
  + 'review above, dated from the schedule. An event per ' + BAF + ' run is approved at once and '
  + 'follows the schedule as runs move — the events feature announces each one as it starts. '
  + 'Both does the two. marathon_event_mode_default decides where this starts.';
const EVENT_SELECT_SHORT = 'Which Discord events this marathon makes; the setting explains the '
  + 'four choices.';
const EVENT_NONE = 'No event.';
const EVENT_WAITING = 'Waiting for the schedule to publish, then one event for the marathon.';
const EVENT_OPEN = 'Open ↗';
const MODES_FALLBACK = [
  { value: 'none', label: 'No event' },
  { value: 'marathon', label: 'One event for the marathon' },
  { value: 'runs', label: `An event per ${BAF} run` },
  { value: 'both', label: 'Both' },
];
const FEED_MODE_FOLLOW = 'Whatever the setting says';
const FEED_MODE_HELP = 'What a marathon this feed adds does about events; the first choice '
  + 'follows marathon_event_mode_default.';
const FEED_MOVE_NOTE = 'Only a channel-only row with no feed of its own, and one that takes '
  + 'marathons, can be picked.';
const NO_MARATHONS_CHANNEL = 'opted out of marathons';
const EVENT_TONE = { pending: 'warn', approved: 'ok', denied: 'danger', cancelled: null, gone: null };
const PHASE_TONE = { far: null, near: 'warn', live: 'ok', over: null, paused: null };
const STATE_TONE = { upcoming: null, live: 'ok', done: null, dropped: 'danger' };
const FEEDS_NOTE = 'A source reads the events list of one channel Black Bloc already watches and '
  + 'adds (or suggests) every new marathon it finds — only for channels on the Go-live page, '
  + 'never random ones. A row opens the rest of its moves.';
const FEEDS_OFF = 'Checks are off (marathon_feeds under **Marathons** in Settings and logs), so '
  + 'nothing checks on its own. **Check now** still works.';
const NO_FEEDS = 'No sources yet. **Add a feed…** starts from a channel on the Go-live page.';
const FEED_ADD_NOTE = 'Pick the channel first — a feed belongs to a channel Black Bloc already '
  + 'watches, one feed per channel. Then what to read: the GDQ tracker, the RPG Limit Break '
  + 'tracker, or a horaro.net event by its slug (ESA is `esa`).';
const FEED_NO_CHANNELS = 'Every channel-only row on the Go-live page has a feed already, or '
  + 'there is none. Add the channel there first.';
const FEED_IGNORED_NOTE = 'A marathon this feed added and staff removed is never added again '
  + 'until **Forget ignored**.';
const FEED_ADDED = 'Added by this feed: ';
const FEED_DRAWER = 'The {feed} feed';
const SUGGESTION_LINE = '**{feed}** has a new event: **{event}**, {date} ({relative}).';
const SUGGESTION_NOTE = 'Staff decide: nothing is added until someone presses **Add it**. It airs '
  + 'on the feed’s channel.';
const FEED_REMOVE_BODY = 'It stops checking. The marathons it added stay on the list.';
const FEED_GONE = 'That feed is gone — the list below is current.';
const ACTION_CHOICES = [{ value: 'add', label: 'Add' }, { value: 'suggest', label: 'Suggest' }];

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

function line(text, tone = null) {
  return el('p', { class: 'field-help mx-line', 'data-tone': tone || undefined }, boldParts(text));
}

function wantedId() {
  const found = HASH.exec(String(location.hash || '').replace(/^#/, '').trim());
  return found ? found[1] : null;
}

function forgetHash() {
  const drawer = document.querySelector('dialog.drawer');
  if (drawer && drawer.open) return;
  shown.id = null;
  if (wantedId()) history.replaceState(null, '', location.pathname + location.search);
}

function datesOf(row) {
  if (!row.starts_at) return 'dates not published';
  return `${when(row.starts_at)} – ${when(row.ends_at)}`;
}

function relative(iso) {
  const at = new Date(iso);
  if (!iso || Number.isNaN(at.getTime())) return '—';
  const seconds = Math.round((at.getTime() - Date.now()) / 1000);
  return seconds >= 0 ? `in ${duration(seconds)}` : `${duration(-seconds)} ago`;
}

function nextSentence(row) {
  const next = row.next || {};
  if (next.state === 'added') return said(NEXT_ADDED, { name: next.added_name || next.name || '' });
  if (next.state === 'none') return said(NEXT_NONE, { marathon: row.name });
  if (!next.state) return said(NEXT_NOT_YET, { marathon: row.name });
  const words = said(NEXT_LINE, {
    marathon: row.name,
    next: next.name,
    date: next.datetime ? new Date(next.datetime).toLocaleDateString() : 'no date yet',
    relative: relative(next.datetime),
  });
  return next.state === 'dismissed' ? `${words} ${NEXT_DISMISSED}` : words;
}

async function addNext(row, say) {
  const done = await run(say, () => send('/api/marathons', 'POST', { next_of: row.id, event_id: row.next.event_id }), (found) => found?.message);
  if (!done.ok) return;
  await refresh();
  await openMarathon(done.found.id, done.found.name, done.found.message);
}

async function dismissNext(row, say) {
  const done = await run(say, () => send(`/api/marathons/${row.id}`, 'PATCH', { dismiss_next: true, event_id: row.next.event_id }), (found) => found?.message);
  await after(row, done);
}

async function lookAgain(row, say) {
  const done = await run(say, () => send(`/api/marathons/${row.id}/next`, 'POST', {}), (found) => found?.message);
  await after(row, done);
}

function nextMoves(row, say) {
  const next = row.next || {};
  const moves = [];
  if (next.state === 'open') {
    moves.push(button('Add it', () => addNext(row, say), { tone: 'warn' }));
    moves.push(button('Not this one', () => dismissNext(row, say), { tone: 'quiet' }));
  }
  if (next.state === 'added' && next.added_marathon_id) {
    moves.push(textAction(`Open ${next.added_name || next.name}`, () => openMarathon(next.added_marathon_id, next.added_name || next.name)));
  }
  if (next.can_look_again && next.state !== 'added') {
    moves.push(button('Look again', () => lookAgain(row, say), { tone: 'quiet' }));
  }
  return moves;
}

async function channelChoices() {
  const rows = await api('/api/golive/spotlight').catch(() => []);
  return (Array.isArray(rows) ? rows : []).map((one) => ({
    value: String(one.id),
    label: (one.display_name && one.display_name.toLowerCase() !== one.twitch_login
      ? `${one.twitch_login} · ${one.display_name}`
      : one.twitch_login) + (one.marathons === false ? ` (${NO_MARATHONS_CHANNEL})` : ''),
    closed: one.marathons === false,
  }));
}

function channelPicker(choices, current) {
  return el('select', { class: 'input' }, [
    el('option', { value: '', text: NO_CHANNEL, selected: !current || undefined }),
    ...choices.map((one) => el('option', {
      value: one.value,
      text: one.label,
      disabled: one.closed && String(current || '') !== one.value ? true : undefined,
      selected: String(current || '') === one.value || undefined,
    })),
  ]);
}

function modeChoices() {
  return eventModes.length ? eventModes : MODES_FALLBACK;
}

function modePicker(current, { follow = false } = {}) {
  const options = modeChoices().map((one) => el('option', {
    value: one.value,
    text: one.label,
    selected: String(current || '') === one.value || undefined,
  }));
  if (follow) options.unshift(el('option', { value: '', text: FEED_MODE_FOLLOW, selected: !current || undefined }));
  return el('select', { class: 'input' }, options);
}

async function addMarathon() {
  const name = el('input', { class: 'input', type: 'text', placeholder: 'AGDQ 2027' });
  const url = el('input', { class: 'input', type: 'url', placeholder: 'https://gamesdonequick.com/schedule/74' });
  const channel = channelPicker(await channelChoices(), null);
  const mode = modePicker(eventModeDefault);
  let made = null;
  const sure = await askForm({
    title: 'Add a marathon',
    body: [
      el('p', { class: 'ask-body', text: ADD_NOTE }),
      field('Name', name),
      field('Schedule link', url),
      field('Channel it airs on', channel, CHANNEL_HELP),
      field(EVENT_SELECT, mode, EVENT_SELECT_HELP),
    ],
    confirmLabel: 'Add it',
    tone: 'warn',
    onConfirm: async () => {
      made = await send('/api/marathons', 'POST', {
        name: name.value.trim(),
        schedule_url: url.value.trim(),
        spotlight_id: channel.value || null,
        event_mode: mode.value,
      });
      return null;
    },
  });
  if (!sure || !made) return;
  await refresh();
  await openMarathon(made.id, made.name, made.message);
}

function personCell(one) {
  return el('span', {}, one.people.map((person, index) => el('span', {}, [
    index ? el('span', { text: ', ' }) : null,
    person.user_id ? nameNode(person.user_id, person.member_name) : el('span', { text: person.name }),
    el('span', { class: 'cell-quiet', text: person.part === 'runner' ? '' : ` (${person.part})` }),
  ])));
}

function whenCell(one) {
  return el('span', {}, [
    el('span', { class: 'mono', text: when(one.scheduled_at) }),
    one.moved && one.previous_scheduled_at
      ? el('span', { class: 'cell-quiet', 'data-tone': 'warn', text: ` · moved from ${when(one.previous_scheduled_at)}` })
      : null,
  ]);
}

async function after(marathon, done) {
  if (!done.ok) return;
  await refresh();
  await openMarathon(marathon.id, marathon.name, (done.found || {}).message || '');
}

function step(marathon, say, label, work, tone = 'quiet') {
  return button(label, async () => {
    const done = await run(say, work, (found) => found?.message);
    await after(marathon, done);
  }, { tone });
}

function runTools(marathon, row, say) {
  const base = `/api/marathons/${marathon.id}/runs/${row.id}`;
  const tools = [];
  if (row.shoutable) tools.push(step(marathon, say, 'Shout it now', () => send(`${base}/shout`, 'POST', {}), 'warn'));
  if (row.can_mark_done && (row.ours || row.state === 'live')) {
    tools.push(step(marathon, say, 'Mark done', () => send(`${base}/done`, 'POST', {})));
  }
  if (row.can_mark_live && !row.shoutable) tools.push(step(marathon, say, 'Mark it live', () => send(`${base}/live`, 'POST', {})));
  if (row.event_id) {
    tools.push(textAction(`event #${row.event_id}${row.event_status ? ` · ${row.event_status}` : ''}`, () => {
      closeDrawer();
      showEvent(row.event_id);
    }));
    tools.push(step(marathon, say, 'Unlink', () => send(`${base}/event`, 'DELETE')));
  } else if (row.ours && row.state !== 'dropped' && row.state !== 'done') {
    tools.push(step(marathon, say, 'Make it now', () => send(`${base}/event`, 'POST', {})));
  }
  if (row.can_mark_upcoming) tools.push(step(marathon, say, 'Mark it upcoming', () => send(`${base}/upcoming`, 'POST', {})));
  return el('div', { class: 'bar' }, tools);
}

function pollField(marathon, say) {
  const poll = el('input', {
    class: 'input',
    type: 'text',
    inputmode: 'numeric',
    size: 4,
    placeholder: String(cadence.near ?? ''),
    value: marathon.poll_minutes ? String(marathon.poll_minutes) : '',
    'aria-label': `${POLL_LABEL} N ${POLL_UNIT}`,
  });
  const save = button('Save', async () => {
    const given = poll.value.trim();
    const wanted = given === '' ? null : (/^\d+$/.test(given) ? Number(given) : given);
    const done = await run(
      say,
      () => send(`/api/marathons/${marathon.id}`, 'PATCH', { poll_minutes: wanted }),
      () => (wanted === null ? `**${marathon.name}** is re-read on the default gap again.` : `**${marathon.name}** is re-read every ${wanted} minutes while it is near.`),
    );
    await after(marathon, done);
  }, { tone: 'quiet' });
  const box = el('span', { class: 'mx-poll' }, [poll, el('span', { text: POLL_UNIT }), save]);
  return field(POLL_LABEL, box, said(POLL_HELP, { minutes: cadence.near ?? '—' }));
}

function nextBlock(marathon, say) {
  if (!marathon.next) return [];
  const moves = nextMoves(marathon, say);
  return [
    el('p', { class: 'field-help mx-line' }, [el('span', { class: 'cell-quiet', text: NEXT_WHEN_ENDS }), ...boldParts(nextSentence(marathon))]),
    marathon.next.state === 'open' ? line(NEXT_NOTE) : null,
    marathon.next.url && marathon.next.state !== 'none'
      ? el('p', { class: 'field-help' }, [el('a', { href: marathon.next.url, text: 'the tracker ↗', rel: 'noreferrer', target: '_blank' })])
      : null,
    moves.length ? bar(moves) : null,
  ];
}

function scheduleCard(marathon, say) {
  const reading = readingLine(marathon, cadence);
  const source = el('p', { class: 'field-help mx-line' }, [
    el('span', { text: READ_FROM }),
    el('strong', { text: marathon.source_word }),
    el('span', { text: ' — ' }),
    el('a', { href: marathon.schedule_page, text: SCHEDULE_LINK, rel: 'noreferrer', target: '_blank' }),
    ...(marathon.feed_name ? boldParts(said(FOUND_BY, { feed: marathon.feed_name })) : []),
  ]);
  const moves = [];
  if (marathon.active) {
    moves.push(step(marathon, say, 'Read it now', () => send(`/api/marathons/${marathon.id}/refresh`, 'POST', {}), 'warn'));
  }
  return card(CARD_SCHEDULE, [
    source,
    line(reading.text, reading.tone),
    line(countsLine(marathon.run_list)),
    pollField(marathon, say),
    moves.length ? bar(moves) : null,
    ...nextBlock(marathon, say),
  ]);
}

function runsCard(marathon, say) {
  const holder = el('div');
  const paint = () => {
    const rows = (marathon.run_list || []).filter((one) => shown.filter === 'all' || one.ours);
    holder.replaceChildren(table([
      { label: 'When', cell: (row) => whenCell(row) },
      { label: 'Game', cell: (row) => el('span', { class: row.ours ? 'cell-name' : '', text: row.game }) },
      { label: 'Category', cell: (row) => row.category },
      { label: 'People', cell: (row) => personCell(row) },
      { label: 'State', cell: (row) => el('span', { class: 'cell-kind' }, [
        badge(row.state_word, STATE_TONE[row.state] || null),
        row.ours ? badge(BAF, 'ok') : null,
        row.event_id ? badge(`event #${row.event_id}`, EVENT_TONE[row.event_status] || null) : null,
        row.held ? badge(HELD_NOTE, 'warn') : null,
      ]) },
      { label: '', cell: (row) => runTools(marathon, row, say) },
    ], rows, { empty: marathon.run_list && marathon.run_list.length ? NO_BAF_RUNS : NO_RUNS }));
  };
  const chips = segment(
    [{ value: 'ours', label: `${BAF} (${marathon.ours})` }, { value: 'all', label: `All (${marathon.runs})` }],
    shown.filter,
    { onChange: () => { shown.filter = chips.readValue(); paint(); } },
  );
  paint();
  return card(CARD_RUNS, [el('p', { class: 'field-help', text: RUNS_NOTE }), chips, holder]);
}

function pairingsCard(marathon, say) {
  const rows = (marathon.pairings || []).map((one) => ({
    runner: one.runner_name,
    member: nameNode(one.user_id, one.member_name),
    scope: one.everywhere ? 'every schedule' : 'this schedule',
    tools: step(marathon, say, 'Unpair', () => send(`/api/marathons/${marathon.id}/people/${one.id}`, 'DELETE')),
  }));
  const pair = button('Pair a runner…', async () => {
    const listed = el('datalist', { id: 'marathon-unmatched' }, (marathon.unmatched || []).map((one) => el('option', { value: one })));
    const runner = el('input', { class: 'input', type: 'text', list: 'marathon-unmatched', placeholder: 'the name as the schedule writes it' });
    const picker = memberPicker({ label: 'Member' });
    const scope = segment([{ value: 'this', label: 'This schedule' }, { value: 'every', label: 'Every schedule' }], 'this');
    let done = null;
    const sure = await askForm({
      title: `Pair a runner on ${marathon.name}`,
      body: [el('p', { class: 'ask-body', text: PAIR_NOTE }), listed, field('Name on the schedule', runner), picker.node, field('Where it counts', scope)],
      confirmLabel: 'Pair them',
      tone: 'warn',
      onConfirm: async () => {
        done = await send(`/api/marathons/${marathon.id}/people`, 'POST', {
          runner_name: runner.value.trim(),
          user_id: picker.id,
          everywhere: scope.readValue() === 'every',
        });
        return null;
      },
    });
    if (!sure || !done) return;
    await after(marathon, { ok: true, found: done });
  }, { tone: 'warn' });
  return card(CARD_PEOPLE, [
    el('p', { class: 'field-help', text: PAIR_NOTE }),
    table([
      { label: 'Name on the schedule', cell: (row) => row.runner },
      { label: 'Member', cell: (row) => row.member },
      { label: 'Counts on', cell: (row) => row.scope },
      { label: '', cell: (row) => row.tools },
    ], rows, { empty: NO_PAIRINGS }),
    bar([pair]),
  ]);
}

function eventCard(marathon, say) {
  const event = marathon.event || {};
  const state = [];
  if (event.id) {
    state.push(badge(event.status || 'gone', EVENT_TONE[event.status] || null), el('span', { text: ` Event #${event.id} ` }));
    if (event.status !== 'gone') {
      state.push(textAction(EVENT_OPEN, () => {
        closeDrawer();
        showEvent(event.id);
      }));
    }
  } else {
    state.push(el('span', { text: event.wanted ? EVENT_WAITING : EVENT_NONE }));
  }
  const moves = [];
  if (event.id || event.wanted) {
    moves.push(step(marathon, say, 'Unlink', () => send(`/api/marathons/${marathon.id}/event`, 'DELETE')));
  } else {
    moves.push(step(marathon, say, 'Make an event now', () => send(`/api/marathons/${marathon.id}/event`, 'POST', {}), 'warn'));
  }
  const mode = modePicker(marathon.event_mode || 'none');
  mode.addEventListener('change', async () => {
    const done = await run(say, () => send(`/api/marathons/${marathon.id}`, 'PATCH', { event_mode: mode.value }), (found) => found?.message);
    if (!done.ok) {
      mode.value = marathon.event_mode || 'none';
      return;
    }
    await after(marathon, done);
  });
  return card(CARD_EVENT, [
    el('p', { class: 'field-help mx-line' }, [...state, el('span', { text: ' ' }), ...moves]),
    field(EVENT_SELECT, mode, EVENT_SELECT_SHORT),
  ]);
}

async function channelCard(marathon, say) {
  const picker = channelPicker(await channelChoices(), marathon.spotlight_id);
  const save = button('Save the channel', async () => {
    const done = await run(say, () => send(`/api/marathons/${marathon.id}`, 'PATCH', { spotlight_id: picker.value || null }), () => 'Saved.');
    await after(marathon, done);
  });
  const windowLine = marathon.window && marathon.channel_login
    ? said(WINDOW_LINE, { login: marathon.channel_login, start: when(marathon.window.starts_at), end: when(marathon.window.ends_at) })
    : NO_WINDOW;
  return card(CARD_CHANNEL, [
    marathon.channel_gone ? notice(CHANNEL_GONE, 'warn') : null,
    field('Airs on', picker, CHANNEL_HELP),
    el('p', { class: 'field-help' }, boldParts(windowLine)),
    bar([save]),
  ]);
}

function postsCard(marathon, say) {
  const posts = postsLines(marathon);
  const board = step(
    marathon,
    say,
    posts.hasBoard ? 'Refresh the board' : 'Post the board',
    () => send(`/api/marathons/${marathon.id}/board`, 'POST', {}),
  );
  const where = posts.hasBoard && marathon.board_channel_id;
  return card(CARD_POSTS, [
    el('p', { class: 'field-help mx-line' }, [
      el('span', { text: posts.board }),
      where ? el('span', { text: ' ' }) : null,
      where ? nameNode(marathon.board_channel_id) : null,
      el('span', { text: ' ' }),
      board,
    ]),
    line(posts.sent),
  ]);
}

function moveBar(marathon, say) {
  return bar([
    step(marathon, say, marathon.active ? 'Pause' : 'Resume', () => send(`/api/marathons/${marathon.id}`, 'PATCH', { active: !marathon.active }), null),
    button('Remove', async () => {
      const sure = await ask({ title: `Remove ${marathon.name}?`, body: [REMOVE_BODY], confirmLabel: 'Remove it' });
      if (!sure) return;
      const done = await run(say, () => send(`/api/marathons/${marathon.id}`, 'DELETE'), (found) => found?.message);
      if (!done.ok) return;
      keepSaying('marathons', say);
      closeDrawer();
      await refresh();
    }, { tone: 'danger' }),
  ]);
}

async function marathonDrawer(marathon, message) {
  if (marathon.board_channel_id) await names([marathon.board_channel_id]).catch(() => null);
  const say = notice();
  if (message) say.say(message, 'ok');
  return [
    say,
    el('p', { class: 'field-help' }, [
      badge(marathon.phase_word, PHASE_TONE[marathon.phase] || null),
      el('span', { text: ` ${datesOf(marathon)}` }),
    ]),
    scheduleCard(marathon, say),
    runsCard(marathon, say),
    pairingsCard(marathon, say),
    eventCard(marathon, say),
    await channelCard(marathon, say),
    postsCard(marathon, say),
    moveBar(marathon, say),
  ];
}

async function openMarathon(marathonId, title, message = '') {
  shown.id = String(marathonId);
  if (wantedId() !== shown.id) {
    history.replaceState(null, '', `${location.pathname}${location.search}#marathon-${shown.id}`);
  }
  openDrawer(title || `Marathon #${marathonId}`, sayNothing(GETTING_IT), { onClose: forgetHash });
  try {
    const marathon = await api(`/api/marathons/${encodeURIComponent(marathonId)}`);
    openDrawer(marathon.name, await marathonDrawer(marathon, message), { onClose: forgetHash });
  } catch (error) {
    const found = sentenceFor(error);
    openDrawer(title || `Marathon #${marathonId}`, [notice(found.text, found.tone)], { onClose: forgetHash });
  }
}

async function feedStep(say, work) {
  const done = await run(say, work, (found) => found?.message);
  if (done.ok) {
    keepSaying('marathons', say);
    await refresh();
  }
  return done;
}

async function feedDrawerStep(feed, say, work) {
  const done = await run(say, work, (found) => found?.message);
  if (!done.ok) return done;
  await refresh();
  await openFeed(feed.id, (done.found || {}).message || '');
  return done;
}

async function renameFeed(feed) {
  const name = el('input', { class: 'input', type: 'text', value: feed.name });
  let done = null;
  const sure = await askForm({
    title: `Rename the ${feed.name} feed`,
    body: [field('Name', name)],
    confirmLabel: 'Rename it',
    tone: 'warn',
    onConfirm: async () => {
      done = await send(`/api/marathons/feeds/${feed.id}`, 'PATCH', { name: name.value.trim() });
      return null;
    },
  });
  if (!sure || !done) return;
  await refresh();
  await openFeed(feed.id, done.message || 'Renamed.');
}

async function moveFeed(feed) {
  const payload = await api('/api/marathons/feeds').catch(() => ({ channels: [] }));
  const free = (payload.channels || []).filter((one) => !one.feed_name && one.marathons !== false);
  const channel = el('select', { class: 'input' }, free.map((one) => el('option', { value: String(one.id), text: `${one.name} · twitch.tv/${one.login}` })));
  let done = null;
  const sure = await askForm({
    title: `Move the ${feed.name} feed`,
    body: [el('p', { class: 'ask-body', text: FEED_MOVE_NOTE }), field('Channel', channel)],
    confirmLabel: 'Move it',
    tone: 'warn',
    onConfirm: async () => {
      done = await send(`/api/marathons/feeds/${feed.id}`, 'PATCH', { spotlight_id: channel.value || null });
      return null;
    },
  });
  if (!sure || !done) return;
  await refresh();
  await openFeed(feed.id, done.message || 'Moved.');
}

function actionCell(feed, say) {
  const chips = segment(ACTION_CHOICES, feed.action, {
    onChange: () => {
      const wanted = chips.readValue();
      if (wanted !== feed.action) feedStep(say, () => send(`/api/marathons/feeds/${feed.id}`, 'PATCH', { action: wanted }));
    },
  });
  return chips;
}

function suggestionCard(feed, record, say, { inDrawer = false } = {}) {
  const base = `/api/marathons/feeds/${feed.id}`;
  const words = said(SUGGESTION_LINE, {
    feed: feed.name,
    event: record.name,
    date: record.starts_at ? new Date(record.starts_at).toLocaleDateString() : 'no date yet',
    relative: relative(record.starts_at),
  });
  const dismiss = () => send(base, 'PATCH', { dismiss: record.ref });
  return card('Next up', [
    el('p', {}, boldParts(words)),
    el('p', { class: 'field-help' }, boldParts(SUGGESTION_NOTE)),
    record.url ? el('p', { class: 'field-help' }, [el('a', { href: record.url, text: 'the schedule ↗', rel: 'noreferrer', target: '_blank' })]) : null,
    bar([
      button('Add it', async () => {
        const done = await feedStep(say, () => send(`${base}/add`, 'POST', { event_ref: record.ref }));
        if (done.ok && done.found.marathon_id) await openMarathon(done.found.marathon_id, record.name, done.found.message);
      }, { tone: 'warn' }),
      button('Not this one', () => (inDrawer ? feedDrawerStep(feed, say, dismiss) : feedStep(say, dismiss)), { tone: 'quiet' }),
    ]),
  ]);
}

function feedDrawer(feed, message) {
  const say = notice();
  if (message) say.say(message, 'ok');
  const base = `/api/marathons/feeds/${feed.id}`;
  const reading = feedReading(feed);
  const mode = modePicker(feed.event_mode, { follow: true });
  mode.addEventListener('change', () => {
    feedDrawerStep(feed, say, () => send(base, 'PATCH', { event_mode: mode.value || null }));
  });
  const moves = [];
  if ((feed.dismissed || []).length) {
    moves.push(button('Look again', () => feedDrawerStep(feed, say, () => send(`${base}/look`, 'POST', {})), { tone: 'quiet' }));
  }
  if (feed.ignored_count) {
    moves.push(button(`Forget ignored (${feed.ignored_count})`, () => feedDrawerStep(feed, say, () => send(`${base}/forget`, 'POST', {})), { tone: 'quiet' }));
  }
  moves.push(button('Rename…', () => renameFeed(feed), { tone: 'quiet' }));
  moves.push(button('Move to channel…', () => moveFeed(feed), { tone: 'quiet' }));
  moves.push(button('Remove', async () => {
    const sure = await ask({ title: `Remove the ${feed.name} feed?`, body: [FEED_REMOVE_BODY], confirmLabel: 'Remove it' });
    if (!sure) return;
    const done = await run(say, () => send(base, 'DELETE'), (found) => found?.message);
    if (!done.ok) return;
    keepSaying('marathons', say);
    closeDrawer();
    await refresh();
  }, { tone: 'danger' }));
  const added = feed.marathons || [];
  return [
    say,
    el('p', { class: 'field-help mx-line' }, [
      el('span', { text: READ_FROM }),
      el('strong', { text: feed.source_word }),
      el('span', { text: ` · ${feed.channel_name} ` }),
      feed.active ? null : badge('paused'),
    ]),
    line(reading.text, reading.tone),
    added.length
      ? el('p', { class: 'field-help mx-line' }, [
        el('span', { class: 'cell-quiet', text: FEED_ADDED }),
        ...added.flatMap((one, index) => [
          index ? el('span', { text: ' · ' }) : null,
          textAction(one.name, () => openMarathon(one.id, one.name)),
        ]),
      ])
      : null,
    field('Event', mode, FEED_MODE_HELP),
    ...(feed.suggestions || []).map((one) => suggestionCard(feed, one, say, { inDrawer: true })),
    line(FEED_IGNORED_NOTE),
    bar(moves),
  ];
}

async function openFeed(feedId, message = '') {
  const payload = await api('/api/marathons/feeds').catch((error) => ({ error: sentenceFor(error) }));
  const feed = (payload.feeds || []).find((one) => String(one.id) === String(feedId));
  if (!feed) {
    openDrawer(said(FEED_DRAWER, { feed: `#${feedId}` }), [notice(payload.error ? payload.error.text : FEED_GONE, 'warn')]);
    return;
  }
  openDrawer(said(FEED_DRAWER, { feed: feed.name }), feedDrawer(feed, message));
}

async function addFeed(payload) {
  const free = (payload.channels || []).filter((one) => !one.feed_name);
  const channel = el('select', { class: 'input' }, free.map((one) => el('option', { value: String(one.id), text: `${one.name} · twitch.tv/${one.login}` })));
  const source = el('select', { class: 'input' }, (payload.sources || []).map((one) => el('option', { value: one.value, text: one.label })));
  const slug = el('input', { class: 'input', type: 'text', placeholder: 'esa' });
  const name = el('input', { class: 'input', type: 'text', placeholder: 'the channel’s name' });
  const action = segment(ACTION_CHOICES, payload.action_default || 'add');
  let made = null;
  const sure = await askForm({
    title: 'Add a feed',
    body: [
      el('p', { class: 'ask-body' }, boldParts(free.length ? FEED_ADD_NOTE : FEED_NO_CHANNELS)),
      field('Channel', channel),
      field('Read from', source),
      field('horaro.net event slug', slug, 'Only for horaro.net — the part after horaro.net/.'),
      field('Name', name, 'Blank uses the channel’s name.'),
      field('New events', action),
    ],
    confirmLabel: 'Add the feed',
    tone: 'warn',
    onConfirm: async () => {
      made = await send('/api/marathons/feeds', 'POST', {
        spotlight_id: channel.value || null,
        source: source.value,
        slug: slug.value.trim() || null,
        name: name.value.trim() || null,
        action: action.readValue(),
      });
      return null;
    },
  });
  if (!sure || !made) return;
  const say = notice();
  say.say(made.message, 'ok');
  keepSaying('marathons', say);
  await refresh();
}

function feedTools(row, say) {
  const base = `/api/marathons/feeds/${row.id}`;
  return el('div', { class: 'bar' }, [
    button('Check now', () => feedStep(say, () => send(`${base}/check`, 'POST', {})), { tone: 'warn' }),
    button(row.active ? 'Pause' : 'Resume', () => feedStep(say, () => send(base, 'PATCH', { active: !row.active })), { tone: 'quiet' }),
  ]);
}

function feedCheckCell(row) {
  const reading = feedReading(row);
  return el('span', { class: 'cell-quiet mx-line', 'data-tone': reading.tone || undefined, text: reading.text });
}

function sourcesFoldout(feeds, say) {
  if (feeds.error) return foldout(sourcesTitle([]), [notice(feeds.error.text, feeds.error.tone)]);
  const rows = feeds.feeds || [];
  const grid = table([
    { label: 'Channel', cell: (row) => el('span', {}, [textAction(row.channel_name || row.name, () => openFeed(row.id)), row.active ? null : badge('paused')]) },
    { label: 'Source', cell: (row) => row.source_word },
    { label: 'Checks', cell: (row) => feedCheckCell(row) },
    { label: 'New events', cell: (row) => actionCell(row, say) },
    { label: '', cell: (row) => feedTools(row, say) },
  ], rows, { empty: NO_FEEDS });
  const waiting = rows.flatMap((feed) => (feed.suggestions || []).map((one) => suggestionCard(feed, one, say)));
  return foldout(sourcesTitle(rows, { enabled: feeds.enabled }), [
    el('p', { class: 'field-help' }, boldParts(FEEDS_NOTE)),
    feeds.enabled === false ? el('p', { class: 'field-help' }, boldParts(FEEDS_OFF)) : null,
    bar([button('Add a feed…', () => addFeed(feeds), { tone: 'warn' })]),
    grid,
    ...waiting,
  ], { open: waiting.length > 0 });
}

function eventCell(row) {
  const event = row.event || {};
  if (event.id) return badge(`#${event.id} ${event.status}`, EVENT_TONE[event.status] || null);
  if (event.waiting) return el('span', { class: 'cell-quiet', text: 'waiting for dates' });
  return el('span', { class: 'cell-quiet', text: '—' });
}

function waitingStrip(rows) {
  const waiting = rows.filter((one) => one.next_waiting);
  if (!waiting.length) return null;
  const count = waiting.length;
  return el('p', { class: 'notice mx-line', 'data-tone': 'warn' }, [
    el('span', { text: said(NEXT_WAITING, { count, s: count === 1 ? '' : 's', have: count === 1 ? 'has' : 'have' }) }),
    ...waiting.flatMap((one, index) => [
      index ? el('span', { text: ' · ' }) : null,
      textAction(one.name, () => openMarathon(one.id, one.name)),
    ]),
  ]);
}

function listSection(payload, feeds, say) {
  const rows = payload.marathons || [];
  const list = section('Marathons', LIST_NOTE, { count: rows.length, id: 'marathons', open: true });
  const add = button('Add a marathon', () => addMarathon(), { tone: 'warn' });
  const grid = table([
    { label: 'Marathon', cell: (row) => textAction(row.name, () => openMarathon(row.id, row.name)) },
    { label: 'Dates', cell: (row) => datesOf(row) },
    { label: 'State', cell: (row) => badge(row.phase_word, PHASE_TONE[row.phase] || null) },
    { label: `${BAF} runs`, cell: (row) => `${row.ours} of ${row.runs}` },
    { label: 'Schedule', cell: (row) => el('span', {
      class: 'cell-quiet mx-line',
      'data-tone': row.last_fetch_ok === false ? 'warn' : undefined,
      text: scheduleCell(row),
    }) },
    { label: 'Event', cell: (row) => eventCell(row) },
  ], rows, { empty: NOTHING_YET });
  list.body.append(...[
    el('p', { class: 'field-help' }, [el('span', { text: 'Marathon posts are ' }), modeChip(payload.mode), el('span', { text: '.' })]),
    payload.mode === 'off' ? el('p', { class: 'field-help' }, boldParts(said(MODE_OFF, { mode: payload.mode }))) : null,
    payload.mode === 'shadow' ? el('p', { class: 'field-help' }, boldParts(MODE_SHADOW)) : null,
    say,
    card(null, [grid, bar([add])]),
    waitingStrip(rows),
    sourcesFoldout(feeds, say),
  ].filter(Boolean));
  return full(list.node);
}

async function readCadence() {
  const specs = settingsNamespace(await settings().catch(() => ({})), 'marathon');
  const held = (key) => {
    const found = specs.find((one) => one.key === key);
    return found ? (found.value ?? found.default ?? null) : null;
  };
  return { near: held('marathon_poll_minutes'), far: held('marathon_far_poll_hours') };
}

/** The Events page's Marathons section: the list, its drawer and the sources that feed it. */
export async function marathonsSection({ reload, openEvent }) {
  refresh = reload;
  showEvent = openEvent;
  const [payload, feeds, found] = await Promise.all([
    api('/api/marathons'),
    api('/api/marathons/feeds').catch((error) => ({ error: sentenceFor(error) })),
    readCadence(),
  ]);
  cadence = found;
  eventModeDefault = payload.event_mode_default || 'none';
  eventModes = Array.isArray(payload.event_modes) ? payload.event_modes : [];
  const say = sayAgain('marathons', notice());
  const node = listSection(payload, feeds, say);
  const wanted = wantedId();
  if (wanted && !deepLinked) {
    deepLinked = true;
    const one = (payload.marathons || []).find((row) => String(row.id) === wanted);
    openMarathon(wanted, one ? one.name : `Marathon #${wanted}`);
  }
  return node;
}

/** The Events page's detail card links back here by address, so the drawer opens the same way. */
export function marathonHref(marathonId) {
  return `#marathon-${marathonId}`;
}

window.addEventListener('hashchange', () => {
  const wanted = wantedId();
  if (!wanted) {
    if (shown.id) closeDrawer();
    return;
  }
  if (wanted === shown.id) return;
  openMarathon(wanted, `Marathon #${wanted}`);
});
