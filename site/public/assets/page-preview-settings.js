import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  button,
  card,
  el,
  humanLabel,
  keysSwitch,
  notice,
  saveBar,
  searchField,
  section,
  settingRow,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

const AT = Date.now();
const minutesAgo = (n) => new Date(AT - n * 60000).toISOString();
const FIRST = 'core';
const FLASH_MS = 2400;

const SETTINGS = {
  "core": [
    {"key":"log_channel_id","type":"channel","value":"800000000000000004","default":null,"help":"where Black Bloc posts what it did"},
    {"key":"shadow_channel_id","type":"channel","value":null,"default":null,"help":"where every rehearsal goes while a feature is in shadow — the welcome post, the front door, the ticket button, polls; blank means the bot’s own log channel. Setting it is the deliberate act that lets test mode speak in that one channel as well, so pick a channel only the people reviewing can see"},
    {"key":"rehearsal_note","type":"text","value":"Rehearsal — this is where it would go: {channel}","default":"Rehearsal — this is where it would go: {channel}","help":"the line the front door and the ticket button carry at the top of their rehearsal copy; {channel} is replaced with the channel the real one is aimed at. Blank leaves the copy with no note at all"},
    {"key":"staff_channel_id","type":"channel","value":"800000000000000005","default":null,"help":"the channel whose viewers count as staff"},
    {"key":"role_menu_channel_id","type":"channel","value":"800000000000000002","default":null,"help":"the channel /rolemenu offers first when a menu is posted"},
    {"key":"core_log_level","type":"enum","value":"important","default":"important","help":"which core log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard either way","choices":["off","important","all"]},
  ],
  "golive": [
    {"key":"golive_mode","type":"enum","value":"shadow","default":"off","help":"off, shadow (log only) or on (post go-live announcements)","choices":["off","shadow","on"]},
    {"key":"golive_channel_id","type":"channel","value":"800000000000000006","default":null,"help":"where go-live announcements are posted"},
    {"key":"golive_template","type":"text","value":"{name} is live playing {game} — {title} {url}","default":"{name} is live: {url}","help":"the announcement wording; {name} {game} {title} {url} {platform}"},
    {"key":"golive_end_template","type":"text","value":"{live} — stream ended","default":"{live} — stream ended","help":"the announcement once the stream is over, and the only place that wording lives. {live} is the sentence exactly as it was posted, so {live} — stream ended appends and a wording without {live} rewrites the whole post; the other fields are {name} {game} {title} {url} {platform} {duration}. Blank keeps the posted sentence and adds nothing; wording that cannot be rendered falls back to the default"},
  ],
  "pings": [
    {"key":"pings_mode","type":"enum","value":"off","default":"off","help":"off, or on (members can opt in to go-live and event pings, and a streamer can have a role of their own that only their followers wear)","choices":["off","on"]},
    {"key":"pings_events_role_name","type":"text","value":"Events","default":"Events","help":"what **Set up the Events role** on `/pings` calls the one opt-in role for go-live and event pings when it has to make it; an existing role of that name is reused rather than duplicated"},
    {"key":"pings_fan_role_creation","type":"enum","value":"follow","default":"follow","help":"when a streamer’s ping role is made: follow (the first person to follow them on `/pings` makes it, which is the default so a role exists only where somebody wants it), self (the streamer, with **Start my own ping role** on `/pings`), staff (only an Auntie/Uncle, from `/pings` ▸ **Streamers…**), or auto (one is made the moment a Twitch channel is linked). Staff can always do it for anybody, whichever this says","choices":["self","staff","auto","follow"]},
    {"key":"pings_fan_role_template","type":"text","value":"{name} pings","default":"{name} pings","help":"what a streamer’s own ping role is called; {name} is their display name at the moment the role is made and is the only field there is"},
  ],
  "tempvoice": [
    {"key":"tempvoice_mode","type":"enum","value":"on","default":"off","help":"off, shadow (join-to-create works, but only staff can see the lobby — the rooms it spawns follow it), or on (the lobby is visible to whoever its category shows)","choices":["off","shadow","on"]},
    {"key":"tempvoice_creator_ids","type":"channels","value":["800000000000000009"],"default":[],"help":"the join-to-create channels; Setup on /voice fills this in"},
    {"key":"tempvoice_name_template","type":"text","value":"{user}'s room","default":"{user}'s room","help":"what a spawned channel is called; {user} is the member"},
  ],
  "honeypot": [
    {"key":"honeypot_mode","type":"enum","value":"shadow","default":"off","help":"off, shadow (log only) or on (ban whoever posts in the trap)","choices":["off","shadow","on"]},
    {"key":"honeypot_channel_ids","type":"channels","value":["800000000000000007"],"default":[],"help":"the trap channels; Setup… on /honeypot fills this in"},
    {"key":"honeypot_purge_days","type":"int","value":1,"default":1,"help":"days of the banned account’s messages to delete with it, 0 to 7","max":7},
    {"key":"honeypot_exempt_role_ids","type":"roles","value":["900000000000000001"],"default":[],"help":"roles the trap ignores; staff are always ignored too"},
    {"key":"honeypot_log_level","type":"enum","value":"important","default":"important","help":"which honeypot log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/honeypot logs` either way","choices":["off","important","all"]},
    {"key":"honeypot_panel_minutes","type":"int","value":10,"default":10,"help":"minutes the /honeypot panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"},
  ],
  "events": [
    {"key":"events_mode","type":"enum","value":"on","default":"off","help":"off, shadow (no public announcement) or on (announce approved events)","choices":["off","shadow","on"]},
    {"key":"events_category_id","type":"channel","value":"800000000000000008","default":null,"help":"the category review channels are made in"},
    {"key":"events_announce_channel_id","type":"channel","value":"800000000000000006","default":null,"help":"where an approved event is announced"},
    {"key":"events_ping_role_id","type":"role","value":null,"default":null,"help":"role mentioned when an event is announced and when it starts"},
    {"key":"events_create_scheduled","type":"bool","value":true,"default":false,"help":"true to make a real Discord scheduled event when one is approved"},
  ],
  "poll": [
    {"key":"poll_mode","type":"enum","value":"on","default":"on","help":"off, shadow (every poll is posted for real, but into the log channel with a line saying why, so staff can rehearse), or on (polls go where they are pointed)","choices":["off","shadow","on"]},
    {"key":"poll_who_can_create","type":"enum","value":"staff","default":"staff","help":"who may run /poll create: staff, or everyone","choices":["staff","everyone"]},
    {"key":"poll_review_mode","type":"enum","value":"off","default":"off","help":"off posts a poll straight away; on holds it for a staff Approve or Deny first","choices":["off","on"]},
    {"key":"poll_default_hours","type":"int","value":24,"default":24,"help":"hours a poll stays open when nobody says otherwise, 1 to 768 (32 days)","max":768,"min":1},
  ],
  "birthday": [
    {"key":"birthday_mode","type":"enum","value":"shadow","default":"off","help":"off, shadow (log only) or on (post birthday wishes)","choices":["off","shadow","on"]},
    {"key":"birthday_channel_id","type":"channel","value":"800000000000000002","default":null,"help":"where birthday wishes are posted"},
    {"key":"birthday_template","type":"text","value":"Happy birthday {name}!","default":"Happy birthday {name}!","help":"the birthday wording; {name} and {age}"},
    {"key":"birthday_color","type":"color","value":"#4eefff","default":"#4eefff","help":"the birthday embed’s colour, as a hex code like #4eefff"},
    {"key":"birthday_role_id","type":"role","value":"900000000000000004","default":null,"help":"role given for the day and taken back the next"},
  ],
  "modmail": [
    {"key":"modmail_enabled","type":"bool","value":true,"default":false,"help":"true when Black Bloc answers DMs"},
    {"key":"modmail_mode","type":"enum","value":"thread","default":"channel","help":"channel (one channel per ticket), thread (private threads in the staff channel) or forum (one post per ticket in the forum channel — the list never grows past the forum’s own archive)","choices":["channel","thread","forum"]},
    {"key":"modmail_category_id","type":"channel","value":"800000000000000011","default":null,"help":"the category ticket channels are made in, in channel mode"},
    {"key":"modmail_staff_channel_id","type":"channel","value":"800000000000000005","default":null,"help":"the channel ticket threads are made in, in thread mode"},
    {"key":"modmail_log_channel_id","type":"channel","value":"800000000000000004","default":null,"help":"where a closed ticket’s transcript is posted"},
  ],
  "automod": [
    {"key":"automod_mode","type":"enum","value":"shadow","default":"off","help":"off, shadow (log what it would do) or on (delete, warn and time out)","choices":["off","shadow","on"]},
    {"key":"automod_rules","type":"json","value":null,"default":null,"help":"the automod rule book; the Automod tab is what changes it"},
    {"key":"automod_exempt_role_ids","type":"roles","value":["900000000000000001","900000000000000002"],"default":[],"help":"roles automod ignores"},
    {"key":"automod_exempt_channel_ids","type":"channels","value":["800000000000000003"],"default":[],"help":"channels automod never reads"},
  ],
  "rolemenu": [
    {"key":"rolemenu_approval_channel_id","type":"channel","value":"800000000000000005","default":null,"help":"where a role request card is posted for staff to answer; defaults to staff_channel_id"},
    {"key":"rolemenu_approver_role_id","type":"role","value":null,"default":null,"help":"role mentioned when a role request needs answering"},
    {"key":"rolemenu_mode","type":"enum","value":"off","default":"off","help":"whether members can pick roles from the panels; off takes them down, on posts them again; /rolemenu itself stays either way","choices":["off","on"]},
    {"key":"rolemenu_log_level","type":"enum","value":"important","default":"important","help":"which role menus log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/rolemenu logs` either way","choices":["off","important","all"]},
    {"key":"rolemenu_panel_minutes","type":"int","value":10,"default":10,"help":"minutes the /rolemenu panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"},
  ],
  "chat": [
    {"key":"chat_mode","type":"enum","value":"on","default":"on","help":"off, or on (Black Bloc answers when somebody @-mentions it)","choices":["off","on"]},
    {"key":"chat_cooldown_seconds","type":"int","value":20,"default":20,"help":"seconds before the same person gets another @-mention reply, 5 to 600","max":600,"min":5},
    {"key":"chat_ignore_channels","type":"channels","value":[],"default":[],"help":"channels Black Bloc never answers an @-mention in"},
    {"key":"chat_ignore_categories","type":"channels","value":[],"default":[],"help":"categories Black Bloc leaves out of everything it reads and tells people about — the channel names and topics it learns each day, and the channel list every conversational answer is written against. The modmail category and any category with `archive` in its name are left out already, and so is every channel @everyone cannot see"},
    {"key":"chat_home_channel_id","type":"channel","value":null,"default":null,"help":"where somebody is sent when a conversational answer points at a channel that does not exist. Blank is safe: the sentence is written again without the channel in it rather than pointing anywhere. Either way the invention is logged, so `/chat` ▸ **Logs** and the Logs page count how often it happens"},
  ],
  "youtube": [
    {"key":"youtube_log_level","type":"enum","value":"important","default":"important","help":"which youtube log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/youtube logs` either way","choices":["off","important","all"]},
    {"key":"youtube_panel_minutes","type":"int","value":10,"default":10,"help":"minutes the /youtube panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"},
    {"key":"youtube_unlink_dms_them","type":"bool","value":true,"default":true,"help":"true to DM a member the reason when STAFF forget their YouTube channel for them; a member unlinking their own channel is never DMed"},
    {"key":"youtube_live_mode","type":"enum","value":"off","default":"off","help":"off, shadow (log what would be announced), or on — a linked YouTube channel going live is announced through the go-live feature, exactly like a Twitch stream","choices":["off","shadow","on"]},
  ],
  "request": [
    {"key":"request_log_level","type":"enum","value":"important","default":"important","help":"which requests log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/request logs` either way","choices":["off","important","all"]},
    {"key":"request_mode","type":"enum","value":"on","default":"on","help":"off, or on (members can ask for things with /request and staff decide on the site)","choices":["off","on"]},
    {"key":"request_who_can_file","type":"enum","value":"everyone","default":"everyone","help":"who may file a request: everyone, or staff only","choices":["everyone","staff"]},
    {"key":"request_notify_channel_id","type":"channel","value":"800000000000000003","default":null,"help":"where one line goes when a request is filed; blank tells nobody and the site is the only place they show up"},
  ],
  "raidtrain": [
    {"key":"raidtrain_log_level","type":"enum","value":"important","default":"important","help":"which raid trains log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/raidtrains logs` either way","choices":["off","important","all"]},
    {"key":"raidtrain_mode","type":"enum","value":"off","default":"off","help":"off, shadow (log what would be sent and send nothing) or on (post the lineup and DM slot holders before their hour)","choices":["off","shadow","on"]},
    {"key":"raidtrain_organizer_role_id","type":"role","value":null,"default":null,"help":"role that may build and change a raid train’s lineup as well as staff; blank leaves it to staff alone"},
  ],
  "applications": [
    {"key":"applications_log_level","type":"enum","value":"important","default":"important","help":"which applications log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/applications logs` either way","choices":["off","important","all"]},
    {"key":"applications_mode","type":"enum","value":"off","default":"off","help":"off, shadow (log only, nothing posted or DMed) or on (members can apply and staff decide on the card)","choices":["off","shadow","on"]},
    {"key":"applications_channel_id","type":"channel","value":"800000000000000005","default":null,"help":"where an application card waits for Approve or Deny when the form does not name a channel of its own; blank falls back to rolemenu_approval_channel_id, then to staff_channel_id"},
  ],
  "guides": [
    {"key":"guides_log_level","type":"enum","value":"important","default":"important","help":"which guides log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard either way","choices":["off","important","all"]},
    {"key":"guides_mode","type":"enum","value":"on","default":"on","help":"on to give members the Guides page and to put a guide link beside a command in /help; off hides both. Staff can still open a guide’s web address while it is off, and the page says so. There is no slash command to hide either way","choices":["off","on"]},
    {"key":"guides_who_edits","type":"enum","value":"staff","default":"staff","help":"who may change a guide’s wording and screenshots: staff (anybody who can see the staff channel, the default) or manage_guild (a Lead only). It is read when Save is pressed rather than when the page is drawn, so taking the role away stops the next save","choices":["staff","manage_guild"]},
    {"key":"guides_help_links","type":"bool","value":true,"default":true,"help":"true to add a small guide link beside every /help line whose command has a published guide, and an All the guides button on the last page; false leaves /help exactly as it was"},
  ],
  "posts": [
    {"key":"posts_log_level","type":"enum","value":"important","default":"important","help":"which posts log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/posts logs` either way","choices":["off","important","all"]},
    {"key":"posts_mode","type":"enum","value":"shadow","default":"shadow","help":"off, shadow (Post it sends the real message into the shadow channel — the test channel while test mode is on, otherwise the log channel — and keeps it edited there, whatever channel the post names) or on (Post it goes to the post's own channel, and the first real post removes the shadow copy). Shadow is the default, so nothing reaches members until a Lead turns posts on. Off hides `/posts` and refuses both doors in words; every word already written is kept in all three","choices":["off","shadow","on"]},
    {"key":"posts_panel_minutes","type":"int","value":10,"default":10,"help":"minutes the /posts panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it","max":1440,"min":1},
  ],
  "cost": [
    {"key":"cost_hosting_usd","type":"int","value":0,"default":0,"help":"what the always-on container costs a month in whole dollars — read it off your Fly invoice; 0 = not filled in yet, and the Costs card on the Health page says so rather than claiming hosting is free","max":10000},
  ],
  "memory": [
    {"key":"memory_panel_minutes","type":"int","value":10,"default":10,"help":"minutes the /memory panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"},
  ],
  "voice": [
    {"key":"voice_panel_minutes","type":"int","value":10,"default":10,"help":"minutes the /voice panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"},
  ],
  "emoji": [
    {"key":"emoji_skin_tone","type":"enum","value":"dark","default":"dark","help":"the skin tone Black Bloc's hand and people emoji wear: none, light, medium-light, medium, medium-dark, dark","choices":["none","light","medium-light","medium","medium-dark","dark"]},
  ],
  "event": [
    {"key":"event_panel_minutes","type":"int","value":10,"default":10,"help":"minutes the /event panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"},
    {"key":"event_panel_own_list","type":"bool","value":false,"default":false,"help":"true to show members the events they proposed on the /event panel; staff always see theirs, and members can still propose one and call one off either way"},
  ],
  "hide": [
    {"key":"hide_commands_when_off","type":"bool","value":true,"default":true,"help":"true to take a feature's slash command out of this server's command list while that feature is turned off, so nobody is offered a command that cannot do anything; turning the feature back on brings the command back within about a minute. false leaves every command showing all the time and an off feature explains itself when it is opened. Only off hides a command — shadow does not"},
  ],
  "logs": [
    {"key":"logs_count","type":"int","value":10,"default":10,"help":"how many lines a Logs button shows to begin with, from 1 to 50; 10 by default. Show more adds the same number again, and stops being offered once the log has run out or 50 lines are shown","max":50,"min":1},
    {"key":"logs_important_only","type":"bool","value":false,"default":false,"help":"true to open every Logs button already filtered to the lines that matter — refusals, errors and staff moves — with Show everything beside the list to see the rest; false opens on everything, which is what it did before"},
  ],
};

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

