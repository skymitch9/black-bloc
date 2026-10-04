import { api, names, saveSetting, send, settings, settingsNamespace } from './api.js';
import {
  BAF,
  CARD_PEOPLE,
  SETTINGS_FOLD,
  archiveCounts,
  archiveTitle,
  archivedWhen,
  archivedWho,
  datesWords,
  dayTitle,
  daysOf,
  entryFor,
  feedSearchFields,
  feedReading,
  headerCounts,
  headerReading,
  postsLine,
  runChip,
  runLength,
  said,
  scheduleCell,
  slotPeople,
  slotText,
  slotTime,
  sourceCell,
  sourcesTitle,
  trackMoves,
  trackedCell,
  trackedLine,
  whenWords,
} from './marathon-words.js';
import { announceMoves, announcedSaid, pingsCard, spotlightCard } from './spotlight-controls.js';
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
  listFilter,
  memberPicker,
  modeChip,
  modeSwitch,
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

const shown = { id: null, slots: new Set(), people: new Set(), settings: false, focus: null, where: null, archived: false };
const HASH = /^marathon-(\d+)$/;
let refresh = async () => {};
let showEvent = () => {};
let eventModeDefault = 'none';
let eventModes = [];
let cadence = { near: null, far: null, lead: null, slack: null, archiveDays: null, modeSpec: null };
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
const NO_BAF_ARCHIVED = `Nobody from ${BAF} was on this schedule.`;
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
const REMOVE_BODY = 'It moves to the archive with its runs and pairings, its ping window closes '
  + 'and its events are called off; a feed will not add it again. Posts already made stay where '
  + 'they are, and Restore in the archive brings it back.';
const ARCHIVE_BODY = 'It stops being read and its ping window closes. Its runs, people and posts are '
  + 'kept under Archive below the list, and Restore brings it back paused.';
const RESTORE_BODY = 'It comes back to the list paused, with its runs and people — nothing is read '
  + 'or posted until someone presses Resume.';
const ARCHIVE_NOTE = 'Marathons that ended {days} day(s) ago or more, and any staff archived or '
  + 'removed. Nothing is deleted: a row opens it read-only, with Restore.';
const ARCHIVE_EMPTY = 'Nothing is archived yet. A marathon moves here {days} day(s) after its last run.';
const ARCHIVE_FAILED = 'The archive could not be read just now. Reload to try again.';
const ARCHIVE_MORE = 'Show {count} more';
const ARCHIVED_NOTE = 'Archived — read-only. **Restore** puts it back on the list, paused.';
const WINDOW_PLAIN = 'Ping window {start} – {end}.';
const NO_WINDOW = 'No ping window — the marathon has no channel, no dates yet, or is paused.';
const CHANNEL_GONE = 'Its channel row is gone from the Go-live page, so it has no window and '
  + 'no live title. Pick another channel, or none.';
const READ_FROM = 'Read from: ';
const SOURCE_LINK = '{source} ↗';
const FEED_WORD = 'feed';
const EVENT_HEAD = 'Event #{id} {status}';
const CHANNEL_GONE_SHORT = 'its channel is gone from Go-live';
const SAVE_SETTINGS = 'Save';
const SAVED = 'Saved.';
const NOTHING_CHANGED = 'Nothing changed, so nothing was saved.';
const SCHEDULE_LINK_ACTION = 'Change the schedule link…';
const SCHEDULE_LINK_TITLE = 'Change the schedule link for {name}';
const SCHEDULE_LINK_FIELD = 'The new schedule link';
const SCHEDULE_LINK_NOTE = 'Any schedule Black Bloc reads: a GDQ or RPG Limit Break tracker, horaro.net, Oengus, '
  + 'Fastest Furs or Lady Arcaders. It keeps its tracking, thread, event and switches, and reads the new '
  + 'schedule at once.';
const SCHEDULE_LINK_NOW = 'Reads from ';
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
const CERTAIN_NOTE = 'certain';
const CERTAIN_HELP = 'The stream’s title and its Twitch category both name this run.';
const SHEET_SAID = ' · sheet said {time}';
const SHEET_TIMES_ACTION = 'Back to the sheet’s times';
const EVENT_SELECT = 'Event';
const EVENT_SELECT_HELP = 'No event by default. One event for the marathon goes into the events '
  + 'review above, dated from the schedule. An event per ' + BAF + ' run and per ' + BAF + ' host block (the runs '
  + 'a host hosts in a row) is approved at once and follows the schedule as runs move — the events feature '
  + 'announces each one as it starts. Hosts are always found; they never make a run a ' + BAF + ' run. '
  + 'Both does the two. marathon_event_mode_default decides where this starts.';
const SPOTLIGHT_FIELD = 'Follow the schedule';
const SPOTLIGHT_CHOICES = [{ value: 'follow', label: 'On' }, { value: 'off', label: 'Off' }];
const SPOTLIGHT_HELP = 'On: the channel is spotlit from marathon_spotlight_lead_minutes before the first run '
  + 'to marathon_spotlight_tail_minutes after the last, and the end moves when the schedule does. A channel '
  + 'kept for ever stays as it is. Staff turning the spotlight off, or saving dates, takes it over.';
const SPOTLIGHT_SHARED = 'These are the channel’s own controls — every change here shows on the Go-live page too.';
const OPEN_ON_GOLIVE = 'Open on Go-live ↗';
const SPOTLIT_WORDS = { held: 'spotlit', held_other: 'spotlit', kept: 'spotlit', until: 'spotlit', scheduled: 'scheduled' };
const NOT_SPOTLIT = 'not spotlit';
const PING_FIELD = 'Ping the marathon role';
const PING_CHOICES = [{ value: 'on', label: 'On' }, { value: 'off', label: 'Off' }];
const PING_HELP = 'On: the public heads-up marathon_ping_minutes before a BaF run mentions the Marathon role (marathon_role_id, marathon_role_pings), '
  + 'its run reminders (the thread’s and the public copy), shoutouts and public highlights mention the runner’s ping role and its channel’s, '
  + 'and its channel gets a ping window while it runs. Off (the default): they still post, with no mention. '
  + 'marathon_ping_role_default decides where a new marathon starts.';
