/** Preview of a redesigned Events page. Static data; no api() call lives here. */
import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  badge,
  bar,
  button,
  card,
  channelLabel,
  el,
  field,
  foldout,
  humanLabel,
  icon,
  nameNode,
  notice,
  openDrawer,
  sayNothing,
  section,
  segment,
  when,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

let refresh = () => {};

const state = { half: 'events', status: '', trainScope: 'all' };

const HERE = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
const TONE = { pending: 'warn', approved: 'ok', denied: null, cancelled: null };
const TRAIN_TONE = { open: 'ok', locked: 'warn', live: 'warn', done: null, cancelled: null };
const SETTLED = 'This one is settled, so its details cannot be changed — only an event waiting '
  + 'for a decision or already approved can be edited.';
const PLACE_WORD = { room: 'Review channel', post: 'Review post' };
const REMOVE_PLACE = { room: 'Remove its room', post: 'Remove its post' };
const OPEN_STATUSES = ['pending', 'approved', 'live'];
const MOVE_BUTTON = 'Move to the forum';
const FORUM_NOTE = 'One forum under BlackMail, one post per event: the review card and its '
  + 'buttons are the post’s first message, the tag says where it has got to, and the list '
  + 'never grows past the forum’s own archive. events_review_mode decides which one a new '
  + 'proposal gets; the events already open keep the room or post they have, and Move to the '
  + 'forum on an open one takes its room into the forum.';
const NOT_RESENT = 'Saving does not rewrite an announcement that is already up or a Discord '
  + 'scheduled event that already exists; the answer says when that applies.';
const NO_TRAINS = 'No raid train matches that. Staff start one below, or with /raidtrain in Discord.';
const TRAIN_OFF = 'Raid trains are {mode} at the moment, so nothing is posted and no reminder is sent. The Settings below turn them on.';
const LOGS_NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in Discord. '
  + 'Important means it acted on a member or failed.';

const minutesAgo = (minutes) => new Date(Date.now() - minutes * 60000).toISOString();

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null },
  { id: '800000000000000003', name: 'blackbloc-logs', type: 'text', category_id: null },
  { id: '800000000000000004', name: 'bot-log', type: 'text', category_id: null },
  { id: '800000000000000005', name: 'staff-room', type: 'text', category_id: null },
  { id: '800000000000000006', name: 'announcements', type: 'text', category_id: null },
  { id: '800000000000000007', name: 'free-nitro-here', type: 'text', category_id: null },
  { id: '800000000000000008', name: 'Events', type: 'category', category_id: null },
  { id: '800000000000000009', name: 'Join to create', type: 'voice', category_id: null },
  { id: '800000000000000010', name: "casey's room", type: 'voice', category_id: null },
  { id: '800000000000000011', name: 'modmail', type: 'category', category_id: null },
  { id: '800000000000000012', name: 'modmail-log', type: 'text', category_id: '800000000000000011' },
];

const ROLES = [
  { id: '900000000000000001', name: 'Aunties / Uncles' },
  { id: '900000000000000002', name: 'Leads' },
  { id: '900000000000000003', name: 'Live now' },
  { id: '900000000000000004', name: 'Birthday' },
  { id: '900000000000000005', name: 'Members' },
  { id: '900000000000000006', name: 'Server Booster' },
  { id: '900000000000000007', name: 'Events' },
  { id: '900000000000000008', name: 'Casey pings' },
];

const NAMES = {
  '700000000000000001': 'Nick',
  '700000000000000002': 'Casey',
  '700000000000000003': 'Rivet',
  '700000000000000004': 'Moth',
  '700000000000000005': 'spamlord99',
  '700000000000000006': 'Quiet Kid',
  '700000000000000007': 'Dax',
};

const trainStart = (startsAt, position, minutes) =>
  new Date(new Date(startsAt).getTime() + (position - 1) * minutes * 60000).toISOString();

const TRAIN_ONE_START = minutesAgo(-2880);
const TRAIN_TWO_START = minutesAgo(43200);