const LOGS = [
  { id: 41, at: minutesAgo(3), kind: 'web.settings.set', feature: 'core', important: false, via: 'website', actor_id: '700000000000000001', actor_name: 'Nick', target_id: null, target_name: null, reason: 'automod_mode = shadow', summary: 'automod_mode = shadow' },
  { id: 34, at: minutesAgo(220), kind: 'web.settings.set', feature: 'core', important: false, via: 'website', actor_id: '700000000000000001', actor_name: 'Nick', target_id: null, target_name: null, reason: 'automod_mode = shadow', summary: 'automod_mode = shadow' },
  { id: 31, at: minutesAgo(900), kind: 'settings.set', feature: 'core', important: false, via: 'discord', actor_id: '700000000000000002', actor_name: 'Casey', target_id: null, target_name: null, reason: 'golive_mode = shadow', summary: 'golive_mode = shadow' },
];

const CORE_LOGS_NOTE = 'Everything done from this dashboard and every settings change, ' +
  'whoever made it. Settings changes are routine — nothing here acts on a member — so switch ' +
  'to All to see them.';

const NAMESPACE_NOTES = {
  core: 'staff_channel_id is what decides who may see this dashboard.',
  automod: 'automod_rules has its own editor on the Automod tab; the JSON box here is the fallback.',
  cost: 'The Costs card on the Health page is where this figure is read; nothing on the bot can see an invoice.',
  pings: 'The Pings section on the Go-live tab is where the Events role is set up and a streamer’s own role is started.',
};

