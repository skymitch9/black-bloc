const COOKIE = 'bb_tz';
const PICKED = 'pick:';
const KEEP_SECONDS = 400 * 86400;
const MOMENT = /\{\{(at|day):([^}]+)\}\}/g;

export function validZone(zone) {
  if (typeof zone !== 'string' || !zone.trim()) return false;
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: zone });
    return true;
  } catch (error) {
    return false;
  }
}

export function deviceZone() {
  try {
    const found = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return validZone(found) ? found : null;
  } catch (error) {
    return null;
  }
}

export function cookieZone(cookieText) {
  for (const part of String(cookieText || '').split(';')) {
    const [key, ...rest] = part.trim().split('=');
    if (key !== COOKIE) continue;
    let value = '';
    try {
      value = decodeURIComponent(rest.join('='));
    } catch (error) {
      return null;
    }
    const picked = value.startsWith(PICKED);
    const zone = picked ? value.slice(PICKED.length) : value;
    return validZone(zone) ? { zone, picked } : null;
  }
  return null;
}

export function zoneChoice(cookieText, device, fallback) {
  const kept = cookieZone(cookieText);
  if (kept && kept.picked) return { zone: kept.zone, picked: true, from: 'picked' };
  if (validZone(device)) return { zone: device, picked: false, from: 'device' };
  if (kept) return { zone: kept.zone, picked: false, from: 'remembered' };
  return { zone: validZone(fallback) ? fallback : 'UTC', picked: false, from: 'server' };
}

export function cookieLine(zone, picked) {
  return `${COOKIE}=${encodeURIComponent(`${picked ? PICKED : ''}${zone}`)}; Path=/; Max-Age=${KEEP_SECONDS}; SameSite=Lax`;
}

export function viewerZone(fallback) {
  const choice = zoneChoice(document.cookie, deviceZone(), fallback);
  if (choice.from !== 'server') document.cookie = cookieLine(choice.zone, choice.picked);
  return choice;
}

export function pickZone(zone) {
  if (validZone(zone)) document.cookie = cookieLine(zone, true);
  else document.cookie = `${COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

function partsOf(iso, zone, options) {
  const at = new Date(iso || '');
  if (Number.isNaN(at.getTime())) return null;
  const parts = {};
  const format = new Intl.DateTimeFormat('en-US', { timeZone: validZone(zone) ? zone : undefined, ...options });
  for (const one of format.formatToParts(at)) parts[one.type] = one.value;
  return parts;
}

export function clockParts(iso, zone) {
  const parts = partsOf(iso, zone, { hour: 'numeric', minute: '2-digit', hour12: true });
  if (!parts) return null;
  return { time: `${Number(parts.hour)}:${parts.minute}`, period: String(parts.dayPeriod || '').toUpperCase() };
}

export function clockTime(iso, zone) {
  const found = clockParts(iso, zone);
  return found ? `${found.time} ${found.period}` : '—';
}

export function dayLabel(iso, zone) {
  const parts = partsOf(iso, zone, { weekday: 'short', day: 'numeric', month: 'short' });
  return parts ? `${parts.weekday} ${Number(parts.day)} ${parts.month}` : '—';
}

export function fillMoments(text, zone) {
  return String(text ?? '').replace(MOMENT, (whole, kind, iso) => (kind === 'day' ? dayLabel(iso, zone) : clockTime(iso, zone)));
}
