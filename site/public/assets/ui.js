import {
  Outage,
  api,
  clearSetting,
  nameRecord,
  refChannels,
  refMembers,
  refRoles,
  saveSetting,
  send,
  settings,
  settingsNamespace,
} from './api.js';
import { messageTree, mountTree } from './discordmock.js';
import { ICONS } from './icons.js';
import { channelLabel, humanLabel } from './labels.js';

export { channelLabel, humanLabel };

const OUTAGE_WRITE = 'Black Bloc did not answer, so nothing was changed. That is an outage, not a ' +
  'permission problem — try again in a minute.';

export function sentenceFor(error) {
  if (error instanceof Outage) return { text: OUTAGE_WRITE, tone: 'danger' };
  return { text: error.message, tone: error.isPermission ? 'warn' : 'danger' };
}

export function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = String(value);
    else if (key === 'on') {
      for (const [type, fn] of Object.entries(value)) node.addEventListener(type, fn);
    } else if (key === 'set') {
      Object.assign(node, value);
    } else if (key === 'style') {
      for (const rule of String(value).split(';')) {
        const at = rule.indexOf(':');
        if (at > 0) node.style.setProperty(rule.slice(0, at).trim(), rule.slice(at + 1).trim());
      }
    } else {
      node.setAttribute(key, value === true ? '' : String(value));
    }
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child);
  }
  return node;
}

export function icon(name, size = 16, className = 'chev') {
  const spec = ICONS[name];
  if (!spec) return el('span');
  const holder = document.createElement('div');
  holder.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" ` +
    `stroke="currentColor" stroke-width="${spec.width}" stroke-linecap="round" ` +
    `stroke-linejoin="round" aria-hidden="true" class="${className}">${spec.body}</svg>`;
  return holder.firstElementChild;
}

export function when(iso) {
  if (!iso) return '—';
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? String(iso) : at.toLocaleString();
}

/**
 * The mock's short stamp: the clock for something that happened today,
 * "Yesterday" for the day before, the date for anything older. The full
 * timestamp travels as the title so nothing is lost by shortening it.
 */
export function shortWhen(iso) {
  const at = new Date(iso);
  if (!iso || Number.isNaN(at.getTime())) return { text: '—', title: '' };
  const day = new Date(at.getFullYear(), at.getMonth(), at.getDate());
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((today - day) / 86400000);
  let text;
  if (days === 0) text = at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  else if (days === 1) text = 'Yesterday';
  else text = at.toLocaleDateString([], { month: 'short', day: 'numeric' });
  return { text, title: at.toLocaleString() };
}

/**
 * Whole days between now and a stamp, as a number so the caller decides the
 * wording. Null when there is no readable stamp — never a guessed zero.
 */
export function daysBetween(iso) {
  if (!iso) return null;
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return null;
  return Math.round((at.getTime() - Date.now()) / 86400000);
}

/** "in 2 days" / "today" / "3 days ago", with the full stamp as the title. */
export function untilWhen(iso) {
  const days = daysBetween(iso);
  if (days === null) return { text: '—', title: '' };
  const title = new Date(iso).toLocaleString();
  if (days === 0) return { text: 'today', title, days };
  if (days > 0) return { text: `in ${days} day${days === 1 ? '' : 's'}`, title, days };
  const gone = Math.abs(days);
  return { text: `${gone} day${gone === 1 ? '' : 's'} ago`, title, days };
}

/** How long ago, in the coarsest unit that still says something useful. */
export function ago(iso) {
  const at = new Date(iso);
  if (!iso || Number.isNaN(at.getTime())) return { text: '—', title: '' };
  const title = at.toLocaleString();
  const seconds = Math.max(0, Math.round((Date.now() - at.getTime()) / 1000));
  if (seconds < 60) return { text: 'just now', title };
  const said = duration(seconds);
  return { text: `${said} ago`, title };
}

