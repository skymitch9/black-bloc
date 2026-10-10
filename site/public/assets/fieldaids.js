const TOKEN = /\{([a-z][a-z0-9_]*)\}/g;

export const NEAR = 0.8;

export function tokensIn(...texts) {
  const found = [];
  for (const text of texts) {
    for (const hit of String(text ?? '').matchAll(TOKEN)) {
      if (!found.includes(hit[0])) found.push(hit[0]);
    }
  }
  return found;
}

export function placeholdersFor(spec) {
  if (!spec) return [];
  const own = tokensIn(spec.default, spec.value);
  return own.length ? tokensIn(spec.default, spec.value, spec.help) : [];
}

export function insertAt(value, start, end, text) {
  const old = String(value ?? '');
  const from = Math.max(0, Math.min(Number.isInteger(start) ? start : old.length, old.length));
  const to = Math.max(from, Math.min(Number.isInteger(end) ? end : from, old.length));
  const at = from + text.length;
  return { value: old.slice(0, from) + text + old.slice(to), start: at, end: at };
}

export function counterState(length, max, near = NEAR) {
  const shown = max > 0 && length >= Math.ceil(max * near);
  const tone = length > max ? 'danger' : length >= max ? 'warn' : null;
  return { shown, tone, text: `${length} / ${max}`, left: max - length };
}

export function capState(count, cap) {
  return { full: count >= cap, text: `${count} of ${cap}` };
}

/** A one-line text key whose value or default has a line break needs a box that keeps it. */
export function keepsLines(spec) {
  return [spec && spec.value, spec && spec.default].some((one) => typeof one === 'string' && /\r|\n/.test(one));
}