const NAMESPACE_NAMES = {
  core: 'The basics',
  mod: 'Moderation',
  automod: 'Automod',
  honeypot: 'Honeypot',
  modmail: 'Modmail',
  golive: 'Go-live',
  pings: 'Ping roles',
  events: 'Events',
  birthday: 'Birthdays',
  tempvoice: 'Temp voice',
  rolemenu: 'Role menus',
  poll: 'Polls',
  chat: 'Chat',
  request: 'Requests',
  cost: 'Costs',
};

/**
 * Measured: every page module that calls namespaceSettings or settingsPanel on
 * this namespace, so the pointer the four real notes give is given by all.
 */
const ALSO = {
  golive: ['the Go-live page', '/golive.html'],
  youtube: ['the Go-live page', '/golive.html'],
  pings: ['the Go-live page', '/golive.html'],
  tempvoice: ['the Temp voice page', '/tempvoice.html'],
  honeypot: ['the Honeypot page', '/honeypot.html'],
  events: ['the Events page', '/events.html'],
  raidtrain: ['the Events page', '/events.html'],
  poll: ['the Polls page', '/polls.html'],
  birthday: ['the Birthdays page', '/birthdays.html'],
  modmail: ['the Modmail page', '/modmail.html'],
  automod: ['the Automod page', '/automod.html'],
  rolemenu: ['the Role menus page', '/rolemenus.html'],
  applications: ['the Role menus page', '/rolemenus.html'],
  chat: ['the Chat page', '/chat.html'],
  request: ['the Requests page', '/requests.html'],
  guides: ['the Guides page', '/guides.html'],
  posts: ['the Posts page', '/posts.html'],
  cost: ['the Health page', '/health.html'],
};