export function duration(seconds) {
  if (seconds === null || seconds === undefined || seconds === '') return 'not known';
  const total = Number(seconds);
  if (!Number.isFinite(total)) return String(seconds);
  const d = Math.floor(total / 86400);
  const h = Math.floor((total % 86400) / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = Math.floor(total % 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m`;
  return `${s}s`;
}

/**
 * An empty state is one sentence and, wherever there is one, one thing to do
 * about it — never a blank box. `action` is a node, so a caller can hand it a
 * button that opens the section that fills this list or a link to the page
 * that does.
 */
export function sayNothing(text, action = null) {
  return el('p', { class: 'say-nothing' }, [
    el('span', { class: 'say-nothing-text', text }),
    action || null,
  ]);
}

export function textAction(label, onClick) {
  return el('button', {
    class: 'say-nothing-do',
    type: 'button',
    text: label,
    on: { click: onClick },
  });
}

export function linkAction(label, href) {
  return el('a', { class: 'say-nothing-do', href, text: label });
}

export function slugOf(text) {
  const made = String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return made || 'section';
}

const DEBOUNCE_MS = 200;

export function searchBox({ label = 'Search', placeholder = 'type to filter', onQuery = null, value = '' } = {}) {
  const input = el('input', {
    class: 'input search',
    type: 'search',
    placeholder,
    autocomplete: 'off',
    'aria-label': label,
    value: value || undefined,
  });
  let timer = null;
  const fire = () => {
    if (onQuery) onQuery(input.value.trim().toLowerCase());
  };
  input.addEventListener('input', () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(fire, DEBOUNCE_MS);
  });
  input.addEventListener('search', () => {
    if (timer) clearTimeout(timer);
    fire();
  });
  return input;
}

/** The mock's search control: a magnifier and a borderless input in one box. */
export function searchField(options = {}) {
  const input = searchBox(options);
  return el('div', { class: 'searchfield' }, [icon('search', 14, 'search-mark'), input]);
}

/** Empties the box a searchField wraps and re-runs its filter. */
export function clearSearch(wrapper) {
  const input = wrapper.querySelector('input');
  if (!input) return;
  input.value = '';
  input.dispatchEvent(new Event('search'));
}

export function filterRows(root, query) {
  let shown = 0;
  let total = 0;
  for (const body of root.querySelectorAll('tbody')) {
    for (const line of body.children) {
      total += 1;
      const hit = query === '' || line.textContent.toLowerCase().includes(query);
      line.hidden = !hit;
      if (hit) shown += 1;
    }
  }
  return { shown, total };
}

/**
 * A search box over a box of cards rather than over table rows — the automod
 * rule book and the twelve months of birthdays are both piles of cards, and
 * one filter over the pile beats a box on each card in it. The "nothing
 * matches" line is put inside `root` so it lands under the cards it is about.
 */
export function searchOver(root, {
  label = 'Search',
  placeholder = 'type to filter',
  selector = '.card',
  noun = 'card(s)',
  empty = 'Nothing here matches what you typed.',
} = {}) {
  const said = el('span', { class: 'table-count' });
  const none = sayNothing(empty, textAction('Clear the search', () => clearSearch(input)));
  none.hidden = true;
  root.append(none);
  const paint = (query) => {
    let shown = 0;
    let total = 0;
    for (const node of root.querySelectorAll(selector)) {
      total += 1;
      const hit = query === '' || node.textContent.toLowerCase().includes(query);
      node.hidden = !hit;
      if (hit) shown += 1;
    }
    said.textContent = query === '' ? `${total} ${noun}` : `${shown} of ${total}`;
    none.hidden = shown > 0;
  };
  const input = searchField({ label, placeholder, onQuery: paint });
  paint('');
  return el('div', { class: 'table-tools' }, [input, said]);
}

export function section(title, note, { count = null, id = null, open = false } = {}) {
  const body = el('div', { class: 'section-body' });
  const slug = id || slugOf(title);
  const countNode = el('span', { class: 'sect-count', hidden: true });
  const heading = el('h2', { class: 'sect-title' }, [
    icon('chevronDown', 14, 'sect-mark'),
    el('span', { class: 'sect-name', text: title }),
    countNode,
  ]);
  const details = el('details', { class: 'card sect-card' }, [
    el('summary', { class: 'sect-summary' }, [heading]),
    el('div', { class: 'sect-inner' }, [
      note ? el('p', { class: 'section-note', text: note }) : null,
      body,
    ]),
  ]);
  const node = el('section', {
    class: 'sect',
    id: `sect-${slug}`,
    'data-sect': slug,
    'data-title': title,
    'data-open': open ? '1' : undefined,
  }, [details]);

  const setCount = (value) => {
    if (value === null || value === undefined) {
      countNode.hidden = true;
      node.removeAttribute('data-count');
      return;
    }
    countNode.textContent = String(value);
    countNode.hidden = false;
    node.setAttribute('data-count', String(value));
  };
  setCount(count);

  return { node, body, details, slug, title, count: setCount };
}

export function card(title, children, { actions = null, count = null, flush = false } = {}) {
  const head = title || actions || count !== null
    ? el('div', { class: 'card-head' }, [
      title ? el('h3', { text: title }) : null,
      count === null || count === undefined ? null : el('span', { class: 'card-count', text: String(count) }),
      actions ? el('div', { class: 'bar card-bar' }, actions) : null,
    ])
    : null;
  return el('div', { class: 'card' }, [
    head,
    el('div', { class: flush ? 'card-body flush' : 'card-body' }, children),
  ]);
}

/**
 * A shut-by-default block inside a section, for the part of a list nobody
 * needs open. It is deliberately NOT a nested `section()`: those are what the
 * "On this page" rail is built from, and a fold inside one is not a place.
 */
export function foldout(title, children, { count = null, open = false } = {}) {
  return el('details', { class: 'foldout', open: open || undefined }, [
    el('summary', { class: 'foldout-head' }, [
      icon('chevronDown', 14, 'sect-mark'),
      el('span', { text: title }),
      count === null || count === undefined
        ? null
        : el('span', { class: 'sect-count', text: String(count) }),
    ]),
    el('div', { class: 'foldout-body' }, children),
  ]);
}

export function bar(children, { sticky = false } = {}) {
  return el('div', { class: sticky ? 'bar card-bar' : 'bar' }, children);
}

export function button(label, onClick, { tone = null, small = true, disabled = false } = {}) {
  const classes = ['btn'];
  if (small) classes.push('small');
  if (tone === 'quiet') classes.push('quiet');
  if (tone === 'danger') classes.push('danger');
  if (tone === 'warn') classes.push('warn');
  return el('button', {
    class: classes.join(' '),
    type: 'button',
    text: label,
    disabled: disabled || undefined,
    on: { click: onClick },
  });
}

const BOLD = /\*\*([^*]+)\*\*/g;

/**
 * The house style writes ids and names as `**#31**`, which every outcome
 * sentence used to print with its asterisks. Text nodes and `el` only - the
 * sentence carries names and reasons people typed, so it never goes near
 * innerHTML.
 */
export function boldParts(text) {
  const said = String(text ?? '');
  const parts = [];
  let at = 0;
  for (const found of said.matchAll(BOLD)) {
    if (found.index > at) parts.push(document.createTextNode(said.slice(at, found.index)));
    parts.push(el('strong', { text: found[1] }));
    at = found.index + found[0].length;
  }
  if (at < said.length) parts.push(document.createTextNode(said.slice(at)));
  return parts;
}

export function notice(text = '', tone = null) {
  const node = el('p', { class: 'notice' });
  const say = (message, messageTone = null) => {
    const said = message || '';
    node.replaceChildren(...boldParts(said));
    node.said = said;
    node.hidden = !said;
    if (messageTone) node.setAttribute('data-tone', messageTone);
    else node.removeAttribute('data-tone');
  };
  say(text, tone);
  node.say = say;
  return node;
}

/** The circle a member wears: their picture, or their initial when it will not load. */
export function avatar(name, url = null) {
  const letter = String(name || '?').trim().charAt(0).toUpperCase() || '?';
  const initial = el('span', { class: 'avatar', 'aria-hidden': 'true', text: letter });
  if (!url) return initial;
  const holder = el('span', { class: 'avatar' });
  holder.append(el('img', {
    src: url,
    alt: '',
    loading: 'lazy',
    width: '28',
    height: '28',
    on: { error: () => holder.replaceWith(initial) },
  }));
  return holder;
}

/** Discord hands a colour out as an int; 0 means "no colour" and must not be black. */
export function hexColour(value) {
  if (typeof value === 'string') return /^#[0-9a-fA-F]{6}$/.test(value) ? value : null;
  if (!Number.isInteger(value) || value <= 0) return null;
  return `#${value.toString(16).padStart(6, '0')}`;
}

/**
 * A role as a chip. The colour travels as the `--role` custom property so
 * site.css keeps its no-raw-colour promise, and `note` is the clock a timed
 * grant puts beside the name.
 */
export function roleChip(name, { color = null, note = null, title = null } = {}) {
  const tint = hexColour(color);
  return el('span', {
    class: 'role-chip',
    style: tint ? `--role: ${tint}` : undefined,
    title: title || String(name || ''),
  }, [
    el('span', { class: 'role-chip-name', text: String(name || '') }),
    note ? el('span', { class: 'role-chip-note', text: `· ${note}` }) : null,
  ]);
}

export function modeChip(mode) {
  const value = mode === null || mode === undefined || mode === '' ? 'not set' : String(mode);
  return el('span', { class: 'mode-chip', 'data-mode': value, text: value });
}

export function badge(text, tone = null) {
  return el('span', { class: 'badge', 'data-tone': tone || undefined, text: String(text) });
}

export function nameNode(id, given = null) {
  if (id === null || id === undefined || id === '') return el('span', { class: 'muted', text: '—' });
  const key = String(id);
  const record = nameRecord(key);
  const label = given || record?.display_name || record?.name || null;
  if (label) {
    return el('span', { class: 'name', title: `Discord id ${key}`, text: label });
  }
  const title = record && record.looked_up
    ? `Discord id ${key} — nothing in the server carries this id any more, so it is shown as the id.`
    : `Discord id ${key} — the name could not be looked up just now, so it is shown as the id.`;
  return el('span', { class: 'name', 'data-unresolved': 'true', title, text: key });
}

export function looksLikeId(value) {
  return typeof value === 'string' && /^\d{15,22}$/.test(value);
}

export function valueNode(value) {
  if (value === null || value === undefined || value === '') return el('span', { class: 'muted', text: 'not set' });
  if (Array.isArray(value)) {
    if (value.length === 0) return el('span', { class: 'muted', text: 'empty' });
    const parts = [];
    value.forEach((item, at) => {
      if (at > 0) parts.push(', ');
      parts.push(looksLikeId(String(item)) ? nameNode(String(item)) : String(item));
    });
    return el('span', {}, parts);
  }
  if (looksLikeId(String(value))) return nameNode(String(value));
  if (typeof value === 'object') {
    try {
      return el('span', { class: 'mono', text: JSON.stringify(value) });
    } catch (e) {
      return el('span', { text: String(value) });
    }
  }
  return el('span', { text: String(value) });
}

export function idsIn(rows, keys) {
  const found = [];
  for (const row of rows || []) {
    for (const key of keys) {
      const value = row?.[key];
      if (Array.isArray(value)) found.push(...value);
      else if (value !== null && value !== undefined && value !== '') found.push(value);
    }
  }
  return found;
}

const SEARCH_FROM = 2;
const LONG_FROM = 12;

/** A header that needs explaining says so with a mark, the way Cloudflare's does. */
function headCell(column) {
  const th = el('th', { scope: 'col', title: column.help || undefined }, [
    el('span', { text: column.label }),
  ]);
  if (column.help) th.append(el('span', { class: 'th-mark', 'aria-hidden': 'true', text: 'ⓘ' }));
  return th;
}

/**
 * "Showing 1–25 of 120 lines" under the table, and what the search left when a
 * search is narrowing it. `from` is the 1-based index of this page's first row,
 * so a server-paged table counts across pages instead of restarting at 1.
 */
function footText(shown, rows, foot) {
  const noun = foot.noun || 'row';
  const said = (n) => `${noun}${n === 1 ? '' : 's'}`;
  const total = typeof foot.total === 'number' ? foot.total : rows.length;
  const from = typeof foot.from === 'number' && foot.from > 0 ? foot.from : 1;
  if (shown !== rows.length) return `Showing ${shown} of the ${rows.length} ${said(rows.length)} on this page`;
  if (rows.length === 0) return `Showing none of ${total} ${said(total)}`;
  return `Showing ${from}–${from + rows.length - 1} of ${total} ${said(total)}`;
}

export function table(columns, rows, {
  empty = 'Nothing here yet.',
  emptyAction = null,
  search = 'auto',
  searchLabel = 'Search this table',
  tools = [],
  foot = null,
} = {}) {
  if (!rows || rows.length === 0) return sayNothing(empty, emptyAction);
  const head = el('tr', {}, columns.map(headCell));
  const body = rows.map((row, index) => el('tr', {}, columns.map((column) => {
    const made = column.cell ? column.cell(row, index) : row[column.key];
    const cell = el('td', { class: column.className || undefined, 'data-label': column.label || '' });
    if (made === null || made === undefined || made === '') cell.textContent = '—';
    else if (made instanceof Node) cell.append(made);
    else cell.textContent = String(made);
    return cell;
  })));
  const scroll = el('div', {
    class: 'table-scroll',
    'data-long': rows.length > LONG_FROM ? 'true' : undefined,
  }, [
    el('table', { class: 'log-table' }, [
      el('thead', {}, [head]),
      el('tbody', {}, body),
    ]),
  ]);

  const wanted = search === true || (search === 'auto' && rows.length >= SEARCH_FROM);
  const extras = [].concat(tools).filter(Boolean);
  if (!wanted && extras.length === 0 && foot === null) return scroll;

  const counted = foot ? el('div', { class: 'table-foot', text: footText(rows.length, rows, foot) }) : null;
  // One home for the count: the foot owns it when there is one, and the
  // toolbar keeps it only when there is not.
  const shown = counted ? null : el('span', { class: 'table-count', text: `${rows.length} row(s)` });
  const none = sayNothing(
    'Nothing in this table matches what you typed.',
    textAction('Clear the search', () => clearSearch(input)),
  );
  none.hidden = true;
  const input = wanted ? searchField({
    label: searchLabel,
    placeholder: 'filter these rows',
    onQuery: (query) => {
      const found = filterRows(scroll, query);
      if (shown) shown.textContent = query === '' ? `${found.total} row(s)` : `${found.shown} of ${found.total}`;
      if (counted) counted.textContent = footText(found.shown, rows, foot);
      none.hidden = found.shown > 0;
      scroll.hidden = found.shown === 0;
    },
  }) : null;
  const bar = input || extras.length || shown
    ? el('div', { class: 'table-tools' }, [input, ...extras, el('span', { class: 'table-gap' }), shown])
    : null;
  return el('div', { class: 'table-block' }, [bar, scroll, counted, none]);
}

const PAGER_GAP = 8;

/**
 * The element that actually scrolls this pager's page. The shell puts
 * `overflow: hidden` on `body` and `overflow-y: auto` on `.content`, so
 * `document.scrollingElement` never moves — walking up for a real scroller is
 * what makes this work on every page rather than only where the window scrolls.
 */
function scrollerOf(node) {
  let found = node.parentElement;
  while (found && found !== document.documentElement) {
    const how = getComputedStyle(found).overflowY;
    if ((how === 'auto' || how === 'scroll') && found.scrollHeight > found.clientHeight) {
      return found;
    }
    found = found.parentElement;
  }
  return document.scrollingElement || document.documentElement;
}

/**
 * How far down the scroller the list this pager belongs to starts. The top bar
 * is a SIBLING of the scroller rather than an overlay on top of it, so nothing
 * covers y=0 inside `.content` and no bar height has to be subtracted here.
 */
function offsetIn(scroller, block) {
  const root = document.scrollingElement || document.documentElement;
  const base = scroller === root ? 0 : scroller.getBoundingClientRect().top;
  return scroller.scrollTop + block.getBoundingClientRect().top - base;
}

function listTop(node) {
  const block = node.closest('.sect, .card, .table-block') || node.parentElement;
  const scroller = scrollerOf(node);
  return { scroller, block, at: offsetIn(scroller, block) };
}

const PAINT_BACKSTOP_MS = 60;

/**
 * Two frames let the rebuilt rows lay out — but `requestAnimationFrame` does
 * not run at all in a tab that is not on screen, so a timer races it and
 * whichever arrives first wins.
 */
function painted() {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      resolve();
    };
    requestAnimationFrame(() => requestAnimationFrame(finish));
    setTimeout(finish, PAINT_BACKSTOP_MS);
  });
}