const ROLE_PING_ON = 'Marathon role';
const ROLE_PING_OFF = 'no Marathon role';
const HIGHLIGHT_FIELD = 'Auto-highlight BaF runners when live';
const HIGHLIGHT_HELP = 'On: the moment a BaF run goes live its highlight posts in the public channel '
  + '(marathon_public_channel_id, blank = go-live) — the thread is staff-only, so this is what members see. '
  + 'For a BaF host it is their host block: posted when the block goes live, edited to done after its last run. '
  + 'Off (the default): nothing is highlighted. Nobody opted out is highlighted, and nothing is while BaF '
  + 'announcements is off. marathon_public_highlight_default decides where a new marathon starts.';
const ANNOUNCE_FIELD = 'BaF announcements';
const ANNOUNCE_HELP = 'On: every BaF runner and host of this marathon is announced publicly — the reminders at every '
  + 'marathon_reminder_minutes mark (marathon_public_reminders is the master switch) and, with Auto-highlight on, the '
  + 'highlight. Off: nobody on this marathon gets a public post. Anyone can be opted out on their own from the People '
  + 'card or the Opt out of highlight button on their run’s post. Follow uses marathon_announcements_default.';
const SWITCH_FOLLOW = 'Follow the setting ({state})';
const TWITCH_FIX_FIELD = 'Twitch name (optional)';
const TWITCH_FIX_HELP = 'Only when the schedule gives the wrong channel. It replaces the schedule’s everywhere Black Bloc '
  + 'uses one — Spotlight…, the run posts and live matching. Blank keeps what the schedule says.';
const TWITCH_FIX_TITLE = 'Twitch name for {name}';
const TWITCH_FIX_NOTE = 'The schedule says **{sheet}**. Type the channel {name} really streams on, or leave it blank to '
  + 'go back to the schedule’s.';
const TWITCH_FIX_BUTTON = 'Twitch name…';
const OPTED_OUT = 'Opted out of public posts';
const OPT_OUT = 'Opt out of highlight';
const OPT_IN = 'Opt back in';
const OPT_OUT_TITLE = 'Opt {name} out of this marathon’s public posts?';
const OPT_OUT_BODY = 'No reminders and no highlight for them on this marathon. A highlight of theirs that is up is edited to say it was taken down. Opt back in undoes it from the next reminder mark.';
const FIXED_FROM = ' (fixed from twitch.tv/{sheet})';
const EVENT_SELECT_SHORT = 'Which Discord events this marathon makes; the setting explains the '
  + 'four choices.';
const EVENT_NONE = 'No event.';
const MODE_LABEL = 'Marathon posts are';
const EVENT_WAITING = 'Waiting for the schedule to publish, then one event for the marathon.';
const EVENT_OPEN = 'Open ↗';
const MODES_FALLBACK = [
  { value: 'none', label: 'No event' },
  { value: 'marathon', label: 'One event for the marathon' },
  { value: 'runs', label: `An event per ${BAF} run and host block` },
  { value: 'both', label: 'Both' },
];
const FEED_MODE_FOLLOW = 'Whatever the setting says';
const FEED_MODE_HELP = 'What a marathon this feed adds does about events; the first choice '
  + 'follows marathon_event_mode_default.';
const FEED_MOVE_NOTE = 'Only a channel-only row that takes marathons and has no feed reading '
  + 'the same source can be picked.';
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
  + 'watches, one feed per source on a channel. Then what to read: the GDQ tracker, the RPG Limit '
  + 'Break tracker, a horaro.net event by its slug (ESA is `esa`), horaro.net events found by name '
  + '(Fast Paced Events), Oengus, which finds the channel’s own marathons on oengus.io by '
  + 'itself, Fastest Furs’ own event list, Lady Arcaders’ next events on ladyarcaders.com, or '
  + 'the GDQ Hotfix shows on the Hotfix schedule sheet.';
const HOTFIX_SHOWS_FIELD = 'Shows';
const HOTFIX_SHOWS_HELP = 'Every show on the Hotfix schedule this week. A ticked show becomes a '
  + 'marathon each run of days it airs. This is marathon_hotfix_shows in Settings; saving here '
  + 'changes it there.';
const HOTFIX_LOADING = 'Reading the Hotfix schedule…';
const HOTFIX_SAVE = 'Save the shows';
const HOTFIX_ADD = 'Add';
const HOTFIX_ADD_PLACEHOLDER = 'a show that is not on the sheet this week';
const HOTFIX_REMOVE = 'Remove';
const HOTFIX_OFF_SHEET = 'listed, not on the sheet this week';
const HOTFIX_TRACKED_LISTED = 'tracked — on the list';
const HOTFIX_TRACKED_BECAUSE = 'tracked because {who}';
const HOTFIX_NOT_TRACKED = 'not tracked';
const HOTFIX_PERSON = { runs: '{name} runs', hosts: '{name} hosts' };
const HOTFIX_HOSTED_BY = 'hosted by {hosts}';
const HOTFIX_NO_HOST = 'no host of its own';
const HOTFIX_CHIP_TITLE = '{runs} run(s) · host: {hosts}';
const HOTFIX_PEOPLE_ON = 'Shows a BaF person runs are tracked too, ticked or not '
  + '(marathon_hotfix_track_people). Hosts always count, like runners.';
const HOTFIX_PEOPLE_OFF = 'Only the ticked shows are tracked — marathon_hotfix_track_people is '
  + 'off, so a BaF runner on another show does not add it.';
const HOTFIX_STALE = 'The Hotfix schedule could not be read just now ({why}), so this is the copy '
  + 'read {when}.';
