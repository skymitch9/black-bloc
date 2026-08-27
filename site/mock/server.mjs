import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { readFile, readdir, stat } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = fileURLToPath(new URL('.', import.meta.url));
const PUBLIC = resolve(HERE, '..', 'public');
const PORT = Number(process.env.MOCK_PORT || 8788);
let testMode = process.env.MOCK_TEST_MODE !== '0';

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.woff2': 'font/woff2',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

// Mirrors black_bloc/api/assets.py: one build id over the bytes of everything the site
// serves, stamped into every /assets URL, HTML never stored and assets revalidated.
const MOCK_VERSION = '0.8.0-mock';
const DIGEST_CHARS = 12;
const ASSET_URL = /(href|src)="(\/assets\/[^"?#]+)"/g;
const NO_STORE = 'no-store';
const REVALIDATE = 'no-cache';

async function filesUnder(root) {
  const found = [];
  for (const entry of await readdir(root, { withFileTypes: true })) {
    const full = join(root, entry.name);
    if (entry.isDirectory()) found.push(...await filesUnder(full));
    else if (entry.isFile()) found.push(full);
  }
  return found;
}

async function buildId() {
  const digest = createHash('sha256').update(MOCK_VERSION);
  const files = (await filesUnder(PUBLIC)).sort();
  for (const file of files) {
    digest.update(file.slice(PUBLIC.length + 1).split('\\').join('/'));
    digest.update(await readFile(file));
  }
  return `${MOCK_VERSION}-${digest.digest('hex').slice(0, DIGEST_CHARS)}`;
}

const BUILD = await buildId();

function stamp(html) {
  return html.replace(ASSET_URL, (whole, attr, url) => `${attr}="${url}?v=${BUILD}"`);
}

const NOT_SIGNED_IN = 'You are not signed in yet. Sign in with the Discord account you moderate Black in a Flash! with.';
const NOT_STAFF = 'This dashboard is for the mods and admins of Black in a Flash!. Your Discord account is signed in, but it does not hold a staff role. Ask a Lead for the role.';
const STAFF_UNKNOWN = 'Black Bloc could not ask Discord which roles you hold, so it cannot tell whether you are staff. That is a fault at the bot, not a problem with your access. Try again in a minute.';
const ROLE_MENUS_OFF = 'Role menus are turned off right now, so nothing was changed. A Lead can turn them back on from the dashboard\'s Role menus tab or with `/rolemenu mode on`.';
const GUARD = 'TEST MODE is on, so Black Bloc refuses to act outside #mute-me-bot-test-spam. Nothing was done. Ask the owner to lift the test guard first.';
const UNKNOWN_ROUTE = 'This dashboard asked Black Bloc for something it does not serve. That is a fault in the page, not a problem with your access.';

const now = () => new Date().toISOString();
const minutesAgo = (m) => new Date(Date.now() - m * 60000).toISOString();
const daysAhead = (d) => new Date(Date.now() + d * 86400000).toISOString();

const ROLES = [
  { id: '900000000000000001', name: 'Aunties / Uncles', color: '#e04a6d', position: 12, managed: false },
  { id: '900000000000000002', name: 'Leads', color: '#4eefff', position: 14, managed: false },
  { id: '900000000000000003', name: 'Live now', color: '#a35bff', position: 5, managed: false },
  { id: '900000000000000004', name: 'Birthday', color: '#ffd166', position: 4, managed: false },
  { id: '900000000000000005', name: 'Members', color: '#8a8f98', position: 1, managed: false },
  { id: '900000000000000006', name: 'Server Booster', color: '#f47fff', position: 9, managed: true },
];

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null, position: 0 },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null, position: 1 },
  { id: '800000000000000003', name: 'mute-me-bot-test-spam', type: 'text', category_id: null, position: 2 },
  { id: '800000000000000004', name: 'bot-log', type: 'text', category_id: null, position: 3 },
  { id: '800000000000000005', name: 'staff-room', type: 'text', category_id: null, position: 4 },
  { id: '800000000000000006', name: 'announcements', type: 'text', category_id: null, position: 5 },
  { id: '800000000000000007', name: 'free-nitro-here', type: 'text', category_id: null, position: 6 },
  { id: '800000000000000008', name: 'Events', type: 'category', category_id: null, position: 7 },
  { id: '800000000000000009', name: 'Join to create', type: 'voice', category_id: null, position: 8 },
  { id: '800000000000000010', name: "casey's room", type: 'voice', category_id: null, position: 9 },
  { id: '800000000000000011', name: 'modmail', type: 'category', category_id: null, position: 10 },
];

const MEMBERS = [
  { id: '700000000000000001', name: 'nbaslamking', display_name: 'Nick', avatar_url: null },
  { id: '700000000000000002', name: 'caseyfast', display_name: 'Casey', avatar_url: null },
  { id: '700000000000000003', name: 'rivet.exe', display_name: 'Rivet', avatar_url: null },
  { id: '700000000000000004', name: 'moth_light', display_name: 'Moth', avatar_url: null },
  { id: '700000000000000005', name: 'spamlord99', display_name: 'spamlord99', avatar_url: null },
  { id: '700000000000000006', name: 'quietkid', display_name: 'Quiet Kid', avatar_url: null },
  { id: '700000000000000007', name: 'daxthecat', display_name: 'Dax', avatar_url: null },
  { id: '700000000000000008', name: 'gonefromguild', display_name: 'Left the server', avatar_url: null },
];

const STAFF = MEMBERS[0];

// The whole server roster the Members tab pages through — the eight above keep their ids
// (the cases, birthdays and hits all point at them) and the rest are filler with bots, staff
// and a handful of joins inside the last week, so every chip has something to show.
const STAFF_ROLE_IDS = ['900000000000000002', '900000000000000001'];
const MEMBER_ROLE_ID = '900000000000000005';
const BOOSTER_ROLE_ID = '900000000000000006';
const LIVE_ROLE_ID = '900000000000000003';

const FILLER_NAMES = [
  'ash', 'bex', 'cato', 'dee', 'echo', 'fen', 'gus', 'hana', 'ines', 'jory',
  'kit', 'lark', 'mika', 'noor', 'opal', 'pim', 'quill', 'rue', 'sable', 'tovi',
  'uma', 'vale', 'wren', 'xan', 'yuki', 'zev', 'bramble', 'cinder', 'dune', 'ember',
  'flint', 'gale', 'harbour', 'indigo', 'juniper', 'kestrel', 'linnet', 'moss', 'nettle', 'onyx',
  'plover', 'quartz', 'rowan', 'sorrel', 'teal', 'umber', 'vetch', 'willow',
];
const BOT_NAMES = ['MEE6', 'Carl-bot', 'Dyno', 'Statbot'];

function rosterRow(at, name, display, { bot = false, minutes, roles }) {
  return {
    id: String(700000000000000001n + BigInt(at)),
    name,
    display_name: display,
    bot,
    joined_at: minutesAgo(minutes),
    role_ids: roles,
    avatar_url: null,
  };
}

const ROSTER = [
  ...MEMBERS.map((member, at) => ({
    ...member,
    bot: false,
    joined_at: minutesAgo([600000, 420000, 300000, 200000, 5000, 120000, 90000, 400000][at]),
    role_ids: at === 0
      ? [STAFF_ROLE_IDS[0], MEMBER_ROLE_ID]
      : at === 1
        ? [STAFF_ROLE_IDS[1], MEMBER_ROLE_ID]
        : at === 2
          ? [STAFF_ROLE_IDS[1], LIVE_ROLE_ID, MEMBER_ROLE_ID]
          : [MEMBER_ROLE_ID],
  })),
  ...BOT_NAMES.map((name, at) => rosterRow(100 + at, name.toLowerCase(), name, {
    bot: true,
    minutes: 500000 - at * 40000,
    roles: [MEMBER_ROLE_ID],
  })),
  ...FILLER_NAMES.map((name, at) => rosterRow(200 + at, `${name}${at}`, name[0].toUpperCase() + name.slice(1), {
    // The last five joined inside the week, so "New this week" is never an empty chip.
    minutes: at >= FILLER_NAMES.length - 5
      ? 120 + (at - (FILLER_NAMES.length - 5)) * 900
      : 20000 + at * 3100,
    roles: at % 7 === 0 ? [BOOSTER_ROLE_ID, MEMBER_ROLE_ID] : [MEMBER_ROLE_ID],
  })),
];

const SETTING_SPECS = [
  ['log_channel_id', 'channel', '800000000000000004', null, 'where Black Bloc posts what it did'],
  ['staff_channel_id', 'channel', '800000000000000005', null, 'the channel whose viewers count as staff'],
  ['role_menu_channel_id', 'channel', '800000000000000002', null, 'where /rolemenu post goes by default'],
  ['golive_mode', 'enum', 'shadow', 'off', 'off, shadow (log only) or on (post go-live announcements)', ['off', 'shadow', 'on']],
  ['golive_channel_id', 'channel', '800000000000000006', null, 'where go-live announcements are posted'],
  ['golive_template', 'text', '{name} is live playing {game} — {title} {url}', '{name} is live: {url}', 'the announcement wording; {name} {game} {title} {url} {platform}'],
  ['golive_end_suffix', 'text', ' — stream ended', ' — stream ended', 'what is added to an announcement once the stream has ended'],
  ['golive_live_role_id', 'role', '900000000000000003', null, 'role given while someone is streaming'],
  ['golive_require_role_id', 'role', null, null, 'only announce people who have this role'],
  ['golive_ignore_role_id', 'role', null, null, 'never announce people who have this role'],
  ['golive_cooldown_minutes', 'int', 60, 60, 'minutes before the same person is announced again'],
  ['golive_ping_role_id', 'role', null, null, 'role mentioned in front of every go-live announcement'],
  ['golive_max_session_hours', 'int', 12, 12, 'hours before a stream still marked live is closed anyway'],
  ['tempvoice_mode', 'enum', 'on', 'off', 'off, or on (join-to-create makes a temporary voice channel)', ['off', 'on']],
  ['tempvoice_creator_ids', 'channels', ['800000000000000009'], [], 'the join-to-create channels; /tempvoice setup fills this in'],
  ['tempvoice_name_template', 'text', "{user}'s room", "{user}'s room", 'what a spawned channel is called; {user} is the member'],
  ['tempvoice_creator_name', 'text', 'join to create a channel', 'join to create a channel', 'what the join-to-create channel is called'],
  ['tempvoice_allowed_role_id', 'role', null, null, 'only members with this role get a temporary channel'],
  ['honeypot_mode', 'enum', 'shadow', 'off', 'off, shadow (log only) or on (ban whoever posts in the trap)', ['off', 'shadow', 'on']],
  ['honeypot_channel_ids', 'channels', ['800000000000000007'], [], 'the trap channels; /honeypot setup fills this in'],
  ['honeypot_purge_days', 'int', 1, 1, 'days of the banned account’s messages to delete with it, 0 to 7', null, 7],
  ['honeypot_exempt_role_ids', 'roles', ['900000000000000001'], [], 'roles the trap ignores; staff are always ignored too'],
  ['events_mode', 'enum', 'on', 'off', 'off, shadow (no public announcement) or on (announce approved events)', ['off', 'shadow', 'on']],
  ['events_category_id', 'channel', '800000000000000008', null, 'the category review channels are made in'],
  ['events_announce_channel_id', 'channel', '800000000000000006', null, 'where an approved event is announced'],
  ['events_ping_role_id', 'role', null, null, 'role mentioned when an event is announced and when it starts'],
  ['events_create_scheduled', 'bool', true, false, 'true to make a real Discord scheduled event when one is approved'],
  ['events_channel_retention_days', 'int', 7, 7, 'days a finished event’s channel is kept before deletion, 1 to 365', null, 365, 1],
  ['events_max_late_minutes', 'int', 30, 30, 'minutes an event may start late and still be announced', null, 1440],
  ['birthday_mode', 'enum', 'shadow', 'off', 'off, shadow (log only) or on (post birthday wishes)', ['off', 'shadow', 'on']],
  ['birthday_channel_id', 'channel', '800000000000000002', null, 'where birthday wishes are posted'],
  ['birthday_template', 'text', 'Happy birthday {name}!', 'Happy birthday {name}!', 'the birthday wording; {name} and {age}'],
  ['birthday_color', 'color', '#4eefff', '#4eefff', 'the birthday embed’s colour, as a hex code like #4eefff'],
  ['birthday_role_id', 'role', '900000000000000004', null, 'role given for the day and taken back the next'],
  ['birthday_show_age', 'bool', false, false, 'true to put {age} in reach for people who stored a birth year'],
  ['modmail_enabled', 'bool', true, false, 'true when Black Bloc answers DMs'],
  ['modmail_mode', 'enum', 'thread', 'channel', 'channel (one channel per ticket) or thread (private threads in one channel)', ['channel', 'thread']],
  ['modmail_category_id', 'channel', '800000000000000011', null, 'the category ticket channels are made in, in channel mode'],
  ['modmail_staff_channel_id', 'channel', '800000000000000005', null, 'the channel ticket threads are made in, in thread mode'],
  ['modmail_log_channel_id', 'channel', '800000000000000004', null, 'where a closed ticket’s transcript is posted'],
  ['automod_mode', 'enum', 'shadow', 'off', 'off, shadow (log what it would do) or on (delete, warn and time out)', ['off', 'shadow', 'on']],
  ['automod_rules', 'json', null, null, 'the automod rule book; the Automod tab is what changes it'],
  ['automod_exempt_role_ids', 'roles', ['900000000000000001', '900000000000000002'], [], 'roles automod ignores'],
  ['automod_exempt_channel_ids', 'channels', ['800000000000000003'], [], 'channels automod never reads'],
  ['automod_warn_threshold', 'int', 8, 8, 'warnings before Black Bloc says so in the log, 0 to stop counting', null, 100],
  ['modlog_channel_id', 'channel', '800000000000000004', null, 'where mod cases are posted; defaults to log_channel_id'],
  ['mod_dm_on_action', 'enum', 'server_action_reason', 'server_action', 'what a punished member is told', ['none', 'server_action', 'server_action_reason']],
  ['rolemenu_approval_channel_id', 'channel', '800000000000000005', null, 'where a role request card is posted for staff to answer; defaults to staff_channel_id'],
  ['rolemenu_approver_role_id', 'role', null, null, 'role mentioned when a role request needs answering'],
  ['rolemenu_mode', 'enum', 'off', 'off', 'whether members can pick roles from the panels; off takes them down and hides the /rolemenu commands, on posts them again', ['off', 'on']],
];

