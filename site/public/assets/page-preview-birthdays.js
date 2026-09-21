import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  bar,
  button,
  card,
  el,
  field,
  fillTemplate,
  humanLabel,
  nameNode,
  notice,
  openDrawer,
  saveBar,
  searchOver,
  section,
  settingRow,
  table,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

const AT = Date.now();
const minutesAgo = (n) => new Date(AT - n * 60000).toISOString();

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const SAMPLE = { name: 'Casey', age: '30' };

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null },
  { id: '800000000000000003', name: 'blackbloc-logs', type: 'text', category_id: null },
  { id: '800000000000000004', name: 'bot-log', type: 'text', category_id: null },
  { id: '800000000000000005', name: 'staff-room', type: 'text', category_id: null },
  { id: '800000000000000006', name: 'announcements', type: 'text', category_id: null },
  { id: '800000000000000007', name: 'free-nitro-here', type: 'text', category_id: null },
  { id: '800000000000000008', name: 'Events', type: 'category', category_id: null },
  { id: '800000000000000009', name: 'Join to create', type: 'voice', category_id: null },
  { id: '800000000000000010', name: "casey's room", type: 'voice', category_id: null },
  { id: '800000000000000011', name: 'modmail', type: 'category', category_id: null },
  { id: '800000000000000012', name: 'modmail-log', type: 'text', category_id: '800000000000000011' },
];

const ROLES = [
  { id: '900000000000000001', name: 'Aunties / Uncles' },
  { id: '900000000000000002', name: 'Leads' },
  { id: '900000000000000003', name: 'Live now' },
  { id: '900000000000000004', name: 'Birthday' },
  { id: '900000000000000005', name: 'Members' },
  { id: '900000000000000006', name: 'Server Booster' },
  { id: '900000000000000007', name: 'Events' },
  { id: '900000000000000008', name: 'Casey pings' },
];

const MEMBERS = [
  { id: '700000000000000001', name: 'nbaslamking', display_name: 'Nick' },
  { id: '700000000000000002', name: 'caseyfast', display_name: 'Casey' },
  { id: '700000000000000003', name: 'rivet.exe', display_name: 'Rivet' },
  { id: '700000000000000004', name: 'moth_light', display_name: 'Moth' },
  { id: '700000000000000005', name: 'spamlord99', display_name: 'spamlord99' },
  { id: '700000000000000006', name: 'quietkid', display_name: 'Quiet Kid' },
  { id: '700000000000000007', name: 'daxthecat', display_name: 'Dax' },
  { id: '700000000000000008', name: 'gonefromguild', display_name: 'Left the server' },
];