const HOTFIX_EMPTY_SHEET = 'The Hotfix sheet lists no shows right now.';
const HOTFIX_SEARCH_FROM = 8;
const HOTFIX_SEARCH_LABEL = 'Find a show';
const HOTFIX_SEARCH_PLACEHOLDER = 'a show, a host or a BaF name';
const HOTFIX_NO_HIT = 'No show matches that.';
const HOTFIX_SHOWS_SAVED = 'The Hotfix feed now reads {shows}. The next check uses them.';
const HOTFIX_SHEET_LINE = 'Reads the sheet the Hotfix page embeds: ';
const PICK_HELP = {
  gdq: 'Every event on the GDQ tracker that is still ahead.',
  rpglb: 'Every event on the RPG Limit Break tracker that is still ahead.',
  horaro: 'Every schedule of one horaro.net event — give its slug below.',
  oengus: 'Every marathon on oengus.io that streams on this channel’s Twitch — nothing to type.',
  horaro_events: 'Every horaro.net event that streams on this channel’s Twitch, found by searching '
    + 'event names for the Name below — Fast Paced Events’ are “Fast Pace for …”, so “Fast Pace”. '
    + 'Once added, its drawer takes several search words and the horaro.net account that owns the events.',
  fastestfurs: 'Every event on Fastest Furs’ own list at fastestfurs.com — nothing to type.',
  ladyarcaders: 'Lady Arcaders’ next events on ladyarcaders.com, found by trying the next event '
    + 'numbers — nothing to type.',
  gdq_hotfix: 'The GDQ Hotfix shows named in marathon_hotfix_shows (GDQueer by default), from the '
    + 'schedule sheet on gamesdonequick.com/hotfix/schedule — each run of days a show airs is one '
    + 'marathon. Nothing to type.',
};
const TRACKER_PICKS = ['gdq', 'rpglb'];
const sourceKind = (pick) => (TRACKER_PICKS.includes(pick) ? 'tracker' : pick);
const PICK_GUESS = { gamesdonequick: 'gdq', rpglimitbreak: 'rpglb', esamarathon: 'horaro', speedstuff4charity: 'oengus', fastpacedevents: 'horaro_events', fastestfurs: 'fastestfurs', ladyarcaders: 'ladyarcaders' };
const FEED_SEEN_NOTE = 'Remembers {count} Oengus marathon(s) it has already looked at, so each is '
  + 'read once. **Look again** reads them all once more.';
const FEED_SEEN_NOTE_HORARO = 'Remembers {count} horaro.net event(s) it has already looked at, '
  + 'so each one’s schedules are read once. **Look again** reads them all once more.';
const FEED_PROBE_NOTE = 'Remembers what {count} Lady Arcaders event number(s) answered; one with '
  + 'no calendar yet is asked again after four checks. **Look again** asks them all now.';
const FEED_NO_CHANNELS = 'There is no channel-only row on the Go-live page that takes '
  + 'marathons. Add the channel there first.';
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
const AUTO_CHOICES = [{ value: 'on', label: 'On' }, { value: 'off', label: 'Off' }];
const AUTO_FIELD = 'Auto-track';
const AUTO_HELP = 'On: each marathon this feed adds is tracked the moment its schedule is out — its '
  + 'thread is made and its posts begin. Off (the default): it waits in the inbox for staff to press Track.';
const THREAD_LINK = 'thread ↗';
const POST_NOW = 'Post it to the inbox now';
const INBOX_LINK = 'inbox ↗';
const TRACK_MOVES = {
  track: { label: 'Track', path: 'track', body: { on: true }, tone: 'warn' },
  anyway: { label: 'Track anyway', path: 'track', body: { on: true }, tone: 'warn' },
  untrack: { label: 'Untrack', path: 'track', body: { on: false }, tone: 'quiet' },
  ignore: { label: 'Ignore', path: 'ignore', body: { on: true }, tone: 'quiet' },
};
const FOUND_NOTE = 'Found, not tracked: it is read and kept current, and posts nothing. **Track** gives it '
  + 'its own thread beside the inbox for its board, reminders and shoutouts; **Ignore** keeps it quiet on the list.';

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
  if (shown.archived) return null;
  const base = `/api/marathons/${marathon.id}/runs/${row.id}`;
  const tools = [];
  if (row.shoutable && marathon.tracked) tools.push(step(marathon, say, 'Shout it now', () => send(`${base}/shout`, 'POST', {}), 'warn'));
  if (row.can_mark_done && (row.ours || row.state === 'live')) {
    tools.push(step(marathon, say, 'Mark done', () => send(`${base}/done`, 'POST', {})));
  }
  if (row.can_mark_live && !(row.shoutable && marathon.tracked)) tools.push(step(marathon, say, 'Mark it live', () => send(`${base}/live`, 'POST', {})));
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

function trackedHead(marathon) {
  const state = trackedCell(marathon);
  return el('span', { class: 'mx-tracked' }, joined([
    el('span', { class: 'mx-line', 'data-tone': state.tone || undefined, text: trackedLine(marathon) }),
    marathon.thread_url && marathon.tracked
      ? el('a', { class: 'say-nothing-do', href: marathon.thread_url, text: THREAD_LINK, rel: 'noreferrer', target: '_blank' })
      : null,
    marathon.inbox_message_url
      ? el('a', { class: 'say-nothing-do', href: marathon.inbox_message_url, text: INBOX_LINK, rel: 'noreferrer', target: '_blank' })
      : null,
  ]));
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
      trackedHead(marathon),
    ])),
    marathon.tracked_state === 'found' ? el('p', { class: 'field-help' }, boldParts(FOUND_NOTE)) : null,
    ...nextBlock(marathon, say),
  ].filter(Boolean);
}

function partWords(parts) {
  return (parts || []).map((one) => PART_WORDS[one] || one).join(', ');
}

function switchPicker(state) {
  const choices = [
    { value: 'follow', label: said(SWITCH_FOLLOW, { state: state && state.default ? 'on' : 'off' }) },
    { value: 'on', label: 'On' },
    { value: 'off', label: 'Off' },
  ];
  const now = !state || state.own === null || state.own === undefined ? 'follow' : (state.own ? 'on' : 'off');
  const node = segment(choices, now);
  node.now = now;
  return node;
}

function switchWanted(value) {
  return value === 'follow' ? null : value === 'on';
}

function twitchInput(value = '') {
  return el('input', { class: 'input', type: 'text', value, placeholder: 'junior_sm', autocomplete: 'off', spellcheck: 'false', 'aria-label': TWITCH_FIX_FIELD });
}

function twitchText(entry) {
  const fixed = entry && entry.sheet_login ? said(FIXED_FROM, { sheet: entry.sheet_login }) : '';
  return `twitch.tv/${entry.login}${fixed}`;
}