/** site/mock/server.mjs state.events, RAID_TRAIN_SEED and RAID_SLOT_SEED, verbatim. */
const DATA = {
  // events_review_mode and events_forum_channel_id are the ONE deviation from the seed:
  // the seed is room/null, which makes Move to the forum illegal on every row and therefore
  // undrawable. Set to forum so the move the brief asks to keep visible exists to be seen.
  forum: { id: '800000000000000008', mode: 'forum' },
  events: [
    {
      id: 3,
      title: 'Movie night',
      description: 'Bring snacks.',
      location: null,
      where_kind: 'voice',
      where_channel_id: '800000000000000010',
      where_label: "🔊 casey's room",
      starts_at: minutesAgo(-2880),
      ends_at: null,
      duration: '2h',
      editable: true,
      announced: false,
      scheduled: false,
      status: 'pending',
      requester_id: '700000000000000004',
      requester_name: 'Moth',
      decided_by_id: null,
      decided_by_name: null,
      decided_at: null,
      deny_reason: null,
      moved_word: null,
      review_channel_id: '800000000000000005',
      review_kind: 'room',
      created_at: minutesAgo(60),
    },
    {
      id: 2,
      title: 'Speedrun race',
      description: null,
      location: 'Twitch',
      where_kind: 'other',
      where_channel_id: null,
      where_label: 'Twitch',
      starts_at: minutesAgo(-10080),
      ends_at: null,
      duration: '2h',
      editable: true,
      announced: false,
      scheduled: false,
      status: 'approved',
      requester_id: '700000000000000002',
      requester_name: 'Casey',
      decided_by_id: '700000000000000001',
      decided_by_name: 'Nick',
      decided_at: minutesAgo(3900),
      deny_reason: null,
      moved_word: null,
      review_channel_id: null,
      review_kind: 'room',
      created_at: minutesAgo(4000),
    },
    {
      id: 1,
      title: 'Crypto giveaway',
      description: 'trust me',
      location: 'DM',
      where_kind: 'other',
      where_channel_id: null,
      where_label: 'DM',
      starts_at: minutesAgo(-500),
      ends_at: null,
      duration: '2h',
      editable: false,
      announced: false,
      scheduled: false,
      status: 'denied',
      requester_id: '700000000000000005',
      requester_name: 'spamlord99',
      decided_by_id: '700000000000000001',
      decided_by_name: 'Nick',
      decided_at: minutesAgo(5900),
      deny_reason: 'This is a scam.',
      moved_word: null,
      review_channel_id: null,
      review_kind: 'room',
      created_at: minutesAgo(6000),
    },
  ],
  trains: [
    {
      id: 1,
      organizer_id: '700000000000000001',
      organizer_name: 'Nick',
      title: 'Saturday raid train',
      description: 'Eight hours, one streamer an hour, raid down the line.',
      starts_at: TRAIN_ONE_START,
      slot_minutes: 60,
      slots_total: 4,
      filled: 2,
      status: 'open',
      editable: true,
      slots: [
        { position: 1, user_id: '700000000000000002', user_name: 'Casey', twitch_login: null, checked_in_at: null, starts_at: trainStart(TRAIN_ONE_START, 1, 60) },
        { position: 2, user_id: '700000000000000003', user_name: 'Rivet', twitch_login: null, checked_in_at: null, starts_at: trainStart(TRAIN_ONE_START, 2, 60) },
        { position: 3, user_id: null, user_name: null, twitch_login: null, checked_in_at: null, starts_at: trainStart(TRAIN_ONE_START, 3, 60) },
        { position: 4, user_id: null, user_name: null, twitch_login: null, checked_in_at: null, starts_at: trainStart(TRAIN_ONE_START, 4, 60) },
      ],
    },
    {
      id: 2,
      organizer_id: '700000000000000002',
      organizer_name: 'Casey',
      title: 'Launch-day train',
      description: 'The one that ran last month.',
      starts_at: TRAIN_TWO_START,
      slot_minutes: 60,
      slots_total: 3,
      filled: 3,
      status: 'done',
      editable: false,
      slots: [
        { position: 1, user_id: '700000000000000002', user_name: 'Casey', twitch_login: null, checked_in_at: null, starts_at: trainStart(TRAIN_TWO_START, 1, 60) },
        { position: 2, user_id: '700000000000000003', user_name: 'Rivet', twitch_login: null, checked_in_at: null, starts_at: trainStart(TRAIN_TWO_START, 2, 60) },
        { position: 3, user_id: '700000000000000004', user_name: 'Moth', twitch_login: null, checked_in_at: null, starts_at: trainStart(TRAIN_TWO_START, 3, 60) },
      ],
    },
  ],
  trainMode: 'off',
  eventSettings: [
    { key: 'events_mode', type: 'enum', value: 'on', default: 'off', help: 'off, shadow (no public announcement) or on (announce approved events)', choices: ['off', 'shadow', 'on'] },
    { key: 'events_category_id', type: 'channel', value: '800000000000000008', default: null, help: 'the category review channels are made in' },
    { key: 'events_announce_channel_id', type: 'channel', value: '800000000000000006', default: null, help: 'where an approved event is announced' },
    { key: 'events_ping_role_id', type: 'role', value: null, default: null, help: 'role mentioned when an event is announced and when it starts' },
    { key: 'events_create_scheduled', type: 'bool', value: true, default: false, help: 'true to make a real Discord scheduled event when one is approved' },
    { key: 'events_where_link_in_description', type: 'bool', value: true, default: true, help: "true to put the link or note typed beside a channel at the end of the Discord scheduled event's description" },
    { key: 'events_where_link_aliases', type: 'text', value: 'ttv=https://twitch.tv/{handle}, yt=https://youtube.com/@{handle}', default: 'ttv=https://twitch.tv/{handle}, yt=https://youtube.com/@{handle}', help: 'the shorthands the Where box turns into links, alias=https://host/{handle} entries separated by commas, up to 32 of them' },
    { key: 'events_where_link_check', type: 'enum', value: 'warn', default: 'warn', help: 'whether a link typed into the Where box is opened once before it is kept: off, warn (kept either way, with a note) or refuse (the box says so in words)', choices: ['off', 'warn', 'refuse'] },
    { key: 'events_where_link_check_seconds', type: 'int', value: 2, default: 2, help: 'seconds the link check waits for an answer, 1 to 3' },
    { key: 'events_where_hint', type: 'text', value: 'If you do not see your channel, start typing the channel name and it should appear.', default: 'If you do not see your channel, start typing the channel name and it should appear.', help: 'the sentence directly above the channel picker on the Where panel, and on the draft card while nothing is picked; empty shows no such line' },
    { key: 'events_channel_retention_days', type: 'int', value: 7, default: 7, help: 'days a finished event’s channel is kept before deletion, 1 to 365' },
    { key: 'events_test_retention_minutes', type: 'int', value: 5, default: 5, help: 'minutes a finished or refused event’s review room is kept while Black Bloc is in test mode, 1 to 1440' },
    { key: 'events_max_late_minutes', type: 'int', value: 30, default: 30, help: 'minutes an event may start late and still be announced' },
    { key: 'events_posts_where', type: 'enum', value: 'room', default: 'room', help: "where an approved event's posts go: room (the event's own review room), announce (only events_announce_channel_id), or both", choices: ['room', 'announce', 'both'] },
    { key: 'events_room_delete_who', type: 'enum', value: 'staff', default: 'staff', help: 'who may press Delete this room: staff, or approver — the role in events_approver_role_id. Staff can always press it whichever this holds', choices: ['staff', 'approver'] },
    { key: 'events_approver_role_id', type: 'role', value: null, default: null, help: 'the role Delete this room asks for when events_room_delete_who is approver; blank falls back to staff' },
    { key: 'events_room_notice', type: 'bool', value: true, default: true, help: 'true to post the message carrying Delete this room in every review room Black Bloc makes' },
    { key: 'events_review_mode', type: 'enum', value: 'forum', default: 'room', help: 'where a proposed event is reviewed: room makes a text channel per event under events_category_id; forum makes one post per event in events_forum_channel_id (Make the forum on /event first)', choices: ['room', 'forum'] },
    { key: 'events_forum_channel_id', type: 'channel', value: '800000000000000008', default: null, help: 'the forum channel every event is posted in, in forum mode; Make the forum on /event makes one under the BlackMail category' },
    { key: 'events_moved_line', type: 'text', value: 'This event now lives in its own post: {post}. This room is being removed.', default: 'This event now lives in its own post: {post}. This room is being removed.', help: "the one line left in an event's old review room when staff press Move to the forum; {post} stands for the new post" },
  ],
  trainSettings: [
    { key: 'raidtrain_mode', type: 'enum', value: 'off', default: 'off', help: 'off, shadow (log what would be sent and send nothing) or on (post the lineup and DM slot holders before their hour)', choices: ['off', 'shadow', 'on'] },
    { key: 'raidtrain_organizer_role_id', type: 'role', value: null, default: null, help: 'role that may build and change a raid train’s lineup as well as staff; blank leaves it to staff alone' },
    { key: 'raidtrain_channel_id', type: 'channel', value: '800000000000000003', default: null, help: 'where a train’s lineup post lives; blank uses events_announce_channel_id' },
    { key: 'raidtrain_ping_role_id', type: 'role', value: null, default: null, help: 'role mentioned in front of a lineup post; blank pings nobody, and members on the lineup are never pinged by an edit' },
    { key: 'raidtrain_slot_minutes', type: 'int', value: 60, default: 60, help: 'how long one slot is by default, 15-720 minutes; each train may be created with its own length' },
    { key: 'raidtrain_reminder_minutes', type: 'int', value: 30, default: 30, help: 'how long before their slot a holder is DMed, with who raids into them and who they raid next; the DM is sent once' },
    { key: 'raidtrain_poll_minutes', type: 'int', value: 5, default: 5, help: 'minutes between sweeps that send those reminders, start and finish a train, and notice who is live' },
    { key: 'raidtrain_require_link', type: 'bool', value: true, default: true, help: 'on makes a linked Twitch channel (`/golive` → Link my Twitch channel) a condition of claiming a slot, so the lineup carries the name the streamer before raids; off lets anybody claim and leaves the name off' },
    { key: 'raidtrain_thread', type: 'bool', value: true, default: true, help: 'on opens a thread under the lineup post for the people on the train' },
    { key: 'raidtrain_live_posts', type: 'bool', value: true, default: true, help: 'on says `X is live — next up Y` in that thread when a slot holder starts streaming inside their own hour, and marks the slot checked in' },
    { key: 'raidtrain_max_slots_per_member', type: 'int', value: 1, default: 1, help: 'how many slots one member may claim on one train; 0 means as many as they like. An organizer assigning a slot is never held to it' },
    { key: 'raidtrain_scheduled_event', type: 'bool', value: false, default: false, help: 'on puts the train on Discord’s own event calendar as well. Off by default: Phase 4’s calendar helper writes to the events table, so raid trains keep their own' },
    { key: 'raidtrain_panel_minutes', type: 'int', value: 10, default: 10, help: "minutes the /raidtrain panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it" },
  ],
  eventLogs: [
    { id: 37, at: minutesAgo(60), kind: 'events.requested', important: false, via: 'discord', actor_id: '700000000000000004', actor_name: 'Moth', target_id: null, target_name: null, reason: 'Movie night' },
    { id: 20, at: minutesAgo(13000), kind: 'events.approved', important: true, via: 'website', actor_id: '700000000000000001', actor_name: 'Nick', target_id: null, target_name: null, reason: 'Speedrun race' },
  ],
  trainLogs: [],
};

