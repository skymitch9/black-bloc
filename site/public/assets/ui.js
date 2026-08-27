import {
  Outage,
  clearSetting,
  nameRecord,
  refChannels,
  refMembers,
  refRoles,
  saveSetting,
  settings,
  settingsNamespace,
} from './api.js';

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

const ICONS = {
  chevronDown: { body: '<polyline points="6 9 12 15 18 9"></polyline>', width: 2 },
  chevronRight: { body: '<polyline points="9 18 15 12 9 6"></polyline>', width: 2 },
  search: { body: '<circle cx="11" cy="11" r="7"></circle><line x1="20" y1="20" x2="16.65" y2="16.65"></line>', width: 2 },
  menu: { body: '<line x1="4" y1="7" x2="20" y2="7"></line><line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="17" x2="20" y2="17"></line>', width: 2 },
};

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

export function sayNothing(text) {
  return el('p', { class: 'say-nothing', text });
}

export function slugOf(text) {
  const made = String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return made || 'section';
}

const DEBOUNCE_MS = 200;

export function searchBox({ label = 'Search', placeholder = 'type to filter', onQuery = null } = {}) {
  const input = el('input', {
    class: 'input search',
    type: 'search',
    placeholder,
    autocomplete: 'off',
    'aria-label': label,
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
  const none = sayNothing(empty);
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

export function notice(text = '', tone = null) {
  const node = el('p', { class: 'notice' });
  const say = (message, messageTone = null) => {
    node.textContent = message || '';
    node.hidden = !message;
    if (messageTone) node.setAttribute('data-tone', messageTone);
    else node.removeAttribute('data-tone');
  };
  say(text, tone);
  node.say = say;
  return node;
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

export function table(columns, rows, {
  empty = 'Nothing here yet.',
  search = 'auto',
  searchLabel = 'Search this table',
} = {}) {
  if (!rows || rows.length === 0) return sayNothing(empty);
  const head = el('tr', {}, columns.map((column) =>
    el('th', { scope: 'col', text: column.label })));
  const body = rows.map((row, index) => el('tr', {}, columns.map((column) => {
    const made = column.cell ? column.cell(row, index) : row[column.key];
    const cell = el('td', { class: column.className || undefined });
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
  if (!wanted) return scroll;

  const shown = el('span', { class: 'table-count', text: `${rows.length} row(s)` });
  const none = sayNothing('Nothing in this table matches what you typed.');
  none.hidden = true;
  const input = searchField({
    label: searchLabel,
    placeholder: 'filter these rows',
    onQuery: (query) => {
      const found = filterRows(scroll, query);
      shown.textContent = query === ''
        ? `${found.total} row(s)`
        : `${found.shown} of ${found.total}`;
      none.hidden = found.shown > 0;
      scroll.hidden = found.shown === 0;
    },
  });
  return el('div', { class: 'table-block' }, [
    el('div', { class: 'table-tools' }, [input, shown]),
    scroll,
    none,
  ]);
}

export function pager({ page, hasMore, onPage, count = null }) {
  const at = Number(page) || 1;
  return el('div', { class: 'pager' }, [
    button('Previous', () => onPage(at - 1), { tone: 'quiet', disabled: at <= 1 }),
    el('span', { class: 'pager-at', text: count === null ? `Page ${at}` : `Page ${at} · ${count} shown` }),
    button('Next', () => onPage(at + 1), { tone: 'quiet', disabled: !hasMore }),
  ]);
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

export function field(label, control, help = null) {
  const id = control && control.id ? control.id : null;
  return el('div', { class: 'field' }, [
    el('label', { class: 'field-label', for: id || undefined, text: label }),
    control,
    help ? el('p', { class: 'field-help', text: help }) : null,
  ]);
}

function optionNode(value, label, selected) {
  return el('option', { value: String(value), text: label, selected: selected || undefined });
}

const CHANNEL_KIND = { text: '#', voice: '🔊', forum: '#', category: '▸' };

function channelLabel(channel) {
  const mark = CHANNEL_KIND[channel.type] || '#';
  return `${mark} ${channel.name}`;
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
    select.append(optionNode(channel.id, channelLabel(channel), chosen.has(String(channel.id))));
  }
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
  return select;
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
function segment(choices, current, { onChange = null } = {}) {
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

const NAMESPACES = ['golive', 'tempvoice', 'honeypot', 'events', 'birthday', 'modmail', 'automod', 'rolemenu'];

/** The human name a key wears; the raw key survives as the mono sub-line. */
export function humanLabel(key) {
  let name = String(key || '');
  for (const namespace of NAMESPACES) {
    if (name.startsWith(`${namespace}_`) && name.length > namespace.length + 1) {
      name = name.slice(namespace.length + 1);
      break;
    }
  }
  name = name.replace(/_ids?$/, '');
  name = name.replace(/_/g, ' ').trim();
  if (!name) name = String(key);
  return name.charAt(0).toUpperCase() + name.slice(1);
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
export async function settingRow(spec, { onDirty = null } = {}) {
  const say = notice();
  const mark = el('span', { class: 'setrow-mark', text: 'CHANGED', hidden: true });
  const node = el('div', {
    class: 'setrow',
    'data-key': spec.key,
    'data-search': `${spec.key} ${humanLabel(spec.key)} ${spec.type} ${spec.help || ''}`.toLowerCase(),
  });
  const state = { loaded: spec.value };
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

  const paint = () => {
    const found = readNow();
    row.dirty = found.ok ? !same(found.value, state.loaded) : true;
    node.setAttribute('data-dirty', row.dirty ? 'true' : 'false');
    mark.hidden = !row.dirty;
    if (onDirty) onDirty();
  };
  row.paint = paint;

  made = await control(spec, paint);
  made.node.addEventListener('input', paint);
  made.node.addEventListener('change', paint);

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
    say,
  );
  say.classList.add('setrow-say');
  paint();
  return row;
}

/**
 * The docked bar: it exists only while something is dirty, says how many
 * settings are waiting, and offers Discard (quiet) beside Save (accent).
 */
export function saveBar(onSave, onDiscard) {
  const text = el('span', { class: 'savebar-text' });
  const node = el('div', { class: 'savebar' }, [
    el('span', { class: 'dot-sm', 'data-tone': 'warn' }),
    text,
    button('Discard', onDiscard, { tone: 'quiet', small: false }),
    el('button', { class: 'btn save', type: 'button', text: 'Save', on: { click: onSave } }),
  ]);
  node.hidden = true;
  node.say = (count, message = null, tone = null) => {
    if (message) {
      text.textContent = message;
      node.querySelector('.dot-sm').setAttribute('data-tone', tone || 'warn');
      node.hidden = false;
      return;
    }
    text.textContent = `Unsaved changes — ${count} setting${count === 1 ? '' : 's'}`;
    node.querySelector('.dot-sm').setAttribute('data-tone', 'warn');
    node.hidden = count === 0;
  };
  return node;
}

/**
 * A set of settings rows sharing ONE save mechanism. `write` sends only the
 * dirty rows; a row emptied back to nothing is CLEARED rather than stored as
 * null, which is how "put this back to its default" survives the docked bar.
 */
export async function settingsEditor(specs, { onSaved = null } = {}) {
  const rows = [];
  const dock = saveBar(() => write(), () => discard());
  const count = () => rows.filter((row) => row.dirty).length;
  const refresh = () => dock.say(count());

  for (const spec of specs) rows.push(await settingRow(spec, { onDirty: refresh }));

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

export async function settingsPanel(specs, { onSaved = null, empty = 'This part of the bot has no settings yet.' } = {}) {
  if (!specs || specs.length === 0) return sayNothing(empty);
  const editor = await settingsEditor(specs, { onSaved });
  return el('div', { class: 'settings-grid' }, [
    ...editor.rows.map((row) => row.node),
    editor.bar,
  ]);
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
    empty: `The bot registers no settings under ${namespace}.`,
  }));
  return group.node;
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
 * A wording key edited with a preview: one settingsEditor row rendered as a
 * textarea, the docked bar the Settings page uses, and `paint` called with the
 * filled-in sample every time the text or one of `controls` changes.
 */
export async function templateEditor(spec, { sample = () => ({}), paint = null, controls = [] } = {}) {
  const editor = await settingsEditor([{ ...spec, type: 'longtext' }]);
  const row = editor.rows[0];
  const say = notice();
  const repaint = () => {
    const found = row.read();
    const filled = found.ok ? fillTemplate(found.value, sample()) : null;
    if (filled === null) say.say(UNREADABLE, 'warn');
    else say.say('');
    if (paint) paint(filled);
  };
  const control = row.node.querySelector('.setrow-control');
  if (control) {
    control.addEventListener('input', repaint);
    control.addEventListener('change', repaint);
  }
  for (const one of controls) one.addEventListener('change', repaint);
  repaint();
  return { row, editor, say, repaint };
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
