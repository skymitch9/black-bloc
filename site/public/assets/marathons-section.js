import { api, names, send, settings, settingsNamespace } from './api.js';
import {
  BAF,
  CARD_PEOPLE,
  SETTINGS_FOLD,
  datesWords,
  dayTitle,
  daysOf,
  entryFor,
  feedReading,
  headerCounts,
  headerReading,
  postsLine,
  runChip,
  runLength,
  said,
  scheduleCell,
  slotPeople,
  slotTime,
  sourceCell,
  sourcesTitle,
  whenWords,
} from './marathon-words.js';
import {
  ask,
  askForm,
  avatar,
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
  linkAction,
  memberPicker,
  modeChip,
  modeSwitch,
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
  table,
  textAction,
  when,
} from './ui.js';

const shown = { id: null, slots: new Set(), people: new Set(), settings: false, focus: null, where: null };
const HASH = /^marathon-(\d+)$/;
let refresh = async () => {};
let showEvent = () => {};
let eventModeDefault = 'none';
let eventModes = [];
let cadence = { near: null, far: null, lead: null, slack: null, modeSpec: null };
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
const NO_RUNS = 'No runs on this schedule yet — it may not be published. Black Bloc keeps '
  + 'reading it.';
const NO_BAF = `Nobody from ${BAF} is on this schedule yet — open a slot below and **Link to a member…**.`;
const SCHEDULE_HEAD = 'The schedule';
const FILTER_PLACEHOLDER = 'name, Twitch or game';
const NO_HIT = 'Nothing on this schedule matches that.';
const SLOT_NOBODY = 'Nobody is named on this slot.';
const NO_TWITCH = 'no Twitch channel';
const LOOKS_LIKE = 'looks like @{username} — Link?';
const LINK_TITLE = 'Link {name} to a member';
const LINK_NOTE = '**{name}** as {marathon}’s schedule writes it. A link beats the automatic match '
  + `and makes their runs ${BAF} at once; **Unlink** gives it back.`;
const SPOTLIGHT_TITLE = 'Spotlight {name}?';
const SPOTLIGHT_BODY = 'A channel-only row for twitch.tv/{login} goes on the Go-live page — spotlit '
  + 'and announced while they stream, from {lead} h before their first run on {marathon} to {slack} h '
  + 'after their last. Stop spotlighting takes it off again.';
const SPOTLIGHT_SLOT_BODY = 'A channel-only row for twitch.tv/{login} goes on the Go-live page — '
  + 'spotlit and announced while they stream, from {lead} h before this run to {slack} h after it. '
  + 'Stop spotlighting takes it off again.';
const UNSPOTLIGHT_TITLE = 'Stop spotlighting {name}?';
const UNSPOTLIGHT_BODY = 'twitch.tv/{login} comes off the Go-live page the same way its own Remove '
  + 'takes it off; any announcement already out stays as posted.';
const SPOTLIT = 'Spotlit';
const SPOTLIT_UNTIL = 'Spotlit until {when}';
const OPEN_GOLIVE = 'Open on Go-live ↗';
const ON_GOLIVE = 'already on the Go-live page ↗';
const GOLIVE_HREF = 'golive.html#streamers';
const OTHER_PAIRINGS = 'Links to names not on this schedule · {count}';
const PEOPLE_FAILED = 'The people on this schedule could not be read just now. Reload to try again.';
const PART_WORDS = { runner: 'runner', host: 'host', commentator: 'on commentary' };
const SOURCES_BUTTON = 'Sources…';
const SOURCES_DRAWER = 'Where marathons come from';
const GETTING_SOURCES = 'Reading the sources…';
const REMOVE_BODY = 'Its runs and pairings go with it and its ping window closes. Posts already '
  + 'made stay where they are.';
const WINDOW_PLAIN = 'Ping window {start} – {end}.';
const NO_WINDOW = 'No ping window — the marathon has no channel, no dates yet, or is paused.';
const CHANNEL_GONE = 'Its channel row is gone from the Go-live page, so it has no window and '
  + 'no live title. Pick another channel, or none.';