function place(scroller, at) {
  scroller.scrollTop = Math.max(0, at - PAGER_GAP);
}

/**
 * UNCONDITIONAL, and after the new rows are in the document. Replacing `#dash`
 * resets the scroller to 0 before this runs, so the old "already at the top,
 * leave it alone" test always fired and every page landed at the top of the
 * PAGE rather than the top of the list. Placed twice on purpose: once the
 * moment `onPage` resolves, which is all a hidden tab will ever get, and again
 * once the rows have laid out, which is what makes the landing exact. The move
 * is instant rather than smooth because a smooth scroll is an animation, and an
 * animation does not run in a tab that is not on screen either.
 */
async function backToTop({ scroller, block, at }) {
  place(scroller, at);
  await painted();
  place(scroller, block.isConnected ? offsetIn(scroller, block) : at);
}

export function pager({ page, hasMore, onPage, count = null }) {
  const at = Number(page) || 1;
  if (at <= 1 && !hasMore && count === 0) return document.createDocumentFragment();
  const node = el('div', { class: 'pager' });
  const go = async (to) => {
    const where = listTop(node);
    await onPage(to);
    await backToTop(where);
  };
  node.append(
    button('Previous', () => go(at - 1), { tone: 'quiet', disabled: at <= 1 }),
    el('span', { class: 'pager-at', text: count === null ? `Page ${at}` : `Page ${at} · ${count} shown` }),
    button('Next', () => go(at + 1), { tone: 'quiet', disabled: !hasMore }),
  );
  return node;
}

