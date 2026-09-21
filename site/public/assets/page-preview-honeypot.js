import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  badge,
  button,
  el,
  humanLabel,
  modeChip,
  nameNode,
  notice,
  saveBar,
  section,
  settingRow,
  table,
  when,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

const AT = Date.now();
const minutesAgo = (n) => new Date(AT - n * 60000).toISOString();

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

const DATA = {
  hits: [
    { id: 7, user_id: '700000000000000005', user_name: 'spamlord99', channel_id: '800000000000000007', channel_name: '#free-nitro-here', message_id: '820000000000000001', content: 'free nitro at scam-link.example', at: minutesAgo(30), mode: 'shadow', action: 'would_ban' },
    { id: 6, user_id: '700000000000000008', user_name: 'Left the server', channel_id: '800000000000000007', channel_name: '#free-nitro-here', message_id: '820000000000000002', content: 'steam gift card giveaway', at: minutesAgo(900), mode: 'shadow', action: 'would_ban' },
    { id: 5, user_id: '700000000000000006', user_name: 'Quiet Kid', channel_id: '800000000000000007', channel_name: '#free-nitro-here', message_id: '820000000000000003', content: 'dm me for cheap nitro', at: minutesAgo(2600), mode: 'on', action: 'banned' },
    { id: 4, user_id: '700000000000000008', user_name: 'Left the server', channel_id: '800000000000000007', channel_name: '#free-nitro-here', message_id: '820000000000000004', content: 'crypto doubler, first 50 only', at: minutesAgo(6100), mode: 'on', action: 'ban_failed' },
  ],
  settings: [
    { key: 'honeypot_mode', type: 'enum', value: 'shadow', default: 'off', help: 'off, shadow (log only) or on (ban whoever posts in the trap)', choices: ['off', 'shadow', 'on'] },
    { key: 'honeypot_channel_ids', type: 'channels', value: ['800000000000000007'], default: [], help: 'the trap channels; Setup… on /honeypot fills this in' },
    { key: 'honeypot_purge_days', type: 'int', value: 1, default: 1, help: 'days of the banned account’s messages to delete with it, 0 to 7', max: 7 },
    { key: 'honeypot_exempt_role_ids', type: 'roles', value: ['900000000000000001'], default: [], help: 'roles the trap ignores; staff are always ignored too' },
    { key: 'honeypot_log_level', type: 'enum', value: 'important', default: 'important', help: 'how much of honeypot is repeated into Discord: off, important or all', choices: ['off', 'important', 'all'] },
    { key: 'honeypot_panel_minutes', type: 'int', value: 10, default: 10, help: "minutes the /honeypot panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it", max: 60, min: 1 },
  ],
  logs: [
    { id: 39, at: minutesAgo(30), kind: 'honeypot.would_ban', feature: 'honeypot', important: false, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000005', target_name: 'spamlord99', reason: 'posted in #free-nitro-here', summary: 'posted in #free-nitro-here' },
    { id: 29, at: minutesAgo(5200), kind: 'honeypot.banned', feature: 'honeypot', important: true, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000006', target_name: 'Quiet Kid', reason: 'posted in #free-nitro-here', summary: 'posted in #free-nitro-here' },
    { id: 28, at: minutesAgo(6100), kind: 'honeypot.ban_failed', feature: 'honeypot', important: true, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000008', target_name: 'Left the server', reason: 'Missing Permissions', summary: 'Missing Permissions' },
  ],
};

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

const STATES = [
  { value: '', label: 'Everything', title: 'Every hit the trap has written down' },
  { value: 'would', label: 'Waiting on you', title: 'The trap only wrote these down — nobody is banned until you say so' },
  { value: 'done', label: 'Carried out', title: 'The trap banned them itself' },
  { value: 'failed', label: 'Could not be done', title: 'The trap tried and Discord refused' },
];

const stateOf = (row) => {
  const said = String(row.action || '');
  if (said.startsWith('would_')) return 'would';
  if (said.includes('failed')) return 'failed';
  return 'done';
};

function actionCell(row) {
  const said = String(row.action || 'logged');
  const tone = said.startsWith('would_') ? 'warn' : (said.includes('failed') ? 'danger' : 'ok');
  const mode = modeChip(row.mode);
  mode.title = row.mode === 'on'
    ? 'The trap was armed when this happened, so it acted by itself.'
    : 'The trap was only watching when this happened, so it wrote this down instead of acting.';
  return el('span', { class: 'chipbar' }, [badge(said, tone), mode]);
}

/** The one place the shadow rule is told, with the key that decides it. */
function strip(hits) {
  const waiting = hits.filter((row) => stateOf(row) === 'would').length;
  const mode = DATA.settings.find((spec) => spec.key === 'honeypot_mode').value;
  const traps = DATA.settings.find((spec) => spec.key === 'honeypot_channel_ids').value;
  const said = el('p', { class: 'today-line' });
  said.append(
    mode === 'on'
      ? 'The trap is armed — whoever posts in it is banned. '
      : (mode === 'shadow'
        ? 'The trap is in shadow: it only writes down what it would have done, and Ban now is how a shadow hit gets carried out. '
        : 'The trap is off, so nothing is watched and nothing is written down. '),
    el('a', {
      class: 'today-link',
      href: '/preview/settings.html#honeypot_mode',
      title: 'honeypot_mode on the Settings page decides this',
      'data-tone': mode === 'on' ? 'calm' : 'warn',
    }, [el('span', { class: 'dot-sm', 'data-tone': mode === 'on' ? 'ok' : 'warn' }), el('span', { text: `honeypot_mode = ${mode}` })]),
    traps.length === 0
      ? '. No trap channel exists yet, so nobody can walk into one — Run setup makes it.'
      : `. ${traps.length} trap channel${traps.length === 1 ? '' : 's'}: ${traps.map((id) => (CHANNELS.find((c) => c.id === id) || {}).name || id).map((name) => `#${name}`).join(', ')}.`,
    waiting === 0
      ? ' Nothing is waiting on a person.'
      : ` ${waiting} hit${waiting === 1 ? '' : 's'} ${waiting === 1 ? 'is' : 'are'} waiting for somebody to carry out.`,
  );
  const node = el('div', {
    class: 'today',
    'data-span': 'full',
    'data-tone': waiting === 0 ? 'calm' : 'danger',
  }, [el('span', { class: 'today-head', text: 'The trap' }), said]);
  return node;
}

async function load() {
  const banner = previewBanner({
    today: 4,
    preview: 3,
    note: 'Trap channels was one card holding one button, so Run setup is the page-head action instead.',
  });
  banner.setAttribute('data-span', 'full');

  const say = notice();
  const aside = document.getElementById('page-aside');
  if (aside) {
    aside.replaceChildren(button('Run setup', () => {
      wouldDo(say, 'POST /api/honeypot/setup — create or repair the trap channel in Discord. Safe to run twice; nobody is let into the trap by it');
    }, { tone: 'warn', small: false }));
  }

  const hits = section('Hits', null, { count: DATA.hits.length, open: true });
  const results = el('div');
  const chips = el('div', { class: 'chipbar' });

  const paint = (pick) => {
    const rows = pick === '' ? DATA.hits : DATA.hits.filter((row) => stateOf(row) === pick);
    results.replaceChildren(table([
      { label: 'When', cell: (row) => when(row.at), className: 'mono' },
      { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
      { label: 'Trap', cell: (row) => nameNode(row.channel_id, row.channel_name) },
      {
        label: 'What happened',
        help: 'What the trap did, and whether it was armed at the time.',
        cell: (row) => actionCell(row),
      },
      { label: 'They posted', cell: (row) => row.content, className: 'wrap' },
      {
        label: '',
        cell: (row) => (stateOf(row) === 'would'
          ? button('Ban now', () => {
            wouldDo(say, `POST /api/honeypot/hits/${row.id}/ban — ban ${row.user_name} and delete honeypot_purge_days of their messages with them. It cannot be undone from here — an unban is a moderation action`);
          }, { tone: 'danger' })
          : null),
      },
    ], rows, { empty: 'Nobody has walked into a trap channel.' }));
    hits.count(rows.length);
  };

  const paintChips = (pick) => {
    chips.replaceChildren(...STATES.map((one) => {
      const count = one.value === '' ? DATA.hits.length : DATA.hits.filter((row) => stateOf(row) === one.value).length;
      return el('button', {
        class: 'chip-filter',
        type: 'button',
        'aria-pressed': pick === one.value ? 'true' : 'false',
        title: one.title,
        text: `${one.label} ${count}`,
        on: {
          click: () => {
            paintChips(one.value);
            paint(one.value);
          },
        },
      });
    }));
  };
  paintChips('');
  paint('');

  hits.body.append(
    previewWas('Replaces Hits and Trap channels. The trap’s own state is the strip above; Run setup is in the page head; Mode then has moved onto the What happened cell, so a row says what was done and why in one place.'),
    el('div', { class: 'table-tools' }, [chips]),
    results,
    say,
  );

  const settingsSay = notice();
  const rows = [];
  const dock = saveBar(
    () => wouldDo(settingsSay, `PUT /api/settings/<key> — write the ${rows.filter((row) => row.dirty).length} changed honeypot key(s), one PUT each`),
    () => {
      for (const row of rows) row.reset();
      dock.say(0);
    },
    { where: 'Settings' },
  );
  const recount = () => dock.say(rows.filter((row) => row.dirty).length);
  for (const spec of DATA.settings) rows.push(await rowFor(spec, recount));
  recount();

  const settings = section('Settings', null, { count: rows.length });
  settings.body.append(
    previewWas('Replaces the Settings section. Same six keys, same shared editor — it is shut on arrival and it stays the second-last thing on the page.'),
    el('div', { class: 'settings-grid' }, rows.map((row) => row.node)),
    settingsSay,
  );

  const logs = section('Logs', 'Everything honeypot has done, whether or not it said so in Discord. Important means it acted on a member or failed.', { count: DATA.logs.length });
  logs.body.append(
    previewWas('Replaces the Logs section, unchanged — one log surface, shut by default.'),
    logsTable(DATA.logs, 'Honeypot has done nothing yet.'),
  );

  document.getElementById('dash').replaceChildren(
    banner,
    strip(DATA.hits),
    hits.node,
    settings.node,
    logs.node,
  );
}

start({ tab: 'honeypot', load });