const RULES = {
  mention_spam: { enabled: true, window_s: 30, threshold: 5, actions: ['delete', 'warn', 'timeout'], timeout_s: 300 },
  slowmode: { enabled: true, window_s: 4, threshold: 6, actions: [], timeout_s: 0 },
  linkspam: { enabled: true, window_s: 1, threshold: 1, actions: [], timeout_s: 0 },
  invitespam: { enabled: false, window_s: 30, threshold: 1, actions: ['delete', 'warn', 'timeout'], timeout_s: 600 },
  attachmentspam: { enabled: false, window_s: 30, threshold: 5, actions: [], timeout_s: 0 },
  caps: { enabled: false, window_s: 0, threshold: 70, actions: [], timeout_s: 0 },
  bad_words: { enabled: false, window_s: 0, threshold: 1, actions: [], timeout_s: 0, words: [] },
};

const RULE_HELP = {
  mention_spam: 'how many people or roles one member may mention in the window',
  slowmode: 'how many messages one member may post in the window',
  linkspam: 'how many links one member may post in the window',
  invitespam: 'how many Discord invites one member may post in the window',
  attachmentspam: 'how many attachments one member may post in the window',
  caps: 'the percentage of shouted letters a message may contain',
  bad_words: 'the blocked word list',
};

function seedState() {
  return {
  settings: new Map(SETTING_SPECS.map((spec) => [spec[0], spec[2]])),
  audit: [
    { key: 'automod_mode', value: 'shadow', updated_by: STAFF.id, updated_at: minutesAgo(220) },
    { key: 'golive_mode', value: 'shadow', updated_by: MEMBERS[1].id, updated_at: minutesAgo(900) },
    { key: 'honeypot_channel_ids', value: ['800000000000000007'], updated_by: STAFF.id, updated_at: minutesAgo(2600) },
  ],
  actions: [],
  rules: JSON.parse(JSON.stringify(RULES)),
  menus: [
    {
      id: 1,
      name: 'colours',
      title: 'Pick a colour',
      description: 'One at a time.',
      mode: 'single',
      channel_id: '800000000000000002',
      message_id: '810000000000000001',
      approval: false,
      expires_days: null,
      retry_days: 7,
      options: [
        { role_id: '900000000000000003', label: 'Live now', emoji: '🔴', position: 0 },
        { role_id: '900000000000000004', label: 'Birthday', emoji: '🎂', position: 1 },
      ],
    },
    {
      id: 2,
      name: 'pings',
      title: 'What should we ping you for?',
      description: null,
      mode: 'multiple',
      channel_id: null,
      message_id: null,
      approval: false,
      expires_days: null,
      retry_days: 7,
      options: [{ role_id: '900000000000000005', label: 'Members', emoji: null, position: 0 }],
    },
    {
      id: 3,
      name: 'runner-status',
      title: 'Runner status',
      description: 'Staff say yes to these, and they run out after a week.',
      mode: 'multiple',
      channel_id: '800000000000000002',
      message_id: '810000000000000002',
      approval: true,
      expires_days: 7,
      retry_days: 7,
      options: [{ role_id: '900000000000000003', label: 'Runner', emoji: '🏃', position: 0 }],
    },
  ],
  requests: [
    { id: 4, menu_id: 3, user_id: MEMBERS[3].id, role_id: '900000000000000003', requested_at: minutesAgo(35), status: 'pending', decided_by: null, decided_at: null, deny_reason: null },
    { id: 3, menu_id: 3, user_id: MEMBERS[6].id, role_id: '900000000000000003', requested_at: minutesAgo(1500), status: 'pending', decided_by: null, decided_at: null, deny_reason: null },
    { id: 2, menu_id: 3, user_id: MEMBERS[1].id, role_id: '900000000000000003', requested_at: minutesAgo(6000), status: 'approved', decided_by: STAFF.id, decided_at: minutesAgo(5900), deny_reason: null },
    { id: 1, menu_id: 3, user_id: MEMBERS[4].id, role_id: '900000000000000003', requested_at: minutesAgo(9000), status: 'denied', decided_by: MEMBERS[1].id, decided_at: minutesAgo(8900), deny_reason: 'Not until the trial run is over.' },
  ],
  grants: [
    { id: 5, user_id: MEMBERS[1].id, role_id: '900000000000000003', source: 'approval', granted_by: STAFF.id, granted_at: minutesAgo(5900), expires_at: daysAhead(2), removed_at: null, removed_reason: null },
    { id: 4, user_id: MEMBERS[2].id, role_id: '900000000000000001', source: 'staff', granted_by: STAFF.id, granted_at: minutesAgo(20000), expires_at: daysAhead(29), removed_at: null, removed_reason: null },
    { id: 3, user_id: MEMBERS[3].id, role_id: '900000000000000004', source: 'menu', granted_by: null, granted_at: minutesAgo(30000), expires_at: null, removed_at: null, removed_reason: null },
    { id: 2, user_id: MEMBERS[5].id, role_id: '900000000000000003', source: 'staff', granted_by: MEMBERS[1].id, granted_at: minutesAgo(40000), expires_at: daysAhead(-1), removed_at: minutesAgo(1200), removed_reason: 'expired' },
    { id: 1, user_id: MEMBERS[6].id, role_id: '900000000000000005', source: 'manual', granted_by: null, granted_at: minutesAgo(50000), expires_at: null, removed_at: minutesAgo(300), removed_reason: 'ended_by_staff' },
  ],
  nextMenu: 4,
  nextRequest: 5,
  nextGrant: 6,
  golive: {
    links: [
      { user_id: MEMBERS[1].id, twitch_login: 'caseyfast', twitch_user_id: '112233', linked_at: minutesAgo(4000) },
      { user_id: MEMBERS[2].id, twitch_login: 'rivetplays', twitch_user_id: '445566', linked_at: minutesAgo(9000) },
    ],
    optouts: [{ user_id: MEMBERS[5].id, at: minutesAgo(2000) }],
    sessions: [
      { id: 12, user_id: MEMBERS[1].id, source: 'twitch', url: 'https://twitch.tv/caseyfast', game: 'Lethal Company', title: 'late night runs', started_at: minutesAgo(120), ended_at: null, mode: 'shadow', announced_message_id: null },
      { id: 11, user_id: MEMBERS[2].id, source: 'presence', url: 'https://twitch.tv/rivetplays', game: 'Balatro', title: 'one more run', started_at: minutesAgo(1500), ended_at: minutesAgo(1300), mode: 'shadow', announced_message_id: null },
    ],
  },
  events: [
    { id: 3, requester_id: MEMBERS[3].id, title: 'Movie night', description: 'Bring snacks.', location: 'Voice: general', starts_at: minutesAgo(-2880), ends_at: null, status: 'pending', created_at: minutesAgo(60), decided_by: null, decided_at: null, deny_reason: null },
    { id: 2, requester_id: MEMBERS[1].id, title: 'Speedrun race', description: null, location: 'Twitch', starts_at: minutesAgo(-10080), ends_at: null, status: 'approved', created_at: minutesAgo(4000), decided_by: STAFF.id, decided_at: minutesAgo(3900), deny_reason: null },
    { id: 1, requester_id: MEMBERS[4].id, title: 'Crypto giveaway', description: 'trust me', location: 'DM', starts_at: minutesAgo(-500), ends_at: null, status: 'denied', created_at: minutesAgo(6000), decided_by: STAFF.id, decided_at: minutesAgo(5900), deny_reason: 'This is a scam.' },
  ],
  birthdays: [
    { user_id: MEMBERS[1].id, month: 2, day: 14, year: 1996, opted_in: true, source: 'self', set_at: minutesAgo(9000) },
    { user_id: MEMBERS[2].id, month: 2, day: 27, year: null, opted_in: true, source: 'import', set_at: minutesAgo(12000) },
    { user_id: MEMBERS[3].id, month: 7, day: 4, year: 2001, opted_in: true, source: 'self', set_at: minutesAgo(15000) },
    { user_id: MEMBERS[6].id, month: 11, day: 30, year: null, opted_in: false, source: 'import', set_at: minutesAgo(16000) },
    { user_id: MEMBERS[0].id, month: 2, day: 3, year: 1990, opted_in: true, source: 'self', set_at: minutesAgo(17000) },
    { user_id: MEMBERS[5].id, month: 7, day: 19, year: null, opted_in: true, source: 'import', set_at: minutesAgo(18000) },
    { user_id: MEMBERS[7].id, month: 4, day: 8, year: 1999, opted_in: true, source: 'import', set_at: minutesAgo(19000) },
  ],
  tempvoice: [
    { channel_id: '800000000000000010', owner_id: MEMBERS[1].id, creator_id: '800000000000000009', created_at: minutesAgo(45) },
  ],
  honeypot: [
    { id: 7, user_id: MEMBERS[4].id, channel_id: '800000000000000007', message_id: '820000000000000001', content: 'free nitro at scam-link.example', at: minutesAgo(30), mode: 'shadow', action: 'would_ban' },
    { id: 6, user_id: MEMBERS[7].id, channel_id: '800000000000000007', message_id: '820000000000000002', content: 'steam gift card giveaway', at: minutesAgo(900), mode: 'shadow', action: 'would_ban' },
    { id: 5, user_id: MEMBERS[5].id, channel_id: '800000000000000007', message_id: '820000000000000003', content: 'dm me for cheap nitro', at: minutesAgo(2600), mode: 'on', action: 'banned' },
    { id: 4, user_id: MEMBERS[7].id, channel_id: '800000000000000007', message_id: '820000000000000004', content: 'crypto doubler, first 50 only', at: minutesAgo(6100), mode: 'on', action: 'ban_failed' },
  ],
  cases: [
    { id: 9, user_id: MEMBERS[4].id, kind: 'timeout', moderator_id: STAFF.id, reason: 'mention spam', duration_s: 300, at: minutesAgo(20), mode: 'shadow', applied: false, actions: ['delete', 'warn', 'timeout'], done: [], failed: [] },
    { id: 8, user_id: MEMBERS[5].id, kind: 'warn', moderator_id: MEMBERS[1].id, reason: 'link spam', duration_s: null, at: minutesAgo(400), mode: 'on', applied: true, actions: ['warn'], done: ['warn'], failed: [] },
    { id: 7, user_id: MEMBERS[4].id, kind: 'warn', moderator_id: STAFF.id, reason: 'told to stop', duration_s: null, at: minutesAgo(800), mode: 'on', applied: true, actions: ['warn'], done: ['warn'], failed: [] },
    { id: 6, user_id: MEMBERS[7].id, kind: 'ban', moderator_id: STAFF.id, reason: 'scam links', duration_s: null, at: minutesAgo(5000), mode: 'on', applied: true, actions: ['ban'], done: ['ban'], failed: [] },
    { id: 5, user_id: MEMBERS[5].id, kind: 'timeout', moderator_id: MEMBERS[1].id, reason: 'shouting in caps', duration_s: 600, at: minutesAgo(6200), mode: 'on', applied: true, actions: ['delete', 'timeout'], done: ['delete', 'timeout'], failed: [] },
    { id: 4, user_id: MEMBERS[6].id, kind: 'warn', moderator_id: MEMBERS[2].id, reason: 'posted an invite to another server', duration_s: null, at: minutesAgo(7400), mode: 'on', applied: true, actions: ['delete', 'warn'], done: ['delete', 'warn'], failed: [] },
    { id: 3, user_id: MEMBERS[4].id, kind: 'timeout', moderator_id: STAFF.id, reason: 'attachment spam', duration_s: 900, at: minutesAgo(9100), mode: 'on', applied: true, actions: ['timeout'], done: ['timeout'], failed: [] },
    { id: 2, user_id: MEMBERS[3].id, kind: 'warn', moderator_id: MEMBERS[1].id, reason: 'arguing in #welcome', duration_s: null, at: minutesAgo(11000), mode: 'on', applied: true, actions: ['warn'], done: ['warn'], failed: [] },
    { id: 1, user_id: MEMBERS[5].id, kind: 'kick', moderator_id: STAFF.id, reason: 'first-day nitro scam', duration_s: null, at: minutesAgo(14000), mode: 'on', applied: true, actions: ['kick'], done: [], failed: ['kick'] },
  ],
  tickets: [
    { id: 5, user_id: MEMBERS[3].id, mode: 'thread', channel_id: '800000000000000005', thread_id: '830000000000000001', status: 'open', opened_at: minutesAgo(90), closed_at: null, closed_by: null, close_reason: null },
    { id: 4, user_id: MEMBERS[6].id, mode: 'thread', channel_id: '800000000000000005', thread_id: '830000000000000002', status: 'open', opened_at: minutesAgo(600), closed_at: null, closed_by: null, close_reason: null },
    { id: 3, user_id: MEMBERS[4].id, mode: 'channel', channel_id: '800000000000000011', thread_id: null, status: 'closed', opened_at: minutesAgo(4000), closed_at: minutesAgo(3800), closed_by: STAFF.id, close_reason: 'spam' },
  ],
  messages: {
    5: [
      { id: 21, at: minutesAgo(90), author_id: MEMBERS[3].id, direction: 'in', anonymous: false, content: 'Someone is posting scam links in general.', attachments: null, delivered: 1 },
      { id: 22, at: minutesAgo(88), author_id: STAFF.id, direction: 'note', anonymous: false, content: 'Same account as the honeypot hit this morning.', attachments: null, delivered: 1 },
      { id: 23, at: minutesAgo(85), author_id: STAFF.id, direction: 'out', anonymous: true, content: 'Thanks for the report — we are on it.', attachments: null, delivered: 1 },
    ],
    4: [
      { id: 18, at: minutesAgo(600), author_id: MEMBERS[6].id, direction: 'in', anonymous: false, content: 'Can I get the Live now role?', attachments: null, delivered: 1 },
    ],
    3: [
      { id: 9, at: minutesAgo(4000), author_id: MEMBERS[4].id, direction: 'in', anonymous: false, content: 'free nitro', attachments: null, delivered: 1 },
    ],
  },
  snippets: [
    { name: 'rules', content: 'Please read #welcome — the rules are pinned there.', by: STAFF.id, at: minutesAgo(20000) },
    { name: 'closing', content: 'Closing this for now; reply again if it comes back.', by: STAFF.id, at: minutesAgo(20000) },
  ],
  blocks: [
    { user_id: MEMBERS[4].id, by: STAFF.id, reason: 'opened twelve tickets about nitro', at: minutesAgo(3000) },
  ],
  nextAction: 42,
  nextCase: 10,
  nextMessage: 40,
  actions: seedActions(),
  };
}

