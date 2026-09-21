import { start } from './app.js';
import { importantSwitch, logsTable } from './logs.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';
import {
  ago,
  badge,
  bar,
  button,
  channelLabel,
  el,
  field,
  fillTemplate,
  icon,
  modeChip,
  nameNode,
  notice,
  openDrawer,
  sayNothing,
  searchField,
  section,
  segment,
  textAction,
  untilWhen,
} from './ui.js';

const minutesAgo = (m) => new Date(Date.now() - m * 60000).toISOString();
const daysAhead = (d) => new Date(Date.now() + d * 86400000).toISOString();

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null, position: 0 },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null, position: 1 },
  { id: '800000000000000003', name: 'blackbloc-logs', type: 'text', category_id: null, position: 2 },
  { id: '800000000000000004', name: 'bot-log', type: 'text', category_id: null, position: 3 },
  { id: '800000000000000005', name: 'staff-room', type: 'text', category_id: null, position: 4 },
  { id: '800000000000000006', name: 'announcements', type: 'text', category_id: null, position: 5 },
  { id: '800000000000000007', name: 'free-nitro-here', type: 'text', category_id: null, position: 6 },
  { id: '800000000000000008', name: 'Events', type: 'category', category_id: null, position: 7 },
  { id: '800000000000000009', name: 'Join to create', type: 'voice', category_id: null, position: 8 },
  { id: '800000000000000010', name: "casey's room", type: 'voice', category_id: null, position: 9 },
  { id: '800000000000000011', name: 'modmail', type: 'category', category_id: null, position: 10 },
  { id: '800000000000000012', name: 'modmail-log', type: 'text', category_id: '800000000000000011', position: 11 },
];

const ROLES = [
  { id: '900000000000000001', name: 'Aunties / Uncles' },
  { id: '900000000000000002', name: 'Leads' },
  { id: '900000000000000003', name: 'Live now' },
  { id: '900000000000000004', name: 'Birthday' },
  { id: '900000000000000005', name: 'Members' },
  { id: '900000000000000007', name: 'Events' },
  { id: '900000000000000008', name: 'Casey pings' },
];