const SETTINGS_WOULD = (key) => `PUT /api/settings/${key} — save the new value`;

/** A settings row that looks like ui.js:settingRow and saves nothing. */
function staticRow(spec) {
  const say = notice();
  const control = () => {
    if (spec.type === 'enum') {
      return segment(spec.choices.map((one) => ({ value: one, label: one })), spec.value, {
        onChange: () => wouldDo(say, SETTINGS_WOULD(spec.key)),
      });
    }
    if (spec.type === 'bool') {
      const box = el('input', { class: 'input switch', type: 'checkbox', checked: spec.value ? true : undefined });
      box.addEventListener('change', () => wouldDo(say, SETTINGS_WOULD(spec.key)));
      return box;
    }
    if (spec.type.startsWith('role') || spec.type.startsWith('channel')) {
      const many = spec.type.endsWith('s');
      const held = new Set((Array.isArray(spec.value) ? spec.value : [spec.value]).filter(Boolean).map(String));
      const select = el('select', { class: 'input', multiple: many ? true : undefined, size: many ? '4' : undefined });
      if (!many) select.append(el('option', { value: '', text: 'not set' }));
      const source = spec.type.startsWith('role') ? ROLES : CHANNELS;
      for (const one of source) {
        select.append(el('option', {
          value: String(one.id),
          text: spec.type.startsWith('role') ? one.name : channelLabel(one, CHANNELS),
          selected: held.has(String(one.id)) ? true : undefined,
        }));
      }
      select.addEventListener('change', () => wouldDo(say, SETTINGS_WOULD(spec.key)));
      return select;
    }
    const box = el('input', {
      class: 'input',
      type: spec.type === 'int' ? 'number' : 'text',
      value: spec.value === null || spec.value === undefined ? '' : String(spec.value),
    });
    box.addEventListener('change', () => wouldDo(say, SETTINGS_WOULD(spec.key)));
    return box;
  };
  const node = el('div', { class: 'setrow', 'data-key': spec.key, 'data-dirty': 'false' }, [
    el('div', { class: 'setrow-head' }, [
      el('span', { class: 'setrow-label', text: humanLabel(spec.key), title: spec.help || undefined }),
      el('span', { class: 'setrow-key', text: spec.key }),
    ]),
    el('div', { class: 'setrow-control' }, [control()]),
    say,
  ]);
  say.classList.add('setrow-say');
  return node;
}

