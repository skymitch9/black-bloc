/* The one place Twitch and YouTube meet: five payloads in, one row per person out.
   PURE — no DOM, no fetch — so site/mock/golive-join.test.mjs feeds it fixtures under plain
   node with no dependency. See docs/info/code-notes.md § site/public/assets/golive-join.js
   and docs/info/golive-page-design.md §B1. */

const PRESENCE = 'presence';
const TWITCH = 'twitch';
const YOUTUBE = 'youtube';
const BOTH = 'both';

const YT_ADDRESS = /youtube\.com|youtu\.be/i;
const YT_CHANNEL = /(?:^|[/=])UC[A-Za-z0-9_-]{22}(?![A-Za-z0-9_-])/;
const YT_HANDLE = /^@[A-Za-z0-9._-]{3,30}$/;
const TW_ADDRESS = /twitch\.tv/i;
const TW_IN_ADDRESS = /twitch\.tv\/([A-Za-z0-9_]{3,25})/i;
const TW_LOGIN = /^[A-Za-z0-9][A-Za-z0-9_]{2,24}$/;

const NOTHING_TYPED = 'Nothing was typed, so nothing was linked. Put the name from '
  + 'twitch.tv/… for a Twitch channel, or the address that starts with youtube.com/channel/UC… '
  + '(or their @handle) for a YouTube one.';
const BOTH_AT_ONCE = ' names a Twitch channel and a YouTube channel at once, so nothing was '
  + 'linked rather than guessing which you meant. Put one of them: the name from twitch.tv/…, '
  + 'or the address that starts with youtube.com/channel/UC… (or their @handle).';
const NEITHER = ' is not a Twitch name and not a YouTube channel, so nothing was linked. A '
  + 'Twitch name is the word in twitch.tv/…; a YouTube channel is the address that starts with '
  + 'youtube.com/channel/UC…, or their @handle.';

export function idOf(value) {
  return value === null || value === undefined || value === '' ? null : String(value);
}

function platformOf(source) {
  return String(source || '').toLowerCase() === YOUTUBE ? YOUTUBE : TWITCH;
}

export function openSessions(sessions) {
  return (sessions || []).filter((row) => row && !row.ended_at);
}

export function platformsOf(session) {
  const found = [platformOf(session.source)];
  if (session.also_source) {
    const other = platformOf(session.also_source);
    if (!found.includes(other)) found.push(other);
  }
  return found;
}

export function liveStreams(sessions) {
  const open = openSessions(sessions);
  const mine = new Map();
  for (const row of open) {
    const id = idOf(row.user_id);
    if (id === null) continue;
    const found = mine.get(id) || [];
    for (const one of platformsOf(row)) if (!found.includes(one)) found.push(one);
    mine.set(id, found);
  }
  return open.map((row) => {
    const platforms = platformsOf(row);
    const theirs = mine.get(idOf(row.user_id)) || platforms;
    const elsewhere = theirs.filter((one) => !platforms.includes(one));
    return {
      session_id: row.id === undefined ? null : row.id,
      user_id: idOf(row.user_id),
      name: row.user_name || null,
      platforms,
      title: row.title || null,
      game: row.game || null,
      url: row.url || null,
      also_url: row.also_url || null,
      announced: Boolean(row.announced_message_id),
      mode: row.mode || null,
      started_at: row.started_at || null,
      held_by: elsewhere.length ? elsewhere[0] : null,
    };
  });
}

function liveByUser(sessions) {
  const found = new Map();
  for (const row of openSessions(sessions)) {
    const id = idOf(row.user_id);
    if (id === null) continue;
    const mine = found.get(id) || { live: null, presence: true, co: false };
    const presence = String(row.source || '').toLowerCase() === PRESENCE;
    const co = platformsOf(row).length > 1;
    if (co) {
      mine.live = BOTH;
      mine.co = true;
    } else if (!mine.co && (mine.live === null || (mine.presence && !presence))) {
      mine.live = platformOf(row.source);
      mine.presence = presence;
    }
    found.set(id, mine);
  }
  const live = new Map();
  for (const [id, mine] of found) live.set(id, mine.live);
  return live;
}

function blankRow(id) {
  return {
    user_id: id,
    name: null,
    twitch: null,
    twitch_at: null,
    youtube: null,
    youtube_id: null,
    youtube_at: null,
    role: null,
    role_id: null,
    role_wearers: null,
    opted_out: false,
    live: null,
    listed: null,
    last_live_at: null,
    live_count: null,
  };
}

function byName(a, b) {
  const one = String(a.name || a.user_id).toLowerCase();
  const two = String(b.name || b.user_id).toLowerCase();
  if (one !== two) return one < two ? -1 : 1;
  return String(a.user_id) < String(b.user_id) ? -1 : 1;
}