const POLLS = [
  { id: 3, creator_id: '700000000000000004', creator_name: 'Moth', question: 'Best day for the cookout?', kind: 'single', surface: 'native', status: 'open', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', opens_at: minutesAgo(120), closes_at: minutesAgo(-1320), closed_at: null, archived_at: null, total_votes: null, deny_reason: null, created_at: minutesAgo(125), votes_dropped: 0, options: [{ position: 0, label: 'Saturday', votes: 22 }, { position: 1, label: 'Sunday', votes: 13 }, { position: 2, label: 'Friday', votes: 6 }] },
  { id: 2, creator_id: '700000000000000002', creator_name: 'Casey', question: 'Movie night or game night?', kind: 'single', surface: 'native', status: 'pending_review', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 48, channel_id: '800000000000000003', opens_at: null, closes_at: null, closed_at: null, archived_at: null, total_votes: null, deny_reason: null, created_at: minutesAgo(40), votes_dropped: 0, options: [{ position: 0, label: 'Movie night', votes: 0 }, { position: 1, label: 'Game night', votes: 0 }] },
  { id: 1, creator_id: '700000000000000001', creator_name: 'Nick', question: 'Keep the Thursday raid slot?', kind: 'yesno', surface: 'native', status: 'closed', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', opens_at: minutesAgo(4000), closes_at: minutesAgo(2560), closed_at: minutesAgo(2560), archived_at: null, total_votes: 18, deny_reason: null, created_at: minutesAgo(4010), votes_dropped: 0, winner_position: 0, options: [{ position: 0, label: 'Yes', votes: 14 }, { position: 1, label: 'No', votes: 4 }] },
  { id: 9, creator_id: '700000000000000002', creator_name: 'Casey', question: 'How was the stream?', kind: 'rating', surface: 'panel', status: 'open', results: 'close', multi: false, anonymous: true, auto_thread: false, hours: 12, channel_id: '800000000000000003', opens_at: minutesAgo(30), closes_at: minutesAgo(-690), closed_at: null, archived_at: null, total_votes: null, deny_reason: null, created_at: minutesAgo(35), votes_dropped: 0, options: [{ position: 0, label: '1', votes: 0 }, { position: 1, label: '2', votes: 1 }, { position: 2, label: '3', votes: 2 }, { position: 3, label: '4', votes: 5 }, { position: 4, label: '5', votes: 9 }] },
  { id: 8, creator_id: '700000000000000004', creator_name: 'Moth', question: 'Which evenings can you make it?', kind: 'date', surface: 'panel', status: 'open', results: 'live', multi: true, anonymous: false, auto_thread: true, hours: 72, channel_id: '800000000000000003', ping_role_id: '900000000000000005', opens_at: minutesAgo(200), closes_at: minutesAgo(-4120), closed_at: null, archived_at: null, total_votes: null, deny_reason: null, created_at: minutesAgo(205), votes_dropped: 0, options: [{ position: 0, label: 'Fri 04 Sep · 7 pm', votes: 4 }, { position: 1, label: 'Sat 05 Sep · 7 pm', votes: 7 }, { position: 2, label: 'Sun 06 Sep · 7 pm', votes: 3 }] },
  { id: 7, creator_id: '700000000000000003', creator_name: 'Rivet', question: 'Rename #general?', kind: 'yesno', surface: 'native', status: 'denied', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', opens_at: null, closes_at: null, closed_at: minutesAgo(3000), archived_at: null, total_votes: null, deny_reason: 'We settled this in the Leads channel last month.', created_at: minutesAgo(3100), votes_dropped: 0, options: [{ position: 0, label: 'Yes', votes: 0 }, { position: 1, label: 'No', votes: 0 }] },
  { id: 6, creator_id: '700000000000000005', creator_name: 'spamlord99', question: 'Double XP weekend?', kind: 'single', surface: 'native', status: 'cancelled', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', opens_at: minutesAgo(5000), closes_at: minutesAgo(4000), closed_at: minutesAgo(4600), archived_at: null, total_votes: null, deny_reason: null, created_at: minutesAgo(5010), votes_dropped: 0, options: [{ position: 0, label: 'Yes please', votes: 2 }, { position: 1, label: 'No thanks', votes: 1 }] },
  { id: 5, creator_id: '700000000000000001', creator_name: 'Nick', question: 'Old cookout, which park?', kind: 'single', surface: 'native', status: 'archived', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', opens_at: minutesAgo(600000), closes_at: minutesAgo(598000), closed_at: minutesAgo(598000), archived_at: minutesAgo(1000), total_votes: 31, deny_reason: null, created_at: minutesAgo(600100), votes_dropped: 31, winner_position: 0, options: [{ position: 0, label: 'Encanto', votes: 19 }, { position: 1, label: 'Steele Indian School', votes: 12 }] },
];

const RECURRENCES = [
  { id: 4, creator_id: '700000000000000001', creator_name: 'Nick', question: 'Are we running tonight?', kind: 'yesno', surface: 'native', hours: 6, anonymous: false, results: 'live', channel_id: '800000000000000003', cadence: 'daily', cadence_said: 'every day at 19:00 America/Phoenix', at: '19:00', tz: 'America/Phoenix', next_at: daysAhead(1), paused: false, created_at: minutesAgo(8000), options: [{ position: 0, label: 'Yes', votes: 0 }, { position: 1, label: 'No', votes: 0 }] },
  { id: 5, creator_id: '700000000000000001', creator_name: 'Nick', question: 'Best day for next week?', kind: 'checkbox', surface: 'native', hours: 48, anonymous: false, results: 'live', channel_id: '800000000000000003', cadence: 'weekly:mon', cadence_said: 'every Monday at 09:00 America/Phoenix', at: '09:00', tz: 'America/Phoenix', next_at: null, paused: true, created_at: minutesAgo(9000), options: [{ position: 0, label: 'Friday', votes: 0 }, { position: 1, label: 'Saturday', votes: 0 }] },
];

const SETTING_SPECS = [
  { key: 'poll_who_can_create', type: 'enum', value: 'staff', choices: ['staff', 'everyone'], label: 'Who can create', help: 'who may run /poll create: staff, or everyone' },
  { key: 'poll_review_mode', type: 'enum', value: 'off', choices: ['off', 'on'], label: 'Review mode', help: 'off posts a poll straight away; on holds it for a staff Approve or Deny first' },
  { key: 'poll_default_hours', type: 'int', value: 24, label: 'Default hours', help: 'hours a poll stays open when nobody says otherwise, 1 to 768 (32 days)' },
  { key: 'poll_channel_id', type: 'channel', value: null, label: 'Poll channel', help: 'where a poll made from the dashboard goes' },
  { key: 'poll_ping_role_id', type: 'role', value: null, label: 'Ping role', help: 'role mentioned when a poll opens; blank pings nobody' },
  { key: 'poll_reminder_minutes', type: 'int', value: 60, label: 'Reminder minutes', help: 'minutes before a poll closes that Black Bloc posts a last call, 0 to say nothing' },
  { key: 'poll_auto_thread', type: 'bool', value: false, label: 'Auto thread', help: 'true to open a discussion thread under every poll' },
  { key: 'poll_pin', type: 'bool', value: true, label: 'Pin', help: "true pins a poll's message while it is open and unpins it when it closes" },
  { key: 'poll_shadow_note', type: 'text', value: 'Posted here because polls are in **shadow** — it would have gone to {channel}.', label: 'Shadow note', help: 'the line above a poll posted in shadow; {channel} is where it would have gone' },
  { key: 'poll_archive_days', type: 'int', value: 365, label: 'Archive days', help: 'days a closed poll stays on the list before it moves to the archive' },
  { key: 'poll_archive_drop_votes', type: 'bool', value: true, label: 'Archive drops votes', help: 'true to forget who voted when a poll is archived; the totals are kept either way' },
  { key: 'poll_date_labels', type: 'enum', value: 'plain', choices: ['plain', 'timestamp'], label: 'Date labels', help: "how a date poll writes its slots: plain (Sat 30 Aug · 7 pm, in the server's zone) or timestamp (each reader sees their own clock, if Discord renders one in an answer)" },
];

const SHADOW_NOTE = 'Posted here because polls are in **shadow** — it would have gone to {channel}.';

const NATIVE_CAP = 10;
const PANEL_CAP = 25;

const KINDS = [
  ['single', 'Single choice'],
  ['checkbox', 'Checkbox — pick several'],
  ['yesno', 'Yes / no'],
  ['rating', 'Rating, 1-5'],
  ['date', 'Date / availability'],
];
const GENERATED = { yesno: ['Yes', 'No'], rating: ['1', '2', '3', '4', '5'] };

const NO_REPEAT = 'no';
const CADENCES = [
  [NO_REPEAT, 'Doesn’t repeat'],
  ['daily', 'Every day'],
  ['weekly', 'Every week'],
  ['monthly', 'Every month'],
];
const WEEKDAYS = [
  ['mon', 'Monday'],
  ['tue', 'Tuesday'],
  ['wed', 'Wednesday'],
  ['thu', 'Thursday'],
  ['fri', 'Friday'],
  ['sat', 'Saturday'],
  ['sun', 'Sunday'],
];

const SWITCH_HELP = 'Off hides Create on the /poll panel and refuses new polls. Shadow posts every ' +
  'poll for real, into the log channel, with a line saying it would have gone elsewhere. Nothing ' +
  'already running is closed or moved, and every result Black Bloc has kept stays on this page.';

const WORK_NOTE = 'Every poll that is still going somewhere: waiting on a Lead, taking votes, or ' +
  'due to open again on its own. Open one to see how it is going and what you can do with it.';
const FINISHED_NOTE = 'How every finished poll went. The export is a CSV of the totals, plus ' +
  'one row per voter when the poll kept them. Polls older than poll_archive_days say archived.';
const SETTINGS_NOTE = 'Who may start a poll, how long one runs, where a poll made here goes, ' +
  'and when a finished one moves to the archive.';
const LOGS_NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in ' +
  'Discord. Important means it acted on a member or failed.';
const CREATE_NOTE = 'The same rules as the /poll panel in Discord — Black Bloc picks the surface ' +
  'from what you ask for and tells you which one it picked.';

const OPEN_NOTE = 'Ending one publishes the result; cancelling stops it without publishing anything.';
const REVIEW_NOTE = 'Approving posts it straight away and DMs the person who asked; denying DMs ' +
  'them the reason you type.';
const RECUR_NOTE = 'Pausing leaves everything it has already opened alone; so does deleting it.';

const NO_WORK = 'Nothing is taking votes right now. Start one with Create a poll, up beside the heading.';
const NO_MATCH = 'Nothing here matches what you typed.';
const NO_FINISHED = 'No poll has finished yet.';

const NEED_A_QUESTION = 'Write the question first — it is the heading everybody votes under.';
const NEED_OPTIONS = 'A poll needs at least two options.';
const NEED_A_START = 'A date poll needs a start date, like 2026-09-05.';
const NEED_A_TIME = 'A repeating poll needs the time of day it opens, on the 24-hour clock — 19:00.';
const NEED_A_WEEKDAY = 'Pick the day of the week it runs on.';
const NEED_A_MONTH_DAY = 'A monthly poll runs on a day from 1 to 28 — every month has those.';
const REPEAT_HELP = 'A repeating poll is a template rather than a poll: nothing is posted when ' +
  'you save it, and Black Bloc opens a fresh copy each time it comes round.';
const TZ_HELP = 'Blank uses the server’s own zone. Write it the tzdata way — America/Phoenix.';
const REPEATED = 'Saves “{question}” as a template that opens in {where} {cadence}, each one ' +
  'open for {hours} hour(s). Nothing is posted until it first comes round.';
const CREATE_LABEL = 'Create the poll';
const REPEAT_LABEL = 'Save the repeating poll';

const STATUS_TONE = {
  open: 'ok',
  pending_review: 'warn',
  closed: null,
  cancelled: null,
  denied: null,
  archived: null,
};

const FILTERS = [
  ['all', 'Everything'],
  ['pending_review', 'Waiting on a Lead'],
  ['open', 'Taking votes'],
  ['repeating', 'Repeating'],
];

const COLUMNS = [
  ['#', 'The poll’s own number.'],
  ['Status', 'Where the poll has got to, and how it is being posted.'],
  ['Kind', 'Single choice, multiple choice, or a date poll.'],
  ['Question', null],
  ['Where', null],
  ['Closes', 'When voting stops. Hover for the exact time.'],
  ['', null],
];

const LOG_ROWS = [];

const state = { mode: 'on', filter: 'all', query: '', important: true };

let refresh = () => {};

function channelName(id) {
  const found = CHANNELS.find((one) => String(one.id) === String(id));
  return found ? `#${found.name}` : null;
}

function roleName(id) {
  const found = ROLES.find((one) => String(one.id) === String(id));
  return found ? `@${found.name}` : null;
}

function said(row) {
  return String(row.status || '').replace(/_/g, ' ');
}

function totalOf(row) {
  if (typeof row.total_votes === 'number') return row.total_votes;
  return (row.options || []).reduce((sum, option) => sum + (option.votes || 0), 0);
}

function resultBars(row) {
  const options = (row.options || []).slice()
    .sort((a, b) => (b.votes || 0) - (a.votes || 0) || a.position - b.position);
  if (options.length === 0) return sayNothing('This poll has no options stored.');
  const total = totalOf(row) || 0;
  return el('div', { class: 'pollbars' }, options.map((option) => {
    const share = total > 0 ? Math.round((100 * (option.votes || 0)) / total) : 0;
    return el('div', {
      class: 'pollbar-row',
      'data-winner': row.winner_position === option.position ? 'true' : undefined,
    }, [
      el('span', { class: 'pollbar-name', text: option.label, title: option.label }),
      el('span', { class: 'pollbar-track' }, [
        el('span', { class: 'pollbar-fill', style: `width: ${share}%` }),
      ]),
      el('span', { class: 'pollbar-count', text: `${option.votes || 0} · ${share}%` }),
    ]);
  }));
}

function closesCell(row) {
  if (row.repeating) {
    if (row.paused) return badge('paused', 'warn');
    if (!row.next_at) return el('span', { class: 'cell-quiet', text: 'not scheduled' });
    const next = untilWhen(row.next_at);
    return el('span', { class: 'cell-quiet', title: next.title, text: next.text });
  }
  if (!row.closes_at) return el('span', { class: 'cell-quiet', text: 'not posted yet' });
  const until = untilWhen(row.closes_at);
  return el('span', {
    class: 'cell-quiet',
    title: until.title,
    text: until.days < 0 ? 'overdue' : `closes ${until.text}`,
  });
}

function surfaceChip(row) {
  if (row.surface !== 'panel') return badge('native');
  const why = row.anonymous
    ? 'it is anonymous'
    : row.results === 'close'
      ? 'its bars stay hidden until it closes'
      : 'it has more options than a Discord poll carries';
  const chip = badge('panel', 'warn');
  chip.setAttribute('title', `Buttons rather than a Discord poll, because ${why}.`);
  return chip;
}

/** Where the mode section used to be: one chip on the row, and only when it changes where a poll lands. */
const GOING_SOMEWHERE = ['open', 'pending_review', 'repeating'];

function whereChip(row) {
  if (state.mode === 'on') return null;
  if (!row.repeating && !GOING_SOMEWHERE.includes(row.status)) return null;
  const chip = modeChip(state.mode);
  if (state.mode === 'shadow') {
    const filled = fillTemplate(SHADOW_NOTE, { channel: channelName(row.channel_id) || 'that channel' });
    chip.setAttribute('title', String(filled || SHADOW_NOTE).replace(/\*\*/g, ''));
  } else {
    chip.setAttribute('title', SWITCH_HELP);
  }
  return chip;
}

function statusKids(row) {
  if (row.repeating) {
    return [
      badge('repeating', row.paused ? null : 'ok'),
      row.paused ? badge('paused', 'warn') : null,
      whereChip(row),
    ].filter(Boolean);
  }
  return [badge(said(row), STATUS_TONE[row.status] ?? null), whereChip(row)].filter(Boolean);
}

const watchers = [];

/** The mode chip is repainted where it stands, so flipping the switch never rebuilds the list. */
function statusCell(row) {
  const node = el('span', { class: 'cell-kind' }, statusKids(row));
  watchers.push(() => node.replaceChildren(...statusKids(row)));
  return node;
}

const MOVES = {
  open: [
    {
      label: 'End now',
      tone: 'warn',
      say: (row) => `POST /api/polls/${row.id}/end — close the vote at Discord and post the ` +
        'result under it. This cannot be undone',
    },
    {
      label: 'Cancel',
      tone: 'danger',
      say: (row) => `POST /api/polls/${row.id}/cancel — stop the vote with no result published. ` +
        'Nobody is told',
    },
  ],
  pending_review: [
    {
      label: 'Approve',
      tone: 'warn',
      say: (row) => `POST /api/polls/requests/${row.id}/approve — post it straight away and DM ` +
        `${row.creator_name} that it is up`,
    },
    {
      label: 'Deny',
      tone: 'danger',
      say: (row) => `POST /api/polls/requests/${row.id}/deny — DM ${row.creator_name} exactly ` +
        'what you type, and never post the poll',
    },
  ],
  repeating: [
    {
      label: 'Pause',
      tone: 'quiet',
      only: (row) => !row.paused,
      say: (row) => `POST /api/polls/recurrences/${row.id}/pause — stop it opening again. Polls ` +
        'it has already opened are untouched',
    },
    {
      label: 'Start it',
      tone: null,
      only: (row) => row.paused,
      say: (row) => `POST /api/polls/recurrences/${row.id}/pause — set it running again, from ` +
        'the next time it comes round',
    },
    {
      label: 'Delete',
      tone: 'danger',
      say: (row) => `DELETE /api/polls/recurrences/${row.id} — it never opens again. Polls it ` +
        'has already opened are untouched',
    },
  ],
  closed: [
    {
      label: 'Export CSV',
      tone: 'quiet',
      say: (row) => `GET /api/polls/${row.id}/export.csv — download the totals, plus one row ` +
        'per voter when the poll kept them',
    },
  ],
};

function movesFor(row) {
  if (row.repeating) return MOVES.repeating;
  return MOVES[row.status] || MOVES.closed;
}

function moveNote(row) {
  if (row.repeating) return RECUR_NOTE;
  if (row.status === 'pending_review') return REVIEW_NOTE;
  if (row.status === 'open') return OPEN_NOTE;
  return null;
}

function detail(row) {
  const asked = ago(row.created_at);
  const parts = [`${row.creator_name} asked ${asked.text}`, row.kind, `${(row.options || []).length} option(s)`];
  if (row.repeating) parts.push(row.cadence_said, `open for ${row.hours}h`);
  else parts.push(`open for ${row.hours}h`, `${totalOf(row)} vote(s)`);
  if (row.ping_role_id) parts.push(`pings ${roleName(row.ping_role_id)}`);
  const say = notice();
  const buttons = movesFor(row)
    .filter((move) => !move.only || move.only(row))
    .map((move) => button(move.label, () => wouldDo(say, move.say(row)), { tone: move.tone, small: false }));
  const note = moveNote(row);
  return [
    el('div', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: row.question }),
      el('span', { class: 'rowlist-note', title: asked.title, text: parts.filter(Boolean).join(' · ') }),
    ]),
    bar([
      row.repeating ? badge('repeating', row.paused ? null : 'ok') : badge(said(row), STATUS_TONE[row.status] ?? null),
      surfaceChip(row),
      whereChip(row),
      el('span', {}, ['in ', nameNode(row.channel_id, channelName(row.channel_id))]),
    ].filter(Boolean)),
    row.deny_reason ? el('p', { class: 'section-note', text: `Why not: ${row.deny_reason}` }) : null,
    row.votes_dropped ? el('p', { class: 'section-note', text: `${row.votes_dropped} per-voter row(s) were dropped when this was archived. The totals are kept.` }) : null,
    row.status === 'pending_review' || row.repeating
      ? el('ol', { class: 'plain-list' }, (row.options || []).map((option) => el('li', { text: option.label })))
      : resultBars(row),
    note ? el('p', { class: 'section-note', text: note }) : null,
    bar(buttons),
    say,
  ].filter(Boolean);
}

function gridRow(row) {
  const searchable = `${row.id} ${row.question} ${row.kind} ${row.creator_name} ${row.status || ''} ${row.repeating ? 'repeating' : ''}`;
  return el('button', {
    class: 'grid-row',
    type: 'button',
    'data-search': searchable.toLowerCase(),
    'data-filter': row.repeating ? 'repeating' : row.status,
    on: { click: () => openDrawer(row.question, detail(row)) },
  }, [
    el('span', { class: 'cell-id', text: `#${row.id}` }),
    statusCell(row),
    el('span', { class: 'cell-kind' }, [badge(row.kind), surfaceChip(row)]),
    el('span', { class: 'cell-reason', text: row.question, title: row.question }),
    el('span', { class: 'cell-quiet' }, [nameNode(row.channel_id, channelName(row.channel_id))]),
    closesCell(row),
    icon('chevronRight', 16),
  ]);
}

function gridHead() {
  return el('div', { class: 'grid-row head' }, COLUMNS.map(([label, help]) => el('span', {
    title: help || undefined,
  }, [
    el('span', { text: label }),
    help ? el('span', { class: 'th-mark', 'aria-hidden': 'true', text: 'ⓘ' }) : null,
  ])));
}

function grid(rows, { empty, emptyAction = null, noun = 'poll' }) {
  if (rows.length === 0) return { node: sayNothing(empty, emptyAction), paint: () => {} };
  const lines = rows.map(gridRow);
  const foot = el('div', { class: 'grid-foot' });
  const none = sayNothing(NO_MATCH, textAction('Clear the search', () => {
    state.query = '';
    refresh();
  }));
  none.hidden = true;
  const body = el('div', { class: 'grid-table' }, [gridHead(), ...lines, foot]);
  const paint = (filter) => {
    let shown = 0;
    lines.forEach((line, at) => {
      const kindHit = !filter || filter === 'all' || line.getAttribute('data-filter') === filter;
      const textHit = state.query === '' || (line.getAttribute('data-search') || '').includes(state.query);
      const hit = kindHit && textHit;
      line.hidden = !hit;
      if (hit) shown += 1;
    });
    foot.textContent = shown === rows.length
      ? `Showing all ${rows.length} ${noun}${rows.length === 1 ? '' : 's'}`
      : `Showing ${shown} of the ${rows.length} ${noun}${rows.length === 1 ? '' : 's'} on this page`;
    none.hidden = shown > 0;
    body.hidden = shown === 0;
  };
  return { node: el('div', {}, [el('div', { class: 'table-scroll' }, [body]), none]), paint };
}

function modeControl(onFlip) {
  const say = notice();
  const node = segment(
    [{ value: 'on', label: 'on' }, { value: 'shadow', label: 'shadow' }, { value: 'off', label: 'off' }],
    state.mode,
    {
      onChange: () => {
        const wanted = node.readValue();
        state.mode = wanted;
        onFlip();
        wouldDo(say, `PUT /api/settings/poll_mode — store ${wanted}. The chips on the rows show ` +
          'what that does to where a poll lands');
      },
    },
  );
  node.setAttribute('aria-label', 'Polls mode');
  return { node, say };
}

function workSection() {
  const rows = POLLS
    .filter((row) => row.status === 'open' || row.status === 'pending_review')
    .map((row) => ({ ...row, repeating: false }))
    .concat(RECURRENCES.map((row) => ({ ...row, repeating: true, status: 'repeating' })));

  const waiting = rows.filter((row) => row.status === 'pending_review').length;
  const one = section('Polls', WORK_NOTE, { count: rows.length, id: 'preview-polls', open: true });
  const made = grid(rows, {
    empty: NO_WORK,
    emptyAction: textAction('Create a poll', () => openDrawer('Create a poll', [createForm()])),
  });

  const chips = FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key,
    'aria-pressed': state.filter === key ? 'true' : 'false',
    text: label,
    on: {
      click: (event) => {
        state.filter = key;
        for (const chip of event.currentTarget.parentElement.children) {
          chip.setAttribute('aria-pressed', chip.getAttribute('data-kind') === key ? 'true' : 'false');
        }
        made.paint(state.filter);
      },
    },
  }));

  const search = searchField({
    label: 'Search polls',
    placeholder: 'Search the question, who asked, or the kind…',
    value: state.query,
    onQuery: (query) => {
      state.query = query;
      made.paint(state.filter);
    },
  });

  const mode = modeControl(() => {
    for (const paint of watchers) paint();
  });
  const tools = el('div', { class: 'card-head' }, [
    search,
    el('div', { class: 'chipbar' }, chips),
    el('span', { class: 'topbar-gap' }),
    el('span', { class: 'table-count', text: `${waiting} waiting on a Lead` }),
  ]);

  one.body.append(
    previewWas('Replaces four sections — Polls (the mode switch on its own), Pending review, ' +
      'Open polls and Repeating. One row per poll, the mode as a chip on the row, and what you ' +
      'can do with one in the drawer it opens.'),
    el('div', { class: 'card' }, [
      tools,
      el('div', { class: 'card-body' }, [
        field('Polls on this server', mode.node, SWITCH_HELP),
        mode.say,
        made.node,
      ]),
    ]),
  );
  made.paint(state.filter);
  return one.node;
}