function seedActions() {
  return [
  { id: 41, at: minutesAgo(3), kind: 'web.settings.set', actor_id: STAFF.id, target_id: null, reason: 'automod_mode = shadow', details: { key: 'automod_mode', value: 'shadow' } },
  { id: 40, at: minutesAgo(20), kind: 'automod.would_timeout', actor_id: null, target_id: MEMBERS[4].id, reason: 'mention spam: 6 mentions in 30s', details: { rule: 'mention_spam' } },
  { id: 39, at: minutesAgo(30), kind: 'honeypot.would_ban', actor_id: null, target_id: MEMBERS[4].id, reason: 'posted in #free-nitro-here', details: null },
  { id: 38, at: minutesAgo(45), kind: 'tempvoice.channel_created', actor_id: MEMBERS[1].id, target_id: '800000000000000010', reason: null, details: null },
  { id: 37, at: minutesAgo(60), kind: 'events.requested', actor_id: MEMBERS[3].id, target_id: null, reason: 'Movie night', details: null },
  { id: 36, at: minutesAgo(88), kind: 'modmail.note_added', actor_id: STAFF.id, target_id: MEMBERS[3].id, reason: null, details: null },
  { id: 35, at: minutesAgo(120), kind: 'golive.would_announce', actor_id: null, target_id: MEMBERS[1].id, reason: 'Lethal Company', details: null },
  { id: 34, at: minutesAgo(220), kind: 'web.settings.set', actor_id: STAFF.id, target_id: null, reason: 'automod_mode = shadow', details: null },
  { id: 33, at: minutesAgo(400), kind: 'mod.warn', actor_id: MEMBERS[1].id, target_id: MEMBERS[5].id, reason: 'link spam', details: null },
  { id: 32, at: minutesAgo(800), kind: 'mod.warn', actor_id: STAFF.id, target_id: MEMBERS[4].id, reason: 'told to stop', details: null },
  { id: 31, at: minutesAgo(900), kind: 'settings.set', actor_id: MEMBERS[1].id, target_id: null, reason: 'golive_mode = shadow', details: null },
  { id: 30, at: minutesAgo(5000), kind: 'mod.ban', actor_id: STAFF.id, target_id: MEMBERS[7].id, reason: 'scam links', details: null },
  { id: 29, at: minutesAgo(5200), kind: 'honeypot.banned', actor_id: null, target_id: MEMBERS[5].id, reason: 'posted in #free-nitro-here', details: null },
  { id: 28, at: minutesAgo(6100), kind: 'honeypot.ban_failed', actor_id: null, target_id: MEMBERS[7].id, reason: 'Missing Permissions', details: null },
  { id: 27, at: minutesAgo(6200), kind: 'automod.timeout', actor_id: null, target_id: MEMBERS[5].id, reason: 'caps: 82% of a 40-character message', details: { rule: 'caps' } },
  { id: 26, at: minutesAgo(7400), kind: 'automod.delete', actor_id: null, target_id: MEMBERS[6].id, reason: 'invitespam: 1 invite in 30s', details: { rule: 'invitespam' } },
  { id: 25, at: minutesAgo(8000), kind: 'rolemenu.role_given', actor_id: MEMBERS[3].id, target_id: '900000000000000003', reason: 'colours', details: null },
  { id: 24, at: minutesAgo(9100), kind: 'automod.timeout', actor_id: null, target_id: MEMBERS[4].id, reason: 'attachmentspam: 6 files in 30s', details: { rule: 'attachmentspam' } },
  { id: 23, at: minutesAgo(9600), kind: 'birthday.would_wish', actor_id: null, target_id: MEMBERS[1].id, reason: 'February 14', details: null },
  { id: 22, at: minutesAgo(11000), kind: 'mod.warn', actor_id: MEMBERS[1].id, target_id: MEMBERS[3].id, reason: 'arguing in #welcome', details: null },
  { id: 21, at: minutesAgo(12000), kind: 'tempvoice.channel_deleted', actor_id: null, target_id: '800000000000000010', reason: 'empty for 60s', details: null },
  { id: 20, at: minutesAgo(13000), kind: 'events.approved', actor_id: STAFF.id, target_id: null, reason: 'Speedrun race', details: null },
  { id: 19, at: minutesAgo(14000), kind: 'mod.kick_failed', actor_id: STAFF.id, target_id: MEMBERS[5].id, reason: 'Missing Permissions', details: null },
  ];
}

let state = seedState();

const CORE_KEYS = ['log_channel_id', 'staff_channel_id', 'role_menu_channel_id'];
const NAMESPACE_OVERRIDE = {
  modlog_channel_id: 'automod',
  mod_dm_on_action: 'automod',
};

function namespaceOf(key) {
  if (key in NAMESPACE_OVERRIDE) return NAMESPACE_OVERRIDE[key];
  if (CORE_KEYS.includes(key)) return 'core';
  const [head, ...rest] = key.split('_');
  return rest.length ? head : 'core';
}

function keyRow(key) {
  const [, type, , fallback, help, choices, max, min] = specOf(key);
  return {
    key,
    type,
    value: state.settings.get(key) ?? null,
    default: fallback ?? null,
    help,
    ...(choices ? { choices } : {}),
    ...(max === undefined || max === null ? {} : { max }),
    ...(min === undefined || min === null ? {} : { min }),
  };
}

function settingsPayload() {
  const grouped = { core: [] };
  for (const [key] of SETTING_SPECS) {
    const namespace = namespaceOf(key);
    grouped[namespace] = grouped[namespace] || [];
    grouped[namespace].push(keyRow(key));
  }
  return grouped;
}