const DATA = {
  birthdays: [
    { user_id: '700000000000000002', user_name: 'Casey', month: 2, day: 14, year: 1996, when: 'February 14', opted_in: true, source: 'self', set_at: minutesAgo(9000), last_announced_on: null },
    { user_id: '700000000000000003', user_name: 'Rivet', month: 2, day: 27, year: null, when: 'February 27', opted_in: true, source: 'import', set_at: minutesAgo(12000), last_announced_on: null },
    { user_id: '700000000000000004', user_name: 'Moth', month: 7, day: 4, year: 2001, when: 'July 4', opted_in: true, source: 'self', set_at: minutesAgo(15000), last_announced_on: null },
    { user_id: '700000000000000007', user_name: 'Dax', month: 11, day: 30, year: null, when: 'November 30', opted_in: false, source: 'import', set_at: minutesAgo(16000), last_announced_on: null },
    { user_id: '700000000000000001', user_name: 'Nick', month: 2, day: 3, year: 1990, when: 'February 3', opted_in: true, source: 'self', set_at: minutesAgo(17000), last_announced_on: null },
    { user_id: '700000000000000006', user_name: 'Quiet Kid', month: 7, day: 19, year: null, when: 'July 19', opted_in: true, source: 'import', set_at: minutesAgo(18000), last_announced_on: null },
    { user_id: '700000000000000008', user_name: 'Left the server', month: 4, day: 8, year: 1999, when: 'April 8', opted_in: true, source: 'import', set_at: minutesAgo(19000), last_announced_on: null },
  ],
  settings: [
    { key: 'birthday_mode', type: 'enum', value: 'shadow', default: 'off', help: 'off, shadow (log only) or on (post birthday wishes)', choices: ['off', 'shadow', 'on'] },
    { key: 'birthday_channel_id', type: 'channel', value: '800000000000000002', default: null, help: 'where birthday wishes are posted' },
    { key: 'birthday_template', type: 'text', value: 'Happy birthday {name}!', default: 'Happy birthday {name}!', help: 'the birthday wording; {name} and {age}' },
    { key: 'birthday_color', type: 'color', value: '#4eefff', default: '#4eefff', help: 'the birthday embed’s colour, as a hex code like #4eefff' },
    { key: 'birthday_role_id', type: 'role', value: '900000000000000004', default: null, help: 'role given for the day and taken back the next' },
    { key: 'birthday_show_age', type: 'bool', value: false, default: false, help: 'true to put {age} in reach for people who stored a birth year' },
    { key: 'birthday_log_level', type: 'enum', value: 'important', default: 'important', help: 'which birthdays log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/birthday logs` either way', choices: ['off', 'important', 'all'] },
    { key: 'birthday_panel_lookup', type: 'bool', value: true, default: true, help: "true to let any member look somebody else's stored birthday up on the /birthday panel; staff always can. Opting out is still the member's own privacy control" },
    { key: 'birthday_panel_minutes', type: 'int', value: 10, default: 10, help: "minutes the /birthday panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it" },
    { key: 'birthday_panel_next_for_members', type: 'bool', value: true, default: true, help: 'true to show every member the birthdays coming up on the /birthday panel; staff always see them. False makes the list staff-only and the panel says so in words' },
  ],
  logs: [
    { id: 23, at: minutesAgo(9600), kind: 'birthday.would_wish', feature: 'birthday', important: false, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000002', target_name: 'Casey', reason: 'February 14', summary: 'February 14' },
  ],
};

const TEMPLATE_KEY = 'birthday_template';
const COLOR_KEY = 'birthday_color';

const REF = {
  channel: { list: CHANNELS, multiple: false },
  channels: { list: CHANNELS, multiple: true },
  role: { list: ROLES, multiple: false },
  roles: { list: ROLES, multiple: true },
};

const CHANNEL_KIND = { text: '#', voice: '🔊', forum: '#', category: '▸' };

function channelOption(one) {
  const mark = CHANNEL_KIND[one.type] || '#';
  const where = one.category_id
    ? (CHANNELS.find((c) => c.id === one.category_id) || {}).name || ''
    : '';
  return where ? `${mark} ${one.name} · ${where}` : `${mark} ${one.name}`;
}

/** ui.js builds a channel/role control by asking the bot for the list, so a static page grows its own. */
function refControl(spec) {
  const { list, multiple } = REF[spec.type];
  const chosen = new Set((multiple ? spec.value || [] : [spec.value]).filter(Boolean).map(String));
  const select = el('select', {
    class: 'input field-control',
    multiple: multiple || undefined,
    size: multiple ? Math.min(8, Math.max(3, list.length)) : undefined,
  });
  if (!multiple) select.append(el('option', { value: '', text: 'not set', selected: chosen.size === 0 || undefined }));
  for (const one of list) {
    select.append(el('option', {
      value: one.id,
      text: list === CHANNELS ? channelOption(one) : `@${one.name}`,
      selected: chosen.has(String(one.id)) || undefined,
    }));
  }
  return select;
}

function refRow(spec, onDirty) {
  const mark = el('span', { class: 'setrow-mark', text: 'CHANGED', hidden: true });
  const control = refControl(spec);
  const say = notice();
  say.classList.add('setrow-say');
  const node = el('div', {
    class: 'setrow',
    'data-key': spec.key,
    'data-dirty': 'false',
    'data-search': `${spec.key} ${humanLabel(spec.key)} ${spec.type} ${spec.help || ''}`.toLowerCase(),
  }, [
    el('div', { class: 'setrow-head' }, [
      el('span', { class: 'setrow-label', text: humanLabel(spec.key), title: spec.help || undefined }),
      el('span', { class: 'setrow-key', text: spec.key }),
    ]),
    mark,
    el('div', { class: 'setrow-control' }, [control]),
    say,
  ]);
  const row = { key: spec.key, spec, node, dirty: false, say, reset: () => {} };
  control.addEventListener('change', () => {
    row.dirty = true;
    node.setAttribute('data-dirty', 'true');
    mark.hidden = false;
    if (onDirty) onDirty();
  });
  return row;
}

const rowFor = (spec, onDirty) => (REF[spec.type] ? refRow(spec, onDirty) : settingRow(spec, { onDirty }));

/** ui.js's memberPicker searches the bot for names, so a static page picks from the seed instead. */
function previewPicker() {
  const chosen = { id: null, name: null };
  const search = el('input', { class: 'input', type: 'search', placeholder: 'type part of a name', autocomplete: 'off' });
  const results = el('ul', { class: 'picker-results', hidden: true });
  const picked = el('p', { class: 'picker-picked', hidden: true });
  const choose = (member) => {
    chosen.id = member ? member.id : null;
    chosen.name = member ? member.display_name : null;
    picked.textContent = member ? `${chosen.name} · id ${chosen.id}` : '';
    picked.hidden = !member;
    results.replaceChildren();
    results.hidden = true;
    search.value = member ? chosen.name : '';
  };
  search.addEventListener('input', () => {
    const query = search.value.trim().toLowerCase();
    if (query.length < 2) {
      results.replaceChildren();
      results.hidden = true;
      return;
    }
    const found = MEMBERS.filter((one) => `${one.name} ${one.display_name}`.toLowerCase().includes(query));
    results.replaceChildren(...found.map((member) => el('li', {}, [
      button(`${member.display_name} · ${member.id}`, () => choose(member), { tone: 'quiet' }),
    ])));
    results.hidden = found.length === 0;
  });
  const node = el('div', { class: 'picker' }, [
    field('Member', search, 'Names come from the bot\'s own copy of the member list.'),
    results,
    picked,
  ]);
  return { node, get id() { return chosen.id; }, get name() { return chosen.name; } };
}

function daysUntil(row) {
  const now = new Date();
  const year = now.getFullYear();
  let next = new Date(year, row.month - 1, row.day);
  const today = new Date(year, now.getMonth(), now.getDate());
  if (next < today) next = new Date(year + 1, row.month - 1, row.day);
  return Math.round((next - today) / 86400000);
}

/** The one place the shadow rule is told, with the key that decides it. */
function strip() {
  const rows = DATA.birthdays;
  const wished = rows.filter((row) => row.opted_in !== false);
  const mode = DATA.settings.find((spec) => spec.key === 'birthday_mode').value;
  const next = wished.slice().sort((a, b) => daysUntil(a) - daysUntil(b))[0];
  const said = el('p', { class: 'today-line' });
  said.append(
    `${rows.length} birthday${rows.length === 1 ? '' : 's'} stored`,
    rows.length === wished.length ? '' : `, ${rows.length - wished.length} opted out`,
    '. ',
    next
      ? `The next is ${next.user_name} on ${next.when} — ${daysUntil(next) === 0 ? 'today' : `in ${daysUntil(next)} day${daysUntil(next) === 1 ? '' : 's'}`}. `
      : 'Nobody has a birthday stored, so there is nothing coming up. ',
    mode === 'on'
      ? 'Black Bloc posts the wish itself. '
      : (mode === 'shadow'
        ? 'Black Bloc is in shadow: it writes the wish down instead of posting it. '
        : 'Birthdays are off, so nothing is posted and nothing is written down. '),
    el('a', {
      class: 'today-link',
      href: '/preview/settings.html#birthday_mode',
      title: 'birthday_mode on the Settings page decides this',
      'data-tone': mode === 'on' ? 'calm' : 'warn',
    }, [el('span', { class: 'dot-sm', 'data-tone': mode === 'on' ? 'ok' : 'warn' }), el('span', { text: `birthday_mode = ${mode}` })]),
  );
  return el('div', {
    class: 'today',
    'data-span': 'full',
    'data-tone': 'calm',
  }, [el('span', { class: 'today-head', text: 'Coming up' }), said]);
}

function setForm(say) {
  const picker = previewPicker();
  const month = el('select', { class: 'input' });
  MONTHS.forEach((name, at) => month.append(el('option', { value: String(at + 1), text: name })));
  const day = el('input', { class: 'input', type: 'number', min: '1', max: '31', value: '1' });
  const year = el('input', { class: 'input', type: 'number', min: '1900', max: '2020', placeholder: 'optional' });
  const save = button('Save birthday', () => {
    if (!picker.id) {
      say.say('Pick the member first.', 'warn');
      return;
    }
    wouldDo(say, `PUT /api/birthdays/${picker.id} — store ${picker.name} as ${MONTHS[Number(month.value) - 1]} ${day.value}${year.value ? `, ${year.value}` : ''}`);
  });
  return [
    picker.node,
    el('div', { class: 'formrow dateline' }, [field('Month', month), field('Day', day), field('Year', year)]),
    el('p', { class: 'field-help', text: 'The year is optional, and only used when birthday_show_age is on.' }),
    bar([save]),
    say,
  ];
}

function wordingCard(say, onDirty) {
  const spec = DATA.settings.find((one) => one.key === TEMPLATE_KEY);
  const color = DATA.settings.find((one) => one.key === COLOR_KEY).value;
  const shown = el('p', { class: 'preview' });
  const area = el('textarea', { class: 'input area field-control', rows: '3' });
  area.value = spec.value;
  const mark = el('span', { class: 'setrow-mark', text: 'CHANGED', hidden: true });
  const warn = notice();
  const repaint = () => {
    const filled = fillTemplate(area.value, SAMPLE);
    shown.textContent = filled === null
      ? 'Black Bloc would post its own default wish instead.'
      : filled;
    warn.say(filled === null
      ? 'Black Bloc cannot read this wording, so it would use its own default instead. Every { needs a matching }.'
      : '', filled === null ? 'warn' : null);
  };
  const row = { key: TEMPLATE_KEY, spec, dirty: false, say, reset: () => { area.value = spec.value; row.dirty = false; mark.hidden = true; repaint(); } };
  area.addEventListener('input', () => {
    row.dirty = area.value !== spec.value;
    mark.hidden = !row.dirty;
    repaint();
    if (onDirty) onDirty();
  });
  repaint();
  const node = el('div', {
    class: 'setrow',
    'data-key': TEMPLATE_KEY,
    'data-search': `${TEMPLATE_KEY} ${humanLabel(TEMPLATE_KEY)} text ${spec.help}`.toLowerCase(),
  }, [
    el('div', { class: 'setrow-head' }, [
      el('span', { class: 'setrow-label', text: humanLabel(TEMPLATE_KEY), title: spec.help }),
      el('span', { class: 'setrow-key', text: TEMPLATE_KEY }),
    ]),
    mark,
    el('div', { class: 'setrow-control' }, [area]),
    warn,
  ]);
  const swatch = el('span', { class: 'swatch', style: color ? `--swatch: ${color}` : undefined });
  return {
    row,
    node: card('What a birthday wish looks like', [
      node,
      el('p', { class: 'field-help' }, [
        'Filled in with a made-up member. The embed’s colour is ',
        swatch,
        color ? ` ${color}` : ' not set',
        ', from birthday_color.',
      ]),
      shown,
    ]),
  };
}

async function load() {
  const banner = previewBanner({
    today: 5,
    preview: 3,
    note: 'Set a birthday is one drawer off the page head; the wording moved into Settings, beside the colour it is drawn in.',
  });
  banner.setAttribute('data-span', 'full');

  const say = notice();
  const aside = document.getElementById('page-aside');
  if (aside) {
    aside.replaceChildren(button('Set a birthday', () => {
      const drawerSay = notice();
      openDrawer('Set a birthday', setForm(drawerSay));
    }, { small: false }));
  }

  const byMonth = new Map();
  for (const row of DATA.birthdays) {
    const key = Number(row.month) || 0;
    byMonth.set(key, (byMonth.get(key) || []).concat([row]));
  }

  const monthTable = (list) => table([
    { label: 'Day', cell: (row) => String(row.day), className: 'mono' },
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Year', cell: (row) => (row.year ? String(row.year) : null) },
    {
      label: 'Wished',
      help: 'Whether Black Bloc says anything on the day. A member can opt out themselves.',
      cell: (row) => button(row.opted_in === false ? 'opted out' : 'yes', () => {
        wouldDo(say, `POST /api/birthdays/${row.user_id}/optin — ${row.opted_in === false ? `put ${row.user_name} back in, so Black Bloc wishes them a happy birthday again` : `opt ${row.user_name} out, so Black Bloc says nothing on their birthday`}`);
      }, { tone: row.opted_in === false ? 'warn' : 'quiet' }),
    },
    { label: 'From', cell: (row) => row.source },
    {
      label: '',
      cell: (row) => button('Remove', () => {
        wouldDo(say, `DELETE /api/birthdays/${row.user_id} — forget ${row.user_name}’s date. They can set it again themselves`);
      }, { tone: 'danger' }),
    },
  ], list.slice().sort((a, b) => a.day - b.day), { search: false });

  const months = section('By month', `${DATA.birthdays.length} birthday(s) stored.`, { count: DATA.birthdays.length, open: true });
  const box = el('div', { class: 'section-body' });
  for (let at = 1; at <= 12; at += 1) {
    const list = byMonth.get(at);
    if (!list || list.length === 0) continue;
    box.append(card(MONTHS[at - 1], [monthTable(list)]));
  }
  months.body.append(
    previewWas('Replaces By month and Add or change one. The list is section one and it is open on arrival, so the page opens on the birthdays rather than on a blank form; Set a birthday is the page-head action.'),
    searchOver(box, {
      label: 'Search the birthday list',
      placeholder: 'a name, a month or a day',
      noun: 'month(s)',
      empty: 'No month has anybody matching that.',
    }),
    box,
    say,
  );

  const settingsSay = notice();
  const rows = [];
  const dock = saveBar(
    () => wouldDo(settingsSay, `PUT /api/settings/<key> — write the ${rows.filter((row) => row.dirty).length} changed birthday key(s), one PUT each`),
    () => {
      for (const row of rows) row.reset();
      dock.say(0);
    },
    { where: 'Settings' },
  );
  const recount = () => dock.say(rows.filter((row) => row.dirty).length);
  const wording = wordingCard(settingsSay, recount);
  rows.push(wording.row);
  const plain = [];
  for (const spec of DATA.settings) {
    if (spec.key === TEMPLATE_KEY) continue;
    const row = await rowFor(spec, recount);
    rows.push(row);
    plain.push(row);
  }
  recount();

  const settings = section('Settings', null, { count: rows.length });
  settings.body.append(
    previewWas('Replaces Birthday wording and Settings. The wording is still its own card with the live preview, but it is now under one save bar with the nine keys around it — including birthday_color, which draws the swatch beside it.'),
    wording.node,
    el('div', { class: 'settings-grid' }, plain.map((row) => row.node)),
    settingsSay,
  );

  const logs = section('Logs', 'Everything birthdays has done, whether or not it said so in Discord. Important means it acted on a member or failed.', { count: DATA.logs.length });
  logs.body.append(
    previewWas('Replaces the Logs section, unchanged — one log surface, shut by default.'),
    logsTable(DATA.logs, 'Birthdays has done nothing yet.'),
  );

  document.getElementById('dash').replaceChildren(
    banner,
    strip(),
    months.node,
    settings.node,
    logs.node,
  );
}

start({ tab: 'birthdays', load });
