/* The Events page's marathon words and lines. PURE — no DOM, no fetch — so
   site/mock/marathon-words.test.mjs proves them under plain node.
   See docs/info/code-notes.md § site/public/assets/marathon-words.js. */

export const BAF = 'BaF';

export const CARD_SCHEDULE = 'Schedule';
export const CARD_PEOPLE = 'People';
export const CARD_EVENT = 'Event';
export const CARD_CHANNEL = 'The channel';
export const CARD_POSTS = 'Posts';
export const DRAWER_CARDS = [CARD_SCHEDULE, CARD_PEOPLE, CARD_EVENT, CARD_CHANNEL, CARD_POSTS];

const LAST_READ = 'Last read {ago}';
const NOT_READ = 'Not read yet';
const NEXT_READ = 'next read {in}';
const NEXT_READ_NOW = 'next read any minute now';
const CADENCE = 'every {near} min while it is near, every {far} h when it is far';
const PAUSED_READ = 'paused — not read until it is resumed';
const TROUBLE = 'Could not be read since {when} — {reason}; read again {in}';
const TROUBLE_PAUSED = 'Could not be read since {when} — {reason}; paused, so not read again until it is resumed';
const NO_RUNS_YET = 'No runs yet — nothing published.';
const CELL_READ = 'read {ago}';
const CELL_NOT_READ = 'not read yet';
const CELL_PAUSED = 'paused';
const CELL_UNPUBLISHED = 'not published — again {in}';
const CELL_TROUBLE = 'could not be read — again {in}';
const FEED_EVERY = 'every {hours} h';
const FEED_LAST = 'last {ago}';
const FEED_NEXT = 'next {in}';
const FEED_NEVER = 'not checked yet';
const FEED_PAUSED = 'paused';
const FEED_TROUBLE = 'Could not be checked since {when} — {reason}; checked again {in}';
const SOURCES_TITLE = 'Where marathons come from · {count} source{s}';
const SOURCES_NEXT = 'next check {in}';
const SOURCES_OFF = 'checks are off';
const BOARD_UP = 'Board: up in';
const BOARD_UP_PINNED = 'Board: up and pinned in';
const BOARD_NONE = 'Board: none yet.';
const SENT_LINE = 'Reminders: {reminders} sent · Shoutouts: {shouts}';
const FEED_MARK = ' · feed';
const DAY_TITLE = '{day} · {slots} slot{s} · {baf} ' + BAF;

export function said(text, values) {
  let out = String(text);
  for (const [key, value] of Object.entries(values)) out = out.replaceAll(`{${key}}`, String(value));
  return out;
}

function stamp(iso) {
  const at = new Date(iso || '');
  return Number.isNaN(at.getTime()) ? null : at.getTime();
}