function specOf(key) {
  return SETTING_SPECS.find((spec) => spec[0] === key) || null;
}

function nameFor(id) {
  const member = MEMBERS.find((m) => m.id === id);
  if (member) return { name: member.name, display_name: member.display_name, kind: 'member' };
  const role = ROLES.find((r) => r.id === id);
  if (role) return { name: role.name, display_name: role.name, kind: 'role' };
  const channel = CHANNELS.find((c) => c.id === id);
  if (channel) return { name: channel.name, display_name: `#${channel.name}`, kind: 'channel' };
  return { name: null, display_name: null, kind: 'unknown' };
}

function memberName(id) {
  const found = nameFor(String(id));
  return found.display_name || found.name || null;
}

function logAction(kind, { actor_id = STAFF.id, target_id = null, reason = null, details = null } = {}) {
  const row = { id: state.nextAction++, at: now(), kind, actor_id, target_id, reason, details };
  state.actions.unshift(row);
  return row;
}

class Refused extends Error {
  constructor(status, error, message) {
    super(message);
    this.status = status;
    this.error = error;
  }
}

function cookieOf(request, name) {
  const raw = request.headers.cookie || '';
  for (const part of raw.split(';')) {
    const [key, ...rest] = part.trim().split('=');
    if (key === name) return decodeURIComponent(rest.join('='));
  }
  return null;
}

function sessionOf(request, url) {
  const asked = url.searchParams.get('as');
  if (asked) return asked;
  return cookieOf(request, 'mock_as') || 'staff';
}

function requireStaff(session) {
  if (session === 'none') throw new Refused(401, 'not_signed_in', NOT_SIGNED_IN);
  if (session === 'stranger') throw new Refused(403, 'not_staff', NOT_STAFF);
  if (session === 'unknown') throw new Refused(503, 'staff_unknown', STAFF_UNKNOWN);
  if (session === 'expired') throw new Refused(401, 'session_expired', 'Your sign-in has expired. Sign in again — nothing is wrong with your access.');
  if (session === 'down') throw new Refused(503, 'database_unavailable', 'Black Bloc’s database is not reachable right now, so this page cannot load its data; try again in a minute.');
}

function guard(what) {
  // Only where the REAL API refuses in test mode. A modmail reply and a warn are not on that
  // list: black_bloc/api/tools/mod.py lets warn past the guard and tools/modmail.py's reply
  // route never asks it, so refusing them here would teach the pages a rule the bot has not got.
  if (testMode) throw new Refused(409, 'test_mode', `${GUARD} (${what})`);
}

function meBody(session) {
  if (session === 'none') return { status: 401, body: { error: 'not_signed_in', message: NOT_SIGNED_IN } };
  if (session === 'expired') return { status: 401, body: { error: 'session_expired', message: 'Your sign-in has expired. Sign in again — nothing is wrong with your access.' } };
  const user = { id: STAFF.id, name: STAFF.name, avatar: null };
  const guild = { id: '600000000000000001', name: 'Black in a Flash!' };
  if (session === 'stranger') {
    return { status: 200, body: { user: { id: MEMBERS[5].id, name: MEMBERS[5].name, avatar: null }, staff: false, state: 'not_staff', guild, message: NOT_STAFF } };
  }
  if (session === 'unknown') {
    return { status: 200, body: { user, staff: false, state: 'staff_unknown', guild, message: STAFF_UNKNOWN } };
  }
  return { status: 200, body: { user, staff: true, state: 'staff', guild, message: null } };
}

function statusBody() {
  const features = SETTING_SPECS
    .map(([key]) => key)
    .filter((key) => key.endsWith('_mode'))
    .map((key) => ({ key, feature: key.slice(0, -'_mode'.length), mode: state.settings.get(key) ?? null }));
  return {
    bot: {
      ready: true,
      latency_ms: 42,
      guilds: 1,
      uptime_seconds: 93720,
      started_at: minutesAgo(1562),
      version: '0.8.0-mock',
      test_mode: testMode,
    },
    guild: { id: '600000000000000001', name: 'Black in a Flash!' },
    features,
    loops: [
      { cog: 'GoLive', name: 'poll_twitch', running: true, failed: false, state: 'ok', next_iteration: minutesAgo(-2), last_ok_at: minutesAgo(3), last_error: null },
      { cog: 'Birthdays', name: 'announce_birthdays', running: true, failed: false, state: 'ok', next_iteration: minutesAgo(-600), last_ok_at: minutesAgo(840), last_error: null },
      { cog: 'Events', name: 'reconcile_events', running: false, failed: true, state: 'danger', next_iteration: null, last_ok_at: minutesAgo(300), last_error: 'HTTPException: 500 Internal Server Error' },
      { cog: 'TempVoice', name: 'sweep_empty', running: true, failed: false, state: 'ok', next_iteration: minutesAgo(-4), last_ok_at: minutesAgo(1), last_error: null },
    ],
    open: {
      role_menus_posted: state.menus.filter((menu) => menu.message_id).length,
      temp_channels: state.tempvoice.length,
      honeypot_hits_7d: state.honeypot.length,
      open_events: state.events.filter((event) => event.status === 'pending').length,
      open_modmail: state.tickets.filter((ticket) => ticket.status === 'open').length,
    },
    notes: [],
    checked_at: now(),
  };
}

function withNames(row, keys) {
  const found = { ...row };
  for (const [from, to] of keys) {
    const id = row[from];
    found[to] = id === null || id === undefined ? null : memberName(id);
  }
  return found;
}

async function readBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  if (chunks.length === 0) return {};
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch (e) {
    throw new Refused(400, 'bad_request', 'That request could not be read. Reload the page and try again.');
  }
}

function validate(key, value) {
  const spec = specOf(key);
  if (spec === null) {
    throw new Refused(400, 'unknown_key', `Black Bloc has no setting called ${key}, so nothing was changed.`);
  }
  const [, type, , , , choices, max] = spec;
  if (value === null) return null;
  if (type === 'int') {
    const number = Number(value);
    if (!Number.isFinite(number)) throw new Refused(400, 'bad_value', `${key} is a number, and "${value}" is not one.`);
    if (max !== undefined && max !== null && number > max) {
      throw new Refused(400, 'bad_value', `${key} cannot be higher than ${max}, so it was left as it was.`);
    }
    if (number < 0) throw new Refused(400, 'bad_value', `${key} cannot be negative.`);
    return Math.round(number);
  }
  if (type === 'enum' && choices && !choices.includes(String(value))) {
    throw new Refused(400, 'bad_value', `${key} has to be one of ${choices.join(', ')}, so "${value}" was refused.`);
  }
  if (type === 'color' && !/^#[0-9a-fA-F]{6}$/.test(String(value))) {
    throw new Refused(400, 'bad_value', `${key} has to be a hex colour like #4eefff.`);
  }
  if ((type === 'channels' || type === 'roles') && !Array.isArray(value)) {
    throw new Refused(400, 'bad_value', `${key} is a list, and that was not one.`);
  }
  if (type === 'bool') return Boolean(value);
  return value;
}

function armingRefusal(key, value) {
  if (key === 'automod_mode' && value === 'on' && !state.settings.get('modlog_channel_id')) {
    throw new Refused(400, 'not_armable', 'Automod will not be armed while modlog_channel_id is unset: nobody would see what it did. Set the mod log channel first.');
  }
  if (key === 'honeypot_mode' && value === 'on' && (state.settings.get('honeypot_channel_ids') || []).length === 0) {
    throw new Refused(400, 'not_armable', 'The honeypot has no trap channels, so arming it would ban nobody and hide the fact. Run setup first.');
  }
}

const ROUTES = [];

function route(method, pattern, handler) {
  ROUTES.push({ method, pattern, handler });
}

function match(pattern, path) {
  const patternParts = pattern.split('/');
  const pathParts = path.split('/');
  if (patternParts.length !== pathParts.length) return null;
  const params = {};
  for (let at = 0; at < patternParts.length; at += 1) {
    const piece = patternParts[at];
    if (piece.startsWith(':')) params[piece.slice(1)] = decodeURIComponent(pathParts[at]);
    else if (piece !== pathParts[at]) return null;
  }
  return params;
}

route('POST', '/api/mock/reset', () => {
  // NOT part of the contract: it exists so site/mock/check.mjs can give every route the
  // same fixture, the way each pytest case gets a fresh database.
  state = seedState();
  return { reset: true };
});

route('POST', '/api/mock/guard', async (context) => {
  // NOT part of the contract either: check.mjs turns the guard off to read the shapes of the
  // routes the guard refuses, then turns it back on. The default is still MOCK_TEST_MODE.
  const body = await context.body();
  testMode = body.on !== false;
  return { test_mode: testMode };
});

route('GET', '/api/auth/me', (context) => meBody(context.session));

route('GET', '/api/auth/login', (context) => ({
  status: 302,
  headers: { location: '/index.html?signin=ok', 'set-cookie': 'mock_as=staff; Path=/; SameSite=Lax' },
  body: null,
}));

route('POST', '/api/auth/logout', () => ({
  status: 200,
  headers: { 'set-cookie': 'mock_as=none; Path=/; SameSite=Lax' },
  body: { ok: true },
}));

route('GET', '/api/status', (context) => {
  requireStaff(context.session);
  return statusBody();
});

route('GET', '/api/actions', (context) => {
  requireStaff(context.session);
  const limit = Math.max(1, Math.min(Number(context.url.searchParams.get('limit') || 50), 200));
  const kind = context.url.searchParams.get('kind');
  const userId = context.url.searchParams.get('user_id');
  let rows = state.actions;
  if (kind) rows = rows.filter((row) => String(row.kind).startsWith(kind));
  if (userId) rows = rows.filter((row) => row.actor_id === userId || row.target_id === userId);
  return {
    actions: rows.slice(0, limit).map((row) => withNames(row, [['actor_id', 'actor_name'], ['target_id', 'target_name']])),
    limit,
    notes: [],
  };
});

route('GET', '/api/ref/channels', (context) => {
  requireStaff(context.session);
  return CHANNELS;
});

route('GET', '/api/ref/roles', (context) => {
  requireStaff(context.session);
  return ROLES;
});

route('GET', '/api/ref/members', (context) => {
  requireStaff(context.session);
  const query = (context.url.searchParams.get('q') || '').toLowerCase();
  const limit = Math.max(1, Math.min(Number(context.url.searchParams.get('limit') || 25), 25));
  return MEMBERS
    .filter((member) => !query || member.name.toLowerCase().includes(query) || member.display_name.toLowerCase().includes(query))
    .slice(0, limit);
});

const NEW_MS = 7 * 24 * 60 * 60 * 1000;
const MEMBERS_PER_PAGE = 50;

function rosterRoles(row) {
  return row.role_ids
    .map((id) => ROLES.find((role) => role.id === id))
    .filter(Boolean)
    .sort((a, b) => b.position - a.position)
    .slice(0, 5)
    .map((role) => ({ id: role.id, name: role.name, color: role.color }));
}

function isStaffRow(row) {
  return !row.bot && row.role_ids.some((id) => STAFF_ROLE_IDS.includes(id));
}

function isNewRow(row) {
  return Date.now() - new Date(row.joined_at).getTime() <= NEW_MS;
}

