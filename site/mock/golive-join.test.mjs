// The Go-live page's join, proved without a browser. `site/public/assets/golive-join.js` takes
// the five payloads the page already fetches and answers with one row per person, whichever
// platform they stream on — so every fixture below is one of the six traps in
// docs/info/golive-page-design.md §B1, plus the two co-stream shapes a linked Twitch AND YouTube
// session arrives in.
//
//   node site/mock/golive-join.test.mjs
//
// Exits 0 when every fixture matched, 1 with a list of what did not.
// scripts/deploy.ps1 and .github/workflows/ci.yml run it beside clipmd.test.mjs.

import {
  DRAWERS,
  STRIP_KEYS,
  STRIP_WHERE,
  WORDING_KEYS,
  WORDING_WHERE,
  joinStreamers,
  liveStreams,
  placeSettings,
  routeTyped,
  spotlightCards,
  spotlightSessions,
} from '../public/assets/golive-join.js';

const failures = [];
const fail = (where, said) => failures.push(`${where}: ${said}`);

function is(where, found, wanted) {
  if (found !== wanted) fail(where, `is ${JSON.stringify(found)} not ${JSON.stringify(wanted)}`);
}

function sorted(list) {
  return [...list].sort();
}

function same(where, found, wanted) {
  const a = JSON.stringify(found);
  const b = JSON.stringify(wanted);
  if (a !== b) fail(where, `is\n${a}\n      not\n${b}`);
}

function ok(where, found, said) {
  if (!found) fail(where, said);
}

function has(where, found, wanted) {
  if (!String(found).includes(wanted)) {
    fail(where, `is missing ${JSON.stringify(wanted)}\n      got: ${JSON.stringify(found)}`);
  }
}

function rowFor(rows, id) {
  return rows.find((one) => one.user_id === String(id)) || null;
}

// --- the five payloads, in the shapes the routes answer with -------------------------------
// TWITCH_ONLY is the common case, measured 21 to 1 on the live guild.
const TWITCH_ONLY = '100';
const YOUTUBE_ONLY = '200';
const OPTED_AND_LINKED = '300';
const ROLE_NO_LINK = '400';
const STRANGER = '500';
const TWO_SESSIONS = '600';

const LINKS = [
  { user_id: TWITCH_ONLY, user_name: 'Namu', twitch_login: 'supernamu', linked_at: '2026-09-01T10:00:00Z' },
  { user_id: OPTED_AND_LINKED, user_name: 'RockStarLexxi', twitch_login: 'rockstarlexxi', linked_at: '2026-09-02T10:00:00Z' },
  { user_id: TWO_SESSIONS, user_name: 'Pawpette', twitch_login: 'popnotarts', linked_at: '2026-09-03T10:00:00Z' },
];

const YOUTUBE_LINKS = [
  { user_id: YOUTUBE_ONLY, user_name: 'Aston', channel_id: 'UC7ydYSU1nZOHB7nVV-As_XA', handle: '@glitchaston', title: 'Glitch Aston', linked_at: '2026-09-04T10:00:00Z' },
  { user_id: TWO_SESSIONS, user_name: 'Pawpette', channel_id: 'UCsXVk37bltHxD1rDPwtNM8Q', handle: null, title: 'Pawpette', linked_at: '2026-09-05T10:00:00Z' },
];

const OPTOUTS = [
  { user_id: OPTED_AND_LINKED, user_name: 'RockStarLexxi', at: '2026-09-06T10:00:00Z' },
];

const LISTING = [
  { member_id: TWITCH_ONLY, member: 'Namu', listed: true, role_id: '900', role: 'Namu pings', followers: 14, last_live_at: '2026-09-18T17:01:00Z', live_count: 14 },
  { member_id: ROLE_NO_LINK, member: 'Prez', listed: false, role_id: '901', role: 'Prez pings', followers: 21, last_live_at: null, live_count: 0 },
];

const STREAMERS = [
  { member_id: TWITCH_ONLY, member: 'Namu', role_id: '900', role: 'Namu pings', followers: 14, created_at: '2026-08-01T10:00:00Z', created_by: '1', created_by_name: 'Sky' },
  { member_id: ROLE_NO_LINK, member: 'Prez', role_id: '901', role: 'Prez pings', followers: 21, created_at: '2026-08-02T10:00:00Z', created_by: '1', created_by_name: 'Sky' },
];