const staticSettings = (specs) => el('div', { class: 'settings-grid' }, specs.map(staticRow));

function channelNode(id) {
  if (!id) return el('span', { class: 'muted', text: '—' });
  const found = CHANNELS.find((one) => String(one.id) === String(id));
  return found
    ? el('span', { class: 'name', title: `Discord id ${id}`, text: channelLabel(found, CHANNELS) })
    : nameNode(id);
}

/** page-events.js:71 detailCard, verbatim, minus the two lines the row already carries. */
function detailCard(row) {
  const line = (label, value) => el('div', { class: 'field' }, [
    el('span', { class: 'field-label', text: label }),
    value instanceof Node ? value : el('span', { text: value === null || value === undefined || value === '' ? '—' : String(value) }),
  ]);
  return card(`What #${row.id} says`, [
    line('What it is', row.description),
    line('Where', row.where_label),
    line('Starts', when(row.starts_at)),
    line('Ends', when(row.ends_at)),
    line('How long', row.duration),
    line('Asked by', nameNode(row.requester_id, row.requester_name)),
    line('Decided', when(row.decided_at)),
    line('Now', row.moved_word),
    line(PLACE_WORD[row.review_kind] || PLACE_WORD.room, channelNode(row.review_channel_id)),
    line('Announced', row.announced ? 'yes' : 'no'),
    line('Scheduled event', row.scheduled ? 'yes' : 'no'),
    line('Proposed', when(row.created_at)),
  ]);
}

