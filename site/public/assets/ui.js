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

export function when(iso) {
  if (!iso) return '—';
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? String(iso) : at.toLocaleString();
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

export function section(title, note) {
  const body = el('div', { class: 'section-body' });
  const node = el('section', {}, [
    el('h2', { text: title }),
    note ? el('p', { class: 'section-note', text: note }) : null,
    body,
  ]);
  return { node, body };
}

export function card(title, children) {
  return el('div', { class: 'card' }, [title ? el('h3', { text: title }) : null].concat(children));
}

export function bar(children) {
  return el('div', { class: 'bar' }, children);
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

export function table(columns, rows, { empty = 'Nothing here yet.' } = {}) {
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
  return el('div', { class: 'table-scroll' }, [
    el('table', { class: 'log-table' }, [
      el('thead', {}, [head]),
      el('tbody', {}, body),
    ]),
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
  try {
    return JSON.stringify(value === null || value === undefined ? {} : value, null, 2);
  } catch (e) {
    return String(value);
  }
}

async function control(spec) {
  const kind = spec.type;
  if (kind === 'channel') return { node: await channelSelect(spec.value), read: (n) => readSelect(n, false) };
  if (kind === 'channels') return { node: await channelSelect(spec.value, { multiple: true }), read: (n) => readSelect(n, true) };
  if (kind === 'role') return { node: await roleSelect(spec.value), read: (n) => readSelect(n, false) };
  if (kind === 'roles') return { node: await roleSelect(spec.value, { multiple: true }), read: (n) => readSelect(n, true) };
  if (kind === 'bool') {
    const box = el('input', { class: 'input switch', type: 'checkbox', checked: spec.value === true || undefined });
    return { node: box, read: (n) => n.checked };
  }
  if (kind === 'enum') {
    const select = el('select', { class: 'input' });
    select.append(optionNode('', 'not set', spec.value === null || spec.value === undefined));
    for (const choice of spec.choices || []) {
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
    const input = el('input', {
      class: 'input color',
      type: 'color',
      value: typeof spec.value === 'string' && /^#[0-9a-fA-F]{6}$/.test(spec.value) ? spec.value : '#4eefff',
    });
    return { node: input, read: (n) => n.value };
  }
  if (kind === 'json') {
    const area = el('textarea', { class: 'input area mono', rows: '10', spellcheck: 'false' });
    area.value = jsonText(spec.value);
    return {
      node: area,
      read: (n) => JSON.parse(n.value),
    };
  }
  const input = el('input', {
    class: 'input',
    type: 'text',
    value: spec.value === null || spec.value === undefined ? '' : String(spec.value),
  });
  return { node: input, read: (n) => (n.value === '' ? null : n.value) };
}

function shown(value) {
  if (value === null || value === undefined || value === '') return 'not set';
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'empty';
  if (typeof value === 'object') return jsonText(value);
  return String(value);
}

async function labeller(type) {
  if (type === 'channel' || type === 'channels') {
    const list = await refChannels();
    return (id) => {
      const found = list.find((channel) => String(channel.id) === String(id));
      return found ? channelLabel(found) : null;
    };
  }
  if (type === 'role' || type === 'roles') {
    const list = await refRoles();
    return (id) => {
      const found = list.find((role) => String(role.id) === String(id));
      return found ? `@${found.name}` : null;
    };
  }
  return null;
}

function labelled(value, label) {
  const items = Array.isArray(value) ? value : [value];
  if (items.length === 0) return el('span', { class: 'muted', text: 'empty' });
  const parts = [];
  items.forEach((item, at) => {
    if (at > 0) parts.push(', ');
    if (item === null || item === undefined || item === '') {
      parts.push(el('span', { class: 'muted', text: 'not set' }));
      return;
    }
    const name = label(item);
    parts.push(name
      ? el('span', { class: 'name', title: `Discord id ${item}`, text: name })
      : nameNode(String(item)));
  });
  return el('span', {}, parts);
}

function describeValue(value, label) {
  return label ? labelled(value, label) : valueNode(value);
}

function describeText(value, label) {
  if (!label) return shown(value);
  const items = Array.isArray(value) ? value : [value];
  if (items.length === 0) return 'empty';
  return items
    .map((item) => (item === null || item === undefined || item === '' ? 'not set' : label(item) || String(item)))
    .join(', ');
}

function storedValue(reply, key) {
  if (reply && typeof reply === 'object' && !Array.isArray(reply)) {
    if ('value' in reply) return reply.value;
    if (key in reply) return reply[key];
  }
  return reply;
}

export async function settingRow(spec, { onSaved = null } = {}) {
  const made = await control(spec);
  const label = await labeller(spec.type);
  const say = notice();
  const current = el('p', { class: 'field-current' });
  const paint = (value) => current.replaceChildren('Now: ', describeValue(value, label));
  paint(spec.value);

  const save = button('Save', async () => {
    let value;
    try {
      value = made.read(made.node);
    } catch (error) {
      say.say(`That is not valid JSON, so nothing was sent: ${error.message}`, 'danger');
      return;
    }
    say.say('Saving…');
    try {
      const reply = await saveSetting(spec.key, value);
      const now = storedValue(reply, spec.key);
      paint(now);
      say.say(`Saved. ${spec.key} is now ${describeText(now, label)}.`, 'ok');
      if (onSaved) onSaved(spec.key, now);
    } catch (error) {
      const said = sentenceFor(error);
      say.say(said.text, said.tone);
    }
  });

  const clear = button('Clear', async () => {
    const sure = await ask({
      title: `Clear ${spec.key}?`,
      body: [
        `This puts ${spec.key} back to its default (${describeText(spec.default, label)}). The bot picks the change up straight away.`,
      ],
      confirmLabel: 'Clear it',
    });
    if (!sure) return;
    say.say('Clearing…');
    try {
      const reply = await clearSetting(spec.key);
      const now = storedValue(reply, spec.key);
      paint(now === undefined ? spec.default : now);
      say.say(`Cleared. ${spec.key} is back to its default.`, 'ok');
      if (onSaved) onSaved(spec.key, now);
    } catch (error) {
      const said = sentenceFor(error);
      say.say(said.text, said.tone);
    }
  }, { tone: 'quiet' });

  return el('div', { class: 'setting' }, [
    el('div', { class: 'setting-head' }, [
      el('span', { class: 'setting-key', text: spec.key }),
      el('span', { class: 'setting-type', text: spec.type }),
    ]),
    spec.help ? el('p', { class: 'field-help', text: spec.help }) : null,
    made.node,
    current,
    bar([save, clear]),
    say,
  ]);
}

export async function settingsPanel(specs, { onSaved = null, empty = 'This part of the bot has no settings yet.' } = {}) {
  if (!specs || specs.length === 0) return sayNothing(empty);
  const rows = [];
  for (const spec of specs) rows.push(await settingRow(spec, { onSaved }));
  return el('div', { class: 'settings-grid' }, rows);
}

export async function namespaceSettings(namespace, { title = 'Settings', note = null, onSaved = null } = {}) {
  const payload = await settings();
  const group = section(title, note);
  group.body.append(await settingsPanel(settingsNamespace(payload, namespace), {
    onSaved,
    empty: `The bot registers no settings under ${namespace}.`,
  }));
  return group.node;
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