const READ_FROM = 'Read from the ';
const SOURCE_LINK = '{source} ↗';
const FEED_WORD = 'feed';
const EVENT_HEAD = 'Event #{id} {status}';
const CHANNEL_GONE_SHORT = 'its channel is gone from Go-live';
const SAVE_SETTINGS = 'Save';
const SAVED = 'Saved.';
const NOTHING_CHANGED = 'Nothing changed, so nothing was saved.';
const POLL_LABEL = 'Re-read every';
const POLL_UNIT = 'minutes';
const POLL_HELP = 'While it is near, 10 to 120; blank = the default ({minutes}). Far off: every {far} h.';
const NEXT_WHEN_ENDS = 'After this one: ';
const NEXT_LINE = '{marathon} is over — the next GDQ event is **{next}**, {date} ({relative}).';
const NEXT_ADDED = 'Added — see **{name}** on the list.';
const NEXT_DISMISSED = 'Dismissed — **Look again** asks the tracker once more.';
const NEXT_NONE = '{marathon} is over and the GDQ tracker lists nothing ahead yet.';
const NEXT_NOT_YET = '{marathon} is over. Black Bloc has not looked up the next GDQ event yet.';
const NEXT_NOTE = 'Staff decide: nothing is added until someone presses **Add it**. It is read '
  + 'from the tracker link and airs on this marathon’s channel.';
const HELD_NOTE = 'held by staff';
const EVENT_SELECT = 'Event';
const EVENT_SELECT_HELP = 'No event by default. One event for the marathon goes into the events '
  + 'review above, dated from the schedule. An event per ' + BAF + ' run is approved at once and '
  + 'follows the schedule as runs move — the events feature announces each one as it starts. '
  + 'Both does the two. marathon_event_mode_default decides where this starts.';
const EVENT_SELECT_SHORT = 'Which Discord events this marathon makes; the setting explains the '
  + 'four choices.';
const EVENT_NONE = 'No event.';
const MODE_LABEL = 'Marathon posts are';
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

function nextBlock(marathon, say) {
  if (!marathon.next) return [];
  const moves = nextMoves(marathon, say);
  return [el('div', { class: 'mx-next' }, [
    el('p', { class: 'field-help mx-line' }, [el('span', { class: 'cell-quiet', text: NEXT_WHEN_ENDS }), ...boldParts(nextSentence(marathon))]),
    marathon.next.state === 'open' ? line(NEXT_NOTE) : null,
    marathon.next.url && marathon.next.state !== 'none'
      ? el('p', { class: 'field-help' }, [el('a', { class: 'say-nothing-do', href: marathon.next.url, text: 'the tracker ↗', rel: 'noreferrer', target: '_blank' })])
      : null,
    moves.length ? bar(moves) : null,
  ])];
}

function joined(parts) {
  const kept = parts.filter(Boolean);
  return kept.flatMap((one, index) => (index ? [el('span', { class: 'mx-dot', text: ' · ' }), one] : [one]));
}

function eventHead(marathon) {
  const event = marathon.event || {};
  if (!event.id) return null;
  const words = said(EVENT_HEAD, { id: event.id, status: event.status || 'gone' });
  if (event.status === 'gone') return el('span', { text: words });
  const open = textAction(`${words} ↗`, () => {
    closeDrawer();
    showEvent(event.id);
  });
  open.dataset.tone = EVENT_TONE[event.status] || '';
  return open;
}

function channelHead(marathon) {
  if (marathon.channel_gone) return el('span', { class: 'mx-line', 'data-tone': 'warn', text: CHANNEL_GONE_SHORT });
  if (!marathon.channel_login) return null;
  return linkAction(marathon.channel_login, GOLIVE_HREF);
}