async function fixTwitch(marathon, say, entry, runId) {
  const input = twitchInput(entry.sheet_login ? entry.login : '');
  let done = null;
  const sure = await askForm({
    title: said(TWITCH_FIX_TITLE, { name: entry.name }),
    body: [
      el('p', { class: 'ask-body' }, boldParts(said(TWITCH_FIX_NOTE, { name: entry.name, sheet: entry.sheet_login || entry.login || '—' }))),
      field(TWITCH_FIX_FIELD, input, TWITCH_FIX_HELP),
    ],
    confirmLabel: 'Save',
    tone: 'warn',
    onConfirm: async () => {
      done = await send(`/api/marathons/${marathon.id}/people/${entry.pairing_id}`, 'PATCH', { twitch_login: input.value.trim() });
      return null;
    },
  });
  if (!sure || !done) return;
  shown.focus = runId;
  await after(marathon, { ok: true, found: done });
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
  const twitch = twitchInput();
  let done = null;
  const sure = await askForm({
    title: said(LINK_TITLE, { name: person.name }),
    body: [
      el('p', { class: 'ask-body' }, boldParts(said(LINK_NOTE, { name: person.name, marathon: marathon.name }))),
      picker.node,
      field('Where it counts', scope),
      field(TWITCH_FIX_FIELD, twitch, TWITCH_FIX_HELP),
    ],
    confirmLabel: 'Link them',
    tone: 'warn',
    onConfirm: async () => {
      const body = {
        runner_name: person.name,
        user_id: picker.id,
        everywhere: scope.readValue() === 'every',
      };
      if (twitch.value.trim()) body.twitch_login = twitch.value.trim();
      done = await send(`/api/marathons/${marathon.id}/people`, 'POST', body);
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

async function optMove(marathon, say, entry, runId, out) {
  if (out) {
    const sure = await ask({ title: said(OPT_OUT_TITLE, { name: entry.member_name || entry.name }), body: [OPT_OUT_BODY], confirmLabel: OPT_OUT });
    if (!sure) return;
  }
  shown.focus = runId;
  const path = `/api/marathons/${marathon.id}/people/${encodeURIComponent(entry.user_id)}/opt-out`;
  const done = await run(say, () => send(path, out ? 'POST' : 'DELETE'), (found) => found?.message);
  await after(marathon, done);
}

function optBits(marathon, say, entry, runId) {
  if (shown.archived || !entry || !entry.user_id || entry.opted_out === null || entry.opted_out === undefined) return [];
  if (entry.opted_out) {
    return [
      el('span', { class: 'cell-quiet', text: OPTED_OUT }),
      button(OPT_IN, () => optMove(marathon, say, entry, runId, false), { tone: 'quiet' }),
    ];
  }
  return [button(OPT_OUT, () => optMove(marathon, say, entry, runId, true), { tone: 'quiet' })];
}

function spotlightBits(marathon, say, entry, runId) {
  if (shown.archived || !entry || !entry.login) return [];
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
  if (shown.archived) return entry && entry.member && entry.matched_word ? [el('span', { class: 'cell-quiet', text: entry.matched_word })] : bits;
  if (entry && entry.member && entry.matched_by === 'pairing' && entry.pairing_id) {
    bits.push(el('span', { class: 'cell-quiet', text: entry.matched_word }));
    bits.push(button('Unlink', async () => {
      shown.focus = runId;
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/people/${entry.pairing_id}`, 'DELETE'), (found) => found?.message);
      await after(marathon, done);
    }, { tone: 'quiet' }));
    bits.push(button(TWITCH_FIX_BUTTON, () => fixTwitch(marathon, say, entry, runId), { tone: 'quiet' }));
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
      el('span', { class: 'cell-quiet mx-person-part', text: entry.part_tag || partWords(entry.parts) }),
    ]),
    el('div', { class: 'bar mx-person-moves mx-person-body' }, [
      entry.login
        ? el('a', { class: 'cell-quiet mono', href: `https://twitch.tv/${entry.login}`, rel: 'noreferrer', target: '_blank', text: twitchText(entry) })
        : el('span', { class: 'cell-quiet', text: NO_TWITCH }),
      ...matchBits(marathon, say, entry, entry, null),
      ...spotlightBits(marathon, say, entry, null),
      ...optBits(marathon, say, entry, null),
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
      el('span', { class: 'cell-quiet', text: ` ${(person.user_id && entry && entry.part_tag) || PART_WORDS[person.part] || person.part}` }),
      person.login ? el('span', { class: 'cell-quiet mono', text: ` · ${twitchText(person)}` }) : el('span', { class: 'cell-quiet', text: ` · ${NO_TWITCH}` }),
    ]),
    el('span', { class: 'bar mx-person-moves' }, [
      ...matchBits(marathon, say, entry, person, run.id, { inSlot: true }),
      ...spotlightBits(marathon, say, entry, run.id),
      ...(person.user_id ? optBits(marathon, say, entry, run.id) : []),
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
      run.retimed && run.sheet_at
        ? el('span', { class: 'cell-quiet', text: SHEET_SAID.replace('{time}', slotTime(run.sheet_at, timeZone)) })
        : null,
    ]),
    el('span', { class: 'mx-chips' }, people.map(slotChip)),
    el('span', { class: 'cell-kind' }, [
      badge(run.state_word, STATE_TONE[run.state] || null),
      run.held ? badge(HELD_NOTE, 'warn') : null,
      run.certain ? el('span', { class: 'badge', 'data-tone': 'ok', title: CERTAIN_HELP, text: CERTAIN_NOTE }) : null,
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
  return node;
}

function scheduleBlock(marathon, say, board) {
  const timeZone = board.timezone || undefined;
  const days = daysOf(marathon.run_list, timeZone);
  if (!days.length) return [line(NO_RUNS)];
  const slots = [];
  const folds = days.map((day, at) => {
    const nodes = day.runs.map((one) => {
      const node = slotRow(marathon, say, board, one, timeZone);
      slots.push({ run: one, node, fold: at });
      return node;
    });
    const fold = foldout(dayTitle(day), nodes, { open: day.open || day.runs.some((one) => shown.slots.has(String(one.id))) });
    fold.classList.add('mx-day');
    fold.dataset.open = day.open ? 'true' : 'false';
    return fold;
  });
  const filter = listFilter({
    items: slots,
    value: (one) => one.run,
    text: slotText,
    label: 'Filter the schedule',
    placeholder: FILTER_PLACEHOLDER,
    empty: line(NO_HIT),
    onChange: ({ query, hits }) => {
      folds.forEach((fold, at) => {
        const here = slots.filter((one, index) => one.fold === at && hits[index]).length;
        fold.hidden = Boolean(query) && here === 0;
        fold.open = query ? here > 0 : fold.dataset.open === 'true';
      });
    },
  });
  return [el('div', { class: 'table-tools' }, [filter.search]), filter.none, ...folds];
}

function otherPairings(marathon, say, board) {
  if (shown.archived) return null;
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
    baf.length ? el('div', { class: 'mx-people' }, baf.map((one) => bafLine(marathon, say, one, timeZone))) : line(shown.archived ? NO_BAF_ARCHIVED : NO_BAF),
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

/** Under the ping switch: whether the heads-up mentions the Marathon role, or why it does not. */
function rolePingLine(marathon) {
  const found = marathon.role_ping || {};
  if (!found.line) return null;
  return el('p', { class: 'field-help mx-line mx-role-ping', 'data-reason': found.reason || '' }, [
    badge(found.mentions ? ROLE_PING_ON : ROLE_PING_OFF, found.mentions ? 'ok' : 'warn'),
    el('span', { text: ` ${found.line}` }),
  ]);
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
  const pingNow = marathon.ping_role ? 'on' : 'off';
  const ping = segment(PING_CHOICES, pingNow);
  const highlightNow = marathon.public_highlight ? 'on' : 'off';
  const highlight = segment(PING_CHOICES, highlightNow);
  const announce = switchPicker(marathon.announcements);
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
    if (ping.readValue() !== pingNow) body.ping_role = ping.readValue() === 'on';
    if (highlight.readValue() !== highlightNow) body.public_highlight = highlight.readValue() === 'on';
    if (announce.readValue() !== announce.now) body.announcements = switchWanted(announce.readValue());
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
    linkLine(marathon),
    field(EVENT_SELECT, mode, EVENT_SELECT_SHORT),
    eventState(marathon, say),
    marathon.channel_gone ? notice(CHANNEL_GONE, 'warn') : null,
    field('Airs on', picker, windowWords(marathon)),
    field(PING_FIELD, ping, PING_HELP),
    rolePingLine(marathon),
    field(HIGHLIGHT_FIELD, highlight, HIGHLIGHT_HELP),
    field(ANNOUNCE_FIELD, announce, ANNOUNCE_HELP),
    field(POLL_LABEL, el('span', { class: 'mx-poll' }, [poll, el('span', { text: POLL_UNIT })]), said(POLL_HELP, { minutes: cadence.near ?? '—', far: cadence.far ?? '—' })),
    bar([save]),
  ], { open: shown.settings });
  fold.classList.add('mx-settings');
  fold.addEventListener('toggle', () => {
    shown.settings = fold.open;
  });
  return fold;
}

function spotlightLine(state) {
  return String(state.line || '')
    .split('{until}').join(whenWords(state.until))
    .split('{starts}').join(whenWords(state.starts));
}

/** The marathon's channel row, through the Go-live drawer's own controls. */
function spotlightBlock(marathon, say) {
  const state = marathon.spotlight_state || {};
  const said = el('p', { class: 'mx-spot-state', 'data-state': state.state || '' }, [
    badge(SPOTLIT_WORDS[state.state] || NOT_SPOTLIT, SPOTLIT_WORDS[state.state] ? 'ok' : null),
    el('span', { text: ` ${spotlightLine(state)}` }),
  ]);
  const one = marathon.channel_spotlight;
  if (!one) return [el('p', { class: 'field-help mx-line' }, [el('span', { text: spotlightLine(state) })])];
  const redraw = (done) => after(marathon, done);
  const followNow = marathon.spotlight_mode === 'off' ? 'off' : 'follow';
  const follow = segment(SPOTLIGHT_CHOICES, followNow, {
    onChange: async () => {
      const wanted = follow.readValue();
      if (wanted === followNow) return;
      await redraw(await run(say, () => send(`/api/marathons/${marathon.id}`, 'PATCH', { spotlight_mode: wanted }), (found) => found?.message || SAVED));
    },
  });
  return [
    spotlightCard(one, say, redraw, {
      head: [said, field(SPOTLIGHT_FIELD, follow, SPOTLIGHT_HELP)],
      foot: [
        announcedSaid(one),
        el('div', { class: 'bar' }, announceMoves(one, say, redraw)),
        el('p', { class: 'field-help' }, [el('span', { text: `${SPOTLIGHT_SHARED} ` }), linkAction(OPEN_ON_GOLIVE, GOLIVE_HREF)]),
      ],
    }),
    pingsCard(one, say, redraw),
  ];
}

async function changeLink(marathon) {
  const url = el('input', { class: 'input', type: 'url', value: marathon.schedule_url || '', 'aria-label': SCHEDULE_LINK_FIELD });
  let done = null;
  const sure = await askForm({
    title: said(SCHEDULE_LINK_TITLE, { name: marathon.name }),
    body: [el('p', { class: 'ask-body', text: SCHEDULE_LINK_NOTE }), field(SCHEDULE_LINK_FIELD, url)],
    confirmLabel: 'Change it',
    tone: 'warn',
    onConfirm: async () => {
      done = await send(`/api/marathons/${marathon.id}`, 'PATCH', { schedule_url: url.value.trim() });
      return null;
    },
  });
  if (!sure || !done) return;
  shown.settings = true;
  await after(marathon, { ok: true, found: done });
}

function linkLine(marathon) {
  return el('p', { class: 'field-help mx-line mx-link' }, joined([
    el('span', {}, [
      el('span', { text: SCHEDULE_LINK_NOW }),
      el('a', { class: 'say-nothing-do', href: marathon.schedule_url, text: marathon.schedule_url, rel: 'noreferrer', target: '_blank' }),
    ]),
    textAction(SCHEDULE_LINK_ACTION, () => changeLink(marathon)),
  ]));
}

function pollSaid(marathon, wanted) {
  return wanted === null
    ? `**${marathon.name}** is re-read on the default gap again.`
    : `**${marathon.name}** is re-read every ${wanted} minutes while it is near.`;
}

function postsRow(marathon, say) {
  const posts = postsLine(marathon);
  const where = posts.hasBoard && marathon.board_channel_id;
  const move = marathon.tracked ? textAction(posts.hasBoard ? 'Refresh the board' : 'Post the board', async () => {
    const done = await run(say, () => send(`/api/marathons/${marathon.id}/board`, 'POST', {}), (found) => found?.message);
    await after(marathon, done);
  }) : null;
  return el('p', { class: 'field-help mx-line mx-posts' }, joined([
    el('span', {}, [el('span', { text: posts.board }), where ? el('span', { text: ' ' }) : null, where ? nameNode(marathon.board_channel_id) : null]),
    posts.sent ? el('span', { text: posts.sent }) : null,
    move,
  ]));
}

function trackButtons(marathon, say) {
  return trackMoves(marathon).map((key) => {
    const move = TRACK_MOVES[key];
    return step(marathon, say, move.label, () => send(`/api/marathons/${marathon.id}/${move.path}`, 'POST', move.body), move.tone);
  });
}

function moveBar(marathon, say) {
  return bar([
    ...trackButtons(marathon, say),
    marathon.inbox_message_url ? null : step(marathon, say, POST_NOW, () => send(`/api/marathons/${marathon.id}/inbox`, 'POST', {}), 'quiet'),
    marathon.active ? step(marathon, say, 'Read it now', () => send(`/api/marathons/${marathon.id}/refresh`, 'POST', {}), 'warn') : null,
    marathon.retimed_runs ? step(marathon, say, SHEET_TIMES_ACTION, () => send(`/api/marathons/${marathon.id}/sheet-times`, 'POST', {}), 'quiet') : null,
    step(marathon, say, marathon.active ? 'Pause' : 'Resume', () => send(`/api/marathons/${marathon.id}`, 'PATCH', { active: !marathon.active }), null),
    button('Archive it', async () => {
      const sure = await ask({ title: `Archive ${marathon.name}?`, body: [ARCHIVE_BODY], confirmLabel: 'Archive it' });
      if (!sure) return;
      const done = await run(say, () => send(`/api/marathons/${marathon.id}/archive`, 'POST', {}), (found) => found?.message);
      if (!done.ok) return;
      keepSaying('marathons', say);
      closeDrawer();
      await refresh();
    }, { tone: 'quiet' }),
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
    ...spotlightBlock(marathon, say),
    peopleCard(marathon, board, say),
    await settingsFold(marathon, say),
    postsRow(marathon, say),
    moveBar(marathon, say),
  ];
}

function archivedHeader(marathon, board) {
  const timeZone = (board && board.timezone) || undefined;
  return [
    el('p', { class: 'mx-head' }, joined([
      badge(marathon.phase_word || 'archived', null),
      el('span', { text: datesWords(marathon, timeZone) }),
      marathon.schedule_page
        ? el('a', { class: 'say-nothing-do', href: marathon.schedule_page, text: said(SOURCE_LINK, { source: marathon.source_word }), rel: 'noreferrer', target: '_blank' })
        : el('span', { text: marathon.source_word }),
    ])),
    el('p', { class: 'field-help mx-head-quiet' }, joined([
      el('span', { text: marathon.archived_word }),
      el('span', { text: archivedWho(marathon) }),
      el('span', { text: headerCounts(marathon.run_list) }),
      eventHead(marathon),
    ])),
  ];
}

async function restoreMarathon(marathon, say) {
  const sure = await ask({ title: `Restore ${marathon.name}?`, body: [RESTORE_BODY], confirmLabel: 'Restore it' });
  if (!sure) return;
  const done = await run(say, () => send(`/api/marathons/${marathon.id}/restore`, 'POST', {}), (found) => found?.message);
  if (!done.ok) return;
  await refresh();
  shown.archived = false;
  await openMarathon(marathon.id, marathon.name, (done.found || {}).message || '');
}

async function archivedDrawer(marathon, board, message) {
  const say = notice();
  if (message) say.say(message, 'ok');
  return [
    say,
    ...archivedHeader(marathon, board),
    el('p', { class: 'field-help' }, boldParts(ARCHIVED_NOTE)),
    peopleCard(marathon, board, say),
    bar([button('Restore', () => restoreMarathon(marathon, say), { tone: 'warn' })]),
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
    shown.archived = Boolean(marathon.archived);
    const body = shown.archived
      ? await archivedDrawer(marathon, board, message)
      : await marathonDrawer(marathon, board, message);
    openDrawer(marathon.name, body, { onClose: forgetHash });
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
  const free = (payload.channels || []).filter((one) => one.marathons !== false
    && !(one.feed_sources || []).some((pick) => sourceKind(pick) === sourceKind(feed.source)));
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

function feedSearchInput(feed, say, one) {
  const input = el('input', { class: 'input', type: 'text', value: one.value, placeholder: one.placeholder });
  input.addEventListener('change', () => {
    const wanted = input.value.trim();
    if (wanted !== one.value) feedDrawerStep(feed, say, () => send(`/api/marathons/feeds/${feed.id}`, 'PATCH', { [one.key]: wanted }));
  });
  return field(one.label, input, one.help);
}

function hotfixKey(name) {
  return String(name || '').toLowerCase().split(/\s+/).filter(Boolean).join('-');
}

function hotfixWhy(because) {
  const people = (because || []).filter((one) => one.kind !== 'listed');
  if (!people.length) return (because || []).length ? HOTFIX_TRACKED_LISTED : HOTFIX_NOT_TRACKED;
  return said(HOTFIX_TRACKED_BECAUSE, { who: people.map((one) => said(HOTFIX_PERSON[one.kind], { name: one.name })).join(', ') });
}

function hotfixShowRow(show, blocks, wanted, redraw) {
  const box = el('input', { type: 'checkbox' });
  box.checked = wanted.has(show.key);
  box.addEventListener('change', () => {
    if (box.checked) wanted.set(show.key, show.name);
    else wanted.delete(show.key);
    redraw();
  });
  const chips = blocks.flatMap((block) => (block.days || []).map((day) => el('span', {
    class: 'mx-chip',
    'data-baf': block.because.some((one) => one.kind !== 'listed') ? 'true' : undefined,
    title: said(HOTFIX_CHIP_TITLE, { runs: block.runs, hosts: (block.hosts || []).join(', ') || HOTFIX_NO_HOST }),
    text: day.starts_local || day.date,
  })));
  const hosts = [...new Set(blocks.flatMap((block) => block.hosts || []))];
  const why = blocks.map((block) => hotfixWhy(block.because)).filter((one, at, all) => all.indexOf(one) === at);
  return el('div', { class: 'field-help mx-line' }, [
    el('label', { class: 'checkline' }, [box, el('strong', { text: show.name })]),
    el('span', { class: 'mx-chips' }, chips),
    hosts.length ? el('span', { class: 'cell-quiet', text: ` · ${said(HOTFIX_HOSTED_BY, { hosts: hosts.join(', ') })}` }) : null,
    el('span', { class: 'cell-quiet', text: ` · ${why.join(' · ')}` }),
  ]);
}

function hotfixPicker(feed, say, answer) {
  const blocks = answer.blocks || [];
  const shows = [];
  for (const block of blocks) {
    let show = shows.find((one) => one.key === block.key);
    if (!show) shows.push(show = { key: block.key, name: block.show, blocks: [] });
    show.blocks.push(block);
  }
  const listed = (answer.shows || []).map((name) => [hotfixKey(name), name]);
  const wanted = new Map(listed);
  const before = listed.map(([key]) => key).join(',');
  const save = button(HOTFIX_SAVE, () => {
    const value = [...wanted.values()].join(', ');
    feedDrawerStep(feed, say, async () => {
      const stored = await saveSetting('marathon_hotfix_shows', value);
      const kept = stored && typeof stored === 'object' && 'value' in stored ? stored.value : value;
      return { message: said(HOTFIX_SHOWS_SAVED, { shows: kept }) };
    });
  }, { tone: 'warn' });
  const extra = el('div', {});
  const redraw = () => {
    save.disabled = [...wanted.keys()].join(',') === before;
    const offSheet = [...wanted].filter(([key]) => !shows.some((one) => one.key === key));
    extra.replaceChildren(...offSheet.map(([key, name]) => el('p', { class: 'field-help mx-line' }, [
      el('strong', { text: name }),
      el('span', { class: 'cell-quiet', text: ` · ${HOTFIX_OFF_SHEET} ` }),
      textAction(HOTFIX_REMOVE, () => { wanted.delete(key); redraw(); }),
    ])));
  };
  const typed = el('input', { class: 'input', type: 'text', placeholder: HOTFIX_ADD_PLACEHOLDER });
  const addTyped = () => {
    const name = typed.value.trim().replace(/\s+/g, ' ');
    if (!name) return;
    const key = hotfixKey(name);
    const onSheet = shows.find((one) => one.key === key);
    wanted.set(key, onSheet ? onSheet.name : name);
    typed.value = '';
    const box = rows.find((one) => one.show.key === key);
    if (box) box.node.querySelector('input[type=checkbox]').checked = true;
    redraw();
  };
  typed.addEventListener('keydown', (event) => { if (event.key === 'Enter') { event.preventDefault(); addTyped(); } });
  const rows = shows.map((show) => ({ show, node: hotfixShowRow(show, show.blocks, wanted, redraw) }));
  const filter = rows.length > HOTFIX_SEARCH_FROM ? listFilter({
    items: rows,
    value: (one) => one.show,
    text: (show) => [show.name, ...show.blocks.flatMap((block) => [...(block.hosts || []), ...block.because.map((one) => one.name || '')])].join(' '),
    label: HOTFIX_SEARCH_LABEL,
    placeholder: HOTFIX_SEARCH_PLACEHOLDER,
    empty: line(HOTFIX_NO_HIT),
  }) : null;
  redraw();
  return [
    answer.stale ? line(said(HOTFIX_STALE, { why: answer.trouble || '', when: relative(answer.read_at) }), 'warn') : null,
    line(answer.track_people ? HOTFIX_PEOPLE_ON : HOTFIX_PEOPLE_OFF),
    filter ? el('div', { class: 'table-tools' }, [filter.search]) : null,
    filter ? filter.none : null,
    ...rows.map((one) => one.node),
    rows.length ? null : line(HOTFIX_EMPTY_SHEET),
    extra,
    el('div', { class: 'bar' }, [typed, button(HOTFIX_ADD, addTyped, { tone: 'quiet' })]),
    bar([save]),
  ];
}

function hotfixFields(feed, say) {
  if (feed.source !== 'gdq_hotfix') return [];
  const box = el('div', { class: 'mx-hotfix-picker' }, [line(HOTFIX_LOADING)]);
  api(`/api/marathons/feeds/${feed.id}/hotfix-shows`)
    .then((answer) => box.replaceChildren(...hotfixPicker(feed, say, answer).filter(Boolean)))
    .catch((error) => {
      const sentence = sentenceFor(error);
      box.replaceChildren(notice(sentence.text, sentence.tone));
    });
  return [
    field(HOTFIX_SHOWS_FIELD, box, HOTFIX_SHOWS_HELP),
    feed.sheet_url ? el('p', { class: 'field-help mx-line' }, [
      el('span', { text: HOTFIX_SHEET_LINE }),
      el('a', { href: feed.sheet_url, text: 'the sheet ↗', rel: 'noreferrer', target: '_blank' }),
    ]) : null,
  ];
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
  const auto = segment(AUTO_CHOICES, feed.auto_track ? 'on' : 'off', {
    onChange: () => {
      const wanted = auto.readValue() === 'on';
      if (wanted !== Boolean(feed.auto_track)) feedDrawerStep(feed, say, () => send(base, 'PATCH', { auto_track: wanted }));
    },
  });
  const moves = [];
  if ((feed.dismissed || []).length || feed.seen_count) {
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
    field(AUTO_FIELD, auto, AUTO_HELP),
    ...feedSearchFields(feed).map((one) => feedSearchInput(feed, say, one)),
    ...hotfixFields(feed, say),
    ...(feed.suggestions || []).map((one) => suggestionCard(feed, one, say, { inDrawer: true })),
    feed.seen_count ? el('p', { class: 'field-help mx-line' }, boldParts(said({ horaro_events: FEED_SEEN_NOTE_HORARO, ladyarcaders: FEED_PROBE_NOTE }[feed.source] || FEED_SEEN_NOTE, { count: feed.seen_count }))) : null,
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
  const free = (payload.channels || []).filter((one) => one.marathons !== false);
  const channel = el('select', { class: 'input' }, free.map((one) => el('option', { value: String(one.id), text: `${one.name} · twitch.tv/${one.login}` })));
  const source = el('select', { class: 'input' }, (payload.sources || []).map((one) => el('option', { value: one.value, text: one.label })));
  const slug = el('input', { class: 'input', type: 'text', placeholder: 'esa' });
  const name = el('input', { class: 'input', type: 'text', placeholder: 'the channel’s name' });
  const action = segment(ACTION_CHOICES, payload.action_default || 'add');
  const pickHelp = el('p', { class: 'field-help' });
  const slugField = field('horaro.net event slug', slug, 'The part after horaro.net/.');
  const shownPick = () => {
    pickHelp.textContent = PICK_HELP[source.value] || '';
    slugField.style.display = source.value === 'horaro' ? '' : 'none';
  };
  const guessPick = () => {
    const picked = free.find((one) => String(one.id) === channel.value);
    const guess = picked ? PICK_GUESS[String(picked.login).toLowerCase()] : null;
    if (guess && [...source.options].some((one) => one.value === guess)) source.value = guess;
    shownPick();
  };
  channel.addEventListener('change', guessPick);
  source.addEventListener('change', shownPick);
  guessPick();
  let made = null;
  const sure = await askForm({
    title: 'Add a feed',
    body: [
      el('p', { class: 'ask-body' }, boldParts(free.length ? FEED_ADD_NOTE : FEED_NO_CHANNELS)),
      field('Channel', channel),
      field('Read from', source),
      pickHelp,
      slugField,
      field('Name', name, 'Blank uses the channel’s name.'),
      field('New events', action),
    ],
    confirmLabel: 'Add the feed',
    tone: 'warn',
    onConfirm: async () => {
      made = await send('/api/marathons/feeds', 'POST', {
        spotlight_id: channel.value || null,
        source: source.value,
        slug: source.value === 'horaro' ? slug.value.trim() || null : null,
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



function archiveLine(row) {
  return el('p', { class: 'field-help mx-line mx-archived' }, joined([
    textAction(row.name, () => openMarathon(row.id, row.name)),
    el('span', { class: 'cell-quiet', text: sourceCell(row) }),
    el('span', { text: datesWords(row) }),
    el('span', { text: archiveCounts(row) }),
    el('span', { class: 'cell-quiet', text: archivedWhen(row) }),
  ]));
}

function archiveFold(archive) {
  const days = cadence.archiveDays ?? 7;
  if (!archive || archive.error) {
    return foldout(archiveTitle(0), [notice(ARCHIVE_FAILED, 'warn')]);
  }
  const rows = archive.marathons || [];
  const list = el('div', { class: 'mx-archive' }, rows.map(archiveLine));
  const children = [line(said(ARCHIVE_NOTE, { days })), rows.length ? list : line(said(ARCHIVE_EMPTY, { days }))];
  let loaded = rows.length;
  if ((archive.total || 0) > loaded) {
    const more = textAction(said(ARCHIVE_MORE, { count: Math.min(archive.limit || 50, archive.total - loaded) }), async () => {
      const next = await api(`/api/marathons/archive?limit=${archive.limit || 50}&offset=${loaded}`).catch(() => null);
      if (!next) return;
      list.append(...(next.marathons || []).map(archiveLine));
      loaded += (next.marathons || []).length;
      if (loaded >= (next.total || 0)) more.remove();
      else more.textContent = said(ARCHIVE_MORE, { count: Math.min(next.limit || 50, next.total - loaded) });
    });
    children.push(more);
  }
  const fold = foldout(archiveTitle(archive.total), children);
  fold.classList.add('mx-archive-fold');
  return fold;
}

function listSection(payload, feeds, say, archive) {
  const rows = payload.marathons || [];
  const list = section('Marathons', LIST_NOTE, { count: rows.length, id: 'marathons', open: true });
  const add = button('Add a marathon', () => addMarathon(), { tone: 'warn' });
  const sources = button(SOURCES_BUTTON, () => openSources(), { tone: 'quiet' });
  const grid = table([
    { label: 'Marathon', cell: (row) => textAction(row.name, () => openMarathon(row.id, row.name)) },
    { label: 'Source', cell: (row) => el('span', { class: 'cell-quiet', text: sourceCell(row) }) },
    { label: 'Dates', cell: (row) => datesOf(row) },
    { label: 'State', cell: (row) => badge(row.phase_word, PHASE_TONE[row.phase] || null) },
    { label: 'Tracked', cell: (row) => {
      const state = trackedCell(row);
      return badge(state.text, state.tone);
    } },
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
    archiveFold(archive),
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
    archiveDays: held('marathon_archive_after_days'),
    modeSpec: specs.find((one) => one.key === 'marathon_mode') || null,
  };
}

/** The Events page's Marathons section: the list, its drawer and the sources that feed it. */
export async function marathonsSection({ reload, openEvent }) {
  refresh = reload;
  showEvent = openEvent;
  const [payload, feeds, found, archive] = await Promise.all([
    api('/api/marathons'),
    api('/api/marathons/feeds').catch((error) => ({ error: sentenceFor(error) })),
    readCadence(),
    api('/api/marathons/archive?limit=50&offset=0').catch((error) => ({ error: sentenceFor(error) })),
  ]);
  cadence = found;
  eventModeDefault = payload.event_mode_default || 'none';
  eventModes = Array.isArray(payload.event_modes) ? payload.event_modes : [];
  const say = sayAgain('marathons', notice());
  const node = listSection(payload, feeds, say, archive);
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