function finishedSection() {
  const rows = POLLS
    .filter((row) => ['closed', 'cancelled', 'denied', 'archived'].includes(row.status))
    .map((row) => ({ ...row, repeating: false }));
  const one = section('Finished', FINISHED_NOTE, { count: rows.length, id: 'preview-finished' });
  const made = grid(rows, { empty: NO_FINISHED, noun: 'finished poll' });
  one.body.append(
    previewWas('Replaces Closed and Archive — one list, with which one it is as the status badge ' +
      'on the row and the result bars in the drawer.'),
    el('div', { class: 'card' }, [el('div', { class: 'card-body' }, [made.node])]),
  );
  made.paint(null);
  return one.node;
}

function settingControl(spec, say) {
  const fire = (value) => wouldDo(say, `PUT /api/settings/${spec.key} — store ${JSON.stringify(value)}`);
  if (spec.type === 'bool') {
    const node = segment(
      [{ value: 'true', label: 'On' }, { value: 'false', label: 'Off' }],
      spec.value === true ? 'true' : 'false',
      { onChange: () => fire(node.readValue() === 'true') },
    );
    return node;
  }
  if (spec.type === 'enum') {
    const node = segment(
      (spec.choices || []).map((choice) => ({ value: choice, label: choice })),
      spec.value,
      { onChange: () => fire(node.readValue()) },
    );
    return node;
  }
  if (spec.type === 'channel' || spec.type === 'role') {
    const node = el('select', { class: 'input' });
    node.append(el('option', { value: '', text: 'not set', selected: true }));
    if (spec.type === 'channel') {
      for (const channel of CHANNELS) {
        node.append(el('option', { value: channel.id, text: channelLabel(channel, CHANNELS) }));
      }
    } else {
      for (const role of ROLES) node.append(el('option', { value: role.id, text: `@${role.name}` }));
    }
    node.addEventListener('change', () => fire(node.value || null));
    return node;
  }
  if (spec.type === 'int') {
    const node = el('input', { class: 'input', type: 'number', step: '1', value: String(spec.value) });
    node.addEventListener('change', () => fire(Number(node.value)));
    return node;
  }
  const node = el('input', { class: 'input', type: 'text', value: spec.value === null ? '' : String(spec.value) });
  node.addEventListener('change', () => fire(node.value));
  return node;
}