route('GET', '/api/members', (context) => {
  requireStaff(context.session);
  const params = context.url.searchParams;
  const query = (params.get('q') || '').trim().toLowerCase();
  const wanted = ['all', 'staff', 'bots', 'new'].includes(params.get('filter')) ? params.get('filter') : 'all';
  const sort = ['joined_desc', 'joined_asc', 'name'].includes(params.get('sort')) ? params.get('sort') : 'joined_desc';
  const page = Math.max(1, Number(params.get('page') || 1) || 1);
  const perPage = Math.max(1, Math.min(Number(params.get('per_page') || MEMBERS_PER_PAGE) || MEMBERS_PER_PAGE, 100));

  let found = ROSTER.filter((row) => !query
    || row.display_name.toLowerCase().includes(query)
    || row.name.toLowerCase().includes(query));
  if (wanted === 'staff') found = found.filter(isStaffRow);
  if (wanted === 'bots') found = found.filter((row) => row.bot);
  if (wanted === 'new') found = found.filter(isNewRow);

  if (sort === 'name') found = [...found].sort((a, b) => a.display_name.toLowerCase().localeCompare(b.display_name.toLowerCase()));
  else {
    found = [...found].sort((a, b) => new Date(a.joined_at) - new Date(b.joined_at));
    if (sort === 'joined_desc') found.reverse();
  }

  const shown = found.slice((page - 1) * perPage, page * perPage);
  return {
    total: ROSTER.length,
    humans: ROSTER.filter((row) => !row.bot).length,
    bots: ROSTER.filter((row) => row.bot).length,
    staff: ROSTER.filter(isStaffRow).length,
    new_7d: ROSTER.filter(isNewRow).length,
    page,
    per_page: perPage,
    shown: shown.length,
    members: shown.map((row) => ({
      id: row.id,
      name: row.display_name,
      username: row.name,
      bot: row.bot,
      joined_at: row.joined_at,
      roles: rosterRoles(row),
      staff: isStaffRow(row),
      cases: state.cases.filter((one) => one.user_id === row.id).length,
      avatar: row.avatar_url,
    })),
  };
});

route('GET', '/api/ref/names', (context) => {
  requireStaff(context.session);
  const ids = (context.url.searchParams.get('ids') || '').split(',').map((id) => id.trim()).filter(Boolean);
  const found = {};
  for (const id of ids) found[id] = nameFor(id);
  return found;
});

route('GET', '/api/settings', (context) => {
  requireStaff(context.session);
  return settingsPayload();
});

route('GET', '/api/settings/audit', (context) => {
  requireStaff(context.session);
  const limit = Math.max(1, Math.min(Number(context.url.searchParams.get('limit') || 100), 500));
  return {
    audit: state.audit.slice(0, limit).map((row) => ({
      key: row.key,
      namespace: namespaceOf(row.key),
      value: row.value,
      updated_by_id: row.updated_by === null || row.updated_by === undefined ? null : String(row.updated_by),
      updated_by_name: memberName(row.updated_by),
      updated_at: row.updated_at,
    })),
    limit,
  };
});

route('PUT', '/api/settings/:key', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const value = validate(context.params.key, body.value === undefined ? null : body.value);
  armingRefusal(context.params.key, value);
  state.settings.set(context.params.key, value);
  state.audit.unshift({ key: context.params.key, value, updated_by: STAFF.id, updated_at: now() });
  logAction('web.settings.set', { reason: `${context.params.key} = ${JSON.stringify(value)}`, details: { key: context.params.key, value } });
  return keyRow(context.params.key);
});

route('DELETE', '/api/settings/:key', (context) => {
  requireStaff(context.session);
  const spec = specOf(context.params.key);
  if (spec === null) throw new Refused(400, 'unknown_key', `Black Bloc has no setting called ${context.params.key}.`);
  state.settings.set(context.params.key, spec[3] ?? null);
  state.audit.unshift({ key: context.params.key, value: spec[3] ?? null, updated_by: STAFF.id, updated_at: now() });
  logAction('web.settings.clear', { reason: context.params.key, details: { key: context.params.key } });
  return { ...keyRow(context.params.key), cleared: true };
});

const BAD_APPROVAL = 'Approval is on or off, so nothing was changed. That is a fault in the page rather than in what you picked.';
const BAD_DAYS = 'That is not a number of days, so nothing was changed. Send a whole number from 0 to 3650 — 0 means the role never runs out.';
const NOT_POSTED_YET = 'That menu is not posted anywhere yet, so there is no panel to move. Post it from the Post a menu section to choose where it goes.';
const NO_SUCH_REQUEST = 'Black Bloc has no record of that request any more, so nothing was done.';
const ALREADY_DECIDED = 'Somebody answered that request already, so nothing was changed.';
const DENY_NEEDS_A_REASON = 'A denied request needs one line the member is sent, so nothing was done. Say why and send it again.';
const NO_SUCH_GRANT = 'Black Bloc has no timed role like that any more, so nothing was changed.';
const ALREADY_ENDED = 'That timed role has already ended, so there was nothing to change.';
const NO_END_DATE = 'That role has no end date, so there is nothing to push back. End it now instead.';
const DAYS_NEEDED = 'Extending a role needs a number of days, so nothing was changed.';
const NO_SUCH_MEMBER = 'That is not somebody Black Bloc can see in this server, so nothing was granted.';
const NO_SUCH_ROLE = 'That is not a role in this server any more, so nothing was granted.';

function wantedApproval(given) {
  if (given === undefined || given === null) return null;
  if (typeof given !== 'boolean') throw new Refused(400, 'bad_approval', BAD_APPROVAL);
  return given;
}

function wantedDays(given, where) {
  if (given === undefined || given === null || given === '') return null;
  const number = Number(given);
  if (!Number.isInteger(number) || number < 0 || number > 3650) {
    throw new Refused(400, 'bad_days', `${BAD_DAYS} (${where})`);
  }
  return number;
}

/** The real API takes the old panel down before the new one goes up. */
function movePanel(menu, channelId) {
  if (!menu.message_id) throw new Refused(400, 'not_posted', NOT_POSTED_YET);
  if (menu.mode === 'staff') throw new Refused(400, 'staff_menu', `${menu.name} is a staff-assigned menu, so there is no panel to post.`);
  if (!menu.options.length) throw new Refused(400, 'no_options', `${menu.name} has no roles on it yet, so there is nothing to post.`);
  if (state.settings.get('rolemenu_mode') !== 'on') throw new Refused(409, 'rolemenu_off', ROLE_MENUS_OFF);
  if (!CHANNELS.some((channel) => channel.id === channelId)) {
    throw new Refused(400, 'no_such_channel', `${channelId} is not a channel Black Bloc can see, so nothing was moved.`);
  }
  guard('moving a role menu panel');
  menu.channel_id = channelId;
  menu.message_id = String(Date.now());
  logAction('web.rolemenu.post', { reason: menu.name, target_id: menu.channel_id, details: { menu: menu.name, channel_id: menu.channel_id, message_id: menu.message_id } });
}

function menuNameOf(menuId) {
  const found = state.menus.find((menu) => String(menu.id) === String(menuId));
  return found ? found.name : null;
}

function requestRow(row) {
  return {
    id: row.id,
    menu_id: String(row.menu_id),
    menu_name: menuNameOf(row.menu_id),
    user_id: String(row.user_id),
    user_name: memberName(row.user_id),
    user_avatar: null,
    role_id: String(row.role_id),
    role_name: memberName(row.role_id),
    requested_at: row.requested_at,
    status: row.status,
    decided_by_id: row.decided_by === null ? null : String(row.decided_by),
    decided_by_name: row.decided_by === null ? null : memberName(row.decided_by),
    decided_at: row.decided_at,
    deny_reason: row.deny_reason,
  };
}

function grantRow(row) {
  return {
    id: row.id,
    user_id: String(row.user_id),
    user_name: memberName(row.user_id),
    role_id: String(row.role_id),
    role_name: memberName(row.role_id),
    source: row.source,
    granted_by_id: row.granted_by === null ? null : String(row.granted_by),
    granted_by_name: row.granted_by === null ? null : memberName(row.granted_by),
    granted_at: row.granted_at,
    expires_at: row.expires_at,
    removed_at: row.removed_at,
    removed_reason: row.removed_reason,
    open: row.removed_at === null,
  };
}

function whenDays(days) {
  return days === null || days === undefined ? null : daysAhead(days);
}

function menuOfRequest(row) {
  return state.menus.find((menu) => String(menu.id) === String(row.menu_id)) || null;
}

function menuRow(menu) {
  return {
    name: menu.name,
    title: menu.title,
    description: menu.description,
    mode: menu.mode,
    channel_id: menu.channel_id === null || menu.channel_id === undefined ? null : String(menu.channel_id),
    message_id: menu.message_id === null || menu.message_id === undefined ? null : String(menu.message_id),
    approval: Boolean(menu.approval),
    expires_days: menu.expires_days ?? null,
    retry_days: menu.retry_days ?? 7,
    options: menu.options.map((option, at) => ({
      role_id: String(option.role_id),
      label: option.label ?? null,
      emoji: option.emoji ?? null,
      position: option.position ?? at,
    })),
  };
}

route('GET', '/api/rolemenus', (context) => {
  requireStaff(context.session);
  return state.menus.map(menuRow);
});

route('POST', '/api/rolemenus', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const name = String(body.name || '').trim();
  if (!name) throw new Refused(400, 'bad_value', 'A role menu needs a name so people can find it again.');
  if (state.menus.some((menu) => menu.name === name)) {
    throw new Refused(409, 'exists', `There is already a role menu called ${name}. Pick another name or edit that one.`);
  }
  const menu = {
    id: state.nextMenu++,
    name,
    title: body.title || name,
    description: body.description || null,
    mode: body.mode || 'multiple',
    channel_id: null,
    message_id: null,
    approval: wantedApproval(body.approval) ?? false,
    expires_days: wantedDays(body.expires_days, 'expires_days') ?? null,
    retry_days: wantedDays(body.retry_days, 'retry_days') ?? 7,
    options: Array.isArray(body.options) ? body.options : [],
  };
  state.menus.unshift(menu);
  logAction('web.rolemenu.create', { reason: name, details: { menu: name, mode: menu.mode } });
  return menuRow(menu);
});

route('PUT', '/api/rolemenus/:name', async (context) => {
  requireStaff(context.session);
  const menu = state.menus.find((entry) => entry.name === context.params.name);
  if (!menu) throw new Refused(404, 'no_menu', `There is no role menu called ${context.params.name}.`);
  const body = await context.body();
  if (body.title !== undefined) menu.title = body.title;
  if (body.description !== undefined) menu.description = body.description;
  if (body.mode !== undefined) menu.mode = body.mode;
  if (body.approval !== undefined) menu.approval = wantedApproval(body.approval);
  if (body.expires_days !== undefined) menu.expires_days = wantedDays(body.expires_days, 'expires_days') || null;
  if (body.retry_days !== undefined) menu.retry_days = wantedDays(body.retry_days, 'retry_days') ?? menu.retry_days;
  if (Array.isArray(body.options)) menu.options = body.options;
  logAction('web.rolemenu.edit', { reason: menu.name, details: { menu: menu.name } });
  const moving = body.channel_id === undefined || body.channel_id === null || body.channel_id === ''
    ? null
    : String(body.channel_id);
  if (moving !== null && moving !== menu.channel_id) movePanel(menu, moving);
  return menuRow(menu);
});

route('DELETE', '/api/rolemenus/:name', (context) => {
  requireStaff(context.session);
  const at = state.menus.findIndex((entry) => entry.name === context.params.name);
  if (at < 0) throw new Refused(404, 'no_menu', `There is no role menu called ${context.params.name}.`);
  state.menus.splice(at, 1);
  logAction('web.rolemenu.delete', { reason: context.params.name, details: { menu: context.params.name } });
  return { deleted: true, name: context.params.name };
});