function headerBlock(marathon, board, say) {
  const reading = headerReading(marathon);
  const timeZone = (board && board.timezone) || undefined;
  return [
    el('p', { class: 'mx-head' }, joined([
      badge(marathon.phase_word, PHASE_TONE[marathon.phase] || null),
      el('span', { text: datesWords(marathon, timeZone) }),
      marathon.schedule_page
        ? el('a', { class: 'say-nothing-do', href: marathon.schedule_page, text: said(SOURCE_LINK, { source: marathon.source_word }), rel: 'noreferrer', target: '_blank' })
        : el('span', { text: marathon.source_word }),
      marathon.feed_name && marathon.feed_id ? textAction(FEED_WORD, () => openFeed(marathon.feed_id)) : null,
    ])),
    el('p', { class: 'field-help mx-head-quiet' }, joined([
      el('span', { class: 'mx-line', 'data-tone': reading.tone || undefined, text: reading.text }),
      el('span', { text: headerCounts(marathon.run_list) }),
      eventHead(marathon),
      channelHead(marathon),
    ])),
    ...nextBlock(marathon, say),
  ];
}

function partWords(parts) {
  return (parts || []).map((one) => PART_WORDS[one] || one).join(', ');
}

async function pairTo(marathon, say, name, userId, everywhere = false) {
  const done = await run(say, () => send(`/api/marathons/${marathon.id}/people`, 'POST', {
    runner_name: name,
    user_id: userId,
    everywhere,
  }), (found) => found?.message);
  await after(marathon, done);
}

async function linkPerson(marathon, say, person, entry, runId) {
  const picker = memberPicker({ label: 'Member' });
  const near = entry && entry.looks_like;
  if (near) picker.set({ id: near.user_id, name: near.username });
  const scope = segment([{ value: 'this', label: 'This schedule' }, { value: 'every', label: 'Every schedule' }], 'this');
  let done = null;
  const sure = await askForm({
    title: said(LINK_TITLE, { name: person.name }),
    body: [
      el('p', { class: 'ask-body' }, boldParts(said(LINK_NOTE, { name: person.name, marathon: marathon.name }))),
      picker.node,
      field('Where it counts', scope),
    ],
    confirmLabel: 'Link them',
    tone: 'warn',
    onConfirm: async () => {
      done = await send(`/api/marathons/${marathon.id}/people`, 'POST', {
        runner_name: person.name,
        user_id: picker.id,
        everywhere: scope.readValue() === 'every',
      });
      return null;
    },
  });
  if (!sure || !done) return;
  shown.focus = runId;
  await after(marathon, { ok: true, found: done });
}

async function spotlightPerson(marathon, say, entry, runId) {
  const body = said(runId ? SPOTLIGHT_SLOT_BODY : SPOTLIGHT_BODY, {
    login: entry.login,
    lead: cadence.lead ?? 2,
    slack: cadence.slack ?? 2,
    marathon: marathon.name,
  });
  const sure = await ask({ title: said(SPOTLIGHT_TITLE, { name: entry.name }), body: [body], confirmLabel: 'Spotlight them', tone: 'warn' });
  if (!sure) return;
  shown.focus = runId;
  const done = await run(say, () => send(`/api/marathons/${marathon.id}/people/${encodeURIComponent(entry.login)}/spotlight`, 'POST', runId ? { run_id: runId } : {}), (found) => found?.message);
  await after(marathon, done);
}

async function unspotlightPerson(marathon, say, entry, runId) {
  const sure = await ask({ title: said(UNSPOTLIGHT_TITLE, { name: entry.name }), body: [said(UNSPOTLIGHT_BODY, { login: entry.login })], confirmLabel: 'Stop spotlighting' });
  if (!sure) return;
  shown.focus = runId;
  const done = await run(say, () => send(`/api/marathons/${marathon.id}/people/${encodeURIComponent(entry.login)}/spotlight`, 'DELETE'), (found) => found?.message);
  await after(marathon, done);
}