function settingsSection() {
  const say = notice();
  const one = section('Settings', SETTINGS_NOTE, { count: SETTING_SPECS.length, id: 'preview-settings' });
  one.body.append(
    previewWas('The same one settings surface the page has today, still shut on arrival — with ' +
      'poll_mode taken out of it, because the switch above the list is now its only home.'),
    el('div', { class: 'settings-grid' }, SETTING_SPECS.map((spec) => el('div', { class: 'setrow', 'data-key': spec.key }, [
      el('div', { class: 'setrow-head' }, [
        el('span', { class: 'setrow-label', text: spec.label, title: spec.help }),
        el('span', { class: 'setrow-key', text: spec.key }),
      ]),
      el('div', { class: 'setrow-control' }, [settingControl(spec, say)]),
    ]))),
    say,
  );
  return one.node;
}

function logsSection() {
  const one = section('Logs', LOGS_NOTE, { id: 'preview-logs' });
  const holder = el('div');
  const paint = () => {
    const rows = state.important ? LOG_ROWS.filter((row) => row.important) : LOG_ROWS;
    holder.replaceChildren(logsTable(
      rows,
      state.important
        ? 'Polls has logged nothing important. Creating a poll and reminding people about it are ' +
          'routine. Switch to All to see the routine lines too.'
        : 'Polls has logged nothing at all yet.',
      state.important
        ? textAction('Show every line', () => {
          state.important = false;
          only.setValue('all');
          paint();
        })
        : null,
      { noun: 'line', total: rows.length },
    ));
  };
  const only = importantSwitch(state.important, (wanted) => {
    state.important = wanted;
    paint();
  });
  paint();
  one.body.append(
    previewWas('The shared logs block, unchanged — one per page, shut on arrival.'),
    el('div', { class: 'card' }, [
      el('div', { class: 'card-head' }, [only, el('span', { class: 'topbar-gap' })]),
      el('div', { class: 'card-body' }, [holder]),
    ]),
  );
  return one.node;
}