let drawerNode = null;
let drawerShut = null;

export function closeDrawer() {
  if (drawerNode && drawerNode.open) drawerNode.close();
}

/**
 * The right-hand detail panel a row opens instead of the page growing a
 * section under it. A native <dialog> in modal state, so Escape, the focus
 * trap and the backdrop are the platform's job and not this file's.
 */
export function openDrawer(title, body, { onClose = null } = {}) {
  if (drawerNode === null) {
    drawerNode = el('dialog', { class: 'drawer' });
    drawerNode.addEventListener('click', (event) => {
      if (event.target === drawerNode) closeDrawer();
    });
    document.body.append(drawerNode);
  }
  drawerNode.replaceChildren(el('div', { class: 'drawer-inner' }, [
    el('div', { class: 'drawer-head' }, [
      el('h2', { class: 'drawer-title', text: title }),
      button('Close', () => closeDrawer(), { tone: 'quiet' }),
    ]),
    el('div', { class: 'drawer-body' }, [].concat(body).filter(Boolean)),
  ]));
  if (drawerShut) drawerNode.removeEventListener('close', drawerShut);
  drawerShut = onClose || null;
  if (drawerShut) drawerNode.addEventListener('close', drawerShut);
  if (!drawerNode.open) drawerNode.showModal();
  return drawerNode;
}

let dialog = null;

export function ask({ title, body, confirmLabel = 'Do it', tone = 'danger' }) {
  if (dialog === null) {
    dialog = el('dialog', { class: 'ask' });
    document.body.append(dialog);
  }
  return new Promise((resolve) => {
    const finish = (answer) => {
      if (dialog.open) dialog.close();
      resolve(answer);
    };
    const heading = el('h2', { text: title });
    const lines = [].concat(body).map((line) =>
      (line instanceof Node ? line : el('p', { class: 'ask-body', text: String(line) })));
    dialog.replaceChildren(el('div', { class: 'ask-inner' }, [
      heading,
      ...lines,
      bar([
        button(confirmLabel, () => finish(true), { tone, small: false }),
        button('Cancel', () => finish(false), { tone: 'quiet', small: false }),
      ]),
    ]));
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      finish(false);
    }, { once: true });
    dialog.showModal();
  });
}

let formDialog = null;
const WORKING = 'Working…';

/**
 * ask()'s dialog for a form that must survive a refusal. `onConfirm` returns
 * null to close and resolve true, or a sentence to show INSIDE and stay open
 * with every field as it was typed; a throw becomes that sentence. `ready`
 * hands the caller the confirm button, so a body can grey it while what is
 * typed cannot be sent.
 */
export function askForm({
  title, body, confirmLabel = 'Do it', tone = 'danger', onConfirm = null, ready = null,
}) {
  if (formDialog === null) {
    formDialog = el('dialog', { class: 'ask' });
    document.body.append(formDialog);
  }
  return new Promise((resolve) => {
    const finish = (answer) => {
      if (formDialog.open) formDialog.close();
      resolve(answer);
    };
    const said = notice();
    const confirm = button(confirmLabel, async () => {
      confirm.disabled = true;
      said.say(WORKING);
      let refusal = null;
      try {
        refusal = onConfirm ? await onConfirm() : null;
      } catch (error) {
        refusal = sentenceFor(error).text;
      }
      confirm.disabled = false;
      if (refusal === null || refusal === undefined) {
        finish(true);
        return;
      }
      said.say(String(refusal), 'danger');
    }, { tone, small: false });
    const lines = [].concat(body).filter(Boolean).map((line) =>
      (line instanceof Node ? line : el('p', { class: 'ask-body', text: String(line) })));
    formDialog.replaceChildren(el('div', { class: 'ask-inner' }, [
      el('h2', { text: title }),
      ...lines,
      said,
      bar([confirm, button('Cancel', () => finish(false), { tone: 'quiet', small: false })]),
    ]));
    formDialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      finish(false);
    }, { once: true });
    formDialog.showModal();
    if (ready) ready({ confirm, say: said });
  });
}

/**
 * The control is tagged by name so the CSS can place it in the middle row of
 * the field's grid. Placing it as "the child that is not a label or help"
 * would silently mis-place anything a caller adds to a field later.
 */
export function field(label, control, help = null) {
  const id = control && control.id ? control.id : null;
  if (control && control.classList) control.classList.add('field-control');
  return el('div', { class: 'field' }, [
    el('label', { class: 'field-label', for: id || undefined, text: label }),
    control,
    help ? el('p', { class: 'field-help', text: help }) : null,
  ]);
}

function optionNode(value, label, selected) {
  return el('option', { value: String(value), text: label, selected: selected || undefined });
}

export async function channelSelect(value, { multiple = false, id = null } = {}) {
  const channels = await refChannels();
  const chosen = new Set((multiple ? value || [] : [value]).filter(Boolean).map(String));
  const select = el('select', {
    class: 'input',
    id: id || undefined,
    multiple: multiple || undefined,
    size: multiple ? Math.min(8, Math.max(3, channels.length)) : undefined,
  });
  if (!multiple) select.append(optionNode('', 'not set', chosen.size === 0));
  for (const channel of channels) {
    select.append(
      optionNode(channel.id, channelLabel(channel, channels), chosen.has(String(channel.id))),
    );
  }
  keepUnlisted(select, chosen, channels, 'a channel the server no longer has');
  return select;
}

