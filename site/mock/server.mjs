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
const MEMBER_NOT_STAFF = 'The rest of this dashboard is for the mods and admins of Black in a Flash!, but you are a member here, so you can still file a request and follow your own. Ask a Lead for a staff role if you need the rest.';
const ROLE_MENUS_OFF = 'Role menus are turned off right now, so nothing was changed. A Lead can turn them back on from the dashboard\'s Role menus tab, or with `/settings` ▸ **Turn a feature back on…**.';
const TEST_CHANNEL_NAME = 'blackbloc-logs';
const GUARD = `TEST MODE is on, so Black Bloc refuses to act outside #${TEST_CHANNEL_NAME}. Nothing was done. Ask the owner to lift the test guard first.`;
const UNKNOWN_ROUTE = 'This dashboard asked Black Bloc for something it does not serve. That is a fault in the page, not a problem with your access.';

const now = () => new Date().toISOString();
const minutesAgo = (m) => new Date(Date.now() - m * 60000).toISOString();
const daysAhead = (d) => new Date(Date.now() + d * 86400000).toISOString();
// A due date is a DAY, not an instant: it travels as YYYY-MM-DD, built from the local
// clock so the day named here is the day the page prints back.
const dayAhead = (d) => {
  const at = new Date(Date.now() + d * 86400000);
  return `${at.getFullYear()}-${String(at.getMonth() + 1).padStart(2, '0')}-${String(at.getDate()).padStart(2, '0')}`;
};

const MINUTES_NO_SUCH = 'There is no meeting **#{meeting_id}** on this server, so nothing was done. It may have been deleted — open the Minutes page and pick one from the list.';
const MINUTES_STILL_RECORDING = 'Meeting **#{meeting_id}** is still being recorded, so there are no notes to work with yet. Press **Stop** on `/minutes` first.';
const MINUTES_ARE_OFF = 'Meeting minutes are off for this server, so `/minutes` is hidden and Start refuses in words. This is a prototype and it ships off on purpose. Every meeting already recorded is kept — a Lead turns it on from the Settings page under **events**.';
const MINUTES_TEST_MODE = 'Black Bloc is in test mode, so a meeting’s announcement and its notes land in #blackbloc-logs rather than the channel they name. **Post again** obeys the same rule.';
const MINUTES_BLANK = 'Notes cannot be empty, so nothing was saved. Write something, or press **Delete** if this meeting should not be kept at all.';
const MINUTES_TOO_LONG = 'Notes hold 4000 characters and those are {count}, so nothing was saved. Take {over} character(s) out.';
const MINUTES_NOTHING_HEARD = 'Nobody said anything Black Bloc could make out, so there is no transcript and no notes were written. The meeting is still on the Minutes page with nothing in it.';
const MINUTES_NOTES_MAX = 4000;
const MINUTES_SEED_NOTES = '**In short**\nThe meeting-minutes prototype ships off and is tested by staff only.\n\n**Decisions**\n- Nobody turns it on until it has been tested.\n\n**Action items**\n- Casey: write the guide.\n\n**Left open**\n- Which channel the notes should land in once it is on.';

const POST_SEED_BODY = "Welcome to** Black in a Flash**, a dedicated space for Black gamers!  While we appreciate and see multiple teams around the content creation space we don't see one that is just for us, and that is what this Discord hopes to alleviate: the creation of a space where we can authentically and openly be ourselves.\n# Familiarize yourselves with the rules before you join the discord.\n**Failure to comply with the rules may lead to moderator action.**\n\n***1. The moderation team reserve the right to remove anyone from the space.***\n> If you cannot abide the rules or plainly speaking are not a good fit for the space, the moderators can remove you at will.\n\n***2. Be respectful of others.***\n> We will not tolerate any forms of harassment or bigotry, such as- but not limited to- harassment about race, gender/identity expression, sexual orientation, religion, disability, physical appearances. There's a line between a friendly roast and being a jerk.\n\n***3. First and foremost, this space is to adapt, learn, and grow.***\n> Let's try to keep that as the primary focus. It's okay to have off topic conversations or to be upset about things, but this is a space to empower ourselves. If you are going to detract from the experience of others, there may be moderator intervention.\n\nYou can head to the landing channel and type a message so you gain access to the rest of the discord. If you are unsure of something, you are welcome to ping the Aunties / Uncles role.";

const ROLES = [
  { id: '900000000000000001', name: 'Aunties / Uncles', color: '#e04a6d', position: 12, managed: false },
  { id: '900000000000000002', name: 'Leads', color: '#4eefff', position: 14, managed: false },
  { id: '900000000000000003', name: 'Live now', color: '#a35bff', position: 5, managed: false },
  { id: '900000000000000004', name: 'Birthday', color: '#ffd166', position: 4, managed: false },
  { id: '900000000000000005', name: 'Members', color: '#8a8f98', position: 1, managed: false },
  { id: '900000000000000006', name: 'Server Booster', color: '#f47fff', position: 9, managed: true },
  { id: '900000000000000007', name: 'Events', color: '#8a8f98', position: 2, managed: false },
  { id: '900000000000000008', name: 'Casey pings', color: '#8a8f98', position: 3, managed: false },
];

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null, position: 0 },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null, position: 1 },
  { id: '800000000000000003', name: TEST_CHANNEL_NAME, type: 'text', category_id: null, position: 2 },
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
const EVENTS_ROLE_ID = '900000000000000007';
// The second is deliberately NOT in ROLES: a fan role somebody deleted by hand, so the Pings
// table has a row whose follower count is null rather than 0.
const FAN_ROLE_IDS = ['900000000000000008', '900000000000000009'];

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
          ? [STAFF_ROLE_IDS[1], LIVE_ROLE_ID, MEMBER_ROLE_ID, FAN_ROLE_IDS[0]]
          : at === 3
            ? [MEMBER_ROLE_ID, FAN_ROLE_IDS[0], EVENTS_ROLE_ID]
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

// Mirrors black_bloc/logkinds.py. The mock only needs enough of it to sort and
// mark its own seed rows; the router is the truth and test_logkinds.py guards it.
const KIND_HEADS = {
  settings: 'core', commands: 'core', presence: 'core',
  automod: 'automod', honeypot: 'honeypot', mod: 'mod', case: 'mod',
  modmail: 'modmail', golive: 'golive', youtube: 'youtube',
  event: 'events', events: 'events',
  birthday: 'birthday', tempvoice: 'tempvoice',
  role: 'rolemenu', role_menu: 'rolemenu', rolemenu: 'rolemenu',
  poll: 'poll', chat: 'chat', request: 'request', requests: 'request',
  pings: 'pings', raidtrain: 'raidtrain',
  application: 'applications', applications: 'applications',
  selftest: 'selftest',
};
// Mirrors black_bloc/logkinds.py:HIDDEN_BY_DEFAULT — the Logs page's unfiltered view
// leaves these out, and the Test chip is the only way to them.
const HIDDEN_BY_DEFAULT = ['selftest'];
const IMPORTANT_SUFFIXES = [
  '_failed', '.approved', '.denied', '.expired', '.warned', '.timed_out', '.timeout',
  '.kicked', '.kick', '.banned', '.ban', '.granted', '.ended', '.removed', '.purged',
  '.blocked', '.closed',
];
const IMPORTANT_KINDS = [
  'automod.deleted', 'mod.warn', 'mod.unbanned', 'mod.untimed_out',
  'event.where_channel_gone',
  'request.declined', 'request.done', 'request.hold',
  'chat.memory_forgot', 'chat.memory_optout',
];
const ROUTINE_KINDS = [
  'poll.closed', 'tempvoice.ban', 'tempvoice.kick', 'honeypot.ban',
  'request.filed', 'request.withdrawn', 'request.resumed',
  'request.notify_skipped_test_mode',
  'request.in_progress', 'request.updated', 'request.comment', 'request.check_asked',
  'chat.memory_distilled', 'chat.memory_expired', 'chat.memory_optin',
  'application.submitted', 'application.withdrawn', 'application.panel_posted',
  'application.form_created', 'application.form_updated', 'application.form_deleted',
  'application.question_changed', 'application.mode', 'application.removed',
  'selftest.started', 'selftest.check', 'selftest.finished', 'selftest.purged',
];

function bareKind(kind) {
  const text = String(kind || '');
  return text.startsWith('web.') ? text.slice(4) : text;
}

function featureOfKind(kind) {
  return KIND_HEADS[bareKind(kind).split('.')[0]] || 'core';
}

// The mock's copy of black_bloc/logkinds.py:via_of — what the writer recorded wins,
// and the `web.` head decides every row written before anybody recorded it.
const VIA_WORDS = { discord: 'Discord', website: 'Website', operator: 'Operator token', forum: 'A forum post' };
function viaOfKind(kind, details) {
  const said = String((details && details.via) || '').trim().toLowerCase();
  if (VIA_WORDS[said]) return said;
  return String(kind || '').startsWith('web.') ? 'website' : 'discord';
}

function isImportantKind(kind) {
  const text = bareKind(kind);
  if (text.includes('.would_')) return false;
  if (ROUTINE_KINDS.includes(text)) return false;
  if (IMPORTANT_KINDS.includes(text)) return true;
  return IMPORTANT_SUFFIXES.some((suffix) => text.endsWith(suffix));
}

// [feature namespace, the word the help uses, the slash group that shows its logs]
// Mirrors black_bloc/personas.py:TROPES — the eleven ported from GABI's
// personality.ts. `noir` ships switched off so the page has an off row to draw.
const TROPE_POOL = [
  ['peppy', 'peppy', 'You are BRIGHT and fast today — genuinely glad to have been asked. Short exclamations, visible delight in the question, quick to celebrate somebody’s good news.'],
  ['dramatic', 'dramatic', 'You are THEATRICAL today — grand pronouncements about small things, a flair for the reveal. The drama is in the framing; what you actually tell somebody stays plain.'],
  ['mischievous', 'mischievous', 'You are PLAYFUL today — light teasing, a raised eyebrow, enjoying yourself. Never mean, and never holding something back to be coy about it.'],
  ['flirty', 'flirty', 'You are CHARMING today, with a playful wink — light compliments, affectionate teasing. CHARM, NOT HEAT, and you never get flustered into dropping the answer.'],
  ['warm', 'warm', 'You are WARM today — familiar, unhurried, glad to see them. Kind without being saccharine.'],
  ['cozy', 'cozy', 'You are COSY today — the voice of a folding chair in the shade and a full plate. Calm rather than sleepy.'],
  ['shy', 'shy', 'You are a little SHY today — soft, hedging, apologetic about taking up room. BUT YOU STILL GIVE THE WHOLE ANSWER, first time.'],
  ['scholar', 'scholarly', 'You are SCHOLARLY today — precise, fond of getting a detail exactly right. Pedantic about accuracy, never about the person.'],
  ['noir', 'noir', 'You are HARD-BOILED today — clipped sentences, a little world-weary, everything faintly a metaphor about rain and long odds.'],
  ['deadpan', 'deadpan', 'You are DEADPAN today — flat, economical, dry. The joke is the flatness. Few words, all of them load-bearing.'],
  ['tsundere', 'tsundere', 'You are BRUSQUE today, and helping anyway — mildly put upon. THE GRUMBLING IS ALL SURFACE: you still answer fully and promptly.'],
];

const PERSONALITY_CHOICES = ['cookout', 'pool', ...TROPE_POOL.map(([name]) => name)];

const LOG_LEVEL_FEATURES = [
  ['core', 'core', null],
  ['automod', 'automod', 'automod'],
  ['honeypot', 'honeypot', 'honeypot'],
  ['mod', 'moderation', null],
  ['modmail', 'modmail', 'modmail'],
  ['golive', 'go-live', 'golive'],
  ['youtube', 'youtube', 'youtube'],
  ['events', 'events', 'event'],
  ['birthday', 'birthdays', 'birthday'],
  ['tempvoice', 'temp voice', 'voice'],
  ['rolemenu', 'role menus', 'rolemenu'],
  ['poll', 'polls', 'poll'],
  ['chat', 'chat', 'chat'],
  ['request', 'requests', 'request'],
  ['pings', 'ping roles', 'pingroles'],
  ['raidtrain', 'raid trains', 'raidtrains'],
  ['applications', 'applications', 'applications'],
  // F-G1: guides are edited on the website only, so there is no panel to name.
  ['guides', 'guides', null],
  ['posts', 'posts', 'posts'],
];

const SETTING_SPECS = [
  ['log_channel_id', 'channel', '800000000000000004', null, 'where Black Bloc posts what it did'],
  ['shadow_channel_id', 'channel', null, null, 'where every rehearsal goes while a feature is in shadow — the welcome post, the front door, the ticket button, polls; blank means the bot’s own log channel. Setting it is the deliberate act that lets test mode speak in that one channel as well, so pick a channel only the people reviewing can see'],
  ['rehearsal_note', 'text', 'Rehearsal — this is where it would go: {channel}', 'Rehearsal — this is where it would go: {channel}', 'the line the front door and the ticket button carry at the top of their rehearsal copy; {channel} is replaced with the channel the real one is aimed at. Blank leaves the copy with no note at all'],
  ['staff_channel_id', 'channel', '800000000000000005', null, 'the channel whose viewers count as staff'],
  ['role_menu_channel_id', 'channel', '800000000000000002', null, 'the channel /rolemenu offers first when a menu is posted'],
  ['golive_mode', 'enum', 'shadow', 'off', 'off, shadow (log only) or on (post go-live announcements)', ['off', 'shadow', 'on']],
  ['golive_channel_id', 'channel', '800000000000000006', null, 'where go-live announcements are posted'],
  ['golive_template', 'text', '{name} is live playing {game} — {title} {url}', '{name} is live: {url}', 'the announcement wording; {name} {game} {title} {url} {platform}'],
  ['golive_end_mode', 'enum', 'off', 'off', 'what happens to the announcement when the stream ends: off leaves it as posted, edit appends the ended wording and marks the card', ['off', 'edit']],
  ['golive_end_suffix', 'text', ' — stream ended', ' — stream ended', 'what is added to an announcement once the stream has ended; only used when golive_end_mode is edit'],
  ['golive_end_template', 'text', '**{name}** was streaming **{game}** — the stream has ended. {url}', '**{name}** was streaming **{game}** — the stream has ended. {url}', 'the whole announcement once the stream is over; {name} {game} {title} {url} {platform} {duration}; blank keeps the live sentence and appends golive_end_suffix as before'],
  ['golive_end_author', 'text', '{name} was live on {platform}', '{name} was live on {platform}', "the card's top line once the stream is over; {name} {platform} {duration}; blank keeps 'was live on'"],
  ['golive_end_keep_mention', 'bool', false, false, 'on keeps the role mention at the front of the edited announcement; off drops it — nobody is pinged by an edit either way'],
  ['golive_costream_mode', 'enum', 'on', 'on', 'on names both platforms in one announcement when somebody streaming on Twitch also goes live on YouTube (or the other way round) and edits the post that is already there; off holds the second platform back, as it did before', ['off', 'on']],
  ['golive_costream_template', 'text', '**{name}** is streaming on **{platform}** and **{also_platform}**! Watch on {platform}: {url} · also live on {also_platform}: {also_url}', '**{name}** is streaming on **{platform}** and **{also_platform}**! Watch on {platform}: {url} · also live on {also_platform}: {also_url}', 'the announcement wording while two platforms are live; {name} {game} {title} {url} {platform} {also_url} {also_platform}. Twitch is always written first and is the only link Discord previews — {also_url} is always posted with its preview suppressed'],
  ['golive_costream_author', 'text', '{name} is live on {platform} and {also_platform}', '{name} is live on {platform} and {also_platform}', "the card's top line while two platforms are live; {name} {game} {title} {url} {platform} {also_url} {also_platform}"],
  ['golive_live_role_id', 'role', '900000000000000003', null, 'role given while someone is streaming'],
  ['golive_require_role_id', 'role', null, null, 'only announce people who have this role'],
  ['golive_ignore_role_id', 'role', null, null, 'never announce people who have this role'],
  ['golive_cooldown_minutes', 'int', 60, 60, 'minutes before the same person is announced again'],
  ['golive_ping_role_id', 'role', null, null, 'role mentioned in front of every go-live announcement'],
  ['golive_max_session_hours', 'int', 12, 12, 'hours before a stream still marked live is closed anyway'],
  ['golive_panel_minutes', 'int', 10, 10, "minutes the /golive panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['pings_mode', 'enum', 'off', 'off', 'off, or on (members can opt in to go-live and event pings, and a streamer can have a role of their own that only their followers wear)', ['off', 'on']],
  ['pings_events_role_name', 'text', 'Events', 'Events', 'what **Set up the Events role** on `/pings` calls the one opt-in role for go-live and event pings when it has to make it; an existing role of that name is reused rather than duplicated'],
  ['pings_fan_role_creation', 'enum', 'follow', 'follow', 'when a streamer’s ping role is made: follow (the first person to follow them on `/pings` makes it, which is the default so a role exists only where somebody wants it), self (the streamer, with **Start my own ping role** on `/pings`), staff (only an Auntie/Uncle, from `/pings` ▸ **Streamers…**), or auto (one is made the moment a Twitch channel is linked). Staff can always do it for anybody, whichever this says', ['self', 'staff', 'auto', 'follow']],
  ['pings_fan_role_template', 'text', '{name} pings', '{name} pings', 'what a streamer’s own ping role is called; {name} is their display name at the moment the role is made and is the only field there is'],
  ['pings_fan_role_on_unlink', 'enum', 'keep', 'keep', 'what happens to a streamer’s ping role when they unlink Twitch or opt out of announcements: keep leaves it alone (nothing is announced, so nobody is pinged), delete takes the role off the server', ['keep', 'delete']],
  ['pings_fan_role_delete', 'bool', true, true, 'true to delete the Discord role itself when a streamer’s ping role is removed; false forgets the role here and leaves it on the server for somebody to tidy by hand'],
  ['pings_streamer_stale_days', 'int', 90, 90, 'days without a go-live before somebody leaves the streamer list `/pings` ▸ **Follow a streamer…** offers; their ping role is kept while anybody still wears it, and one more go-live puts them back on', null, 365, 7],
  ['pings_empty_role_days', 'int', 30, 30, 'days a streamer’s ping role that nobody wears survives before Black Bloc deletes it, so the server’s role count tracks who is actually followed; a role somebody wears is never deleted by this', null, 365, 1],
  ['pings_onboarding_managed', 'bool', true, true, 'true to let Black Bloc keep its two Discord onboarding prompts in step with the Events, raid-train and streamer roles; false leaves the prompts exactly as they are and Black Bloc never writes to onboarding again. Only does anything on a Community server'],
  ['pings_onboarding_prompt_title', 'text', 'What should ping you?', 'What should ping you?', 'what Black Bloc’s first onboarding prompt is called; it is also how Black Bloc knows which prompts are its own, so changing it makes a fresh pair and leaves the old ones for somebody to delete by hand'],
  ['pings_onboarding_option_cap', 'int', 25, 25, 'how many streamers the **Which streamers?** onboarding prompt lists before it says how many more are on `/pings`. Discord publishes no number for this, so 25 is Black Bloc’s own conservative cap — raise it and Discord refuses in words if it is too high', null, 50, 1],
  ['tempvoice_mode', 'enum', 'on', 'off', 'off, shadow (join-to-create works, but only staff can see the lobby — the rooms it spawns follow it), or on (the lobby is visible to whoever its category shows)', ['off', 'shadow', 'on']],
  ['tempvoice_creator_ids', 'channels', ['800000000000000009'], [], 'the join-to-create channels; Setup on /voice fills this in'],
  ['tempvoice_name_template', 'text', "{user}'s room", "{user}'s room", 'what a spawned channel is called; {user} is the member'],
  ['tempvoice_creator_name', 'text', 'join to create a channel', 'join to create a channel', 'what the join-to-create channel is called'],
  ['tempvoice_allowed_role_id', 'role', null, null, 'only members with this role get a temporary channel'],
  ['tempvoice_room_overwrites', 'enum', 'lobby', 'lobby', "what a new room's permissions start from: lobby (the join-to-create channel's own — a staff-only lobby makes staff-only rooms) or category (the category's, as before)", ['lobby', 'category']],
  ['honeypot_mode', 'enum', 'shadow', 'off', 'off, shadow (log only) or on (ban whoever posts in the trap)', ['off', 'shadow', 'on']],
  ['honeypot_channel_ids', 'channels', ['800000000000000007'], [], 'the trap channels; Setup… on /honeypot fills this in'],
  ['honeypot_purge_days', 'int', 1, 1, 'days of the banned account’s messages to delete with it, 0 to 7', null, 7],
  ['honeypot_exempt_role_ids', 'roles', ['900000000000000001'], [], 'roles the trap ignores; staff are always ignored too'],
  ['events_mode', 'enum', 'on', 'off', 'off, shadow (no public announcement) or on (announce approved events)', ['off', 'shadow', 'on']],
  ['events_category_id', 'channel', '800000000000000008', null, 'the category review channels are made in'],
  ['events_announce_channel_id', 'channel', '800000000000000006', null, 'where an approved event is announced'],
  ['events_ping_role_id', 'role', null, null, 'role mentioned when an event is announced and when it starts'],
  ['events_create_scheduled', 'bool', true, false, 'true to make a real Discord scheduled event when one is approved'],
  ['events_where_link_in_description', 'bool', true, true, "true to put the link or note typed beside a channel at the end of the Discord scheduled event's description"],
  ['events_where_link_aliases', 'text', 'ttv=https://twitch.tv/{handle}, yt=https://youtube.com/@{handle}', 'ttv=https://twitch.tv/{handle}, yt=https://youtube.com/@{handle}', 'the shorthands the Where box turns into links, alias=https://host/{handle} entries separated by commas, up to 32 of them'],
  ['events_where_link_check', 'enum', 'warn', 'warn', 'whether a link typed into the Where box is opened once before it is kept: off, warn (kept either way, with a note) or refuse (the box says so in words)', ['off', 'warn', 'refuse']],
  ['events_where_link_check_seconds', 'int', 2, 2, 'seconds the link check waits for an answer, 1 to 3', null, 3, 1],
  ['events_where_hint', 'text', 'If you do not see your channel, start typing the channel name and it should appear.', 'If you do not see your channel, start typing the channel name and it should appear.', 'the sentence directly above the channel picker on the Where panel, and on the draft card while nothing is picked; empty shows no such line'],
  ['events_channel_retention_days', 'int', 7, 7, 'days a finished event’s channel is kept before deletion, 1 to 365', null, 365, 1],
  ['events_test_retention_minutes', 'int', 5, 5, 'minutes a finished or refused event’s review room is kept while Black Bloc is in test mode, 1 to 1440', null, 1440, 1],
  ['events_max_late_minutes', 'int', 30, 30, 'minutes an event may start late and still be announced', null, 1440],
  ['events_posts_where', 'enum', 'room', 'room', "where an approved event's posts go: room (the event's own review room), announce (only events_announce_channel_id), or both", ['room', 'announce', 'both']],
  ['events_room_delete_who', 'enum', 'staff', 'staff', 'who may press Delete this room: staff, or approver — the role in events_approver_role_id. Staff can always press it whichever this holds', ['staff', 'approver']],
  ['events_approver_role_id', 'role', null, null, 'the role Delete this room asks for when events_room_delete_who is approver; blank falls back to staff'],
  ['events_room_notice', 'bool', true, true, 'true to post the message carrying Delete this room in every review room Black Bloc makes'],
  ['events_review_mode', 'enum', 'room', 'room', 'where a proposed event is reviewed: room makes a text channel per event under events_category_id; forum makes one post per event in events_forum_channel_id (Make the forum on /event first)', ['room', 'forum']],
  ['events_forum_channel_id', 'channel', null, null, 'the forum channel every event is posted in, in forum mode; Make the forum on /event makes one under the BlackMail category'],
  ['events_moved_line', 'text', 'This event now lives in its own post: {post}. This room is being removed.', 'This event now lives in its own post: {post}. This room is being removed.', "the one line left in an event's old review room when staff press Move to the forum; {post} stands for the new post"],
  ['poll_mode', 'enum', 'on', 'on', 'off, shadow (every poll is posted for real, but into the log channel with a line saying why, so staff can rehearse), or on (polls go where they are pointed)', ['off', 'shadow', 'on']],
  ['poll_who_can_create', 'enum', 'staff', 'staff', 'who may run /poll create: staff, or everyone', ['staff', 'everyone']],
  ['poll_review_mode', 'enum', 'off', 'off', 'off posts a poll straight away; on holds it for a staff Approve or Deny first', ['off', 'on']],
  ['poll_default_hours', 'int', 24, 24, 'hours a poll stays open when nobody says otherwise, 1 to 768 (32 days)', null, 768, 1],
  ['poll_channel_id', 'channel', null, null, 'where a poll made from the dashboard goes'],
  ['poll_ping_role_id', 'role', null, null, 'role mentioned when a poll opens; blank pings nobody'],
  ['poll_reminder_minutes', 'int', 60, 60, 'minutes before a poll closes that Black Bloc posts a last call, 0 to say nothing', null, 10080],
  ['poll_auto_thread', 'bool', false, false, 'true to open a discussion thread under every poll'],
  ['poll_pin', 'bool', true, true, "true pins a poll's message while it is open and unpins it when it closes"],
  ['poll_shadow_note', 'text', 'Posted here because polls are in **shadow** — it would have gone to {channel}.', 'Posted here because polls are in **shadow** — it would have gone to {channel}.', 'the line above a poll posted in shadow; {channel} is where it would have gone'],
  ['poll_archive_days', 'int', 365, 365, 'days a closed poll stays on the list before it moves to the archive', null, 3650, 1],
  ['poll_archive_drop_votes', 'bool', true, true, 'true to forget who voted when a poll is archived; the totals are kept either way'],
  ['poll_date_labels', 'enum', 'plain', 'plain', "how a date poll writes its slots: plain (Sat 30 Aug · 7 pm, in the server's zone) or timestamp (each reader sees their own clock, if Discord renders one in an answer)", ['plain', 'timestamp']],
  ['birthday_mode', 'enum', 'shadow', 'off', 'off, shadow (log only) or on (post birthday wishes)', ['off', 'shadow', 'on']],
  ['birthday_channel_id', 'channel', '800000000000000002', null, 'where birthday wishes are posted'],
  ['birthday_template', 'text', 'Happy birthday {name}!', 'Happy birthday {name}!', 'the birthday wording; {name} and {age}'],
  ['birthday_color', 'color', '#4eefff', '#4eefff', 'the birthday embed’s colour, as a hex code like #4eefff'],
  ['birthday_role_id', 'role', '900000000000000004', null, 'role given for the day and taken back the next'],
  ['birthday_show_age', 'bool', false, false, 'true to put {age} in reach for people who stored a birth year'],
  ['modmail_enabled', 'bool', true, false, 'true when Black Bloc answers DMs'],
  ['modmail_mode', 'enum', 'thread', 'channel', 'channel (one channel per ticket), thread (private threads in the staff channel) or forum (one post per ticket in the forum channel — the list never grows past the forum’s own archive)', ['channel', 'thread', 'forum']],
  ['modmail_category_id', 'channel', '800000000000000011', null, 'the category ticket channels are made in, in channel mode'],
  ['modmail_staff_channel_id', 'channel', '800000000000000005', null, 'the channel ticket threads are made in, in thread mode'],
  ['modmail_log_channel_id', 'channel', '800000000000000004', null, 'where a closed ticket’s transcript is posted'],
  ['modmail_member_command', 'bool', true, true, 'true when anybody running /modmail gets the Open a ticket panel; false leaves /modmail to staff, as it was before, and a member’s only door is a DM'],
  ['modmail_panel_channel_id', 'channel', null, null, 'where the Open a ticket message with its button is posted; blank means no button is up anywhere. Post it from /modmail ▸ Setup… ▸ Ticket button…'],
  ['modmail_panel_message_id', 'text', null, null, 'the Open a ticket message Black Bloc posted, so it can be moved, taken down and put back after somebody deletes it. Written by the bot as TEXT, because a snowflake does not survive a JavaScript number; there is no reason to set it by hand'],
  ['modmail_panel_shadow_message_id', 'text', null, null, 'the rehearsal copy of the Open a ticket message Black Bloc posted in the rehearsal home while test mode refuses the real channel, so it can be kept current, moved with shadow_channel_id and taken down. Written by the bot as TEXT; there is no reason to set it by hand'],
  ['modmail_panel_shadow_hash', 'text', null, null, 'a fingerprint of the wording that rehearsal copy is showing, so a sweep edits it only when the heading or the line under it has actually changed. Written by the bot; there is no reason to set it by hand'],
  ['modmail_panel_title', 'text', 'Need a moderator?', 'Need a moderator?', 'the heading on the posted Open a ticket message'],
  ['modmail_panel_text', 'text', 'Press the button and tell us what is happening. Only staff see it.', 'Press the button and tell us what is happening. Only staff see it.', 'what the posted Open a ticket message says under its heading'],
  ['modmail_open_with_button', 'bool', false, false, 'true draws Open a ticket with… on the staff row of /modmail, so staff can start a ticket for somebody else; false hides that door and leaves every other way in untouched. The door is only hidden, never removed — turning this back on brings it straight back, and a press on a panel that was open when it went off is refused in words'],
  ['modmail_forum_channel_id', 'channel', null, null, 'the forum channel tickets are posted in, in forum mode; Setup on /modmail makes one under the ticket category'],
  ['modmail_forum_tags', 'bool', true, true, 'true keeps the open / closed tags on each ticket post in forum mode; false leaves every post untagged and the forum’s own tag list alone'],
  ['modmail_log_on_open', 'bool', true, true, "true posts a New-ticket card to the transcripts channel the moment a ticket opens (what the old ModMail bot's log did); false logs opens only in the action log"],
  ['modmail_panel_follows_post', 'text', 'welcome', 'welcome', 'the slug of the post the Open a ticket button sits under — welcome by default, so the button lands right after the rules and is put back there whenever that post is posted again. none never moves the button for that reason'],
  ['frontdoor_mode', 'enum', 'on', 'on', 'off hides /ask and takes the door down; shadow posts the rehearsal copy into shadow_channel_id with the rehearsal note and nothing into the real channel; on posts it where it is pointed. /ask answers in both shadow and on, and the three flows behind it (modmail, requests, events) keep their own modes whatever this says. In shadow the Open a ticket button follows the door while frontdoor_replaces_ticket_button is true', ['off', 'shadow', 'on']],
  ['frontdoor_channel_id', 'channel', null, null, 'where the front-door message is posted; blank posts nothing, and the /ask command still works. Post it from the Modmail page’s Front door card'],
  ['frontdoor_message_id', 'text', null, null, 'the front-door message Black Bloc posted, so it can be moved, taken down and put back after somebody deletes it. Written by the bot as TEXT, because a snowflake does not survive a JavaScript number; there is no reason to set it by hand'],
  ['frontdoor_shadow_message_id', 'text', null, null, 'the rehearsal copy of the front door Black Bloc posted in the rehearsal home while test mode refuses the real channel, so it can be kept current, moved with shadow_channel_id and taken down. Written by the bot as TEXT; there is no reason to set it by hand'],
  ['frontdoor_shadow_hash', 'text', null, null, 'a fingerprint of the wording the rehearsal copy is showing, so a sweep edits it only when the heading, the line or a button label has actually changed. Written by the bot; there is no reason to set it by hand'],
  ['frontdoor_title', 'text', 'Need something?', 'Need something?', 'the heading on the posted front-door message and on the /ask panel'],
  ['frontdoor_text', 'text', 'Pick the one that fits and Black Bloc takes it from there. Staff only see what you write.', 'Pick the one that fits and Black Bloc takes it from there. Staff only see what you write.', 'the line under that heading, on both'],
  ['frontdoor_ticket_label', 'text', 'Ask staff privately', 'Ask staff privately', 'what the button that opens a private modmail ticket is called, at most 80 characters, which is Discord’s own cap; blank restores the shipped wording'],
  ['frontdoor_request_label', 'text', 'Request something', 'Request something', 'what the button that files a request is called, at most 80 characters; blank restores the shipped wording'],
  ['frontdoor_event_label', 'text', 'Propose an event', 'Propose an event', 'what the button that starts an event proposal is called, at most 80 characters; blank restores the shipped wording'],
  ['frontdoor_follows_post', 'text', 'welcome', 'welcome', 'the slug of the post the front door sits directly under — welcome by default, so the door lands right after the rules and is put back there whenever that post is posted again. none never moves the door for that reason'],
  ['frontdoor_replaces_ticket_button', 'bool', true, true, 'true takes the posted Open-a-ticket message down while the front door is up in the same channel — one door per channel. modmail_panel_channel_id keeps its value, so moving the front door elsewhere or taking it down puts the ticket button back'],
  ['frontdoor_panel_minutes', 'int', 10, 10, "minutes the /ask panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['automod_mode', 'enum', 'shadow', 'off', 'off, shadow (log what it would do) or on (delete, warn and time out)', ['off', 'shadow', 'on']],
  ['automod_rules', 'json', null, null, 'the automod rule book; the Automod tab is what changes it'],
  ['automod_exempt_role_ids', 'roles', ['900000000000000001', '900000000000000002'], [], 'roles automod ignores'],
  ['automod_exempt_channel_ids', 'channels', ['800000000000000003'], [], 'channels automod never reads'],
  ['automod_warn_threshold', 'int', 8, 8, 'warnings before Black Bloc says so in the log, 0 to stop counting', null, 100],
  ['modlog_channel_id', 'channel', '800000000000000004', null, 'where mod cases are posted; defaults to log_channel_id'],
  ['mod_dm_on_action', 'enum', 'server_action_reason', 'server_action', 'what a punished member is told', ['none', 'server_action', 'server_action_reason']],
  ['rolemenu_approval_channel_id', 'channel', '800000000000000005', null, 'where a role request card is posted for staff to answer; defaults to staff_channel_id'],
  ['rolemenu_approver_role_id', 'role', null, null, 'role mentioned when a role request needs answering'],
  ['rolemenu_mode', 'enum', 'off', 'off', 'whether members can pick roles from the panels; off takes them down, on posts them again; /rolemenu itself stays either way', ['off', 'on']],
  ['chat_mode', 'enum', 'on', 'on', 'off, or on (Black Bloc answers when somebody @-mentions it)', ['off', 'on']],
  ['chat_cooldown_seconds', 'int', 20, 20, 'seconds before the same person gets another @-mention reply, 5 to 600', null, 600, 5],
  ['chat_ignore_channels', 'channels', [], [], 'channels Black Bloc never answers an @-mention in'],
  ['chat_ignore_categories', 'channels', [], [], 'categories Black Bloc leaves out of everything it reads and tells people about — the channel names and topics it learns each day, and the channel list every conversational answer is written against. The modmail category and any category with `archive` in its name are left out already, and so is every channel @everyone cannot see'],
  ['chat_home_channel_id', 'channel', null, null, 'where somebody is sent when a conversational answer points at a channel that does not exist. Blank is safe: the sentence is written again without the channel in it rather than pointing anywhere. Either way the invention is logged, so `/chat` ▸ **Logs** and the Logs page count how often it happens'],
  ['chat_visibility_role_id', 'role', '1073741054563602532', '1073741054563602532', "the role whose view of the server IS the bot's map: channels this role can read are the ones the bot may learn about, list and point people at. This server hides everything from @everyone until the rules screen grants Member, so the default is the Member role - clearing it falls back to @everyone, which on this server means almost no channels at all"],
  ['chat_staff_can_ping_roles', 'bool', true, true, "on lets Black Bloc's conversational answers mention a role when the person who @-mentioned it is staff — an Auntie or Uncle and up. Nobody else can make it ping anything, and `@everyone` and `@here` never go through for anyone. Off means a conversational answer pings nobody at all, whoever asked"],
  ['chat_escalation_names', 'int', 2, 2, 'how many online staff Black Bloc names when somebody asks for a mod, 0 to name nobody and up to 10. They are named in plain words, never pinged — the person does that themselves. Nobody online says so instead', null, 10],
  ['chat_greeting_reaction', 'bool', false, false, 'true to answer a bare hello with a wave reaction instead of a sentence; anything longer still gets a reply'],
  ['chat_reply_in_threads', 'bool', true, true, 'true to answer @-mentions inside threads as well as channels'],
  ['chat_route_ping_staff', 'bool', false, false, 'true to drop one line in the staff channel when somebody asks the bot for a mod; only used while modmail_enabled is true'],
  ['chat_llm_mode', 'enum', 'on', 'off', 'off, or on (an @-mention no built-in intent recognises is answered by a language model instead of the catch-all line). Off is the default and off is safe: with it off, or with no keys set, Black Bloc answers exactly as it does today', ['off', 'on']],
  ['chat_simple_model', 'text', 'openai/gpt-oss-120b', 'openai/gpt-oss-120b', 'which Groq model the quick tier asks; it is a setting because Groq retires model names faster than a deploy can follow'],
  ['chat_personality', 'enum', 'cookout', 'cookout', 'the voice Black Bloc writes a conversational answer in: cookout is the house voice, pool lets a conversation pick one of the moods and drift a step at a time, or name one mood to keep it. Only used when chat_llm_mode is on', PERSONALITY_CHOICES],
  ['chat_person_hourly_turns', 'int', 20, 20, "how many conversational answers one member may get in a rolling hour, up to 10000; 0 means no ceiling of its own. Past it they still get Black Bloc's own written lines", null, 10000],
  ['chat_daily_turns', 'int', 200, 200, 'how many conversational answers the whole server may get in a UTC day, up to 10000; 0 means no ceiling of its own', null, 10000],
  ['chat_monthly_cap_usd', 'int', 20, 20, "whole dollars a month Black Bloc may run the conversation models for, up to 1000. At the figure it stops calling them until the 1st and answers from its own written lines; 0 stops them altogether", null, 1000],
  ['chat_status_admin_only', 'bool', true, true, "on keeps the spend block on `/chat` (what the conversation models are spending) to server administrators; the rest of the panel still opens for any staff member, and off lets them read the spend too. The dashboard's Spend section stays staff-visible either way"],
  ...LOG_LEVEL_FEATURES.map(([feature, label, command]) => [
    `${feature}_log_level`,
    'enum',
    'important',
    'important',
    `which ${label} log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard${command ? ` and in \`/${command} logs\`` : ''} either way`,
    ['off', 'important', 'all'],
  ]),
  ['chat_memory_mode', 'enum', 'off', 'off', 'off, or on (Black Bloc keeps a few preferences about each person — what to call them, how they like to be answered — and reads them back next time). Off writes nothing and reads nothing; the profiles already stored stay until somebody clears them', ['off', 'on']],
  ['chat_memory_consent', 'enum', 'optout', 'optout', 'optout means memory is on for everybody until they stop it themselves on the `/memory` panel; optin means nobody is remembered until they start it there', ['optout', 'optin']],
  ['chat_memory_retention_days', 'int', 180, 180, 'days a profile nobody has added to is kept before it is deleted, up to 3650; 0 keeps them forever. Leaving the server clears one straight away', null, 3650],
  ['chat_memory_dm_scope', 'enum', 'separate', 'separate', 'separate keeps what Black Bloc learns in a DM out of public channels — a name or pronouns set by DM never reach the server; shared lets every note be used anywhere', ['separate', 'shared']],
  ['chat_memory_staff_view', 'enum', 'counts', 'counts', 'counts shows staff only how many profiles there are and when each changed; full lets staff read the notes themselves. The person can always read their own with `/memory`', ['counts', 'full']],
  ['chat_memory_notes_max', 'int', 6, 6, 'how many preferences one profile holds, up to 20; the oldest drops off when a newer one arrives', null, 20],
  ['chat_memory_threads_max', 'int', 5, 5, 'how many open topics (“was asking about the Thursday event”) one profile holds, up to 20', null, 20],
  ['chat_memory_model', 'text', '', '', 'which Groq model writes the profile up after a conversation ends; blank uses chat_simple_model, the same quick tier that answers'],
  ['request_mode', 'enum', 'on', 'on', 'off, or on (members can ask for things with /request and staff decide on the site)', ['off', 'on']],
  ['request_filed_line', 'text', 'Filed as **#{request_id}** — Request has been received. You will get a DM every time the status is updated.', 'Filed as **#{request_id}** — Request has been received. You will get a DM every time the status is updated.', "what a member is told the moment their request is filed; {request_id} stands for the request's number and is the only thing that may be filled in"],
  ['request_who_can_file', 'enum', 'everyone', 'everyone', 'who may file a request: everyone, or staff only', ['everyone', 'staff']],
  ['request_notify_channel_id', 'channel', '800000000000000003', null, 'where one line goes when a request is filed; blank tells nobody and the site is the only place they show up'],
  ['request_status_channel_id', 'channel', null, null, 'where a line goes each time staff move a request — picked up, on hold, done, declined; blank uses request_notify_channel_id, so one channel carries both'],
  ['request_forum_channel_id', 'channel', null, null, 'a forum channel where every request is its own post; blank posts the card into request_notify_channel_id as before. /request ▸ Make the forum… makes one under the ticket category'],
  ['request_dm_on_decision', 'bool', true, true, 'true to DM the person who asked every time staff move their request — picked up, on hold, done or declined'],
  ['request_channel_moves', 'enums', ['filed', 'in_progress', 'review', 'sent_back', 'hold', 'declined'], ['filed', 'in_progress', 'review', 'sent_back', 'hold', 'declined'], 'which moves put a card in the request channel: filed, in_progress, review, sent_back, done, hold, declined, check_asked; every one but done and check_asked by default (the done card repeats what the site log already says, and the check card is a DM to one person), and an empty list posts nothing at all', ['filed', 'in_progress', 'review', 'sent_back', 'done', 'hold', 'declined', 'check_asked']],
  ['request_review_by_other', 'bool', false, false, 'true to make somebody other than the staffer who marked a request ready to check be the one who accepts it'],
  ['request_check_fallback_channel', 'bool', true, true, 'true to ping the person who asked in the request channel when Ask-them-to-check cannot DM them (closed DMs); false to tell staff nobody was reached and leave it there'],
  ['request_check_on_ready', 'bool', false, false, 'true to ask the person who asked to try the work the moment a request is marked ready to check, without a staffer pressing Ask them to check'],
  ['request_post_buttons', 'bool', true, true, "true draws the staff move buttons on each request's forum post (and edits them as the request moves); false leaves the post a notice with the site link"],
  ['request_forum_adopts_posts', 'bool', true, true, 'true turns a post somebody starts by hand in the requests forum into a request filed by them; false leaves such posts alone'],
  ['cost_hosting_usd', 'int', 0, 0, 'what the always-on container costs a month in whole dollars — read it off your Fly invoice; 0 = not filled in yet, and the Costs card on the Health page says so rather than claiming hosting is free', null, 10000],
  ['raidtrain_mode', 'enum', 'off', 'off', 'off, shadow (log what would be sent and send nothing) or on (post the lineup and DM slot holders before their hour)', ['off', 'shadow', 'on']],
  ['raidtrain_organizer_role_id', 'role', null, null, 'role that may build and change a raid train’s lineup as well as staff; blank leaves it to staff alone'],
  ['raidtrain_channel_id', 'channel', '800000000000000003', null, 'where a train’s lineup post lives; blank uses events_announce_channel_id'],
  ['raidtrain_ping_role_id', 'role', null, null, 'role mentioned in front of a lineup post; blank pings nobody, and members on the lineup are never pinged by an edit'],
  ['raidtrain_slot_minutes', 'int', 60, 60, 'how long one slot is by default, 15-720 minutes; each train may be created with its own length', null, 720, 15],
  ['raidtrain_reminder_minutes', 'int', 30, 30, 'how long before their slot a holder is DMed, with who raids into them and who they raid next; the DM is sent once', null, 1440, 5],
  ['raidtrain_poll_minutes', 'int', 5, 5, 'minutes between sweeps that send those reminders, start and finish a train, and notice who is live', null, 60, 1],
  ['raidtrain_require_link', 'bool', true, true, 'on makes a linked Twitch channel (`/golive` → Link my Twitch channel) a condition of claiming a slot, so the lineup carries the name the streamer before raids; off lets anybody claim and leaves the name off'],
  ['raidtrain_thread', 'bool', true, true, 'on opens a thread under the lineup post for the people on the train'],
  ['raidtrain_live_posts', 'bool', true, true, 'on says `X is live — next up Y` in that thread when a slot holder starts streaming inside their own hour, and marks the slot checked in'],
  ['raidtrain_max_slots_per_member', 'int', 1, 1, 'how many slots one member may claim on one train; 0 means as many as they like. An organizer assigning a slot is never held to it', null, 24],
  ['raidtrain_scheduled_event', 'bool', false, false, 'on puts the train on Discord’s own event calendar as well. Off by default: Phase 4’s calendar helper writes to the events table, so raid trains keep their own'],
  ['raidtrain_scheduled_name_template', 'text', '{title}', '{title}', "what a raid train is called on Discord's own calendar when `raidtrain_scheduled_event` is on; `{title}` stands for the train's title and is the only thing that may be filled in. It ships as `{title}`, the plain title — set it to `{title} Feat. BaF` to match what `/event` events are called. The lineup post, the thread and the DMs keep the plain title"],
  ['applications_mode', 'enum', 'off', 'off', 'off, shadow (log only, nothing posted or DMed) or on (members can apply and staff decide on the card)', ['off', 'shadow', 'on']],
  ['applications_channel_id', 'channel', '800000000000000005', null, 'where an application card waits for Approve or Deny when the form does not name a channel of its own; blank falls back to rolemenu_approval_channel_id, then to staff_channel_id'],
  ['applications_approver_role_id', 'role', null, null, 'who may approve or deny an application when the form does not name a role of its own; blank falls back to rolemenu_approver_role_id, then to staff'],
  ['applications_ping_role_id', 'role', null, null, 'role mentioned when a new application arrives; blank pings nobody'],
  ['applications_retry_days', 'int', 30, 30, 'days somebody waits after a decision before they may apply for the same form again; a form can set its own, and 0 lets them apply again straight away', null, 3650],
  ['applications_dm_on_decision', 'bool', true, true, 'true to DM the applicant when their application is approved or denied'],
  ['applications_roster_shows_left', 'bool', true, true, 'whether the approved list still shows people who have left the server, marked as gone; false hides them'],
  ['applications_panel_minutes', 'int', 10, 10, "minutes the /applications show panel stays live before its buttons disable themselves; 10 by default. The 'this panel went quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['memory_panel_minutes', 'int', 10, 10, "minutes the /memory panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['youtube_panel_minutes', 'int', 10, 10, "minutes the /youtube panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['pings_panel_minutes', 'int', 10, 10, "minutes the /pings panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['voice_panel_minutes', 'int', 10, 10, "minutes the /voice panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['chat_panel_minutes', 'int', 10, 10, "minutes the /chat panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['youtube_unlink_dms_them', 'bool', true, true, 'true to DM a member the reason when STAFF forget their YouTube channel for them; a member unlinking their own channel is never DMed'],
  ['youtube_live_mode', 'enum', 'off', 'off', 'off, shadow (log what would be announced), or on — a linked YouTube channel going live is announced through the go-live feature, exactly like a Twitch stream', ['off', 'shadow', 'on']],
  ['youtube_live_poll_minutes', 'int', 5, 5, 'how often linked YouTube channels are probed for a live stream', null, 60, 2],
  ['youtube_live_end_misses', 'int', 2, 2, 'how many probes in a row must read offline before a stream is treated as ended', null, 5, 1],
  ['spotlight_mode', 'enum', "shadow", "shadow", "off, shadow (post the rehearsal copy where shadow_channel_id points), or on — spotlighted Twitch channels are announced, bumped and pinned in the go-live channel even though nobody behind them is in this server", ['off', 'shadow', 'on']],
  ['spotlight_poll_minutes', 'int', 5, 5, "how often Twitch is asked whether the spotlighted channels are live; one batched call covers the whole list", null, 30, 2],
  ['spotlight_end_misses', 'int', 2, 2, "how many looks in a row must read offline before a spotlighted stream is treated as over", null, 5, 1],
  ['spotlight_bump_hours', 'int', 4, 4, "hours between reminders that a spotlighted stream is still going; a row can set its own instead. 4 by default, which is the owner's number for a GDQ marathon", null, 48, 1],
  ['spotlight_bump_template', 'text', "**{name}** is still live — **{game}**, {duration} so far. {url}", "**{name}** is still live — **{game}**, {duration} so far. {url}", "what a reminder says while a spotlighted stream runs on; {name} {game} {title} {url} {duration}. It is a new short message, never pinned and never a ping"],
  ['spotlight_bump_cleanup', 'bool', true, true, "true to delete a spotlighted stream's reminders when it ends, so the channel is left with the one announcement"],
  ['spotlight_pin', 'bool', true, true, "true if a channel added to the spotlight list has its announcement pinned while it streams; each row can say otherwise"],
  ['spotlight_default_days', 'int', 7, 7, "how long a newly spotlighted channel lasts before it is purged, unless it is kept for ever", null, 365, 1],
  ['spotlight_event_slack_hours', 'int', 2, 2, "hours past an approved event's end that its spotlight row survives, so a marathon that overruns is still announced", null, 24, 0],
  ['automod_panel_minutes', 'int', 10, 10, "minutes the /automod panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['automod_arm_needs_confirm', 'bool', true, true, 'true to ask a second time before automod is turned on from the panel, naming what will start happening; turning it off or back to shadow is always one press'],
  ['raidtrain_panel_minutes', 'int', 10, 10, "minutes the /raidtrain panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['rolemenu_panel_minutes', 'int', 10, 10, "minutes the /rolemenu panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['honeypot_panel_minutes', 'int', 10, 10, "minutes the /honeypot panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['modmail_panel_minutes', 'int', 10, 10, "minutes the /modmail panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['mod_panel_minutes', 'int', 10, 10, "minutes the /mod panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['settings_panel_minutes', 'int', 10, 10, "minutes the /settings panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ['settings_core_keys_admin_only', 'bool', true, true, 'true keeps the four settings that decide who counts as staff and where Black Bloc talks — the staff channel, the log channel, the moderation log channel and the role-menu channel — to somebody with Manage Server; the rest of /settings still opens for any staff member, and false lets any staff member re-point them too. The dashboard’s Settings page stays staff-visible either way'],
  ['modmail_reply_style', 'enum', 'both', 'both', 'how staff answer a ticket. typing: a plain message in the ticket is relayed to the member, as it always has been. buttons: it is not — only the ticket card’s Reply and /reply reach them, so a ticket channel can be talked in safely. both is the default and is today’s behaviour with the card added', ['buttons', 'typing', 'both']],
  ['selftest_on_boot', 'bool', false, false, 'true to run the self-test at every boot, so a deploy proves itself in the hosting log without anybody opening Discord; false to run it only when staff ask with `/test`. The default is on while test mode is on and off otherwise, so a live server is not given a card per panel at every deploy. It posts a card per panel into the self-test channel and deletes them again a few minutes later'],
  ['selftest_channel_id', 'channel', '800000000000000003', '800000000000000003', 'where the self-test posts the cards it is proving; every one of them is deleted again once selftest_purge_minutes has passed. Unset means the test channel. While test mode is on, the guard refuses any other channel anyway'],
  ['selftest_purge_minutes', 'int', 1, 1, 'how long a self-test’s messages stay in the self-test channel before Black Bloc deletes them; 1 by default. The log lines stay on the dashboard’s Logs page under Test whatever this says', null, 1440, 1],
  ['personality_pool_sync', 'bool', true, true, 'true to bring the mood pool up to the estate’s shared personality manifest at every boot — new moods are added, a mood’s wording, wings and order are refreshed, and a mood the manifest has dropped is retired and switched off. Whether a mood is ON is always staff’s, and this never touches it. false adds missing moods only, which is what to use if a manifest change ever lands wrong'],
  ['personality_pool_peer_url', 'text', 'https://discord.heygabi.ai/api/health', 'https://discord.heygabi.ai/api/health', 'the health address of the estate’s other bot, read by the self-test so the two cannot drift apart unnoticed: it compares that bot’s personality pool version with this one’s and says which side is ahead. It cannot be left blank, and reaching it is never required for Black Bloc to work — a bot that will not answer is reported as unreachable, never as drifted'],
  ['selftest_log_level', 'enum', 'off', 'off', 'which test log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/settings` ▸ **Logs** either way', ['off', 'important', 'all']],
  // The four error keys (docs/info/errors-design.md §B); they sit under core beside the rest.
  ['error_sentence', 'text', 'Black Bloc hit an error at that step; it has been logged for staff. Press **Try again** to pick up where you were — your answers are kept.', 'Black Bloc hit an error at that step; it has been logged for staff. Press **Try again** to pick up where you were — your answers are kept.', 'what somebody is told when a panel, a modal or a button fails and Black Bloc can put them back where they were; it is said beside a Try again button that re-renders what they had open, answers kept. A failure with nothing to re-render says the plain \'hit an error running that command\' sentence instead'],
  ['error_retry_label', 'text', 'Try again', 'Try again', 'what the Try again button on that sentence is called'],
  ['error_retry_minutes', 'int', 10, 10, 'minutes a Try again button keeps working before it says it has run out; 10 by default. Discord closes the interaction it re-renders through after 15 minutes, so anything above that is a button that answers \'run it again\' rather than working', null, 30, 1],
  ['error_retry_expired', 'text', 'That Try again has run out — Black Bloc can only put somebody back where they were for a few minutes. Run {command} again to start it fresh, and tell a Lead if it keeps happening.', 'That Try again has run out — Black Bloc can only put somebody back where they were for a few minutes. Run {command} again to start it fresh, and tell a Lead if it keeps happening.', 'what a Try again pressed too late says. `{command}` is filled in with the command the member was running when it is known, and with \'that command\' when it is not'],
  // The three boot-status keys (docs/info/boot-status-design.md); they sit under core too.
  ['boot_status_mode', 'enum', 'on', 'on', 'on makes Black Bloc read Do Not Disturb with the restarting sentence from the moment Discord sees it until every cog is loaded and it is ready, and flip to it again on the way down; off is the older behaviour, where it simply appears', ['off', 'on']],
  ['boot_status_text', 'text', 'Restarting and booting — back in a moment', 'Restarting and booting — back in a moment', 'the status Black Bloc carries while it is starting up, beside the red Do Not Disturb dot. It is replaced by the member count the moment it is ready'],
  ['shutdown_status_text', 'text', 'Restarting — back in a moment', 'Restarting — back in a moment', 'the status Black Bloc carries on its way down, beside the red dot. Discord keeps a bot\'s status only while it is connected, so this shows for the last second and then it reads offline'],
  // The sixteen registry keys the mock never had a row for, generated from black_bloc/settings_store.py.
  // contract.json's `settings` block is what keeps this list and the registry's bounds in step from now on.
  ["applications_panel_own_list", "bool", true, true, "whether the /apply panel writes a member's own applications out for them; true by default, and false makes that list staff-only"],
  ["birthday_panel_lookup", "bool", true, true, "true to let any member look somebody else's stored birthday up on the /birthday panel; staff always can. Opting out is still the member's own privacy control"],
  ["birthday_panel_minutes", "int", 10, 10, "minutes the /birthday panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ["birthday_panel_next_for_members", "bool", true, true, "true to show every member the birthdays coming up on the /birthday panel; staff always see them. False makes the list staff-only and the panel says so in words"],
  ["bot_bio", "text", "Black Bloc \u2014 moderation & content bot for Black in a Flash!. Staff dashboard: https://blackbloc.heygabi.ai", "Black Bloc \u2014 moderation & content bot for Black in a Flash!. Staff dashboard: https://blackbloc.heygabi.ai", "the About Me on Black Bloc's own profile, dashboard link and all"],
  ["emoji_skin_tone", "enum", "dark", "dark", "the skin tone Black Bloc's hand and people emoji wear: none, light, medium-light, medium, medium-dark, dark", ["none", "light", "medium-light", "medium", "medium-dark", "dark"]],
  ["event_panel_minutes", "int", 10, 10, "minutes the /event panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ["event_panel_own_list", "bool", false, false, "true to show members the events they proposed on the /event panel; staff always see theirs, and members can still propose one and call one off either way"],
  ["golive_embed", "bool", true, true, "post the announcement as an embed with the game's art; off = the sentence only"],
  ["golive_boot_sweep", "bool", true, true, "true walks every member's Discord presence at boot and announces anyone already streaming with no session; false trusts presence updates alone, as before v149"],
  ["hide_commands_when_off", "bool", true, true, "true to take a feature's slash command out of this server's command list while that feature is turned off, so nobody is offered a command that cannot do anything; turning the feature back on brings the command back within about a minute. false leaves every command showing all the time and an off feature explains itself when it is opened. Only off hides a command \u2014 shadow does not"],
  ["logs_count", "int", 10, 10, "how many lines a Logs button shows to begin with, from 1 to 50; 10 by default. Show more adds the same number again, and stops being offered once the log has run out or 50 lines are shown", null, 50, 1],
  ["logs_important_only", "bool", false, false, "true to open every Logs button already filtered to the lines that matter — refusals, errors and staff moves — with Show everything beside the list to see the rest; false opens on everything, which is what it did before"],
  ["operator_read_log", "bool", true, true, "true to write one Core log line for every read a Claude session makes with the operator token, saying which path it read; false reads the same data and leaves no row. The token itself is the on/off switch \u2014 unset it and there are no reads at all"],
  ["spawned_channels_staff_reach", "bool", true, true, "true gives the staff roles view + manage on every channel Black Bloc makes (temp voice rooms and the lobby, event rooms, ticket channels), so a hidden room is still theirs to open or delete by hand; false leaves each builder's own permissions"],
  ["poll_creator_may_end", "bool", true, true, "true to let whoever started a poll close it early from the /poll panel; staff can always close one either way"],
  ["poll_draft_days", "int", 14, 14, "days a saved poll draft is kept before Black Bloc drops it, up to 365; 0 keeps it for ever", null, 365],
  ["poll_drafts", "bool", true, true, "true to let somebody save a half-written poll from the /poll panel and come back to it; false hides Save for later and Resume draft, and the drafts already saved are kept, not deleted"],
  ["poll_panel_minutes", "int", 10, 10, "minutes the /poll panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ["request_panel_minutes", "int", 10, 10, "minutes the /request panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"],
  ["request_panel_own_list", "bool", false, false, "true to show members their own requests on the /request panel; staff always see them, and members can still file and take one back"],
  ["handoff_mode", "enum", "on", "on", "on draws the Send to... moves for staff -- a request becomes an event, an event becomes a request, a ticket becomes either with the member's say-so; off hides them and refuses a stale press in words", ["off", "on"]],
  ["handoff_confirm_hours", "int", 24, 24, "how long a member has to answer a make-this-a-request/event DM before it counts as no; the ticket stays open either way", null, 168, 1],
  ["status_prefix", "text", "Cookout attendees", "Cookout attendees", "what goes in front of the member count in Black Bloc's status"],
  // The "When?" picker's five keys — black_bloc/settings_store.py owns them; these are the mock's copy.
  ["events_default_minutes", "int", 120, 120, "how long a proposed event runs when nobody changes How long, 5 to 10080 minutes; whoever proposes one picks their own length from the dropdown", null, 10080, 5],
  ["events_scheduled_name_template", "text", "{title} Feat. BaF", "{title} Feat. BaF", "what an approved event is called on Discord's own calendar; `{title}` stands for the event's title and is the only thing that may be filled in. The review card, the announcement and the DM keep the plain title"],
  ["default_timezone", "text", "America/Phoenix", "America/Phoenix", "the `Region/City` zone times are read in for anybody who has never picked their own — the Time zone button on `/event` is how a member changes theirs"],
  ["timezone_choices", "text", "America/Phoenix, America/Los_Angeles, America/Denver, America/Chicago, America/New_York, America/Anchorage, Pacific/Honolulu, America/Toronto, America/Vancouver, America/Mexico_City, America/Sao_Paulo, Europe/London, Europe/Paris, Europe/Berlin, Europe/Madrid, Europe/Moscow, Asia/Tokyo, Asia/Seoul, Asia/Shanghai, Asia/Kolkata, Asia/Dubai, Australia/Sydney, Australia/Perth, Pacific/Auckland", "America/Phoenix, America/Los_Angeles, America/Denver, America/Chicago, America/New_York, America/Anchorage, Pacific/Honolulu, America/Toronto, America/Vancouver, America/Mexico_City, America/Sao_Paulo, Europe/London, Europe/Paris, Europe/Berlin, Europe/Madrid, Europe/Moscow, Asia/Tokyo, Asia/Seoul, Asia/Shanghai, Asia/Kolkata, Asia/Dubai, Australia/Sydney, Australia/Perth, Pacific/Auckland", "the zones the Time zone dropdown offers, `Region/City` names separated by commas, up to 24 of them; a name Black Bloc cannot resolve is dropped, and Other — type it… always sits at the bottom of the list for the rest"],
  // Posts (§C7) — black_bloc/settings_store.py owns them; these are the mock's copy.
  ['posts_mode', 'enum', 'shadow', 'shadow', "off, shadow (Post it sends the real message into the shadow channel — the test channel while test mode is on, otherwise the log channel — and keeps it edited there, whatever channel the post names) or on (Post it goes to the post's own channel, and the first real post removes the shadow copy). Shadow is the default, so nothing reaches members until a Lead turns posts on. Off hides `/posts` and refuses both doors in words; every word already written is kept in all three", ['off', 'shadow', 'on']],
  ['posts_panel_minutes', 'int', 10, 10, "minutes the /posts panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it", null, 1440, 1],
  ['posts_versions_keep', 'int', 0, 0, 'how many saved versions of a post are kept; 0 (the default) keeps every one of them, and 1 to 500 trims the oldest after each save. History is cheap and a lost version is not, so raise it rather than lower it. The only remaining version is never trimmed, whatever the number says', null, 500, 0],
  ['posts_versions_summary_chars', 'int', 80, 80, 'how many characters of a version’s message are shown on its row in the Versions list, 20 to 300; 80 by default. It is one line beside View and Use this version — the whole message is in View', null, 300, 20],
  // Guides (G1) — black_bloc/settings_store.py owns them; these are the mock's copy.
  ['guides_mode', 'enum', 'on', 'on', 'on to give members the Guides page and to put a guide link beside a command in /help; off hides both. Staff can still open a guide\u2019s web address while it is off, and the page says so. There is no slash command to hide either way', ['off', 'on']],
  ['guides_who_edits', 'enum', 'staff', 'staff', 'who may change a guide\u2019s wording and screenshots: staff (anybody who can see the staff channel, the default) or manage_guild (a Lead only). It is read when Save is pressed rather than when the page is drawn, so taking the role away stops the next save', ['staff', 'manage_guild']],
  ['guides_help_links', 'bool', true, true, 'true to add a small guide link beside every /help line whose command has a published guide, and an All the guides button on the last page; false leaves /help exactly as it was'],
  ['guides_show_facts', 'bool', true, true, 'true to show the Right now block on a guide \u2014 up to four live values read from the bot as the page opens, such as which mode a feature is in; false shows the steps only'],
  ['guides_fault_files_request', 'bool', true, true, 'true to make Something\u2019s off at the foot of a guide file a request, so staff see it where they see everything else; false makes it a sentence telling the reader to tell a Lead'],
  // Meeting minutes (prototype) — black_bloc/settings_store.py owns them; these are the mock's
  // copy. Filed under `events` in NAMESPACE_OVERRIDE, because the group select is at its cap.
  ['minutes_mode', 'enum', 'off', 'off', 'off or on. This is a PROTOTYPE and it ships off: while it is off `/minutes` is hidden and both doors refuse in words. On lets staff have Black Bloc join the voice channel they are in and take notes; it always announces itself first, and the audio is never stored', ['off', 'on']],
  ['minutes_channel_id', 'channel', null, null, 'where a meeting\u2019s announcement and its notes go; blank means the voice channel\u2019s own text chat. While test mode is on, both land in the test channel or the rehearsal home instead, and the panel says where they went'],
  ['minutes_opt_out_role_id', 'role', null, null, 'a role that means do not record me: if anybody in the voice channel is wearing it, Start refuses and names them. Blank means nobody can opt out that way'],
  ['minutes_start_text', 'text', '\ud83d\udd34 Black Bloc is taking notes in this meeting. Say **stop notes** or press Stop on /minutes to end it.', '\ud83d\udd34 Black Bloc is taking notes in this meeting. Say **stop notes** or press Stop on /minutes to end it.', 'the message Black Bloc posts the moment it joins a meeting, before a word is recorded. It cannot be blank \u2014 a meeting that is recorded silently is the one thing this feature must never do'],
  ['minutes_notes_title', 'text', 'Meeting notes', 'Meeting notes', 'the heading on the notes embed when a meeting is written up'],
  ['minutes_prompt', 'text', 'You are writing the minutes of a voice meeting from an automatic transcript.', 'You are writing the minutes of a voice meeting from an automatic transcript.', 'what Black Bloc asks the model for when it turns a transcript into notes. The transcript is sent after it, so write instructions rather than content'],
  ['minutes_chunk_seconds', 'int', 60, 60, 'how much of one person\u2019s speech is gathered before it is sent to be transcribed; 60 by default, 30\u2013120. Nothing reaches the transcript until a chunk is finished, so this is also how far behind the live meeting the transcript runs', null, 120, 30],
  ['minutes_max_hours', 'int', 3, 3, 'the longest a single meeting may be recorded before Black Bloc leaves and writes the notes anyway; 3 by default. It is what stops a bot left in an empty channel recording all night', null, 6, 1],
  ['minutes_keep_days', 'int', 90, 90, 'how long a meeting\u2019s TRANSCRIPT is kept before it is deleted; 90 days by default. The notes and the meeting itself are kept until somebody deletes them', null, 365, 1],
  ['minutes_panel_minutes', 'int', 10, 10, "minutes the /minutes panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it", null, 1440, 1],
  ["time_step_minutes", "int", 15, 15, "how far apart the Minute dropdown's choices are on the /event and /raidtrain draft panels, 5 to 60 minutes; 15 gives :00, :15, :30 and :45", null, 60, 5],
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

// Requests (13b). [id, member, what, why, dueInDays|null, status, priority|null,
// assignee|null, notes|null, filedMinutesAgo, reason|null, heldFrom|null] — the wide rows
// are derived from these so thirty of them stay readable. `reason` is the one sentence the
// requester is sent, on a decline AND on a hold; `heldFrom` is where a hold came back from.
const REQUEST_SEED = [
  [30, 3, 'A #suggestions channel with a poll under every idea', 'The ideas doc is where suggestions go to die. If each one opened a poll we would know in a day whether anybody else wants it.', null, 'open', null, null, null, 40, null],
  [29, 0, 'Let /request take screenshots', 'Half of what I want to describe is a picture of the thing being wrong. Typing it out loses the detail.', 21, 'open', null, null, null, 120, null],
  [28, 6, 'A weekly digest of what the bot did', 'Nobody reads the log channel. One Monday post with the week in five lines would actually get read.', 7, 'open', null, null, null, 300, null],
  [27, 2, 'Birthday shout-outs should skip people who are not in the server any more', 'We wished a happy birthday to somebody who left in March and it was awkward for everyone.', null, 'open', null, null, null, 900, null],
  [26, 5, 'Let members mute the go-live pings without leaving the role', 'I want the colour, not the notification. Right now it is both or neither.', 30, 'open', null, null, null, 1500, null],
  [25, 0, 'A queue for the karaoke nights', 'We keep losing the running order in chat. A /queue with a list everybody can see would fix it.', 14, 'open', null, null, null, 2600, null],
  [24, 1, 'Temp voice channels should remember the name I gave them', 'I rename mine every single time. It should come back the way I left it.', null, 'open', 3, null, null, 4200, null],
  [23, 6, 'Show who is in a temp voice room from the text channel', 'You cannot tell whether it is worth joining without joining.', 45, 'open', 2, 0, null, 5000, null],
  [22, 2, 'An /events ical export', 'Half the group lives in a different time zone and reads the calendar app, not Discord.', 60, 'open', 4, null, 'Casey has the feed format from last year.', 6400, null],
  [21, 4, 'Automod should let me appeal a timeout', 'I got a ten minute timeout for a link nobody minded and there was nowhere to say so.', null, 'open', 5, null, null, 7000, null],
  [20, 3, 'Role menus with a description under each role', 'The emoji is not enough. New people pick the wrong one every week.', 25, 'hold', 2, 0, 'Fits under the existing menu editor — no new storage.', 8200, 'Waiting on the role menu rewrite so this is not built twice.', 'in_progress'],
  [19, 1, 'A #welcome message that names the three channels worth reading', 'We say the same three things to every new person by hand.', null, 'open', 3, 1, null, 9000, null],
  [18, 6, 'Let staff pin a poll result to the top of the channel', 'The result scrolls away and then we argue about it again a month later.', 40, 'open', 3, null, null, 9800, null],
  [17, 2, 'Modmail should show the member\'s last five messages', 'You open a ticket with no idea what happened just before it.', null, 'hold', 1, 0, 'Needs a message cache the bot does not keep yet — ask before starting.', 11000, 'Nothing keeps old messages yet, so there is nothing to show. Waiting on that.', 'open'],
  [16, 5, 'A quiet hours mode for the announcement pings', 'Three in the morning go-live pings are why I turned notifications off entirely.', 90, 'open', 4, null, null, 12000, null],
  [15, 3, 'The cookout countdown on the dashboard', 'Everybody asks how long is left and somebody has to do the arithmetic in their head.', 10, 'in_progress', 2, 0, 'Half built; the timer is drawn, the setting is not wired.', 13000, null],
  [14, 1, 'Search the audit log by member', 'Scrolling to find one person\'s three lines takes minutes.', null, 'in_progress', 1, 1, null, 14000, null],
  [13, 6, 'Let me file a request from a message with a right-click', 'Half of the requests start as somebody complaining in chat.', 35, 'in_progress', 3, 0, null, 15000, null],
  [12, 2, 'Honeypot should tell staff what the trap caught', 'The ban lands and nobody knows what was posted.', null, 'in_progress', 2, 3, 'Rivet is on this one while Moth is away.', 16000, null],
  [11, 3, 'Stop the bot answering @-mentions inside threads', 'It talks over serious threads and it is hard to take seriously afterwards.', null, 'review', 2, 0, null, 20000, null, null, 'A chat_reply_in_threads setting, on by default, that stops the bot answering an @-mention inside a thread.', 'Turn chat_reply_in_threads off on the Chat page, @-mention the bot inside any thread, and watch it stay quiet. Turn it back on and it answers again.'],
  [10, 0, 'A /help that lists only the commands I can actually run', 'The full list is intimidating and most of it refuses me anyway.', null, 'done', 3, 0, null, 22000, null, null, '/help now filters the list against what the caller may actually run, and marks the staff ones.', 'Run /help as a member and again as a Lead — the second list is longer and the staff lines carry the (staff) mark.'],
  [9, 6, 'Timed roles for the event crew', 'We hand the role out and then forget to take it back for months.', null, 'done', 1, 1, 'Shipped as part of the role menus work.', 24000, null, null, 'Role menus grew an expires_days field, and the sweep takes the role back when it runs out.', 'Set a role menu option to expire after a day, take the role, and check the Role menus page shows when it lapses.'],
  [8, 2, 'Birthday wishes with the member\'s own colour', 'A grey embed for a birthday is a bit sad.', null, 'done', 5, 0, null, 26000, null],
  [7, 4, 'Let people opt out of go-live announcements', 'Some of us stream for four people on purpose.', null, 'done', 2, 1, null, 28000, null],
  [6, 5, 'A dashboard I can read on my phone', 'I am never at a desk when something needs answering.', null, 'done', 1, 0, 'The whole site got this, not just one page.', 30000, null],
  [5, 4, 'Give everybody the ping role by default', 'More people would see the announcements.', null, 'declined', null, null, null, 32000, 'Opt-in is the whole point of that role — a default ping is the thing people leave servers over. Ask again if you want a second, quieter role.'],
  [4, 5, 'Let members delete other people\'s messages in their own temp room', 'It is my room, I should be able to tidy it.', null, 'declined', null, null, null, 34000, 'Deleting somebody else\'s words is a moderator action and it stays with the moderators. You can kick somebody from your room instead.'],
  [3, 7, 'An auto-role that gives new joins the Member role instantly', 'The manual step is slow.', null, 'declined', null, null, null, 40000, 'The manual step is the anti-raid measure. We looked at this in March and the answer has not changed — see the pinned post in the Leads channel.'],
  [2, 1, 'Rename #general to #the-porch', 'It suits the place better.', null, 'withdrawn', null, null, null, 41000, null],
  [1, 3, 'A second bot for music', 'Nobody has bothered since the last one broke.', null, 'withdrawn', null, null, null, 44000, null],
];

const REQUEST_DECIDED = ['in_progress', 'review', 'hold', 'done', 'declined'];

function seedRequests() {
  return REQUEST_SEED.map(([id, who, what, why, due, status, priority, assignee, notes, aged, reason, heldFrom, built, howToTest]) => ({
    id,
    user_id: MEMBERS[who].id,
    what,
    why,
    due_on: due === null ? null : dayAhead(due),
    status,
    priority,
    assignee_id: assignee === null ? null : MEMBERS[assignee].id,
    notes,
    created_at: minutesAgo(aged),
    decided_by: REQUEST_DECIDED.includes(status) ? STAFF.id : null,
    decided_at: REQUEST_DECIDED.includes(status) ? minutesAgo(Math.round(aged * 0.7)) : null,
    decline_reason: reason,
    held_from: status === 'hold' ? heldFrom || 'open' : null,
    built: built || null,
    how_to_test: howToTest || null,
    ready_by: built ? STAFF.id : null,
    sent_back_reason: null,
    done_at: status === 'done' ? minutesAgo(Math.round(aged * 0.2)) : null,
    message_id: null,
  }));
}

// [id, request, author, text, minutesAgo] — every section on the page has at least one
// row with a thread on it, so the drawer is never drawn only against an empty list.
const REQUEST_COMMENT_SEED = [
  [1, 30, 0, 'This is close to what #ideas was meant to be. Worth doing properly once rather than twice badly.', 30],
  [2, 30, 2, 'A poll under every one would drown the channel. Poll the ones that get five reactions?', 20],
  [3, 27, 0, 'Agreed, and it is a one-line check against the member list.', 800],
  [4, 25, 3, 'I have the running order from the last three nights if that helps size it.', 2400],
  [5, 22, 0, 'Casey is right that the feed format is the hard part. Nothing else here is new.', 6000],
  [6, 22, 1, 'I will dig the old one out this week.', 5900],
  [7, 20, 0, 'Planned for after the requests work lands.', 8000],
  [8, 17, 0, 'Holding this one — the message cache is a bigger change than the ticket view is.', 10500],
  [9, 17, 2, 'Even the last one message would help.', 10400],
  [10, 15, 0, 'Timer is drawn. The setting for the date is the bit left.', 12500],
  [11, 15, 3, 'Can it count down to the next one automatically rather than a date somebody types?', 12400],
  [12, 12, 2, 'Taking this while Moth is away.', 15500],
  [13, 11, 0, 'Shipped — chat_reply_in_threads turns it off.', 19000],
  [14, 5, 0, 'Saying no here rather than in DMs so the reasoning is on the record.', 31000],
  [15, 3, 0, 'Third time this has been asked. The pinned post is the long answer.', 39000],
];

function seedRequestComments() {
  return REQUEST_COMMENT_SEED.map(([id, request_id, who, text, aged]) => ({
    id,
    request_id,
    author_id: MEMBERS[who].id,
    text,
    at: minutesAgo(aged),
  }));
}

// Phase 18. Slots are built from the train's own start the way create_train does it, so the
// times on the page are always consecutive and a swap never has to move one.
const RAID_TRAIN_SEED = [
  [1, 3, 'Saturday raid train', 'Eight hours, one streamer an hour, raid down the line.', -2880, 60, 4, 'open', ['830000000000000020', '830000000000000021']],
  [2, 1, 'Launch-day train', 'The one that ran last month.', 43200, 60, 3, 'done', ['830000000000000022', null]],
];
const RAID_SLOT_SEED = {
  1: [[1, 1, 40], [2, 2, 30], [3, null, null], [4, null, null]],
  2: [[1, 1, 4300], [2, 2, 4200], [3, 3, 4100]],
};

function seedRaidTrains() {
  return RAID_TRAIN_SEED.map(([id, who, title, description, aged, minutes, count, status, ids]) => ({
    id,
    organizer_id: who === 3 ? STAFF.id : MEMBERS[who].id,
    title,
    description,
    starts_at: minutesAgo(aged),
    slot_minutes: minutes,
    slot_count: count,
    status,
    channel_id: '800000000000000003',
    lineup_message_id: ids[0],
    thread_id: ids[1],
    scheduled_event_id: null,
    cancel_reason: null,
    created_at: minutesAgo(aged + 6000),
  }));
}

function seedRaidSlots(trains) {
  const rows = [];
  let id = 1;
  for (const train of trains) {
    const start = new Date(train.starts_at).getTime();
    const length = train.slot_minutes * 60000;
    for (const [position, who, claimedAgo] of RAID_SLOT_SEED[train.id]) {
      rows.push({
        id: id += 1,
        train_id: train.id,
        position,
        starts_at: new Date(start + length * (position - 1)).toISOString(),
        ends_at: new Date(start + length * position).toISOString(),
        user_id: who === null ? null : MEMBERS[who].id,
        twitch_login: who === null ? null : ['caseyfast', 'rivetplays', 'mothlight'][who - 1],
        claimed_at: claimedAgo === null ? null : minutesAgo(claimedAgo),
        assigned_by: null,
        reminded_at: null,
        checked_in_at: null,
        live_posted_at: null,
      });
    }
  }
  return rows;
}

function seedState() {
  const raidTrains = seedRaidTrains();
  return {
  raidTrains,
  raidSlots: seedRaidSlots(raidTrains),
  nextRaidTrain: 3,
  settings: new Map(SETTING_SPECS.map((spec) => [spec[0], spec[2]])),
  audit: [
    { key: 'automod_mode', value: 'shadow', updated_by: STAFF.id, updated_at: minutesAgo(220) },
    { key: 'golive_mode', value: 'shadow', updated_by: MEMBERS[1].id, updated_at: minutesAgo(900) },
    { key: 'honeypot_channel_ids', value: ['800000000000000007'], updated_by: STAFF.id, updated_at: minutesAgo(2600) },
  ],
  actions: [],
  guides: [
    {
      id: 1,
      slug: 'golive-announce',
      title: 'Get your stream announced in #live-now',
      goal: 'Link your Twitch channel once. Black Bloc posts whenever Discord shows you streaming.',
      audience: 'member',
      feature: 'golive',
      command: '/golive',
      sort: 10,
      published: true,
      seeded: true,
      updated_at: minutesAgo(400),
      updated_by: null,
      steps: [
        { id: 1, do_text: 'Type **/golive** in any channel.', expect_text: 'A panel only you can see, with **Link my Twitch channel** on it.', media_id: 1, seed_do: 'Type **/golive** in any channel.', seed_expect: 'A panel only you can see, with **Link my Twitch channel** on it.' },
        { id: 2, do_text: 'Press **Link my Twitch channel** and type the part after twitch.tv/.', expect_text: 'The panel reads twitch.tv/your-name.', media_id: null, seed_do: 'Press **Link my Twitch channel** and type the part after twitch.tv/.', seed_expect: 'The panel reads twitch.tv/your-name.' },
      ],
      faults: [
        { id: 1, symptom: 'Nothing posted', answer: 'Announcements are in shadow. The panel\u2019s Announcements line says so; a Lead flips it.' },
        { id: 2, symptom: 'Discord does not show you streaming', answer: 'Reconnect Twitch under Discord\u2019s Connections and turn Display on profile on.' },
      ],
      facts: [
        { kind: 'setting', ref: 'golive_mode' },
        { kind: 'probe', ref: 'golive.linked_count' },
      ],
    },
    {
      id: 2,
      slug: 'house-rules',
      title: 'Write the house rules down',
      goal: 'A guide staff wrote here rather than one Black Bloc ships with.',
      audience: 'staff',
      feature: 'core',
      command: null,
      sort: 900,
      published: false,
      seeded: false,
      updated_at: minutesAgo(60),
      updated_by: STAFF.id,
      steps: [
        { id: 3, do_text: 'Press **Edit this guide**.', expect_text: 'Every line becomes a box.', media_id: 2, seed_do: null, seed_expect: null },
      ],
      faults: [{ id: 3, symptom: 'No Edit this guide', answer: 'guides_who_edits is manage_guild. Ask a Lead.' }],
      facts: [{ kind: 'probe', ref: 'test_mode' }],
    },
  ],
  guideMedia: [
    {
      id: 1,
      guide_id: 1,
      step_id: 1,
      file: '1.png',
      sha256: 'a2b7c2fc4f1c6a3f2e3f4e5d6c7b8a99001122334455667788990011223344ff',
      width: 1280,
      height: 720,
      bytes: 84210,
      source: 'capture',
      surface: 'discord',
      shot_release: 'v110',
      shot_by: STAFF.id,
      shot_at: minutesAgo(2600),
      caption: 'the /golive panel',
      stale: true,
      stale_since: minutesAgo(120),
    },
    {
      id: 2,
      guide_id: 2,
      step_id: 3,
      file: '2.png',
      sha256: 'b3c8d3fd5e2d7b4a3f4a5b6c7d8e9f00112233445566778899aabbccddeeff00',
      width: 1280,
      height: 720,
      bytes: 61400,
      source: 'capture',
      surface: 'website',
      shot_release: 'v110',
      shot_at: minutesAgo(2400),
      shot_by: STAFF.id,
      caption: 'the guide editor',
      stale: false,
      stale_since: null,
    },
  ],
  posts: [
    {
      id: 1,
      slug: 'welcome',
      title: 'Welcome and rules',
      channel_id: '800000000000000001',
      body: POST_SEED_BODY,
      style: 'plain',
      pin: true,
      message_id: null,
      shadow_message_id: null,
      posted_hash: null,
      posted_at: null,
      posted_by: null,
      seeded: true,
      updated_at: minutesAgo(500),
      updated_by: null,
    },
    {
      id: 2,
      slug: 'opening-hours',
      title: 'When staff are around',
      channel_id: '800000000000000003',
      body: '**Staff hours**\n> Somebody is usually around between 6pm and 11pm Phoenix time.\n> Outside that, open a modmail and it is answered in the morning.',
      style: 'embed',
      pin: false,
      message_id: '810000000000000004',
      shadow_message_id: null,
      // Deliberately the hash of something else, so this one wears "changes not yet posted"
      // the moment the page opens — the pill has to be visible in the mock to be looked at.
      posted_hash: 'not-what-the-row-says-now',
      posted_at: minutesAgo(300),
      posted_by: STAFF.id,
      seeded: false,
      updated_at: minutesAgo(90),
      updated_by: STAFF.id,
    },
    {
      id: 3,
      slug: 'scratch-post',
      title: 'A post staff wrote here',
      channel_id: null,
      body: '',
      style: 'plain',
      pin: true,
      message_id: null,
      shadow_message_id: null,
      posted_hash: null,
      posted_at: null,
      posted_by: null,
      seeded: false,
      updated_at: minutesAgo(20),
      updated_by: STAFF.id,
    },
  ],
  nextPost: 4,
  nextPostMessage: 820000000000000001,
  // Version history. welcome carries the backfilled `shipped` row the migration writes, so
  // the Versions foldout has a chip of every colour to look at; scratch-post has none, which
  // is what a post nobody has saved yet looks like.
  postVersions: [
    { post_id: 1, n: 1, title: 'Welcome and rules', body: POST_SEED_BODY, style: 'plain', channel_id: '800000000000000001', pin: true, saved_at: minutesAgo(5000), saved_by: null, via: 'boot', because: 'backfill' },
    { post_id: 2, n: 1, title: 'When staff are around', body: '**Staff hours**\n> Somebody is usually around between 6pm and 10pm Phoenix time.', style: 'embed', channel_id: '800000000000000003', pin: false, saved_at: minutesAgo(300), saved_by: STAFF.id, via: 'discord', because: 'posted' },
    { post_id: 2, n: 2, title: 'When staff are around', body: '**Staff hours**\n> Somebody is usually around between 6pm and 11pm Phoenix time.\n> Outside that, open a modmail and it is answered in the morning.', style: 'embed', channel_id: '800000000000000003', pin: false, saved_at: minutesAgo(90), saved_by: STAFF.id, via: 'website', because: 'saved' },
  ],
  // Meeting minutes (prototype). Meeting 1 is finished, written up and posted, with a short
  // transcript; meeting 2 is still recording, which is the state every notes move refuses from.
  meetings: [
    {
      id: 1,
      channel_id: '800000000000000009',
      started_by: STAFF.id,
      started_at: minutesAgo(200),
      ended_at: minutesAgo(160),
      ended_reason: 'by hand',
      notes: MINUTES_SEED_NOTES,
      notes_channel_id: '800000000000000003',
      notes_message_id: '830000000000000001',
      status: 'done',
    },
    {
      id: 2,
      channel_id: '800000000000000009',
      started_by: STAFF.id,
      started_at: minutesAgo(4),
      ended_at: null,
      ended_reason: null,
      notes: '',
      notes_channel_id: null,
      notes_message_id: null,
      status: 'recording',
    },
  ],
  meetingLines: [
    { id: 1, meeting_id: 1, speaker_id: STAFF.id, speaker: 'Mod', started_at: minutesAgo(199), text: 'We should ship the prototype off by default.' },
    { id: 2, meeting_id: 1, speaker_id: '700000000000000002', speaker: 'Casey', started_at: minutesAgo(198), text: 'I will write the guide for it.' },
    { id: 3, meeting_id: 1, speaker_id: STAFF.id, speaker: 'Mod', started_at: minutesAgo(197), text: 'Agreed. Nobody turns it on until we have tested it.' },
  ],
  nextMeetingMessage: 830000000000000002,
  nextGuide: 3,
  nextGuideStep: 4,
  nextGuideMedia: 3,
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
    // The two open clocks sit on roles their member ACTUALLY holds in ROSTER, so the
    // Members tab's chips have something to count down.
    { id: 5, user_id: MEMBERS[1].id, role_id: '900000000000000001', source: 'approval', granted_by: STAFF.id, granted_at: minutesAgo(5900), expires_at: daysAhead(2), removed_at: null, removed_reason: null },
    { id: 4, user_id: MEMBERS[2].id, role_id: '900000000000000003', source: 'staff', granted_by: STAFF.id, granted_at: minutesAgo(20000), expires_at: daysAhead(29), removed_at: null, removed_reason: null },
    { id: 3, user_id: MEMBERS[3].id, role_id: '900000000000000004', source: 'menu', granted_by: null, granted_at: minutesAgo(30000), expires_at: null, removed_at: null, removed_reason: null },
    { id: 2, user_id: MEMBERS[5].id, role_id: '900000000000000003', source: 'staff', granted_by: MEMBERS[1].id, granted_at: minutesAgo(40000), expires_at: daysAhead(-1), removed_at: minutesAgo(1200), removed_reason: 'expired' },
    { id: 1, user_id: MEMBERS[6].id, role_id: '900000000000000005', source: 'manual', granted_by: null, granted_at: minutesAgo(50000), expires_at: null, removed_at: minutesAgo(300), removed_reason: 'ended_by_staff' },
  ],
  nextMenu: 4,
  nextRequest: 5,
  nextGrant: 6,
  applicationForms: [
    {
      id: 1,
      name: 'twitch-team',
      title: 'Twitch Team',
      description: 'Join the Black in a Flash! Twitch Team.',
      role_id: null,
      review_channel_id: '800000000000000005',
      approver_role_id: null,
      owner_user_id: STAFF.id,
      next_step: 'the Team owner sends your twitch.tv invite — accept it from your Twitch notifications',
      approved_text: "You're on the Team.",
      expires_days: null,
      retry_days: 30,
      open: true,
      panel_channel_id: '800000000000000002',
      panel_message_id: '840000000000000001',
      questions: [
        { position: 1, label: 'Twitch handle', style: 'short', required: true, placeholder: 'twitch.tv/…' },
        { position: 2, label: 'How long have you been streaming', style: 'short', required: true, placeholder: null },
        { position: 3, label: 'Why the Team', style: 'long', required: false, placeholder: null },
      ],
    },
    {
      id: 2,
      name: 'mod-team',
      title: 'Mod Team',
      description: null,
      role_id: '900000000000000001',
      review_channel_id: null,
      approver_role_id: '900000000000000002',
      owner_user_id: null,
      next_step: null,
      approved_text: null,
      expires_days: 90,
      retry_days: null,
      open: false,
      panel_channel_id: null,
      panel_message_id: null,
      questions: [
        { position: 1, label: 'Why do you want to help moderate', style: 'long', required: true, placeholder: null },
      ],
    },
  ],
  applications: [
    { id: 1, form_id: 1, user_id: MEMBERS[3].id, answers: [{ label: 'Twitch handle', answer: 'twitch.tv/rivetplays' }, { label: 'How long have you been streaming', answer: 'about two years' }, { label: 'Why the Team', answer: 'I stream the same games and half the Team already raids me.' }], status: 'pending', submitted_at: minutesAgo(40), decided_by: null, decided_at: null, deny_reason: null, grant_id: null },
    { id: 2, form_id: 1, user_id: MEMBERS[1].id, answers: [{ label: 'Twitch handle', answer: 'twitch.tv/caseyfast' }, { label: 'How long have you been streaming', answer: 'four years' }, { label: 'Why the Team', answer: '' }], status: 'approved', submitted_at: minutesAgo(6000), decided_by: STAFF.id, decided_at: minutesAgo(5900), deny_reason: null, grant_id: '5' },
    { id: 3, form_id: 1, user_id: MEMBERS[4].id, answers: [{ label: 'Twitch handle', answer: 'twitch.tv/nobody' }, { label: 'How long have you been streaming', answer: 'today' }, { label: 'Why the Team', answer: 'free raids' }], status: 'denied', submitted_at: minutesAgo(9000), decided_by: MEMBERS[1].id, decided_at: minutesAgo(8900), deny_reason: 'Come back once you have streamed here for a month.', grant_id: null },
    { id: 4, form_id: 1, user_id: MEMBERS[6].id, answers: [{ label: 'Twitch handle', answer: 'twitch.tv/namu' }, { label: 'How long have you been streaming', answer: 'six months' }, { label: 'Why the Team', answer: 'I want the raid train.' }], status: 'pending', submitted_at: minutesAgo(90), decided_by: null, decided_at: null, deny_reason: null, grant_id: null },
    { id: 5, form_id: 1, user_id: MEMBERS[2].id, answers: [{ label: 'Twitch handle', answer: 'twitch.tv/rivetplays' }], status: 'approved', submitted_at: minutesAgo(12000), decided_by: STAFF.id, decided_at: minutesAgo(11900), deny_reason: null, grant_id: null },
    { id: 6, form_id: 1, user_id: MEMBERS[7].id, answers: [{ label: 'Twitch handle', answer: 'twitch.tv/gone' }], status: 'approved', submitted_at: minutesAgo(20000), decided_by: STAFF.id, decided_at: minutesAgo(19900), deny_reason: null, grant_id: null },
  ],
  nextApplicationForm: 3,
  nextApplication: 7,
  // Wave 5. Run 2 is the one whose cards are still in Discord, so the purge entry has
  // something to take down; run 1 is already cleaned up.
  selftestRuns: [
    { id: 2, started_at: minutesAgo(3), finished_at: minutesAgo(2), ok: 79, failed: 1, posted: 18, purged_at: null, via: 'website', actor_id: STAFF.id, waiting: 18 },
    { id: 1, started_at: minutesAgo(600), finished_at: minutesAgo(599), ok: 80, failed: 0, posted: 18, purged_at: minutesAgo(594), via: 'boot', actor_id: null, waiting: 0 },
  ],
  selftestChecks: {
    2: [
      { name: 'config.log_channel_id', feature: 'core', ok: true, detail: '#bot-log (800000000000000002); view_channel, send_messages, embed_links', at: minutesAgo(3) },
      { name: 'panel.settings', feature: 'core', ok: true, detail: 'posted; 7 buttons, 2 selects', at: minutesAgo(3) },
      { name: 'read./api/status', feature: 'selftest', ok: true, detail: '200; bot, guild, features, loops, open, notes, checked_at', at: minutesAgo(2) },
      { name: 'config.birthday_channel_id', feature: 'birthday', ok: false, detail: 'CheckFailed: Black Bloc is missing embed_links in #birthdays', at: minutesAgo(2) },
    ],
    1: [
      { name: 'config.log_channel_id', feature: 'core', ok: true, detail: '#bot-log (800000000000000002); view_channel, send_messages, embed_links', at: minutesAgo(600) },
    ],
  },
  nextSelftestRun: 3,
  golive: {
    links: [
      { user_id: MEMBERS[1].id, twitch_login: 'caseyfast', twitch_user_id: '112233', linked_at: minutesAgo(4000) },
      { user_id: MEMBERS[2].id, twitch_login: 'rivetplays', twitch_user_id: '445566', linked_at: minutesAgo(9000) },
    ],
    optouts: [{ user_id: MEMBERS[5].id, at: minutesAgo(2000) }],
    fanRoles: [
      { user_id: MEMBERS[1].id, role_id: FAN_ROLE_IDS[0], created_at: minutesAgo(3000), created_by: STAFF.id },
      { user_id: MEMBERS[2].id, role_id: FAN_ROLE_IDS[1], created_at: minutesAgo(2000), created_by: MEMBERS[2].id },
    ],
    // Mirrors the `streamers` table (schema 39). Nobody is added by hand — a go-live is what
    // puts somebody here — so the mock seeds three: two with a role, one with none yet, and
    // MEMBERS[3] hidden by their own press.
    streamers: [
      { user_id: MEMBERS[1].id, first_live_at: minutesAgo(9000), last_live_at: minutesAgo(120), live_count: 14, platform: 'Twitch', login: 'caseyfast', listed: true, hidden_by: null, hidden_at: null },
      { user_id: MEMBERS[2].id, first_live_at: minutesAgo(9500), last_live_at: minutesAgo(1300), live_count: 6, platform: 'Twitch', login: 'rivetplays', listed: true, hidden_by: null, hidden_at: null },
      { user_id: MEMBERS[4].id, first_live_at: minutesAgo(400), last_live_at: minutesAgo(400), live_count: 1, platform: 'Twitch', login: null, listed: true, hidden_by: null, hidden_at: null },
      { user_id: MEMBERS[3].id, first_live_at: minutesAgo(8000), last_live_at: minutesAgo(5000), live_count: 3, platform: 'Twitch', login: null, listed: false, hidden_by: MEMBERS[3].id, hidden_at: minutesAgo(4000) },
    ],
    onboardingManaged: true,
    onboardingSyncedAt: null,
    sessions: [
      { id: 12, user_id: MEMBERS[1].id, source: 'twitch', platform: 'Twitch', url: 'https://twitch.tv/caseyfast', game: 'Lethal Company', title: 'late night runs', also_source: 'youtube', also_platform: 'YouTube', also_url: 'https://www.youtube.com/watch?v=caseyfastlive', also_started_at: minutesAgo(30), started_at: minutesAgo(120), ended_at: null, mode: 'shadow', announced_message_id: null },
      { id: 11, user_id: MEMBERS[2].id, source: 'presence', platform: 'Twitch', url: 'https://twitch.tv/rivetplays', game: 'Balatro', title: 'one more run', also_source: null, also_platform: null, also_url: null, also_started_at: null, started_at: minutesAgo(1500), ended_at: minutesAgo(1300), mode: 'shadow', announced_message_id: null },
      { id: 10, user_id: MEMBERS[3].id, source: 'presence', platform: 'Twitch', url: 'https://twitch.tv/mothlight', game: 'Hades II', title: 'first time, be nice', also_source: null, also_platform: null, also_url: null, also_started_at: null, started_at: minutesAgo(1500), ended_at: minutesAgo(1300), mode: 'shadow', announced_message_id: null },
    ],
    // Spotlight (schema 48): Twitch channels with nobody here behind them. GamesDoneQuick is
    // kept for ever and live right now; ESA runs out with its marathon; the expired one is
    // absent, exactly as the sweep leaves it.
    spotlights: [
      { id: 1, twitch_login: 'gamesdonequick', display_name: 'GamesDoneQuick', note: "the owner's marathon channel", added_by: STAFF.id, added_at: minutesAgo(40000), expires_at: null, bump_hours: null, pin: true, event_id: null },
      { id: 2, twitch_login: 'esamarathon', display_name: 'ESA Marathon', note: 'summer marathon', added_by: STAFF.id, added_at: minutesAgo(3000), expires_at: daysAhead(6), bump_hours: 6, pin: true, event_id: 2 },
      { id: 3, twitch_login: 'frostfatales', display_name: 'Frost Fatales', note: null, added_by: STAFF.id, added_at: minutesAgo(20000), expires_at: daysAhead(30), bump_hours: null, pin: false, event_id: null },
    ],
    spotlightSessions: [
      { id: 5, spotlight_id: 1, started_at: minutesAgo(560), ended_at: null, title: 'AGDQ 2027 — Day 4', game: 'Celeste', url: 'https://www.twitch.tv/gamesdonequick', mode: 'shadow', announced_message_id: '830000000000000020', last_bump_at: minutesAgo(80), bump_count: 2 },
      { id: 4, spotlight_id: 1, started_at: minutesAgo(40000), ended_at: minutesAgo(38500), title: 'SGDQ 2026 — finale', game: 'Super Metroid', url: 'https://www.twitch.tv/gamesdonequick', mode: 'shadow', announced_message_id: '830000000000000019', last_bump_at: minutesAgo(38800), bump_count: 6 },
    ],
  },
  youtube: {
    links: [
      { user_id: MEMBERS[1].id, channel_id: 'UCsXVk37bltHxD1rDPwtNM8Q', handle: '@caseyfast', title: 'Casey Fast', linked_at: minutesAgo(4000) },
      { user_id: MEMBERS[2].id, channel_id: 'UC_x5XG1OV2P6uZZ5FSM9Ttw', handle: null, title: 'Rivet Plays', linked_at: minutesAgo(300) },
    ],
  },
  events: [
    { id: 3, requester_id: MEMBERS[3].id, title: 'Movie night', description: 'Bring snacks.', location: null, where_kind: 'voice', where_channel_id: '800000000000000010', starts_at: minutesAgo(-2880), ends_at: null, status: 'pending', created_at: minutesAgo(60), decided_by: null, decided_at: null, deny_reason: null, review_channel_id: '800000000000000005' },
    { id: 2, requester_id: MEMBERS[1].id, title: 'Speedrun race', description: null, location: 'Twitch', starts_at: minutesAgo(-10080), ends_at: null, status: 'approved', created_at: minutesAgo(4000), decided_by: STAFF.id, decided_at: minutesAgo(3900), deny_reason: null },
    { id: 1, requester_id: MEMBERS[4].id, title: 'Crypto giveaway', description: 'trust me', location: 'DM', starts_at: minutesAgo(-500), ends_at: null, status: 'denied', created_at: minutesAgo(6000), decided_by: STAFF.id, decided_at: minutesAgo(5900), deny_reason: 'This is a scam.' },
  ],
  polls: [
    { id: 3, creator_id: MEMBERS[3].id, question: 'Best day for the cookout?', kind: 'single', surface: 'native', status: 'open', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', message_id: '830000000000000001', thread_id: null, ping_role_id: null, opens_at: minutesAgo(120), closes_at: minutesAgo(-1320), reminded_at: null, closed_at: null, archived_at: null, total_votes: null, decided_by: null, decided_at: null, deny_reason: null, created_at: minutesAgo(125), votes_dropped: 0, options: [{ position: 0, label: 'Saturday', votes: 22 }, { position: 1, label: 'Sunday', votes: 13 }, { position: 2, label: 'Friday', votes: 6 }] },
    { id: 2, creator_id: MEMBERS[1].id, question: 'Movie night or game night?', kind: 'single', surface: 'native', status: 'pending_review', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 48, channel_id: '800000000000000003', message_id: null, thread_id: null, ping_role_id: null, opens_at: null, closes_at: null, reminded_at: null, closed_at: null, archived_at: null, total_votes: null, decided_by: null, decided_at: null, deny_reason: null, created_at: minutesAgo(40), votes_dropped: 0, options: [{ position: 0, label: 'Movie night', votes: 0 }, { position: 1, label: 'Game night', votes: 0 }] },
    { id: 1, creator_id: STAFF.id, question: 'Keep the Thursday raid slot?', kind: 'yesno', surface: 'native', status: 'closed', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', message_id: '830000000000000000', thread_id: null, ping_role_id: null, opens_at: minutesAgo(4000), closes_at: minutesAgo(2560), reminded_at: minutesAgo(2620), closed_at: minutesAgo(2560), archived_at: null, total_votes: 18, decided_by: null, decided_at: null, deny_reason: null, created_at: minutesAgo(4010), votes_dropped: 0, options: [{ position: 0, label: 'Yes', votes: 14 }, { position: 1, label: 'No', votes: 4 }] },
    // One of every surface and status the page has a section for, so nothing renders untested.
    { id: 9, creator_id: MEMBERS[1].id, question: 'How was the stream?', kind: 'rating', surface: 'panel', status: 'open', results: 'close', multi: false, anonymous: true, auto_thread: false, hours: 12, channel_id: '800000000000000003', message_id: '830000000000000004', thread_id: null, ping_role_id: null, opens_at: minutesAgo(30), closes_at: minutesAgo(-690), reminded_at: null, closed_at: null, archived_at: null, total_votes: null, decided_by: null, decided_at: null, deny_reason: null, created_at: minutesAgo(35), votes_dropped: 0, options: [{ position: 0, label: '1', votes: 0 }, { position: 1, label: '2', votes: 1 }, { position: 2, label: '3', votes: 2 }, { position: 3, label: '4', votes: 5 }, { position: 4, label: '5', votes: 9 }] },
    { id: 8, creator_id: MEMBERS[3].id, question: 'Which evenings can you make it?', kind: 'date', surface: 'panel', status: 'open', results: 'live', multi: true, anonymous: false, auto_thread: true, hours: 72, channel_id: '800000000000000003', message_id: '830000000000000005', thread_id: '830000000000000006', ping_role_id: '900000000000000005', opens_at: minutesAgo(200), closes_at: minutesAgo(-4120), reminded_at: null, closed_at: null, archived_at: null, total_votes: null, decided_by: null, decided_at: null, deny_reason: null, created_at: minutesAgo(205), votes_dropped: 0, options: [{ position: 0, label: 'Fri 04 Sep · 7 pm', votes: 4 }, { position: 1, label: 'Sat 05 Sep · 7 pm', votes: 7 }, { position: 2, label: 'Sun 06 Sep · 7 pm', votes: 3 }] },
    { id: 7, creator_id: MEMBERS[2].id, question: 'Rename #general?', kind: 'yesno', surface: 'native', status: 'denied', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', message_id: null, thread_id: null, ping_role_id: null, opens_at: null, closes_at: null, reminded_at: null, closed_at: minutesAgo(3000), archived_at: null, total_votes: null, decided_by: STAFF.id, decided_at: minutesAgo(3000), deny_reason: 'We settled this in the Leads channel last month.', created_at: minutesAgo(3100), votes_dropped: 0, options: [{ position: 0, label: 'Yes', votes: 0 }, { position: 1, label: 'No', votes: 0 }] },
    { id: 6, creator_id: MEMBERS[4].id, question: 'Double XP weekend?', kind: 'single', surface: 'native', status: 'cancelled', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', message_id: '830000000000000007', thread_id: null, ping_role_id: null, opens_at: minutesAgo(5000), closes_at: minutesAgo(4000), reminded_at: null, closed_at: minutesAgo(4600), archived_at: null, total_votes: null, decided_by: null, decided_at: null, deny_reason: null, created_at: minutesAgo(5010), votes_dropped: 0, options: [{ position: 0, label: 'Yes please', votes: 2 }, { position: 1, label: 'No thanks', votes: 1 }] },
    { id: 5, creator_id: STAFF.id, question: 'Old cookout, which park?', kind: 'single', surface: 'native', status: 'archived', results: 'live', multi: false, anonymous: false, auto_thread: false, hours: 24, channel_id: '800000000000000003', message_id: '830000000000000008', thread_id: null, ping_role_id: null, opens_at: minutesAgo(600000), closes_at: minutesAgo(598000), reminded_at: minutesAgo(598060), closed_at: minutesAgo(598000), archived_at: minutesAgo(1000), total_votes: 31, decided_by: null, decided_at: null, deny_reason: null, created_at: minutesAgo(600100), votes_dropped: 31, options: [{ position: 0, label: 'Encanto', votes: 19 }, { position: 1, label: 'Steele Indian School', votes: 12 }] },
  ],
  pollVotes: [
    { poll_id: 3, position: 0, label: 'Saturday', user_id: MEMBERS[1].id, at: minutesAgo(100) },
    { poll_id: 3, position: 1, label: 'Sunday', user_id: MEMBERS[2].id, at: minutesAgo(90) },
  ],
  pollRecurrences: [
    { id: 4, creator_id: STAFF.id, question: 'Are we running tonight?', kind: 'yesno', surface: 'native', hours: 6, anonymous: false, results: 'live', channel_id: '800000000000000003', cadence: 'daily', at: '19:00', tz: 'America/Phoenix', next_at: daysAhead(1), created_at: minutesAgo(8000), options: [{ position: 0, label: 'Yes', votes: 0 }, { position: 1, label: 'No', votes: 0 }] },
    { id: 5, creator_id: STAFF.id, question: 'Best day for next week?', kind: 'checkbox', surface: 'native', hours: 48, anonymous: false, results: 'live', channel_id: '800000000000000003', cadence: 'weekly:mon', at: '09:00', tz: 'America/Phoenix', next_at: null, created_at: minutesAgo(9000), options: [{ position: 0, label: 'Friday', votes: 0 }, { position: 1, label: 'Saturday', votes: 0 }] },
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
    { channel_id: '800000000000000010', owner_id: MEMBERS[1].id, creator_id: '800000000000000009', created_at: minutesAgo(45), user_limit: 0, locked: false, hidden: false },
  ],
  honeypot: [
    { id: 7, user_id: MEMBERS[4].id, channel_id: '800000000000000007', message_id: '820000000000000001', content: 'free nitro at scam-link.example', at: minutesAgo(30), mode: 'shadow', action: 'would_ban' },
    { id: 6, user_id: MEMBERS[7].id, channel_id: '800000000000000007', message_id: '820000000000000002', content: 'steam gift card giveaway', at: minutesAgo(900), mode: 'shadow', action: 'would_ban' },
    { id: 5, user_id: MEMBERS[5].id, channel_id: '800000000000000007', message_id: '820000000000000003', content: 'dm me for cheap nitro', at: minutesAgo(2600), mode: 'on', action: 'banned' },
    { id: 4, user_id: MEMBERS[7].id, channel_id: '800000000000000007', message_id: '820000000000000004', content: 'crypto doubler, first 50 only', at: minutesAgo(6100), mode: 'on', action: 'ban_failed' },
  ],
  cases: [
    { id: 9, user_id: MEMBERS[4].id, kind: 'timeout', moderator_id: STAFF.id, reason: 'mention spam', duration_s: 300, at: minutesAgo(20), mode: 'shadow', applied: false, actions: ['delete', 'warn', 'timeout'], done: [], failed: [] },
    // Already voided in the seed, because /restore is only legal from there and every contract
    // entry runs against a fresh seed.
    { id: 8, user_id: MEMBERS[5].id, kind: 'warn', moderator_id: MEMBERS[1].id, reason: 'link spam', duration_s: null, at: minutesAgo(400), mode: 'on', applied: true, actions: ['warn'], done: ['warn'], failed: [], voided_at: minutesAgo(300), voided_by: STAFF.id, void_reason: 'wrong member' },
    { id: 7, user_id: MEMBERS[4].id, kind: 'warn', moderator_id: STAFF.id, reason: 'told to stop', duration_s: null, at: minutesAgo(800), mode: 'on', applied: true, actions: ['warn'], done: ['warn'], failed: [] },
    { id: 6, user_id: MEMBERS[7].id, kind: 'ban', moderator_id: STAFF.id, reason: 'scam links', duration_s: null, at: minutesAgo(5000), mode: 'on', applied: true, actions: ['ban'], done: ['ban'], failed: [] },
    { id: 5, user_id: MEMBERS[5].id, kind: 'timeout', moderator_id: MEMBERS[1].id, reason: 'shouting in caps', duration_s: 600, at: minutesAgo(6200), mode: 'on', applied: true, actions: ['delete', 'timeout'], done: ['delete', 'timeout'], failed: [] },
    { id: 4, user_id: MEMBERS[6].id, kind: 'warn', moderator_id: MEMBERS[2].id, reason: 'posted an invite to another server', duration_s: null, at: minutesAgo(7400), mode: 'on', applied: true, actions: ['delete', 'warn'], done: ['delete', 'warn'], failed: [] },
    { id: 3, user_id: MEMBERS[4].id, kind: 'timeout', moderator_id: STAFF.id, reason: 'attachment spam', duration_s: 900, at: minutesAgo(9100), mode: 'on', applied: true, actions: ['timeout'], done: ['timeout'], failed: [] },
    { id: 2, user_id: MEMBERS[3].id, kind: 'warn', moderator_id: MEMBERS[1].id, reason: 'arguing in #welcome', duration_s: null, at: minutesAgo(11000), mode: 'on', applied: true, actions: ['warn'], done: ['warn'], failed: [] },
    { id: 1, user_id: MEMBERS[5].id, kind: 'kick', moderator_id: STAFF.id, reason: 'first-day nitro scam', duration_s: null, at: minutesAgo(14000), mode: 'on', applied: true, actions: ['kick'], done: [], failed: ['kick'] },
  ],
  tickets: [
    { id: 5, user_id: MEMBERS[3].id, mode: 'thread', channel_id: '800000000000000005', thread_id: '830000000000000001', status: 'open', opened_at: minutesAgo(90), closed_at: null, closed_by: null, close_reason: null, source: 'dm', opened_by: null },
    { id: 4, user_id: MEMBERS[6].id, mode: 'thread', channel_id: '800000000000000005', thread_id: '830000000000000002', status: 'open', opened_at: minutesAgo(600), closed_at: null, closed_by: null, close_reason: null, source: 'panel', opened_by: null },
    { id: 3, user_id: MEMBERS[4].id, mode: 'channel', channel_id: '800000000000000011', thread_id: null, status: 'closed', opened_at: minutesAgo(4000), closed_at: minutesAgo(3800), closed_by: STAFF.id, close_reason: 'spam', source: 'staff', opened_by: STAFF.id },
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
  // The CUSTOM intent is id 1 and its line is id 1 on purpose: the contract's PUT / POST /
  // DELETE entries point at {chat_intent_id} and {chat_line_id}, and a built-in refuses DELETE.
  chatIntents: [
    { id: 1, name: 'cookout_hours', kind: 'canned', triggers: ['when is the cookout'], enabled: true, sort: 0, created_by: STAFF.id, updated_at: minutesAgo(50), builtin: false },
    { id: 2, name: 'need_a_mod', kind: 'route', triggers: ['i need a mod', 'staff please', 'help me'], enabled: true, sort: 3, created_by: null, updated_at: minutesAgo(9000), builtin: true },
    { id: 3, name: 'who_is_live', kind: 'data', triggers: ['whos live', 'who is live', 'anyone live'], enabled: true, sort: 6, created_by: null, updated_at: minutesAgo(9000), builtin: true },
    { id: 4, name: 'greeting', kind: 'canned', triggers: ['hi', 'hey', 'hello', 'good morning'], enabled: true, sort: 13, created_by: null, updated_at: minutesAgo(9000), builtin: true },
  ],
  chatLines: [
    { id: 1, intent_id: 1, text: 'Doors at six, {name}.', slot: 'filled', enabled: true, created_by: STAFF.id, updated_at: minutesAgo(50) },
    { id: 2, intent_id: 2, text: 'DM me and I will open a ticket for staff, {name}.', slot: 'filled', enabled: true, created_by: null, updated_at: minutesAgo(9000) },
    { id: 3, intent_id: 2, text: 'Staff to ask, {name}: {roles}.', slot: 'empty', enabled: true, created_by: null, updated_at: minutesAgo(9000) },
    { id: 4, intent_id: 3, text: 'Live right now, {name}: {names} — {links}', slot: 'filled', enabled: true, created_by: null, updated_at: minutesAgo(9000) },
    { id: 5, intent_id: 3, text: 'Nobody is streaming right now, {name} — the cookout is all off-camera.', slot: 'empty', enabled: true, created_by: null, updated_at: minutesAgo(9000) },
    { id: 6, intent_id: 4, text: 'Hey {name}! Pull up a chair — the cookout is already going.', slot: 'filled', enabled: true, created_by: null, updated_at: minutesAgo(9000) },
    { id: 7, intent_id: 4, text: 'Hey {name}! That makes {attendees} of us at the cookout today.', slot: 'attendee', enabled: true, created_by: null, updated_at: minutesAgo(9000) },
  ],
  // The feature-request fixture. {feature_request_id} = 25 is the staff session's own PENDING
  // row, so GET /api/requests/mine is never empty and Approve/Decline always have something to
  // act on; {member_request_id} = 30 is the member session's own pending row, the only kind
  // Withdraw takes. `asks` and not `requests`: state.requests is the ROLE-request list.
  // 14b. Section 1 is a staff note on purpose — the contract's PUT and DELETE entries point at
  // {chat_section_id} — and section 3 is the one Black Bloc writes for itself, which every
  // write refuses in words.
  knowledge: [
    { id: 1, title: 'Cookout hours', body: 'The grill goes on at six on a Saturday and the last plate goes out about nine. Nobody minds if you turn up late.', source: 'staff', tag: 'cookout', updated_at: minutesAgo(300), updated_by: STAFF.id },
    { id: 2, title: 'How to get a role', body: 'Pick one from the role menus in #roles. A few of them are asked for rather than taken, and staff answer those on the site.', source: 'staff', tag: 'roles', updated_at: minutesAgo(4000), updated_by: MEMBERS[1].id },
    { id: 3, title: 'Channels', body: 'general — the front room. cookout-planning — who is bringing what. free-nitro-here — a trap, do not post in it.', source: 'server', tag: null, updated_at: minutesAgo(120), updated_by: null },
  ],
  tropes: seedTropes(),
  ledger: seedLedger(),
  // The mock's stand-in for the two keys config.py will carry: Anthropic is set, Groq is not,
  // so the Spend section shows a live tier and a keyless one side by side.
  llmKeys: { ANTHROPIC_API_KEY: true, GROQ_API_KEY: false },
  asks: seedRequests(),
  askComments: seedRequestComments(),
  // Phase 17. Preferences only, never a quote — the third row carries a DM-scope note so the
  // page has something to draw the "learned in a DM" mark against.
  profiles: [
    {
      user_id: MEMBERS[1].id,
      call_me: 'Sky',
      notes: [
        { text: 'likes short answers', where: 'server', at: minutesAgo(200) },
        { text: 'reads on a phone, so keep paragraphs small', where: 'server', at: minutesAgo(200) },
      ],
      threads: [{ text: 'was asking about the Thursday cookout', where: 'server', at: minutesAgo(200) }],
      turns_seen: 14,
      created_at: minutesAgo(9000),
      updated_at: minutesAgo(200),
    },
    {
      user_id: MEMBERS[3].id,
      call_me: '',
      notes: [{ text: 'hates emoji', where: 'server', at: minutesAgo(1400) }],
      threads: [],
      turns_seen: 4,
      created_at: minutesAgo(5000),
      updated_at: minutesAgo(1400),
    },
    {
      user_id: MEMBERS[6].id,
      call_me: '',
      notes: [
        { text: 'English is their second language — keep it simple', where: 'dm', at: minutesAgo(4000) },
      ],
      threads: [],
      turns_seen: 6,
      created_at: minutesAgo(12000),
      updated_at: minutesAgo(4000),
    },
  ],
  memoryOptOut: [{ user_id: MEMBERS[5].id, at: minutesAgo(3000) }],
  nextKnowledge: 4,
  nextAction: 47,
  nextCase: 10,
  nextMessage: 40,
  nextPoll: 10,
  nextChatIntent: 5,
  nextChatLine: 8,
  nextAsk: 31,
  nextAskComment: 16,
  actions: seedActions(),
  };
}


function seedTropes() {
  return TROPE_POOL.map(([name, label, voice], sort) => ({
    name,
    label,
    voice,
    enabled: name !== 'noir',
    sort,
    updated_at: name === 'noir' ? minutesAgo(700) : minutesAgo(9000),
    updated_by: name === 'noir' ? STAFF.id : null,
  }));
}

// ⚠️ The costs are the REAL arithmetic, not a round number picked to fill a bar: Haiku 4.5 is
// $1 in / $5 out per MTok, so a grounded turn is about a third of a cent and a busy month of
// chat is pennies against a $20 cap. The Spend section has to read honestly at 1% as well as
// at 99%, which is exactly what this fixture makes it prove.
function seedLedger() {
  // ⚠️ Spread across THIS month rather than across the last 25 days, so the fixture is the
  // same size on the 1st as on the 28th — a month-to-date sum seeded with last month's turns
  // reads as zero on the day the page most needs checking.
  const at = new Date();
  const monthStart = Date.UTC(at.getUTCFullYear(), at.getUTCMonth(), 1);
  const span = Math.max(90, Math.floor((at.getTime() - monthStart) / 60000) - 20);
  const rows = [];
  const turns = 112;
  for (let n = 0; n < turns; n += 1) {
    const groq = n % 3 === 0;
    const inputs = groq ? 380 + (n % 7) * 40 : 1700 + (n % 9) * 220;
    const outputs = groq ? 80 + (n % 7) * 10 : 240 + (n % 9) * 30;
    rows.push({
      at: minutesAgo(Math.floor(span * (n / turns)) + 6),
      provider: groq ? 'groq' : 'anthropic',
      model: groq ? 'openai/gpt-oss-120b' : 'claude-haiku-4-5',
      input_tokens: inputs,
      output_tokens: outputs,
      cost_microdollars: groq ? 0 : inputs + outputs * 5,
    });
  }
  // Three turns from before the 1st, so the month sum has something to leave out.
  for (let n = 0; n < 3; n += 1) {
    rows.push({
      at: minutesAgo(Math.floor((at.getTime() - monthStart) / 60000) + 2000 + n * 300),
      provider: 'anthropic',
      model: 'claude-haiku-4-5',
      input_tokens: 2600,
      output_tokens: 400,
      cost_microdollars: 4600,
    });
  }
  return rows;
}

function seedActions() {
  return [
  { id: 46, at: minutesAgo(1), kind: 'web.request.declined', actor_id: STAFF.id, target_id: MEMBERS[7].id, reason: 'Opt-in is the whole point of that role.', details: { request_id: 5, via: 'website' } },
  { id: 45, at: minutesAgo(2), kind: 'web.request.in_progress', actor_id: STAFF.id, target_id: MEMBERS[1].id, reason: null, details: { request_id: 24, was: 'open', via: 'website' } },
  { id: 44, at: minutesAgo(2), kind: 'request.filed', actor_id: MEMBERS[3].id, target_id: MEMBERS[3].id, reason: null, details: { request_id: 30, via: 'discord' } },
  { id: 43, at: minutesAgo(3), kind: 'web.request.updated', actor_id: STAFF.id, target_id: null, reason: null, details: { request_id: 20, changed: ['assignee_id', 'priority'], via: 'website' } },
  { id: 42, at: minutesAgo(3), kind: 'request.done', actor_id: STAFF.id, target_id: MEMBERS[6].id, reason: null, details: { request_id: 11, via: 'discord' } },
  { id: 41, at: minutesAgo(3), kind: 'web.settings.set', actor_id: STAFF.id, target_id: null, reason: 'automod_mode = shadow', details: { key: 'automod_mode', value: 'shadow', via: 'website' } },
  { id: 40, at: minutesAgo(20), kind: 'automod.would_timeout', actor_id: null, target_id: MEMBERS[4].id, reason: 'mention spam: 6 mentions in 30s', details: { rule: 'mention_spam' } },
  { id: 39, at: minutesAgo(30), kind: 'honeypot.would_ban', actor_id: null, target_id: MEMBERS[4].id, reason: 'posted in #free-nitro-here', details: null },
  { id: 38, at: minutesAgo(45), kind: 'tempvoice.channel_created', actor_id: MEMBERS[1].id, target_id: '800000000000000010', reason: null, details: null },
  { id: 37, at: minutesAgo(60), kind: 'events.requested', actor_id: MEMBERS[3].id, target_id: null, reason: 'Movie night', details: null },
  { id: 36, at: minutesAgo(88), kind: 'modmail.note_added', actor_id: STAFF.id, target_id: MEMBERS[3].id, reason: null, details: null },
  { id: 35, at: minutesAgo(120), kind: 'golive.would_announce', actor_id: null, target_id: MEMBERS[1].id, reason: 'Lethal Company', details: null },
  { id: 34, at: minutesAgo(220), kind: 'web.settings.set', actor_id: STAFF.id, target_id: null, reason: 'automod_mode = shadow', details: { key: 'automod_mode', value: 'shadow', via: 'website' } },
  { id: 33, at: minutesAgo(400), kind: 'mod.warn', actor_id: MEMBERS[1].id, target_id: MEMBERS[5].id, reason: 'link spam', details: null },
  { id: 32, at: minutesAgo(800), kind: 'mod.warn', actor_id: STAFF.id, target_id: MEMBERS[4].id, reason: 'told to stop', details: null },
  { id: 31, at: minutesAgo(900), kind: 'settings.set', actor_id: MEMBERS[1].id, target_id: null, reason: 'golive_mode = shadow', details: { key: 'golive_mode', value: 'shadow', via: 'discord' } },
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

const CORE_KEYS = ['log_channel_id', 'shadow_channel_id', 'rehearsal_note', 'staff_channel_id', 'role_menu_channel_id', 'bot_bio', 'status_prefix', 'operator_read_log', 'spawned_channels_staff_reach', 'settings_panel_minutes', 'settings_core_keys_admin_only', 'selftest_on_boot', 'selftest_channel_id', 'selftest_purge_minutes', 'selftest_log_level', 'personality_pool_sync', 'personality_pool_peer_url', 'error_sentence', 'error_retry_label', 'error_retry_minutes', 'error_retry_expired', 'boot_status_mode', 'boot_status_text', 'shutdown_status_text'];
const NOT_A_FEATURE = ['golive_end_mode'];
const NAMESPACE_OVERRIDE = {
  modlog_channel_id: 'automod',
  mod_dm_on_action: 'automod',
  mod_log_level: 'automod',
  mod_panel_minutes: 'automod',
  default_timezone: 'events',
  timezone_choices: 'events',
  time_step_minutes: 'events',
  frontdoor_mode: 'modmail',
  frontdoor_channel_id: 'modmail',
  frontdoor_message_id: 'modmail',
  frontdoor_shadow_message_id: 'modmail',
  frontdoor_shadow_hash: 'modmail',
  frontdoor_title: 'modmail',
  frontdoor_text: 'modmail',
  frontdoor_ticket_label: 'modmail',
  frontdoor_request_label: 'modmail',
  frontdoor_event_label: 'modmail',
  frontdoor_follows_post: 'modmail',
  frontdoor_replaces_ticket_button: 'modmail',
  frontdoor_panel_minutes: 'modmail',
  handoff_mode: 'request',
  handoff_confirm_hours: 'request',
  minutes_mode: 'events',
  minutes_channel_id: 'events',
  minutes_opt_out_role_id: 'events',
  minutes_start_text: 'events',
  minutes_notes_title: 'events',
  minutes_prompt: 'events',
  minutes_chunk_seconds: 'events',
  minutes_max_hours: 'events',
  minutes_keep_days: 'events',
  minutes_panel_minutes: 'events',
  minutes_log_level: 'events',
  spotlight_mode: 'golive',
  spotlight_poll_minutes: 'golive',
  spotlight_end_misses: 'golive',
  spotlight_bump_hours: 'golive',
  spotlight_bump_template: 'golive',
  spotlight_bump_cleanup: 'golive',
  spotlight_pin: 'golive',
  spotlight_default_days: 'golive',
  spotlight_event_slack_hours: 'golive',
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

const MEMBER = MEMBERS[3];

/** The one session that is a signed-in guild member and NOT staff: requests only. */
function requireMember(session) {
  if (session === 'member') return;
  requireStaff(session);
}

function actorOf(session) {
  return session === 'member' ? MEMBER.id : STAFF.id;
}

function requireStaff(session) {
  if (session === 'none') throw new Refused(401, 'not_signed_in', NOT_SIGNED_IN);
  if (session === 'member') throw new Refused(403, 'not_staff', NOT_STAFF);
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
  if (session === 'member') {
    return { status: 200, body: { user: { id: MEMBER.id, name: MEMBER.display_name, avatar: null }, staff: false, member: true, state: 'not_staff', guild, message: MEMBER_NOT_STAFF } };
  }
  if (session === 'stranger') {
    return { status: 200, body: { user: { id: MEMBERS[5].id, name: MEMBERS[5].name, avatar: null }, staff: false, member: false, state: 'not_staff', guild, message: NOT_STAFF } };
  }
  if (session === 'unknown') {
    return { status: 200, body: { user, staff: false, member: false, state: 'staff_unknown', guild, message: STAFF_UNKNOWN } };
  }
  return { status: 200, body: { user, staff: true, member: true, state: 'staff', guild, message: null } };
}

function statusBody() {
  const features = SETTING_SPECS
    .map(([key]) => key)
    .filter((key) => key.endsWith('_mode') && !NOT_A_FEATURE.includes(key))
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

// The one home for money (owner ask, 2026-09-01). Mirrors black_bloc/api/costs.py: the model
// rows are the ledger grouped, hosting is a setting, the free things are named at $0 and the
// keys are NAMES with set/unset. ⚠️ The mock's ledger rows carry no tier or turn column, so a
// tier is derived from the provider and a turn is a row; 14a's real ledger has both.
const COST_MICRODOLLARS = 1000000;
const COST_PROVIDER_LABELS = { anthropic: 'Anthropic', groq: 'Groq' };
const COST_TIERS = { anthropic: 'important', groq: 'simple' };
const COST_HOSTING_NAME = 'Hosting — the always-on container';
const COST_HOSTING_BLANK = 'Nobody has filled this in yet, so the total below is only what the models have cost. Read the monthly figure off your Fly invoice and put it in `cost_hosting_usd`.';
const COST_FREE_ITEMS = [
  ['Discord', 'The gateway, the API and the slash commands are free at any size this bot is.'],
  ['Twitch API', 'Helix costs nothing for the go-live checks Black Bloc makes.'],
  ['Groq — the quick chat tier', 'Free while their tier is. Every call is still written to the ledger with its real token counts, so the day it is not free the figure is already there.'],
];
const COST_SECRETS = [
  ['DISCORD_TOKEN', true, "the bot's own login. Without it Black Bloc does not start at all."],
  ['TWITCH_CLIENT_ID', true, 'reads Twitch for go-live posts. Free; unset means presence only.'],
  ['TWITCH_CLIENT_SECRET', true, 'the other half of the Twitch app.'],
  ['DISCORD_CLIENT_ID', true, 'the dashboard’s sign-in. Without it nobody can sign in to this site.'],
  ['DISCORD_CLIENT_SECRET', true, 'the other half of the dashboard sign-in.'],
  ['SESSION_SECRET', true, 'signs the sign-in cookie. Changing it signs everybody out.'],
  ['POLL_VOTE_SECRET', false, 'keys anonymous poll votes. Unset falls back to a plain hash.'],
  ['ANTHROPIC_API_KEY', true, 'pays for the careful chat tier. Unset means that tier does not exist.'],
  ['GROQ_API_KEY', false, 'the free chat tier. Unset means that tier does not exist.'],
];

function costMonthName(iso) {
  return new Date(iso).toLocaleString('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' });
}

function costGrouped(rows) {
  const found = new Map();
  for (const row of rows) {
    const key = `${row.provider}|${row.model}`;
    const seen = found.get(key) || {
      provider: row.provider,
      model: row.model,
      tier: COST_TIERS[row.provider] || 'important',
      turns: 0,
      calls: 0,
      input_tokens: 0,
      output_tokens: 0,
      spent: 0,
    };
    seen.turns += 1;
    seen.calls += 1;
    seen.input_tokens += row.input_tokens;
    seen.output_tokens += row.output_tokens;
    seen.spent += row.cost_microdollars;
    found.set(key, seen);
  }
  return [...found.values()].sort((a, b) => b.spent - a.spent);
}

function costRound(microdollars) {
  return Math.round((microdollars / COST_MICRODOLLARS) * 100) / 100;
}

route('GET', '/api/costs', (context) => {
  requireStaff(context.session);
  const at = new Date();
  const thisMonth = new Date(Date.UTC(at.getUTCFullYear(), at.getUTCMonth(), 1)).toISOString();
  const lastMonth = new Date(Date.UTC(at.getUTCFullYear(), at.getUTCMonth() - 1, 1)).toISOString();
  const now = costGrouped(state.ledger.filter((row) => row.at >= thisMonth));
  const was = costGrouped(state.ledger.filter((row) => row.at >= lastMonth && row.at < thisMonth));
  const before = new Map(was.map((row) => [`${row.provider}|${row.model}`, row.spent]));

  const models = now.map((row) => {
    const spent = costRound(row.spent);
    const tokens = row.input_tokens + row.output_tokens;
    return {
      provider: row.provider,
      provider_label: COST_PROVIDER_LABELS[row.provider] || row.provider,
      model: row.model,
      tier: row.tier,
      turns: row.turns,
      calls: row.calls,
      input_tokens: row.input_tokens,
      output_tokens: row.output_tokens,
      cache_read_tokens: 0,
      cache_write_tokens: 0,
      spent_usd: spent,
      prior_usd: costRound(before.get(`${row.provider}|${row.model}`) || 0),
      word: spent === 0
        ? `${row.turns} answer(s), ${tokens} tokens, free at this tier.`
        : `${row.turns} answer(s), ${tokens} tokens, ${money(spent)}.`,
    };
  });
  const spentUsd = Math.round(models.reduce((total, row) => total + row.spent_usd, 0) * 100) / 100;
  const priorUsd = costRound(was.reduce((total, row) => total + row.spent, 0));
  const hosting = Number(state.settings.get('cost_hosting_usd') ?? 0);
  const totalUsd = Math.round((spentUsd + hosting) * 100) / 100;

  return {
    month: {
      from: thisMonth,
      spent_usd: spentUsd,
      word: models.length
        ? `${money(spentUsd)} on models so far this month.`
        : 'No model has been asked anything this month, so the models have cost nothing.',
    },
    prior: {
      from: lastMonth,
      to: thisMonth,
      spent_usd: priorUsd,
      word: was.length
        ? `${money(priorUsd)} on models in ${costMonthName(lastMonth)}.`
        : `Nothing was spent on models in ${costMonthName(lastMonth)}.`,
    },
    models,
    items: [
      {
        name: COST_HOSTING_NAME,
        kind: 'configured',
        amount_usd: hosting,
        key: 'cost_hosting_usd',
        word: hosting > 0
          ? `$${hosting} a month, as somebody typed it in off the invoice.`
          : COST_HOSTING_BLANK,
      },
      ...COST_FREE_ITEMS.map(([name, word]) => ({
        name, kind: 'free', amount_usd: 0, key: null, word,
      })),
    ],
    total: {
      month_usd: totalUsd,
      models_usd: spentUsd,
      hosting_usd: hosting,
      word: hosting > 0
        ? `${money(totalUsd)} this month: ${money(spentUsd)} on models and ${money(hosting)} on hosting.`
        : `${money(spentUsd)} this month, all of it models — hosting has not been filled in.`,
    },
    secrets: COST_SECRETS.map(([name, set, what]) => ({ name, set, what })),
    hosting_key: 'cost_hosting_usd',
    notes: models.length || was.length
      ? []
      : ['Black Bloc has never called a model, so there is nothing on the models line yet. That is what an unspent month looks like, not a fault.'],
    checked_at: at.toISOString(),
  };
});

// actionlog.py:SUMMARY_SKIPS — `via` is its own column, so it never joins the summary.
const SUMMARY_SKIPS = ['via'];

function summaryOfAction(row) {
  if (row.reason) return String(row.reason);
  if (!row.details) return '';
  if (typeof row.details !== 'object') return String(row.details);
  return Object.entries(row.details)
    .filter(([key]) => !SUMMARY_SKIPS.includes(key))
    .map(([key, value]) => `${key}=${value}`)
    .join(', ');
}

function kindsPresent(feature) {
  const rows = feature
    ? state.actions.filter((row) => featureOfKind(row.kind) === feature)
    : state.actions.filter((row) => !HIDDEN_BY_DEFAULT.includes(featureOfKind(row.kind)));
  return [...new Set(rows.map((row) => row.kind))].sort();
}

function searchedActions(params) {
  const kind = params.get('kind');
  const userId = params.get('user_id');
  const feature = params.get('feature');
  const since = params.get('since');
  const until = params.get('until');
  const needle = (params.get('q') || '').trim().toLowerCase();
  let rows = state.actions;
  if (kind) rows = rows.filter((row) => String(row.kind).startsWith(kind));
  if (userId) rows = rows.filter((row) => row.actor_id === userId || row.target_id === userId);
  if (feature) rows = rows.filter((row) => featureOfKind(row.kind) === feature);
  else if (!kind) {
    rows = rows.filter((row) => !HIDDEN_BY_DEFAULT.includes(featureOfKind(row.kind)));
  }
  if (since) rows = rows.filter((row) => row.at >= since);
  if (until) rows = rows.filter((row) => row.at <= until);
  if (params.get('important') === '1') rows = rows.filter((row) => isImportantKind(row.kind));
  rows = rows.map((row) => ({
    ...withNames(row, [['actor_id', 'actor_name'], ['target_id', 'target_name']]),
    feature: featureOfKind(row.kind),
    important: isImportantKind(row.kind),
    summary: summaryOfAction(row),
    via: viaOfKind(row.kind, row.details),
  }));
  if (needle) {
    rows = rows.filter((row) =>
      [row.kind, row.actor_name, row.target_name, row.reason, JSON.stringify(row.details || '')]
        .join(' ')
        .toLowerCase()
        .includes(needle),
    );
  }
  return rows;
}

route('GET', '/api/actions', (context) => {
  requireStaff(context.session);
  const params = context.url.searchParams;
  const size = Math.max(1, Math.min(Number(params.get('per_page') || params.get('limit') || 50), 200));
  const page = Math.max(1, Number(params.get('page') || 1));
  const rows = searchedActions(params);
  const shown = rows.slice((page - 1) * size, (page - 1) * size + size);
  return {
    actions: shown,
    kinds: kindsPresent(params.get('feature')),
    limit: size,
    per_page: size,
    page,
    total: rows.length,
    shown: shown.length,
    notes: [],
  };
});

route('GET', '/api/actions/export.csv', (context) => {
  // NOT in contract.json: check.mjs reads JSON shapes, and this one answers text/csv.
  requireStaff(context.session);
  const columns = ['id', 'at', 'kind', 'feature', 'important', 'actor_id', 'actor_name', 'target_id', 'target_name', 'reason', 'details'];
  const cell = (row, name) => {
    const value = name === 'details' ? (row.details ? JSON.stringify(row.details) : '') : row[name];
    if (value === null || value === undefined) return '';
    const text = String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const lines = [columns.join(',')];
  for (const row of searchedActions(context.url.searchParams)) {
    lines.push(columns.map((name) => cell(row, name)).join(','));
  }
  return {
    status: 200,
    headers: { 'content-type': 'text/csv; charset=utf-8', 'content-disposition': 'attachment; filename="black-bloc-log.csv"' },
    body: `${lines.join('\n')}\n`,
  };
});

// Wave 5 — the self-test. Mirrors black_bloc/api/selftest_api.py: the POST starts a run and
// lets go, so the mock finishes it at once and the Health card's poll sees it done first time.
const SELFTEST_NOTHING_TO_PURGE = 'That self-test run has nothing left to delete — its cards have already gone. Nothing was done, and nothing is wrong.';

function selftestRow(row) {
  return {
    run_id: row.id,
    started_at: row.started_at,
    finished_at: row.finished_at,
    ok: row.ok,
    failed: row.failed,
    posted: row.posted,
    purged_at: row.purged_at,
    via: row.via,
    actor_id: row.actor_id === null ? null : String(row.actor_id),
    running: !row.finished_at,
  };
}

function wantedSelftestRun(runId) {
  const found = state.selftestRuns.find((row) => String(row.id) === String(runId));
  if (!found) {
    throw new Refused(404, 'no_such_run', `Black Bloc has no self-test run numbered ${runId} for this server, so there was nothing to purge. Open the Health page to see the runs it does have.`);
  }
  return found;
}

route('POST', '/api/selftest', (context) => {
  requireStaff(context.session);
  const going = state.selftestRuns.find((row) => !row.finished_at);
  if (going) {
    throw new Refused(409, 'selftest_running', `A self-test is already running (started ${going.started_at}, 0 of 106 checks done). Nothing was started a second time — wait for it to finish, or watch it on the dashboard's Health page.`);
  }
  const row = {
    id: state.nextSelftestRun++,
    started_at: now(),
    finished_at: now(),
    ok: 80,
    failed: 0,
    posted: 18,
    purged_at: null,
    via: 'website',
    actor_id: actorOf(context.session),
    waiting: 18,
  };
  state.selftestRuns.unshift(row);
  state.selftestChecks[row.id] = [
    { name: 'config.log_channel_id', feature: 'core', ok: true, detail: '#bot-log (800000000000000002); view_channel, send_messages, embed_links', at: now() },
    { name: 'panel.settings', feature: 'core', ok: true, detail: 'posted; 7 buttons, 2 selects', at: now() },
  ];
  logAction('web.selftest.started', { details: { run_id: row.id, checks: 106, via: 'website' } });
  logAction('web.selftest.finished', { details: { run_id: row.id, ok: row.ok, failed: row.failed, posted: row.posted, via: 'website' } });
  return { run_id: row.id, started_at: row.started_at, checks: 106 };
});

route('GET', '/api/selftest', (context) => {
  requireStaff(context.session);
  const going = state.selftestRuns.find((row) => !row.finished_at);
  return {
    runs: state.selftestRuns.map(selftestRow),
    running: going ? going.id : null,
    purge_minutes: Number(state.settings.get('selftest_purge_minutes') || 1),
    notes: [],
  };
});

route('GET', '/api/selftest/:run_id', (context) => {
  requireStaff(context.session);
  const row = wantedSelftestRun(context.params.run_id);
  return { ...selftestRow(row), checks: state.selftestChecks[row.id] || [] };
});

route('POST', '/api/selftest/:run_id/purge', (context) => {
  requireStaff(context.session);
  const row = wantedSelftestRun(context.params.run_id);
  const gone = row.waiting;
  row.waiting = 0;
  if (gone) {
    row.purged_at = now();
    logAction('web.selftest.purged', { details: { run_id: row.id, messages: gone, via: 'website' } });
  }
  return { ...selftestRow(row), purged: gone, notes: gone ? [] : [SELFTEST_NOTHING_TO_PURGE] };
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

/** The clock an open timed grant puts on a chip, the way api/tools/members.py joins it on. */
function expiryOf(userId, roleId) {
  const found = state.grants
    .filter((row) => String(row.user_id) === String(userId)
      && String(row.role_id) === String(roleId)
      && row.removed_at === null
      && row.expires_at !== null)
    .map((row) => row.expires_at)
    .sort();
  return found.length ? found[0] : null;
}

function rosterRoles(row) {
  return row.role_ids
    .map((id) => ROLES.find((role) => role.id === id))
    .filter(Boolean)
    .sort((a, b) => b.position - a.position)
    .slice(0, 5)
    .map((role) => ({
      id: role.id,
      name: role.name,
      color: role.color,
      expires_at: expiryOf(row.id, role.id),
    }));
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

// --- posts (§C4) ------------------------------------------------------------------------------
// The shapes black_bloc/api/tools/posts.py answers with. Staff only: there is no member view.

const POST_CAPS = { plain: 2000, embed: 4096 };
const POST_STYLE_WORDS = { plain: 'a plain message', embed: 'an embed' };
const POST_TITLE_MAX = 256;
const POST_NO_SUCH = 'There is no post called **{slug}**, so nothing was done. It may have been renamed — open the Posts page and pick it from the list.';
const POST_SEEDED = '**{slug}** is the post Black Bloc ships with, so it cannot be deleted — a deploy would only put it back. Press **Take it down** instead: the message goes and every word you have written is kept.';
const POST_STILL_POSTED = '**{title}** is still posted in Discord, so it was not deleted. Press **Take it down** first — every word is kept either way.';
const POST_NO_CHANNEL = '**{title}** has no channel to go in yet, so there is nothing to post it to. Pick one under **Channel**, press Save Changes, then press Post it.';
const POST_NOTHING_TO_POST = '**{title}** has nothing written in it yet, so there is nothing to post. Write the message in the box, save it, then press Post it.';
const POST_NOT_POSTED = '**{title}** is not posted anywhere right now, so there is nothing to take down. Press Post it first.';
const POST_UNKNOWN_CHANNEL = '**{given}** is not a channel Black Bloc can see in this server, so nothing was saved. Pick one from the list under **Channel**.';
const POST_TITLE_NEEDED = 'A post needs a title, so nothing was saved. Fill it in and save again.';
const POST_SLUG_TAKEN = 'There is already a post at **{slug}**, so nothing was made. Give this one a different title, or edit the one that is there.';
const POST_SLUG_NEEDED = 'A post needs a title Black Bloc can turn into a web address, and that one came out empty, so nothing was made. Use some letters or numbers in the title.';
const POSTS_ARE_OFF = 'Posts are off for this server, so **Post it** and **Take it down** refuse in words and `/posts` is hidden. Every word written here is kept — a Lead turns them back on from the Settings page under **posts**.';
const POST_TEST_MODE_NOTE = `Black Bloc is in test mode, so a post only reaches #${TEST_CHANNEL_NAME} or a channel it made itself. **Post it** on anything else writes down what it would have sent and sends nothing.`;
const POSTS_ARE_SHADOW = 'Posts are in **shadow**: **Post it** sends the real message to {where} and keeps it edited there, whatever channel a post names, so nothing reaches members yet. Turning posts **on** is the go-live — the next **Post it** goes to the post\u2019s own channel and the shadow copy is removed.';
const POST_NO_SUCH_VERSION = 'There is no version {n} of **{title}**, so nothing was changed. Open **Versions** and pick one from the list.';
const POST_VERSION_IS_CURRENT = 'Version {n} is already what the post says, so nothing was changed. Pick an older version, or edit the words in the box.';
const POST_NO_SHADOW_CHANNEL = 'Posts are in **shadow**, so **{title}** goes to the shadow channel rather than its own — and this server has neither a test channel nor a log channel, so there is nowhere to put it. A Lead sets **log_channel_id** on the Settings page, or turns posts on.';
// The shadow channel: the guard's own while test mode is on, otherwise log_channel_id. The
// mock has no guard object, so it reads the same two places the bot does.
const POST_SHADOW_CHANNEL = '800000000000000003';

function postCap(style) {
  return POST_CAPS[style] || POST_CAPS.plain;
}

function postHash(row) {
  return JSON.stringify([row.style, row.title, row.body]);
}

function postIsUp(row) {
  return Boolean(row.message_id) || Boolean(row.shadow_message_id);
}

function postWhere(row) {
  if (row.message_id) return 'channel';
  return row.shadow_message_id ? 'shadow' : null;
}

function postPending(row) {
  return postIsUp(row) && row.posted_hash !== postHash(row);
}

function postStatus(row) {
  if (!postIsUp(row)) return ['not posted'];
  const found = [postWhere(row) === 'shadow' ? 'posted (shadow)' : 'posted'];
  if (row.pin) found.push('pinned');
  if (postPending(row)) found.push('changes not yet posted');
  return found;
}

function postsMode() {
  const found = String(state.settings.get('posts_mode') || 'shadow');
  return ['off', 'shadow', 'on'].includes(found) ? found : 'shadow';
}

function postShadowChannel() {
  return testMode ? POST_SHADOW_CHANNEL : (state.settings.get('log_channel_id') || null);
}

function postTooLong(count, limit, style, doing) {
  const over = count - limit;
  const switched = style === 'plain' ? ' — or set the style to an embed, which holds 4096' : '';
  return `That post is ${count} characters and ${POST_STYLE_WORDS[style]} holds ${limit}, so nothing was ${doing}. Take ${over} character${over === 1 ? '' : 's'} out${switched}.`;
}

function postChannelName(id) {
  const found = CHANNELS.find((one) => one.id === String(id));
  return found ? found.name : null;
}

function postRow(row) {
  return {
    id: String(row.id),
    slug: row.slug,
    title: row.title,
    body: row.body,
    style: row.style,
    cap: postCap(row.style),
    title_cap: POST_TITLE_MAX,
    pin: Boolean(row.pin),
    channel_id: row.channel_id ? String(row.channel_id) : null,
    channel_name: postChannelName(row.channel_id),
    posted: postIsUp(row),
    posted_where: postWhere(row),
    pinned: postIsUp(row) && Boolean(row.pin),
    changes_pending: postPending(row),
    status: postStatus(row),
    move: postIsUp(row) ? 'Update the post' : 'Post it',
    message_id: row.message_id ? String(row.message_id) : null,
    shadow_message_id: row.shadow_message_id ? String(row.shadow_message_id) : null,
    posted_at: row.posted_at,
    posted_by: row.posted_by ? String(row.posted_by) : null,
    posted_by_name: row.posted_by ? memberName(row.posted_by) : null,
    seeded: Boolean(row.seeded),
    updated_at: row.updated_at,
    updated_by: row.updated_by ? String(row.updated_by) : null,
    updated_by_name: row.updated_by ? memberName(row.updated_by) : null,
  };
}

function postStyles() {
  return Object.keys(POST_CAPS).map((style) => ({
    style,
    cap: POST_CAPS[style],
    label: POST_STYLE_WORDS[style],
  }));
}

function postGuard() {
  return {
    test_mode: testMode,
    test_channel: testMode ? TEST_CHANNEL_NAME : null,
    said: testMode ? POST_TEST_MODE_NOTE : null,
  };
}

function postShadow() {
  const channel_id = postShadowChannel();
  return {
    channel_id: channel_id ? String(channel_id) : null,
    channel_name: channel_id ? postChannelName(channel_id) : null,
  };
}

function postNotes() {
  const mode = postsMode();
  if (mode === 'off') return [POSTS_ARE_OFF];
  if (mode !== 'shadow') return [];
  const where = postShadowChannel();
  if (!where) return [POST_NO_SHADOW_CHANNEL.split('{title}').join('a post')];
  return [POSTS_ARE_SHADOW.split('{where}').join(`#${postChannelName(where)}`)];
}

function postVersionsOf(row) {
  return state.postVersions
    .filter((one) => one.post_id === row.id)
    .sort((a, b) => b.n - a.n);
}

function postVersionTop(row) {
  const found = postVersionsOf(row);
  return found.length ? found[0].n : null;
}

function postSummaryChars() {
  return Number(state.settings.get('posts_versions_summary_chars') ?? 80) || 80;
}

function postVersionsKeep() {
  return Math.max(0, Number(state.settings.get('posts_versions_keep') ?? 0) || 0);
}

function postSummary(version) {
  const limit = postSummaryChars();
  const text = String(version.body || '').split(/\s+/).filter(Boolean).join(' ');
  return text.length <= limit ? text : `${text.slice(0, limit).trimEnd()}\u2026`;
}

function postIsShipped(row, version) {
  return Boolean(row.seeded) && version.because === 'backfill' && version.body === POST_SEED_BODY;
}

function postBecauseSaid(version, shipped) {
  const [head, rest] = String(version.because || '').split(':');
  if (head === 'restored' && rest) return `restored from ${rest}`;
  if (shipped) return 'shipped';
  if (version.because === 'backfill') return 'what it said before';
  return version.because;
}

function postVersionRow(row, version) {
  const shipped = postIsShipped(row, version);
  return {
    n: version.n,
    title: version.title,
    summary: postSummary(version),
    style: version.style,
    channel_id: version.channel_id ? String(version.channel_id) : null,
    channel_name: postChannelName(version.channel_id),
    pin: Boolean(version.pin),
    saved_at: version.saved_at,
    saved_by: version.saved_by ? String(version.saved_by) : null,
    saved_by_name: version.saved_by ? memberName(version.saved_by) : null,
    via: version.via,
    because: version.because,
    because_said: postBecauseSaid(version, shipped),
    shipped,
    current: version.n === postVersionTop(row),
  };
}

function postVersionList(row) {
  return postVersionsOf(row).map((one) => postVersionRow(row, one));
}

function postVersionFields(one) {
  return [
    String(one.title || ''),
    String(one.body || ''),
    one.style,
    one.channel_id ? String(one.channel_id) : null,
    Boolean(one.pin),
  ].join('\u0000');
}

/** The mock's twin of posts.record_version: a version per press that CHANGED something. */
function postRecordVersion(row, { because, always = false } = {}) {
  const found = postVersionsOf(row);
  const latest = found.length ? found[0] : null;
  if (!always && latest && postVersionFields(latest) === postVersionFields(row)) return null;
  const n = (latest ? latest.n : 0) + 1;
  state.postVersions.push({
    post_id: row.id,
    n,
    title: row.title,
    body: row.body,
    style: row.style,
    channel_id: row.channel_id,
    pin: Boolean(row.pin),
    saved_at: now(),
    saved_by: STAFF.id,
    via: 'website',
    because,
  });
  const keep = postVersionsKeep();
  if (keep > 0) {
    const left = postVersionsOf(row).slice(0, Math.max(1, keep)).map((one) => one.n);
    const dropped = postVersionsOf(row).filter((one) => !left.includes(one.n)).map((one) => one.n);
    if (dropped.length) {
      state.postVersions = state.postVersions
        .filter((one) => one.post_id !== row.id || left.includes(one.n));
      logAction('web.post.versions_trimmed', {
        details: { slug: row.slug, post_id: row.id, versions: dropped.sort(), kept: n, via: 'website' },
      });
    }
  }
  return n;
}

function postVersionNow(row, made) {
  return made === null ? postVersionTop(row) : made;
}

function postWhole(row, said) {
  const found = {
    post: postRow(row),
    styles: postStyles(),
    guard: postGuard(),
    mode: postsMode(),
    shadow: postShadow(),
    notes: postNotes(),
    read_at: now(),
  };
  return said === undefined ? found : { ...found, message: said };
}

function wantedPost(slug) {
  const found = state.posts.find((one) => one.slug === slug);
  if (!found) throw new Refused(404, 'no_such_post', POST_NO_SUCH.split('{slug}').join(slug));
  return found;
}

function postSlugify(text) {
  return String(text || '')
    .toLowerCase()
    .split('\u2019').join('')
    .split("'").join('')
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
}

route('GET', '/api/posts', (context) => {
  requireStaff(context.session);
  return {
    posts: state.posts.map(postRow),
    mode: postsMode(),
    may_edit: true,
    styles: postStyles(),
    guard: postGuard(),
    shadow: postShadow(),
    notes: postNotes(),
    checked_at: now(),
  };
});

route('POST', '/api/posts', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const title = String(body.title || '').trim().slice(0, POST_TITLE_MAX);
  if (!title) throw new Refused(400, 'no_title', POST_TITLE_NEEDED);
  const slug = postSlugify(body.slug || title);
  if (!slug) throw new Refused(400, 'no_slug', POST_SLUG_NEEDED);
  if (state.posts.some((one) => one.slug === slug)) {
    throw new Refused(409, 'slug_taken', POST_SLUG_TAKEN.split('{slug}').join(slug));
  }
  const made = {
    id: state.nextPost++,
    slug,
    title,
    channel_id: null,
    body: '',
    style: 'plain',
    pin: true,
    message_id: null,
    shadow_message_id: null,
    posted_hash: null,
    posted_at: null,
    posted_by: null,
    seeded: false,
    updated_at: now(),
    updated_by: STAFF.id,
  };
  state.posts.push(made);
  logAction('web.post.created', { details: { slug, post_id: made.id, via: 'website' } });
  return postWhole(made, `**${title}** is made. Nothing is in Discord until you press Post it.`);
});

route('GET', '/api/posts/:slug', (context) => {
  requireStaff(context.session);
  return postWhole(wantedPost(context.params.slug));
});

route('PUT', '/api/posts/:slug', async (context) => {
  requireStaff(context.session);
  const row = wantedPost(context.params.slug);
  const body = await context.body();
  const title = 'title' in body ? String(body.title || '').trim().slice(0, POST_TITLE_MAX) : row.title;
  if (!title) throw new Refused(400, 'no_title', POST_TITLE_NEEDED);
  const style = 'style' in body && POST_CAPS[body.style] ? body.style : row.style;
  const wanted = 'body' in body ? String(body.body || '') : row.body;
  if (wanted.length > postCap(style)) {
    throw new Refused(400, 'body_too_long', postTooLong(wanted.length, postCap(style), style, 'saved'));
  }
  if ('channel_id' in body && body.channel_id) {
    if (!postChannelName(body.channel_id)) {
      throw new Refused(400, 'unknown_channel', POST_UNKNOWN_CHANNEL.split('{given}').join(String(body.channel_id)));
    }
    row.channel_id = String(body.channel_id);
  } else if ('channel_id' in body) {
    row.channel_id = null;
  }
  row.title = title;
  row.style = style;
  row.body = wanted;
  if ('pin' in body) row.pin = Boolean(body.pin);
  row.updated_at = now();
  row.updated_by = STAFF.id;
  const made = postRecordVersion(row, { because: 'saved' });
  logAction('web.post.saved', {
    details: { slug: row.slug, post_id: row.id, version: postVersionNow(row, made), via: 'website' },
  });
  return postWhole(row, `**${row.title}** is saved.`);
});

route('POST', '/api/posts/:slug/publish', (context) => {
  requireStaff(context.session);
  const row = wantedPost(context.params.slug);
  const mode = postsMode();
  if (mode === 'off') throw new Refused(409, 'posts_off', POSTS_ARE_OFF);
  const shadow = mode === 'shadow';
  if (!shadow && !row.channel_id) throw new Refused(409, 'no_channel', POST_NO_CHANNEL.split('{title}').join(row.title));
  if (!row.body.trim()) throw new Refused(409, 'nothing_to_post', POST_NOTHING_TO_POST.split('{title}').join(row.title));
  if (row.body.length > postCap(row.style)) {
    throw new Refused(400, 'body_too_long', postTooLong(row.body.length, postCap(row.style), row.style, 'posted'));
  }
  const target = shadow ? postShadowChannel() : row.channel_id;
  if (shadow && !target) throw new Refused(409, 'no_shadow_channel', POST_NO_SHADOW_CHANNEL.split('{title}').join(row.title));
  if (testMode && String(target) !== '800000000000000003') {
    logAction('web.post.would_post', { details: { slug: row.slug, post_id: row.id, via: 'website' } });
    throw new Refused(409, 'test_mode', GUARD);
  }
  const column = shadow ? 'shadow_message_id' : 'message_id';
  const updating = Boolean(row[column]);
  if (!updating) row[column] = String(state.nextPostMessage++);
  row.posted_hash = postHash(row);
  row.posted_at = now();
  row.posted_by = STAFF.id;
  const kinds = shadow
    ? ['web.post.shadow_updated', 'web.post.shadow_posted']
    : ['web.post.updated', 'web.post.posted'];
  const posted = postRecordVersion(row, { because: 'posted' });
  logAction(updating ? kinds[0] : kinds[1], {
    details: {
      slug: row.slug,
      post_id: row.id,
      message_id: row[column],
      version: postVersionNow(row, posted),
      via: 'website',
    },
  });
  // The first real post takes the rehearsal back down; a failure here would be logged and
  // not abort, which the mock has no way to produce.
  if (!shadow && row.shadow_message_id) {
    const was = row.shadow_message_id;
    row.shadow_message_id = null;
    logAction('web.post.shadow_taken_down', {
      details: { slug: row.slug, post_id: row.id, message_id: was, via: 'website' },
    });
  }
  if (row.pin) {
    logAction('web.post.pinned', { details: { slug: row.slug, post_id: row.id, via: 'website' } });
  }
  const where = `#${postChannelName(target)}`;
  if (shadow) {
    return postWhole(
      row,
      updating
        ? `**${row.title}** is updated in ${where} — the shadow copy, because posts are in shadow. Nothing went to its own channel.`
        : `**${row.title}** is posted in ${where} — the shadow copy, because posts are in shadow. Nothing went to its own channel.`,
    );
  }
  return postWhole(
    row,
    updating
      ? `**${row.title}** is updated where it was already posted, in ${where}.`
      : `**${row.title}** is posted in ${where}.`,
  );
});

route('POST', '/api/posts/:slug/takedown', (context) => {
  requireStaff(context.session);
  const row = wantedPost(context.params.slug);
  if (!postIsUp(row)) throw new Refused(409, 'not_posted', POST_NOT_POSTED.split('{title}').join(row.title));
  const copies = [];
  if (row.message_id) copies.push([row.channel_id, row.message_id]);
  if (row.shadow_message_id) copies.push([postShadowChannel(), row.shadow_message_id]);
  for (const [where] of copies) {
    if (testMode && String(where) !== '800000000000000003') {
      logAction('web.post.would_take_down', { details: { slug: row.slug, post_id: row.id, via: 'website' } });
      throw new Refused(409, 'test_mode', GUARD);
    }
  }
  const was = row.message_id;
  const ghost = row.shadow_message_id;
  row.message_id = null;
  row.shadow_message_id = null;
  row.posted_hash = null;
  row.posted_at = null;
  row.posted_by = null;
  logAction('web.post.taken_down', { details: { slug: row.slug, post_id: row.id, message_id: was, shadow_message_id: ghost, via: 'website' } });
  return postWhole(row, `**${row.title}** is taken down. Every word is still here.`);
});

route('GET', '/api/posts/:slug/versions', (context) => {
  requireStaff(context.session);
  const row = wantedPost(context.params.slug);
  const found = postVersionList(row);
  return {
    slug: row.slug,
    versions: found,
    count: found.length,
    keep: postVersionsKeep(),
    read_at: now(),
  };
});

route('GET', '/api/posts/:slug/versions/:n', (context) => {
  requireStaff(context.session);
  const row = wantedPost(context.params.slug);
  const version = postVersionsOf(row).find((one) => String(one.n) === String(context.params.n));
  if (!version) {
    throw new Refused(404, 'no_such_version', POST_NO_SUCH_VERSION
      .split('{n}').join(String(context.params.n))
      .split('{title}').join(row.title));
  }
  return {
    slug: row.slug,
    version: { ...postVersionRow(row, version), body: version.body },
    preview: {
      style: version.style,
      title: version.title,
      body: version.body,
      cap: postCap(version.style),
    },
    read_at: now(),
  };
});

route('POST', '/api/posts/:slug/versions/:n/restore', (context) => {
  requireStaff(context.session);
  const row = wantedPost(context.params.slug);
  const version = postVersionsOf(row).find((one) => String(one.n) === String(context.params.n));
  if (!version) {
    throw new Refused(404, 'no_such_version', POST_NO_SUCH_VERSION
      .split('{n}').join(String(context.params.n))
      .split('{title}').join(row.title));
  }
  if (version.n === postVersionTop(row)) {
    throw new Refused(409, 'version_is_current',
      POST_VERSION_IS_CURRENT.split('{n}').join(String(version.n)));
  }
  row.title = version.title;
  row.body = version.body;
  row.style = version.style;
  row.channel_id = version.channel_id;
  row.pin = Boolean(version.pin);
  row.updated_at = now();
  row.updated_by = STAFF.id;
  const made = postRecordVersion(row, { because: `restored:${version.n}`, always: true });
  logAction('web.post.restored', {
    details: {
      slug: row.slug,
      post_id: row.id,
      from_version: version.n,
      new_version: made,
      via: 'website',
    },
  });
  return {
    ...postWhole(
      row,
      `**${row.title}** is back to version ${version.n}. What it said a moment ago is kept as `
        + `version ${made}, so nothing is lost either way. Press **Post it** to send the change `
        + 'to Discord.',
    ),
    from_version: version.n,
    versions: postVersionList(row),
  };
});

route('DELETE', '/api/posts/:slug', (context) => {
  requireStaff(context.session);
  const row = wantedPost(context.params.slug);
  if (row.seeded) throw new Refused(409, 'seeded_post', POST_SEEDED.split('{slug}').join(row.slug));
  if (postIsUp(row)) throw new Refused(409, 'still_posted', POST_STILL_POSTED.split('{title}').join(row.title));
  state.posts = state.posts.filter((one) => one.id !== row.id);
  state.postVersions = state.postVersions.filter((one) => one.post_id !== row.id);
  logAction('web.post.deleted', { details: { slug: row.slug, post_id: row.id, via: 'website' } });
  return { deleted: row.slug, message: `**${row.title}** is gone.` };
});

// --- meeting minutes (prototype) ---------------------------------------------------------------
// The shapes black_bloc/api/tools/minutes.py answers with. The feature ships OFF, so the list
// carries the "it is off" note, and every staff move still works on a meeting already recorded.

function minutesMode() {
  return String(state.settings.get('minutes_mode') ?? 'off');
}

function minutesGuard() {
  return {
    test_mode: testMode,
    test_channel: testMode ? 'blackbloc-logs' : null,
    said: testMode ? MINUTES_TEST_MODE : null,
  };
}

function minutesHost() {
  return { extension: true, opus: true, transcriber: true, notes_writer: true };
}

function minutesNotes() {
  return minutesMode() === 'on' ? [] : [MINUTES_ARE_OFF];
}

function minutesChannelName(channelId) {
  if (!channelId) return 'nowhere yet';
  const found = CHANNELS.find((one) => String(one.id) === String(channelId));
  return found ? `#${found.name}` : `<#${channelId}>`;
}

function minutesStatusWords(row) {
  if (row.status === 'recording') return 'recording';
  if (row.status === 'writing') return 'writing the notes';
  if (row.status === 'failed') return 'the notes did not get written';
  return 'done';
}

function meetingLinesOf(id) {
  return state.meetingLines.filter((one) => one.meeting_id === id);
}

function meetingRow(row) {
  return {
    id: String(row.id),
    channel_id: row.channel_id ? String(row.channel_id) : null,
    channel_name: minutesChannelName(row.channel_id),
    started_by: String(row.started_by || ''),
    started_by_name: String(row.started_by) === String(STAFF.id) ? STAFF.display_name : null,
    started_at: row.started_at,
    ended_at: row.ended_at,
    ended_reason: row.ended_reason,
    status: row.status,
    status_words: minutesStatusWords(row),
    notes: String(row.notes || ''),
    notes_cap: MINUTES_NOTES_MAX,
    notes_channel_id: row.notes_channel_id ? String(row.notes_channel_id) : null,
    notes_channel_name: minutesChannelName(row.notes_channel_id),
    notes_message_id: row.notes_message_id ? String(row.notes_message_id) : null,
    posted: Boolean(row.notes_message_id),
    lines: meetingLinesOf(row.id).length,
  };
}

function meetingWhole(row, said) {
  const rows = meetingLinesOf(row.id);
  const found = {
    meeting: meetingRow(row),
    transcript: rows.map((one) => ({
      id: String(one.id),
      speaker: one.speaker,
      speaker_id: String(one.speaker_id),
      started_at: one.started_at,
      text: one.text,
    })),
    speakers: [...new Set(rows.map((one) => one.speaker))],
    mode: minutesMode(),
    guard: minutesGuard(),
    host: minutesHost(),
    notes: minutesNotes(),
    read_at: now(),
  };
  return said === undefined ? found : { ...found, message: said };
}

function wantedMeeting(id) {
  const found = state.meetings.find((one) => String(one.id) === String(id));
  if (!found) {
    throw new Refused(404, 'no_such_meeting', MINUTES_NO_SUCH.split('{meeting_id}').join(String(id)));
  }
  return found;
}

function meetingIsOver(row) {
  if (row.status === 'recording') {
    throw new Refused(409, 'still_recording', MINUTES_STILL_RECORDING.split('{meeting_id}').join(String(row.id)));
  }
}

route('GET', '/api/minutes', (context) => {
  requireStaff(context.session);
  return {
    meetings: state.meetings.map(meetingRow),
    mode: minutesMode(),
    may_edit: true,
    guard: minutesGuard(),
    host: minutesHost(),
    notes: minutesNotes(),
    checked_at: now(),
  };
});

route('GET', '/api/minutes/:id', (context) => {
  requireStaff(context.session);
  return meetingWhole(wantedMeeting(context.params.id));
});

route('PUT', '/api/minutes/:id', async (context) => {
  requireStaff(context.session);
  const row = wantedMeeting(context.params.id);
  const body = await context.body();
  const notes = String(body.notes || '').trim();
  if (!notes) throw new Refused(400, 'notes_blank', MINUTES_BLANK);
  if (notes.length > MINUTES_NOTES_MAX) {
    throw new Refused(400, 'notes_too_long', MINUTES_TOO_LONG
      .split('{count}').join(String(notes.length))
      .split('{over}').join(String(notes.length - MINUTES_NOTES_MAX)));
  }
  row.notes = notes;
  row.status = 'done';
  logAction('web.minutes.notes_edited', { details: { meeting: row.id, via: 'website' } });
  return meetingWhole(row, `Saved the notes for meeting **#${row.id}**.`);
});

route('POST', '/api/minutes/:id/write', (context) => {
  requireStaff(context.session);
  const row = wantedMeeting(context.params.id);
  meetingIsOver(row);
  const rows = meetingLinesOf(row.id);
  if (rows.length === 0) throw new Refused(409, 'nothing_heard', MINUTES_NOTHING_HEARD);
  row.notes = MINUTES_SEED_NOTES;
  row.status = 'done';
  logAction('web.minutes.notes_written', { details: { meeting: row.id, lines: rows.length, via: 'website' } });
  return meetingWhole(row, `Notes written for meeting **#${row.id}**.`);
});

route('POST', '/api/minutes/:id/post', (context) => {
  requireStaff(context.session);
  const row = wantedMeeting(context.params.id);
  meetingIsOver(row);
  row.notes_channel_id = testMode ? '800000000000000003' : (row.notes_channel_id || row.channel_id);
  row.notes_message_id = String(state.nextMeetingMessage++);
  logAction('web.minutes.posted', { details: { meeting: row.id, channel: row.notes_channel_id, via: 'website' } });
  return meetingWhole(row, `Posted the notes for meeting **#${row.id}** in ${minutesChannelName(row.notes_channel_id)}.`);
});

route('DELETE', '/api/minutes/:id', (context) => {
  requireStaff(context.session);
  const row = wantedMeeting(context.params.id);
  state.meetings = state.meetings.filter((one) => one.id !== row.id);
  state.meetingLines = state.meetingLines.filter((one) => one.meeting_id !== row.id);
  logAction('web.minutes.deleted', { details: { meeting: row.id, via: 'website' } });
  return {
    deleted: String(row.id),
    message: `Deleted meeting **#${row.id}** — the notes and the transcript went with it.`,
  };
});

// --- guides (G1) ------------------------------------------------------------------------------
// The shapes black_bloc/api/tools/guides.py answers with. F-G3: a member sees member guides,
// published, and nothing else.

const GUIDE_PROBE_LABELS = {
  'golive.linked_count': 'Twitch channels linked',
  'golive.live_now': 'Streaming right now',
  'events.open_count': 'Events waiting on staff',
  'requests.open_count': 'Requests still open',
  'tempvoice.open_rooms': 'Voice rooms open',
  'polls.open_count': 'Polls open',
  'birthdays.next': 'The next birthday',
  'raidtrain.next': 'Raid trains',
  test_mode: 'Test mode',
};
const GUIDE_PROBE_VALUES = {
  'golive.linked_count': '3 linked',
  'golive.live_now': '1 live now',
  'events.open_count': '2 waiting',
  'requests.open_count': '4 open',
  'tempvoice.open_rooms': '1 open',
  'polls.open_count': '2 open',
  'birthdays.next': 'Ada, in 6 days',
  'raidtrain.next': '1 upcoming, 2 of 3 hours taken',
  test_mode: `on \u2014 #${TEST_CHANNEL_NAME}`,
};
const GUIDE_FEATURE_PAGES = {
  core: 'settings.html', automod: 'automod.html', honeypot: 'honeypot.html', mod: 'moderation.html',
  modmail: 'modmail.html', golive: 'golive.html', youtube: 'golive.html', events: 'events.html',
  birthday: 'birthdays.html', tempvoice: 'tempvoice.html', rolemenu: 'rolemenus.html',
  poll: 'polls.html', chat: 'chat.html', request: 'requests.html', pings: 'golive.html',
  raidtrain: 'events.html', applications: 'rolemenus.html', selftest: 'health.html',
  guides: 'guides.html',
};
const GUIDE_CORE_KEYS = ['staff_channel_id', 'log_channel_id', 'modlog_channel_id', 'role_menu_channel_id'];
const GUIDE_NO_SUCH = 'There is no guide called **{slug}**, so nothing was done. It may have been renamed \u2014 open the guides page and pick it from the list.';
const GUIDE_SEEDED = '**{slug}** is one of the guides Black Bloc ships with, so it cannot be deleted \u2014 a deploy would only put it back. Press **Unpublish** instead: members and `/help` stop seeing it and every word you have written is kept.';
const GUIDE_NOT_SEEDED = '**{slug}** was written here rather than shipped with Black Bloc, so there is no original to put back. Nothing was changed.';
const GUIDE_BAD_PICTURE = 'That upload did not arrive as a picture Black Bloc could read, so nothing was uploaded. It is a fault in the page rather than in the file \u2014 reload the guide and try again.';
const GUIDE_WRONG_TYPE = '**{name}** is not a picture Black Bloc can serve. Nothing was uploaded \u2014 send a PNG, a JPEG or a WebP.';
const GUIDE_OFF = 'Guides are turned off for this server, so there is nothing to show. A Lead turns them back on from the dashboard\u2019s Settings page under **guides**.';
const GUIDE_RELEASE = 'v110';
const GUIDE_ALL_STALE = '{count} screenshots are marked for re-shooting. The capture runbook\'s stale list is the whole job.';
const GUIDE_ONE_STALE = '1 screenshot is marked for re-shooting. The capture runbook\'s stale list is the whole job.';
const GUIDE_ALREADY_STALE = 'Every screenshot was already marked.';
const GUIDES_OFF_FOR_STAFF = 'Guides are off for members right now, so nobody but staff can open this page. A Lead turns them back on from the Settings page under **guides**.';

function guideOrigin() {
  return 'https://blackbloc.heygabi.ai';
}

function guideLint(doText, expectText) {
  const said = [];
  const bolds = String(doText || '').match(/\*\*(.+?)\*\*/g) || [];
  if (/\s+(and\s+then|then)\s+/.test(String(doText || '')) || bolds.length > 1) {
    said.push('This step asks for more than one thing. Split it so each step is one press.');
  }
  if (bolds.length === 0) {
    said.push('No control is named. Write the button, select or menu item in **bold**, spelled the way Discord spells it.');
  }
  for (const word of ['You can', 'Simply', 'Just', 'Easily', 'Please']) {
    if (String(doText || '').toLowerCase().startsWith(word.toLowerCase())) {
      said.push(`This step opens with **${word}**. Start with the verb \u2014 Press, Type, Pick \u2014 and say it straight.`);
      break;
    }
  }
  if (String(doText || '').length > 140) said.push(`This step is ${String(doText).length} characters. Keep it under 140.`);
  if (String(expectText || '').length > 200) said.push(`This expect line is ${String(expectText).length} characters. Keep it under 200.`);
  return said;
}

function guideMediaRow(row, alt) {
  return {
    id: String(row.id),
    url: `/api/guides/media/${row.id}`,
    step_id: row.step_id === null ? null : String(row.step_id),
    source: row.source,
    surface: row.surface,
    caption: row.caption,
    width: row.width,
    height: row.height,
    bytes: row.bytes,
    sha256: row.sha256,
    shot_release: row.shot_release,
    shot_at: row.shot_at,
    shot_by: row.shot_by === null ? null : String(row.shot_by),
    shot_by_name: memberName(row.shot_by),
    stale: Boolean(row.stale),
    stale_since: row.stale_since,
    alt: alt || '',
  };
}

function guideStepRow(step) {
  const picture = state.guideMedia.find((one) => one.id === step.media_id) || null;
  return {
    id: String(step.id),
    position: state.guides.find((one) => one.steps.includes(step)).steps.indexOf(step) + 1,
    do_text: step.do_text,
    expect_text: step.expect_text,
    media_id: step.media_id === null ? null : String(step.media_id),
    media: picture ? guideMediaRow(picture, step.do_text) : null,
    seed_do: step.seed_do,
    seed_expect: step.seed_expect,
    can_restore: Boolean(step.seed_do) && (step.seed_do !== step.do_text || step.seed_expect !== step.expect_text),
    warnings: guideLint(step.do_text, step.expect_text),
  };
}

function guideRow(guide) {
  const pictures = state.guideMedia.filter((one) => one.guide_id === guide.id);
  return {
    id: String(guide.id),
    slug: guide.slug,
    title: guide.title,
    goal: guide.goal,
    audience: guide.audience,
    feature: guide.feature,
    feature_page: GUIDE_FEATURE_PAGES[guide.feature] || null,
    feature_mode: state.settings.has(`${guide.feature}_mode`)
      ? String(state.settings.get(`${guide.feature}_mode`) ?? '')
      : null,
    command: guide.command,
    sort: guide.sort,
    published: Boolean(guide.published),
    seeded: Boolean(guide.seeded),
    url: `${guideOrigin()}/guides.html#${guide.slug}`,
    step_count: guide.steps.length,
    media_count: pictures.length,
    stale_count: pictures.filter((one) => one.stale).length,
    updated_at: guide.updated_at,
    updated_by: guide.updated_by === null ? null : String(guide.updated_by),
    updated_by_name: memberName(guide.updated_by),
  };
}

function guideFactRows(guide) {
  if (!state.settings.get('guides_show_facts')) return [];
  const at = now();
  return guide.facts
    .filter((one) => one.kind !== 'setting' || (!GUIDE_CORE_KEYS.includes(one.ref) && !one.ref.endsWith('_log_level')))
    .map((one) => {
      const spec = one.kind === 'setting' ? specOf(one.ref) : null;
      return {
        kind: one.kind,
        ref: one.ref,
        label: one.kind === 'setting' ? one.ref : GUIDE_PROBE_LABELS[one.ref] || one.ref,
        value: one.kind === 'setting' ? String(state.settings.get(one.ref) ?? 'not set') : GUIDE_PROBE_VALUES[one.ref] || 'not readable',
        help: one.kind === 'setting' && spec ? spec[4] : '',
        read_at: at,
      };
    });
}

function guideWhole(guide) {
  return {
    guide: guideRow(guide),
    steps: guide.steps.map(guideStepRow),
    faults: guide.faults.map((one, at) => ({ id: String(one.id), position: at + 1, symptom: one.symptom, answer: one.answer })),
    facts: guideFactRows(guide),
    chosen_facts: guide.facts.map((one) => ({ kind: one.kind, ref: one.ref })),
    media: state.guideMedia.filter((one) => one.guide_id === guide.id).map((one) => guideMediaRow(one, '')),
    read_at: now(),
  };
}

function guidesAreOn() {
  return String(state.settings.get('guides_mode') || 'on') === 'on';
}

/** What the editor's fact picker may offer; the same rule black_bloc/guides.py refuses by. */
function guideFactChoices() {
  return {
    settings: SETTING_SPECS
      .map(([key]) => key)
      .filter((key) => !GUIDE_CORE_KEYS.includes(key) && !key.endsWith('_log_level'))
      .sort(),
    probes: Object.keys(GUIDE_PROBE_LABELS).sort().map((ref) => ({ ref, label: GUIDE_PROBE_LABELS[ref] })),
  };
}

/** G2's hub strip. /api/status is staff-only, so the hub reads the same facts from here. */
function guideRightNow() {
  let on = 0;
  let shadow = 0;
  let off = 0;
  for (const [key] of SETTING_SPECS) {
    if (!key.endsWith('_mode') || NOT_A_FEATURE.includes(key)) continue;
    const mode = String(state.settings.get(key) ?? '');
    if (mode === 'shadow') shadow += 1;
    else if (mode === 'off') off += 1;
    else on += 1;
  }
  return {
    test_mode: testMode,
    test_channel: testMode ? TEST_CHANNEL_NAME : null,
    on,
    shadow,
    off,
  };
}

function wantedGuide(slug, session) {
  const staff = session !== 'member';
  const found = state.guides.find((one) => one.slug === slug);
  const hidden = found && !staff && (!found.published || found.audience === 'staff');
  if (!found || hidden) throw new Refused(404, 'no_such_guide', GUIDE_NO_SUCH.split('{slug}').join(slug));
  return found;
}

function guideSlugify(text) {
  return String(text || '')
    .toLowerCase()
    .split('\u2019').join('')
    .split("'").join('')
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
}

route('GET', '/api/guides', (context) => {
  requireMember(context.session);
  const staff = context.session !== 'member';
  if (!guidesAreOn() && !staff) throw new Refused(409, 'guides_off', GUIDE_OFF);
  const rows = state.guides
    .filter((one) => staff || (one.published && one.audience === 'member'))
    .sort((a, b) => a.sort - b.sort)
    .map(guideRow);
  return {
    guides: rows,
    audience: staff ? 'staff' : 'member',
    may_edit: staff,
    mode: state.settings.get('guides_mode') || 'on',
    stale: staff ? rows.reduce((total, one) => total + one.stale_count, 0) : 0,
    features: Object.entries(GUIDE_FEATURE_PAGES).map(([feature, page]) => ({ feature, page })),
    fact_choices: staff ? guideFactChoices() : { settings: [], probes: [] },
    right_now: guideRightNow(),
    notes: guidesAreOn() ? [] : [GUIDES_OFF_FOR_STAFF],
    checked_at: now(),
  };
});

route('GET', '/api/guides/stale', (context) => {
  requireStaff(context.session);
  const shots = state.guideMedia
    .filter((one) => one.stale)
    .map((one) => {
      const guide = state.guides.find((row) => row.id === one.guide_id);
      return { ...guideMediaRow(one, ''), slug: guide.slug, title: guide.title, feature: guide.feature };
    });
  return { shots, count: shots.length, checked_at: now() };
});

// Registered before the /:slug routes so `stale/all` is never read as a slug.
route('POST', '/api/guides/stale/all', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const reason = String(body.reason || '').trim().slice(0, 200) || null;
  const rows = state.guideMedia.filter((one) => !one.stale);
  for (const one of rows) {
    one.stale = true;
    one.stale_since = now();
  }
  logAction('web.guide.shots_stale', {
    actor_id: STAFF.id,
    reason,
    details: { release: GUIDE_RELEASE, features: ['all'], count: rows.length, reason },
  });
  let message = GUIDE_ALREADY_STALE;
  if (rows.length === 1) message = GUIDE_ONE_STALE;
  else if (rows.length) message = GUIDE_ALL_STALE.split('{count}').join(String(rows.length));
  return { marked: rows.length, message };
});

route('GET', '/api/guides/media/:id', (context) => {
  requireMember(context.session);
  const row = state.guideMedia.find((one) => String(one.id) === String(context.params.id));
  if (!row) {
    throw new Refused(404, 'no_such_media', 'That picture is not one of this server\u2019s guide screenshots, so nothing was shown. It may have been replaced \u2014 reload the guide.');
  }
  return {
    status: 200,
    headers: { 'content-type': 'image/png', 'cache-control': 'private, max-age=86400', etag: `"${row.sha256}"` },
    body: Buffer.from('89504e470d0a1a0a', 'hex'),
  };
});

route('POST', '/api/guides', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const title = String(body.title || '').trim().slice(0, 120);
  const goal = String(body.goal || '').trim().slice(0, 300);
  if (!title || !goal) throw new Refused(400, 'no_title', 'A guide needs a title and a goal, so nothing was saved. Fill both in and save again.');
  const slug = guideSlugify(body.slug || title);
  if (!slug) throw new Refused(400, 'no_slug', 'A guide needs a title Black Bloc can turn into a web address, and that one came out empty, so nothing was made. Use some letters or numbers in the title.');
  if (state.guides.some((one) => one.slug === slug)) {
    throw new Refused(409, 'slug_taken', `There is already a guide at **${slug}**, so nothing was made. Give this one a different title, or edit the one that is there.`);
  }
  const made = {
    id: state.nextGuide++,
    slug,
    title,
    goal,
    audience: body.audience === 'staff' ? 'staff' : 'member',
    feature: body.feature || 'core',
    command: body.command ? String(body.command) : null,
    sort: Number(body.sort || 0),
    published: false,
    seeded: false,
    updated_at: now(),
    updated_by: STAFF.id,
    steps: [],
    faults: [],
    facts: [],
  };
  state.guides.push(made);
  logAction('web.guide.created', { actor_id: STAFF.id, details: { slug, guide_id: made.id } });
  return { ...guideWhole(made), message: `**${title}** is made. It is unpublished until you press Publish.` };
});

route('GET', '/api/guides/:slug', (context) => {
  requireMember(context.session);
  const staff = context.session !== 'member';
  if (!guidesAreOn() && !staff) throw new Refused(409, 'guides_off', GUIDE_OFF);
  const guide = wantedGuide(context.params.slug, context.session);
  return {
    ...guideWhole(guide),
    may_edit: staff,
    fault_files_request: Boolean(state.settings.get('guides_fault_files_request')),
    notes: guidesAreOn() ? [] : [GUIDES_OFF_FOR_STAFF],
  };
});

route('POST', '/api/guides/:slug/confirmed', (context) => {
  requireMember(context.session);
  const staff = context.session !== 'member';
  if (!guidesAreOn() && !staff) throw new Refused(409, 'guides_off', GUIDE_OFF);
  const guide = wantedGuide(context.params.slug, context.session);
  logAction('web.guide.confirmed', {
    actor_id: actorOf(context.session),
    details: { slug: guide.slug, guide_id: guide.id, release: GUIDE_RELEASE },
  });
  return {
    slug: guide.slug,
    release: GUIDE_RELEASE,
    message: `Thank you — **${guide.title}** is marked as working. Staff read the count; nothing else was sent.`,
  };
});

route('PUT', '/api/guides/:slug', async (context) => {
  requireStaff(context.session);
  const guide = wantedGuide(context.params.slug, context.session);
  const body = await context.body();
  const was = guide.published;
  guide.title = String(body.title || guide.title).slice(0, 120);
  guide.goal = String(body.goal || guide.goal).slice(0, 300);
  if (Array.isArray(body.steps)) {
    guide.steps = body.steps.map((one) => ({
      id: one.id ? Number(one.id) : state.nextGuideStep++,
      do_text: String(one.do_text || ''),
      expect_text: one.expect_text ? String(one.expect_text) : null,
      media_id: one.media_id ? Number(one.media_id) : null,
      seed_do: null,
      seed_expect: null,
    }));
  }
  if (Array.isArray(body.faults)) {
    guide.faults = body.faults.map((one, at) => ({ id: at + 1, symptom: String(one.symptom || ''), answer: String(one.answer || '') }));
  }
  if (Array.isArray(body.facts)) guide.facts = body.facts.map((one) => ({ kind: one.kind, ref: one.ref }));
  if ('published' in body) guide.published = Boolean(body.published);
  guide.updated_at = now();
  guide.updated_by = STAFF.id;
  logAction('web.guide.edited', { actor_id: STAFF.id, details: { slug: guide.slug, guide_id: guide.id, changed: 'steps +0 \u22120 ~1, faults +0 \u22120 ~0, facts +0 \u22120 ~0' } });
  let said = `**${guide.title}** is saved.`;
  if (guide.published !== was) {
    logAction(guide.published ? 'web.guide.published' : 'web.guide.unpublished', { actor_id: STAFF.id, details: { slug: guide.slug, guide_id: guide.id } });
    said = guide.published
      ? `**${guide.title}** is published \u2014 members and \`/help\` can see it now.`
      : `**${guide.title}** is unpublished. Staff still see it; members and \`/help\` do not.`;
  }
  return { ...guideWhole(guide), message: said };
});

route('DELETE', '/api/guides/:slug', (context) => {
  requireStaff(context.session);
  const guide = wantedGuide(context.params.slug, context.session);
  if (guide.seeded) throw new Refused(409, 'seeded_guide', GUIDE_SEEDED.split('{slug}').join(guide.slug));
  state.guideMedia = state.guideMedia.filter((one) => one.guide_id !== guide.id);
  state.guides = state.guides.filter((one) => one.id !== guide.id);
  logAction('web.guide.deleted', { actor_id: STAFF.id, details: { slug: guide.slug, guide_id: guide.id } });
  return { deleted: guide.slug, message: `**${guide.title}** is gone.` };
});

route('POST', '/api/guides/:slug/reset', (context) => {
  requireStaff(context.session);
  const guide = wantedGuide(context.params.slug, context.session);
  if (!guide.seeded) throw new Refused(409, 'not_seeded', GUIDE_NOT_SEEDED.split('{slug}').join(guide.slug));
  for (const step of guide.steps) {
    step.do_text = step.seed_do === null ? step.do_text : step.seed_do;
    step.expect_text = step.seed_expect === null ? step.expect_text : step.seed_expect;
  }
  guide.updated_at = now();
  logAction('web.guide.reset', { actor_id: STAFF.id, details: { slug: guide.slug, guide_id: guide.id } });
  return { ...guideWhole(guide), message: `**${guide.title}** is back to the words it shipped with.` };
});

route('POST', '/api/guides/:slug/media', async (context) => {
  requireStaff(context.session);
  const guide = wantedGuide(context.params.slug, context.session);
  const body = await context.body();
  const name = String(body.filename || 'shot.png');
  if (!/\.(png|jpe?g|webp)$/i.test(name)) {
    throw new Refused(415, 'bad_picture', GUIDE_WRONG_TYPE.split('{name}').join(name));
  }
  let raw;
  try {
    raw = Buffer.from(String(body.data || '').split(',').pop(), 'base64');
  } catch (e) {
    throw new Refused(400, 'bad_picture', GUIDE_BAD_PICTURE);
  }
  if (!raw || raw.length === 0) throw new Refused(400, 'bad_picture', GUIDE_BAD_PICTURE);
  if (raw.length > 2 * 1024 * 1024) {
    throw new Refused(413, 'picture_too_big', `That picture is ${Math.round(raw.length / 1024)} KB and Black Bloc keeps guide screenshots under 2.0 MB. Nothing was uploaded \u2014 crop it, or save it again as a PNG at no more than 1600 pixels on its longest side.`);
  }
  const stepId = body.step_id ? Number(body.step_id) : null;
  const step = guide.steps.find((one) => one.id === stepId) || null;
  state.guideMedia = state.guideMedia.filter((one) => !(one.guide_id === guide.id && one.step_id === stepId));
  const made = {
    id: state.nextGuideMedia++,
    guide_id: guide.id,
    step_id: stepId,
    file: `${state.nextGuideMedia}.png`,
    sha256: 'b1'.repeat(32),
    width: 1,
    height: 1,
    bytes: raw.length,
    source: body.source === 'mock' ? 'mock' : 'capture',
    surface: body.surface === 'website' ? 'website' : 'discord',
    shot_release: body.shot_release ? String(body.shot_release) : null,
    shot_by: STAFF.id,
    shot_at: now(),
    caption: body.caption ? String(body.caption) : null,
    stale: false,
    stale_since: null,
  };
  state.guideMedia.push(made);
  if (step) step.media_id = made.id;
  logAction('web.guide.media_replaced', { actor_id: STAFF.id, details: { slug: guide.slug, guide_id: guide.id, media_id: made.id } });
  return {
    media: guideMediaRow(made, step ? step.do_text : ''),
    message: step ? `The picture on step ${guide.steps.indexOf(step) + 1} is replaced.` : `The picture on **${guide.title}** is replaced.`,
  };
});

route('GET', '/api/settings', (context) => {
  requireStaff(context.session);
  return settingsPayload();
});

const SETTINGS_KINDS = ['settings.set', 'settings.clear', 'web.settings.set', 'web.settings.clear'];

/** The settings table has no column for where a change came from; the action log has. */
function viaForKey(key) {
  const found = state.actions.find(
    (row) => SETTINGS_KINDS.includes(row.kind) && String((row.details || {}).key || '') === String(key),
  );
  return found ? viaOfKind(found.kind, found.details) : null;
}

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
      via: viaForKey(row.key),
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
  logAction('web.settings.set', { reason: `${context.params.key} = ${JSON.stringify(value)}`, details: { key: context.params.key, value, via: 'website' } });
  return keyRow(context.params.key);
});

route('DELETE', '/api/settings/:key', (context) => {
  requireStaff(context.session);
  const spec = specOf(context.params.key);
  if (spec === null) throw new Refused(400, 'unknown_key', `Black Bloc has no setting called ${context.params.key}.`);
  state.settings.set(context.params.key, spec[3] ?? null);
  state.audit.unshift({ key: context.params.key, value: spec[3] ?? null, updated_by: STAFF.id, updated_at: now() });
  logAction('web.settings.clear', { reason: context.params.key, details: { key: context.params.key, via: 'website' } });
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

function checkMove(menu, channelId) {
  if (!menu.message_id) throw new Refused(400, 'not_posted', NOT_POSTED_YET);
  if (menu.mode === 'staff') throw new Refused(400, 'staff_menu', `${menu.name} is a staff-assigned menu, so there is no panel to post.`);
  if (!menu.options.length) throw new Refused(400, 'no_options', `${menu.name} has no roles on it yet, so there is nothing to post.`);
  if (state.settings.get('rolemenu_mode') !== 'on') throw new Refused(409, 'rolemenu_off', ROLE_MENUS_OFF);
  if (!CHANNELS.some((channel) => channel.id === channelId)) {
    throw new Refused(400, 'no_such_channel', `${channelId} is not a channel Black Bloc can see, so nothing was moved.`);
  }
  guard('moving a role menu panel');
}

/** The real API takes the old panel down before the new one goes up. */
function movePanel(menu, channelId) {
  checkMove(menu, channelId);
  menu.channel_id = channelId;
  menu.message_id = String(Date.now());
  logAction('web.role_menu.post', { reason: menu.name, target_id: menu.channel_id, details: { menu: menu.name, channel_id: menu.channel_id, message_id: menu.message_id } });
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
  logAction('web.role_menu.create', { reason: name, details: { menu: name, mode: menu.mode } });
  return menuRow(menu);
});

route('PUT', '/api/rolemenus/:name', async (context) => {
  requireStaff(context.session);
  const menu = state.menus.find((entry) => entry.name === context.params.name);
  if (!menu) throw new Refused(404, 'no_menu', `There is no role menu called ${context.params.name}.`);
  const body = await context.body();
  // Asked BEFORE the edit lands, the way the real router does it, so a refused move
  // never leaves a half-saved menu behind.
  const moving = body.channel_id === undefined || body.channel_id === null || body.channel_id === ''
    ? null
    : String(body.channel_id);
  if (moving !== null && moving !== menu.channel_id) checkMove(menu, moving);
  if (body.title !== undefined) menu.title = body.title;
  if (body.description !== undefined) menu.description = body.description;
  if (body.mode !== undefined) menu.mode = body.mode;
  if (body.approval !== undefined) menu.approval = wantedApproval(body.approval);
  if (body.expires_days !== undefined) menu.expires_days = wantedDays(body.expires_days, 'expires_days') || null;
  if (body.retry_days !== undefined) menu.retry_days = wantedDays(body.retry_days, 'retry_days') ?? menu.retry_days;
  if (Array.isArray(body.options)) menu.options = body.options;
  logAction('web.role_menu.edit', { reason: menu.name, details: { menu: menu.name } });
  if (moving !== null && moving !== menu.channel_id) movePanel(menu, moving);
  return menuRow(menu);
});

route('DELETE', '/api/rolemenus/:name', (context) => {
  requireStaff(context.session);
  const at = state.menus.findIndex((entry) => entry.name === context.params.name);
  if (at < 0) throw new Refused(404, 'no_menu', `There is no role menu called ${context.params.name}.`);
  state.menus.splice(at, 1);
  logAction('web.role_menu.delete', { reason: context.params.name, details: { menu: context.params.name } });
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
  logAction('web.role_menu.post', { reason: menu.name, target_id: menu.channel_id, details: { menu: menu.name, channel_id: menu.channel_id, message_id: menu.message_id } });
  return { posted: true, name: menu.name, channel_id: menu.channel_id, message_id: menu.message_id };
});

// The six names black_bloc/cogs/community/role_menus.py:SEED creates; a name this server
// already has is left exactly as it is, options and all.
const SEED_MENUS = ['pronouns', 'playstyle', 'mentoring', 'interests', 'event-alerts', 'runner-status'];

route('POST', '/api/rolemenus/seed', (context) => {
  requireStaff(context.session);
  const created = [];
  const skipped = [];
  for (const name of SEED_MENUS) {
    if (state.menus.some((entry) => entry.name === name)) {
      skipped.push(name);
      continue;
    }
    state.menus.push({
      id: state.nextMenu++,
      name,
      title: name,
      description: null,
      mode: name === 'runner-status' ? 'staff' : 'multiple',
      channel_id: null,
      message_id: null,
      approval: false,
      expires_days: null,
      retry_days: 7,
      options: [],
    });
    created.push(name);
  }
  const parts = [];
  if (created.length) parts.push(`Created: ${created.join(', ')}`);
  if (skipped.length) {
    parts.push(`Already there, left alone: ${skipped.join(', ')}`);
    parts.push('A menu that already exists is left exactly as it is, options and all.');
  }
  parts.push('Pick each one on `/rolemenu` and press **Post it** — except `runner-status`, which staff hand out with **Hand roles out…**.');
  logAction('web.role_menu.seeded', { details: { created, skipped } });
  return { created, skipped, message: parts.join(' · ') };
});

// Roles are changed by the same helper the /rolemenu assign picker uses, and neither asks the
// guard: a member's roles are not a channel, so this is not one of the test-mode refusals.
route('POST', '/api/rolemenus/:name/assign', async (context) => {
  requireStaff(context.session);
  const menu = state.menus.find((entry) => entry.name === context.params.name);
  if (!menu) throw new Refused(404, 'no_such_menu', `This server has no role menu called **${context.params.name}**, so nothing was changed.`);
  if (!(menu.options || []).length) {
    throw new Refused(400, 'no_options', `**${menu.name}** has no roles on it yet, so there is nothing to hand out. Add one to the menu first.`);
  }
  if (state.settings.get('rolemenu_mode') !== 'on') throw new Refused(409, 'rolemenu_off', ROLE_MENUS_OFF);
  const body = await context.body();
  const wanted = String(body.user_id || '');
  if (!MEMBERS.some((member) => member.id === wanted)) {
    throw new Refused(404, 'no_such_member', `**${wanted}** is not somebody Black Bloc can see in this server, so nothing was changed. Pick them from the list rather than typing an id.`);
  }
  const remove = body.remove === true;
  const owned = new Map((menu.options || []).map((option) => [String(option.role_id), option.label]));
  const picked = (body.role_ids || []).map(String).filter((id) => owned.has(id));
  if (picked.length === 0) {
    return {
      assigned: !remove,
      name: menu.name,
      user_id: wanted,
      message: `**${memberName(wanted)}** already has exactly those roles, so nothing changed.`,
    };
  }
  const words = picked.map((id) => owned.get(id)).join(', ');
  logAction(remove ? 'web.role_menu.unassign' : 'web.role_menu.assign', { target_id: wanted, details: { menu_id: menu.id } });
  return {
    assigned: !remove,
    name: menu.name,
    user_id: wanted,
    message: `**${memberName(wanted)}** — ${remove ? 'Removed' : 'Added'}: ${words}`,
  };
});

route('POST', '/api/rolemenus/:name/unpost', (context) => {
  requireStaff(context.session);
  const menu = state.menus.find((entry) => entry.name === context.params.name);
  if (!menu) throw new Refused(404, 'no_such_menu', `This server has no role menu called **${context.params.name}**, so nothing was changed.`);
  if (!menu.message_id) {
    throw new Refused(400, 'not_posted', `**${menu.name}** has no panel up right now, so there was nothing to take down. Post it from the Post a menu section first.`);
  }
  const where = menu.channel_id;
  menu.message_id = null;
  logAction('web.role_menu.unposted', { target_id: where, details: { menu: menu.name, channel_id: where } });
  return {
    unposted: true,
    name: menu.name,
    channel_id: where === null || where === undefined ? null : String(where),
    message: `**${menu.name}**'s panel is down. The menu and its roles are untouched and nobody loses a role — post it again whenever you want it back.`,
  };
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
    platform: row.platform ?? null,
    also_source: row.also_source ?? null,
    also_url: row.also_url ?? null,
    also_platform: row.also_platform ?? null,
    started_at: row.started_at,
    ended_at: row.ended_at,
    mode: row.mode,
    announced_message_id: row.announced_message_id === null ? null : String(row.announced_message_id),
  }));
});

// The Wording card. The real route renders through black_bloc/golive.py; this is the mock's own
// short copy of the same shapes, as every other mock answer is.
const PREVIEW_SAMPLE = {
  name: 'Ada',
  game: 'Celeste',
  title: 'Any% attempts',
  url: 'https://www.twitch.tv/blackbloc',
  platform: 'Twitch',
  duration: '2 h 10 min',
};

function fillWording(template, fields) {
  const filled = String(template || '').replace(/\{(\w+)\}/g, (whole, token) => (
    token in fields ? fields[token] : whole
  ));
  return filled
    .replace(/\(\s*\)|\[\s*\]/g, '')
    .replace(/[ \t]+(?:for|on|in|at|—|–|·)(?=[ \t]*(?:[.,;:!?)\]]|$))/gi, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/[ \t]+([.,;:!?])/g, '$1')
    .trim();
}

function spotlightSessionRow(row) {
  return {
    id: row.id,
    started_at: row.started_at,
    ended_at: row.ended_at,
    title: row.title,
    game: row.game,
    url: row.url,
    mode: row.mode,
    bump_count: row.bump_count,
    announced_message_id: row.announced_message_id === null ? null : String(row.announced_message_id),
  };
}

function spotlightOpen(id) {
  return state.golive.spotlightSessions.find((one) => one.spotlight_id === id && !one.ended_at) || null;
}

function spotlightUntil(row) {
  if (!row.expires_at) return 'kept';
  const when = new Date(row.expires_at);
  return `until ${when.getUTCDate()} ${when.toLocaleString('en', { month: 'short', timeZone: 'UTC' })}`;
}

function spotlightRow(row) {
  const live = spotlightOpen(row.id);
  return {
    id: row.id,
    twitch_login: row.twitch_login,
    display_name: row.display_name || row.twitch_login,
    note: row.note,
    added_by: row.added_by === null ? null : String(row.added_by),
    added_by_name: row.added_by === null ? null : memberName(row.added_by),
    added_at: row.added_at,
    expires_at: row.expires_at,
    kept: !row.expires_at,
    until: spotlightUntil(row),
    bump_hours: row.bump_hours,
    pin: Boolean(row.pin),
    event_id: row.event_id,
    url: `https://www.twitch.tv/${row.twitch_login}`,
    live: live !== null,
    session: live === null ? null : spotlightSessionRow(live),
    sessions: state.golive.spotlightSessions
      .filter((one) => one.spotlight_id === row.id)
      .map(spotlightSessionRow),
  };
}

function wantedSpotlight(params) {
  const row = state.golive.spotlights.find((one) => String(one.id) === String(params.spotlight_id));
  if (!row) {
    throw new Refused(404, 'no_spotlight', 'That spotlight row is not there any more, so nothing was changed. It may have run out, or somebody else may have removed it \u2014 the Go-live page\u2019s Streamers list shows what is left.');
  }
  return row;
}

function spotlightDays(given) {
  if (given === null || given === undefined || String(given).trim() === '') return null;
  if (!/^\d+$/.test(String(given).trim())) {
    throw new Refused(400, 'bad_days', `**${String(given).slice(0, 40)}** is not a number of days, so nothing was changed. Give a whole number of days, or say it is kept for ever.`);
  }
  return Number(String(given).trim());
}

route('GET', '/api/golive/spotlight', (context) => {
  requireStaff(context.session);
  return state.golive.spotlights.map(spotlightRow);
});

route('POST', '/api/golive/spotlight', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const given = String(body.twitch_login || '');
  const login = given.trim().toLowerCase().replace(/^.*twitch\.tv\//, '').split(/[?/]/)[0].replace(/^@/, '');
  if (!login || login.length > 25 || !/^[a-z0-9_]+$/.test(login)) {
    throw new Refused(400, 'bad_login', `**${given || 'nothing'}** is not a Twitch channel name, so nothing was spotlighted. Use the name from the channel address \u2014 the part after twitch.tv/ \u2014 for example \`gamesdonequick\`.`);
  }
  if (state.golive.spotlights.some((one) => one.twitch_login === login)) {
    throw new Refused(409, 'already_spotlit', `**${login}** is already on the spotlight list, so nothing was added. **Extend** on its own row moves the date it runs out instead \u2014 that is the move you want if this is a new marathon on the same channel.`);
  }
  const days = spotlightDays(body.days);
  const keep = body.keep === true || days === null;
  const row = {
    id: state.golive.spotlights.reduce((top, one) => Math.max(top, one.id), 0) + 1,
    twitch_login: login,
    display_name: login,
    note: body.note ?? null,
    added_by: context.session.id,
    added_at: now(),
    expires_at: keep ? null : daysAhead(days),
    bump_hours: body.bump_hours ?? null,
    pin: body.pin === undefined || body.pin === null ? true : Boolean(body.pin),
    event_id: null,
  };
  state.golive.spotlights.push(row);
  logAction('web.golive.spotlight_added', { details: { login, expires_at: row.expires_at } });
  const hours = row.bump_hours || state.settings.get('spotlight_bump_hours') || 4;
  const pinWords = row.pin ? 'pins the announcement for the duration' : 'leaves the announcement unpinned';
  return {
    ...spotlightRow(row),
    message: `**${login}** is on the spotlight list, ${spotlightUntil(row)}. Black Bloc announces it in the go-live channel whenever it goes live, reminds people every ${hours} hours while it runs, and ${pinWords}.`,
  };
});

route('PATCH', '/api/golive/spotlight/:spotlight_id', async (context) => {
  requireStaff(context.session);
  const row = wantedSpotlight(context.params);
  const body = await context.body();
  if (body.keep === true) row.expires_at = null;
  else if ('expires_at' in body) row.expires_at = body.expires_at || null;
  else if (body.days !== undefined && body.days !== null) row.expires_at = daysAhead(spotlightDays(body.days));
  if ('bump_hours' in body) row.bump_hours = body.bump_hours || null;
  if ('pin' in body) row.pin = Boolean(body.pin);
  if ('note' in body) row.note = body.note || null;
  logAction('web.golive.spotlight_updated', { details: { login: row.twitch_login } });
  return { ...spotlightRow(row), message: `**${row.twitch_login}** now runs ${spotlightUntil(row)}.` };
});

route('DELETE', '/api/golive/spotlight/:spotlight_id', (context) => {
  requireStaff(context.session);
  const row = wantedSpotlight(context.params);
  state.golive.spotlights = state.golive.spotlights.filter((one) => one.id !== row.id);
  state.golive.spotlightSessions = state.golive.spotlightSessions.filter((one) => one.spotlight_id !== row.id);
  logAction('web.golive.spotlight_removed', { details: { login: row.twitch_login } });
  return {
    id: row.id,
    twitch_login: row.twitch_login,
    removed: true,
    message: `**${row.twitch_login}** is off the spotlight list. Any announcement it has out there is left as posted; nothing else was changed.`,
  };
});

route('POST', '/api/golive/spotlight/:spotlight_id/bump', (context) => {
  requireStaff(context.session);
  const row = wantedSpotlight(context.params);
  const live = spotlightOpen(row.id);
  if (live === null) {
    throw new Refused(409, 'not_live', `**${row.twitch_login}** is not live right now, so there was nothing to remind anybody about. The reminder is offered again the moment Black Bloc sees it go live.`);
  }
  live.last_bump_at = now();
  live.bump_count += 1;
  logAction('web.golive.spotlight_bumped', { details: { login: row.twitch_login } });
  return {
    ...spotlightRow(row),
    bumped: true,
    message: `Reminded the go-live channel that **${row.twitch_login}** is still live.`,
  };
});

route('GET', '/api/golive/preview', (context) => {
  requireStaff(context.session);
  const value = (key) => state.settings.get(key) ?? (specOf(key) || [])[3] ?? null;
  const fields = { ...PREVIEW_SAMPLE, name: STAFF.display_name || PREVIEW_SAMPLE.name };
  const pingRole = value('golive_ping_role_id');
  const prefix = pingRole ? `<@&${pingRole}> ` : '';
  const suffix = String(value('golive_end_suffix') || '');
  const live = prefix + fillWording(value('golive_template'), fields);
  const template = String(value('golive_end_template') || '').trim();
  const author = String(value('golive_end_author') || '').trim();
  const keep = Boolean(value('golive_end_keep_mention'));
  const plain = live.replace(/^(?:<@&\d+>[ \t]*)+/, '');
  const ended = template
    ? (keep ? prefix : '') + fillWording(template, fields)
    : (keep ? prefix : '') + (plain.endsWith(suffix) ? plain : plain + suffix);
  return {
    live: { text: live, author: `${fields.name} is now live on ${fields.platform}!` },
    ended: {
      text: ended,
      author: author ? fillWording(author, fields) : `${fields.name} was live on ${fields.platform}`,
      footer: suffix.trim() ? `Black Bloc · via Twitch · ${suffix.replace(/^[\s—–\-·|,;:]+/, '')}` : 'Black Bloc · via Twitch',
    },
  };
});

// The Discord mock (2026-09-20). The BOT is the source of truth for every word — see
// black_bloc/preview.py — so this side only has to answer the same SHAPE from the same keys,
// which is what lets a page be developed against the mock and still be honest against the bot.
const PREVIEW_FEATURES = [
  ['golive_live', 'The announcement while they are live', 'golive.html', ['golive_template']],
  ['golive_ended', 'The announcement once the stream has ended', 'golive.html', ['golive_end_template', 'golive_end_author']],
  ['golive_costream', 'The announcement while both platforms are live', 'golive.html', ['golive_costream_template', 'golive_costream_author']],
  ['spotlight_bump', 'The spotlight reminder', 'golive.html', ['spotlight_bump_template']],
  ['frontdoor', 'The front door', 'modmail.html', ['frontdoor_title', 'frontdoor_text', 'frontdoor_ticket_label', 'frontdoor_request_label', 'frontdoor_event_label']],
  ['ticket_button', 'The Open a ticket message', 'modmail.html', ['modmail_panel_title', 'modmail_panel_text']],
  ['rehearsal', 'The line a rehearsal copy carries', 'settings.html', ['rehearsal_note']],
  ['request_filed', 'What a member is told when they file a request', 'requests.html', ['request_filed_line']],
  ['request_card', "A request's card", 'requests.html', []],
  ['event_card', "An event's card", 'events.html', []],
  ['modmail_relay', 'A relayed modmail message', 'modmail.html', []],
  ['post', 'A post', 'posts.html', []],
  ['birthday', 'A birthday announcement', 'birthdays.html', ['birthday_template']],
  ['poll_card', 'A poll, and the line its rehearsal copy carries', 'polls.html', ['poll_shadow_note']],
  ['minutes_notes', 'What minutes post when a meeting starts and ends', 'minutes.html', ['minutes_start_text', 'minutes_notes_title']],
];

const PREVIEW_SAMPLES = {
  golive_live: { ...PREVIEW_SAMPLE, source: 'twitch' },
  golive_ended: { ...PREVIEW_SAMPLE, source: 'twitch' },
  golive_costream: { ...PREVIEW_SAMPLE, source: 'twitch' },
  spotlight_bump: { ...PREVIEW_SAMPLE, source: 'twitch' },
  rehearsal: { channel: '#live-now' },
  request_filed: { request_id: 14 },
  request_card: { what: '', why: '' },
  event_card: { title: '', description: '' },
  modmail_relay: { name: '', text: '' },
  post: { style: 'plain', title: '', body: '' },
  birthday: { name: 'Casey', age: '' },
  poll_card: { question: '', channel: '#announcements' },
  minutes_notes: { notes: '' },
  frontdoor: {},
  ticket_button: {},
};

const PREVIEW_NO_FEATURE = 'Black Bloc draws no preview for **{feature}**, so nothing was shown. That is a fault in the page rather than a problem with your access — reload the dashboard, and tell a Lead if it keeps happening.';
const PREVIEW_NOT_ITS_KEY = '**{key}** is not one of the words {feature} posts, so nothing was drawn. A preview only ever shows a setting inside the message it really belongs to — edit {key} where its own feature lives, or on the Settings page.';

const PREVIEW_BLURPLE = 0x5865f2;

function previewFeature(name) {
  return PREVIEW_FEATURES.find((one) => one[0] === name) || null;
}

function previewPills(...texts) {
  const joined = texts.filter(Boolean).join('\n');
  const roles = [...new Set([...joined.matchAll(/<@&(\d+)>/g)].map((one) => one[1]))]
    .map((id) => ({ id, name: (ROLES.find((r) => String(r.id) === id) || {}).name || 'unknown' }));
  const channels = [...new Set([...joined.matchAll(/<#(\d+)>/g)].map((one) => one[1]))]
    .map((id) => ({ id, name: (CHANNELS.find((c) => String(c.id) === id) || {}).name || 'deleted-channel' }));
  return { roles, channels };
}

function previewEmbedWords(embed) {
  return [embed.title, embed.description, ...(embed.fields || []).flatMap((one) => [one.name, one.value])]
    .filter(Boolean).join('\n');
}

function previewMade(content, embeds = [], components = []) {
  const cards = embeds.filter(Boolean);
  return {
    content: String(content || ''),
    embeds: cards,
    components: components.filter((row) => row && row.length),
    mentions: previewPills(String(content || ''), ...cards.map(previewEmbedWords)),
  };
}

function previewButton(label, style = 'secondary', url = null) {
  return { label: String(label || ''), style: url ? 'link' : style, url, disabled: false, emoji: null };
}

// Mirrors black_bloc/preview.py:platform_facts — the platform owns the address and the
// watcher, so the Preview-as-YouTube chip cannot leave a Twitch link behind.
const PREVIEW_PLATFORMS = {
  twitch: { platform: 'Twitch', url: 'https://twitch.tv/caseyfast', source: 'twitch' },
  youtube: { platform: 'YouTube', url: 'https://youtube.com/watch?v=caseyfast', source: 'youtube' },
};

function previewStreamFacts(sample) {
  const found = PREVIEW_PLATFORMS[String(sample.platform || '').trim().toLowerCase()]
    || PREVIEW_PLATFORMS.twitch;
  return { ...sample, ...found };
}

function previewStreamEmbed(fields, author, footer) {
  return {
    title: fields.title || 'Live now',
    url: fields.url || null,
    color: String(fields.platform).toLowerCase() === 'youtube' ? 0xff0000 : 0x9146ff,
    author: { name: author },
    fields: [{ name: 'Game', value: fields.game || 'something', inline: false }],
    footer: { text: footer },
    timestamp: new Date().toISOString(),
  };
}

const PREVIEW_DRAW = {
  golive_live(read, sample) {
    const fields = previewStreamFacts(sample);
    const ping = read('golive_ping_role_id');
    const content = (ping ? `<@&${ping}> ` : '') + fillWording(read('golive_template'), fields);
    return previewMade(content, [previewStreamEmbed(fields, `${fields.name} is now live on ${fields.platform}!`, `Black Bloc · via ${fields.platform}`)]);
  },
  golive_ended(read, sample) {
    const fields = previewStreamFacts(sample);
    const live = fillWording(read('golive_template'), fields);
    const author = String(read('golive_end_author') || '').trim();
    const content = fillWording(String(read('golive_end_template') || '').trim() || '{live}', { ...fields, live });
    return previewMade(content, [previewStreamEmbed(
      fields,
      author ? fillWording(author, fields) : `${fields.name} was live on ${fields.platform}`,
      `Black Bloc · via ${fields.platform} · stream ended`,
    )]);
  },
  golive_costream(read, sample) {
    const lead = previewStreamFacts(sample);
    const other = PREVIEW_PLATFORMS[lead.source === 'twitch' ? 'youtube' : 'twitch'];
    const fields = { ...lead, also_platform: other.platform, also_url: `<${other.url}>` };
    const author = String(read('golive_costream_author') || '').trim();
    return previewMade(fillWording(read('golive_costream_template'), fields), [previewStreamEmbed(
      fields,
      author ? fillWording(author, fields) : `${fields.name} is now live on ${fields.platform}!`,
      `Black Bloc · via ${fields.platform} + ${other.platform}`,
    )]);
  },
  spotlight_bump(read, sample) {
    return previewMade(fillWording(read('spotlight_bump_template'), previewStreamFacts(sample)));
  },
  frontdoor(read) {
    return previewMade('', [{
      title: String(read('frontdoor_title') || ''),
      description: String(read('frontdoor_text') || ''),
      color: PREVIEW_BLURPLE,
      fields: [],
    }], [[
      previewButton(read('frontdoor_ticket_label'), 'primary'),
      previewButton(read('frontdoor_request_label')),
      previewButton(read('frontdoor_event_label')),
    ]]);
  },
  ticket_button(read) {
    return previewMade('', [{
      title: String(read('modmail_panel_title') || ''),
      description: String(read('modmail_panel_text') || ''),
      color: PREVIEW_BLURPLE,
      fields: [],
    }], [[previewButton('Open a ticket', 'primary')]]);
  },
  rehearsal(read, sample) {
    return previewMade(fillWording(read('rehearsal_note'), { channel: sample.channel || '#live-now' }));
  },
  request_filed(read, sample) {
    return previewMade(String(read('request_filed_line') || '').replace('{request_id}', String(sample.request_id || 14)));
  },
  request_card(read, sample) {
    return previewMade('', [{
      title: 'Request #14',
      color: PREVIEW_BLURPLE,
      author: { name: 'Black in a Flash!' },
      fields: [
        { name: 'Asked for', value: sample.what || 'A pinned index of every guide', inline: false },
        { name: 'Why', value: sample.why || 'people keep asking the same three questions in #general', inline: false },
      ],
      footer: { text: 'Black Bloc · requests' },
    }], [[
      previewButton('Pick up', 'primary'),
      previewButton('Hold'),
      previewButton('Decline', 'danger'),
    ]]);
  },
  event_card(read, sample) {
    return previewMade('', [{
      title: sample.title || 'Movie night — Paprika',
      description: sample.description || 'Subtitles on, chat in the voice room.',
      color: 0xfaa81a,
      fields: [
        { name: 'Who', value: `<@${STAFF.id}>`, inline: true },
        { name: 'Status', value: 'pending', inline: true },
        { name: 'How long', value: '2 hours', inline: true },
      ],
      footer: { text: 'Event #9' },
    }], [[previewButton('Approve', 'success'), previewButton('Not this one', 'danger')]]);
  },
  modmail_relay(read, sample) {
    return previewMade('', [{
      title: 'From the member',
      description: sample.text || 'Someone is posting links in #general again.',
      color: PREVIEW_BLURPLE,
      author: { name: sample.name || 'Casey' },
      fields: [],
      footer: { text: `${sample.name || 'Casey'} · ${STAFF.id}` },
    }]);
  },
  post(read, sample) {
    if (String(sample.style) === 'embed') {
      return previewMade('', [{ title: sample.title || '', description: sample.body || '', fields: [] }]);
    }
    return previewMade(sample.body || '');
  },
  birthday(read, sample) {
    const text = String(read('birthday_template') || '')
      .replace('{name}', sample.name || 'Casey')
      .replace('{age}', String(sample.age || ''));
    return previewMade('', [{ description: text, color: 0x4eefff, fields: [] }]);
  },
  poll_card(read, sample) {
    return previewMade(fillWording(read('poll_shadow_note'), { channel: sample.channel || '#announcements' }), [{
      title: sample.question || 'Which day for the next movie night?',
      description: '```\nSaturday   #######  7  ( 70%)\nSunday     ###      3  ( 30%)\n```',
      color: 0x3ba55d,
      fields: [
        { name: 'Status', value: 'open', inline: true },
        { name: 'Voters', value: '10', inline: true },
      ],
      footer: { text: 'Poll #3' },
    }]);
  },
  minutes_notes(read, sample) {
    return previewMade(String(read('minutes_start_text') || ''), [{
      title: String(read('minutes_notes_title') || ''),
      description: sample.notes || 'Agreed to ship the guide index on Friday.',
      fields: [{ name: 'Where', value: 'nowhere yet', inline: true }],
    }]);
  },
};

route('GET', '/api/preview/features', (context) => {
  requireStaff(context.session);
  return {
    features: PREVIEW_FEATURES.map(([feature, title, where, keys]) => ({
      feature, title, where, keys, sample: { ...(PREVIEW_SAMPLES[feature] || {}) },
    })),
    keys: Object.fromEntries(PREVIEW_FEATURES.flatMap(([feature, , , keys]) => keys.map((key) => [key, feature]))),
  };
});

route('POST', '/api/preview/message', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const found = previewFeature(String(body.feature || ''));
  if (!found) throw new Refused(400, 'no_such_preview', PREVIEW_NO_FEATURE.replace('{feature}', String(body.feature || 'nothing').slice(0, 60)));
  const [feature, title, , keys] = found;
  const overrides = body.overrides || {};
  for (const key of Object.keys(overrides)) {
    if (!keys.includes(key)) {
      throw new Refused(400, 'not_this_features_key', PREVIEW_NOT_ITS_KEY.replace(/\{key\}/g, key.slice(0, 60)).replace('{feature}', title));
    }
  }
  const read = (key) => (
    key in overrides ? overrides[key] : (state.settings.get(key) ?? (specOf(key) || [])[3] ?? null)
  );
  const sample = { ...(PREVIEW_SAMPLES[feature] || {}) };
  for (const [key, value] of Object.entries(body.sample || {})) {
    if (key in sample) sample[key] = String(value === null || value === undefined ? '' : value).slice(0, 4000);
  }
  if (!sample.name) sample.name = PREVIEW_SAMPLE.name;
  return PREVIEW_DRAW[feature](read, sample);
});

// F3. The linked YouTube channels. The mock keeps them beside the go-live state for the same
// reason the bot does: a linked channel going live is announced through go-live, and one page
// shows both.
function youtubeLinkRow(row) {
  return {
    user_id: String(row.user_id),
    user_name: memberName(row.user_id),
    channel_id: row.channel_id,
    handle: row.handle,
    title: row.title,
    linked_at: row.linked_at,
  };
}

route('GET', '/api/youtube/links', (context) => {
  requireStaff(context.session);
  return state.youtube.links.map(youtubeLinkRow);
});

route('POST', '/api/youtube/links', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const memberId = String(body.member_id || '');
  const given = String(body.channel || '').trim();
  if (!memberId) throw new Refused(400, 'bad_request', 'Pick the member this is about first.');
  if (!given) {
    throw new Refused(400, 'bad_request', 'No channel was given, so nothing was linked. Paste the channel address \u2014 the one that starts with youtube.com/channel/UC\u2026, or the @handle.');
  }
  const direct = given.match(/(UC[A-Za-z0-9_-]{22})/);
  const handle = given.match(/^@?([A-Za-z0-9._-]{3,30})$/);
  if (!direct && !handle) {
    throw new Refused(400, 'bad_channel', 'I could not turn **' + given.slice(0, 60) + '** into a YouTube channel id, so nothing was linked. Paste the channel address that starts with youtube.com/channel/UC\u2026, or ask a Lead to set a YouTube API key so handles like @yourname can be looked up.');
  }
  const channelId = direct ? direct[1] : 'UCmockmockmockmockmock1';
  const title = direct ? 'Kurzgesagt \u2013 In a Nutshell' : '@' + handle[1];
  const owner = state.youtube.links.find((link) => link.channel_id === channelId);
  if (owner && String(owner.user_id) !== memberId) {
    throw new Refused(409, 'link_taken', '**' + title + '** is already linked to another member here, so nothing was changed. A YouTube channel can only belong to one member \u2014 if that channel is yours, ask a Lead to remove the other link first.');
  }
  const row = { user_id: memberId, channel_id: channelId, handle: direct ? null : '@' + handle[1], title, linked_at: now() };
  const at = state.youtube.links.findIndex((link) => String(link.user_id) === memberId);
  if (at >= 0) state.youtube.links[at] = row;
  else state.youtube.links.unshift(row);
  logAction('web.youtube.link', { target_id: memberId, details: { channel_id: channelId, title } });
  return Object.assign(youtubeLinkRow(row), {
    message: '**' + (memberName(memberId) || memberId) + '** is linked to ' + title + '. Black Bloc posts when that channel goes live.',
  });
});

route('DELETE', '/api/youtube/links/:member_id', (context) => {
  requireStaff(context.session);
  const at = state.youtube.links.findIndex((link) => String(link.user_id) === context.params.member_id);
  if (at < 0) {
    throw new Refused(404, 'not_linked', '**' + context.params.member_id + '** has no YouTube channel linked, so there was nothing to unlink. The links table shows who has one.');
  }
  state.youtube.links.splice(at, 1);
  logAction('web.youtube.unlink', { target_id: context.params.member_id });
  return { unlinked: true, user_id: context.params.member_id };
});

route('GET', '/api/youtube/status', (context) => {
  requireStaff(context.session);
  return {
    api_key_set: false,
    links: state.youtube.links.length,
    live_mode: keyRow('youtube_live_mode').value ?? keyRow('youtube_live_mode').default,
    live_minutes: keyRow('youtube_live_poll_minutes').default,
    live_end_misses: keyRow('youtube_live_end_misses').default,
    live_running: true,
    last_probe_at: minutesAgo(3),
    last_probe_error: null,
    probed: state.youtube.links.length,
    quota_today: 0,
    botcheck: false,
    live_now: 0,
    reading_live: 0,
  };
});

// Phase 18. `/status` is declared before `/:train_id` because the mock's matcher takes the
// first pattern of the right shape, exactly as FastAPI takes the first route that matches.
const RAID_STATUS_WORDS = {
  open: 'open for sign-ups',
  locked: 'locked — the lineup is set',
  live: 'running now',
  done: 'finished',
  cancelled: 'cancelled',
};
const RAID_MOVES = {
  open: ['locked', 'live', 'cancelled'],
  locked: ['open', 'live', 'cancelled'],
  live: ['done'],
  done: [],
  cancelled: [],
};

function raidSlotsOf(trainId) {
  return state.raidSlots
    .filter((row) => row.train_id === Number(trainId))
    .sort((a, b) => a.position - b.position);
}

function raidTrainOf(trainId) {
  const found = state.raidTrains.find((row) => row.id === Number(trainId));
  if (!found) {
    throw new Refused(404, 'not_found', 'Black Bloc has no raid train **' + trainId + '** in this server, so nothing was done. The table above lists the ones it does have.');
  }
  return found;
}

function raidSlotRow(row) {
  return {
    id: row.id,
    position: row.position,
    starts_at: row.starts_at,
    ends_at: row.ends_at,
    user_id: row.user_id === null ? null : String(row.user_id),
    user_name: row.user_id === null ? null : memberName(row.user_id),
    twitch_login: row.twitch_login,
    claimed_at: row.claimed_at,
    assigned_by: row.assigned_by === null ? null : String(row.assigned_by),
    reminded_at: row.reminded_at,
    checked_in_at: row.checked_in_at,
    state: row.user_id === null ? 'open' : 'taken',
  };
}

function raidTrainRow(row) {
  const slots = raidSlotsOf(row.id);
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    starts_at: row.starts_at,
    slot_minutes: row.slot_minutes,
    slot_count: row.slot_count,
    status: row.status,
    status_word: RAID_STATUS_WORDS[row.status] || row.status,
    filled: slots.filter((one) => one.user_id !== null).length,
    slots_total: slots.length,
    channel_id: row.channel_id,
    lineup_message_id: row.lineup_message_id,
    thread_id: row.thread_id,
    scheduled: Boolean(row.scheduled_event_id),
    cancel_reason: row.cancel_reason,
    created_at: row.created_at,
    organizer_id: String(row.organizer_id),
    organizer_name: memberName(row.organizer_id) || String(row.organizer_id),
    editable: row.status === 'open' || row.status === 'locked',
  };
}

function raidLineup(row) {
  const slots = raidSlotsOf(row.id);
  const lines = ['**' + row.title + '** — raid train', RAID_STATUS_WORDS[row.status] || row.status];
  for (const slot of slots) {
    const who = slot.user_id === null ? '_open_' : '<@' + slot.user_id + '> (https://twitch.tv/' + slot.twitch_login + ')';
    lines.push('`#' + String(slot.position).padStart(2, ' ') + '` ' + who);
  }
  return lines.join('\n');
}

function raidDetail(row) {
  return Object.assign(raidTrainRow(row), {
    slots: raidSlotsOf(row.id).map(raidSlotRow),
    lineup: raidLineup(row),
  });
}

route('GET', '/api/raidtrains/status', (context) => {
  requireStaff(context.session);
  const slots = state.raidSlots;
  return {
    mode: state.settings.get('raidtrain_mode'),
    channel_id: state.settings.get('raidtrain_channel_id') || null,
    running: true,
    last_ok_at: minutesAgo(3),
    last_error: null,
    failures: 0,
    every_minutes: state.settings.get('raidtrain_poll_minutes'),
    trains: state.raidTrains.length,
    upcoming: state.raidTrains.filter((row) => ['open', 'locked', 'live'].includes(row.status)).length,
    slots: slots.length,
    claimed: slots.filter((row) => row.user_id !== null).length,
  };
});

route('GET', '/api/raidtrains', (context) => {
  requireStaff(context.session);
  const scope = context.url.searchParams.get('scope') || 'upcoming';
  const wanted = ['upcoming', 'past', 'all'].includes(scope) ? scope : 'upcoming';
  return state.raidTrains
    .filter((row) => {
      if (wanted === 'all') return true;
      const open = ['open', 'locked', 'live'].includes(row.status);
      return wanted === 'upcoming' ? open : !open;
    })
    .sort((a, b) => String(a.starts_at).localeCompare(String(b.starts_at)))
    .map(raidTrainRow);
});

route('GET', '/api/raidtrains/:train_id', (context) => {
  requireStaff(context.session);
  return raidDetail(raidTrainOf(context.params.train_id));
});

route('POST', '/api/raidtrains', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const title = String(body.title || '').trim().slice(0, 100);
  if (!title) throw new Refused(400, 'bad_request', 'A raid train needs a title, so nothing was made. Give it one and try again.');
  const minutes = Number(body.slot_minutes || state.settings.get('raidtrain_slot_minutes'));
  const count = Number(body.slot_count || 0);
  const startedAt = Date.parse(String(body.start || '').replace(' ', 'T'));
  if (Number.isNaN(startedAt)) {
    throw new Refused(400, 'bad_start', '**' + String(body.start || '').slice(0, 80) + '** is not a date Black Bloc can read, so nothing was submitted. Write it as `YYYY-MM-DD HH:MM` on a 24-hour clock.');
  }
  if (startedAt <= Date.now()) {
    throw new Refused(400, 'start_in_the_past', '**' + String(body.start || '').slice(0, 80) + '** has already gone by, so nothing was submitted. Pick a time in the future.');
  }
  if (minutes < 15 || minutes > 720 || count < 1 || count > 24) {
    throw new Refused(400, 'bad_size', 'A raid train runs 1 to 24 slots of 15 to 720 minutes each, so nothing was made. Discord will not carry a longer lineup in one message.');
  }
  const id = state.nextRaidTrain;
  state.nextRaidTrain += 1;
  const train = {
    id,
    organizer_id: context.session.id,
    title,
    description: String(body.description || '').slice(0, 500) || null,
    starts_at: new Date(startedAt).toISOString(),
    slot_minutes: minutes,
    slot_count: count,
    status: 'open',
    channel_id: state.settings.get('raidtrain_channel_id'),
    lineup_message_id: null,
    thread_id: null,
    scheduled_event_id: null,
    cancel_reason: null,
    created_at: now(),
  };
  state.raidTrains.push(train);
  let nextId = Math.max(0, ...state.raidSlots.map((row) => row.id));
  for (let position = 1; position <= count; position += 1) {
    nextId += 1;
    state.raidSlots.push({
      id: nextId,
      train_id: id,
      position,
      starts_at: new Date(startedAt + minutes * 60000 * (position - 1)).toISOString(),
      ends_at: new Date(startedAt + minutes * 60000 * position).toISOString(),
      user_id: null,
      twitch_login: null,
      claimed_at: null,
      assigned_by: null,
      reminded_at: null,
      checked_in_at: null,
      live_posted_at: null,
    });
  }
  logAction('web.raidtrain.create', { details: { train_id: id, title, slot_minutes: minutes, slot_count: count } });
  return Object.assign(raidTrainRow(train), {
    message: '**' + title + '** is up with ' + count + ' slot(s) of ' + minutes + ' minutes each.',
  });
});

route('POST', '/api/raidtrains/:train_id/slots/:position', async (context) => {
  requireStaff(context.session);
  const train = raidTrainOf(context.params.train_id);
  const slots = raidSlotsOf(train.id);
  const position = Number(context.params.position);
  const slot = slots.find((row) => row.position === position);
  if (!slot) {
    throw new Refused(404, 'no_such_slot', 'This train has no slot **#' + position + '**, so nothing was changed. It runs from #1 to #' + slots.length + ', and the lineup lists every one of them.');
  }
  const body = await context.body();
  const given = body.member_id;
  let said;
  if (given === null || given === undefined || given === '') {
    if (slot.user_id === null) {
      throw new Refused(409, 'already_empty', 'Slot #' + position + ' is already empty, so there was nothing to take off it.');
    }
    logAction('web.raidtrain.unassign', { target_id: slot.user_id, details: { train_id: train.id, position } });
    Object.assign(slot, { user_id: null, twitch_login: null, claimed_at: null, assigned_by: null, reminded_at: null, checked_in_at: null });
    said = 'Slot #' + position + ' is open again.';
  } else {
    const memberId = String(given);
    const link = state.golive.links.find((one) => String(one.user_id) === memberId);
    if (!link && state.settings.get('raidtrain_require_link')) {
      throw new Refused(409, 'not_linked', '**' + (memberName(memberId) || memberId) + '** has no Twitch channel linked, so the lineup cannot say who to raid. They run `/golive` → **Link my Twitch channel**, or a Lead turns `raidtrain_require_link` off.');
    }
    Object.assign(slot, {
      user_id: memberId,
      twitch_login: link ? link.twitch_login : null,
      claimed_at: now(),
      assigned_by: context.session.id,
    });
    logAction('web.raidtrain.assign', { target_id: memberId, details: { train_id: train.id, position } });
    said = 'Slot #' + position + ' now belongs to ' + (memberName(memberId) || memberId) + '.';
  }
  return Object.assign(raidDetail(train), { message: said });
});

route('POST', '/api/raidtrains/:train_id/swap', async (context) => {
  requireStaff(context.session);
  const train = raidTrainOf(context.params.train_id);
  const body = await context.body();
  const first = Number(body.a);
  const second = Number(body.b);
  if (first === second) throw new Refused(400, 'bad_request', 'Those are the same slot, so nothing was changed.');
  const slots = raidSlotsOf(train.id);
  const one = slots.find((row) => row.position === first);
  const other = slots.find((row) => row.position === second);
  if (!one || !other) {
    throw new Refused(404, 'no_such_slot', 'This train has no slot **#' + (one ? second : first) + '**, so nothing was changed. It runs from #1 to #' + slots.length + ', and the lineup lists every one of them.');
  }
  const carried = ['user_id', 'twitch_login', 'claimed_at', 'assigned_by', 'reminded_at'];
  const held = Object.fromEntries(carried.map((name) => [name, one[name]]));
  for (const name of carried) one[name] = other[name];
  for (const name of carried) other[name] = held[name];
  logAction('web.raidtrain.swap', { details: { train_id: train.id, a: first, b: second } });
  return Object.assign(raidDetail(train), { message: 'Slots #' + first + ' and #' + second + ' have changed places.' });
});

route('POST', '/api/raidtrains/:train_id/status', async (context) => {
  requireStaff(context.session);
  const train = raidTrainOf(context.params.train_id);
  const body = await context.body();
  const wanted = String(body.status || '').trim().toLowerCase();
  if (!RAID_STATUS_WORDS[wanted]) {
    throw new Refused(400, 'bad_status', '**' + (wanted || '(nothing)') + '** is not a state a raid train can be in. It is one of open, locked, live, done or cancelled, and only some of those can be reached from where this one is.');
  }
  const allowed = RAID_MOVES[train.status] || [];
  if (!allowed.includes(wanted)) {
    const words = allowed.length === 0
      ? '**' + train.status + '** is the end of the line for a raid train, so nothing was changed.'
      : 'A raid train that is **' + train.status + '** cannot be marked **' + wanted + '**, so nothing was changed. From here it can only become ' + allowed.map((one) => '**' + one + '**').join(', ') + '.';
    throw new Refused(409, 'bad_move', words);
  }
  const reason = String(body.reason || '').trim().slice(0, 500);
  if (wanted === 'cancelled' && !reason) {
    throw new Refused(400, 'bad_request', 'Cancelling tells everybody who signed up, so it needs a reason to tell them. Type one and try again.');
  }
  train.status = wanted;
  train.cancel_reason = wanted === 'cancelled' ? reason : null;
  if (wanted === 'cancelled') logAction('web.raidtrain.cancel', { reason, details: { train_id: train.id, title: train.title } });
  else logAction(wanted === 'locked' ? 'web.raidtrain.lock' : 'web.raidtrain.unlock', { details: { train_id: train.id, title: train.title } });
  return Object.assign(raidDetail(train), { message: '**' + train.title + '** is now **' + wanted + '**.' });
});

// F14. The mock keeps the fan roles beside the go-live state because that is where the real
// bot keeps them (`golive_fan_roles`), and the Pings section that reads them is on the same page.
// A role the mock "makes" is remembered on the ROW, never pushed into ROLES: check.mjs re-seeds
// `state` between routes and ROLES is module-level, so a mutation there would outlive the reset.
function roleOf(roleId) {
  return ROLES.find((role) => role.id === String(roleId)) || null;
}

function followersOf(roleId) {
  return ROSTER.filter((row) => (row.role_ids || []).includes(String(roleId))).length;
}

function fanRoleRow(row) {
  const role = roleOf(row.role_id);
  const name = role ? role.name : (row.role_name || null);
  return {
    member_id: String(row.user_id),
    member: memberName(row.user_id),
    role_id: String(row.role_id),
    role: name,
    followers: name === null ? null : (role ? followersOf(row.role_id) : 0),
    created_at: row.created_at,
    created_by: row.created_by === null ? null : String(row.created_by),
    created_by_name: row.created_by === null ? null : memberName(row.created_by),
  };
}

// Mirrors black_bloc/api/tools/pings.py:listing_row — the list is who has STREAMED, and the
// role is a column on it rather than the thing the list is made of.
function listingRow(row) {
  const held = state.golive.fanRoles.find((one) => String(one.user_id) === String(row.user_id));
  const role = held ? roleOf(held.role_id) : null;
  const name = held ? (role ? role.name : (held.role_name || null)) : null;
  return {
    member_id: String(row.user_id),
    member: memberName(row.user_id),
    listed: Boolean(row.listed),
    hidden_by: row.hidden_by === null ? null : String(row.hidden_by),
    hidden_by_name: row.hidden_by === null ? null : memberName(row.hidden_by),
    hidden_at: row.hidden_at,
    first_live_at: row.first_live_at,
    last_live_at: row.last_live_at,
    live_count: row.live_count,
    platform: row.platform,
    login: row.login,
    role_id: held ? String(held.role_id) : null,
    role: name,
    followers: name === null ? null : (role ? followersOf(held.role_id) : 0),
  };
}

// Mirrors black_bloc/pings_onboarding.py:wanted_prompts. The mock server is never a Community
// guild, so `community` is false and every write refuses in words — which is the half of C5
// the browser can actually be shown.
function onboardingPrompts() {
  const title = String(state.settings.get('pings_onboarding_prompt_title') ?? 'What should ping you?');
  const cap = Number(state.settings.get('pings_onboarding_option_cap') ?? 25);
  const feeds = [];
  const events = state.settings.get('golive_ping_role_id');
  const raid = state.settings.get('raidtrain_ping_role_id');
  if (events && roleOf(events)) feeds.push('Events and go-lives');
  if (raid && roleOf(raid)) feeds.push('Raid trains');
  const listed = new Set(state.golive.streamers.filter((row) => row.listed).map((row) => String(row.user_id)));
  const people = state.golive.fanRoles
    .filter((row) => listed.has(String(row.user_id)) && roleOf(row.role_id))
    .map((row) => ({ title: roleOf(row.role_id).name, followers: followersOf(row.role_id) }))
    .sort((a, b) => b.followers - a.followers);
  const prompts = [];
  if (feeds.length) prompts.push({ title, options: feeds });
  if (people.length) prompts.push({ title: 'Which streamers?', options: people.slice(0, cap).map((one) => one.title) });
  return { prompts, more: Math.max(people.length - cap, 0) };
}

route('GET', '/api/pings/streamers', (context) => {
  requireStaff(context.session);
  return state.golive.fanRoles.map(fanRoleRow);
});

route('POST', '/api/pings/streamers', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const memberId = String(body.member_id || '');
  if (!memberId || !/^[0-9]+$/.test(memberId)) {
    throw new Refused(400, 'bad_request', `**${memberId || 'nothing'}** is not an id Black Bloc can read, so nothing was done. Ids are the long numbers Discord shows under Copy ID.`);
  }
  if (!ROSTER.some((row) => row.id === memberId)) {
    throw new Refused(404, 'no_such_member', `**${memberId}** is not somebody Black Bloc can see in this server, so nothing was changed. Pick them from the list rather than typing an id.`);
  }
  if (state.golive.fanRoles.some((row) => String(row.user_id) === memberId)) {
    throw new Refused(409, 'not_created', `**${memberName(memberId)}** already has a ping role. Nothing was changed; people follow it with **Follow a streamer…** on \`/pings\`.`);
  }
  const given = body.role_id ? String(body.role_id) : null;
  if (given && !roleOf(given)) {
    throw new Refused(400, 'no_such_role', `**${given}** is not a role in this server any more, so nothing was changed. Reload the page and pick the role again.`);
  }
  const name = given ? roleOf(given).name : `${memberName(memberId)} pings`;
  const roleId = given || String(910000000000000000n + BigInt(state.golive.fanRoles.length + 1));
  const row = {
    user_id: memberId,
    role_id: roleId,
    role_name: name,
    created_at: now(),
    created_by: STAFF.id,
  };
  state.golive.fanRoles.push(row);
  logAction('web.pings.fan_role_created', { target_id: memberId, details: { role_id: roleId, role: name, reused: Boolean(given) } });
  return {
    ...fanRoleRow(row),
    message: given
      ? `Used the role **${name}** for **${memberName(memberId)}** and put it on the *streamers* panel. People pick it there, or with **Follow a streamer…** on \`/pings\`.`
      : `Made **${name}** and put it on the *streamers* panel. People pick it there, or with **Follow a streamer…** on \`/pings\`, and Black Bloc mentions it in front of their go-live announcement.`,
  };
});

route('DELETE', '/api/pings/streamers/:member_id', (context) => {
  requireStaff(context.session);
  const memberId = String(context.params.member_id);
  const at = state.golive.fanRoles.findIndex((row) => String(row.user_id) === memberId);
  if (at < 0) {
    throw new Refused(404, 'no_fan_role', `**${memberName(memberId) || memberId}** has no ping role, so there was nothing to take away. \`/pings\` ▸ **Streamers…** shows who has one.`);
  }
  const [row] = state.golive.fanRoles.splice(at, 1);
  const role = roleOf(row.role_id) || (row.role_name ? { name: row.role_name } : null);
  const deleting = state.settings.get('pings_fan_role_delete') !== false && role !== null;
  logAction('web.pings.fan_role_removed', { target_id: memberId, details: { role_id: row.role_id, deleted: deleting } });
  return {
    removed: true,
    member_id: memberId,
    role_id: String(row.role_id),
    message: deleting
      ? `**${memberName(memberId)}** no longer has a ping role, and the Discord role **${role.name}** is gone from the server. Everybody who followed them simply stops being pinged.`
      : `**${memberName(memberId)}** no longer has a ping role here. The Discord role had already been deleted by hand, so there was nothing to take off the server.`,
  };
});

route('POST', '/api/pings/setup', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const given = body && body.role_id ? String(body.role_id) : null;
  if (given && !roleOf(given)) {
    throw new Refused(400, 'no_such_role', `**${given}** is not a role in this server any more, so nothing was changed. Reload the page and pick the role again.`);
  }
  const wanted = String(state.settings.get('pings_events_role_name') ?? 'Events');
  const found = given ? roleOf(given) : ROLES.find((one) => one.name.toLowerCase() === wanted.toLowerCase());
  const created = !found;
  const role = found || { id: String(920000000000000000n + BigInt(ROLES.length)), name: wanted };
  const before = state.settings.get('golive_ping_role_id');
  state.settings.set('golive_ping_role_id', role.id);
  state.settings.set('events_ping_role_id', role.id);
  logAction('web.pings.setup', { details: { role_id: role.id, role: role.name, created } });
  let message = created
    ? `Made the role **${role.name}** and pointed go-live and event pings at it.`
    : (before === role.id
      ? `Both feeds already pointed at **${role.name}**, so nothing was changed.`
      : `Used the role **${role.name}** that was already here and pointed both feeds at it.`);
  message += ' Put it on the *notifications* panel — `/rolemenu` ▸ *notifications* ▸ **Post it**.';
  if (state.settings.get('pings_mode') !== 'on') {
    message += ' Ping roles are still off, so nobody can opt in yet — turn them on with `/settings` ▸ **Turn a feature back on…** or from the dashboard\u2019s Go-live tab.';
  }
  return { role_id: role.id, created, menu: 'notifications', message };
});

route('POST', '/api/pings/raidtrain-role', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const given = body && body.role_id ? String(body.role_id) : null;
  if (given && !roleOf(given)) {
    throw new Refused(400, 'no_such_role', `**${given}** is not a role in this server any more, so nothing was changed. Reload the page and pick the role again.`);
  }
  const found = given ? roleOf(given) : ROLES.find((one) => one.name.toLowerCase() === 'raid trains');
  const created = !found;
  const role = found || { id: String(930000000000000000n + BigInt(ROLES.length)), name: 'Raid trains' };
  const before = state.settings.get('raidtrain_ping_role_id');
  state.settings.set('raidtrain_ping_role_id', role.id);
  logAction('web.pings.raidtrain_setup', { details: { role_id: role.id, role: role.name, created } });
  let message = created
    ? `Made the role **${role.name}** and pointed raid-train pings at it. Members opt in with **Ping me for raid trains** on \`/pings\`.`
    : (before === role.id
      ? `Raid-train pings already pointed at **${role.name}**, so nothing was changed.`
      : `Used the role **${role.name}** that was already here and pointed raid-train pings at it. Members opt in with **Ping me for raid trains** on \`/pings\`.`);
  if (state.settings.get('pings_mode') !== 'on') {
    message += ' Ping roles are still off, so nobody can opt in yet — turn them on with `/settings` ▸ **Turn a feature back on…** or from the dashboard’s Go-live tab.';
  }
  return { role_id: role.id, created, message };
});

route('GET', '/api/pings/list', (context) => {
  requireStaff(context.session);
  return [...state.golive.streamers]
    .sort((a, b) => String(b.last_live_at).localeCompare(String(a.last_live_at)))
    .map(listingRow);
});

route('POST', '/api/pings/list/:member_id', async (context) => {
  requireStaff(context.session);
  const memberId = String(context.params.member_id);
  const body = await context.body();
  const listed = body && body.listed === false ? false : true;
  const row = state.golive.streamers.find((one) => String(one.user_id) === memberId);
  if (!row) {
    throw new Refused(409, 'not_changed', `**${memberName(memberId) || memberId}** is not somebody on this server's streamer list, so nothing was changed. Press **Refresh** and pick again.`);
  }
  if (Boolean(row.listed) === listed) {
    throw new Refused(409, 'not_changed', listed
      ? `**${memberName(memberId)}** is already on the streamer list, so nothing was changed.`
      : `**${memberName(memberId)}** is already off the streamer list, so nothing was changed. **Put me back on the list** puts them back.`);
  }
  row.listed = listed;
  row.hidden_by = listed ? null : STAFF.id;
  row.hidden_at = listed ? null : now();
  logAction(listed ? 'web.pings.streamer_restored' : 'web.pings.streamer_hidden', { target_id: memberId, details: { user_id: memberId, self: false } });
  return {
    ...listingRow(row),
    message: listed
      ? `Done — **${memberName(memberId)}** is back on the streamer list.`
      : `Done — **${memberName(memberId)}** is off the streamer list, so nobody new can follow them and going live does not put them back. **Restore** on this panel puts them back.`,
  };
});

route('GET', '/api/pings/onboarding', (context) => {
  requireStaff(context.session);
  const { prompts, more } = onboardingPrompts();
  return {
    community: false,
    managed: state.golive.onboardingManaged !== false,
    last_synced_at: state.golive.onboardingSyncedAt,
    more_on_pings: more,
    foreign_prompts: 0,
    prompts,
  };
});

route('POST', '/api/pings/onboarding/sync', (context) => {
  requireStaff(context.session);
  if (state.golive.onboardingManaged === false) {
    throw new Refused(409, 'not_managed', 'Black Bloc is not managing this server’s onboarding, so nothing was changed. **Manage onboarding again** on this panel turns it back on.');
  }
  throw new Refused(409, 'no_community', 'This server is not a Community server yet, so Discord has no onboarding screen to put anything on and nothing was changed. Turn Community on in **Server Settings ▸ Enable Community** first; until then the *Notifications* role menu is how members opt in.');
});

// The two words black_bloc/api/tools/events.py:EDITABLE names; every other state is settled.
const EVENTS_EDITABLE = ['pending', 'approved'];

function eventMinutes(row) {
  return row.ends_at ? Math.round((Date.parse(row.ends_at) - Date.parse(row.starts_at)) / 60000) : 120;
}

function eventDuration(minutes) {
  const hours = Math.floor(Math.max(minutes, 0) / 60);
  const rest = Math.max(minutes, 0) % 60;
  if (hours && rest) return `${hours}h ${rest}m`;
  return hours ? `${hours}h` : `${rest}m`;
}

// Mirrors black_bloc/events.py:read_where — a row from before schema 34 reads as `other`.
function eventWhere(row) {
  if ((row.where_kind === 'voice' || row.where_kind === 'text') && row.where_channel_id) {
    return { kind: row.where_kind, channel_id: String(row.where_channel_id), text: '' };
  }
  const text = String(row.location || '').trim().slice(0, 100);
  return text ? { kind: 'other', channel_id: null, text } : { kind: null, channel_id: null, text: '' };
}

function eventWhereLabel(where) {
  if (!where.channel_id) return where.text;
  const channel = CHANNELS.find((one) => String(one.id) === String(where.channel_id));
  if (!channel) return 'a channel that has gone';
  return `${where.kind === 'voice' ? '🔊 ' : '#'}${channel.name}`;
}

// Mirrors black_bloc/events.py:checked_where — every refusal is a sentence, never a bare status.
function checkedWhere(body) {
  const kind = String(body.where_kind || '').trim().toLowerCase();
  const text = String(body.location || '').trim().slice(0, 100);
  if (!kind || kind === 'other') {
    return text ? { kind: 'other', channel_id: null, text } : { kind: null, channel_id: null, text: '' };
  }
  if (!['voice', 'text'].includes(kind)) {
    throw new Refused(400, 'where_refused', `**${kind.slice(0, 40)}** is not a kind of place Black Bloc can set, so nothing was saved. It takes a voice channel, a text channel, or **somewhere else** with the place typed in.`);
  }
  const given = String(body.where_channel_id || '').trim();
  if (!/^\d+$/.test(given)) {
    throw new Refused(400, 'where_refused', 'A voice or text channel has to be picked before it can be saved, so nothing was changed. Pick one from the list, or choose **somewhere else** and type where it is.');
  }
  const channel = CHANNELS.find((one) => String(one.id) === given);
  if (!channel) {
    throw new Refused(400, 'where_refused', `Black Bloc cannot find channel **${given}** on this server, so nothing was saved. It may have been deleted — pick one from the list, or choose **somewhere else** and type it.`);
  }
  if (channel.type !== 'voice' && channel.type !== 'text') {
    throw new Refused(400, 'where_refused', `**${channel.name}** is not somewhere an event can happen, so nothing was saved. Discord takes a voice channel, a stage or a text channel — or **somewhere else** with the place typed in.`);
  }
  return { kind: channel.type, channel_id: given, text: '' };
}

// Send to... — `moved_to` is `kind:id`; `handoff.moved_words` is the wording it reads as.
function movedWord(movedTo) {
  const [kind, ident] = String(movedTo || '').split(':');
  return (kind === 'event' || kind === 'request') && /^\d+$/.test(ident || '')
    ? `${kind} #${ident}`
    : '';
}

function eventRow(row) {
  const minutes = eventMinutes(row);
  const where = eventWhere(row);
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    location: row.location,
    where_kind: where.kind,
    where_channel_id: where.channel_id,
    where_label: eventWhereLabel(where),
    starts_at: row.starts_at,
    ends_at: row.ends_at,
    minutes,
    duration: eventDuration(minutes),
    editable: EVENTS_EDITABLE.includes(row.status),
    announced: Boolean(row.announce_message_id),
    scheduled: Boolean(row.scheduled_event_id),
    status: row.status,
    requester_id: String(row.requester_id),
    requester_name: memberName(row.requester_id),
    decided_by_id: row.decided_by === null || row.decided_by === undefined ? null : String(row.decided_by),
    decided_by_name: memberName(row.decided_by),
    decided_at: row.decided_at,
    deny_reason: row.deny_reason,
    moved_to: row.moved_to === undefined ? null : row.moved_to,
    moved_word: movedWord(row.moved_to),
    review_channel_id: row.review_channel_id === undefined ? null : row.review_channel_id,
    review_kind: row.review_kind === 'post' ? 'post' : 'room',
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

route('GET', '/api/events/:id', (context) => {
  requireStaff(context.session);
  return { event: eventRow(eventOf(context.params.id)) };
});

route('PUT', '/api/events/:id', async (context) => {
  requireStaff(context.session);
  const event = eventOf(context.params.id);
  if (!EVENTS_EDITABLE.includes(event.status)) {
    throw new Refused(409, 'not_editable', `Event **#${event.id}** is **${event.status}**, so its details cannot be changed — only an event still waiting for a decision or already approved can be edited.`);
  }
  const body = await context.body();
  const title = String(body.title || '').trim();
  if (!title) {
    throw new Refused(400, 'event_refused', 'An event needs a name, so nothing was submitted. Put something in the Title box — it is the heading everybody sees on the card.');
  }
  const start = String(body.start || '').trim();
  const when = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(start) ? Date.parse(start.replace(' ', 'T') + 'Z') : NaN;
  if (Number.isNaN(when)) {
    throw new Refused(400, 'event_refused', `**${start}** is not a date Black Bloc can read, so nothing was submitted. Write it as \`YYYY-MM-DD HH:MM\` on a 24-hour clock.`);
  }
  if (when <= Date.now()) {
    throw new Refused(400, 'event_refused', `**${start}** has already gone by, so nothing was submitted. Pick a time in the future.`);
  }
  const raw = String(body.duration || '').trim();
  const parts = raw === '' ? [null, '2', null] : /^(?:(\d{1,4})h)?(?:(\d{1,5})m)?$/.exec(raw.toLowerCase().replace(/\s+/g, ''));
  if (!parts || (raw !== '' && !parts[1] && !parts[2])) {
    throw new Refused(400, 'event_refused', `**${raw}** is not a length Black Bloc can read, so nothing was submitted. Write it as \`1h30m\`, \`2h\` or \`45m\`.`);
  }
  const minutes = Number(parts[1] || 0) * 60 + Number(parts[2] || 0);
  const where = checkedWhere(body);
  event.title = title;
  event.description = String(body.description || '').trim() || null;
  event.location = where.text || null;
  event.where_kind = where.kind;
  event.where_channel_id = where.channel_id;
  event.starts_at = new Date(when).toISOString();
  event.ends_at = new Date(when + minutes * 60000).toISOString();
  logAction('web.event.edited', { target_id: event.requester_id, details: { event_id: event.id, title } });
  const notes = [];
  if (event.announce_message_id) notes.push('The public announcement still says what it said before; Black Bloc does not rewrite one it has already posted.');
  if (event.scheduled_event_id) notes.push('The Discord scheduled event still has the old details — nothing here edits one that was already made.');
  return { event: eventRow(event), message: "Saved, and the review channel's name follows the title.", notes };
});

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

// Part 2D: one canonical `delete_room` on the bot's side, so the mock answers the same way —
// the room goes, and an event still open is called off with it.
route('POST', '/api/events/:id/room/delete', async (context) => {
  requireStaff(context.session);
  const event = eventOf(context.params.id);
  if (!event.review_channel_id) {
    throw new Refused(409, 'no_room', `Event **#${event.id}** has no room of its own any more, so there was nothing to remove.`);
  }
  const body = await context.body();
  const note = String(body.note || '').trim();
  const cancelled = ['pending', 'approved', 'live'].includes(event.status);
  if (cancelled) {
    event.status = 'cancelled';
    event.decided_by = STAFF.id;
    event.decided_at = now();
    logAction('web.event.cancelled', { target_id: event.requester_id, reason: note || 'room_deleted', details: { event_id: event.id } });
  }
  const channel_id = event.review_channel_id;
  event.review_channel_id = null;
  logAction('web.event.channel_deleted', { target_id: event.requester_id, details: { event_id: event.id, channel_id, by: STAFF.id, cancelled } });
  const said = cancelled
    ? `The room is gone. Event #${event.id} is cancelled, and the person who proposed it has been told why.`
    : 'The room is gone.';
  return { event: eventRow(event), message: said };
});

route('POST', '/api/events/forum', (context) => {
  requireStaff(context.session);
  const known = state.settings.get('events_forum_channel_id');
  if (known) {
    throw new Refused(409, 'forum_exists', `<#${known}> is already the events forum, so nothing was made. Clear **events_forum_channel_id** on the events page first if you want a new one.`);
  }
  if (!state.settings.get('modmail_category_id')) {
    throw new Refused(409, 'no_category', '**modmail_category_id** is not pointed at a category Black Bloc can see, so there is nowhere under BlackMail to make the forum. Point it at one with `/modmail` \u25b8 **Setup\u2026** \u25b8 **Ticket category\u2026** first.');
  }
  const channelId = String(Date.now());
  state.settings.set('events_forum_channel_id', channelId);
  logAction('web.event.forum_made', { target_id: channelId, details: { channel_id: channelId } });
  return { made: true, channel_id: channelId, message: `<#${channelId}> is up: a forum under the BlackMail category, with its overwrites, and one tag for each place an event can be.` };
});

// §H: an open room becomes a post. The post first, then the room goes — and the event is NOT
// settled on the way, which is the one thing that separates this from /room/delete.
route('POST', '/api/events/:id/forum', (context) => {
  requireStaff(context.session);
  const event = eventOf(context.params.id);
  if (event.review_kind === 'post') {
    throw new Refused(409, 'already_a_post', `Event #${event.id} is already reviewed in a post, so there is nothing to move. Its own post is where the buttons are.`);
  }
  if (!['pending', 'approved', 'live'].includes(event.status)) {
    throw new Refused(409, 'settled', `Event #${event.id} is **${event.status}**, so it is not moving anywhere — only an event still waiting for a decision, approved or running is worth a post. Its room goes on its own.`);
  }
  if (!event.review_channel_id) {
    throw new Refused(409, 'no_room', `Event #${event.id} has no room of its own any more, so there is nothing to move into the forum. Propose it again if it still needs reviewing.`);
  }
  const forum = state.settings.get('events_forum_channel_id');
  if (!forum) {
    throw new Refused(409, 'no_forum', '**events_forum_channel_id** is blank or points at a channel Black Bloc cannot see, so there is no forum to move it into and nothing was changed. Press **Make the forum** on `/event` ▸ **Settings** ▸ **Rooms…** ▸ **Forum…** first.');
  }
  const was = event.review_channel_id;
  const post = String(Date.now());
  event.review_channel_id = post;
  event.review_kind = 'post';
  logAction('web.event.room_moved', { target_id: event.requester_id, details: { event_id: event.id, from: was, to: post } });
  return {
    event: eventRow(event),
    message: `Event #${event.id} now lives in <#${post}>. The room is gone.`,
  };
});

route('POST', '/api/events/:id/cancel', (context) => {
  requireStaff(context.session);
  const event = eventOf(context.params.id);
  if (event.status === 'cancelled') throw new Refused(409, 'already_decided', 'That event is already cancelled.');
  event.status = 'cancelled';
  event.decided_by = STAFF.id;
  event.decided_at = now();
  logAction('web.event.cancelled', { target_id: event.requester_id, details: { event_id: event.id } });
  return { event: eventRow(event), message: 'Cancelled.' };
});

// Polls (10a, with 10b's create form, panel surface and recurrences).
const POLL_STATUSES = ['draft', 'pending_review', 'open', 'closed', 'archived', 'denied', 'cancelled', 'recurring'];
const POLL_PER_PAGE = 25;
const POLL_PER_PAGE_MAX = 100;

function pollWinner(row) {
  const best = Math.max(0, ...row.options.map((option) => option.votes));
  const top = row.options.filter((option) => option.votes === best && best > 0);
  return top.length === 1 ? top[0].position : null;
}

function pollRow(row) {
  return {
    id: row.id,
    question: row.question,
    kind: row.kind,
    surface: row.surface,
    status: row.status,
    results: row.results,
    multi: Boolean(row.multi),
    anonymous: Boolean(row.anonymous),
    auto_thread: Boolean(row.auto_thread),
    hours: row.hours,
    creator_id: String(row.creator_id),
    creator_name: memberName(row.creator_id),
    channel_id: row.channel_id,
    message_id: row.message_id,
    thread_id: row.thread_id,
    ping_role_id: row.ping_role_id,
    opens_at: row.opens_at,
    closes_at: row.closes_at,
    reminded_at: row.reminded_at,
    closed_at: row.closed_at,
    archived_at: row.archived_at,
    total_votes: row.total_votes,
    decided_by_id: row.decided_by === null || row.decided_by === undefined ? null : String(row.decided_by),
    decided_by_name: memberName(row.decided_by),
    decided_at: row.decided_at,
    deny_reason: row.deny_reason,
    created_at: row.created_at,
    options: row.options.map((option) => ({ ...option })),
    winner_position: pollWinner(row),
    votes_dropped: row.votes_dropped || 0,
    schedule_id: row.schedule_id === undefined || row.schedule_id === null ? null : String(row.schedule_id),
  };
}

const WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
const WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

/** Mirrors black_bloc/polls.py:describe_cadence, so both halves read the same sentence. */
function describeCadence(row) {
  const [kind, detail] = String(row.cadence || '').split(':');
  if (kind === 'weekly' && WEEKDAYS.includes(detail)) {
    return `every ${WEEKDAY_NAMES[WEEKDAYS.indexOf(detail)]} at ${row.at} ${row.tz}`;
  }
  if (kind === 'monthly' && /^\d+$/.test(detail || '')) {
    const at = Number(detail);
    const suffix = at % 100 >= 11 && at % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' }[at % 10] || 'th');
    return `on the ${at}${suffix} of each month at ${row.at} ${row.tz}`;
  }
  return `every day at ${row.at} ${row.tz}`;
}

function pollRecurrenceRow(row) {
  return {
    id: row.id,
    question: row.question,
    kind: row.kind,
    surface: row.surface,
    hours: row.hours,
    anonymous: Boolean(row.anonymous),
    results: row.results,
    creator_id: String(row.creator_id),
    creator_name: memberName(row.creator_id),
    channel_id: row.channel_id,
    cadence: row.cadence,
    cadence_said: describeCadence(row),
    at: row.at,
    tz: row.tz,
    next_at: row.next_at,
    paused: row.next_at === null,
    options: row.options.map((option) => ({ ...option })),
    created_at: row.created_at,
  };
}

function pollRecurrenceOf(id) {
  const found = state.pollRecurrences.find((row) => String(row.id) === String(id));
  if (!found) throw new Refused(404, 'no_such_recurrence', `Black Bloc has no repeating poll #${id}, so nothing was done. It may have been deleted already.`);
  return found;
}

function pollVoteRow(vote) {
  return {
    user_id: String(vote.user_id),
    user_name: memberName(vote.user_id),
    position: vote.position,
    label: vote.label,
    at: vote.at,
  };
}

function pollOf(id) {
  const found = state.polls.find((row) => String(row.id) === String(id));
  if (!found) throw new Refused(404, 'no_such_poll', `Black Bloc has no poll #${id} any more, so nothing was done. The polls page lists the ones it has.`);
  return found;
}

route('GET', '/api/polls', (context) => {
  requireStaff(context.session);
  const wanted = String(context.url.searchParams.get('status') || '').split(',').filter(Boolean);
  for (const part of wanted) {
    if (!POLL_STATUSES.includes(part)) {
      throw new Refused(400, 'unknown_status', `${part} is not a state a poll can be in, so nothing was listed. They are ${POLL_STATUSES.join(', ')}.`);
    }
  }
  const rows = (wanted.length ? state.polls.filter((row) => wanted.includes(row.status)) : state.polls)
    .slice()
    .sort((a, b) => b.id - a.id);
  const page = Math.max(1, Number(context.url.searchParams.get('page') || 1) || 1);
  const perPage = Math.min(POLL_PER_PAGE_MAX, Math.max(1, Number(context.url.searchParams.get('per_page') || POLL_PER_PAGE) || POLL_PER_PAGE));
  const window = rows.slice((page - 1) * perPage, page * perPage);
  return {
    polls: window.map(pollRow),
    total: rows.length,
    shown: window.length,
    page,
    per_page: perPage,
    notes: [],
  };
});

route('POST', '/api/polls', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const labels = Array.isArray(body.options)
    ? body.options.map((one) => String(one).trim()).filter(Boolean)
    : String(body.options || '').split('|').map((one) => one.trim()).filter(Boolean);
  const kind = String(body.kind || 'single');
  const generated = kind === 'yesno' ? ['Yes', 'No'] : kind === 'rating' ? ['1', '2', '3', '4', '5'] : null;
  const slots = kind === 'date' ? dateSlots(body) : null;
  const found = slots || generated || labels;
  if (found.length < 2) {
    throw new Refused(400, 'poll_refused', 'A poll needs at least 2 options and this one has ' + found.length + ', so nothing was posted. Write them separated by `|` — `Pizza | Tacos | Neither` is three.');
  }
  if (found.length > 25) {
    throw new Refused(400, 'poll_refused', `**${found.length}** options is more than the 25 Black Bloc can put on one poll, so nothing was posted. Cut it to 25 or fewer and run it again.`);
  }
  const channelId = body.channel_id || state.settings.get('poll_channel_id');
  if (!channelId) {
    throw new Refused(400, 'no_channel', 'Black Bloc has nowhere to put this poll, so nothing was posted. Pick a channel on the form, or set a default one in the Settings section below.');
  }
  const anonymous = Boolean(body.anonymous);
  const results = String(body.results || 'live');
  const why = anonymous
    ? "Discord's own polls list everybody who voted, so an **anonymous** one cannot be theirs"
    : results === 'close'
      ? "Discord's own polls show the bars as the votes come in and there is no way to hide them"
      : found.length > 10
        ? `**${found.length}** options is more than the 10 a Discord poll carries`
        : null;
  const holding = state.settings.get('poll_review_mode') === 'on';
  const made = {
    id: state.nextPoll++,
    creator_id: STAFF.id,
    question: String(body.question || '').trim(),
    kind,
    surface: why ? 'panel' : 'native',
    status: holding ? 'pending_review' : 'open',
    results,
    multi: kind === 'checkbox' || kind === 'date',
    anonymous,
    auto_thread: Boolean(body.auto_thread),
    hours: Number(body.hours || 24),
    channel_id: String(channelId),
    message_id: holding ? null : '830000000000000010',
    thread_id: null,
    ping_role_id: body.ping_role_id || null,
    opens_at: holding ? null : now(),
    closes_at: holding ? null : daysAhead(1),
    reminded_at: null,
    closed_at: null,
    archived_at: null,
    total_votes: null,
    decided_by: null,
    decided_at: null,
    deny_reason: null,
    created_at: now(),
    votes_dropped: 0,
    options: found.map((label, position) => ({ position, label, votes: 0 })),
  };
  state.polls.push(made);
  logAction('web.poll.created', { details: { poll_id: made.id, kind, surface: made.surface } });
  return {
    poll: pollRow(made),
    message: holding
      ? `**${made.question}** is in — a Lead has to approve it before it posts, and the person who asked is DM'd either way.`
      : `**${made.question}** is up in <#${channelId}>.`,
    note: why
      ? `This one is a Black Bloc panel rather than a Discord poll, because ${why}. People vote with the buttons under it; everything else works the same.`
      : null,
  };
});

/** The same shape black_bloc/polls.py:date_slots writes: plain labels in the server's zone. */
function dateSlots(body) {
  const start = new Date(String(body.start || '').replace(' ', 'T'));
  if (Number.isNaN(start.getTime())) {
    throw new Refused(400, 'poll_refused', `**${body.start || 'nothing'}** is not a date Black Bloc can read, so nothing was posted. Write it as \`2026-09-05\`, or \`2026-09-05 19:00\` when the time of day matters.`);
  }
  const count = Math.max(2, Math.min(25, Number(body.slots || 5)));
  const step = Math.max(1, Number(body.step || 1));
  const hours = String(body.step_unit || 'days') === 'hours';
  const made = [];
  for (let n = 0; n < count; n += 1) {
    const at = new Date(start.getTime() + n * step * (hours ? 3600000 : 86400000));
    const day = at.toUTCString().slice(0, 11).trim().replace(',', '');
    made.push(hours ? `${day} · ${at.getUTCHours() % 12 || 12} ${at.getUTCHours() < 12 ? 'am' : 'pm'}` : day);
  }
  return made;
}

route('GET', '/api/polls/requests', (context) => {
  requireStaff(context.session);
  return state.polls.filter((row) => row.status === 'pending_review').map(pollRow);
});

route('GET', '/api/polls/recurrences', (context) => {
  requireStaff(context.session);
  return state.pollRecurrences.map(pollRecurrenceRow);
});

/** Mirrors black_bloc/polls.py:cadence_token — the one string the row carries. */
function cadenceToken(cadence, day) {
  const kind = String(cadence || '').trim().toLowerCase();
  if (kind === 'daily') return 'daily';
  if (kind === 'weekly') {
    const wanted = String(day || '').trim().toLowerCase().slice(0, 3);
    return WEEKDAYS.includes(wanted) ? `weekly:${wanted}` : null;
  }
  if (kind === 'monthly') {
    const at = Number(String(day || '').trim());
    return Number.isInteger(at) && at >= 1 && at <= 28 ? `monthly:${at}` : null;
  }
  return null;
}

route('POST', '/api/polls/recurrences', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const kind = String(body.kind || 'single');
  if (kind === 'date') {
    throw new Refused(400, 'not_a_recurrence', 'A **date** poll cannot recur, so nothing was saved — its slots are fixed days, and the second time round it would be asking about a day that has been and gone. Make a one-off date poll when you need one, or recur a checkbox poll with the days written on it.');
  }
  const token = cadenceToken(body.cadence, body.day);
  if (!token) {
    throw new Refused(400, 'not_a_recurrence', `**${body.day || body.cadence || 'nothing'}** is not a day of the week, so nothing was saved. A weekly poll runs on one of ${WEEKDAYS.join(', ')}.`);
  }
  if (!/^\d{1,2}:\d{2}$/.test(String(body.at || ''))) {
    throw new Refused(400, 'not_a_recurrence', `**${body.at || 'nothing'}** is not a time of day Black Bloc can read, so nothing was saved. Write it on the 24-hour clock — \`09:00\`, \`19:30\`.`);
  }
  const labels = Array.isArray(body.options)
    ? body.options.map((one) => String(one).trim()).filter(Boolean)
    : String(body.options || '').split('|').map((one) => one.trim()).filter(Boolean);
  const found = kind === 'yesno' ? ['Yes', 'No'] : kind === 'rating' ? ['1', '2', '3', '4', '5'] : labels;
  if (found.length < 2) {
    throw new Refused(400, 'poll_refused', `A poll needs at least 2 options and this one has ${found.length}, so nothing was posted. Write them separated by \`|\` — \`Pizza | Tacos | Neither\` is three.`);
  }
  const channelId = body.channel_id || state.settings.get('poll_channel_id');
  if (!channelId) {
    throw new Refused(400, 'no_channel', 'Black Bloc has nowhere to put this poll, so nothing was posted. Pick a channel on the form, or set a default one in the Settings section below.');
  }
  // next_at is black_bloc/polls.py:next_occurrence's sum in the bot; the mock only has to carry
  // a real instant, the way the resume half of the pause route below already does.
  const made = {
    id: state.nextPoll++,
    creator_id: STAFF.id,
    question: String(body.question || '').trim(),
    kind,
    surface: 'native',
    hours: Number(body.hours || 24),
    anonymous: Boolean(body.anonymous),
    results: String(body.results || 'live'),
    channel_id: String(channelId),
    cadence: token,
    at: String(body.at),
    tz: String(body.tz || 'America/Phoenix'),
    next_at: daysAhead(1),
    created_at: now(),
    options: found.map((label, position) => ({ position, label, votes: 0 })),
  };
  state.pollRecurrences.push(made);
  logAction('web.poll.created', { details: { poll_id: made.id, kind, surface: made.surface } });
  logAction('web.poll.recur_created', { details: { recurrence_id: made.id, cadence: token, at: made.at, tz: made.tz } });
  return {
    recurrence: pollRecurrenceRow(made),
    message: `**${made.question}** will run ${describeCadence(made)}. Nothing is posted yet — the Repeating section above says when the first one opens, and Pause stops it at any time.`,
  };
});

route('POST', '/api/polls/recurrences/:id/pause', async (context) => {
  requireStaff(context.session);
  const row = pollRecurrenceOf(context.params.id);
  const body = await context.body();
  const pausing = body.paused === undefined ? true : Boolean(body.paused);
  row.next_at = pausing ? null : daysAhead(1);
  logAction(pausing ? 'web.poll.recur_paused' : 'web.poll.recur_resumed', { details: { recurrence_id: row.id } });
  return {
    recurrence: pollRecurrenceRow(row),
    message: pausing
      ? `**${row.question}** is paused. Nothing opens until it is started again.`
      : `**${row.question}** is running again.`,
  };
});

route('DELETE', '/api/polls/recurrences/:id', (context) => {
  requireStaff(context.session);
  const row = pollRecurrenceOf(context.params.id);
  state.pollRecurrences = state.pollRecurrences.filter((one) => one.id !== row.id);
  logAction('web.poll.recur_deleted', { details: { recurrence_id: row.id, question: row.question } });
  return {
    recurrence_id: String(row.id),
    message: `**${row.question}** will not run again. Polls it already opened are untouched.`,
  };
});

route('POST', '/api/polls/requests/:id/approve', (context) => {
  requireStaff(context.session);
  const poll = pollOf(context.params.id);
  if (poll.status !== 'pending_review') {
    throw new Refused(409, 'not_waiting', `Poll #${poll.id} is ${poll.status}, so it is not waiting on a decision any more.`);
  }
  // No guard() here on purpose: black_bloc/api/tools/polls.py refuses in test mode only when
  // the poll's own channel is not the test channel, and every fixture poll is in it.
  poll.status = 'open';
  poll.decided_by = STAFF.id;
  poll.decided_at = now();
  poll.opens_at = now();
  poll.message_id = '830000000000000009';
  logAction('web.poll.approved', { target_id: poll.creator_id, details: { poll_id: poll.id } });
  return { poll: pollRow(poll), message: `Approved and posted: https://discord.test/${poll.message_id}` };
});

route('POST', '/api/polls/requests/:id/deny', async (context) => {
  requireStaff(context.session);
  const poll = pollOf(context.params.id);
  const body = await context.body();
  if (!String(body.reason || '').trim()) {
    throw new Refused(400, 'no_reason', 'A denied poll needs one line the person who asked is sent, so nothing was done. Say why and send it again.');
  }
  if (poll.status !== 'pending_review') {
    throw new Refused(409, 'not_waiting', `Poll #${poll.id} is ${poll.status}, so it is not waiting on a decision any more.`);
  }
  poll.status = 'denied';
  poll.deny_reason = body.reason;
  poll.decided_by = STAFF.id;
  poll.decided_at = now();
  poll.closed_at = now();
  logAction('web.poll.denied', { target_id: poll.creator_id, reason: body.reason, details: { poll_id: poll.id } });
  return { poll: pollRow(poll), message: 'Denied, and the person who asked has been told why.' };
});

route('GET', '/api/polls/:id', (context) => {
  requireStaff(context.session);
  const poll = pollOf(context.params.id);
  const votes = poll.anonymous ? [] : state.pollVotes.filter((vote) => vote.poll_id === poll.id);
  return { poll: pollRow(poll), votes: votes.map(pollVoteRow) };
});

route('POST', '/api/polls/:id/end', (context) => {
  requireStaff(context.session);
  const poll = pollOf(context.params.id);
  if (poll.status !== 'open') {
    throw new Refused(409, 'not_closeable', `Poll #${poll.id} is ${poll.status} already, so there was nothing to close.`);
  }
  poll.status = 'closed';
  poll.closed_at = now();
  poll.total_votes = poll.options.reduce((sum, option) => sum + option.votes, 0);
  logAction('web.poll.closed', { target_id: poll.creator_id, details: { poll_id: poll.id } });
  return { poll: pollRow(poll), message: `Poll #${poll.id} is closed and the result is posted.` };
});

route('POST', '/api/polls/:id/cancel', (context) => {
  requireStaff(context.session);
  const poll = pollOf(context.params.id);
  if (!['draft', 'pending_review', 'open'].includes(poll.status)) {
    throw new Refused(409, 'not_cancellable', `Poll #${poll.id} is ${poll.status} already, so there was nothing to cancel.`);
  }
  poll.status = 'cancelled';
  poll.closed_at = now();
  logAction('web.poll.cancelled', { target_id: poll.creator_id, details: { poll_id: poll.id } });
  return { poll: pollRow(poll), message: `Poll #${poll.id} is cancelled. No result was published.` };
});

route('GET', '/api/polls/:id/export.csv', (context) => {
  // NOT in contract.json: check.mjs reads JSON shapes, and this one answers text/csv.
  requireStaff(context.session);
  const poll = pollOf(context.params.id);
  const lines = [
    'poll_id,question,status,closed_at,total_votes',
    `${poll.id},"${poll.question}",${poll.status},${poll.closed_at || ''},${poll.total_votes || 0}`,
    '',
    'position,option,votes',
    ...poll.options.map((option) => `${option.position},"${option.label}",${option.votes}`),
    '',
  ];
  if (poll.anonymous) {
    lines.push('note,"This poll was run without a voter list, so there is nothing per-person to export."');
  } else {
    lines.push('user_id,user_name,position,option,at');
    for (const vote of state.pollVotes.filter((row) => row.poll_id === poll.id)) {
      lines.push(`${vote.user_id},"${memberName(vote.user_id)}",${vote.position},"${vote.label}",${vote.at}`);
    }
  }
  return {
    status: 200,
    body: `${lines.join('\n')}\n`,
    headers: { 'content-type': 'text/csv; charset=utf-8', 'content-disposition': `attachment; filename="poll-${poll.id}.csv"` },
  };
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

function roomRow(row) {
  const live = CHANNELS.find((channel) => channel.id === String(row.channel_id)) || null;
  return {
    channel_id: String(row.channel_id),
    name: row.name ?? (live ? live.name : null),
    gone: live === null,
    owner_id: String(row.owner_id),
    owner_name: memberName(row.owner_id),
    creator_id: String(row.creator_id),
    created_at: row.created_at,
    connected: row.connected ?? 0,
    user_limit: row.user_limit ?? 0,
    locked: row.locked === true,
    hidden: row.hidden === true,
  };
}

// The real gate on a room action is black_bloc/cogs/community/tempvoice.py:may_act_in — the
// room has to sit in the test channel's own category, because a channel edit is a side effect
// guard.py cannot see. A room spawned from a lobby the guard placed is in that category, which
// is why these four are not in check.mjs's GUARDED list.
function roomFor(given) {
  const wanted = String(given || '');
  const row = state.tempvoice.find((one) => String(one.channel_id) === wanted);
  if (!row) {
    throw new Refused(404, 'no_such_room', 'Black Bloc is not keeping track of a temporary voice channel with that id, so nothing was changed. The Open now list on this page is the ones it knows about.');
  }
  const live = CHANNELS.find((channel) => channel.id === wanted) || null;
  const test = CHANNELS.find((channel) => channel.id === '800000000000000003') || null;
  if (live === null) {
    throw new Refused(404, 'channel_gone', 'That temporary voice channel is gone, so nothing was changed. Join the join-to-create channel again to get a fresh one.');
  }
  if (testMode && live.category_id !== (test ? test.category_id : null)) {
    throw new Refused(409, 'test_mode', `**${live.name}** sits outside the test channel's category, so test mode stopped that change and nothing happened.`);
  }
  return { row, live };
}

route('GET', '/api/tempvoice/channels', (context) => {
  requireStaff(context.session);
  return state.tempvoice.map(roomRow);
});

route('POST', '/api/tempvoice/rooms/:channel_id/rename', async (context) => {
  requireStaff(context.session);
  const { row } = roomFor(context.params.channel_id);
  const wanted = String((await context.body()).name || '').trim().slice(0, 100);
  if (!wanted) {
    throw new Refused(400, 'no_name', 'A channel needs a name, so nothing was changed. Type what it should be called and save again.');
  }
  row.name = wanted;
  logAction('web.tempvoice.rename', { target_id: row.channel_id, details: { name: wanted } });
  return { room: roomRow(row), message: `Renamed to **${wanted}**, and remembered for next time.` };
});

route('POST', '/api/tempvoice/rooms/:channel_id/limit', async (context) => {
  requireStaff(context.session);
  const { row } = roomFor(context.params.channel_id);
  const given = (await context.body()).limit;
  const value = Number(given);
  if (!/^\d+$/.test(String(given ?? '')) || value < 0 || value > 99) {
    throw new Refused(400, 'bad_limit', `**${given}** is not a number of people Black Bloc can use, so nothing was changed. Pick a whole number from 0 to 99 — 0 means no limit.`);
  }
  row.user_limit = value;
  logAction('web.tempvoice.limit', { target_id: row.channel_id, details: { user_limit: value } });
  return {
    room: roomRow(row),
    message: value === 0 ? 'Anyone can join now.' : `Capped at **${value}** people.`,
  };
});

route('POST', '/api/tempvoice/rooms/:channel_id/lock', async (context) => {
  requireStaff(context.session);
  const { row } = roomFor(context.params.channel_id);
  const want = (await context.body()).locked !== false;
  if (want === row.locked) {
    return { room: roomRow(row), message: `This channel is already ${want ? 'locked' : 'unlocked'}, so nothing was changed.` };
  }
  row.locked = want;
  logAction(want ? 'web.tempvoice.lock' : 'web.tempvoice.unlock', { target_id: row.channel_id });
  return {
    room: roomRow(row),
    message: want ? 'Locked — nobody new may join.' : 'Unlocked — anyone may join.',
  };
});

route('POST', '/api/tempvoice/rooms/:channel_id/hide', async (context) => {
  requireStaff(context.session);
  const { row } = roomFor(context.params.channel_id);
  const want = (await context.body()).hidden !== false;
  if (want === row.hidden) {
    return { room: roomRow(row), message: `This channel is already ${want ? 'hidden' : 'visible to everyone'}, so nothing was changed.` };
  }
  row.hidden = want;
  logAction(want ? 'web.tempvoice.hide' : 'web.tempvoice.show', { target_id: row.channel_id });
  return {
    room: roomRow(row),
    message: want ? 'Hidden — only people already in it can see it.' : 'Visible again to everyone.',
  };
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
    throw new Refused(404, 'not_a_lobby', `**${wanted}** is not one of Black Bloc's join-to-create channels, so nothing was forgotten. \`/voice\` lists the ones it knows about.`);
  }
  state.settings.set('tempvoice_creator_ids', ids.filter((id) => id !== wanted));
  logAction('web.tempvoice.creator_removed', { target_id: wanted });
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
  logAction('web.honeypot.banned', { target_id: hit.user_id, details: { hit_id: hit.id } });
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
    note: row.note ?? null,
    note_by: row.note_by === undefined || row.note_by === null ? null : String(row.note_by),
    note_at: row.note_at ?? null,
    voided_at: row.voided_at ?? null,
    voided_by: row.voided_by === undefined || row.voided_by === null ? null : String(row.voided_by),
    void_reason: row.void_reason ?? null,
  };
}

function wantedCase(context) {
  const found = state.cases.find((row) => String(row.id) === String(context.params.id));
  if (!found) throw new Refused(404, 'no_case', 'There is no case with that number.');
  return found;
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
  logAction('web.automod.warned', { target_id: found.user_id, details: { case_id: found.id } });
  return { applied: true, case_id: found.id, message: `Case ${found.id} was carried out: ${found.done.join(', ')}.` };
});

route('POST', '/api/mod/cases/:id/reason', async (context) => {
  requireStaff(context.session);
  const found = wantedCase(context);
  const body = await context.body();
  const said = String(body.reason || '').trim();
  if (!said) throw new Refused(400, 'bad_reason', 'A case with no reason is a case nobody can read later, so nothing was changed.');
  found.reason = said;
  logAction('web.case.reason_edited', { target_id: found.user_id, details: { case_id: found.id } });
  return { done: true, case_id: found.id, message: `Case **#${found.id}**'s reason now reads what you wrote.` };
});

route('POST', '/api/mod/cases/:id/note', async (context) => {
  requireStaff(context.session);
  const found = wantedCase(context);
  const body = await context.body();
  const said = String(body.note || '').trim();
  if (!said) throw new Refused(400, 'bad_note', 'An empty note is a note nobody can read later, so nothing was changed.');
  found.note = said;
  found.note_by = context.session.id;
  found.note_at = new Date().toISOString();
  logAction('web.case.noted', { target_id: found.user_id, details: { case_id: found.id } });
  return { done: true, case_id: found.id, message: `Case **#${found.id}** carries your note.` };
});

route('POST', '/api/mod/cases/:id/void', async (context) => {
  requireStaff(context.session);
  const found = wantedCase(context);
  const body = await context.body();
  const said = String(body.reason || '').trim();
  if (!said) throw new Refused(400, 'bad_reason', 'Cancelling a case with no reason leaves the next moderator guessing, so nothing was changed.');
  if (found.voided_at) throw new Refused(409, 'already_voided', 'Somebody voided this case a moment ago, so nothing was done twice.');
  found.voided_at = new Date().toISOString();
  found.voided_by = context.session.id;
  found.void_reason = said;
  logAction('web.case.voided', { target_id: found.user_id, details: { case_id: found.id } });
  return { done: true, case_id: found.id, message: `Case **#${found.id}** is marked cancelled. It is still on the record.` };
});

route('POST', '/api/mod/cases/:id/restore', (context) => {
  requireStaff(context.session);
  const found = wantedCase(context);
  if (!found.voided_at) throw new Refused(409, 'not_voided', 'Somebody restored this case a moment ago, so nothing was done twice.');
  found.voided_at = null;
  found.voided_by = null;
  found.void_reason = null;
  logAction('web.case.restored', { target_id: found.user_id, details: { case_id: found.id } });
  return { done: true, case_id: found.id, message: `Case **#${found.id}** is back on the record as it was.` };
});

const MOD_ACTIONS = ['warn', 'timeout', 'untimeout', 'kick', 'ban', 'unban'];
// The shared punish helpers log what HAPPENED, not what was asked for, and the dashboard now
// goes through them rather than leaving a second line of its own.
const MOD_KIND_DONE = {
  warn: 'warned',
  timeout: 'timed_out',
  untimeout: 'untimed_out',
  kick: 'kicked',
  ban: 'banned',
  unban: 'unbanned',
};

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
    logAction(`web.mod.${MOD_KIND_DONE[action] || action}`, { target_id: row.user_id, reason: row.reason });
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
  logAction('web.automod.rule', { reason: context.params.name, details: { rule: context.params.name } });
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
    practice: Boolean(ticket.practice),
    source: ticket.source || 'dm',
    opened_by_id: ticket.opened_by === null || ticket.opened_by === undefined ? null : String(ticket.opened_by),
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
  logAction('web.modmail.closed', { target_id: ticket.user_id, reason: ticket.close_reason, details: { ticket_id: ticket.id, silent: Boolean(body.silent) } });
  return { closed: true, ticket: ticketRow(ticket), transcript: true };
});

route('POST', '/api/modmail/panel', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const channelId = body.channel_id ? String(body.channel_id) : state.settings.get('modmail_panel_channel_id');
  if (!channelId || !CHANNELS.some((one) => one.id === channelId)) {
    throw new Refused(400, 'no_such_channel', `**${channelId}** is not a channel Black Bloc can see, so the ticket button was not posted. Pick one from the list and try again.`);
  }
  guard('putting an Open a ticket button up');
  const moving = Boolean(state.settings.get('modmail_panel_message_id'));
  const messageId = String(Date.now());
  state.settings.set('modmail_panel_channel_id', channelId);
  state.settings.set('modmail_panel_message_id', messageId);
  logAction(moving ? 'web.modmail.panel_moved' : 'web.modmail.panel_posted', { target_id: channelId, details: { channel_id: channelId, message_id: messageId } });
  return { posted: true, channel_id: channelId, message_id: messageId, message: `The **Open a ticket** button is up in <#${channelId}>.` };
});

route('DELETE', '/api/modmail/panel', (context) => {
  requireStaff(context.session);
  const channelId = state.settings.get('modmail_panel_channel_id');
  const messageId = state.settings.get('modmail_panel_message_id');
  if (!channelId) {
    return { taken_down: false, channel_id: null, message_id: null, message: 'There is no **Open a ticket** button up, so nothing was taken down.' };
  }
  state.settings.set('modmail_panel_channel_id', null);
  state.settings.set('modmail_panel_message_id', null);
  logAction('web.modmail.panel_taken_down', { target_id: channelId, details: { channel_id: channelId, message_id: messageId } });
  return { taken_down: true, channel_id: String(channelId), message_id: messageId === null || messageId === undefined ? null : String(messageId), message: 'The **Open a ticket** button is down. Nothing else changed.' };
});

route('POST', '/api/frontdoor/panel', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const channelId = body.channel_id ? String(body.channel_id) : state.settings.get('frontdoor_channel_id');
  if (!channelId || !CHANNELS.some((one) => one.id === channelId)) {
    throw new Refused(400, 'no_such_channel', 'That is not a channel Black Bloc can see, so the front door was not posted. Pick one from the list and try again.');
  }
  guard('putting the front door up');
  const moving = Boolean(state.settings.get('frontdoor_message_id'));
  const messageId = String(Date.now());
  state.settings.set('frontdoor_channel_id', channelId);
  state.settings.set('frontdoor_message_id', messageId);
  if (state.settings.get('frontdoor_replaces_ticket_button') && state.settings.get('modmail_panel_channel_id') === channelId) {
    state.settings.set('modmail_panel_message_id', null);
    logAction('frontdoor.ticket_button_hidden', { target_id: channelId, details: { channel_id: channelId } });
  }
  logAction(moving ? 'web.frontdoor.moved' : 'web.frontdoor.posted', { target_id: channelId, details: { channel_id: channelId, message_id: messageId } });
  return { posted: true, channel_id: channelId, message_id: messageId, message: `The front door is up in <#${channelId}>.` };
});

route('DELETE', '/api/frontdoor/panel', (context) => {
  requireStaff(context.session);
  const channelId = state.settings.get('frontdoor_channel_id');
  const messageId = state.settings.get('frontdoor_message_id');
  if (!channelId) {
    return { taken_down: false, channel_id: null, message_id: null, message: 'There is no front door posted anywhere, so nothing was taken down. **Post the front door** on the Modmail page is what puts one up.' };
  }
  state.settings.set('frontdoor_channel_id', null);
  state.settings.set('frontdoor_message_id', null);
  logAction('web.frontdoor.taken_down', { target_id: channelId, details: { channel_id: channelId, message_id: messageId } });
  return { taken_down: true, channel_id: String(channelId), message_id: messageId === null || messageId === undefined ? null : String(messageId), message: 'The front door is down. Nothing else changed, and `/ask` still works.' };
});

route('POST', '/api/modmail/forum', (context) => {
  requireStaff(context.session);
  const known = state.settings.get('modmail_forum_channel_id');
  if (known) {
    throw new Refused(409, 'forum_exists', `<#${known}> is already the ticket forum, so nothing was made. **Forget…** → **The ticket forum** lets go of it first if you want a new one.`);
  }
  if (!state.settings.get('modmail_category_id')) {
    throw new Refused(409, 'no_category', '**modmail_category_id** is not pointed at a category Black Bloc can see, so there is nowhere to make the forum. **Setup…** → **Ticket category…** points it at one first.');
  }
  const channelId = String(Date.now());
  state.settings.set('modmail_forum_channel_id', channelId);
  logAction('web.modmail.forum_made', { target_id: channelId, details: { channel_id: channelId } });
  return { made: true, channel_id: channelId, message: `<#${channelId}> is up: a forum under the ticket category, with its overwrites, and with an **open** and a **closed** tag.` };
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
  logAction('web.modmail.snippet_saved', { reason: name, details: { name } });
  return { saved: true, name, content: body.content };
});

route('DELETE', '/api/modmail/snippets/:name', (context) => {
  requireStaff(context.session);
  const at = state.snippets.findIndex((row) => row.name === context.params.name);
  if (at < 0) throw new Refused(404, 'no_snippet', `There is no snippet called ${context.params.name}.`);
  state.snippets.splice(at, 1);
  logAction('web.modmail.snippet_removed', { reason: context.params.name, details: { name: context.params.name } });
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
  logAction('web.modmail.blocked', { target_id: row.user_id, reason: row.reason });
  return { blocked: true, user_id: row.user_id };
});

route('DELETE', '/api/modmail/blocks/:user_id', (context) => {
  requireStaff(context.session);
  const at = state.blocks.findIndex((row) => row.user_id === context.params.user_id);
  if (at >= 0) state.blocks.splice(at, 1);
  logAction('web.modmail.unblocked', { target_id: context.params.user_id });
  return { unblocked: true, user_id: context.params.user_id };
});

const CHAT_SLOTS = ['filled', 'empty', 'attendee'];
const CHAT_BUILT_INS = ['insult', 'love', 'thanks', 'need_a_mod', 'birthdays', 'whats_next',
  'who_is_live', 'who_has', 'head_count', 'my_roles', 'time_for_me', 'what_can_you_do', 'help',
  'how_are_you', 'greeting', 'unknown'];
const CHAT_NAME = /^[a-z][a-z0-9_]*$/;
// Mirrors black_bloc/chat.py:TOKENS — the chips the Chat page offers for each intent.
const CHAT_TOKENS = {
  who_is_live: ['{names}', '{links}'],
  whats_next: ['{title}', '{when}', '{channel}'],
  birthdays: ['{list}'],
  head_count: ['{count}'],
  who_has: ['{role}', '{count}', '{holders}', '{more}', '{escalate}', '{trouble}'],
  my_roles: ['{menus}', '{roles}'],
  time_for_me: ['{time}'],
  need_a_mod: ['{roles}'],
};
const CHAT_SETTING_KEYS = ['chat_mode', 'chat_cooldown_seconds', 'chat_ignore_channels',
  'chat_ignore_categories', 'chat_home_channel_id', 'chat_visibility_role_id', 'chat_staff_can_ping_roles', 'chat_escalation_names',
  'chat_greeting_reaction', 'chat_reply_in_threads',
  'chat_route_ping_staff', 'chat_llm_mode', 'chat_simple_model', 'chat_personality',
  'chat_person_hourly_turns', 'chat_daily_turns', 'chat_monthly_cap_usd', 'chat_panel_minutes',
  'chat_log_level'];
// Phase 17. Their own list because the Memory section reads them as one block.
const CHAT_MEMORY_SETTING_KEYS = ['chat_memory_mode', 'chat_memory_consent',
  'chat_memory_retention_days', 'chat_memory_dm_scope', 'chat_memory_staff_view',
  'chat_memory_notes_max', 'chat_memory_threads_max', 'chat_memory_model'];
const CHAT_UNKNOWN_LINE = 'Not sure I follow, {name} — try `/help` for what I can do.';
const CHAT_NO_SUCH_INTENT = 'Black Bloc has no chat intent **#%s** any more, so nothing was done. The Chat page lists the ones it has.';
const CHAT_NO_SUCH_LINE = 'Black Bloc has no chat line **#%s** any more, so nothing was done. Somebody may have removed it while this page was open.';
const CHAT_BUILT_IN_STAYS = 'is one of Black Bloc’s own intents, so it cannot be deleted — turn it off instead and it will stop answering, or edit its triggers and lines to say something else.';
const CHAT_BUILT_IN_NAME = 'is one of Black Bloc’s own intents and its name is what the bot looks it up by, so the name cannot change. Its triggers, its lines and its on/off switch all can.';

function chatLineRow(row) {
  return {
    id: String(row.id),
    intent_id: String(row.intent_id),
    text: row.text,
    slot: row.slot,
    enabled: row.enabled,
    created_by: row.created_by === null ? null : String(row.created_by),
    updated_at: row.updated_at,
  };
}

function chatIntentRow(row) {
  return {
    id: String(row.id),
    name: row.name,
    kind: row.kind,
    enabled: row.enabled,
    sort: row.sort,
    triggers: [...row.triggers],
    builtin: row.builtin,
    tokens: [...(CHAT_TOKENS[row.name] || [])],
    created_by: row.created_by === null ? null : String(row.created_by),
    updated_at: row.updated_at,
    lines: state.chatLines.filter((line) => line.intent_id === row.id).map(chatLineRow),
  };
}

function wantedChatIntent(id) {
  const found = state.chatIntents.find((row) => String(row.id) === String(id));
  if (!found) throw new Refused(404, 'no_such_intent', CHAT_NO_SUCH_INTENT.replace('%s', id));
  return found;
}

function wantedChatLine(id) {
  const found = state.chatLines.find((row) => String(row.id) === String(id));
  if (!found) throw new Refused(404, 'no_such_line', CHAT_NO_SUCH_LINE.replace('%s', id));
  return found;
}

function chatName(given) {
  const said = String(given || '').trim().toLowerCase().replace(/[ -]/g, '_');
  if (said.length > 60) throw new Refused(400, 'chat_refused', 'An intent’s name has to be 60 characters or fewer, so nothing was saved. Shorten it and send it again.');
  if (!CHAT_NAME.test(said)) throw new Refused(400, 'chat_refused', `An intent’s name is lowercase letters, numbers and underscores — \`cookout_hours\`, say. ${JSON.stringify(String(given || ''))} is not one, so nothing was saved.`);
  if (CHAT_BUILT_INS.includes(said)) throw new Refused(400, 'chat_refused', `**${said}** is one of Black Bloc’s own intents, so a second one cannot take that name. Edit the built-in one instead, or pick another name.`);
  return said;
}

function chatTriggers(given) {
  const list = Array.isArray(given) ? given : String(given || '').split(',');
  const found = [];
  for (const item of list) {
    const said = String(item).trim().split(/\s+/).filter(Boolean).join(' ');
    if (!said) continue;
    if (said.length > 60) throw new Refused(400, 'chat_refused', `A trigger phrase has to be 60 characters or fewer, so nothing was saved. **${said}** is longer than that.`);
    if (!found.includes(said)) found.push(said);
  }
  if (!found.length) throw new Refused(400, 'chat_refused', 'An intent needs at least one trigger phrase, or nothing would ever reach it. Add a phrase and send it again.');
  if (found.length > 40) throw new Refused(400, 'chat_refused', 'An intent takes at most 40 trigger phrases, so nothing was saved. Trim the list, or split it into two intents.');
  return found;
}

function chatText(given) {
  const said = String(given || '').trim();
  if (!said) throw new Refused(400, 'chat_refused', 'A line needs some words in it, so nothing was saved.');
  if (said.length > 500) throw new Refused(400, 'chat_refused', 'A line has to be 500 characters or fewer, so nothing was saved. Discord will take a longer one, but nobody reads it.');
  return said;
}

function chatSlot(given) {
  const said = String(given === undefined || given === null ? 'filled' : given).trim().toLowerCase();
  if (!CHAT_SLOTS.includes(said)) throw new Refused(400, 'chat_refused', `**${said}** is not somewhere a line can go. They are ${CHAT_SLOTS.join(', ')} — \`filled\` is the ordinary answer, \`empty\` is what a data intent says when there is nothing to report.`);
  return said;
}

/** Mirrors black_bloc/chat.py:normalise, so the mock's Try it lands where the bot's would. */
function chatWords(text) {
  return String(text || '')
    .replace(/<@[!&]?\d+>/g, ' ')
    .toLowerCase()
    .replace(/['’]/g, '')
    .replace(/[^0-9a-z ]+/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .join(' ');
}

function chatMatches(words, triggers) {
  return triggers.some((phrase) => ` ${words} `.includes(` ${chatWords(phrase)} `));
}

function chatLinesOf(intentId, slot) {
  return state.chatLines.filter((line) => line.intent_id === intentId && line.slot === slot && line.enabled);
}

function chatClassify(text) {
  const words = chatWords(text);
  if (!words) return null;
  const order = [...state.chatIntents]
    .filter((row) => row.enabled)
    .sort((a, b) => Number(a.builtin) - Number(b.builtin) || a.sort - b.sort || a.id - b.id);
  for (const row of order) {
    if (row.builtin === false && !chatLinesOf(row.id, 'filled').length) continue;
    if (chatMatches(words, row.triggers)) return row;
  }
  return null;
}

function chatFilled(row) {
  if (row.kind === 'data' && row.name === 'who_is_live') {
    return state.golive.sessions.some((one) => one.ended_at === null);
  }
  if (row.kind === 'route') return Boolean(state.settings.get('modmail_enabled'));
  return true;
}

function chatTokens(row, filled) {
  const live = state.golive.sessions.filter((one) => one.ended_at === null);
  return {
    name: STAFF.display_name,
    attendees: MEMBERS.length,
    count: filled ? live.length : 0,
    names: live.map((one) => memberName(one.user_id)).join(', ') || 'nobody',
    links: live.map((one) => `<${one.url}>`).join(', ') || 'no links',
    roles: '**Aunties / Uncles**',
  };
}

function chatRender(text, tokens) {
  return String(text).replace(/\{([a-z_]+)\}/g, (whole, key) => (key in tokens ? String(tokens[key]) : whole));
}

route('GET', '/api/chat/intents', (context) => {
  requireStaff(context.session);
  return {
    intents: state.chatIntents.map(chatIntentRow),
    settings: CHAT_SETTING_KEYS.map(keyRow),
    slots: [...CHAT_SLOTS],
    notes: [],
  };
});

route('POST', '/api/chat/intents', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const name = chatName(body.name);
  const triggers = chatTriggers(body.triggers);
  if (state.chatIntents.some((row) => row.name === name)) {
    throw new Refused(409, 'name_taken', `This server already has an intent called **${name}**, so nothing was saved. Pick another name, or edit the one that is there.`);
  }
  const made = {
    id: state.nextChatIntent++,
    name,
    kind: 'canned',
    triggers,
    enabled: body.enabled !== false,
    sort: Number(body.sort || 0),
    created_by: STAFF.id,
    updated_at: now(),
    builtin: false,
  };
  state.chatIntents.push(made);
  if (body.text) {
    state.chatLines.push({
      id: state.nextChatLine++,
      intent_id: made.id,
      text: chatText(body.text),
      slot: 'filled',
      enabled: true,
      created_by: STAFF.id,
      updated_at: now(),
    });
  }
  logAction('web.chat.intent_created', { details: { name } });
  return { intent: chatIntentRow(made), message: `**${name}** is in. It will answer as soon as it has a line to say.` };
});

route('PUT', '/api/chat/intents/:id', async (context) => {
  requireStaff(context.session);
  const row = wantedChatIntent(context.params.id);
  const body = await context.body();
  const changed = [];
  if (body.name !== undefined && body.name !== null && String(body.name) !== row.name) {
    if (row.builtin) throw new Refused(409, 'built_in', `**${row.name}** ${CHAT_BUILT_IN_NAME}`);
    row.name = chatName(body.name);
    changed.push('name');
  }
  if (body.triggers !== undefined && body.triggers !== null) {
    row.triggers = chatTriggers(body.triggers);
    changed.push('triggers');
  }
  if (body.enabled !== undefined && body.enabled !== null) {
    row.enabled = Boolean(body.enabled);
    changed.push('enabled');
  }
  if (body.sort !== undefined && body.sort !== null) {
    row.sort = Number(body.sort);
    changed.push('sort');
  }
  row.updated_at = now();
  logAction('web.chat.intent_edited', { details: { intent_id: row.id, changed: changed.sort() } });
  return { intent: chatIntentRow(row), message: `**${row.name}** is saved.` };
});

route('DELETE', '/api/chat/intents/:id', (context) => {
  requireStaff(context.session);
  const row = wantedChatIntent(context.params.id);
  if (row.builtin) throw new Refused(409, 'built_in', `**${row.name}** ${CHAT_BUILT_IN_STAYS}`);
  state.chatIntents = state.chatIntents.filter((one) => one.id !== row.id);
  state.chatLines = state.chatLines.filter((one) => one.intent_id !== row.id);
  logAction('web.chat.intent_deleted', { details: { name: row.name } });
  return {
    removed: true,
    intent_id: String(row.id),
    message: `**${row.name}** is gone. Nothing answers to those phrases any more.`,
  };
});

route('POST', '/api/chat/intents/:id/lines', async (context) => {
  requireStaff(context.session);
  const row = wantedChatIntent(context.params.id);
  const body = await context.body();
  const made = {
    id: state.nextChatLine++,
    intent_id: row.id,
    text: chatText(body.text),
    slot: chatSlot(body.slot),
    enabled: body.enabled !== false,
    created_by: STAFF.id,
    updated_at: now(),
  };
  state.chatLines.push(made);
  logAction('web.chat.line_added', { details: { intent_id: row.id, slot: made.slot } });
  return { line: chatLineRow(made), message: `That line is in — **${row.name}** may say it from now on.` };
});

route('PUT', '/api/chat/lines/:id', async (context) => {
  requireStaff(context.session);
  const row = wantedChatLine(context.params.id);
  const body = await context.body();
  const changed = [];
  if (body.text !== undefined && body.text !== null) {
    row.text = chatText(body.text);
    changed.push('text');
  }
  if (body.slot !== undefined && body.slot !== null) {
    row.slot = chatSlot(body.slot);
    changed.push('slot');
  }
  if (body.enabled !== undefined && body.enabled !== null) {
    row.enabled = Boolean(body.enabled);
    changed.push('enabled');
  }
  row.updated_at = now();
  logAction('web.chat.line_edited', { details: { line_id: row.id, changed: changed.sort() } });
  return { line: chatLineRow(row), message: 'That line is saved.' };
});

route('DELETE', '/api/chat/lines/:id', (context) => {
  requireStaff(context.session);
  const row = wantedChatLine(context.params.id);
  state.chatLines = state.chatLines.filter((one) => one.id !== row.id);
  logAction('web.chat.line_deleted', { details: { intent_id: row.intent_id, slot: row.slot } });
  return { removed: true, line_id: String(row.id), message: 'That line is gone.' };
});

route('POST', '/api/chat/try', async (context) => {
  // A dry run, the way black_bloc/api/tools/chat.py does it: nothing is sent anywhere.
  requireStaff(context.session);
  const body = await context.body();
  const text = String(body.text || '').trim();
  if (!text) throw new Refused(400, 'no_text', 'There is nothing to try yet, so nothing was worked out. Type the sentence somebody would say and send it again.');
  const row = chatClassify(text);
  if (!row) {
    return { intent: 'unknown', kind: 'canned', slot: 'filled', line: chatRender(CHAT_UNKNOWN_LINE, chatTokens({ kind: 'canned' }, true)) };
  }
  const filled = chatFilled(row);
  const slot = row.kind === 'canned' || filled ? 'filled' : 'empty';
  const lines = chatLinesOf(row.id, slot);
  const tokens = chatTokens(row, filled);
  const said = lines.length ? lines[0].text : CHAT_UNKNOWN_LINE;
  return { intent: row.name, kind: row.kind, slot, line: chatRender(said, tokens) };
});

// Chat step 3 (14b). Mirrors black_bloc/api/tools/chat.py: ids as strings, refusals in words,
// a server-written note shown but locked, and liveness measured rather than assumed.
const KNOWLEDGE_TITLE_LIMIT = 100;
const KNOWLEDGE_BODY_LIMIT = 4000;
const KNOWLEDGE_TAG_LIMIT = 40;
const GROUNDING_SECTIONS = 3;
const GROUNDING_CHARACTERS = 6144;
const MICRODOLLARS = 1000000;

const KNOWLEDGE_STAFF_WROTE_IT = 'written here by staff';
const KNOWLEDGE_SERVER_WROTE_IT = 'written by Black Bloc from the server itself, every day';
const KNOWLEDGE_LOCKED = 'is one of the notes Black Bloc writes for itself out of the server — the channel list, the roles, what is coming up — so it cannot be changed by hand. It is written again from scratch every day, and an edit here would be gone by morning. Write your own note beside it and Black Bloc reads both.';
const KNOWLEDGE_NO_SUCH = 'Black Bloc has no note **#%s** any more, so nothing was done. Somebody may have removed it while this page was open.';
const KNOWLEDGE_NEEDS_TITLE = 'A note needs a heading, so nothing was saved. That is the line Black Bloc matches a question against — something like `Cookout hours`.';
const KNOWLEDGE_NEEDS_BODY = 'A note needs some words under the heading, so nothing was saved. Write what you would tell somebody who asked.';
const KNOWLEDGE_BUDGET_WORD = `At most ${GROUNDING_SECTIONS} notes ride an answer, and a note that will not fit is left out rather than cut short.`;

const PERSONA_COOKOUT_WORD = 'Everybody gets the cookout voice — warm, playful, the one the rest of the site is written in.';
const PERSONA_TROPE_WORD = 'Black Bloc is **%s** with everybody, and it does not drift.';
const PERSONA_NO_SUCH = '**%s** is not one of the voices Black Bloc knows, so nothing was changed. The list on this page is all of them.';
const PERSONA_NEEDS_A_NAME = 'That arrived with no voice in it, so nothing was changed. Pick the cookout voice, the pool, or one of the names on the list.';
const PERSONA_IS_OFF = '**%s** is switched off in the pool, so Black Bloc cannot be it. Turn it back on first, or pick another one.';
const PERSONA_LAST_ONE = '**%s** is the last voice left on and the pool is what Black Bloc is using, so it was left alone. Turn another one on first, or move the voice to the cookout one.';
const PERSONA_IN_USE = 'Black Bloc is set to be **%s** and nothing else, so that voice cannot be switched off. Point it at the cookout voice or the pool first.';

const TIER_INTENTS_WORD = 'Always on. The phrases on this page answer first, they cost nothing, and they are checked before any model is asked.';
const TIER_MODE_OFF = 'Not in use: `chat_llm_mode` is off, so Black Bloc answers from the phrases on this page and nothing else.';
const TIER_NO_KEY = 'Black Bloc has not been given a **%s** yet, so this tier does not exist and the answer falls through to the next one. A Lead sets it on the host.';
const TIER_CAPPED = 'Closed until the 1st: this month’s %s is spent. Black Bloc is answering from the phrases on this page in the meantime.';

function knowledgeRow(row) {
  const own = row.source === 'staff';
  return {
    id: String(row.id),
    title: row.title,
    body: row.body,
    tag: row.tag,
    source: row.source,
    source_word: own ? KNOWLEDGE_STAFF_WROTE_IT : KNOWLEDGE_SERVER_WROTE_IT,
    editable: own,
    locked_why: own ? null : `**${row.title}** ${KNOWLEDGE_LOCKED}`,
    characters: row.body.length,
    updated_at: row.updated_at,
    updated_by: row.updated_by === null ? null : { id: String(row.updated_by), name: memberName(row.updated_by) || String(row.updated_by) },
  };
}

function wantedSection(id) {
  const found = state.knowledge.find((row) => String(row.id) === String(id));
  if (!found) throw new Refused(404, 'no_such_section', KNOWLEDGE_NO_SUCH.replace('%s', id));
  return found;
}

function staffSectionOnly(row) {
  if (row.source !== 'staff') {
    throw new Refused(409, 'written_by_the_bot', `**${row.title}** ${KNOWLEDGE_LOCKED}`);
  }
}

function knowledgeTitle(given) {
  const said = String(given || '').split(/\s+/).filter(Boolean).join(' ');
  if (!said) throw new Refused(400, 'chat_refused', KNOWLEDGE_NEEDS_TITLE);
  if (said.length > KNOWLEDGE_TITLE_LIMIT) throw new Refused(400, 'chat_refused', `A note’s heading has to be ${KNOWLEDGE_TITLE_LIMIT} characters or fewer, so nothing was saved. Shorten it and send it again.`);
  return said;
}

function knowledgeBody(given) {
  const said = String(given || '').trim();
  if (!said) throw new Refused(400, 'chat_refused', KNOWLEDGE_NEEDS_BODY);
  if (said.length > KNOWLEDGE_BODY_LIMIT) throw new Refused(400, 'chat_refused', `A note has to be ${KNOWLEDGE_BODY_LIMIT} characters or fewer, so nothing was saved. Anything longer will not fit in an answer — split it into two notes with headings of their own.`);
  return said;
}

function knowledgeTag(given) {
  const said = String(given || '').split(/\s+/).filter(Boolean).join(' ');
  if (!said) return null;
  if (said.length > KNOWLEDGE_TAG_LIMIT) throw new Refused(400, 'chat_refused', `A tag has to be ${KNOWLEDGE_TAG_LIMIT} characters or fewer, so nothing was saved.`);
  return said;
}

function knowledgePayload() {
  const rows = [...state.knowledge]
    .sort((a, b) => a.source.localeCompare(b.source) || a.title.localeCompare(b.title))
    .map(knowledgeRow);
  return {
    sections: rows,
    counts: {
      total: rows.length,
      staff: rows.filter((row) => row.source === 'staff').length,
      server: rows.filter((row) => row.source === 'server').length,
    },
    budget: { sections: GROUNDING_SECTIONS, characters: GROUNDING_CHARACTERS, word: KNOWLEDGE_BUDGET_WORD },
    notes: [],
  };
}

route('GET', '/api/chat/knowledge', (context) => {
  requireStaff(context.session);
  return knowledgePayload();
});

route('POST', '/api/chat/knowledge', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const title = knowledgeTitle(body.title);
  const words = knowledgeBody(body.body);
  const tag = knowledgeTag(body.tag);
  if (state.knowledge.some((row) => row.source === 'staff' && row.title === title)) {
    throw new Refused(409, 'title_taken', `This server already has a note called **${title}**, so nothing was saved. Edit that one, or give this one a heading of its own.`);
  }
  const made = { id: state.nextKnowledge++, title, body: words, source: 'staff', tag, updated_at: now(), updated_by: STAFF.id };
  state.knowledge.push(made);
  logAction('web.chat.knowledge_added', { details: { title, via: 'website' } });
  return { section: knowledgeRow(made), message: `**${title}** is in. Black Bloc quotes it when somebody asks something it matches.` };
});

route('PUT', '/api/chat/knowledge/:id', async (context) => {
  requireStaff(context.session);
  const row = wantedSection(context.params.id);
  staffSectionOnly(row);
  const body = await context.body();
  const changed = [];
  if (body.title !== undefined && body.title !== null) {
    row.title = knowledgeTitle(body.title);
    changed.push('title');
  }
  if (body.body !== undefined && body.body !== null) {
    row.body = knowledgeBody(body.body);
    changed.push('body');
  }
  if ('tag' in body) {
    row.tag = knowledgeTag(body.tag);
    changed.push('tag');
  }
  row.updated_at = now();
  row.updated_by = STAFF.id;
  logAction('web.chat.knowledge_edited', { details: { section_id: row.id, changed: changed.sort(), via: 'website' } });
  return { section: knowledgeRow(row), message: `**${row.title}** is saved.` };
});

route('DELETE', '/api/chat/knowledge/:id', (context) => {
  requireStaff(context.session);
  const row = wantedSection(context.params.id);
  staffSectionOnly(row);
  state.knowledge = state.knowledge.filter((one) => one.id !== row.id);
  logAction('web.chat.knowledge_removed', { details: { title: row.title, via: 'website' } });
  return { removed: true, section_id: String(row.id), message: `**${row.title}** is gone. Black Bloc will not quote it again.` };
});

function personaMode() {
  return String(state.settings.get('chat_personality') || 'cookout');
}

function personaKind(mode) {
  if (mode === 'cookout') return 'cookout';
  return mode === 'pool' ? 'pool' : 'trope';
}

function tropeRow(row, mode) {
  return {
    name: row.name,
    label: row.label,
    voice: row.voice,
    enabled: row.enabled,
    in_use: mode === row.name,
    updated_at: row.updated_at,
    updated_by: row.updated_by === null ? null : { id: String(row.updated_by), name: memberName(row.updated_by) || String(row.updated_by) },
  };
}

function personaWord(mode) {
  const kind = personaKind(mode);
  if (kind === 'cookout') return PERSONA_COOKOUT_WORD;
  if (kind === 'pool') {
    const on = state.tropes.filter((row) => row.enabled).length;
    return `Each conversation gets one of the ${on} voices left on, and it moves a step at a time as people talk.`;
  }
  const found = state.tropes.find((row) => row.name === mode);
  return PERSONA_TROPE_WORD.replace('%s', found ? found.label : mode);
}

function personalityPayload() {
  const mode = personaMode();
  return {
    mode,
    mode_kind: personaKind(mode),
    mode_word: personaWord(mode),
    tropes: state.tropes.map((row) => tropeRow(row, mode)),
    counts: { total: state.tropes.length, enabled: state.tropes.filter((row) => row.enabled).length },
    ported_from: 'catalog-platform@03dcb91',
    notes: [],
  };
}

// Phase 17. Counts always; the notes themselves only where chat_memory_staff_view is `full`.
const MEMORY_IS_OFF = 'Black Bloc is not remembering anybody on this server, so there is nothing here yet. The Memory switch above turns it on, and profiles start appearing after the next sweep.';
const MEMORY_IS_PRIVATE = 'This server keeps what Black Bloc remembers about a member private to that member, so the notes were not shown — only the counts on this page. It needs `chat_memory_staff_view` set to `full`, which a Lead can change on the Settings page, or in Discord with `/settings` and the chat settings group. The member can always read their own with `/memory`.';
const MEMORY_NO_SUCH = 'Black Bloc remembers nothing about that member on this server, so there was nothing to show or clear.';

function memoryFull() {
  return state.settings.get('chat_memory_staff_view') === 'full';
}

function memoryRow(row, full) {
  return {
    member: { id: String(row.user_id), name: memberName(row.user_id) || String(row.user_id) },
    notes: row.notes.length,
    threads: row.threads.length,
    turns_seen: row.turns_seen,
    created_at: row.created_at,
    updated_at: row.updated_at,
    call_me: full ? row.call_me : null,
    lines: full
      ? [
        ...row.notes.map((one) => ({ text: one.text, where: one.where, kind: 'note' })),
        ...row.threads.map((one) => ({ text: one.text, where: one.where, kind: 'thread' })),
      ]
      : [],
  };
}

function wantedProfile(id) {
  const found = state.profiles.find((row) => String(row.user_id) === String(id));
  if (!found) throw new Refused(404, 'no_such_profile', MEMORY_NO_SUCH);
  return found;
}

route('GET', '/api/chat/memory', (context) => {
  requireStaff(context.session);
  const full = memoryFull();
  const on = state.settings.get('chat_memory_mode') === 'on';
  return {
    mode: state.settings.get('chat_memory_mode'),
    on,
    staff_view: full ? 'full' : 'counts',
    profiles: state.profiles.map((row) => memoryRow(row, full)),
    total: state.profiles.length,
    opted_out: state.memoryOptOut.length,
    dm_notes: state.profiles.reduce((sum, row) => sum + row.notes.filter((one) => one.where === 'dm').length, 0),
    message: on ? '' : MEMORY_IS_OFF,
  };
});

route('GET', '/api/chat/memory/:id', (context) => {
  requireStaff(context.session);
  if (!memoryFull()) throw new Refused(403, 'memory_is_private', MEMORY_IS_PRIVATE);
  return { profile: memoryRow(wantedProfile(context.params.id), true) };
});

route('DELETE', '/api/chat/memory/:id', (context) => {
  requireStaff(context.session);
  const row = wantedProfile(context.params.id);
  state.profiles = state.profiles.filter((one) => one !== row);
  const who = memberName(row.user_id) || String(row.user_id);
  logAction('web.chat.memory_forgot', { target_id: row.user_id, details: { who_asked: 'staff', via: 'website' } });
  return {
    member: { id: String(row.user_id), name: who },
    message: `Cleared. Black Bloc remembers nothing about ${who} here.`,
  };
});

route('GET', '/api/chat/personality', (context) => {
  requireStaff(context.session);
  return personalityPayload();
});

route('PUT', '/api/chat/personality', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const wanted = String(body.mode || '').trim().toLowerCase();
  if (!wanted) throw new Refused(400, 'chat_refused', PERSONA_NEEDS_A_NAME);
  let said = 'Black Bloc talks in the cookout voice from now on.';
  if (wanted !== 'cookout' && wanted !== 'pool') {
    const found = state.tropes.find((row) => row.name === wanted);
    if (!found) throw new Refused(404, 'no_such_trope', PERSONA_NO_SUCH.replace('%s', wanted));
    if (!found.enabled) throw new Refused(409, 'voice_is_off', PERSONA_IS_OFF.replace('%s', found.label));
    said = `Black Bloc is **${found.label}** with everybody from now on.`;
  } else if (wanted === 'pool') {
    said = 'Black Bloc picks a voice out of the pool for each conversation from now on, and moves a step at a time as people talk.';
  }
  state.settings.set('chat_personality', wanted);
  logAction('web.chat.personality_mode', { details: { mode: wanted, via: 'website' } });
  const found = personalityPayload();
  return { mode: found.mode, mode_kind: found.mode_kind, mode_word: found.mode_word, message: said };
});

route('PUT', '/api/chat/personality/:name', async (context) => {
  requireStaff(context.session);
  const name = String(context.params.name || '').trim().toLowerCase();
  const row = state.tropes.find((one) => one.name === name);
  if (!row) throw new Refused(404, 'no_such_trope', PERSONA_NO_SUCH.replace('%s', name));
  const body = await context.body();
  const wanted = body.enabled !== false;
  const mode = personaMode();
  if (!wanted && mode === row.name) {
    throw new Refused(409, 'voice_in_use', PERSONA_IN_USE.replace('%s', row.label));
  }
  const on = state.tropes.filter((one) => one.enabled);
  if (!wanted && mode === 'pool' && on.length === 1 && on[0].name === row.name) {
    throw new Refused(409, 'last_voice', PERSONA_LAST_ONE.replace('%s', row.label));
  }
  row.enabled = wanted;
  row.updated_at = now();
  row.updated_by = STAFF.id;
  logAction(wanted ? 'web.chat.trope_enabled' : 'web.chat.trope_disabled', { details: { trope: row.name, via: 'website' } });
  return {
    trope: tropeRow(row, mode),
    message: wanted ? `**${row.label}** is back in the pool.` : `**${row.label}** is out of the pool. Black Bloc will not pick it again.`,
  };
});

function money(value) {
  return `$${value.toFixed(2)}`;
}

function chatTier(name, label, key, liveWord, modeOn, capSaid) {
  if (!modeOn) return { name, label, live: false, word: TIER_MODE_OFF };
  if (!state.llmKeys[key]) return { name, label, live: false, word: TIER_NO_KEY.replace('%s', key) };
  if (capSaid) return { name, label, live: false, word: TIER_CAPPED.replace('%s', capSaid) };
  return { name, label, live: true, word: liveWord };
}

route('GET', '/api/chat/spend', (context) => {
  requireStaff(context.session);
  const at = new Date();
  const monthFrom = new Date(Date.UTC(at.getUTCFullYear(), at.getUTCMonth(), 1)).toISOString();
  const dayFrom = new Date(Date.UTC(at.getUTCFullYear(), at.getUTCMonth(), at.getUTCDate())).toISOString();
  const spent = state.ledger.filter((row) => row.at >= monthFrom)
    .reduce((total, row) => total + row.cost_microdollars, 0);
  const turns = state.ledger.filter((row) => row.at >= dayFrom).length;
  const capUsd = Number(state.settings.get('chat_monthly_cap_usd') ?? 20);
  const daily = 200;
  const modeOn = String(state.settings.get('chat_llm_mode') || 'off') === 'on';
  const spentUsd = Math.round((spent / MICRODOLLARS) * 100) / 100;
  const leftUsd = Math.round(Math.max(capUsd - spentUsd, 0) * 100) / 100;
  const capped = capUsd > 0 && spentUsd >= capUsd;
  const capSaid = money(capUsd);
  const word = capped
    ? `${money(spentUsd)} of the ${capSaid} Black Bloc may spend this month, so the two model tiers are shut until the 1st.`
    : `${money(spentUsd)} of the ${capSaid} Black Bloc may spend this month, so ${money(leftUsd)} is left.`;
  const latest = state.ledger.map((row) => row.at).sort();
  return {
    month: {
      spent_usd: spentUsd,
      cap_usd: capUsd,
      left_usd: leftUsd,
      share: capUsd > 0 ? Math.round((spentUsd / capUsd) * 10000) / 10000 : 0,
      word,
    },
    today: {
      turns,
      limit: daily,
      word: `${turns} answers came from a model today, out of the ${daily} a day Black Bloc gives.`,
    },
    tiers: [
      { name: 'intents', label: 'Phrases', live: true, word: TIER_INTENTS_WORD },
      chatTier('important', 'Claude Haiku', 'ANTHROPIC_API_KEY', 'Live. Grounded answers and longer questions go here.', modeOn, capped ? capSaid : null),
      chatTier('simple', 'Groq Llama', 'GROQ_API_KEY', 'Live. Greetings and one-liners that slipped past the phrases go here.', modeOn, capped ? capSaid : null),
    ],
    capped,
    cap_key: 'chat_monthly_cap_usd',
    last_turn_at: latest.length ? latest[latest.length - 1] : null,
    notes: [],
  };
});

// Requests (13a). The helpers are ask* rather than request* because requestRow above is
// already the role-request row. Mirrors black_bloc/api/tools/requests.py: ids as strings, refusals in
// words, pending first. POST /api/requests, GET /api/requests/mine and the withdraw route
// are the only three the real API lets a non-staff member call.
const REQUEST_STATUSES = ['open', 'in_progress', 'review', 'hold', 'done', 'declined', 'withdrawn'];
// One table, the same one black_bloc/requests.py:TRANSITIONS holds. `done` is reachable only
// from `review`, so every done card has a line saying what was actually built.
const REQUEST_TRANSITIONS = {
  open: ['declined', 'hold', 'in_progress'],
  in_progress: ['declined', 'hold', 'review'],
  review: ['declined', 'done', 'hold', 'in_progress'],
  hold: ['declined', 'in_progress', 'review'],
  done: [],
  declined: [],
  withdrawn: [],
};
const REQUEST_STAFF_STATUSES = ['declined', 'done', 'hold', 'in_progress', 'review'];
const REQUEST_OPEN_STATUSES = ['open', 'in_progress', 'review', 'hold'];
const REQUEST_WITHDRAWABLE = ['open', 'hold'];
const REQUEST_NEEDS_A_REASON = ['hold', 'declined'];
const REQUEST_STATUS_WORDS = {
  open: 'open',
  in_progress: 'being worked on',
  review: 'ready to check',
  hold: 'on hold',
  done: 'done',
  declined: 'declined',
  withdrawn: 'withdrawn',
};
const REQUEST_PAGE = 20;
const REQUEST_PRIORITY_MAX = 5;
const REQUESTS_OFF = 'Requests are turned off on this server, so nothing was filed. A Lead turns them back on with `/settings` ▸ **Turn a feature back on…** — ask one if you have something to ask for.';
const REQUEST_STAFF_ONLY = 'Only staff may file a request on this server at the moment, so nothing was filed. Ask a Lead to put it in for you, or to set `request_who_can_file` to everyone.';
const REQUEST_NEEDS_WHAT = 'A request needs a line saying what you are asking for, so nothing was filed. Fill the What box in and send it again.';
const REQUEST_NEEDS_WHY = 'A request needs a line saying why it is worth doing, so nothing was filed. That is the part staff read first — fill the Why box in and send it again.';
const REQUEST_DECLINE_NEEDS_A_REASON = 'A declined request needs one line the person who asked is sent, so nothing was changed. Say why and send it again.';
const REQUEST_HOLD_NEEDS_A_REASON = 'A request put on hold needs one line the person who asked is sent, so nothing was changed. Say why it is waiting and send it again.';
const REQUEST_REASON_NEEDED = { declined: REQUEST_DECLINE_NEEDS_A_REASON, hold: REQUEST_HOLD_NEEDS_A_REASON };
const REQUEST_READY_NEEDS_BUILT = 'Marking a request ready to check needs a line saying what was actually built, so nothing was changed. That sentence is what the person who asked reads on the card. `/request ready {id}` opens a box for it — or use the **Ready to check** button on the site.';
const REQUEST_SENDBACK_NEEDS_A_NOTE = 'Sending a request back needs one line saying what is still to do, so nothing was changed. The staffer who marked it ready is sent exactly what you type — say what is missing and send it again.';
const REQUEST_DONE_NEEDS_A_CHECK = 'Request **#{id}** is **{status}**, and a request only finishes once somebody has checked it, so nothing was changed. `/request ready {id}` marks it ready to check — what was built, and how to try it — and `/request accept {id}` finishes it after that. On the site it is the **Ready to check** button on the card.';
const REQUEST_NOT_READY = 'Request **#{id}** is **{status}**, not ready to check, so there was nothing to {doing}. **Ready to check** on its card is what puts one there.';
const REQUEST_CHECK_ASKED = 'Request **#{id}** — {who} has been asked by DM to try it.';
const REQUEST_REVIEW_BY_OTHER = 'You are the one who marked request **#{id}** ready to check, and this server asks somebody else on staff to check it, so nothing was changed. Ask another staffer to press Accept, or a Lead can turn `request_review_by_other` off if one pair of eyes is enough.';
const REQUEST_COMMENT_NEEDS_TEXT = 'There is nothing to add, so no comment was left. Type what you want on the request and send it again.';
const REQUEST_NOTHING_TO_SAVE = 'That change arrived with nothing in it, so nothing was saved. It is a fault in the page rather than in what you typed — reload the requests page and try again.';

function askPerson(id) {
  if (id === null || id === undefined || id === '') return null;
  return { id: String(id), name: memberName(id) || String(id), avatar: null };
}

function askRow(row) {
  return {
    id: String(row.id),
    what: row.what,
    why: row.why,
    due_on: row.due_on,
    status: row.status,
    status_word: REQUEST_STATUS_WORDS[row.status] || row.status,
    moved_to: row.moved_to === undefined ? null : row.moved_to,
    moved_word: movedWord(row.moved_to),
    priority: row.priority,
    notes: row.notes,
    requester: askPerson(row.user_id),
    assignee: askPerson(row.assignee_id),
    comment_count: state.askComments.filter((one) => one.request_id === row.id).length,
    created_at: row.created_at,
    decided_by: row.decided_by ? String(row.decided_by) : null,
    decided_by_name: row.decided_by ? memberName(row.decided_by) : null,
    decided_at: row.decided_at,
    decline_reason: row.decline_reason,
    held_from: row.held_from || null,
    held_word: row.held_from ? REQUEST_STATUS_WORDS[row.held_from] || row.held_from : '',
    built: row.built || null,
    how_to_test: row.how_to_test || null,
    ready_by: row.ready_by ? String(row.ready_by) : null,
    ready_by_name: row.ready_by ? memberName(row.ready_by) : null,
    sent_back_reason: row.sent_back_reason || null,
    check_asked_by: row.check_asked_by ? String(row.check_asked_by) : null,
    check_asked_by_name: row.check_asked_by ? memberName(row.check_asked_by) : null,
    check_asked_at: row.check_asked_at || null,
    moves: REQUEST_TRANSITIONS[row.status] || [],
    resume_to: row.status === 'hold' ? askResumeTarget(row) : null,
    done_at: row.done_at,
  };
}

function askResumeTarget(row) {
  const found = String(row.held_from || '');
  return (REQUEST_TRANSITIONS.hold || []).includes(found) ? found : 'in_progress';
}

function askCommentRow(row) {
  return {
    id: String(row.id),
    request_id: String(row.request_id),
    author: askPerson(row.author_id),
    text: row.text,
    at: row.at,
  };
}

function wantedAsk(id) {
  const found = state.asks.find((one) => String(one.id) === String(id));
  if (!found) {
    throw new Refused(404, 'no_such_request', `Black Bloc has no request **#${id}**, so nothing was done. \`/request list\` shows the ones it has.`);
  }
  return found;
}

function asksSorted(rows) {
  return [...rows].sort((a, b) => {
    const first = (a.status === 'pending' ? 0 : 1) - (b.status === 'pending' ? 0 : 1);
    return first !== 0 ? first : b.id - a.id;
  });
}

function askPage(rows, page) {
  const total = rows.length;
  const pages = Math.max(1, Math.ceil(total / REQUEST_PAGE));
  const at = Math.max(1, Math.min(Number(page || 1), pages));
  return {
    requests: rows.slice((at - 1) * REQUEST_PAGE, at * REQUEST_PAGE).map(askRow),
    total,
    page: at,
    pages,
    per_page: REQUEST_PAGE,
  };
}

function askFields(body) {
  const what = String(body.what || '').trim().slice(0, 1000);
  if (!what) throw new Refused(400, 'request_refused', REQUEST_NEEDS_WHAT);
  const why = String(body.why || '').trim().slice(0, 1000);
  if (!why) throw new Refused(400, 'request_refused', REQUEST_NEEDS_WHY);
  const given = String(body.due_on || '').trim();
  if (given && !/^\d{4}-\d{2}-\d{2}$/.test(given)) {
    throw new Refused(400, 'request_refused', `**${given}** is not a date Black Bloc can read, so nothing was filed. Write it as \`YYYY-MM-DD\` — \`2026-09-15\`, say — or leave the box empty if there is no deadline.`);
  }
  return { what, why, due_on: given || null };
}

function askMovesSentence(status) {
  const found = REQUEST_TRANSITIONS[status] || [];
  const where = REQUEST_STATUS_WORDS[status] || status;
  if (!found.length) return `**${where}** is where a request finishes — nothing moves it now.`;
  return `From **${where}** it can go to ${found.map((one) => `**${one}**`).join(', ')}.`;
}

function askLook(was, status) {
  return status === 'in_progress' && was === 'review' ? 'sent_back' : status;
}

function askDecide(row, status, reason, extra = {}) {
  const where = row.status;
  if (where === status) {
    throw new Refused(409, 'not_decided', `Request **#${row.id}** is already **${REQUEST_STATUS_WORDS[where] || where}**, so nothing was changed.`);
  }
  if (!(REQUEST_TRANSITIONS[where] || []).includes(status)) {
    // `done` is reachable only from `review`, so the refusal names the ready step rather
    // than reciting the table — the same words black_bloc/requests.py:checked_move gives.
    if (status === 'done' && REQUEST_OPEN_STATUSES.includes(where)) {
      throw new Refused(409, 'not_decided', REQUEST_DONE_NEEDS_A_CHECK.split('{id}').join(row.id).split('{status}').join(REQUEST_STATUS_WORDS[where] || where));
    }
    throw new Refused(409, 'not_decided', `Request **#${row.id}** is **${REQUEST_STATUS_WORDS[where] || where}**, and staff cannot move it to **${status}** from there, so nothing was changed. ${askMovesSentence(where)}`);
  }
  if (REQUEST_NEEDS_A_REASON.includes(status) && !reason) {
    throw new Refused(400, 'no_reason', REQUEST_REASON_NEEDED[status]);
  }
  const look = askLook(where, status);
  if (look === 'review' && !String(extra.built || row.built || '').trim()) {
    throw new Refused(400, 'no_built', REQUEST_READY_NEEDS_BUILT.split('{id}').join(row.id));
  }
  if (look === 'sent_back' && !String(extra.sent_back_reason || '').trim()) {
    throw new Refused(400, 'no_reason', REQUEST_SENDBACK_NEEDS_A_NOTE);
  }
  if (status === 'done' && state.settings.get('request_review_by_other') && String(row.ready_by || '') === String(STAFF.id)) {
    throw new Refused(409, 'not_decided', REQUEST_REVIEW_BY_OTHER.split('{id}').join(row.id));
  }
  row.status = status;
  row.decided_by = STAFF.id;
  row.decided_at = now();
  row.decline_reason = REQUEST_NEEDS_A_REASON.includes(status) ? reason : null;
  row.held_from = status === 'hold' ? where : null;
  if (status === 'review') {
    if (extra.built !== undefined) row.built = extra.built || null;
    if (extra.how_to_test !== undefined) row.how_to_test = extra.how_to_test || null;
    row.ready_by = STAFF.id;
    row.sent_back_reason = null;
  }
  if (look === 'sent_back') row.sent_back_reason = extra.sent_back_reason || null;
  if (status === 'done') row.done_at = now();
  logAction(`web.request.${look}`, { target_id: row.user_id, reason: reason || extra.sent_back_reason || null, details: { request_id: row.id, was: where } });
  if (look === 'review') return `Request **#${row.id}** is ready to check — staff will look at it.`;
  if (look === 'sent_back') return `Request **#${row.id}** is back with whoever is working on it.`;
  if (status === 'done') return `Request **#${row.id}** is done. The person who asked has been told.`;
  return `Request **#${row.id}** is now **${REQUEST_STATUS_WORDS[status]}**.`;
}

function notReadyToCheck(row, doing) {
  return REQUEST_NOT_READY
    .split('{id}').join(row.id)
    .split('{status}').join(REQUEST_STATUS_WORDS[row.status] || row.status)
    .split('{doing}').join(doing);
}

function askResume(row) {
  if (row.status !== 'hold') {
    throw new Refused(409, 'not_on_hold', `Request **#${row.id}** is **${REQUEST_STATUS_WORDS[row.status] || row.status}**, not on hold, so there was nothing to resume. \`/request set\` moves it from where it is.`);
  }
  const wanted = askResumeTarget(row);
  row.status = wanted;
  row.held_from = null;
  row.decided_by = STAFF.id;
  row.decided_at = now();
  logAction('web.request.resumed', { target_id: row.user_id, details: { request_id: row.id, was: 'hold', held_from: wanted } });
  return `Request **#${row.id}** is off hold and back to **${REQUEST_STATUS_WORDS[wanted]}**.`;
}

route('GET', '/api/requests', (context) => {
  requireStaff(context.session);
  const url = context.url;
  const wanted = String(url.searchParams.get('status') || '').split(',').map((one) => one.trim()).filter(Boolean);
  for (const one of wanted) {
    if (!REQUEST_STATUSES.includes(one)) {
      throw new Refused(400, 'request_refused', `**${one}** is not a state a request can be in, so nothing was changed. They are ${REQUEST_STATUSES.join(', ')}.`);
    }
  }
  const assignee = String(url.searchParams.get('assignee') || '').trim();
  const query = String(url.searchParams.get('q') || '').trim().toLowerCase();
  const rows = asksSorted(state.asks).filter((row) => {
    if (wanted.length && !wanted.includes(row.status)) return false;
    // `assignee=none` is the board's Unassigned column.
    if (assignee.toLowerCase() === 'none' && row.assignee_id) return false;
    if (assignee && assignee.toLowerCase() !== 'none' && String(row.assignee_id) !== assignee) return false;
    // `q` reaches the requester's NAME as well as the three text columns.
    const haystack = [row.what, row.why, row.notes, memberName(row.user_id)];
    if (query && !haystack.some((one) => String(one || '').toLowerCase().includes(query))) return false;
    return true;
  });
  return {
    ...askPage(rows, url.searchParams.get('page')),
    open: state.asks.filter((row) => row.status === 'open').length,
  };
});

route('POST', '/api/requests', async (context) => {
  requireMember(context.session);
  if (state.settings.get('request_mode') === 'off') throw new Refused(409, 'requests_off', REQUESTS_OFF);
  const staff = context.session !== 'member';
  if (!staff && state.settings.get('request_who_can_file') === 'staff') {
    throw new Refused(403, 'staff_only', REQUEST_STAFF_ONLY);
  }
  const mine = actorOf(context.session);
  const body = await context.body();
  const fields = askFields(body);
  const made = {
    id: state.nextAsk++,
    user_id: mine,
    ...fields,
    status: 'open',
    priority: null,
    assignee_id: null,
    notes: null,
    created_at: now(),
    decided_by: null,
    decided_at: null,
    decline_reason: null,
    held_from: null,
    built: null,
    how_to_test: null,
    ready_by: null,
    sent_back_reason: null,
    done_at: null,
    message_id: null,
  };
  state.asks.push(made);
  logAction('web.request.filed', { actor_id: mine, target_id: mine, details: { request_id: made.id } });
  return { request: askRow(made), message: `Filed as **#${made.id}** — staff will see it on this page.` };
});

route('POST', '/api/requests/forum', (context) => {
  requireStaff(context.session);
  const known = state.settings.get('request_forum_channel_id');
  if (known) {
    throw new Refused(409, 'forum_exists', `<#${known}> is already the request forum, so nothing was made. Clear **request_forum_channel_id** on the Settings page first if you want a new one.`);
  }
  if (!state.settings.get('modmail_category_id')) {
    throw new Refused(409, 'no_category', '**modmail_category_id** is not pointed at a category Black Bloc can see, so there is nowhere under Blackmail to make the forum. Point it at one with `/modmail` ▸ **Setup…** ▸ **Ticket category…** first.');
  }
  const channelId = String(Date.now());
  state.settings.set('request_forum_channel_id', channelId);
  logAction('web.request.forum_made', { target_id: channelId, details: { channel_id: channelId } });
  return { made: true, channel_id: channelId, message: `<#${channelId}> is up: a forum under the Blackmail category, with its overwrites, and one tag for each place a request can be.` };
});

route('GET', '/api/requests/mine', (context) => {
  requireMember(context.session);
  const mine = actorOf(context.session);
  const rows = asksSorted(state.asks.filter((row) => String(row.user_id) === String(mine)));
  return askPage(rows, context.url.searchParams.get('page'));
});

route('GET', '/api/requests/export.csv', (context) => {
  requireStaff(context.session);
  const header = 'id,status,what,why,due_on,priority,requester_id,requester_name,assignee_id,assignee_name,created_at,decided_by,decided_at,decline_reason,held_from,built,how_to_test,ready_by,sent_back_reason,done_at,comments';
  const lines = asksSorted(state.asks).map((row) => {
    const shown = askRow(row);
    return [
      shown.id,
      shown.status,
      `"${shown.what.split('"').join('""')}"`,
      `"${shown.why.split('"').join('""')}"`,
      shown.due_on || '',
      shown.priority === null ? '' : shown.priority,
      (shown.requester || {}).id || '',
      (shown.requester || {}).name || '',
      (shown.assignee || {}).id || '',
      (shown.assignee || {}).name || '',
      shown.created_at,
      shown.decided_by || '',
      shown.decided_at || '',
      shown.decline_reason || '',
      shown.held_from || '',
      `"${String(shown.built || '').split('"').join('""')}"`,
      `"${String(shown.how_to_test || '').split('"').join('""')}"`,
      shown.ready_by || '',
      `"${String(shown.sent_back_reason || '').split('"').join('""')}"`,
      shown.done_at || '',
      shown.comment_count,
    ].join(',');
  });
  return {
    status: 200,
    headers: { 'content-type': 'text/csv; charset=utf-8', 'content-disposition': 'attachment; filename="requests.csv"' },
    body: [header, ...lines].join('\n'),
  };
});

route('GET', '/api/requests/:id', (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  return {
    request: askRow(row),
    comments: state.askComments.filter((one) => one.request_id === row.id).map(askCommentRow),
  };
});

route('POST', '/api/requests/:id/decline', async (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  const body = await context.body();
  const reason = String(body.reason || '').trim().slice(0, 400);
  if (!reason) throw new Refused(400, 'no_reason', REQUEST_DECLINE_NEEDS_A_REASON);
  return { request: askRow(row), message: askDecide(row, 'declined', reason) };
});

route('POST', '/api/requests/:id/hold', async (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  const body = await context.body();
  const reason = String(body.reason || '').trim().slice(0, 400);
  if (!reason) throw new Refused(400, 'no_reason', REQUEST_HOLD_NEEDS_A_REASON);
  return { request: askRow(row), message: askDecide(row, 'hold', reason) };
});

route('POST', '/api/requests/:id/resume', (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  return { request: askRow(row), message: askResume(row) };
});

route('POST', '/api/requests/:id/ready', async (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  const body = await context.body();
  const built = String(body.built || '').trim().slice(0, 1000);
  if (!built) throw new Refused(400, 'no_built', REQUEST_READY_NEEDS_BUILT.split('{id}').join(row.id));
  const howToTest = String(body.how_to_test || '').trim().slice(0, 1000);
  const said = askDecide(row, 'review', null, { built, how_to_test: howToTest });
  return { request: askRow(row), message: said };
});

route('POST', '/api/requests/:id/accept', async (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  await context.body();
  // The row is read AFTER the move, not as an argument beside it: JavaScript evaluates the
  // object's properties in order and `askRow` would otherwise answer the state it was in.
  const said = askDecide(row, 'done', null);
  return { request: askRow(row), message: said };
});

route('POST', '/api/requests/:id/sendback', async (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  const body = await context.body();
  const reason = String(body.reason || '').trim().slice(0, 500);
  if (!reason) throw new Refused(400, 'no_reason', REQUEST_SENDBACK_NEEDS_A_NOTE);
  if (row.status !== 'review') {
    throw new Refused(409, 'not_decided', notReadyToCheck(row, 'send back'));
  }
  const said = askDecide(row, 'in_progress', null, { sent_back_reason: reason });
  return { request: askRow(row), message: said };
});

route('POST', '/api/requests/:id/check', async (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  await context.body();
  if (row.status !== 'review') {
    throw new Refused(409, 'not_decided', notReadyToCheck(row, 'ask them to check'));
  }
  row.check_asked_by = STAFF.id;
  row.check_asked_at = now();
  logAction('web.request.check_asked', { target_id: row.user_id, details: { request_id: row.id, told: 'dm' } });
  return {
    request: askRow(row),
    message: REQUEST_CHECK_ASKED.split('{id}').join(row.id).split('{who}').join(`<@${row.user_id}>`),
  };
});

route('POST', '/api/requests/:id/status', async (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  const body = await context.body();
  const changed = [];
  if ('assignee_id' in body) {
    const given = body.assignee_id;
    if (given === null || given === '') row.assignee_id = null;
    else if (!MEMBERS.some((one) => one.id === String(given))) {
      throw new Refused(400, 'no_such_member', `**${given}** is not somebody Black Bloc can see in this server, so nothing was changed. Pick a name from the list.`);
    } else row.assignee_id = String(given);
    changed.push('assignee_id');
  }
  if ('priority' in body) {
    const given = body.priority;
    if (given === null || given === '') row.priority = null;
    else {
      const number = Number(given);
      if (!Number.isInteger(number) || number < 0 || number > REQUEST_PRIORITY_MAX) {
        throw new Refused(400, 'request_refused', `**${given}** is not a priority Black Bloc can read, so nothing was changed. Send a whole number from 0 to ${REQUEST_PRIORITY_MAX}, or nothing at all to leave it unranked.`);
      }
      row.priority = number;
    }
    changed.push('priority');
  }
  if ('notes' in body) {
    row.notes = String(body.notes || '').trim().slice(0, 1000) || null;
    changed.push('notes');
  }
  // A typo in "how to test" must not need a state change to fix (owner, 2026-09-03).
  if ('built' in body) {
    row.built = String(body.built || '').trim().slice(0, 1000) || null;
    changed.push('built');
  }
  if ('how_to_test' in body) {
    row.how_to_test = String(body.how_to_test || '').trim().slice(0, 1000) || null;
    changed.push('how_to_test');
  }
  const status = body.status ? String(body.status).trim().toLowerCase() : null;
  if (status && !REQUEST_STAFF_STATUSES.includes(status)) {
    throw new Refused(400, 'request_refused', `**${body.status}** is not a state a request can be in, so nothing was changed. They are ${REQUEST_STAFF_STATUSES.join(', ')}.`);
  }
  if (!status && !changed.length) throw new Refused(400, 'nothing_to_save', REQUEST_NOTHING_TO_SAVE);
  let said = `Request **#${row.id}** is saved.`;
  if (changed.length) logAction('web.request.updated', { details: { request_id: row.id, changed: changed.sort() } });
  if (status) {
    said = askDecide(row, status, String(body.reason || '').trim() || null, {
      built: body.built,
      how_to_test: body.how_to_test,
      sent_back_reason: String(body.sent_back_reason || body.reason || '').trim() || null,
    });
  }
  return { request: askRow(row), message: said };
});

route('POST', '/api/requests/:id/withdraw', (context) => {
  requireMember(context.session);
  const mine = actorOf(context.session);
  const row = wantedAsk(context.params.id);
  if (String(row.user_id) !== String(mine)) {
    throw new Refused(403, 'not_yours', `Request **#${row.id}** is not yours, so nothing was withdrawn. Only the person who filed it can take it back; staff decline one instead.`);
  }
  if (!REQUEST_WITHDRAWABLE.includes(row.status)) {
    throw new Refused(409, 'too_late_to_withdraw', `Request **#${row.id}** is **${REQUEST_STATUS_WORDS[row.status]}**, so there was nothing to withdraw. You can take back one that is still open or on hold; ask staff if you want this one stopped.`);
  }
  row.status = 'withdrawn';
  logAction('web.request.withdrawn', { actor_id: mine, target_id: row.user_id, details: { request_id: row.id } });
  return { request: askRow(row), message: `Request **#${row.id}** is withdrawn. Nobody will pick it up now.` };
});

route('POST', '/api/requests/:id/comments', async (context) => {
  requireStaff(context.session);
  const row = wantedAsk(context.params.id);
  const body = await context.body();
  const text = String(body.text || '').trim().slice(0, 1000);
  if (!text) throw new Refused(400, 'no_text', REQUEST_COMMENT_NEEDS_TEXT);
  const made = { id: state.nextAskComment++, request_id: row.id, author_id: STAFF.id, text, at: now() };
  state.askComments.push(made);
  logAction('web.request.comment', { details: { request_id: row.id, comment_id: made.id } });
  return { comment: askCommentRow(made), message: `Your comment is on request **#${row.id}**.` };
});

function send(response, status, body, headers = {}) {
  // A string body is already the bytes to send (the CSV export); everything else is JSON.
  const payload = body === null ? '' : typeof body === 'string' ? body : JSON.stringify(body);
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    ...headers,
  });
  response.end(payload);
}

const CSP = "default-src 'self'; img-src 'self' data: https://cdn.discordapp.com https://media.discordapp.net; "
  + "style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'";

// A lower environment: with LIVE_ROOT set to a checkout of the deployed release, every path
// outside /preview serves that release's site, and /preview/<page> serves the working tree's
// preview page (or, failing that, its real page) on the working tree's assets — so what is
// coming can be compared with what is live today at the normal URL.
const LIVE_ROOT = process.env.LIVE_ROOT ? resolve(process.env.LIVE_ROOT, 'site', 'public') : null;
const PREVIEW_ASSETS = /(src|href)="\/assets\//g;

function whereFrom(wanted) {
  if (!LIVE_ROOT) return { root: PUBLIC, path: wanted, rewrite: false };
  if (wanted === '/previews' || wanted.startsWith('/previews/')) return { root: PUBLIC, path: wanted, rewrite: true };
  if (wanted.startsWith('/preview/assets/')) return { root: PUBLIC, path: wanted.slice('/preview'.length), rewrite: false };
  if (wanted.startsWith('/preview/')) return { root: PUBLIC, path: wanted, rewrite: true, fallback: wanted.slice('/preview'.length) };
  return { root: LIVE_ROOT, path: wanted, rewrite: false };
}

async function serveStatic(request, response, path, asked) {
  const wanted = path === '/' ? '/index.html' : path;
  const cookie = asked ? { 'set-cookie': `mock_as=${asked}; Path=/; SameSite=Lax` } : {};
  const from = whereFrom(wanted);
  const under = (rel) => join(from.root, normalize(rel).replace(/^([/\\])+/, ''));
  let target = under(from.path);
  if (from.fallback) {
    try { await stat(target); } catch (e) { target = under(from.fallback); }
  }
  if (!target.startsWith(from.root)) {
    response.writeHead(403, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('outside the site directory');
    return;
  }
  try {
    let info = await stat(target);
    let file = target;
    if (info.isDirectory()) {
      if (!wanted.endsWith('/')) {
        response.writeHead(307, { location: `${wanted}/`, ...cookie });
        response.end();
        return;
      }
      file = join(target, 'index.html');
      info = await stat(file);
    }
    const html = extname(file) === '.html';
    let body = html ? stamp(await readFile(file, 'utf8')) : await readFile(file);
    if (html && from.rewrite) body = body.replace(PREVIEW_ASSETS, '$1="/preview/assets/');
    response.writeHead(200, {
      'content-type': TYPES[extname(file)] || 'application/octet-stream',
      'cache-control': html ? NO_STORE : REVALIDATE,
      ...(html ? { 'content-security-policy': CSP } : {}),
      ...cookie,
    });
    response.end(body);
  } catch (e) {
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    response.end(`no such file: ${wanted}`);
  }
}

// --- Applications (19) -------------------------------------------------------------
// The Role menus page owns "how members get roles", so the Applications section lives
// there rather than on a page of its own.

const APPLICATION_STATUSES = ['pending', 'approved', 'denied', 'withdrawn', 'removed'];
const QUESTIONS_MAX = 5;
// The one seeded member who is on a list but is no longer in the server. The record outlives
// the membership, so `nameFor` still knows them and the roster flags them rather than hiding
// them — which is what applications_roster_shows_left decides.
const GONE_FROM_GUILD = new Set([MEMBERS[7].id]);
const NO_ROSTER_FORM = 'Black Bloc has no application form with that number, so there is no list to show. Reload the Role menus page — somebody may have deleted it.';
const REMOVE_NEEDS_A_REASON = 'Taking somebody off the list needs one line they are sent, so nothing was done. Say why and send it again.';
const REMOVE_IS_FOR_LISTS = (name, role) => `**${name}** hands over <@&${role}>, so there is no list to take them off; \`/rolemenu\` ▸ **Grants…** ▸ the grant ▸ **End it now** takes the role back and ends the grant — the approval stays on record.`;
const REMOVE_NOT_APPROVED = (status) => `That application is **${status}**, not approved, so there was nobody to take off the list. \`/applications list status:approved\` says who is on it.`;
const NO_SUCH_FORM = 'Black Bloc has no application form with that number any more, so nothing was changed. Reload the Role menus page — somebody may have deleted it.';
const NO_SUCH_APPLICATION = 'Black Bloc has no application with that number any more, so nothing was changed. Reload the Role menus page.';

function applicationForm(id) {
  const found = state.applicationForms.find((one) => String(one.id) === String(id));
  if (!found) throw new Refused(404, 'no_such_form', NO_SUCH_FORM);
  return found;
}

function pendingOn(formId) {
  return state.applications.filter((one) => one.form_id === formId && one.status === 'pending').length;
}

function applicationFormRow(form) {
  return {
    id: form.id,
    name: form.name,
    title: form.title,
    description: form.description,
    role_id: form.role_id,
    role_name: form.role_id ? memberName(form.role_id) : null,
    review_channel_id: form.review_channel_id,
    approver_role_id: form.approver_role_id,
    owner_user_id: form.owner_user_id,
    owner_name: form.owner_user_id ? memberName(form.owner_user_id) : null,
    next_step: form.next_step,
    approved_text: form.approved_text,
    expires_days: form.expires_days,
    retry_days: form.retry_days,
    open: Boolean(form.open),
    panel_channel_id: form.panel_channel_id,
    panel_message_id: form.panel_message_id,
    pending: pendingOn(form.id),
    questions: form.questions.map((one) => ({ ...one })),
  };
}

function applicationRow(row) {
  const form = state.applicationForms.find((one) => one.id === row.form_id);
  return {
    id: row.id,
    form_id: String(row.form_id),
    form_name: form ? form.name : null,
    user_id: row.user_id,
    user_name: memberName(row.user_id),
    user_avatar: null,
    status: row.status,
    submitted_at: row.submitted_at,
    decided_by_id: row.decided_by,
    decided_by_name: row.decided_by ? memberName(row.decided_by) : null,
    decided_at: row.decided_at,
    deny_reason: row.deny_reason,
    grant_id: row.grant_id,
    answers: row.answers.map((one) => ({ ...one })),
  };
}

function wantedQuestions(given) {
  if (!Array.isArray(given)) {
    throw new Refused(400, 'bad_questions', 'The questions arrived in a shape Black Bloc could not read, so nothing was changed. It is a fault in the page rather than in what you typed — reload the Role menus page and try again.');
  }
  if (given.length > QUESTIONS_MAX) {
    throw new Refused(400, 'bad_request', `Discord shows at most ${QUESTIONS_MAX} boxes on one form and this would be number ${given.length}, so nothing was added. Remove one with \`/applications question remove\` first.`);
  }
  return given.map((one, at) => ({
    position: at + 1,
    label: String(one.label || '').slice(0, 45),
    style: one.style === 'long' ? 'long' : 'short',
    required: one.required === undefined ? true : Boolean(one.required),
    placeholder: one.placeholder || null,
  }));
}

route('GET', '/api/applications/status', (context) => {
  requireStaff(context.session);
  return {
    mode: state.settings.get('applications_mode') || 'off',
    forms: state.applicationForms.length,
    open_forms: state.applicationForms.filter((one) => one.open).length,
    pending: state.applications.filter((one) => one.status === 'pending').length,
    questions_max: QUESTIONS_MAX,
  };
});

route('GET', '/api/applications/forms', (context) => {
  requireStaff(context.session);
  return state.applicationForms.map(applicationFormRow);
});

route('POST', '/api/applications/forms', async (context) => {
  requireStaff(context.session);
  const body = await context.body();
  const name = String(body.name || '').trim().toLowerCase();
  if (!name || !body.title) {
    throw new Refused(400, 'bad_request', 'An application form needs a short name and a heading, so nothing was created. Fill both in and try again — the role is optional, and a form without one keeps a list instead.');
  }
  if (!/^[a-z0-9][a-z0-9_-]*$/.test(name)) {
    throw new Refused(400, 'bad_request', `**${body.name}** is not a name Black Bloc can use, so nothing was changed. Use lower-case letters, numbers, \`-\` and \`_\`, start with a letter or a number, and keep it under 32 characters — \`twitch-team\` is the shape.`);
  }
  if (state.applicationForms.some((one) => one.name === name)) {
    throw new Refused(400, 'name_taken', `This server already has an application form called **${name}**, so nothing was created. Pick another name, or change that one with \`/applications edit\`.`);
  }
  const form = {
    id: state.nextApplicationForm++,
    name,
    title: String(body.title),
    description: body.description || null,
    role_id: body.role_id ? String(body.role_id) : null,
    review_channel_id: body.review_channel_id ? String(body.review_channel_id) : null,
    approver_role_id: body.approver_role_id ? String(body.approver_role_id) : null,
    owner_user_id: null,
    next_step: null,
    approved_text: null,
    expires_days: null,
    retry_days: null,
    open: true,
    panel_channel_id: null,
    panel_message_id: null,
    questions: [],
  };
  state.applicationForms.push(form);
  logAction('web.application.form_created', { reason: name, details: { form: name, role_id: form.role_id } });
  return applicationFormRow(form);
});

route('PATCH', '/api/applications/forms/:id', async (context) => {
  requireStaff(context.session);
  const form = applicationForm(context.params.id);
  const body = await context.body();
  const changed = [];
  for (const field of ['title', 'description', 'next_step', 'approved_text', 'expires_days', 'retry_days', 'open']) {
    if (body[field] !== undefined) {
      form[field] = body[field];
      changed.push(field);
    }
  }
  for (const field of ['role_id', 'review_channel_id', 'approver_role_id', 'owner_user_id']) {
    if (body[field] !== undefined) {
      form[field] = body[field] ? String(body[field]) : null;
      changed.push(field);
    }
  }
  logAction('web.application.form_updated', { reason: form.name, details: { form: form.name, changed } });
  return applicationFormRow(form);
});

route('DELETE', '/api/applications/forms/:id', (context) => {
  requireStaff(context.session);
  const form = applicationForm(context.params.id);
  const waiting = pendingOn(form.id);
  if (waiting) {
    throw new Refused(409, 'form_has_pending', `**${form.name}** still has ${waiting} application(s) waiting on staff, so it was not deleted. Decide them first, or close the form with \`/applications edit ${form.name} open:false\`.`);
  }
  state.applicationForms = state.applicationForms.filter((one) => one.id !== form.id);
  logAction('web.application.form_deleted', { reason: form.name, details: { form: form.name } });
  return { deleted: true, id: form.id, name: form.name };
});

route('PUT', '/api/applications/forms/:id/questions', async (context) => {
  requireStaff(context.session);
  const form = applicationForm(context.params.id);
  const body = await context.body();
  form.questions = wantedQuestions(body.questions);
  logAction('web.application.question_changed', { reason: form.name, details: { form: form.name, questions: form.questions.length } });
  return applicationFormRow(form);
});

route('POST', '/api/applications/forms/:id/panel', async (context) => {
  requireStaff(context.session);
  const form = applicationForm(context.params.id);
  const body = await context.body();
  const channelId = body.channel_id ? String(body.channel_id) : form.panel_channel_id;
  if (!channelId || !CHANNELS.some((one) => one.id === channelId)) {
    throw new Refused(400, 'no_such_channel', `**${channelId}** is not a channel Black Bloc can see, so nothing was posted. Pick one from the list and try again.`);
  }
  guard('putting an Apply button up');
  form.panel_channel_id = channelId;
  form.panel_message_id = String(Date.now());
  logAction('web.application.panel_posted', { reason: form.name, target_id: channelId, details: { form: form.name, channel_id: channelId, message_id: form.panel_message_id } });
  return { posted: true, id: form.id, name: form.name, channel_id: channelId, message_id: form.panel_message_id };
});

route('GET', '/api/applications/roster', (context) => {
  requireStaff(context.session);
  const wanted = context.url.searchParams.get('form');
  const form = state.applicationForms.find((one) => String(one.id) === String(wanted));
  if (!form) throw new Refused(404, 'no_such_form', NO_ROSTER_FORM);
  const showsLeft = state.settings.get('applications_roster_shows_left') !== false;
  return state.applications
    .filter((one) => one.form_id === form.id && one.status === 'approved')
    .filter((one) => showsLeft || !GONE_FROM_GUILD.has(one.user_id))
    .sort((a, b) => b.id - a.id)
    .map((one) => {
      const link = state.golive.links.find((two) => two.user_id === one.user_id);
      return {
        application_id: one.id,
        user_id: one.user_id,
        user_name: memberName(one.user_id),
        user_avatar: null,
        in_server: !GONE_FROM_GUILD.has(one.user_id),
        twitch_login: link ? link.twitch_login : null,
        decided_at: one.decided_at,
        decided_by_name: one.decided_by ? memberName(one.decided_by) : null,
      };
    });
});

route('GET', '/api/applications', (context) => {
  requireStaff(context.session);
  const wantedForm = context.url.searchParams.get('form');
  const wantedStatus = (context.url.searchParams.get('status') || '').split(',').filter(Boolean);
  for (const one of wantedStatus) {
    if (!APPLICATION_STATUSES.includes(one)) {
      throw new Refused(400, 'unknown_status', `**${one}** is not a state an application can be in, so nothing was listed. They are ${APPLICATION_STATUSES.join(', ')}.`);
    }
  }
  return state.applications
    .filter((one) => (wantedForm ? String(one.form_id) === String(wantedForm) : true))
    .filter((one) => (wantedStatus.length ? wantedStatus.includes(one.status) : true))
    .slice()
    .sort((a, b) => (a.status === 'pending' ? 0 : 1) - (b.status === 'pending' ? 0 : 1) || b.id - a.id)
    .map(applicationRow);
});

route('GET', '/api/applications/:id', (context) => {
  requireStaff(context.session);
  const row = state.applications.find((one) => String(one.id) === String(context.params.id));
  if (!row) throw new Refused(404, 'no_such_application', NO_SUCH_APPLICATION);
  return applicationRow(row);
});

route('POST', '/api/applications/:id/decide', async (context) => {
  requireStaff(context.session);
  const row = state.applications.find((one) => String(one.id) === String(context.params.id));
  if (!row) throw new Refused(404, 'no_such_application', NO_SUCH_APPLICATION);
  const body = await context.body();
  const status = String(body.status || '');
  if (status !== 'approved' && status !== 'denied') {
    throw new Refused(400, 'bad_status', `**${status || 'nothing'}** is not a decision, so nothing was changed. It is \`approved\` or \`denied\`.`);
  }
  const reason = String(body.reason || '').trim();
  if (status === 'denied' && !reason) {
    throw new Refused(400, 'no_reason', 'A denied application needs one line the person is sent, so nothing was done. Say why and send it again.');
  }
  if (row.status !== 'pending') {
    throw new Refused(409, 'not_decided', `Somebody got there first — that application is already **${row.status}**, so nothing was changed. The card above says who decided and when.`);
  }
  const form = state.applicationForms.find((one) => one.id === row.form_id);
  row.status = status;
  row.decided_by = STAFF.id;
  row.decided_at = now();
  row.deny_reason = status === 'denied' ? reason : null;
  if (status === 'approved') row.grant_id = String(state.nextGrant++);
  logAction(`web.application.${status}`, { target_id: row.user_id, reason: reason || null, details: { application_id: row.id, form: form ? form.name : null } });
  return {
    application: applicationRow(row),
    message: status === 'approved'
      ? `Approved — **${memberName(row.user_id)}** has that role now.`
      : 'Denied, and they have been told why.',
  };
});

route('POST', '/api/applications/:id/remove', async (context) => {
  requireStaff(context.session);
  const row = state.applications.find((one) => String(one.id) === String(context.params.id));
  if (!row) throw new Refused(404, 'no_such_application', NO_SUCH_APPLICATION);
  const body = await context.body();
  const reason = String(body.reason || '').trim();
  if (!reason) throw new Refused(400, 'no_reason', REMOVE_NEEDS_A_REASON);
  const form = state.applicationForms.find((one) => one.id === row.form_id);
  if (form && form.role_id) {
    throw new Refused(400, 'not_removed', REMOVE_IS_FOR_LISTS(form.name, form.role_id));
  }
  if (row.status !== 'approved') {
    throw new Refused(400, 'not_removed', REMOVE_NOT_APPROVED(row.status));
  }
  row.status = 'removed';
  row.decided_by = STAFF.id;
  row.decided_at = now();
  row.deny_reason = reason;
  logAction('web.application.removed', { target_id: row.user_id, reason, details: { application_id: row.id, form: form ? form.name : null, reason } });
  return {
    application: applicationRow(row),
    message: 'Taken off the list, and they have been told why.',
  };
});

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