function spotlightBits(marathon, say, entry, runId) {
  if (!entry || !entry.login) return [];
  if (entry.spotlight_id) {
    return [
      el('span', { class: 'cell-quiet', text: entry.spotlight_until ? said(SPOTLIT_UNTIL, { when: whenWords(entry.spotlight_until) }) : SPOTLIT }),
      linkAction(OPEN_GOLIVE, GOLIVE_HREF),
      button('Stop spotlighting', () => unspotlightPerson(marathon, say, entry, runId), { tone: 'quiet' }),
    ];
  }
  if (entry.channel_id) return [linkAction(ON_GOLIVE, GOLIVE_HREF)];
  return [button('Spotlight…', () => spotlightPerson(marathon, say, entry, runId), { tone: 'quiet' })];
}

function matchBits(marathon, say, entry, person, runId, { inSlot = false } = {}) {
  const bits = [];
  if (entry && entry.member && entry.matched_by === 'pairing' && entry.pairing_id) {
    bits.push(el('span', { class: 'cell-quiet', text: entry.matched_word }));
    bits.push(button('Unlink', async () => {
      shown.focus = runId;
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/people/${entry.pairing_id}`, 'DELETE'), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'quiet' }));
    return bits;
  }
  if (entry && entry.member) bits.push(el('span', { class: 'cell-quiet', text: entry.matched_word || '' }));
  const near = entry && !entry.member && entry.looks_like;
  if (inSlot && near) {
    bits.push(textAction(said(LOOKS_LIKE, { username: near.username }), () => {
      shown.focus = runId;
      pairTo(marathon, say, person.name, near.user_id);
    }));
  }
  if (inSlot) bits.push(button('Link to a member…', () => linkPerson(marathon, say, person, entry, runId), { tone: entry && entry.member ? 'quiet' : 'warn' }));
  return bits;
}

function bafLine(marathon, say, entry, timeZone) {
  const key = String(entry.key || entry.login || entry.name);
  const chips = (entry.runs || []).map((one) => el('span', {
    class: 'mx-chip',
    'data-state': one.state,
    title: one.category || '',
    text: runChip(one, timeZone),
  }));
  const node = el('details', {
    class: 'mx-person',
    'data-live': entry.live ? 'true' : undefined,
    open: shown.people.has(key) || undefined,
  }, [
    el('summary', { class: 'mx-person-head' }, [
      avatar(entry.member_name || entry.name, entry.avatar_url),
      el('span', { class: 'mx-person-who' }, [
        el('strong', { text: entry.member_name || entry.name }),
        entry.username ? el('span', { class: 'cell-quiet', text: ` @${entry.username}` }) : null,
      ]),
      el('span', { class: 'mx-chips' }, chips),
      el('span', { class: 'cell-quiet mx-person-part', text: partWords(entry.parts) }),
    ]),
    el('div', { class: 'bar mx-person-moves mx-person-body' }, [
      entry.login
        ? el('a', { class: 'cell-quiet mono', href: `https://twitch.tv/${entry.login}`, rel: 'noreferrer', target: '_blank', text: `twitch.tv/${entry.login}` })
        : el('span', { class: 'cell-quiet', text: NO_TWITCH }),
      ...matchBits(marathon, say, entry, entry, null),
      ...spotlightBits(marathon, say, entry, null),
    ]),
  ]);
  node.addEventListener('toggle', () => {
    if (node.open) shown.people.add(key);
    else shown.people.delete(key);
  });
  return node;
}

function slotChip(person) {
  return el('span', {
    class: 'mx-chip',
    'data-baf': person.user_id ? 'true' : undefined,
    'data-quiet': person.part === 'runner' ? undefined : 'true',
    title: person.part,
    text: person.user_id ? `${person.member_name || person.name} ✦${BAF}` : person.name,
  });
}

function slotPersonLine(marathon, say, board, run, person) {
  const entry = entryFor(board, run.id, person);
  return el('div', { class: 'mx-slot-person' }, [
    el('span', { class: 'mx-slot-name' }, [
      el('strong', { text: person.user_id ? (person.member_name || person.name) : person.name }),
      person.user_id ? el('span', { class: 'badge', 'data-tone': 'ok', text: BAF }) : null,
      el('span', { class: 'cell-quiet', text: ` ${PART_WORDS[person.part] || person.part}` }),
      person.login ? el('span', { class: 'cell-quiet mono', text: ` · twitch.tv/${person.login}` }) : el('span', { class: 'cell-quiet', text: ` · ${NO_TWITCH}` }),
    ]),
    el('span', { class: 'bar mx-person-moves' }, [
      ...matchBits(marathon, say, entry, person, run.id, { inSlot: true }),
      ...spotlightBits(marathon, say, entry, run.id),
    ]),
  ]);
}