const SESSIONS = [
  { id: 12, user_id: TWITCH_ONLY, source: 'twitch', url: 'https://twitch.tv/supernamu', game: 'Fortnite', title: 'birthday eve', started_at: '2026-09-18T17:01:00Z', ended_at: null, mode: 'on', announced_message_id: '830' },
  { id: 11, user_id: STRANGER, user_name: 'Somebody Else', source: 'presence', url: 'https://twitch.tv/somebody', game: 'PEAK', title: 'first time here', started_at: '2026-09-18T18:00:00Z', ended_at: null, mode: 'shadow', announced_message_id: null },
  { id: 10, user_id: TWO_SESSIONS, source: 'presence', url: 'https://twitch.tv/popnotarts', game: 'Onimusha', title: 'NG+', started_at: '2026-09-18T13:13:00Z', ended_at: null, mode: 'on', announced_message_id: '831' },
  { id: 9, user_id: TWO_SESSIONS, source: 'youtube', url: 'https://youtube.com/watch?v=ui6', game: 'Onimusha', title: 'Routing a NG+ Speedrun', started_at: '2026-09-18T20:12:00Z', ended_at: null, mode: 'on', announced_message_id: null },
  { id: 8, user_id: YOUTUBE_ONLY, source: 'youtube', url: 'https://youtube.com/watch?v=old', game: 'Retro', title: 'done', started_at: '2026-09-17T10:00:00Z', ended_at: '2026-09-17T12:00:00Z', mode: 'on', announced_message_id: '832' },
];

const PAYLOAD = {
  links: LINKS,
  youtubeLinks: YOUTUBE_LINKS,
  optouts: OPTOUTS,
  listing: LISTING,
  streamers: STREAMERS,
  sessions: SESSIONS,
  status: null,
};

// --- the six traps ---------------------------------------------------------------------------
{
  const where = 'the six traps';
  const rows = joinStreamers(PAYLOAD);

  is(`${where} — one row per person`, rows.length, 6);
  same(`${where} — sorted by display name`, rows.map((one) => one.name), [
    'Aston', 'Namu', 'Pawpette', 'Prez', 'RockStarLexxi', 'Somebody Else',
  ]);

  // 1. Twitch and no YouTube — the common case.
  const namu = rowFor(rows, TWITCH_ONLY);
  ok(`${where} — 1 Twitch, no YouTube`, namu !== null, 'Namu has no row at all');
  is(`${where} — 1 Twitch, no YouTube`, namu.twitch, 'supernamu');
  is(`${where} — 1 Twitch, no YouTube`, namu.youtube, null);
  is(`${where} — 1 Twitch, no YouTube`, namu.youtube_id, null);
  is(`${where} — 1 the role travels with the person`, namu.role, 'Namu pings');
  is(`${where} — 1 the role travels with the person`, namu.role_wearers, 14);

  // 2. YouTube and no Twitch.
  const aston = rowFor(rows, YOUTUBE_ONLY);
  ok(`${where} — 2 YouTube, no Twitch`, aston !== null, 'Aston has no row at all');
  is(`${where} — 2 YouTube, no Twitch`, aston.twitch, null);
  is(`${where} — 2 YouTube, no Twitch`, aston.youtube, 'Glitch Aston');
  is(`${where} — 2 YouTube, no Twitch`, aston.youtube_id, 'UC7ydYSU1nZOHB7nVV-As_XA');
  is(`${where} — 2 an ended session is not live`, aston.live, null);

  // 3. Opted out AND linked — one row that says both.
  const lexxi = rowFor(rows, OPTED_AND_LINKED);
  ok(`${where} — 3 opted out and linked`, lexxi !== null, 'RockStarLexxi has no row at all');
  is(`${where} — 3 opted out and linked`, lexxi.opted_out, true);
  is(`${where} — 3 opted out and linked`, lexxi.twitch, 'rockstarlexxi');

  // 4. ⚠️ A ping role and NO link at all — they must still appear, or a role goes invisible.
  const prez = rowFor(rows, ROLE_NO_LINK);
  ok(`${where} — 4 a ping role and no link`, prez !== null, 'Prez has no row, so a whole ping role is invisible');
  is(`${where} — 4 a ping role and no link`, prez.twitch, null);
  is(`${where} — 4 a ping role and no link`, prez.youtube, null);
  is(`${where} — 4 a ping role and no link`, prez.role, 'Prez pings');
  is(`${where} — 4 the streamer list travels too`, prez.listed, false);

  // 5. An open session matching nobody linked — still on the page, named by the session.
  const stranger = rowFor(rows, STRANGER);
  ok(`${where} — 5 a session matching nobody`, stranger !== null, 'the stranger has no row');
  is(`${where} — 5 a session matching nobody`, stranger.name, 'Somebody Else');
  is(`${where} — 5 a session matching nobody`, stranger.live, 'twitch');
  is(`${where} — 5 a session matching nobody`, stranger.twitch, null);

  // 6. Two open sessions, one member, two platforms — ONE row, live from the non-presence one.
  const pawpette = rows.filter((one) => one.user_id === TWO_SESSIONS);
  is(`${where} — 6 two sessions, one row`, pawpette.length, 1);
  is(`${where} — 6 live comes from the session whose source is not presence`, pawpette[0].live, 'youtube');
  is(`${where} — 6 both links are on the one row`, pawpette[0].twitch, 'popnotarts');
  is(`${where} — 6 both links are on the one row`, pawpette[0].youtube, 'Pawpette');
}