function optionRow(value, onChange) {
  const box = el('input', { class: 'input', type: 'text', value: value || '', placeholder: 'an answer' });
  box.addEventListener('input', onChange);
  const node = el('div', { class: 'formrow' }, [
    field('Option', box),
    bar([button('Remove', () => {
      node.remove();
      onChange();
    }, { tone: 'quiet' })]),
  ]);
  return { node, read: () => box.value.trim() };
}

function ordinal(value) {
  if (value % 100 >= 11 && value % 100 <= 13) return 'th';
  return { 1: 'st', 2: 'nd', 3: 'rd' }[value % 10] || 'th';
}

function cadenceOf(form) {
  const clock = form.at.value.trim();
  const zone = form.zone.value.trim() || 'the server’s own zone';
  if (form.repeat.value === 'weekly') {
    const found = WEEKDAYS.find(([value]) => value === form.weekday.value);
    return `every ${found ? found[1] : form.weekday.value} at ${clock} ${zone}`;
  }
  if (form.repeat.value === 'monthly') {
    const day = Number(form.monthDay.value) || 0;
    return `on the ${day}${ordinal(day)} of each month at ${clock} ${zone}`;
  }
  return `every day at ${clock} ${zone}`;
}

function repeatTrouble(form) {
  if (!/^\d{1,2}:\d{2}$/.test(form.at.value.trim())) return NEED_A_TIME;
  if (form.repeat.value === 'weekly' && !form.weekday.value) return NEED_A_WEEKDAY;
  const day = Number(form.monthDay.value);
  if (form.repeat.value === 'monthly' && !(day >= 1 && day <= 28)) return NEED_A_MONTH_DAY;
  return null;
}