function slotRow(marathon, say, board, run, timeZone) {
  const people = slotPeople(run);
  const head = el('summary', { class: 'mx-slot-head' }, [
    el('span', { class: 'mono mx-slot-time', text: slotTime(run.scheduled_at, timeZone) }),
    el('span', { class: 'mx-slot-game' }, [
      el('strong', { text: run.game }),
      run.category ? el('span', { class: 'cell-quiet', text: ` · ${run.category}` }) : null,
      runLength(run) ? el('span', { class: 'cell-quiet mono', text: ` · ${runLength(run)}` }) : null,
      run.moved && run.previous_scheduled_at
        ? el('span', { class: 'cell-quiet', 'data-tone': 'warn', text: ` · moved from ${slotTime(run.previous_scheduled_at, timeZone)}` })
        : null,
    ]),
    el('span', { class: 'mx-chips' }, people.map(slotChip)),
    el('span', { class: 'cell-kind' }, [
      badge(run.state_word, STATE_TONE[run.state] || null),
      run.held ? badge(HELD_NOTE, 'warn') : null,
      run.event_id ? badge(`event #${run.event_id}`, EVENT_TONE[run.event_status] || null) : null,
    ]),
  ]);
  const node = el('details', {
    class: 'mx-slot',
    id: `slot-${run.id}`,
    'data-state': run.state,
    'data-baf': run.ours ? 'true' : undefined,
    open: shown.slots.has(String(run.id)) || undefined,
  }, [
    head,
    el('div', { class: 'mx-slot-body' }, [
      ...(people.length ? people.map((one) => slotPersonLine(marathon, say, board, run, one)) : [line(SLOT_NOBODY)]),
      runTools(marathon, run, say),
    ]),
  ]);
  node.addEventListener('toggle', () => {
    if (node.open) shown.slots.add(String(run.id));
    else shown.slots.delete(String(run.id));
  });
  node.dataset.search = [run.game, run.category, ...(run.people || []).flatMap((one) => [one.name, one.login, one.member_name])].filter(Boolean).join(' ').toLowerCase();
  return node;
}

function scheduleBlock(marathon, say, board) {
  const timeZone = board.timezone || undefined;
  const days = daysOf(marathon.run_list, timeZone);
  if (!days.length) return [line(NO_RUNS)];
  const folds = days.map((day) => {
    const fold = foldout(dayTitle(day), day.runs.map((one) => slotRow(marathon, say, board, one, timeZone)), { open: day.open || day.runs.some((one) => shown.slots.has(String(one.id))) });
    fold.classList.add('mx-day');
    fold.dataset.open = day.open ? 'true' : 'false';
    return fold;
  });
  const none = line(NO_HIT);
  none.hidden = true;
  const filter = searchField({
    label: 'Filter the schedule',
    placeholder: FILTER_PLACEHOLDER,
    onQuery: (query) => {
      let hits = 0;
      for (const fold of folds) {
        let here = 0;
        for (const slot of fold.querySelectorAll('.mx-slot')) {
          const hit = !query || slot.dataset.search.includes(query);
          slot.hidden = !hit;
          if (hit) here += 1;
        }
        fold.hidden = Boolean(query) && here === 0;
        fold.open = query ? here > 0 : fold.dataset.open === 'true';
        hits += here;
      }
      none.hidden = !query || hits > 0;
    },
  });
  return [el('div', { class: 'table-tools' }, [filter]), none, ...folds];
}