route('POST', '/api/rolemenus/:name/post', async (context) => {
  requireStaff(context.session);
  const menu = state.menus.find((entry) => entry.name === context.params.name);
  if (!menu) throw new Refused(404, 'no_menu', `There is no role menu called ${context.params.name}.`);
  const body = await context.body();
  if (!body.channel_id) throw new Refused(400, 'bad_value', 'Pick a channel to post the menu in.');
  if (state.settings.get('rolemenu_mode') !== 'on') throw new Refused(409, 'rolemenu_off', ROLE_MENUS_OFF);
  guard('posting a role menu');
  menu.channel_id = String(body.channel_id);
  menu.message_id = String(Date.now());
  logAction('web.rolemenu.post', { reason: menu.name, target_id: menu.channel_id, details: { menu: menu.name, channel_id: menu.channel_id, message_id: menu.message_id } });
  return { posted: true, name: menu.name, channel_id: menu.channel_id, message_id: menu.message_id };
});

route('GET', '/api/rolemenus/requests', (context) => {
  requireStaff(context.session);
  const asked = (context.url.searchParams.get('status') || '').split(',').filter(Boolean);
  const known = ['pending', 'approved', 'denied', 'withdrawn', 'granted_by_hand'];
  for (const one of asked) {
    if (!known.includes(one)) {
      throw new Refused(400, 'unknown_status', `${one} is not a state a role request can be in, so nothing was listed. They are ${known.join(', ')}.`);
    }
  }
  const wanted = asked.length ? asked : known;
  return state.requests
    .filter((row) => wanted.includes(row.status))
    .slice()
    .sort((a, b) => (b.status === 'pending') - (a.status === 'pending') || b.id - a.id)
    .map(requestRow);
});

route('POST', '/api/rolemenus/requests/:id/approve', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const row = state.requests.find((one) => String(one.id) === context.params.id);
  if (!row) throw new Refused(409, 'not_decided', NO_SUCH_REQUEST);
  if (row.status !== 'pending') throw new Refused(409, 'not_decided', `${ALREADY_DECIDED} It is already ${row.status}.`);
  const given = wantedDays(body.days, 'days');
  const menu = menuOfRequest(row);
  const days = body.days === undefined || body.days === null ? (menu ? menu.expires_days : null) : given;
  row.status = 'approved';
  row.decided_by = STAFF.id;
  row.decided_at = now();
  const until = days ? whenDays(days) : null;
  state.grants.unshift({
    id: state.nextGrant++,
    user_id: row.user_id,
    role_id: row.role_id,
    source: 'approval',
    granted_by: STAFF.id,
    granted_at: now(),
    expires_at: until,
    removed_at: null,
    removed_reason: null,
  });
  logAction('web.role.approved', { target_id: row.user_id, details: { request_id: row.id, role_id: row.role_id } });
  return {
    request: requestRow(row),
    message: `Approved — ${memberName(row.user_id)} has ${memberName(row.role_id)} now.${until ? ' It runs out in ' + days + ' days.' : ''}`,
  };
});

route('POST', '/api/rolemenus/requests/:id/deny', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const row = state.requests.find((one) => String(one.id) === context.params.id);
  if (!row) throw new Refused(409, 'not_decided', NO_SUCH_REQUEST);
  const reason = String(body.reason || '').trim();
  if (!reason) throw new Refused(400, 'no_reason', DENY_NEEDS_A_REASON);
  if (row.status !== 'pending') throw new Refused(409, 'not_decided', `${ALREADY_DECIDED} It is already ${row.status}.`);
  row.status = 'denied';
  row.decided_by = STAFF.id;
  row.decided_at = now();
  row.deny_reason = reason;
  logAction('web.role.denied', { target_id: row.user_id, reason, details: { request_id: row.id, role_id: row.role_id } });
  return { request: requestRow(row), message: 'Denied, and they have been told why.' };
});

route('GET', '/api/roles/grants', (context) => {
  requireStaff(context.session);
  const params = context.url.searchParams;
  const userId = params.get('user_id') || '';
  const roleId = params.get('role_id') || '';
  const limit = Math.max(1, Math.min(Number(params.get('limit') || 200) || 200, 200));
  return state.grants
    .filter((row) => (!userId || String(row.user_id) === userId) && (!roleId || String(row.role_id) === roleId))
    .slice()
    .sort((a, b) => (b.removed_at === null) - (a.removed_at === null) || b.id - a.id)
    .slice(0, limit)
    .map(grantRow);
});

route('POST', '/api/roles/grants', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const userId = String(body.user_id || '');
  const roleId = String(body.role_id || '');
  if (!ROSTER.some((row) => row.id === userId)) throw new Refused(404, 'no_such_member', NO_SUCH_MEMBER);
  if (!ROLES.some((row) => row.id === roleId)) throw new Refused(404, 'no_such_role', NO_SUCH_ROLE);
  const days = wantedDays(body.days, 'days');
  const row = {
    id: state.nextGrant++,
    user_id: userId,
    role_id: roleId,
    source: 'staff',
    granted_by: STAFF.id,
    granted_at: now(),
    expires_at: days ? whenDays(days) : null,
    removed_at: null,
    removed_reason: null,
  };
  state.grants.unshift(row);
  logAction('web.role.granted', { target_id: userId, reason: body.reason || null, details: { grant_id: row.id, role_id: roleId, expires_at: row.expires_at } });
  return grantRow(row);
});

route('POST', '/api/roles/grants/:id/extend', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const row = state.grants.find((one) => String(one.id) === context.params.id);
  if (!row) throw new Refused(404, 'no_such_grant', NO_SUCH_GRANT);
  if (row.removed_at) throw new Refused(409, 'already_ended', ALREADY_ENDED);
  if (!row.expires_at) throw new Refused(409, 'no_end_date', NO_END_DATE);
  if (body.days === undefined || body.days === null || body.days === '') {
    throw new Refused(400, 'no_days', DAYS_NEEDED);
  }
  const days = Math.max(1, wantedDays(body.days, 'days') || 1);
  row.expires_at = new Date(new Date(row.expires_at).getTime() + days * 86400000).toISOString();
  logAction('web.role.extended', { target_id: row.user_id, details: { grant_id: row.id, role_id: row.role_id, expires_at: row.expires_at } });
  return grantRow(row);
});

route('DELETE', '/api/roles/grants/:id', (context) => {
  requireStaff(context.session);
  const row = state.grants.find((one) => String(one.id) === context.params.id);
  if (!row) throw new Refused(404, 'no_such_grant', NO_SUCH_GRANT);
  if (row.removed_at) throw new Refused(409, 'already_ended', ALREADY_ENDED);
  row.removed_at = now();
  row.removed_reason = 'ended_by_staff';
  logAction('web.role.ended', { target_id: row.user_id, details: { grant_id: row.id, role_id: row.role_id } });
  return grantRow(row);
});

route('GET', '/api/golive/links', (context) => {
  requireStaff(context.session);
  return state.golive.links.map((link) => ({ user_id: String(link.user_id), user_name: memberName(link.user_id), twitch_login: link.twitch_login, twitch_user_id: link.twitch_user_id, linked_at: link.linked_at }));
});

route('DELETE', '/api/golive/links/:user_id', (context) => {
  requireStaff(context.session);
  const at = state.golive.links.findIndex((link) => link.user_id === context.params.user_id);
  if (at < 0) throw new Refused(404, 'no_link', 'That member has no Twitch link stored, so there was nothing to unlink.');
  state.golive.links.splice(at, 1);
  logAction('web.golive.unlink', { target_id: context.params.user_id });
  return { unlinked: true, user_id: context.params.user_id };
});

route('POST', '/api/golive/links', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const userId = String(body.user_id || '');
  const given = String(body.twitch_login || '');
  const login = given.trim().toLowerCase().replace(/^.*twitch\.tv\//, '').split(/[?/]/)[0].replace(/^@/, '');
  if (!userId) throw new Refused(400, 'bad_request', 'Pick the member this is about first.');
  if (!login || login.length > 25 || !/^[a-z0-9_]+$/.test(login)) {
    throw new Refused(400, 'bad_login', `**${given || 'nothing'}** is not a Twitch channel name Black Bloc can use, so nothing was linked. Give the name out of the channel's own address — letters, numbers and underscores, 25 at most.`);
  }
  const owner = state.golive.links.find((link) => link.twitch_login === login);
  if (owner && owner.user_id !== userId) {
    throw new Refused(409, 'link_taken', `**${login}** is already linked to another member here, so nothing was changed. A Twitch channel name can only belong to one member — if that channel is yours, ask a Lead to remove the other link first.`);
  }
  const row = { user_id: userId, twitch_login: login, twitch_user_id: null, linked_at: now() };
  const at = state.golive.links.findIndex((link) => link.user_id === userId);
  if (at >= 0) state.golive.links[at] = row;
  else state.golive.links.unshift(row);
  logAction('web.golive.link', { target_id: userId, details: { login } });
  return {
    user_id: userId,
    user_name: memberName(userId),
    twitch_login: login,
    twitch_user_id: null,
    linked_at: row.linked_at,
    checked: false,
    message: `**${memberName(userId) || userId}** is linked to twitch.tv/${login}. Black Bloc did not check that channel exists — it finds that out the first time it looks for a stream.`,
  };
});

route('GET', '/api/golive/optouts', (context) => {
  requireStaff(context.session);
  return state.golive.optouts.map((row) => ({ user_id: String(row.user_id), user_name: memberName(row.user_id), at: row.at }));
});

route('POST', '/api/golive/optouts', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const userId = String(body.user_id || '');
  if (!userId) throw new Refused(400, 'bad_request', 'Pick the member this is about first.');
  const at = state.golive.optouts.findIndex((row) => row.user_id === userId);
  const row = { user_id: userId, at: now() };
  if (at >= 0) state.golive.optouts[at] = row;
  else state.golive.optouts.unshift(row);
  logAction('web.golive.optout', { target_id: userId });
  return {
    user_id: userId,
    user_name: memberName(userId),
    opted_out: true,
    message: `**${memberName(userId) || userId}** is opted out, so no stream of theirs is announced from now on.`,
  };
});

route('DELETE', '/api/golive/optouts/:user_id', (context) => {
  requireStaff(context.session);
  const at = state.golive.optouts.findIndex((row) => row.user_id === context.params.user_id);
  if (at < 0) {
    throw new Refused(404, 'not_opted_out', `**${context.params.user_id}** was not opted out, so there was nothing to undo. The opt-outs table lists everyone who is.`);
  }
  state.golive.optouts.splice(at, 1);
  logAction('web.golive.optin', { target_id: context.params.user_id });
  return {
    user_id: context.params.user_id,
    user_name: memberName(context.params.user_id),
    opted_out: false,
    message: `**${memberName(context.params.user_id) || context.params.user_id}** is no longer opted out, so their streams can be announced again.`,
  };
});

route('GET', '/api/golive/sessions', (context) => {
  requireStaff(context.session);
  const limit = Math.max(1, Math.min(Number(context.url.searchParams.get('limit') || 50), 200));
  return state.golive.sessions.slice(0, limit).map((row) => ({
    user_id: String(row.user_id),
    user_name: memberName(row.user_id),
    id: row.id,
    source: row.source,
    url: row.url,
    game: row.game,
    title: row.title,
    started_at: row.started_at,
    ended_at: row.ended_at,
    mode: row.mode,
    announced_message_id: row.announced_message_id === null ? null : String(row.announced_message_id),
  }));
});