// --- Live now: a card per open stream --------------------------------------------------------
{
  const where = 'live now';
  const cards = liveStreams(SESSIONS);
  is(`${where} — one card per open stream`, cards.length, 4);

  const stranger = cards.find((one) => one.user_id === STRANGER);
  is(`${where} — named by the session itself`, stranger.name, 'Somebody Else');
  is(`${where} — a shadow session is not announced`, stranger.announced, false);
  is(`${where} — nobody else's stream to hold it back`, stranger.held_by, null);

  const twitch = cards.find((one) => one.session_id === 10);
  const youtube = cards.find((one) => one.session_id === 9);
  is(`${where} — 6 announced for one`, twitch.announced, true);
  is(`${where} — 6 held back for the other`, youtube.announced, false);
  is(`${where} — 6 and it says which stream has it`, youtube.held_by, 'twitch');
  is(`${where} — 6 and the other way round`, twitch.held_by, 'youtube');
  same(`${where} — one platform each`, youtube.platforms, ['youtube']);
}

// --- co-streaming: the two nullable fields the `costream` build adds --------------------------
// Today they are absent and nothing may change; when they arrive the ONE session covers both.
{
  const where = 'co-streaming';

  const without = [{ id: 20, user_id: '700', user_name: 'Zee', source: 'twitch', url: 'https://twitch.tv/zvrra', game: 'Balatro', title: 'one more run', started_at: '2026-09-19T10:00:00Z', ended_at: null, mode: 'on', announced_message_id: '840' }];
  const before = liveStreams(without);
  same(`${where} — absent: one platform`, before[0].platforms, ['twitch']);
  is(`${where} — absent: no second address`, before[0].also_url, null);
  is(`${where} — absent: live is the one platform`, joinStreamers({ sessions: without })[0].live, 'twitch');

  const withBoth = [{ ...without[0], also_source: 'youtube', also_url: 'https://youtube.com/watch?v=zee' }];
  const after = liveStreams(withBoth);
  same(`${where} — present: both platforms on one card`, after[0].platforms, ['twitch', 'youtube']);
  is(`${where} — present: the second address travels`, after[0].also_url, 'https://youtube.com/watch?v=zee');
  is(`${where} — present: still one card, not two`, after.length, 1);
  is(`${where} — present: the row says both`, joinStreamers({ sessions: withBoth })[0].live, 'both');
  is(`${where} — present: it is still one row`, joinStreamers({ sessions: withBoth }).length, 1);
}