export async function roleSelect(value, { multiple = false, id = null } = {}) {
  const roles = await refRoles();
  const chosen = new Set((multiple ? value || [] : [value]).filter(Boolean).map(String));
  const select = el('select', {
    class: 'input',
    id: id || undefined,
    multiple: multiple || undefined,
    size: multiple ? Math.min(8, Math.max(3, roles.length)) : undefined,
  });
  if (!multiple) select.append(optionNode('', 'not set', chosen.size === 0));
  for (const role of roles) {
    select.append(optionNode(role.id, `@${role.name}`, chosen.has(String(role.id))));
  }
  keepUnlisted(select, chosen, roles, 'a role the server no longer has');
  return select;
}

/** A stored id the list cannot show still reads back as itself, so a save elsewhere never clears it. */
function keepUnlisted(select, chosen, listed, said) {
  const known = new Set(listed.map((one) => String(one.id)));
  for (const id of chosen) {
    if (!known.has(id)) select.append(optionNode(id, `${said} · ${id}`, true));
  }
}

export function readSelect(select, multiple) {
  if (multiple) return [...select.selectedOptions].map((option) => option.value).filter(Boolean);
  return select.value === '' ? null : select.value;
}

export function memberPicker({ label = 'Member', onPick = null } = {}) {
  const chosen = { id: null, name: null };
  const search = el('input', {
    class: 'input',
    type: 'search',
    placeholder: 'type part of a name',
    autocomplete: 'off',
  });
  const results = el('ul', { class: 'picker-results', hidden: true });
  const picked = el('p', { class: 'picker-picked', hidden: true });
  const status = notice();

  const choose = (member) => {
    chosen.id = member ? String(member.id) : null;
    chosen.name = member ? member.display_name || member.name : null;
    picked.textContent = member ? `${chosen.name} · id ${chosen.id}` : '';
    picked.hidden = !member;
    results.replaceChildren();
    results.hidden = true;
    search.value = member ? chosen.name : '';
    if (onPick) onPick(member ? { id: chosen.id, name: chosen.name } : null);
  };

  let timer = null;
  search.addEventListener('input', () => {
    if (timer) clearTimeout(timer);
    const query = search.value.trim();
    if (query.length < 2) {
      results.replaceChildren();
      results.hidden = true;
      return;
    }
    timer = setTimeout(async () => {
      try {
        const found = await refMembers(query);
        status.say('');
        results.replaceChildren(...found.map((member) => el('li', {}, [
          button(`${member.display_name || member.name} · ${member.id}`, () => choose(member), { tone: 'quiet' }),
        ])));
        results.hidden = found.length === 0;
        if (found.length === 0) status.say('Nobody in the server matches that.', 'warn');
      } catch (error) {
        results.hidden = true;
        status.say(error.message, 'danger');
      }
    }, 250);
  });

  const node = el('div', { class: 'picker' }, [
    field(label, search, 'Names come from the bot\'s own copy of the member list.'),
    results,
    picked,
    status,
  ]);
  return { node, get id() { return chosen.id; }, get name() { return chosen.name; }, clear: () => choose(null) };
}

function jsonText(value) {
  if (value === null || value === undefined) return '';
  try {
    return JSON.stringify(value, null, 2);
  } catch (e) {
    return String(value);
  }
}

const SEG_MAX = 3;
const SEG_FIRST = ['on', 'shadow', 'off'];

/** The mock reads ON · SHADOW · OFF; the registry lists them the other way. */
function segOrder(choices) {
  const known = choices.filter((choice) => SEG_FIRST.includes(String(choice)));
  if (known.length !== choices.length) return choices;
  return SEG_FIRST.filter((one) => choices.map(String).includes(one));
}

/**
 * The mock's three-segment control: ON / SHADOW / OFF for a mode key, and the
 * same shape for any short enum or a yes/no. Wider enums stay a <select>.
 */
export function segment(choices, current, { onChange = null } = {}) {
  const node = el('div', { class: 'seg', role: 'group' });
  const buttons = choices.map((choice) => el('button', {
    type: 'button',
    'data-value': String(choice.value),
    'aria-pressed': String(choice.value) === String(current) ? 'true' : 'false',
    text: choice.label,
  }));
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      for (const other of buttons) {
        other.setAttribute('aria-pressed', other === button ? 'true' : 'false');
      }
      if (onChange) onChange();
    });
    node.append(button);
  });
  node.readValue = () => {
    const on = buttons.find((button) => button.getAttribute('aria-pressed') === 'true');
    return on ? on.getAttribute('data-value') : null;
  };
  node.setValue = (value) => {
    for (const button of buttons) {
      button.setAttribute('aria-pressed', button.getAttribute('data-value') === String(value) ? 'true' : 'false');
    }
  };
  return node;
}