function otherPairings(marathon, say, board) {
  const onSchedule = new Set([...(board.baf || []), ...(board.others || [])]
    .flatMap((entry) => (entry.runs || []).map((one) => String(one.name).trim().toLowerCase())));
  const rows = (board.pairings || []).filter((one) => !onSchedule.has(one.runner_name));
  if (!rows.length) return null;
  return foldout(said(OTHER_PAIRINGS, { count: rows.length }), rows.map((one) => el('p', { class: 'field-help mx-line' }, [
    el('span', { text: `${one.runner_name} → ` }),
    nameNode(one.user_id, one.member_name),
    el('span', { class: 'cell-quiet', text: one.everywhere ? ' · every schedule ' : ' · this schedule ' }),
    step(marathon, say, 'Unlink', () => send(`/api/marathons/${marathon.id}/people/${one.id}`, 'DELETE')),
  ])));
}

function peopleCard(marathon, board, say) {
  if (!board || board.error) {
    const found = (board && board.error) || { text: PEOPLE_FAILED, tone: 'warn' };
    return card(CARD_PEOPLE, [notice(found.text, found.tone)]);
  }
  const timeZone = board.timezone || undefined;
  const baf = board.baf || [];
  return card(CARD_PEOPLE, [
    el('h4', { class: 'mx-block-head', text: `${BAF} · ${baf.length}` }),
    baf.length ? el('div', { class: 'mx-people' }, baf.map((one) => bafLine(marathon, say, one, timeZone))) : line(NO_BAF),
    el('h4', { class: 'mx-block-head', text: SCHEDULE_HEAD }),
    ...scheduleBlock(marathon, say, board),
    otherPairings(marathon, say, board),
  ]);
}

function eventState(marathon, say) {
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
  const move = event.id || event.wanted
    ? step(marathon, say, 'Unlink', () => send(`/api/marathons/${marathon.id}/event`, 'DELETE'))
    : step(marathon, say, 'Make an event now', () => send(`/api/marathons/${marathon.id}/event`, 'POST', {}), 'warn');
  return el('p', { class: 'field-help mx-line' }, [...state, el('span', { text: ' ' }), move]);
}

function windowWords(marathon) {
  if (!marathon.window || !marathon.channel_login) return NO_WINDOW;
  return said(WINDOW_PLAIN, { start: when(marathon.window.starts_at), end: when(marathon.window.ends_at) });
}

function pollWanted(given) {
  const text = given.trim();
  if (text === '') return null;
  return /^\d+$/.test(text) ? Number(text) : text;
}

async function settingsFold(marathon, say) {
  const mode = modePicker(marathon.event_mode || 'none');
  const picker = channelPicker(await channelChoices(), marathon.spotlight_id);
  const poll = el('input', {
    class: 'input',
    type: 'text',
    inputmode: 'numeric',
    size: 4,
    placeholder: 'default',
    value: marathon.poll_minutes ? String(marathon.poll_minutes) : '',
    'aria-label': `${POLL_LABEL} N ${POLL_UNIT}`,
  });
  const save = button(SAVE_SETTINGS, async () => {
    const body = {};
    if (mode.value !== (marathon.event_mode || 'none')) body.event_mode = mode.value;
    if (String(picker.value || '') !== String(marathon.spotlight_id || '')) body.spotlight_id = picker.value || null;
    const wanted = pollWanted(poll.value);
    if (wanted !== (marathon.poll_minutes || null)) body.poll_minutes = wanted;
    if (!Object.keys(body).length) {
      say.say(NOTHING_CHANGED, null);
      return;
    }
    const words = (found) => [found?.message, 'poll_minutes' in body ? pollSaid(marathon, wanted) : null].filter(Boolean).join(' ') || SAVED;
    const done = await run(say, () => send(`/api/marathons/${marathon.id}`, 'PATCH', body), words);
    if (done.ok) done.found = { ...(done.found || {}), message: words(done.found) };
    await after(marathon, done);
  }, { tone: 'warn' });
  const fold = foldout(SETTINGS_FOLD, [
    field(EVENT_SELECT, mode, EVENT_SELECT_SHORT),
    eventState(marathon, say),
    marathon.channel_gone ? notice(CHANNEL_GONE, 'warn') : null,
    field('Airs on', picker, windowWords(marathon)),
    field(POLL_LABEL, el('span', { class: 'mx-poll' }, [poll, el('span', { text: POLL_UNIT })]), said(POLL_HELP, { minutes: cadence.near ?? '—', far: cadence.far ?? '—' })),
    bar([save]),
  ], { open: shown.settings });
  fold.classList.add('mx-settings');
  fold.addEventListener('toggle', () => {
    shown.settings = fold.open;
  });
  return fold;
}