export function span(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  if (total < 60) return 'under a minute';
  const minutes = Math.round(total / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return minutes % 60 ? `${hours} h ${minutes % 60} min` : `${hours} h`;
  const days = Math.floor(hours / 24);
  return hours % 24 ? `${days} d ${hours % 24} h` : `${days} d`;
}

export function agoWords(iso, now = Date.now()) {
  const at = stamp(iso);
  if (at === null) return '—';
  const seconds = (now - at) / 1000;
  return seconds < 60 ? 'just now' : `${span(seconds)} ago`;
}

export function inWords(iso, now = Date.now()) {
  const at = stamp(iso);
  if (at === null) return null;
  const seconds = (at - now) / 1000;
  return seconds < 60 ? 'any minute now' : `in ${span(seconds)}`;
}

export function whenWords(iso) {
  const at = stamp(iso);
  if (at === null) return '—';
  return new Date(at).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

/** The Schedule card's reading line: `{ text, tone }`, tone `warn` when the last read failed. */
export function readingLine(row, cadence = {}, now = Date.now()) {
  const next = inWords(row.next_read_at, now);
  if (row.last_fetch_ok === false) {
    const values = { when: whenWords(row.last_fetched_at), reason: row.last_error || 'no reason given', in: next || 'soon' };
    return { text: said(row.active === false ? TROUBLE_PAUSED : TROUBLE, values), tone: 'warn' };
  }
  const bits = [row.last_fetched_at ? said(LAST_READ, { ago: agoWords(row.last_fetched_at, now) }) : NOT_READ];
  if (row.active === false) {
    bits.push(PAUSED_READ);
    return { text: bits.join(' · '), tone: null };
  }
  if (next) bits.push(next === 'any minute now' ? NEXT_READ_NOW : said(NEXT_READ, { in: next }));
  if (cadence.near || row.poll_minutes) {
    bits.push(said(CADENCE, { near: row.poll_minutes || cadence.near, far: cadence.far ?? '—' }));
  }
  return { text: bits.join(' · '), tone: null };
}

/** The table's short Schedule cell; the full reason is in the drawer. */
export function scheduleCell(row, now = Date.now()) {
  if (row.active === false) return CELL_PAUSED;
  const next = inWords(row.next_read_at, now) || 'soon';
  if (row.last_fetch_ok === false) return said(CELL_TROUBLE, { in: next });
  if (!row.last_fetched_at) return CELL_NOT_READ;
  if (!Number(row.runs)) return said(CELL_UNPUBLISHED, { in: next });
  return said(CELL_READ, { ago: agoWords(row.last_fetched_at, now) });
}

export function countsLine(runList) {
  const runs = (runList || []).filter((one) => one.state !== 'dropped');
  if (!runs.length) return NO_RUNS_YET;
  const bits = [`${runs.length} run${runs.length === 1 ? '' : 's'}`, `${runs.filter((one) => one.ours).length} ${BAF}`];
  const done = runs.filter((one) => one.state === 'done').length;
  const live = runs.filter((one) => one.state === 'live').length;
  if (done) bits.push(`${done} done`);
  if (live) bits.push(`${live} on now`);
  return bits.join(' · ');
}

export function feedNextAt(feed) {
  const last = stamp(feed.last_checked_at);
  if (last === null || !feed.active) return null;
  return new Date(last + Number(feed.hours || 0) * 3600000).toISOString();
}

/** A feed row's reading: `{ text, tone }` in the same shape as a marathon's. */
export function feedReading(feed, now = Date.now()) {
  const next = inWords(feedNextAt(feed), now);
  if (feed.last_ok === false) {
    const values = { when: whenWords(feed.last_checked_at), reason: feed.last_error || 'no reason given', in: next || 'soon' };
    return { text: said(FEED_TROUBLE, values), tone: 'warn' };
  }
  const bits = [said(FEED_EVERY, { hours: feed.hours })];
  bits.push(feed.last_checked_at ? said(FEED_LAST, { ago: agoWords(feed.last_checked_at, now) }) : FEED_NEVER);
  if (!feed.active) bits.push(FEED_PAUSED);
  else if (next) bits.push(said(FEED_NEXT, { in: next }));
  return { text: bits.join(' · '), tone: null };
}

export function sourcesTitle(feeds, { enabled = true } = {}, now = Date.now()) {
  const rows = feeds || [];
  const head = said(SOURCES_TITLE, { count: rows.length, s: rows.length === 1 ? '' : 's' });
  if (enabled === false) return `${head} · ${SOURCES_OFF}`;
  const soonest = rows.map(feedNextAt).filter(Boolean).sort()[0];
  return soonest ? `${head} · ${said(SOURCES_NEXT, { in: inWords(soonest, now) })}` : head;
}

/** `{ board, sent }`: the board words (the channel is drawn beside them) and the sent counts. */
export function postsLines(row) {
  const runs = row.run_list || [];
  const reminders = runs.reduce((total, one) => total + (Array.isArray(one.reminders_sent) ? one.reminders_sent.length : 0), 0);
  const shouts = runs.filter((one) => one.shouted).length;
  const board = row.board_message_id ? (row.board_pinned ? BOARD_UP_PINNED : BOARD_UP) : BOARD_NONE;
  return { board, hasBoard: Boolean(row.board_message_id), sent: said(SENT_LINE, { reminders, shouts }) };
}

/** The drawer's card titles, in order; the moves bar (Pause / Remove) follows the last. */
export function drawerCards() {
  return [...DRAWER_CARDS];
}

/** The marathon table's Source cell: the source words, and `· feed` when a feed made the row. */
export function sourceCell(row) {
  return `${row.source_word || row.source || '—'}${row.feed_id ? FEED_MARK : ''}`;
}

function zoned(iso, timeZone) {
  const at = stamp(iso);
  if (at === null) return null;
  const parts = {};
  const format = new Intl.DateTimeFormat('en-GB', {
    timeZone: timeZone || undefined,
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  });
  for (const one of format.formatToParts(new Date(at))) parts[one.type] = one.value;
  const months = { Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06', Jul: '07', Aug: '08', Sep: '09', Sept: '09', Oct: '10', Nov: '11', Dec: '12' };
  return {
    key: `${parts.year}-${months[parts.month] || '00'}-${String(parts.day).padStart(2, '0')}`,
    day: `${parts.weekday} ${Number(parts.day)} ${parts.month === 'Sept' ? 'Sep' : parts.month}`,
    time: `${parts.hour}:${parts.minute}`,
  };
}

/** `15:15` in the guild's zone. */
export function slotTime(iso, timeZone) {
  const found = zoned(iso, timeZone);
  return found ? found.time : '—';
}

/** How long a run is booked for, as `0:43`. */
export function runLength(run) {
  const start = stamp(run.scheduled_at);
  const end = stamp(run.ends_at);
  if (start === null || end === null || end < start) return '';
  const minutes = Math.round((end - start) / 60000);
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
}

/** A BaF person's run as a short chip: `Sun 12 Jan 15:15 Super Metroid`. */
export function runChip(run, timeZone) {
  const found = zoned(run.scheduled_at, timeZone);
  return found ? `${found.day} ${found.time} ${run.game}` : String(run.game || '');
}

/**
 * The schedule by day in the guild's zone: `[{ key, label, runs, baf, today, past, open }]`.
 * A slot is one run, so a race shares its row. Today is open, a past day shut, a future day
 * shut unless it holds a BaF run.
 */
export function daysOf(runList, timeZone, now = Date.now()) {
  const today = zoned(new Date(now).toISOString(), timeZone).key;
  const days = new Map();
  const runs = (runList || [])
    .filter((one) => one.state !== 'dropped' && stamp(one.scheduled_at) !== null)
    .sort((a, b) => stamp(a.scheduled_at) - stamp(b.scheduled_at) || (a.order_no || 0) - (b.order_no || 0));
  for (const run of runs) {
    const found = zoned(run.scheduled_at, timeZone);
    if (!days.has(found.key)) days.set(found.key, { key: found.key, label: found.day, runs: [] });
    days.get(found.key).runs.push(run);
  }
  return [...days.values()].map((day) => {
    const baf = day.runs.filter((one) => one.ours).length;
    const isToday = day.key === today;
    const past = day.key < today;
    return { ...day, baf, today: isToday, past, open: isToday || (!past && baf > 0) };
  });
}

export function dayTitle(day) {
  const slots = day.runs.length;
  return said(DAY_TITLE, { day: day.label, slots, s: slots === 1 ? '' : 's', baf: day.baf });
}

/** The People answer's entry a person on a run belongs to. */
export function entryFor(board, runId, person) {
  const all = [...((board && board.baf) || []), ...((board && board.others) || [])];
  return all.find((entry) => (entry.runs || []).some((one) => String(one.id) === String(runId)
    && one.name === person.name && one.part === person.part)) || null;
}

/** Runner chips first, then hosts and commentators, each once. */
export function slotPeople(run) {
  const people = run.people || [];
  return [...people.filter((one) => one.part === 'runner'), ...people.filter((one) => one.part !== 'runner')];
}

/** The schedule filter: names, Twitch logins and games. */
export function slotMatches(run, query) {
  const wanted = String(query || '').trim().toLowerCase();
  if (!wanted) return true;
  const words = [run.game, run.category, ...(run.people || []).flatMap((one) => [one.name, one.login, one.member_name])];
  return words.some((one) => String(one || '').toLowerCase().includes(wanted));
}