/** page-events.js:145 editCard, verbatim, with Save turned into a note. */
function editCard(row) {
  const say = notice();
  if (!row.editable) return [sayNothing(SETTLED)];
  const title = el('input', { class: 'input', type: 'text', value: row.title || '' });
  const description = el('textarea', { class: 'input area', rows: '3' });
  description.value = row.description || '';
  const start = el('input', { class: 'input', type: 'text', value: '', placeholder: '2026-09-14 19:30' });
  const duration = el('input', { class: 'input', type: 'text', value: row.duration || '', placeholder: '2h' });
  const where = el('select', { class: 'input' });
  where.append(el('option', { value: '', text: '— nowhere in particular —' }));
  where.append(el('option', { value: '__other__', text: '— somewhere else —' }));
  for (const [kind, label] of [['voice', 'Voice channels'], ['text', 'Text channels']]) {
    const group = el('optgroup', { label });
    for (const channel of CHANNELS.filter((one) => one.type === kind)) {
      group.append(el('option', {
        value: String(channel.id),
        text: channelLabel(channel, CHANNELS),
        selected: String(row.where_channel_id || '') === String(channel.id) ? true : undefined,
      }));
    }
    if (group.childElementCount) where.append(group);
  }
  if (row.where_kind === 'other') where.value = '__other__';
  const typed = el('input', { class: 'input', type: 'text', value: row.location || '', placeholder: 'twitch.tv/blackbloc' });

  const save = button('Save', () => {
    wouldDo(say, `PUT /api/events/${row.id} — save the title, the description, where it is, when it starts and how long it runs`);
  }, { tone: 'warn', small: false });

  return [card('Change it', [
    el('p', { class: 'field-help', text: `Times are read in ${HERE}. ${NOT_RESENT}` }),
    field('Title', title),
    field('What it is', description),
    field('Where', where, 'A voice or stage channel gives everybody a Join button on the Discord event; anything else is written on it as words.'),
    field('Where, or a link', typed, 'Only used when it is somewhere else.'),
    field('Starts', start, 'YYYY-MM-DD HH:MM on a 24-hour clock.'),
    field('How long', duration, 'Like 1h30m, 2h or 45m; blank means two hours.'),
    bar([save]),
    say,
  ])];
}

/** page-events.js:184 decide() — a move that would be refused is never drawn. */
function moves(row, say) {
  const buttons = [];
  if (row.status === 'pending') {
    buttons.push(button('Approve', () => {
      wouldDo(say, `POST /api/events/${row.id}/approve — update the review channel, announce it at the configured time and make a Discord scheduled event`);
    }));
    buttons.push(button('Deny', () => {
      wouldDo(say, `POST /api/events/${row.id}/deny — tell ${row.requester_name} it is denied, with the reason typed in`);
    }, { tone: 'danger' }));
  }
  if (row.status !== 'cancelled' && row.status !== 'denied') {
    buttons.push(button('Cancel', () => {
      wouldDo(say, `POST /api/events/${row.id}/cancel — tell everyone who was told about it that it is off and remove the scheduled event`);
    }, { tone: 'quiet' }));
  }
  const movable = row.review_channel_id && row.review_kind !== 'post'
    && OPEN_STATUSES.includes(row.status) && DATA.forum.id && DATA.forum.mode === 'forum';
  if (movable) {
    buttons.push(button(MOVE_BUTTON, () => {
      wouldDo(say, `POST /api/events/${row.id}/forum — put the card and its buttons up as a forum post, tell the room where it went and remove the room`);
    }, { tone: 'warn' }));
  }
  if (row.review_channel_id) {
    const place = row.review_kind === 'post' ? 'post' : 'room';
    buttons.push(button(REMOVE_PLACE[place], () => {
      wouldDo(say, `POST /api/events/${row.id}/room/delete — remove the ${place} for good, and call the event off if it is still open`);
    }, { tone: 'danger' }));
  }
  return buttons;
}

const QUEUE_GRID = 'grid-template-columns: 56px 100px minmax(0, 1fr) 110px 140px 110px 150px 140px 24px;';