// --- Add a streamer: one box, two destinations, and a refusal in words ------------------------
{
  const where = 'add a streamer';
  same(`${where} — a bare Twitch name`, routeTyped('supernamu'), { where: 'twitch', value: 'supernamu' });
  same(`${where} — a Twitch address`, routeTyped('https://twitch.tv/supernamu'), { where: 'twitch', value: 'supernamu' });
  same(`${where} — a YouTube address`, routeTyped('https://youtube.com/channel/UC7ydYSU1nZOHB7nVV-As_XA'), {
    where: 'youtube', value: 'https://youtube.com/channel/UC7ydYSU1nZOHB7nVV-As_XA',
  });
  same(`${where} — a bare channel id`, routeTyped('UC7ydYSU1nZOHB7nVV-As_XA'), {
    where: 'youtube', value: 'UC7ydYSU1nZOHB7nVV-As_XA',
  });
  same(`${where} — an @handle`, routeTyped('@glitchaston'), { where: 'youtube', value: '@glitchaston' });

  const both = routeTyped('twitch.tv/supernamu youtube.com/@supernamu');
  is(`${where} — ⚠️ both at once is refused, never guessed`, both.where, null);
  has(`${where} — the refusal names Twitch`, both.why, 'twitch.tv/');
  has(`${where} — the refusal names YouTube`, both.why, 'youtube.com/channel/UC');

  const neither = routeTyped('kick.com/somebody');
  is(`${where} — something that is neither`, neither.where, null);
  has(`${where} — and says what both look like`, neither.why, 'youtube.com/channel/UC');
  is(`${where} — nothing typed`, routeTyped('').where, null);
  is(`${where} — nothing typed`, routeTyped(null).where, null);
}


// --- spotlight: a channel with no member behind it ---------------------------------------------
// docs/info/spotlight-design.md §C. GamesDoneQuick is kept for ever and live; the ESA row runs
// out with its marathon; `caseyfast` is ALSO a linked member's login, so it must be ONE row (the
// member's) carrying the spotlight facts; a row that has already expired is simply absent,
// because the sweep deletes it rather than hiding it.
const SPOTLIGHT = [
  {
    id: 1,
    twitch_login: 'gamesdonequick',
    display_name: 'GamesDoneQuick',
    note: "the owner's marathon channel",
    role_id: '900000000000000010',
    role: 'GamesDoneQuick pings',
    role_wearers: 3,
    added_at: '2026-01-01T00:00:00+00:00',
    expires_at: null,
    kept: true,
    until: 'kept',
    bump_hours: null,
    pin: true,
    event_id: null,
    url: 'https://www.twitch.tv/gamesdonequick',
    live: true,
    session: {
      id: 5,
      started_at: '2026-09-20T02:00:00+00:00',
      ended_at: null,
      title: 'AGDQ 2027 — Day 4',
      game: 'Celeste',
      url: 'https://www.twitch.tv/gamesdonequick',
      mode: 'on',
      bump_count: 2,
      announced_message_id: '830000000000000020',
    },
    sessions: [
      { id: 5, started_at: '2026-09-20T02:00:00+00:00', ended_at: null, title: 'AGDQ 2027 — Day 4', game: 'Celeste', url: 'https://www.twitch.tv/gamesdonequick', mode: 'on', bump_count: 2, announced_message_id: '830000000000000020' },
      { id: 4, started_at: '2026-06-01T02:00:00+00:00', ended_at: '2026-06-08T02:00:00+00:00', title: 'SGDQ 2026', game: 'Super Metroid', url: 'https://www.twitch.tv/gamesdonequick', mode: 'on', bump_count: 6, announced_message_id: '830000000000000019' },
    ],
  },
  {
    id: 2,
    twitch_login: 'esamarathon',
    display_name: 'ESA Marathon',
    note: null,
    role_id: null,
    role: null,
    role_wearers: null,
    added_at: '2026-09-01T00:00:00+00:00',
    expires_at: '2026-09-30T00:00:00+00:00',
    kept: false,
    until: 'until 30 Sep',
    bump_hours: 6,
    pin: true,
    event_id: 2,
    url: 'https://www.twitch.tv/esamarathon',
    live: false,
    session: null,
    sessions: [],
  },
  {
    id: 3,
    twitch_login: 'supernamu',
    display_name: 'supernamu',
    note: null,
    role_id: '900000000000000011',
    role: 'supernamu pings',
    role_wearers: 1,
    added_at: '2026-09-10T00:00:00+00:00',
    expires_at: null,
    kept: true,
    until: 'kept',
    bump_hours: null,
    pin: false,
    event_id: null,
    url: 'https://www.twitch.tv/supernamu',
    live: false,
    session: null,
    sessions: [],
  },
];

