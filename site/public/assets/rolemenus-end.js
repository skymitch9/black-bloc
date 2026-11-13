// Role menus page: the pure half of a menu's end, so node tests can hold it without a browser.

export const BY_MARATHON = 'marathon';
export const BY_DATE = 'date';
export const NO_END = 'none';
export const END_FIELDS = ['ends_source', 'ends_marathon_id', 'ends_at', 'buffer_days'];

export const DRAWER_HEAD = 'Roles ending with this marathon:';
export const ENDS_WITH = 'ends with';
export const WEARING = 'wearing';
export const UNKNOWN_COUNT = '?';

const SECTION_HASH = /^sect-/;

/** `rolemenus.html#<menu name>` opens that menu; a `#sect-…` hash is a section, not a menu. */
export function menuFromHash(hash) {
  const raw = String(hash || '').replace(/^#/, '');
  if (!raw || SECTION_HASH.test(raw)) return null;
  try {
    return decodeURIComponent(raw);
  } catch (error) {
    return null;
  }
}

export function menuHash(name) {
  return `#${encodeURIComponent(String(name))}`;
}

/** Title, description and roles only: a words save must never carry an end field. */
export function wordsBody(fields) {
  const body = {};
  for (const key of ['name', 'title', 'description', 'options']) {
    if (fields[key] !== undefined) body[key] = fields[key];
  }
  return body;
}

function trimmed(value) {
  return value === null || value === undefined ? '' : String(value).trim();
}

/**
 * The PUT body for what the End card holds, or null when it would change nothing — any end write
 * clears `ended_at` and re-arms a menu, so an untouched card must send no end field at all.
 */
export function endBody(menu, picked) {
  const current = menu.ends_source || NO_END;
  if (picked.how === NO_END) return current === NO_END ? null : { ends_source: NO_END };
  if (picked.how === BY_DATE) {
    const day = trimmed(picked.date);
    if (!day) return null;
    const time = trimmed(picked.time);
    return { ends_source: BY_DATE, ends_at: time ? `${day} ${time}` : day };
  }
  if (picked.how !== BY_MARATHON) return null;
  const marathon = trimmed(picked.marathonId);
  if (!marathon) return null;
  const buffer = trimmed(picked.buffer);
  const kept = menu.buffer_days === null || menu.buffer_days === undefined ? '' : String(menu.buffer_days);
  if (current === BY_MARATHON && String(menu.ends_marathon_id) === marathon && buffer === kept) return null;
  return { ends_source: BY_MARATHON, ends_marathon_id: marathon, buffer_days: buffer === '' ? null : buffer };
}

/** What a typed date resolves to before it is saved: 23:59 in the server's zone unless a time is given. */
export function resolvedMoment(date, time, zone) {
  const day = trimmed(date);
  if (!day) return '';
  return `${day} ${trimmed(time) || '23:59'}${zone ? ` · ${zone}` : ''}`;
}

export function countOf(value) {
  return value === null || value === undefined ? UNKNOWN_COUNT : String(value);
}

/** One menu's state line: its end in the API's own words, and who wears its roles. */
export function endLine(menu) {
  if ((menu.ends_source || NO_END) === NO_END) return menu.end_label || '';
  return `${menu.end_label} · ${countOf(menu.wearing)} ${WEARING}`;
}

/** A staff-editable sentence, filled the way the bot fills it; the shipped words if it is broken. */
export function filled(template, fallback, values, fill) {
  const said = fill(template, values);
  return said === null ? fill(fallback, values) : said;
}

/** End it now's answer in words: the ended sentence, then one line per member still wearing a role. */
export function resultLines(found) {
  const lines = [];
  if (found && found.message) lines.push(String(found.message));
  for (const line of (found && found.pass && found.pass.left) || []) lines.push(String(line));
  return lines;
}

/** The marathon drawer's one line: each menu that ends with it, with its counts. */
export function drawerItems(menus) {
  return (menus || []).map((menu) => ({
    name: menu.name,
    text: `${menu.name} (${menu.roles} roles · ${countOf(menu.wearing)} people)`,
  }));
}

/** A grant that ends with its menu says so; Push it back is the menu's move, not the grant's. */
export function grantEndsWithMenu(row) {
  return Boolean(row && row.open && row.ends_with_menu);
}