function queueHead() {
  return el('div', { class: 'grid-row head', style: QUEUE_GRID }, [
    el('span', { text: 'Event' }),
    el('span', { text: 'Status' }),
    el('span', { text: 'Title' }),
    el('span', { text: 'Asked by' }),
    el('span', { text: 'Starts' }),
    el('span', { text: 'Decided by' }),
    el('span', { text: 'Why not' }),
    el('span', { text: PLACE_WORD.room }),
    el('span', {}),
  ]);
}

function openEvent(row) {
  const say = notice();
  openDrawer(`Event #${row.id} — ${row.title}`, [
    detailCard(row),
    ...editCard(row),
    bar(moves(row, say)),
    say,
  ]);
}

function queueRow(row) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: QUEUE_GRID,
    'data-search': `${row.id} ${row.title} ${row.requester_name} ${row.status} ${row.deny_reason || ''}`.toLowerCase(),
    on: { click: () => openEvent(row) },
  }, [
    el('span', { class: 'cell-id', text: `#${row.id}` }),
    badge(row.status, TONE[row.status] || null),
    el('span', { class: 'cell-name', text: row.title }),
    el('span', { class: 'cell-quiet' }, [nameNode(row.requester_id, row.requester_name)]),
    el('span', { class: 'cell-quiet', text: when(row.starts_at) }),
    el('span', { class: 'cell-quiet' }, [nameNode(row.decided_by_id, row.decided_by_name)]),
    el('span', { class: 'cell-reason', title: row.deny_reason || undefined, text: row.deny_reason || '—' }),
    el('span', { class: 'cell-quiet' }, [channelNode(row.review_channel_id)]),
    icon('chevronRight', 16),
  ]);
}

function queueSection() {
  const say = notice();
  const status = el('select', { class: 'input' });
  for (const one of [['pending', 'waiting for a decision'], ['approved', 'approved'], ['denied', 'denied'], ['cancelled', 'cancelled'], ['', 'every event']]) {
    status.append(el('option', { value: one[0], text: one[1], selected: state.status === one[0] ? true : undefined }));
  }
  status.addEventListener('change', () => {
    state.status = status.value;
    refresh();
  });

  const rows = state.status ? DATA.events.filter((row) => row.status === state.status) : DATA.events;
  const one = section('Queue', 'The same lock and the same allowed-transition check as the buttons in Discord.', {
    count: rows.length,
    open: true,
  });
  one.body.append(
    previewWas('Replaces Queue and the Event #N section an Open button used to grow underneath it — the detail and Change it are in the drawer now.'),
    bar([field('Show', status)], { sticky: true }),
  );

  if (rows.length === 0) {
    one.body.append(sayNothing('Nothing matches that.'));
    return one;
  }
  const grid = el('div', { class: 'grid-table', style: 'min-width: 1040px;' }, [queueHead()]);
  for (const row of rows) {
    grid.append(queueRow(row));
    const buttons = moves(row, say);
    if (buttons.length) {
      grid.append(el('div', { class: 'bar', style: 'padding: 0 16px 10px;' }, buttons));
    }
  }
  one.body.append(el('div', { class: 'table-scroll' }, [grid]), say);
  return one;
}

function eventsReference() {
  const say = notice();
  const one = section('Reference', null, { id: 'events-reference' });
  one.body.append(
    previewWas('Replaces Events forum, events settings and events logs — three sections that were reference, now three foldouts.'),
    foldout('Events forum', [
      el('p', { text: FORUM_NOTE }),
      sayNothing('Set events_review_mode to forum and every event proposed from then on gets its own post there.'),
      sayNothing('Clear events_forum_channel_id below to let go of it.'),
      say,
    ]),
    foldout('events settings', [staticSettings(DATA.eventSettings)], { count: DATA.eventSettings.length }),
    foldout('events logs', [
      el('p', { class: 'section-note', text: LOGS_NOTE }),
      logsTable(DATA.eventLogs, 'Events has not done anything yet.'),
    ], { count: DATA.eventLogs.length }),
  );
  return one;
}