{
  const where = 'spotlight';
  const rows = joinStreamers({ links: LINKS, optouts: OPTOUTS, listing: LISTING, sessions: SESSIONS, spotlight: SPOTLIGHT });

  const gdq = rows.find((one) => one.twitch === 'gamesdonequick');
  ok(`${where} — a channel with no member is still a row`, Boolean(gdq), 'gamesdonequick has no row');
  is(`${where} — and it has no member id`, gdq.user_id, 'spotlight:1');
  is(`${where} — it reads kept`, gdq.spotlight.until, 'kept');
  is(`${where} — and it is live on Twitch`, gdq.live, 'twitch');

  is(`${where} — a channel's own ping role lands on its row`, gdq.role, 'GamesDoneQuick pings');
  is(`${where} — with the count that wears it`, gdq.role_wearers, 3);
  is(`${where} — and its id as a string`, gdq.role_id, '900000000000000010');

  const esa = rows.find((one) => one.twitch === 'esamarathon');
  is(`${where} — a dated row says the day it runs out`, esa.spotlight.until, 'until 30 Sep');
  is(`${where} — and it is not live`, esa.live, null);

  const shared = rows.filter((one) => one.twitch === 'supernamu');
  is(`${where} — a channel that is ALSO a member's login is ONE row`, shared.length, 1);
  is(`${where} — and it is the member's row`, shared[0].user_id, TWITCH_ONLY);
  is(`${where} — carrying the spotlight facts`, shared[0].spotlight.id, 3);
  is(`${where} — and the MEMBER's own ping role wins that row's cell`, shared[0].role, 'Namu pings');
  is(`${where} — a channel with no role of its own leaves the cell empty`, esa.role_id, null);

  ok(`${where} — an expired row is absent, because the sweep deletes it`,
    !rows.some((one) => one.twitch === 'frostfatales'), 'an expired row appeared');

  const plain = joinStreamers({ links: LINKS, optouts: OPTOUTS, listing: LISTING, sessions: SESSIONS });
  ok(`${where} — with no spotlight payload nothing changes`,
    plain.every((one) => one.spotlight === null), 'a row has a spotlight with no payload');

  const cards = spotlightCards(SPOTLIGHT);
  is(`${where} — only a live spotlight is a Live-now card`, cards.length, 1);
  is(`${where} — the card names the channel`, cards[0].name, 'GamesDoneQuick');
  is(`${where} — the card says it was announced`, cards[0].announced, true);
  is(`${where} — the card says it is pinned`, cards[0].pinned, true);
  same(`${where} — a spotlight is a Twitch card`, cards[0].platforms, ['twitch']);

  const past = spotlightSessions(SPOTLIGHT);
  is(`${where} — every spotlight session joins Recent streams`, past.length, 2);
  is(`${where} — with its own source`, past[0].source, 'spotlight');
  is(`${where} — named by the channel`, past[1].user_name, 'GamesDoneQuick');
}

// --- ⚠️ every settings key lands in exactly one drawer or one named surface -------------------
// The 49 keys the three namespaces held on 2026-09-20, measured with
//   python -c "from black_bloc import settings_store as s; print([k for k in s.KEY_TYPES if
//              s.namespace_of(k) in ('golive','pings','youtube')])"
// The catch-all is what keeps this satisfiable: a key added tomorrow appears in Everything
// else rather than vanishing from the page, and the last assertion below pins that.
const NAMESPACE_KEYS = [
  'golive_mode', 'golive_channel_id', 'golive_template', 'golive_live_author',
  'golive_end_template', 'golive_end_author', 'golive_end_keep_mention', 'golive_live_role_id',
  'golive_require_role_id', 'golive_ignore_role_id', 'golive_cooldown_minutes',
  'golive_ping_role_id', 'golive_max_session_hours', 'golive_embed', 'golive_boot_sweep',
  'golive_log_level',
  'golive_panel_minutes', 'golive_costream_mode', 'golive_costream_template',
  'golive_costream_author',
  'pings_mode', 'pings_events_role_name', 'pings_fan_role_creation', 'pings_fan_role_template',
  'pings_fan_role_on_unlink', 'pings_fan_role_delete', 'pings_streamer_stale_days',
  'pings_empty_role_days', 'pings_onboarding_managed', 'pings_onboarding_prompt_title',
  'pings_onboarding_option_cap', 'pings_log_level', 'pings_panel_minutes',
  'youtube_log_level', 'youtube_panel_minutes', 'youtube_unlink_dms_them', 'youtube_live_mode',
  'youtube_live_poll_minutes', 'youtube_live_end_misses',
  'spotlight_mode', 'spotlight_poll_minutes', 'spotlight_end_misses', 'spotlight_bump_hours',
  'spotlight_bump_template', 'spotlight_bump_cleanup', 'spotlight_bump_pings', 'spotlight_pin',
  'spotlight_default_days', 'spotlight_event_slack_hours',
];