async function control(spec, onChange) {
  const kind = spec.type;
  if (kind === 'channel') return { node: await channelSelect(spec.value), read: (n) => readSelect(n, false) };
  if (kind === 'channels') return { node: await channelSelect(spec.value, { multiple: true }), read: (n) => readSelect(n, true) };
  if (kind === 'role') return { node: await roleSelect(spec.value), read: (n) => readSelect(n, false) };
  if (kind === 'roles') return { node: await roleSelect(spec.value, { multiple: true }), read: (n) => readSelect(n, true) };
  if (kind === 'bool') {
    const node = segment(
      [{ value: 'true', label: 'On' }, { value: 'false', label: 'Off' }],
      spec.value === true ? 'true' : 'false',
      { onChange },
    );
    return { node, read: (n) => n.readValue() === 'true' };
  }
  if (kind === 'enum') {
    const choices = spec.choices || [];
    if (choices.length && choices.length <= SEG_MAX) {
      const node = segment(
        segOrder(choices).map((choice) => ({ value: choice, label: String(choice) })),
        spec.value,
        { onChange },
      );
      return { node, read: (n) => n.readValue() };
    }
    const select = el('select', { class: 'input' });
    select.append(optionNode('', 'not set', spec.value === null || spec.value === undefined));
    for (const choice of choices) {
      select.append(optionNode(choice, choice, String(spec.value) === String(choice)));
    }
    return { node: select, read: (n) => (n.value === '' ? null : n.value) };
  }
  // A multi-enum: every choice is a checkbox, because the answer is a SET and a
  // segment control would say only one of them can be on. Order comes from the
  // registry's own choices list, so the saved value reads the same every time.
  if (kind === 'enums') {
    const wanted = new Set((spec.value || []).map(String));
    const boxes = (spec.choices || []).map((choice) => {
      const box = el('input', { type: 'checkbox', 'data-value': String(choice) });
      box.checked = wanted.has(String(choice));
      if (onChange) box.addEventListener('change', onChange);
      return el('label', { class: 'checkline' }, [box, el('span', { text: String(choice) })]);
    });
    const node = el('div', { class: 'checkset' }, boxes);
    return {
      node,
      read: (n) => [...n.querySelectorAll('input[type=checkbox]')]
        .filter((box) => box.checked)
        .map((box) => box.getAttribute('data-value')),
    };
  }
  if (kind === 'int') {
    const input = el('input', {
      class: 'input',
      type: 'number',
      step: '1',
      min: spec.min === null || spec.min === undefined ? undefined : String(spec.min),
      max: spec.max === null || spec.max === undefined ? undefined : String(spec.max),
      value: spec.value === null || spec.value === undefined ? '' : String(spec.value),
    });
    return { node: input, read: (n) => (n.value === '' ? null : Number(n.value)) };
  }
  if (kind === 'color') {
    const hex = (value) => (typeof value === 'string' && /^#[0-9a-fA-F]{6}$/.test(value) ? value : null);
    const input = el('input', {
      class: 'input color',
      type: 'color',
      value: hex(spec.value) || hex(spec.default) || '#000000',
    });
    return { node: input, read: (n) => n.value };
  }
  if (kind === 'longtext') {
    const area = el('textarea', { class: 'input area', rows: '3' });
    area.value = spec.value === null || spec.value === undefined ? '' : String(spec.value);
    return { node: area, read: (n) => (n.value === '' ? null : n.value) };
  }
  if (kind === 'json') {
    const area = el('textarea', { class: 'input area mono', rows: '6', spellcheck: 'false' });
    area.value = jsonText(spec.value);
    return {
      node: area,
      read: (n) => (n.value.trim() === '' ? null : JSON.parse(n.value)),
    };
  }
  const input = el('input', {
    class: 'input',
    type: 'text',
    value: spec.value === null || spec.value === undefined ? '' : String(spec.value),
  });
  return { node: input, read: (n) => (n.value === '' ? null : n.value) };
}

function storedValue(reply, key) {
  if (reply && typeof reply === 'object' && !Array.isArray(reply)) {
    if ('value' in reply) return reply.value;
    if (key in reply) return reply[key];
  }
  return reply;
}

function same(a, b) {
  try {
    return JSON.stringify(a === undefined ? null : a) === JSON.stringify(b === undefined ? null : b);
  } catch (e) {
    return a === b;
  }
}

function blank(value) {
  return value === null || value === undefined || value === '' || (Array.isArray(value) && value.length === 0);
}

/**
 * One settings row: human label, mono raw key, control. It carries its own
 * dirty mark and left border; saving is the panel's job, not the row's.
 */
export async function settingRow(spec, { onDirty = null, mock = true } = {}) {
  const say = notice();
  const drawnBy = mock && WORDING_TYPES.has(spec.type) ? await previewFeatureFor(spec.key) : null;
  const mark = el('span', { class: 'setrow-mark', text: 'CHANGED', hidden: true });
  const node = el('div', {
    class: 'setrow',
    'data-key': spec.key,
    'data-search': `${spec.key} ${humanLabel(spec.key)} ${spec.type} ${spec.help || ''}`.toLowerCase(),
  });
  const state = { loaded: spec.value };
  const wipe = el('button', {
    class: 'setrow-reset',
    type: 'button',
    'aria-label': `Put ${humanLabel(spec.key)} back to its default`,
    title: 'Put this back to its default',
    hidden: true,
  }, [icon('backspace', 14, 'setrow-reset-mark')]);
  let made = null;

  const readNow = () => {
    try {
      return { ok: true, value: made.read(made.node) };
    } catch (error) {
      return { ok: false, error };
    }
  };

  const row = {
    key: spec.key,
    spec,
    node,
    dirty: false,
    read: () => readNow(),
    reset: null,
    paint: null,
    say,
  };

  const shown = drawnBy
    ? discordMock({
      feature: drawnBy,
      lazy: true,
      draft: () => {
        const found = readNow();
        return { [spec.key]: found.ok && !blank(found.value) ? String(found.value) : '' };
      },
    })
    : null;

  const paint = () => {
    const found = readNow();
    row.dirty = found.ok ? !(same(found.value, state.loaded) || (blank(found.value) && blank(state.loaded))) : true;
    node.setAttribute('data-dirty', row.dirty ? 'true' : 'false');
    mark.hidden = !row.dirty;
    wipe.hidden = !(clearable() && found.ok && !blank(found.value));
    if (shown) shown.repaint();
    if (onDirty) onDirty();
  };
  row.paint = paint;

  made = await control(spec, paint);
  made.node.addEventListener('input', paint);
  made.node.addEventListener('change', paint);

  /** A segment always holds one of its choices and a colour always holds a
      colour, so neither has an empty state to put back. */
  function clearable() {
    return !made.node.setValue && spec.type !== 'color';
  }

  row.blankOut = () => {
    if (made.node.tagName === 'SELECT') {
      for (const option of made.node.options) option.selected = option.value === '';
    } else {
      made.node.value = '';
    }
    say.say('');
    paint();
  };
  wipe.addEventListener('click', () => row.blankOut());

  row.reset = () => {
    if (made.node.setValue) made.node.setValue(state.loaded);
    else if (made.node.tagName === 'SELECT') {
      const wanted = new Set((Array.isArray(state.loaded) ? state.loaded : [state.loaded]).filter((v) => v !== null && v !== undefined).map(String));
      for (const option of made.node.options) option.selected = wanted.has(option.value) || (wanted.size === 0 && option.value === '');
    } else if (made.node.type === 'checkbox') made.node.checked = state.loaded === true;
    else made.node.value = state.loaded === null || state.loaded === undefined ? '' : (typeof state.loaded === 'object' ? jsonText(state.loaded) : String(state.loaded));
    say.say('');
    paint();
  };
  row.settle = (value) => {
    state.loaded = value === undefined ? state.loaded : value;
    paint();
  };

  node.append(
    el('div', { class: 'setrow-head' }, [
      el('span', { class: 'setrow-label', text: humanLabel(spec.key), title: spec.help || undefined }),
      el('span', { class: 'setrow-key', text: spec.key }),
    ]),
    mark,
    el('div', { class: 'setrow-control' }, [made.node]),
    wipe,
    say,
    shown ? el('div', { class: 'setrow-mock' }, [shown.node, shown.say]) : null,
  );
  say.classList.add('setrow-say');
  paint();
  return row;
}

/** The two types whose value is words the bot posts, and so the two a mock is drawn under. */
const WORDING_TYPES = new Set(['text', 'longtext']);

const SHOW_KEYS = 'bb_show_keys';

function keysWanted() {
  try {
    return localStorage.getItem(SHOW_KEYS) === 'true';
  } catch (e) {
    return false;
  }
}

/* Stamped at import, before a row is drawn, so a person who wants the keys
   never sees them appear a frame late. */
document.documentElement.setAttribute('data-showkeys', keysWanted() ? 'true' : 'false');

export function setShowKeys(on) {
  document.documentElement.setAttribute('data-showkeys', on ? 'true' : 'false');
  try {
    localStorage.setItem(SHOW_KEYS, on ? 'true' : 'false');
  } catch (e) {
    /* private mode, a full quota, storage switched off — the choice just is not remembered */
  }
}

/**
 * The switch that reveals the mono raw-key sub-lines. CSS hides them, so they
 * are still in the DOM and the command palette still finds a setting by its
 * key while they are out of sight.
 */
export function keysSwitch() {
  const node = el('button', {
    class: 'btn quiet small',
    type: 'button',
    text: 'Show keys',
    title: 'Show each setting’s raw registry key under its name',
  });
  const paint = () => node.setAttribute(
    'aria-pressed',
    document.documentElement.getAttribute('data-showkeys') === 'true' ? 'true' : 'false',
  );
  node.addEventListener('click', () => {
    setShowKeys(node.getAttribute('aria-pressed') !== 'true');
    paint();
  });
  paint();
  return node;
}

/** Every bar from the render that is being replaced goes with it. */
export function clearDock() {
  const zone = document.getElementById('dockzone');
  if (zone) zone.replaceChildren();
}

/** The one strip at the foot of the page every save bar docks into. */
function dockZone() {
  const found = document.getElementById('dockzone');
  if (found) return found;
  const main = document.querySelector('.shell-main');
  if (!main) return null;
  const zone = el('div', { class: 'dockzone', id: 'dockzone' });
  main.append(zone);
  return zone;
}

/**
 * The docked bar: it exists only while something is dirty, says how many
 * changes are waiting, and offers Discard (quiet) beside Save Changes
 * (accent). It docks itself at the foot of the page rather than sitting in
 * the panel it belongs to, so a caller never places it.
 */
export function saveBar(onSave, onDiscard, { where = null } = {}) {
  const text = el('span', { class: 'savebar-text' });
  const node = el('div', { class: 'savebar' }, [
    el('span', { class: 'dot-sm', 'data-tone': 'warn' }),
    text,
    button('Discard', onDiscard, { tone: 'quiet', small: false }),
    el('button', { class: 'btn save', type: 'button', text: 'Save Changes', on: { click: onSave } }),
  ]);
  const named = (said) => (where ? `${where} — ${said}` : said);
  node.hidden = true;
  node.say = (count, message = null, tone = null) => {
    if (message) {
      text.textContent = named(message);
      node.querySelector('.dot-sm').setAttribute('data-tone', tone || 'warn');
      node.hidden = false;
      return;
    }
    text.textContent = named(`${count} change${count === 1 ? '' : 's'} pending`);
    node.querySelector('.dot-sm').setAttribute('data-tone', 'warn');
    node.hidden = count === 0;
  };
  const zone = dockZone();
  if (zone) zone.append(node);
  return node;
}

/**
 * A set of settings rows sharing ONE save mechanism. `write` sends only the
 * dirty rows; a row emptied back to nothing is CLEARED rather than stored as
 * null, which is how "put this back to its default" survives the docked bar.
 */
export async function settingsEditor(specs, { onSaved = null, where = null, mock = true } = {}) {
  const rows = [];
  const dock = saveBar(() => write(), () => discard(), { where });
  const count = () => rows.filter((row) => row.dirty).length;
  const refresh = () => dock.say(count());

  for (const spec of specs) rows.push(await settingRow(spec, { onDirty: refresh, mock }));

  const discard = () => {
    for (const row of rows) row.reset();
    refresh();
  };

  const write = async () => {
    const dirty = rows.filter((row) => row.dirty);
    if (dirty.length === 0) return;
    dock.say(0, 'Saving…', 'info');
    let saved = 0;
    let refused = 0;
    for (const row of dirty) {
      const found = row.read();
      if (!found.ok) {
        row.say.say(`That is not valid JSON, so nothing was sent: ${found.error.message}`, 'danger');
        refused += 1;
        continue;
      }
      try {
        const clearing = blank(found.value) && !blank(row.spec.value);
        const reply = clearing
          ? await clearSetting(row.key)
          : await saveSetting(row.key, found.value);
        const now = storedValue(reply, row.key);
        row.spec.value = now;
        row.settle(now);
        row.say.say('');
        saved += 1;
        if (onSaved) onSaved(row.key, now);
      } catch (error) {
        const said = sentenceFor(error);
        row.say.say(said.text, said.tone);
        refused += 1;
      }
    }
    if (refused === 0) {
      dock.say(0, `Saved — ${saved} setting${saved === 1 ? '' : 's'}.`, 'ok');
      setTimeout(refresh, 2500);
      return;
    }
    dock.say(0, `${saved} saved, ${refused} refused — the refused rows say why.`, 'danger');
  };

  refresh();
  return { rows, bar: dock, discard, write, dirtyCount: count };
}

export async function settingsPanel(specs, {
  onSaved = null,
  where = null,
  empty = 'This part of the bot has no settings yet.',
} = {}) {
  if (!specs || specs.length === 0) return sayNothing(empty);
  const editor = await settingsEditor(specs, { onSaved, where });
  return el('div', { class: 'settings-grid' }, editor.rows.map((row) => row.node));
}

/** `omit` is how a key that has its own editor higher up the page keeps one home. */
export async function namespaceSettings(namespace, {
  title = 'Settings',
  note = null,
  onSaved = null,
  omit = [],
} = {}) {
  const payload = await settings();
  const skip = new Set(omit);
  const specs = settingsNamespace(payload, namespace).filter((spec) => !skip.has(spec.key));
  const group = section(title, note, { count: specs.length || null });
  group.body.append(await settingsPanel(specs, {
    onSaved,
    where: title,
    empty: `The bot registers no settings under ${namespace}.`,
  }));
  return group.node;
}


/* ---- the Discord mock: what the bot would actually post, live as they type ---- */

const PREVIEW_EVERY_MS = 250;
const MOCK_WORKING = 'Drawing what Discord would show…';
let previewFeatures = null;

/** The map of which settings key has a mock and which has none, asked for once per page.
    The PROMISE is cached, not the answer: ninety rows are built in one pass and would
    otherwise fire ninety requests before the first one came back. */
export function previewMap() {
  if (previewFeatures === null) {
    previewFeatures = api('/api/preview/features').catch(() => ({ features: [], keys: {} }));
  }
  return previewFeatures;
}

/** The feature whose message a settings key writes a word of, or null when it writes none. */
export async function previewFeatureFor(key) {
  const found = await previewMap();
  return (found.keys || {})[key] || null;
}

/** One message, drawn as Discord draws it. `rendered` is /api/preview/message's own answer. */
export function discordMessage(rendered, options = {}) {
  return mountTree(messageTree(rendered, options), el);
}

/**
 * A live mock: it asks the BOT what it would post for `feature` with the draft laid over
 * the stored wording, and repaints on every keystroke (debounced). `draft()` answers the
 * overrides, `sample()` the made-up facts; both are read at paint time so a caller only
 * has to call `repaint()`. Nothing is ever saved by this — the route only ever reads.
 */
export function discordMock({
  feature,
  draft = () => ({}),
  sample = () => ({}),
  say = null,
  lazy = false,
} = {}) {
  const voice = say || notice();
  const holder = el('div', { class: 'dcmock-holder' });
  let timer = null;
  let run = 0;
  let drawn = false;

  const paint = async () => {
    const mine = (run += 1);
    drawn = true;
    try {
      const found = await send('/api/preview/message', 'POST', {
        feature,
        overrides: draft() || {},
        sample: sample() || {},
      });
      if (mine !== run) return;
      holder.replaceChildren(discordMessage(found));
      voice.say('');
    } catch (error) {
      if (mine !== run) return;
      const said = sentenceFor(error);
      voice.say(said.text, said.tone);
    }
  };

  /** Nothing is asked for until the mock has been drawn once — see `watch` below. */
  const repaint = () => {
    if (!drawn) return;
    if (timer) clearTimeout(timer);
    timer = setTimeout(paint, PREVIEW_EVERY_MS);
  };

  /** A lazy mock draws itself the first time it is scrolled to, and not before: a
      settings page holds ninety rows and must not ask the bot ninety times on load. */
  const watch = () => {
    if (typeof IntersectionObserver !== 'function') {
      paint();
      return;
    }
    const seen = new IntersectionObserver((entries) => {
      if (!entries.some((one) => one.isIntersecting)) return;
      seen.disconnect();
      paint();
    });
    seen.observe(holder);
  };

  holder.replaceChildren(el('p', { class: 'field-help', text: MOCK_WORKING }));
  if (lazy) watch();
  else paint();
  return { node: holder, paint, repaint, say: voice };
}

const TEMPLATE_TOKEN = /\{\{|\}\}|\{([^{}]*)\}/g;

const UNREADABLE = 'Black Bloc cannot read this wording, so it would use its own default instead. ' +
  'Every { needs a matching }.';

/**
 * The answer Python's `str.format_map` gives the bot: known tokens filled in,
 * an unknown one left standing, `{{` and `}}` unescaped — and null when a
 * stray brace would have raised, so a caller says the default would be used
 * rather than pretending this wording works.
 */
export function fillTemplate(template, values) {
  const text = String(template === null || template === undefined ? '' : template);
  if (/[{}]/.test(text.replace(TEMPLATE_TOKEN, ''))) return null;
  return text.replace(TEMPLATE_TOKEN, (whole, token) => {
    if (whole === '{{') return '{';
    if (whole === '}}') return '}';
    return token in values ? values[token] : whole;
  });
}

/**
 * One wording key, or several under one save bar: each row is a textarea (or a
 * one-line input where the spec says `editorType: 'text'`), the docked bar the
 * Settings page uses, and `paint(filled, key)` called with the filled-in sample
 * every time the text or one of `controls` changes. `onSaved` is the Settings
 * page's own hook, passed through so a card below can refresh itself.
 * `preview: {feature, sample}` mounts the Discord mock under the rows and asks
 * the bot to re-render the whole message from the draft on every keystroke.
 */
export async function templateEditor(spec, {
  sample = () => ({}),
  paint = null,
  controls = [],
  where = null,
  onSaved = null,
  preview = null,
} = {}) {
  const wanted = (Array.isArray(spec) ? spec : [spec]).map(
    (one) => ({ ...one, type: one.editorType || 'longtext' }),
  );
  const editor = await settingsEditor(wanted, {
    where: where || humanLabel(wanted[0].key),
    onSaved,
    mock: !preview,
  });
  const say = notice();
  const draft = () => Object.fromEntries(editor.rows.map((row) => {
    const found = row.read();
    return [row.key, found.ok && found.value !== null && found.value !== undefined ? String(found.value) : ''];
  }));
  const mock = preview
    ? discordMock({ feature: preview.feature, draft, sample: preview.sample || (() => ({})) })
    : null;
  const repaintOne = (row) => {
    const found = row.read();
    const filled = found.ok ? fillTemplate(found.value, sample()) : null;
    if (filled === null) say.say(UNREADABLE, 'warn');
    else say.say('');
    if (paint) paint(filled, row.key);
  };
  const repaint = () => {
    editor.rows.forEach(repaintOne);
    if (mock) mock.repaint();
  };
  for (const row of editor.rows) {
    const control = row.node.querySelector('.setrow-control');
    if (control) {
      control.addEventListener('input', repaint);
      control.addEventListener('change', repaint);
    }
  }
  for (const one of controls) one.addEventListener('change', repaint);
  repaint();
  return { row: editor.rows[0], rows: editor.rows, editor, say, repaint, mock };
}

/**
 * The mode switch the Overview and Moderation rows share: the settings
 * editor's own three segments, saving on the click because there is no docked
 * bar out here, and putting the old value back with a sentence when the bot
 * refuses. `spec` is the row /api/settings reports for the key.
 */
export function modeSwitch(spec, { onSaved = null, say = null, label = null } = {}) {
  const voice = say || notice();
  const named = label || humanLabel(spec.key);
  let stored = spec.value === null || spec.value === undefined ? null : String(spec.value);
  const choices = segOrder(spec.choices || []).map((choice) => ({
    value: choice,
    label: String(choice),
  }));
  const node = segment(choices, stored, {
    onChange: async () => {
      const wanted = node.readValue();
      if (wanted === stored) return;
      voice.say('Saving…');
      try {
        const reply = await saveSetting(spec.key, wanted);
        stored = String(storedValue(reply, spec.key) ?? wanted);
        node.setValue(stored);
        voice.say(`${named} is now ${stored}.`, 'ok');
        if (onSaved) onSaved(spec.key, stored);
      } catch (error) {
        node.setValue(stored);
        const said = sentenceFor(error);
        voice.say(said.text, said.tone);
      }
    },
  });
  node.setAttribute('data-key', spec.key);
  node.setAttribute('aria-label', `${named} mode`);
  return { node, say: voice };
}

export async function run(say, work, okText) {
  say.say('Working…');
  try {
    const found = await work();
    say.say(typeof okText === 'function' ? okText(found) : okText, 'ok');
    return { ok: true, found };
  } catch (error) {
    const said = sentenceFor(error);
    say.say(said.text, said.tone);
    return { ok: false, found: null };
  }
}

const outcomes = new Map();

/**
 * A write that reloads the page would throw away the sentence saying what it
 * did, because the reload replaces the notice it was written into. `keepSaying`
 * parks it under a name and `sayAgain` puts it back on the notice the reload
 * built, so the outcome survives its own refresh.
 */
export function keepSaying(where, say) {
  const text = say.said === undefined ? say.textContent : say.said;
  outcomes.set(where, { text, tone: say.getAttribute('data-tone') || 'ok' });
}

export function sayAgain(where, say) {
  const found = outcomes.get(where);
  if (!found) return say;
  outcomes.delete(where);
  say.say(found.text, found.tone);
  return say;
}