/** page-events.js:296 slotRow, with both staff controls kept and turned into notes. */
function slotTable(train) {
  const say = notice();
  const rows = train.slots.map((slot) => {
    const buttons = [];
    if (train.editable && slot.user_id !== null) {
      buttons.push(button('Take off', () => {
        wouldDo(say, `POST /api/raidtrains/${train.id}/slots/${slot.position} — put the hour back on the lineup and redraw the lineup post`);
      }, { tone: 'quiet' }));
    }
    if (train.editable && slot.user_id === null) {
      buttons.push(button('Put somebody in', () => {
        wouldDo(say, `POST /api/raidtrains/${train.id}/slots/${slot.position} — put the member named into slot #${slot.position}`);
      }));
    }
    return el('tr', {}, [
      el('td', { class: 'mono', 'data-label': 'Slot', text: `#${slot.position}` }),
      el('td', { class: 'mono', 'data-label': 'Starts', text: when(slot.starts_at) }),
      el('td', { 'data-label': 'Who' }, [slot.user_id === null
        ? el('span', { class: 'muted', text: 'open' })
        : nameNode(slot.user_id, slot.user_name)]),
      el('td', { 'data-label': 'Twitch' }, [slot.twitch_login
        ? el('a', { href: `https://twitch.tv/${slot.twitch_login}`, text: slot.twitch_login, rel: 'noreferrer' })
        : el('span', { class: 'muted', text: '—' })]),
      el('td', { 'data-label': '' }, [slot.checked_in_at ? badge('live', 'ok') : el('span', { class: 'muted', text: '—' })]),
      el('td', { 'data-label': '' }, [el('div', { class: 'bar' }, buttons)]),
    ]);
  });
  const head = el('tr', {}, ['Slot', 'Starts', 'Who', 'Twitch', '', ''].map((label) => el('th', { text: label })));
  return [el('div', { class: 'table-scroll' }, [
    el('table', { class: 'log-table' }, [el('thead', {}, [head]), el('tbody', {}, rows)]),
  ]), say];
}

function openTrain(train) {
  const swapSay = notice();
  const first = el('input', { class: 'input', type: 'text', placeholder: '1' });
  const second = el('input', { class: 'input', type: 'text', placeholder: '2' });
  const swap = button('Change them round', () => {
    wouldDo(swapSay, `POST /api/raidtrains/${train.id}/swap — move the two people; the times belong to the position and stay put`);
  });
  const toolSay = notice();
  const tools = [];
  if (train.status === 'open' || train.status === 'locked') {
    const to = train.status === 'open' ? 'locked' : 'open';
    tools.push(button(to === 'locked' ? 'Lock' : 'Unlock', () => {
      wouldDo(toolSay, `POST /api/raidtrains/${train.id}/status — set this train to ${to}`);
    }));
    tools.push(button('Cancel', () => {
      wouldDo(toolSay, `POST /api/raidtrains/${train.id}/status — DM everybody holding a slot and say on the lineup post that it is off`);
    }, { tone: 'danger' }));
  }
  const [grid, slotSay] = slotTable(train);
  openDrawer(`Train #${train.id} — ${train.title}`, [
    el('p', { class: 'field-help', text: train.description }),
    bar(tools),
    toolSay,
    grid,
    slotSay,
    train.editable
      ? card('Change two slots round', [
        el('p', { class: 'field-help', text: 'The people move; the times belong to the position and stay put.' }),
        field('One slot', first),
        field('The other', second),
        bar([swap]),
        swapSay,
      ])
      : sayNothing('This train is settled, so its lineup cannot be changed any more.'),
  ]);
}

const TRAIN_GRID = 'grid-template-columns: 56px minmax(0, 1fr) 150px 90px 120px 110px 130px 24px;';

function trainRow(train) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: TRAIN_GRID,
    'data-search': `${train.id} ${train.title} ${train.organizer_name} ${train.status}`.toLowerCase(),
    on: { click: () => openTrain(train) },
  }, [
    el('span', { class: 'cell-id', text: String(train.id) }),
    el('span', { class: 'cell-name', text: train.title }),
    el('span', { class: 'cell-quiet', text: when(train.starts_at) }),
    el('span', { class: 'cell-quiet', text: `${train.filled}/${train.slots_total}` }),
    el('span', { class: 'cell-quiet', text: `${train.slot_minutes} min` }),
    badge(train.status, TRAIN_TONE[train.status] || null),
    el('span', { class: 'cell-quiet' }, [nameNode(train.organizer_id, train.organizer_name)]),
    icon('chevronRight', 16),
  ]);
}