const ORPHAN = 'A group of one, because the registry names a namespace from the key’s first ' +
  'word. No page anywhere is called this.';

const named = (namespace) => NAMESPACE_NAMES[namespace]
  || String(namespace).replace(/^./, (c) => c.toUpperCase());

function order(payload) {
  const found = Object.keys(payload || {}).filter((key) => Array.isArray(payload[key]));
  found.sort((a, b) => {
    if (a === FIRST) return -1;
    if (b === FIRST) return 1;
    return a.localeCompare(b);
  });
  return found;
}

const REF = {
  channel: { list: CHANNELS, multiple: false },
  channels: { list: CHANNELS, multiple: true },
  role: { list: ROLES, multiple: false },
  roles: { list: ROLES, multiple: true },
};

const CHANNEL_KIND = { text: '#', voice: '🔊', forum: '#', category: '▸' };

function channelOption(one) {
  const mark = CHANNEL_KIND[one.type] || '#';
  const where = one.category_id
    ? (CHANNELS.find((c) => c.id === one.category_id) || {}).name || ''
    : '';
  return where ? `${mark} ${one.name} · ${where}` : `${mark} ${one.name}`;
}

/** ui.js builds a channel/role control by asking the bot for the list, so a static page grows its own. */
function refControl(spec) {
  const { list, multiple } = REF[spec.type];
  const chosen = new Set((multiple ? spec.value || [] : [spec.value]).filter(Boolean).map(String));
  const select = el('select', {
    class: 'input field-control',
    multiple: multiple || undefined,
    size: multiple ? Math.min(8, Math.max(3, list.length)) : undefined,
  });
  if (!multiple) select.append(el('option', { value: '', text: 'not set', selected: chosen.size === 0 || undefined }));
  for (const one of list) {
    select.append(el('option', {
      value: one.id,
      text: list === CHANNELS ? channelOption(one) : `@${one.name}`,
      selected: chosen.has(String(one.id)) || undefined,
    }));
  }
  return select;
}