function eventRow(row) {
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    location: row.location,
    starts_at: row.starts_at,
    ends_at: row.ends_at,
    minutes: row.ends_at ? Math.round((Date.parse(row.ends_at) - Date.parse(row.starts_at)) / 60000) : null,
    status: row.status,
    requester_id: String(row.requester_id),
    requester_name: memberName(row.requester_id),
    decided_by_id: row.decided_by === null || row.decided_by === undefined ? null : String(row.decided_by),
    decided_by_name: memberName(row.decided_by),
    decided_at: row.decided_at,
    deny_reason: row.deny_reason,
    review_channel_id: row.review_channel_id === undefined ? null : row.review_channel_id,
    created_at: row.created_at,
  };
}

route('GET', '/api/events', (context) => {
  requireStaff(context.session);
  const status = context.url.searchParams.get('status');
  const wanted = String(status || '').split(',').filter(Boolean);
  const rows = wanted.length ? state.events.filter((event) => wanted.includes(event.status)) : state.events;
  return rows.map(eventRow);
});

function eventOf(id) {
  const found = state.events.find((event) => String(event.id) === String(id));
  if (!found) throw new Refused(404, 'no_event', 'That event is not in the queue any more — somebody may have decided it already.');
  return found;
}

route('POST', '/api/events/:id/approve', (context) => {
  requireStaff(context.session);
  const event = eventOf(context.params.id);
  if (event.status !== 'pending') {
    throw new Refused(409, 'already_decided', `That event is already ${event.status}, so it was left alone.`);
  }
  event.status = 'approved';
  event.decided_by = STAFF.id;
  event.decided_at = now();
  logAction('web.event.approved', { target_id: event.requester_id, details: { event_id: event.id } });
  return { event: eventRow(event), message: `“${event.title}” is approved.` };
});

route('POST', '/api/events/:id/deny', async (context) => {
  requireStaff(context.session);
  const event = eventOf(context.params.id);
  const body = await context.body();
  if (!String(body.reason || '').trim()) {
    throw new Refused(400, 'need_reason', 'Denying an event needs a reason — the person who asked is told what it says.');
  }
  if (event.status !== 'pending') {
    throw new Refused(409, 'already_decided', `That event is already ${event.status}, so it was left alone.`);
  }
  event.status = 'denied';
  event.deny_reason = body.reason;
  event.decided_by = STAFF.id;
  event.decided_at = now();
  logAction('web.event.denied', { target_id: event.requester_id, reason: body.reason, details: { event_id: event.id } });
  return { event: eventRow(event), message: `“${event.title}” is denied.` };
});

route('POST', '/api/events/:id/cancel', (context) => {
  requireStaff(context.session);
  const event = eventOf(context.params.id);
  if (event.status === 'cancelled') throw new Refused(409, 'already_decided', 'That event is already cancelled.');
  event.status = 'cancelled';
  event.decided_by = STAFF.id;
  event.decided_at = now();
  logAction('web.event.cancel', { target_id: event.requester_id, details: { event_id: event.id } });
  return { event: eventRow(event), message: 'Cancelled.' };
});

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function birthdayRow(row) {
  return {
    user_id: String(row.user_id),
    user_name: memberName(row.user_id),
    month: Number(row.month),
    day: Number(row.day),
    year: row.year ? Number(row.year) : null,
    when: `${MONTH_NAMES[Number(row.month) - 1]} ${Number(row.day)}`,
    opted_in: Boolean(row.opted_in),
    source: row.source,
    set_at: row.set_at,
    last_announced_on: row.last_announced_on ?? null,
  };
}

route('GET', '/api/birthdays', (context) => {
  requireStaff(context.session);
  return state.birthdays.map(birthdayRow);
});

route('PUT', '/api/birthdays/:user_id', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const month = Number(body.month);
  const day = Number(body.day);
  if (!(month >= 1 && month <= 12) || !(day >= 1 && day <= 31)) {
    throw new Refused(400, 'bad_value', 'That is not a date anybody has a birthday on — pick a month from 1 to 12 and a day that exists in it.');
  }
  const existing = state.birthdays.find((row) => row.user_id === context.params.user_id);
  const row = existing || { user_id: context.params.user_id, opted_in: true, source: 'web', set_at: now() };
  row.month = month;
  row.day = day;
  row.year = body.year ? Number(body.year) : null;
  row.set_at = now();
  if (!existing) state.birthdays.push(row);
  logAction('web.birthday.set', { target_id: row.user_id, details: { month, day, year: row.year } });
  return birthdayRow(row);
});

route('POST', '/api/birthdays/:user_id/optin', async (context) => {
  requireStaff(context.session);
  const row = state.birthdays.find((one) => one.user_id === context.params.user_id);
  if (!row) throw new Refused(404, 'no_birthday', `Black Bloc has no birthday stored for **${context.params.user_id}**, so there was nothing to change.`);
  const body = await context.body();
  row.opted_in = body.opted_in !== false;
  logAction('web.birthday.optin', { target_id: row.user_id, details: { opted_in: row.opted_in } });
  const name = memberName(row.user_id) || row.user_id;
  return {
    ...birthdayRow(row),
    message: row.opted_in
      ? `**${name}** gets a birthday wish again.`
      : `**${name}** is opted out, so Black Bloc says nothing on their birthday.`,
  };
});

route('DELETE', '/api/birthdays/:user_id', (context) => {
  requireStaff(context.session);
  const at = state.birthdays.findIndex((row) => row.user_id === context.params.user_id);
  if (at < 0) throw new Refused(404, 'no_birthday', 'That member has no birthday stored, so there was nothing to remove.');
  state.birthdays.splice(at, 1);
  logAction('web.birthday.clear', { target_id: context.params.user_id });
  return { removed: true, user_id: context.params.user_id };
});

route('POST', '/api/birthdays/import', (context) => {
  requireStaff(context.session);
  const searched = MEMBERS.length;
  const asOf = 2026;
  const report = {
    imported: ['Dax — March 3 → <@700000000000000007>'],
    already: ['Casey — February 14 → <@700000000000000002> (kept the self entry)'],
    ambiguous: ['moth — June 1 → Moth, moth_light'],
    not_found: ['someonewholeft — August 9'],
  };
  const counts = Object.fromEntries(Object.entries(report).map(([key, value]) => [key, value.length]));
  logAction('web.birthday.import', { details: counts });
  return {
    counts,
    searched,
    as_of_year: asOf,
    report,
    notes: [
      `**${counts.imported} imported** · ${counts.already} already stored · ${counts.ambiguous} ambiguous · ${counts.not_found} not found`,
      `Matched against the **${searched}** members Black Bloc can see in this server.`,
    ],
  };
});

route('GET', '/api/tempvoice/channels', (context) => {
  requireStaff(context.session);
  return state.tempvoice.map((row) => {
    const live = CHANNELS.find((channel) => channel.id === String(row.channel_id)) || null;
    return {
      channel_id: String(row.channel_id),
      name: live ? live.name : null,
      gone: live === null,
      owner_id: String(row.owner_id),
      owner_name: memberName(row.owner_id),
      creator_id: String(row.creator_id),
      created_at: row.created_at,
      connected: row.connected ?? 0,
    };
  });
});

route('POST', '/api/tempvoice/setup', (context) => {
  requireStaff(context.session);
  guard('creating the join-to-create channel');
  logAction('web.tempvoice.setup', { details: { name: null } });
  return {
    created: true,
    outcome: 'repaired',
    message: 'Black Bloc repaired the join-to-create channel it already had — <#800000000000000009> — instead of making a second one.',
  };
});

route('POST', '/api/tempvoice/forget', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const wanted = String(body.channel_id || '');
  const ids = (state.settings.get('tempvoice_creator_ids') || []).map(String);
  if (!ids.includes(wanted)) {
    throw new Refused(404, 'not_a_lobby', `**${wanted}** is not one of Black Bloc's join-to-create channels, so nothing was forgotten. \`/tempvoice status\` lists the ones it knows about.`);
  }
  state.settings.set('tempvoice_creator_ids', ids.filter((id) => id !== wanted));
  logAction('web.tempvoice.forget', { target_id: wanted });
  return {
    forgotten: true,
    channel_id: wanted,
    message: `Black Bloc has forgotten **${wanted}** — joining it no longer makes anybody a temporary channel.`,
  };
});

route('GET', '/api/honeypot/hits', (context) => {
  requireStaff(context.session);
  const limit = Math.max(1, Math.min(Number(context.url.searchParams.get('limit') || 50), 200));
  return state.honeypot.slice(0, limit).map((row) => ({
    id: row.id,
    user_id: String(row.user_id),
    user_name: memberName(row.user_id),
    channel_id: String(row.channel_id),
    channel_name: memberName(row.channel_id),
    message_id: row.message_id === null ? null : String(row.message_id),
    content: row.content,
    at: row.at,
    mode: row.mode,
    action: row.action,
  }));
});

route('POST', '/api/honeypot/hits/:id/ban', (context) => {
  requireStaff(context.session);
  const hit = state.honeypot.find((row) => String(row.id) === String(context.params.id));
  if (!hit) throw new Refused(404, 'no_hit', 'That honeypot hit is not on file any more.');
  guard('banning from a honeypot hit');
  hit.action = 'banned';
  logAction('web.honeypot.ban', { target_id: hit.user_id, details: { hit_id: hit.id } });
  return { banned: true, hit_id: hit.id, message: `Banned <@${hit.user_id}> and purged their recent messages.` };
});

route('POST', '/api/honeypot/setup', (context) => {
  requireStaff(context.session);
  guard('creating the trap channel');
  logAction('web.honeypot.setup', { details: { name: null } });
  return { created: true, message: '**free-nitro-here** is ready — <#800000000000000007>. Nobody but Black Bloc can post in it.' };
});

function caseRow(row) {
  return {
    id: row.id,
    kind: row.kind,
    user_id: row.user_id === null || row.user_id === undefined ? null : String(row.user_id),
    user_name: memberName(row.user_id),
    moderator_id: row.moderator_id === null || row.moderator_id === undefined ? null : String(row.moderator_id),
    moderator_name: memberName(row.moderator_id),
    reason: row.reason,
    duration_s: row.duration_s ?? null,
    at: row.at,
    mode: row.mode,
    applied: Boolean(row.applied),
    actions: row.actions || [],
    done: row.done || [],
    failed: row.failed || [],
    channel_id: row.channel_id === undefined || row.channel_id === null ? null : String(row.channel_id),
  };
}

route('GET', '/api/mod/cases', (context) => {
  requireStaff(context.session);
  const userId = context.url.searchParams.get('user_id');
  const page = Math.max(1, Number(context.url.searchParams.get('page') || 1));
  const size = 10;
  const rows = userId ? state.cases.filter((row) => row.user_id === userId) : state.cases;
  const slice = rows.slice((page - 1) * size, page * size);
  return {
    cases: slice.map(caseRow),
    total: rows.length,
    page,
    pages: Math.max(1, Math.ceil(rows.length / size)),
    per_page: size,
  };
});

route('GET', '/api/mod/cases/:id', (context) => {
  requireStaff(context.session);
  const found = state.cases.find((row) => String(row.id) === String(context.params.id));
  if (!found) throw new Refused(404, 'no_case', 'There is no case with that number.');
  return caseRow(found);
});

route('POST', '/api/mod/cases/:id/apply', (context) => {
  requireStaff(context.session);
  const found = state.cases.find((row) => String(row.id) === String(context.params.id));
  if (!found) throw new Refused(404, 'no_case', 'There is no case with that number.');
  if (found.applied) throw new Refused(409, 'already_applied', 'That case has already been applied, so nothing was done twice.');
  guard('applying a shadow case');
  found.applied = true;
  found.done = found.actions;
  logAction('web.mod.apply', { target_id: found.user_id, details: { case_id: found.id } });
  return { applied: true, case_id: found.id, message: `Case ${found.id} was carried out: ${found.done.join(', ')}.` };
});