{
  const where = 'every key lands once';
  is(`${where} — the namespaces held 49 keys when this was measured`, NAMESPACE_KEYS.length, 49);

  const specs = NAMESPACE_KEYS.map((key) => ({ key, type: 'text', value: null }));
  const placed = placeSettings(specs);
  const seen = new Map();
  const count = (key, home) => seen.set(key, (seen.get(key) || []).concat([home]));
  for (const spec of placed.strip) count(spec.key, STRIP_WHERE);
  for (const spec of placed.wording) count(spec.key, WORDING_WHERE);
  for (const drawer of placed.drawers) for (const spec of drawer.specs) count(spec.key, drawer.title);

  for (const key of NAMESPACE_KEYS) {
    const homes = seen.get(key) || [];
    if (homes.length !== 1) fail(where, `${key} lands in ${homes.length} places: ${homes.join(', ') || 'none'}`);
  }
  is(`${where} — nothing else was invented`, seen.size, NAMESPACE_KEYS.length);
  is(`${where} — and placeSettings agrees`, placed.placed.size, NAMESPACE_KEYS.length);

  same(`${where} — the strip holds the three modes`, sorted(placed.strip.map((one) => one.key)), sorted(STRIP_KEYS));
  same(`${where} — the announcement holds the wording`, sorted(placed.wording.map((one) => one.key)), sorted(WORDING_KEYS));

  const home = (id) => sorted(placed.drawers.find((one) => one.id === id).specs.map((one) => one.key));
  same(`${where} — who gets announced`, home('who'), sorted(DRAWERS[0].keys));
  same(`${where} — where it goes`, home('where'), sorted(DRAWERS[1].keys));
  same(`${where} — how streams are spotted`, home('spotted'), sorted(DRAWERS[3].keys));
  is(`${where} — ping roles holds every pings_* but the mode and the log level`, home('pings').length, 11);
  ok(`${where} — and pings_log_level is not one of them`, !home('pings').includes('pings_log_level'), 'pings_log_level is in the Ping roles drawer');
  same(`${where} — the catch-all holds what nobody claimed`, home('rest'), sorted([
    'golive_log_level', 'golive_panel_minutes', 'pings_log_level',
    'youtube_log_level', 'youtube_panel_minutes',
    'golive_costream_mode', 'golive_costream_template', 'golive_costream_author',
  ]));

  const tomorrow = placeSettings([{ key: 'golive_brand_new_thing', type: 'text', value: null }]);
  same(`${where} — a key added tomorrow lands in the catch-all, never nowhere`,
    tomorrow.drawers.find((one) => one.id === 'rest').specs.map((one) => one.key),
    ['golive_brand_new_thing']);
}

process.stdout.write('golive-join: the streamers join against its fixtures\n');
if (failures.length) {
  process.stdout.write(`golive-join: ${failures.length} problem(s)\n`);
  for (const said of failures) process.stdout.write(`  - ${said}\n`);
  process.exit(1);
}
process.stdout.write(
  'golive-join: ok - one row per person across five payloads; a ping role with no link still '
    + 'has a row; two open sessions are one row; a co-stream says both platforms; an ambiguous '
    + 'address is refused in words; a spotlighted channel with no member is its own row and one '
    + 'that IS a linked login is not a second; all 49 settings keys land in exactly one place\n',
);