function refRow(spec, onDirty) {
  const mark = el('span', { class: 'setrow-mark', text: 'CHANGED', hidden: true });
  const control = refControl(spec);
  const say = notice();
  say.classList.add('setrow-say');
  const node = el('div', {
    class: 'setrow',
    'data-key': spec.key,
    'data-dirty': 'false',
    'data-search': `${spec.key} ${humanLabel(spec.key)} ${spec.type} ${spec.help || ''}`.toLowerCase(),
  }, [
    el('div', { class: 'setrow-head' }, [
      el('span', { class: 'setrow-label', text: humanLabel(spec.key), title: spec.help || undefined }),
      el('span', { class: 'setrow-key', text: spec.key }),
    ]),
    mark,
    el('div', { class: 'setrow-control' }, [control]),
    say,
  ]);
  const row = { key: spec.key, spec, node, dirty: false, say, reset: () => {} };
  control.addEventListener('change', () => {
    row.dirty = true;
    node.setAttribute('data-dirty', 'true');
    mark.hidden = false;
    if (onDirty) onDirty();
  });
  return row;
}

/**
 * ui.js keeps a key's help in the label's title, where a mouse finds it and a
 * reader does not. The preview's whole claim is that this page answers "what
 * does this key do" without leaving it, so the sentence goes under the name.
 */