/** The sentence under the button, rebuilt on every keystroke — page-polls.js:477, verbatim. */
function outcomeOf(form) {
  const question = form.question.value.trim();
  if (!question) return NEED_A_QUESTION;
  const labels = form.labels();
  if (form.kind.value === 'date' && !form.start.value.trim()) return NEED_A_START;
  if (labels.length < 2) return NEED_OPTIONS;
  if (labels.length > PANEL_CAP) {
    return `${labels.length} options is more than the ${PANEL_CAP} Black Bloc can put on one ` +
      'poll. Cut it down and the sentence here will say what happens.';
  }
  const anonymous = form.anonymous.readValue() === 'true';
  const hidden = form.results.readValue() === 'close';
  const why = anonymous
    ? 'nobody can be shown who voted'
    : hidden
      ? 'the bars stay hidden until it closes'
      : labels.length > NATIVE_CAP
        ? `${labels.length} options is more than a Discord poll carries`
        : null;
  const where = form.channelName();
  const hours = Number(form.hours.value) || 24;
  if (form.repeating()) {
    return repeatTrouble(form) || REPEATED
      .replace('{question}', question)
      .replace('{where}', where)
      .replace('{cadence}', cadenceOf(form))
      .replace('{hours}', String(hours));
  }
  const shape = why
    ? `a Black Bloc panel — buttons rather than Discord's own poll, because ${why}`
    : "a Discord poll, on Discord's own voting UI";
  const thread = form.thread.readValue() === 'true' ? ' A discussion thread opens under it.' : '';
  return `Posts “${question}” in ${where} with ${labels.length} options, open for ${hours} ` +
    `hour(s), as ${shape}.${thread}`;
}

