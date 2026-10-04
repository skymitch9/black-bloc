const REFRESH_DEFAULT = 30;
const REFRESH_MIN = 10;
const REFRESH_MAX = 300;

export const FLASH_NEW = 'new';
export const FLASH_LIVE = 'live';
export const FLASH_DONE = 'done';
export const FLASH_MOVED = 'moved';

export function refreshMs(seconds) {
  const given = Number(seconds);
  const kept = Number.isFinite(given) && given > 0 ? given : REFRESH_DEFAULT;
  return Math.min(REFRESH_MAX, Math.max(REFRESH_MIN, Math.round(kept))) * 1000;
}

export function signature(...parts) {
  return JSON.stringify(parts);
}

export function changesOf(before, after) {
  const found = {};
  if (!before || !after || String(before.marathon?.id) !== String(after.marathon?.id)) return found;
  const was = new Map((before.rows || []).map((one) => [String(one.id), one]));
  for (const row of after.rows || []) {
    const old = was.get(String(row.id));
    if (!old) found[row.id] = FLASH_NEW;
    else if (old.state !== row.state && row.state === 'live') found[row.id] = FLASH_LIVE;
    else if (old.state !== row.state && row.state === 'done') found[row.id] = FLASH_DONE;
    else if (old.state !== row.state || old.start_at !== row.start_at) found[row.id] = FLASH_MOVED;
  }
  return found;
}

export function secondsWords(ms) {
  const seconds = Math.max(0, Math.round(Number(ms || 0) / 1000));
  if (seconds < 5) return 'just now';
  if (seconds < 90) return `${seconds} seconds ago`;
  const minutes = Math.round(seconds / 60);
  return `${minutes} minutes ago`;
}

export function placed(current, wanted) {
  const kept = new Set(wanted);
  const gone = current.filter((node) => !kept.has(node));
  const now = current.filter((node) => kept.has(node));
  const steps = [];
  wanted.forEach((node, at) => {
    if (now[at] === node) return;
    const from = now.indexOf(node);
    if (from !== -1) now.splice(from, 1);
    now.splice(at, 0, node);
    steps.push({ node, before: now[at + 1] || null });
  });
  return { steps, gone };
}