function pollSaid(marathon, wanted) {
  return wanted === null
    ? `**${marathon.name}** is re-read on the default gap again.`
    : `**${marathon.name}** is re-read every ${wanted} minutes while it is near.`;
}

function postsRow(marathon, say) {
  const posts = postsLine(marathon);
  const where = posts.hasBoard && marathon.board_channel_id;
  const move = textAction(posts.hasBoard ? 'Refresh the board' : 'Post the board', async () => {
    const done = await run(say, () => send(`/api/marathons/${marathon.id}/board`, 'POST', {}), (found) => found?.message);
    await after(marathon, done);
  });
  return el('p', { class: 'field-help mx-line mx-posts' }, joined([
    el('span', {}, [el('span', { text: posts.board }), where ? el('span', { text: ' ' }) : null, where ? nameNode(marathon.board_channel_id) : null]),
    posts.sent ? el('span', { text: posts.sent }) : null,
    move,
  ]));
}

function moveBar(marathon, say) {
  return bar([
    marathon.active ? step(marathon, say, 'Read it now', () => send(`/api/marathons/${marathon.id}/refresh`, 'POST', {}), 'warn') : null,
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
  ].filter(Boolean));
}

async function marathonDrawer(marathon, board, message) {
  if (marathon.board_channel_id) await names([marathon.board_channel_id]).catch(() => null);
  const say = notice();
  if (message) say.say(message, 'ok');
  return [
    say,
    ...headerBlock(marathon, board, say),
    peopleCard(marathon, board, say),
    await settingsFold(marathon, say),
    postsRow(marathon, say),
    moveBar(marathon, say),
  ];
}

async function openMarathon(marathonId, title, message = '') {
  if (shown.id !== String(marathonId)) {
    shown.slots = new Set();
    shown.people = new Set();
    shown.settings = false;
  }
  shown.id = String(marathonId);
  shown.where = 'marathon';
  if (wantedId() !== shown.id) {
    history.replaceState(null, '', `${location.pathname}${location.search}#marathon-${shown.id}`);
  }
  openDrawer(title || `Marathon #${marathonId}`, sayNothing(GETTING_IT), { onClose: forgetHash });
  try {
    const [marathon, board] = await Promise.all([
      api(`/api/marathons/${encodeURIComponent(marathonId)}`),
      api(`/api/marathons/${encodeURIComponent(marathonId)}/people`).catch((error) => ({ error: sentenceFor(error) })),
    ]);
    openDrawer(marathon.name, await marathonDrawer(marathon, board, message), { onClose: forgetHash });
    const focus = shown.focus ? document.getElementById(`slot-${shown.focus}`) : null;
    shown.focus = null;
    if (focus) {
      focus.open = true;
      focus.scrollIntoView({ block: 'center' });
    }
  } catch (error) {
    const found = sentenceFor(error);
    openDrawer(title || `Marathon #${marathonId}`, [notice(found.text, found.tone)], { onClose: forgetHash });
  }
}

