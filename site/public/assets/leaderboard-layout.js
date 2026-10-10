import { fill } from './bracket-layout.js';

export { fill };

export const PAGE_SIZE = 25;
export const ORDERS = ['points', 'xp'];

/** One page of a board, the page number kept inside 1..pages. */
export function pageOf(rows, page, size = PAGE_SIZE) {
  const list = rows || [];
  const pages = Math.max(1, Math.ceil(list.length / size));
  const at = Math.min(Math.max(1, Math.floor(Number(page) || 1)), pages);
  return { rows: list.slice((at - 1) * size, at * size), page: at, pages };
}

/** The page of a board a member's row is on, or 1 when they are not on it. */
export function pageWith(rows, userId, size = PAGE_SIZE) {
  const at = (rows || []).findIndex((row) => row.user_id === String(userId));
  return at < 0 ? 1 : Math.floor(at / size) + 1;
}

/** The viewer's own row when it is NOT among the rows shown, so it can be pinned under them. */
export function pinned(shown, all, userId) {
  if (!userId) return null;
  const wanted = String(userId);
  if ((shown || []).some((row) => row.user_id === wanted)) return null;
  return (all || []).find((row) => row.user_id === wanted) || null;
}

/** One game per line; blanks dropped, spaces squeezed, repeats (any capitals) kept once. */
export function gamesOf(text) {
  const seen = new Set();
  const found = [];
  for (const line of String(text || '').split(/\r?\n/)) {
    const game = line.replace(/\s+/g, ' ').trim();
    if (!game || seen.has(game.toLowerCase())) continue;
    seen.add(game.toLowerCase());
    found.push(game);
  }
  return found;
}

export function runLine(run) {
  return [run.game, run.category, run.time].filter(Boolean).join(' · ');
}

export function ticketHref(guildId, placeId) {
  return guildId && placeId ? `https://discord.com/channels/${guildId}/${placeId}` : null;
}

const pad = (value) => String(value).padStart(2, '0');

function partsIn(ms, zone) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: zone,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(new Date(ms));
  const get = (type) => Number(parts.find((part) => part.type === type).value);
  return { year: get('year'), month: get('month'), day: get('day'), hour: get('hour') % 24, minute: get('minute'), second: get('second') };
}

function offsetAt(ms, zone) {
  const p = partsIn(ms, zone);
  return Math.round((Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - ms) / 60000);
}

/** `YYYY-MM-DD HH:MM` on the wall clock of `zone` as an ISO instant with its offset; null when unreadable. */
export function zonedIso(wall, zone) {
  const found = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})$/.exec(String(wall || '').trim());
  if (!found) return null;
  const [, year, month, day, hour, minute] = found;
  const naive = Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute));
  try {
    const first = offsetAt(naive, zone);
    const offset = offsetAt(naive - first * 60000, zone);
    const sign = offset < 0 ? '-' : '+';
    const size = Math.abs(offset);
    return `${year}-${month}-${day}T${hour}:${minute}:00${sign}${pad(Math.floor(size / 60))}:${pad(size % 60)}`;
  } catch (error) {
    return null;
  }
}

/** An instant as `YYYY-MM-DD HH:MM` on the wall clock of `zone`; '' when there is none. */
export function wallIn(iso, zone) {
  const ms = Date.parse(iso || '');
  if (Number.isNaN(ms)) return '';
  try {
    const p = partsIn(ms, zone);
    return `${p.year}-${pad(p.month)}-${pad(p.day)} ${pad(p.hour)}:${pad(p.minute)}`;
  } catch (error) {
    return '';
  }
}

/** live · upcoming · ended · idle (an event bounty whose event has no window yet). */
export function bountyStatus(bounty, nowIso = new Date().toISOString()) {
  if (!bounty.active) return 'ended';
  if (bounty.live) return 'live';
  const at = Date.parse(nowIso);
  const ends = Date.parse(bounty.ends_at || '');
  const starts = Date.parse(bounty.starts_at || '');
  if (!Number.isNaN(ends) && ends <= at) return 'ended';
  if (!Number.isNaN(starts) && starts > at) return 'upcoming';
  return 'idle';
}

const STATUS_ORDER = { live: 0, upcoming: 1, idle: 2, ended: 3 };

export function sortedBounties(bounties, nowIso = new Date().toISOString()) {
  return (bounties || [])
    .map((bounty) => ({ bounty, status: bountyStatus(bounty, nowIso) }))
    .sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]
      || String(a.bounty.starts_at || '').localeCompare(String(b.bounty.starts_at || ''))
      || b.bounty.id - a.bounty.id);
}

/** The amount box's bounds per bonus kind, the move's own limits (points_moves.bounty_values). */
export function amountRules(kind) {
  return kind === 'multiplier'
    ? { min: '1.01', max: '10', step: '0.01', value: '2' }
    : { min: '1', max: '100000', step: '1', value: '10' };
}