function showHelp(row, spec) {
  const head = row.node.querySelector('.setrow-head');
  if (!head || !spec.help) return;
  head.append(el('p', {
    class: 'field-help',
    style: 'margin: 2px 0 0; max-width: 46rem;',
    text: spec.help,
  }));
}

async function rowFor(spec, onDirty) {
  const row = REF[spec.type] ? refRow(spec, onDirty) : await settingRow(spec, { onDirty });
  showHelp(row, spec);
  return row;
}

function groupNote(namespace) {
  if (NAMESPACE_NOTES[namespace]) return el('p', { class: 'field-help', text: NAMESPACE_NOTES[namespace] });
  const also = ALSO[namespace];
  if (!also) return el('p', { class: 'field-help', text: ORPHAN });
  return el('p', { class: 'field-help' }, [
    'These keys have a second editor on ',
    el('a', { class: 'celllink', href: also[1], text: also[0] }),
    ' as well. Every one of them is here; only some of them are there.',
  ]);
}

let jumpTo = () => {};

function jumpToKey() {
  const key = decodeURIComponent(String(location.hash || '').replace(/^#/, ''));
  if (!key) return;
  jumpTo(key);
  const row = document.querySelector(`.setrow[data-key="${CSS.escape(key)}"]`);
  if (!row) return;
  row.scrollIntoView({ behavior: 'auto', block: 'center' });
  row.setAttribute('data-found', 'true');
  setTimeout(() => row.removeAttribute('data-found'), FLASH_MS);
}

window.addEventListener('hashchange', jumpToKey);

async function load() {
  const banner = previewBanner({
    today: 26,
    preview: 2,
    note: 'Eighty-seven of the registry’s 276 keys are embedded here, across all 25 groups, with their real help text — enough to judge the shape, not the whole registry.',
  });
  banner.setAttribute('data-span', 'full');

  const namespaces = order(SETTINGS);
  const specs = namespaces.flatMap((namespace) => SETTINGS[namespace]);

  const say = notice();
  const rows = [];
  const dock = saveBar(
    () => wouldDo(say, `PUT /api/settings/<key> — write the ${rows.filter((row) => row.dirty).length} changed key(s), one PUT each, and clear any row emptied back to nothing`),
    () => {
      for (const row of rows) row.reset();
      dock.say(0);
    },
    { where: 'Settings' },
  );
  const recount = () => dock.say(rows.filter((row) => row.dirty).length);

  const byKey = new Map();
  const groups = [];
  for (const namespace of namespaces) {
    const made = [];
    for (const spec of SETTINGS[namespace]) {
      const row = await rowFor(spec, recount);
      rows.push(row);
      made.push(row);
      byKey.set(row.key, row);
    }
    const count = el('span', { class: 'card-count', text: String(made.length) });
    const node = el('div', { class: 'card', 'data-ns': namespace }, [
      el('div', { class: 'card-head' }, [el('h3', { text: named(namespace) }), count]),
      el('div', { class: 'card-body' }, [
        groupNote(namespace),
        el('div', { class: 'settings-grid' }, made.map((row) => row.node)),
      ]),
    ]);
    groups.push({ namespace, node, count, size: made.length });
  }
  recount();

  const list = el('div', { class: 'colstack' }, groups.map((group) => group.node));
  const chips = el('div', { class: 'chipbar' });
  const said = el('span', { class: 'table-count' });
  const state = { query: '', group: '' };
  const none = el('p', { class: 'say-nothing', hidden: true }, [
    el('span', { class: 'say-nothing-text', text: 'No key matches that, in that group.' }),
  ]);
  list.append(none);

  const paint = (query, group) => {
    state.query = query;
    state.group = group;
    let shown = 0;
    for (const one of groups) {
      const wanted = group === '' || group === one.namespace;
      let here = 0;
      for (const row of one.node.querySelectorAll('.setrow')) {
        const hit = wanted && (query === '' || (row.getAttribute('data-search') || '').includes(query));
        row.hidden = !hit;
        if (hit) here += 1;
      }
      shown += here;
      one.node.hidden = here === 0;
      one.count.textContent = String(here);
    }
    said.textContent = query === '' && group === ''
      ? `${specs.length} keys · ${groups.length} groups`
      : `${shown} of ${specs.length} keys`;
    none.hidden = shown > 0;
  };

  const paintChips = (group) => {
    const one = (label, value, title) => el('button', {
      class: 'chip-filter',
      type: 'button',
      'aria-pressed': group === value ? 'true' : 'false',
      title,
      text: label,
      on: {
        click: () => {
          const next = group === value ? '' : value;
          paintChips(next);
          paint(state.query, next);
        },
      },
    });
    chips.replaceChildren(
      one('Everything', '', 'Every key the bot reads'),
      ...groups.map((group_) => one(
        `${named(group_.namespace)} ${group_.size}`,
        group_.namespace,
        ALSO[group_.namespace]
          ? `${named(group_.namespace)} — also edited on ${ALSO[group_.namespace][0]}`
          : `${named(group_.namespace)} — edited here and nowhere else`,
      )),
    );
  };

  const box = searchField({
    label: 'Filter settings',
    placeholder: `Filter ${specs.length} keys…`,
    onQuery: (query) => paint(query, state.group),
  });

  none.append(el('button', {
    class: 'say-nothing-do',
    type: 'button',
    text: 'Clear the search and the group',
    on: {
      click: () => {
        const input = box.querySelector('input');
        if (input) input.value = '';
        paintChips('');
        paint('', '');
      },
    },
  }));

  jumpTo = (key) => {
    if (!byKey.has(key)) return;
    const input = box.querySelector('input');
    if (input) input.value = '';
    paintChips('');
    paint('', '');
  };

  paintChips('');
  paint('', '');

  const aside = document.getElementById('page-aside');
  if (aside) aside.replaceChildren(box, said);

  const all = section('Every setting', null, { count: specs.length, open: true, id: 'every-setting' });
  all.body.append(
    previewWas('Replaces all twenty-five namespace sections. One list, one search, one save bar; the group is a chip over the list instead of a shut header above it, the way the Logs page already filters twenty-one features.'),
    el('p', {
      class: 'section-note',
      text: 'The ⌫ beside a row puts it back to its default; nothing is written until you press ' +
        'Save Changes. Show keys puts each setting’s raw name back under it. Each key’s help ' +
        'sentence is under its name rather than hidden in a tooltip, so "where do I change this" ' +
        'and "what does it do" are answered in the same place.',
    }),
    el('div', { class: 'table-tools' }, [chips, el('span', { class: 'table-gap' }), keysSwitch()]),
    list,
    say,
  );

  const logs = section('Logs', CORE_LOGS_NOTE, { count: LOGS.length });
  logs.body.append(
    previewWas('Replaces the Logs section, unchanged — the one log surface, still shut by default.'),
    logsTable(LOGS, 'Nothing has been changed from this dashboard yet.'),
  );

  document.getElementById('dash').replaceChildren(banner, all.node, logs.node);
  setTimeout(jumpToKey, 0);
}

start({ tab: 'settings', load });