export function joinStreamers({
  links = [],
  youtubeLinks = [],
  optouts = [],
  listing = [],
  streamers = [],
  sessions = [],
} = {}) {
  const rows = new Map();
  const reach = (value, name) => {
    const id = idOf(value);
    if (id === null) return null;
    let row = rows.get(id);
    if (!row) {
      row = blankRow(id);
      rows.set(id, row);
    }
    if (!row.name && name) row.name = String(name);
    return row;
  };

  for (const one of listing || []) {
    const row = reach(one.member_id, one.member);
    if (!row) continue;
    row.listed = one.listed === true;
    row.last_live_at = one.last_live_at || null;
    row.live_count = one.live_count === undefined ? null : one.live_count;
    if (one.role_id) {
      row.role_id = idOf(one.role_id);
      row.role = one.role || null;
      row.role_wearers = one.followers === undefined ? null : one.followers;
    }
  }
  for (const one of streamers || []) {
    const row = reach(one.member_id, one.member);
    if (!row) continue;
    row.role_id = idOf(one.role_id);
    row.role = one.role || null;
    row.role_wearers = one.followers === undefined ? null : one.followers;
  }
  for (const one of links || []) {
    const row = reach(one.user_id, one.user_name);
    if (!row) continue;
    row.twitch = one.twitch_login || null;
    row.twitch_at = one.linked_at || null;
  }
  for (const one of youtubeLinks || []) {
    const row = reach(one.user_id, one.user_name);
    if (!row) continue;
    row.youtube = one.title || one.handle || one.channel_id || null;
    row.youtube_id = one.channel_id || null;
    row.youtube_at = one.linked_at || null;
  }
  for (const one of optouts || []) {
    const row = reach(one.user_id, one.user_name);
    if (!row) continue;
    row.opted_out = true;
  }
  for (const one of openSessions(sessions)) reach(one.user_id, one.user_name);

  const live = liveByUser(sessions);
  for (const [id, row] of rows) row.live = live.get(id) || null;
  return [...rows.values()].sort(byName);
}

export function routeTyped(given) {
  const value = String(given === null || given === undefined ? '' : given).trim();
  if (!value) return { where: null, why: NOTHING_TYPED };
  const youtube = YT_ADDRESS.test(value) || YT_CHANNEL.test(value) || YT_HANDLE.test(value);
  const twitch = TW_ADDRESS.test(value);
  if (youtube && twitch) return { where: null, why: `**${value}**${BOTH_AT_ONCE}` };
  if (youtube) return { where: YOUTUBE, value };
  if (twitch) {
    const found = TW_IN_ADDRESS.exec(value);
    if (found) return { where: TWITCH, value: found[1] };
    return { where: null, why: `**${value}**${NEITHER}` };
  }
  if (TW_LOGIN.test(value)) return { where: TWITCH, value };
  return { where: null, why: `**${value}**${NEITHER}` };
}

export const STRIP_KEYS = ['golive_mode', 'youtube_live_mode', 'pings_mode'];

export const WORDING_KEYS = [
  'golive_template',
  'golive_end_mode',
  'golive_end_suffix',
  'golive_end_template',
  'golive_end_author',
  'golive_end_keep_mention',
];

export const DRAWERS = [
  {
    id: 'who',
    title: 'Who gets announced',
    keys: [
      'golive_require_role_id',
      'golive_ignore_role_id',
      'golive_cooldown_minutes',
      'golive_live_role_id',
      'golive_max_session_hours',
    ],
  },
  {
    id: 'where',
    title: 'Where it goes',
    keys: ['golive_channel_id', 'golive_ping_role_id', 'golive_embed'],
  },
  {
    id: 'pings',
    title: 'Ping roles',
    holds: (key) => key.startsWith('pings_') && key !== 'pings_log_level',
  },
  {
    id: 'spotted',
    title: 'How streams are spotted',
    keys: ['youtube_live_poll_minutes', 'youtube_live_end_misses', 'youtube_unlink_dms_them'],
  },
  { id: 'rest', title: 'Everything else' },
];

export const STRIP_WHERE = 'the header strip';
export const WORDING_WHERE = 'the announcement';

export function placeSettings(specs) {
  const drawers = DRAWERS.map((one) => ({ id: one.id, title: one.title, specs: [] }));
  const catchAll = drawers[drawers.length - 1];
  const strip = [];
  const wording = [];
  const placed = new Map();
  for (const spec of specs || []) {
    const key = spec && spec.key ? String(spec.key) : null;
    if (key === null || placed.has(key)) continue;
    if (STRIP_KEYS.includes(key)) {
      strip.push(spec);
      placed.set(key, STRIP_WHERE);
      continue;
    }
    if (WORDING_KEYS.includes(key)) {
      wording.push(spec);
      placed.set(key, WORDING_WHERE);
      continue;
    }
    const at = DRAWERS.findIndex(
      (one) => (one.keys ? one.keys.includes(key) : Boolean(one.holds && one.holds(key))),
    );
    const found = at < 0 ? catchAll : drawers[at];
    found.specs.push(spec);
    placed.set(key, found.title);
  }
  return { drawers, strip, wording, placed };
}