async function feedStep(say, work) {
  const done = await run(say, work, (found) => found?.message);
  if (!done.ok) return done;
  await refresh();
  if (shown.where === 'sources') await openSources((done.found || {}).message || '');
  else keepSaying('marathons', say);
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
  shown.where = 'feed';
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
  await refresh();
  await openSources(made.message);
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

function sourcesBody(feeds, say) {
  if (feeds.error) return [notice(feeds.error.text, feeds.error.tone)];
  const rows = feeds.feeds || [];
  const grid = table([
    { label: 'Channel', cell: (row) => el('span', {}, [textAction(row.channel_name || row.name, () => openFeed(row.id)), row.active ? null : badge('paused')]) },
    { label: 'Source', cell: (row) => row.source_word },
    { label: 'Checks', cell: (row) => feedCheckCell(row) },
    { label: 'New events', cell: (row) => actionCell(row, say) },
    { label: '', cell: (row) => feedTools(row, say) },
  ], rows, { empty: NO_FEEDS });
  const waiting = rows.flatMap((feed) => (feed.suggestions || []).map((one) => suggestionCard(feed, one, say)));
  return [
    say,
    el('p', { class: 'field-help' }, boldParts(FEEDS_NOTE)),
    feeds.enabled === false ? el('p', { class: 'field-help' }, boldParts(FEEDS_OFF)) : null,
    bar([button('Add a feed…', () => addFeed(feeds), { tone: 'warn' })]),
    grid,
    ...waiting,
  ];
}

async function openSources(message = '') {
  shown.where = 'sources';
  const say = notice();
  if (message) say.say(message, 'ok');
  openDrawer(SOURCES_DRAWER, sayNothing(GETTING_SOURCES));
  const feeds = await api('/api/marathons/feeds').catch((error) => ({ error: sentenceFor(error) }));
  openDrawer(feeds.error ? SOURCES_DRAWER : sourcesTitle(feeds.feeds || [], { enabled: feeds.enabled }), sourcesBody(feeds, say));
}

function eventCell(row) {
  const event = row.event || {};
  if (event.id) return badge(`#${event.id} ${event.status}`, EVENT_TONE[event.status] || null);
  if (event.waiting) return el('span', { class: 'cell-quiet', text: 'waiting for dates' });
  return el('span', { class: 'cell-quiet', text: row.event_mode_word || EVENT_NONE.replace(/\.$/, '') });
}



function listSection(payload, feeds, say) {
  const rows = payload.marathons || [];
  const list = section('Marathons', LIST_NOTE, { count: rows.length, id: 'marathons', open: true });
  const add = button('Add a marathon', () => addMarathon(), { tone: 'warn' });
  const sources = button(SOURCES_BUTTON, () => openSources(), { tone: 'quiet' });
  const grid = table([
    { label: 'Marathon', cell: (row) => textAction(row.name, () => openMarathon(row.id, row.name)) },
    { label: 'Source', cell: (row) => el('span', { class: 'cell-quiet', text: sourceCell(row) }) },
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
  const switched = cadence.modeSpec
    ? modeSwitch(cadence.modeSpec, { onSaved: () => refresh() })
    : null;
  list.body.append(...[
    switched
      ? el('div', { class: 'bar mx-mode' }, [el('span', { class: 'cell-quiet', text: MODE_LABEL }), switched.node, switched.say])
      : el('p', { class: 'field-help' }, [el('span', { text: 'Marathon posts are ' }), modeChip(payload.mode), el('span', { text: '.' })]),
    payload.mode === 'off' ? el('p', { class: 'field-help' }, boldParts(said(MODE_OFF, { mode: payload.mode }))) : null,
    payload.mode === 'shadow' ? el('p', { class: 'field-help' }, boldParts(MODE_SHADOW)) : null,
    say,
    card(null, [grid, bar([add, sources])]),
  ].filter(Boolean));
  return full(list.node);
}

async function readCadence() {
  const specs = settingsNamespace(await settings().catch(() => ({})), 'marathon');
  const held = (key) => {
    const found = specs.find((one) => one.key === key);
    return found ? (found.value ?? found.default ?? null) : null;
  };
  return {
    near: held('marathon_poll_minutes'),
    far: held('marathon_far_poll_hours'),
    lead: held('marathon_spotlight_lead_hours'),
    slack: held('marathon_spotlight_slack_hours'),
    modeSpec: specs.find((one) => one.key === 'marathon_mode') || null,
  };
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
