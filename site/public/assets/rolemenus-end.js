// Timed roles page: the pure half (an event's end, the list, the fill), so node tests can hold it.

export const BY_MARATHON = 'marathon';
export const BY_DATE = 'date';
export const NO_END = 'none';
export const END_FIELDS = ['ends_source', 'ends_marathon_id', 'ends_at', 'buffer_days'];

export const DRAWER_HEAD = 'Timed roles end with this marathon:';
export const UNKNOWN_COUNT = '?';
export const GIVE = 'give';
export const TAKE = 'take';

const SECTION_HASH = /^sect-/;

/** `rolemenus.html#<event name>` opens that event; a `#sect-…` hash is a section, not an event. */
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

function trimmed(value) {
  return value === null || value === undefined ? '' : String(value).trim();
}

/**
 * The PUT body for what the End card holds, or null when it would change nothing — any end write
 * clears `ended_at` and re-arms an event, so an untouched card must send no end field at all.
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

/** The marathon drawer's one line: each open event that ends with it, by its name, with its people. */
export function drawerItems(events) {
  return (events || []).map((event) => ({
    name: event.name,
    text: `${event.title || event.name} (${countOf(event.assigned)} people)`,
  }));
}

/** A grant that ends with its event says so; Push it back is the event's move, not the grant's. */
export function grantEndsWithMenu(row) {
  return Boolean(row && row.open && row.ends_with_menu);
}

/** Open events first (the API's order), the ended ones apart. */
export function splitEvents(events) {
  const open = [];
  const ended = [];
  for (const event of events || []) (event.open === false ? ended : open).push(event);
  return { open, ended };
}

/** The roles an event has people on; a zero is no fact and is not drawn. */
export function heldRoles(event) {
  return ((event && event.assigned_by_role) || []).filter((one) => Number(one.count) > 0);
}

/** Marathons an event may follow: none another open event already follows (one event each). */
export function freeMarathons(marathons, eventName = null) {
  return (marathons || []).filter((one) => !one.event || (eventName !== null && one.event === eventName));
}

/** Roles the ad-hoc grant form and the list's Add offer: never one already on the timed list. */
export function notTimed(roles, timed) {
  const listed = new Set((timed || []).map((one) => String(one.role_id)));
  return (roles || []).filter((role) => !listed.has(String(role.id)));
}

/** What Check the list sends: the pasted lines as typed and the ticked members by id. */
export function previewBody({ roleId, text, ticked, mode }) {
  return {
    role_id: String(roleId || ''),
    lines: String(text || ''),
    user_ids: [...new Set((ticked || []).map((one) => String(one.id)))],
    remove: mode === TAKE,
  };
}

/** What the save sends: exactly the people the preview said it would change, nobody else. */
export function saveBody(preview) {
  return {
    role_id: String(preview.role_id),
    user_ids: [...(preview.to_save || [])],
    remove: Boolean(preview.remove),
  };
}

/** The key a preview row's note reads from; null when the save will change that person. */
export const NOTE_KEYS = {
  already: 'rolemenu_list_already_note',
  not_assigned: 'rolemenu_list_not_assigned_note',
  ambiguous: 'rolemenu_list_ambiguous_note',
  unknown: 'rolemenu_list_unknown_note',
};

export function noteKey(reason) {
  return NOTE_KEYS[reason] || null;
}

/** One Fill line: which key says it, and with what. */
export function fillLine(line) {
  if (!line.role_id) return { key: 'rolemenu_fill_no_role_line', values: { part: line.part_label, setting: line.setting } };
  if (!line.timed) return { key: 'rolemenu_site_fill_not_timed_line', values: { part: line.part_label, role: line.role_name } };
  return {
    key: 'rolemenu_site_fill_line',
    values: { part: line.part_label, matched: line.matched, missing: line.missing, role: line.role_name },
  };
}

/** The unmatched names of one Fill line, with the count past the ones shown. */
export function fillUnmatched(line) {
  if (!line.unmatched_count) return null;
  const more = line.unmatched_count - (line.unmatched || []).length;
  return {
    key: 'rolemenu_fill_unmatched_line',
    values: {
      part: line.part_label,
      count: line.unmatched_count,
      names: (line.unmatched || []).join(', ') + (more > 0 ? ` +${more}` : ''),
    },
  };
}