function channelPicker() {
  const node = el('select', { class: 'input' });
  node.append(el('option', { value: '', text: 'not set', selected: true }));
  for (const channel of CHANNELS) {
    node.append(el('option', { value: channel.id, text: channelLabel(channel, CHANNELS) }));
  }
  return node;
}

function rolePicker() {
  const node = el('select', { class: 'input' });
  node.append(el('option', { value: '', text: 'not set', selected: true }));
  for (const role of ROLES) node.append(el('option', { value: role.id, text: `@${role.name}` }));
  return node;
}

function createForm() {
  const say = notice();
  const question = el('input', { class: 'input', type: 'text', placeholder: 'what you are asking' });
  const kind = el('select', { class: 'input' });
  for (const [value, label] of KINDS) kind.append(el('option', { value, text: label }));
  const hours = el('input', { class: 'input', type: 'number', min: '1', max: '768', value: '24' });
  const where = channelPicker();
  const ping = rolePicker();
  const anonymous = segment([{ value: 'false', label: 'Named' }, { value: 'true', label: 'Anonymous' }], 'false');
  const results = segment([{ value: 'live', label: 'Live bars' }, { value: 'close', label: 'Hidden until close' }], 'live');
  const thread = segment([{ value: 'false', label: 'No thread' }, { value: 'true', label: 'Open a thread' }], 'false');
  const start = el('input', { class: 'input', type: 'text', placeholder: '2026-09-05 or 2026-09-05 19:00' });
  const slots = el('input', { class: 'input', type: 'number', min: '2', max: '25', value: '5' });
  const step = el('input', { class: 'input', type: 'number', min: '1', max: '168', value: '1' });
  const stepUnit = segment([{ value: 'days', label: 'Days' }, { value: 'hours', label: 'Hours' }], 'days');
  const repeat = el('select', { class: 'input' });
  for (const [value, label] of CADENCES) repeat.append(el('option', { value, text: label }));
  const weekday = el('select', { class: 'input' });
  for (const [value, label] of WEEKDAYS) weekday.append(el('option', { value, text: label }));
  const monthDay = el('input', { class: 'input', type: 'number', min: '1', max: '28', value: '1' });
  const at = el('input', { class: 'input', type: 'text', placeholder: '19:00', maxlength: '5' });
  const zone = el('input', { class: 'input', type: 'text', placeholder: 'America/Phoenix' });

  const list = el('div');
  const outcome = el('p', { class: 'section-note' });
  const options = [];
  const form = {
    question,
    kind,
    hours,
    anonymous,
    results,
    thread,
    start,
    repeat,
    weekday,
    monthDay,
    at,
    zone,
    repeating: () => repeat.value !== NO_REPEAT && kind.value !== 'date',
    labels: () => (GENERATED[kind.value]
      ? GENERATED[kind.value]
      : kind.value === 'date'
        ? Array.from({ length: Math.max(0, Number(slots.value) || 0) }, (v, n) => `slot ${n + 1}`)
        : options.map((one) => one.read()).filter(Boolean)),
    channelName: () => {
      const chosen = where.options[where.selectedIndex];
      return where.value && chosen ? chosen.textContent : 'the default channel';
    },
  };
  const repaint = () => {
    outcome.textContent = outcomeOf(form);
  };

  const addOption = (value) => {
    const made = optionRow(value, repaint);
    options.push(made);
    list.append(made.node);
    repaint();
  };
  addOption('');
  addOption('');

  const typedBlock = el('div', {}, [
    el('h3', { text: 'Options' }),
    list,
    bar([button('Add option', () => addOption(''), { tone: 'quiet' })]),
  ]);
  const dateBlock = el('div', { class: 'formrow' }, [
    field('First slot', start, 'A date, or a date and a time when the hour matters.'),
    field('How many slots', slots, 'Two to twenty-five.'),
    field('Gap between slots', step),
    field('Counted in', stepUnit),
  ]);

  const weekdayField = field('Which day', weekday);
  const monthDayField = field('Day of the month', monthDay, 'One to 28 — every month has those.');
  const repeatWhen = el('div', { class: 'formrow' }, [
    weekdayField,
    monthDayField,
    field('Time of day', at, 'On the 24-hour clock, like 19:00.'),
    field('Timezone', zone, TZ_HELP),
  ]);
  const repeatBlock = el('div', {}, [
    el('div', { class: 'formrow' }, [field('Repeat', repeat, REPEAT_HELP)]),
    repeatWhen,
  ]);

  const create = button(CREATE_LABEL, () => {
    const trouble = outcomeOf(form);
    if (trouble === NEED_A_QUESTION || trouble === NEED_OPTIONS || trouble === NEED_A_START) {
      say.say(trouble, 'warn');
      return;
    }
    const route = form.repeating() ? 'POST /api/polls/recurrences' : 'POST /api/polls';
    wouldDo(say, `${route} — ${trouble.replace(/\.$/, '')}`);
  }, { tone: 'warn', small: false });

  const paintRepeat = () => {
    repeatBlock.hidden = kind.value === 'date';
    repeatWhen.hidden = !form.repeating();
    weekdayField.hidden = repeat.value !== 'weekly';
    monthDayField.hidden = repeat.value !== 'monthly';
    create.textContent = form.repeating() ? REPEAT_LABEL : CREATE_LABEL;
    repaint();
  };

  const paintKind = () => {
    typedBlock.hidden = Boolean(GENERATED[kind.value]) || kind.value === 'date';
    dateBlock.hidden = kind.value !== 'date';
    paintRepeat();
  };
  kind.addEventListener('change', paintKind);
  repeat.addEventListener('change', paintRepeat);
  weekday.addEventListener('change', repaint);
  for (const box of [question, hours, start, slots, step, monthDay, at, zone]) {
    box.addEventListener('input', repaint);
  }
  where.addEventListener('change', repaint);
  for (const seg of [anonymous, results, thread, stepUnit]) {
    seg.addEventListener('click', () => setTimeout(repaint, 0));
  }
  paintKind();

  return el('div', {}, [
    el('p', { class: 'section-note', text: CREATE_NOTE }),
    el('div', { class: 'formrow' }, [
      field('Question', question),
      field('Kind', kind),
      field('Open for, hours', hours, 'One hour to 32 days — Discord counts in whole hours.'),
    ]),
    typedBlock,
    dateBlock,
    el('div', { class: 'formrow' }, [
      field('Channel', where, 'Blank uses poll_channel_id.'),
      field('Ping', ping, 'Blank pings nobody.'),
      field('Voters', anonymous),
      field('Results', results),
      field('Thread', thread),
    ]),
    repeatBlock,
    outcome,
    bar([create]),
    say,
  ]);
}

function pageHead() {
  const aside = document.getElementById('page-aside');
  if (!aside) return;
  aside.replaceChildren(button('Create a poll', () => {
    openDrawer('Create a poll', [createForm()]);
  }, { tone: 'warn', small: false }));
}

async function load() {
  watchers.length = 0;
  pageHead();
  const banner = previewBanner({
    today: 9,
    preview: 4,
    note: 'Every button says what it would do and does nothing.',
  });
  banner.setAttribute('data-span', 'full');
  document.getElementById('dash').replaceChildren(
    banner,
    workSection(),
    finishedSection(),
    settingsSection(),
    logsSection(),
  );
}

refresh = start({ tab: 'polls', load });