function trainsSection() {
  const scope = el('select', { class: 'input' });
  for (const one of [['upcoming', 'coming up'], ['past', 'finished and cancelled'], ['all', 'every train']]) {
    scope.append(el('option', { value: one[0], text: one[1], selected: state.trainScope === one[0] ? true : undefined }));
  }
  scope.addEventListener('change', () => {
    state.trainScope = scope.value;
    refresh();
  });
  const now = Date.now();
  const rows = DATA.trains.filter((train) => {
    if (state.trainScope === 'all') return true;
    const ahead = new Date(train.starts_at).getTime() >= now;
    return state.trainScope === 'upcoming' ? ahead : !ahead;
  });

  const one = section('Raid trains', 'Sign-ups by the hour, and a DM to each streamer before their slot.', {
    count: rows.length,
    id: 'raidtrains',
    open: true,
  });
  one.body.append(previewWas('Superseded 2026-09-20 — raid trains left the Events page for a page of their own, /raidtrain.html. This tab is kept only so the preview still shows what Events used to carry.'));
  if (DATA.trainMode !== 'on') {
    one.body.append(notice(TRAIN_OFF.replace('{mode}', DATA.trainMode), 'warn'));
  }
  one.body.append(bar([field('Show', scope)], { sticky: true }));
  if (rows.length === 0) {
    one.body.append(sayNothing(NO_TRAINS));
    return one;
  }
  const head = el('div', { class: 'grid-row head', style: TRAIN_GRID }, [
    el('span', { text: 'Train' }),
    el('span', { text: 'Title' }),
    el('span', { text: 'Starts' }),
    el('span', { text: 'Slots' }),
    el('span', { text: 'How long each' }),
    el('span', { text: 'Status' }),
    el('span', { text: 'Organizer' }),
    el('span', {}),
  ]);
  const grid = el('div', { class: 'grid-table', style: 'min-width: 900px;' }, [head, ...rows.map(trainRow)]);
  one.body.append(el('div', { class: 'table-scroll' }, [grid]));
  return one;
}

function trainsReference() {
  const one = section('Reference', null, { id: 'raidtrain-reference' });
  one.body.append(
    previewWas('Replaces Raid train settings and Raid train logs — the second settings-and-logs pair this page used to carry.'),
    foldout('Raid train settings', [staticSettings(DATA.trainSettings)], { count: DATA.trainSettings.length }),
    foldout('Raid train logs', [
      el('p', { class: 'section-note', text: LOGS_NOTE }),
      logsTable(DATA.trainLogs, 'Raid trains have not done anything yet.'),
    ], { count: DATA.trainLogs.length }),
  );
  return one;
}

/** page-events.js:366 newTrainCard, with Start it turned into a note. */
function newTrainDrawer() {
  const say = notice();
  const title = el('input', { class: 'input', type: 'text', placeholder: 'Saturday raid train' });
  const description = el('textarea', { class: 'input area', rows: '2' });
  const start = el('input', { class: 'input', type: 'text', placeholder: '2026-09-14 19:30' });
  const minutes = el('input', { class: 'input', type: 'text', value: '60' });
  const count = el('input', { class: 'input', type: 'text', value: '8' });
  const make = button('Start it', () => {
    wouldDo(say, 'POST /api/raidtrains — build the lineup and post it once, editing it in place after that');
  }, { tone: 'warn', small: false });
  openDrawer('Start a raid train', [card(null, [
    el('p', { class: 'field-help', text: `Times are read in ${HERE}. The lineup is posted once and edited in place after that.` }),
    field('Title', title),
    field('What it is', description),
    field('Starts', start, 'YYYY-MM-DD HH:MM on a 24-hour clock.'),
    field('Minutes per slot', minutes, '15 to 720.'),
    field('How many slots', count, '1 to 24 — Discord will not carry a longer lineup in one message.'),
    bar([make]),
    say,
  ])]);
}

function halfSwitch() {
  const pick = segment(
    [{ value: 'events', label: 'Events' }, { value: 'raidtrains', label: 'Raid trains' }],
    state.half,
    {
      onChange: () => {
        const wanted = pick.readValue();
        if (wanted === state.half) return;
        state.half = wanted;
        refresh();
      },
    },
  );
  pick.setAttribute('aria-label', 'Which half of this page');
  return bar([field('Show', pick)], { sticky: true });
}

async function load() {
  const banner = previewBanner({
    today: 7,
    preview: 2,
    note: 'Raid trains are the second tab rather than four more sections.',
  });
  banner.setAttribute('data-span', 'full');

  const aside = document.getElementById('page-aside');
  const asideSay = notice();
  if (state.half === 'events') {
    const waiting = DATA.events.filter((row) => row.status === 'pending');
    const go = button(`Decide the ${waiting.length} waiting`, () => {
      if (waiting.length === 0) {
        asideSay.say('Nothing is waiting for a decision.', 'warn');
        return;
      }
      openEvent(waiting[waiting.length - 1]);
    }, { tone: 'warn', small: false, disabled: waiting.length === 0 });
    if (aside) aside.replaceChildren(go, asideSay);
  } else if (aside) {
    aside.replaceChildren(button('Start a raid train', newTrainDrawer, { tone: 'warn', small: false }), asideSay);
  }

  const nodes = state.half === 'events'
    ? [queueSection().node, eventsReference().node]
    : [trainsSection().node, trainsReference().node];

  document.getElementById('dash').replaceChildren(banner, halfSwitch(), ...nodes);
}

refresh = start({ tab: 'events', load });