const MOD_ACTIONS = ['warn', 'timeout', 'untimeout', 'kick', 'ban', 'unban'];

for (const action of MOD_ACTIONS) {
  route('POST', `/api/mod/${action}`, async (context) => {
    requireStaff(context.session);
    const body = await context.body();
    if (!body.user_id) throw new Refused(400, 'bad_value', 'Pick the member this is about first.');
    if (!String(body.reason || '').trim()) {
      throw new Refused(400, 'need_reason', 'Every mod action needs a reason: it goes in the case, the log and the member’s DM.');
    }
    if (action === 'timeout' && !body.duration) {
      throw new Refused(400, 'need_duration', 'A timeout needs a length, or nothing would happen.');
    }
    if (action !== 'warn') guard(`${action} from the dashboard`);
    const row = {
      id: state.nextCase++,
      user_id: String(body.user_id),
      kind: action,
      moderator_id: STAFF.id,
      reason: body.reason,
      duration_s: body.duration ? Number(body.duration) : null,
      at: now(),
      mode: 'on',
      applied: true,
      actions: [action],
      done: [action],
      failed: [],
    };
    state.cases.unshift(row);
    logAction(`web.mod.${action}`, { target_id: row.user_id, reason: row.reason });
    return {
      done: true,
      kind: action,
      user_id: row.user_id,
      message: `${memberName(row.user_id) || row.user_id} — ${action} done, case ${row.id}.`,
    };
  });
}

route('GET', '/api/mod/rules', (context) => {
  requireStaff(context.session);
  return Object.entries(state.rules).map(([name, rule]) => ({ name, help: RULE_HELP[name] || '', ...rule }));
});

route('PUT', '/api/mod/rules/:name', async (context) => {
  requireStaff(context.session);
  const rule = state.rules[context.params.name];
  if (!rule) throw new Refused(404, 'no_rule', `Automod has no rule called ${context.params.name}.`);
  const body = await context.body();
  if (body.window_s !== undefined && Number(body.window_s) > 3600) {
    throw new Refused(400, 'bad_value', 'A window longer than an hour is not a burst any more; 3600 seconds is the most automod will watch.');
  }
  if (body.timeout_s !== undefined && Number(body.timeout_s) > 28 * 24 * 3600) {
    throw new Refused(400, 'bad_value', 'Discord refuses a timeout longer than 28 days, so that would fail every time it fired.');
  }
  for (const key of ['enabled', 'window_s', 'threshold', 'actions', 'timeout_s', 'words']) {
    if (body[key] !== undefined) rule[key] = body[key];
  }
  logAction('web.mod.rule', { reason: context.params.name, details: { rule: context.params.name } });
  return { name: context.params.name, help: RULE_HELP[context.params.name] || '', ...rule };
});

function ticketRow(ticket) {
  return {
    id: ticket.id,
    user_id: String(ticket.user_id),
    user_name: memberName(ticket.user_id),
    mode: ticket.mode,
    status: ticket.status,
    channel_id: ticket.channel_id === null ? null : String(ticket.channel_id),
    thread_id: ticket.thread_id === null ? null : String(ticket.thread_id),
    opened_at: ticket.opened_at,
    closed_at: ticket.closed_at,
    closed_by_id: ticket.closed_by === null || ticket.closed_by === undefined ? null : String(ticket.closed_by),
    closed_by_name: memberName(ticket.closed_by),
    close_reason: ticket.close_reason,
  };
}

function messageRow(message) {
  return {
    id: message.id,
    at: message.at,
    author_id: String(message.author_id),
    author_name: memberName(message.author_id),
    direction: message.direction,
    anonymous: Boolean(message.anonymous),
    content: message.content,
    attachments: message.attachments || [],
    delivered: Boolean(message.delivered),
  };
}

route('GET', '/api/modmail/tickets', (context) => {
  requireStaff(context.session);
  const status = context.url.searchParams.get('status');
  const rows = status ? state.tickets.filter((ticket) => ticket.status === status) : state.tickets;
  return rows.map(ticketRow);
});

function ticketOf(id) {
  const found = state.tickets.find((ticket) => String(ticket.id) === String(id));
  if (!found) throw new Refused(404, 'no_ticket', 'There is no ticket with that number.');
  return found;
}

route('GET', '/api/modmail/tickets/:id', (context) => {
  requireStaff(context.session);
  const ticket = ticketOf(context.params.id);
  return { ...ticketRow(ticket), messages: (state.messages[ticket.id] || []).map(messageRow) };
});

route('POST', '/api/modmail/tickets/:id/reply', async (context) => {
  requireStaff(context.session);
  const ticket = ticketOf(context.params.id);
  const body = await context.body();
  if (!String(body.text || '').trim()) throw new Refused(400, 'bad_value', 'An empty reply would tell them nothing.');
  if (ticket.status !== 'open') throw new Refused(409, 'closed', 'That ticket is closed, so the member would never see the reply.');
  const message = {
    id: state.nextMessage++,
    at: now(),
    author_id: STAFF.id,
    direction: 'out',
    anonymous: Boolean(body.anonymous),
    content: body.text,
    attachments: [],
    delivered: true,
  };
  state.messages[ticket.id] = (state.messages[ticket.id] || []).concat([message]);
  logAction('web.modmail.reply', { target_id: ticket.user_id, details: { ticket_id: ticket.id, anonymous: message.anonymous, delivered: true } });
  return { sent: true, ticket_id: ticket.id, message: 'Sent.' };
});

route('POST', '/api/modmail/tickets/:id/close', async (context) => {
  requireStaff(context.session);
  const ticket = ticketOf(context.params.id);
  const body = await context.body();
  if (ticket.status !== 'open') throw new Refused(409, 'closed', 'That ticket is already closed.');
  guard('closing a modmail ticket');
  ticket.status = 'closed';
  ticket.closed_at = now();
  ticket.closed_by = STAFF.id;
  ticket.close_reason = body.reason || null;
  logAction('web.modmail.close', { target_id: ticket.user_id, reason: ticket.close_reason, details: { ticket_id: ticket.id, silent: Boolean(body.silent) } });
  return { closed: true, ticket: ticketRow(ticket), transcript: true };
});

route('GET', '/api/modmail/snippets', (context) => {
  requireStaff(context.session);
  return state.snippets.map((row) => ({
    name: row.name,
    content: row.content,
    by_id: row.by === null || row.by === undefined ? null : String(row.by),
    by_name: memberName(row.by),
    at: row.at,
  }));
});

route('POST', '/api/modmail/snippets', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const name = String(body.name || '').trim();
  if (!name || !String(body.content || '').trim()) {
    throw new Refused(400, 'bad_value', 'A snippet needs a name and something to say.');
  }
  const existing = state.snippets.find((row) => row.name === name);
  if (existing) existing.content = body.content;
  else state.snippets.unshift({ name, content: body.content, by: STAFF.id, at: now() });
  logAction('web.modmail.snippet', { reason: name, details: { name } });
  return { saved: true, name, content: body.content };
});

route('DELETE', '/api/modmail/snippets/:name', (context) => {
  requireStaff(context.session);
  const at = state.snippets.findIndex((row) => row.name === context.params.name);
  if (at < 0) throw new Refused(404, 'no_snippet', `There is no snippet called ${context.params.name}.`);
  state.snippets.splice(at, 1);
  logAction('web.modmail.snippet_remove', { reason: context.params.name, details: { name: context.params.name } });
  return { removed: true, name: context.params.name };
});

route('GET', '/api/modmail/blocks', (context) => {
  requireStaff(context.session);
  return state.blocks.map((row) => ({
    user_id: String(row.user_id),
    user_name: memberName(row.user_id),
    by_id: row.by === null || row.by === undefined ? null : String(row.by),
    by_name: memberName(row.by),
    reason: row.reason,
    at: row.at,
  }));
});

route('POST', '/api/modmail/blocks', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  if (!body.user_id) throw new Refused(400, 'bad_value', 'Pick the member to block first.');
  const row = { user_id: String(body.user_id), by: STAFF.id, reason: body.reason || null, at: now() };
  const at = state.blocks.findIndex((entry) => entry.user_id === row.user_id);
  if (at >= 0) state.blocks[at] = row;
  else state.blocks.unshift(row);
  logAction('web.modmail.block', { target_id: row.user_id, reason: row.reason });
  return { blocked: true, user_id: row.user_id };
});

route('DELETE', '/api/modmail/blocks/:user_id', (context) => {
  requireStaff(context.session);
  const at = state.blocks.findIndex((row) => row.user_id === context.params.user_id);
  if (at >= 0) state.blocks.splice(at, 1);
  logAction('web.modmail.unblock', { target_id: context.params.user_id });
  return { unblocked: true, user_id: context.params.user_id };
});

function send(response, status, body, headers = {}) {
  const payload = body === null ? '' : JSON.stringify(body);
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    ...headers,
  });
  response.end(payload);
}

async function serveStatic(request, response, path, asked) {
  const wanted = path === '/' ? '/index.html' : path;
  const cookie = asked ? { 'set-cookie': `mock_as=${asked}; Path=/; SameSite=Lax` } : {};
  const target = join(PUBLIC, normalize(wanted).replace(/^([/\\])+/, ''));
  if (!target.startsWith(PUBLIC)) {
    response.writeHead(403, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('outside the site directory');
    return;
  }
  try {
    const info = await stat(target);
    if (info.isDirectory()) throw new Error('directory');
    const html = extname(target) === '.html';
    const body = html ? stamp(await readFile(target, 'utf8')) : await readFile(target);
    response.writeHead(200, {
      'content-type': TYPES[extname(target)] || 'application/octet-stream',
      'cache-control': html ? NO_STORE : REVALIDATE,
      ...cookie,
    });
    response.end(body);
  } catch (e) {
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    response.end(`no such file: ${wanted}`);
  }
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url, `http://${request.headers.host || 'localhost'}`);
  const path = url.pathname;

  if (!path.startsWith('/api/')) {
    await serveStatic(request, response, path, url.searchParams.get('as'));
    return;
  }

  const session = sessionOf(request, url);
  const setCookie = url.searchParams.get('as') ? { 'set-cookie': `mock_as=${session}; Path=/; SameSite=Lax` } : {};

  for (const entry of ROUTES) {
    if (entry.method !== request.method) continue;
    const params = match(entry.pattern, path);
    if (params === null) continue;
    try {
      const found = await entry.handler({
        params,
        url,
        session,
        body: () => readBody(request),
      });
      if (found && typeof found === 'object' && 'status' in found && 'body' in found) {
        send(response, found.status, found.body, { ...setCookie, ...(found.headers || {}) });
      } else {
        send(response, 200, found, setCookie);
      }
    } catch (error) {
      if (error instanceof Refused) {
        send(response, error.status, { error: error.error, message: error.message }, setCookie);
      } else {
        send(response, 500, { error: 'mock_broke', message: `The mock server threw: ${error.message}` }, setCookie);
      }
    }
    return;
  }

  send(response, 404, { error: 'no_route', message: `${UNKNOWN_ROUTE} (${request.method} ${path})` });
});

server.listen(PORT, () => {
  process.stdout.write(`mock: http://127.0.0.1:${PORT} serving ${PUBLIC}\n`);
  process.stdout.write(`mock: TEST_MODE ${testMode ? 'on (destructive writes refuse with 409)' : 'off'}\n`);
});
