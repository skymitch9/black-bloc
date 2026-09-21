/** Preview of a redesigned Automod page. Static data; no api() call lives here. */
import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  badge,
  bar,
  button,
  channelLabel,
  el,
  field,
  foldout,
  humanLabel,
  icon,
  notice,
  openDrawer,
  searchOver,
  section,
  segment,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

let refresh = () => {};

const ACTIONS = ['delete', 'warn', 'timeout'];

const minutesAgo = (minutes) => new Date(Date.now() - minutes * 60000).toISOString();

const CHANNELS = [
  { id: '800000000000000001', name: 'welcome', type: 'text', category_id: null },
  { id: '800000000000000002', name: 'general', type: 'text', category_id: null },
  { id: '800000000000000003', name: 'blackbloc-logs', type: 'text', category_id: null },
  { id: '800000000000000004', name: 'bot-log', type: 'text', category_id: null },
  { id: '800000000000000005', name: 'staff-room', type: 'text', category_id: null },
  { id: '800000000000000006', name: 'announcements', type: 'text', category_id: null },
  { id: '800000000000000007', name: 'free-nitro-here', type: 'text', category_id: null },
  { id: '800000000000000012', name: 'modmail-log', type: 'text', category_id: '800000000000000011' },
  { id: '800000000000000011', name: 'modmail', type: 'category', category_id: null },
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

/** site/mock/server.mjs RULES + RULE_HELP, verbatim. */
const DATA = {
  rules: [
    { name: 'mention_spam', help: 'how many people or roles one member may mention in the window', enabled: true, window_s: 30, threshold: 5, actions: ['delete', 'warn', 'timeout'], timeout_s: 300 },
    { name: 'slowmode', help: 'how many messages one member may post in the window', enabled: true, window_s: 4, threshold: 6, actions: [], timeout_s: 0 },
    { name: 'linkspam', help: 'how many links one member may post in the window', enabled: true, window_s: 1, threshold: 1, actions: [], timeout_s: 0 },
    { name: 'invitespam', help: 'how many Discord invites one member may post in the window', enabled: false, window_s: 30, threshold: 1, actions: ['delete', 'warn', 'timeout'], timeout_s: 600 },
    { name: 'attachmentspam', help: 'how many attachments one member may post in the window', enabled: false, window_s: 30, threshold: 5, actions: [], timeout_s: 0 },
    { name: 'caps', help: 'the percentage of shouted letters a message may contain', enabled: false, window_s: 0, threshold: 70, actions: [], timeout_s: 0 },
    { name: 'bad_words', help: 'the blocked word list', enabled: false, window_s: 0, threshold: 1, actions: [], timeout_s: 0, words: [] },
  ],
  mode: {
    key: 'automod_mode',
    type: 'enum',
    value: 'shadow',
    default: 'off',
    help: 'off, shadow (log what it would do) or on (delete, warn and time out)',
    choices: ['off', 'shadow', 'on'],
  },
  exempt: [
    { key: 'automod_exempt_role_ids', type: 'roles', value: ['900000000000000001', '900000000000000002'], default: [], help: 'roles automod ignores' },
    { key: 'automod_exempt_channel_ids', type: 'channels', value: ['800000000000000003'], default: [], help: 'channels automod never reads' },
  ],
  rest: [
    { key: 'automod_rules', type: 'json', value: null, default: null, help: 'the automod rule book; the Automod tab is what changes it' },
    { key: 'automod_warn_threshold', type: 'int', value: 8, default: 8, help: 'warnings before Black Bloc says so in the log, 0 to stop counting' },
    { key: 'automod_panel_minutes', type: 'int', value: 10, default: 10, help: "minutes the /automod panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it" },
    { key: 'automod_arm_needs_confirm', type: 'bool', value: true, default: true, help: 'true to ask a second time before automod is turned on from the panel, naming what will start happening; turning it off or back to shadow is always one press' },
  ],
  logs: [
    { id: 40, at: minutesAgo(20), kind: 'automod.would_timeout', important: true, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000005', target_name: 'spamlord99', reason: 'mention spam: 6 mentions in 30s' },
    { id: 34, at: minutesAgo(220), kind: 'web.settings.set', important: false, via: 'website', actor_id: '700000000000000001', actor_name: 'Nick', target_id: null, target_name: null, reason: 'automod_mode = shadow' },
    { id: 27, at: minutesAgo(6200), kind: 'automod.timeout', important: true, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000006', target_name: 'Quiet Kid', reason: 'caps: 82% of a 40-character message' },
    { id: 26, at: minutesAgo(7400), kind: 'automod.delete', important: true, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000007', target_name: 'Dax', reason: 'invitespam: 1 invite in 30s' },
    { id: 24, at: minutesAgo(9100), kind: 'automod.timeout', important: true, via: 'discord', actor_id: null, actor_name: null, target_id: '700000000000000005', target_name: 'spamlord99', reason: 'attachmentspam: 6 files in 30s' },
  ],
};

const GRID = 'grid-template-columns: 74px 150px 120px minmax(0, 1fr) 96px 110px 24px;';

/** Test 5: what KIND of rule this is rides on the row, with its reason in the title. */
function kindChip(rule) {
  const word = Array.isArray(rule.words) ? 'word list' : rule.window_s === 0 ? 'percentage' : 'burst';
  const chip = badge(word, word === 'burst' ? null : 'warn');
  chip.setAttribute('title', rule.help);
  return chip;
}

/** The sentence page-automod.js:59 writes after a save, drawn before one. */
function ruleWord(rule) {
  return `${rule.name} is ${rule.enabled ? 'on' : 'off'}, ${rule.threshold} in ${rule.window_s}s, `
    + `doing ${rule.actions.join(', ') || 'nothing'}.`;
}

/** page-automod.js:31–78, unchanged except that every write is a note. */
function ruleEditor(rule) {
  const say = notice();
  const enabled = el('input', { class: 'input switch', type: 'checkbox', checked: rule.enabled ? true : undefined });
  const window = el('input', { class: 'input', type: 'number', min: '0', max: '3600', value: String(rule.window_s ?? 0) });
  const threshold = el('input', { class: 'input', type: 'number', min: '0', max: '1000', value: String(rule.threshold ?? 0) });
  const timeout = el('input', { class: 'input', type: 'number', min: '0', value: String(rule.timeout_s ?? 0) });
  const boxes = ACTIONS.map((action) => {
    const box = el('input', {
      class: 'input switch',
      type: 'checkbox',
      checked: (rule.actions || []).includes(action) ? true : undefined,
    });
    return { action, box, node: field(action, box) };
  });
  const words = Array.isArray(rule.words)
    ? el('textarea', { class: 'input area mono', rows: '4', spellcheck: 'false' })
    : null;
  if (words) words.value = (rule.words || []).join('\n');

  const save = button('Save rule', () => {
    wouldDo(say, `PUT /api/mod/rules/${rule.name} — save ${rule.name} and redraw its row`);
  });

  return [
    el('p', { class: 'field-help', text: rule.help }),
    el('div', { class: 'formrow' }, [
      field('Enabled', enabled),
      field('Window, seconds', window),
      field('Threshold', threshold),
      field('Timeout, seconds', timeout),
    ]),
    el('div', { class: 'formrow' }, boxes.map((one) => one.node)),
    words ? field('Blocked words, one per line', words) : null,
    bar([save]),
    say,
  ].filter(Boolean);
}

/** page-moderation.js:144 — the row IS the button, and the chevron says there is more. */
function ruleRow(rule) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: GRID,
    'data-search': `${rule.name} ${rule.help} ${rule.actions.join(' ')}`.toLowerCase(),
    on: { click: () => openDrawer(rule.name, ruleEditor(rule)) },
  }, [
    badge(rule.enabled ? 'on' : 'off', rule.enabled ? 'ok' : null),
    el('span', { class: 'cell-name', text: rule.name }),
    kindChip(rule),
    el('span', { class: 'cell-reason', text: ruleWord(rule) }),
    el('span', { class: 'cell-quiet', title: 'Window, seconds', text: `${rule.window_s}s` }),
    el('span', { class: 'cell-quiet', title: 'Timeout, seconds', text: `${rule.timeout_s}s` }),
    icon('chevronRight', 16),
  ]);
}

/** A settings row that looks like ui.js:settingRow and saves nothing. */
function staticRow(spec) {
  const control = () => {
    if (spec.type === 'enum') {
      return segment(spec.choices.map((one) => ({ value: one, label: one })), spec.value, {
        onChange: () => wouldDo(say, `PUT /api/settings/${spec.key} — save the new value`),
      });
    }
    if (spec.type === 'bool') {
      const box = el('input', { class: 'input switch', type: 'checkbox', checked: spec.value ? true : undefined });
      box.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — save the new value`));
      return box;
    }
    if (spec.type === 'roles' || spec.type === 'channels' || spec.type === 'role' || spec.type === 'channel') {
      const many = spec.type.endsWith('s');
      const held = new Set((Array.isArray(spec.value) ? spec.value : [spec.value]).filter(Boolean).map(String));
      const select = el('select', { class: 'input', multiple: many ? true : undefined, size: many ? '4' : undefined });
      if (!many) select.append(el('option', { value: '', text: 'not set' }));
      const source = spec.type.startsWith('role') ? ROLES : CHANNELS;
      for (const one of source) {
        select.append(el('option', {
          value: String(one.id),
          text: spec.type.startsWith('role') ? one.name : channelLabel(one, CHANNELS),
          selected: held.has(String(one.id)) ? true : undefined,
        }));
      }
      select.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — save the new value`));
      return select;
    }
    if (spec.type === 'json') {
      const area = el('textarea', { class: 'input area mono', rows: '3', spellcheck: 'false' });
      area.value = spec.value === null ? '' : JSON.stringify(spec.value, null, 2);
      area.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — save the new value`));
      return area;
    }
    const box = el('input', {
      class: 'input',
      type: spec.type === 'int' ? 'number' : 'text',
      value: spec.value === null || spec.value === undefined ? '' : String(spec.value),
    });
    box.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — save the new value`));
    return box;
  };
  const say = notice();
  const node = el('div', { class: 'setrow', 'data-key': spec.key, 'data-dirty': 'false' }, [
    el('div', { class: 'setrow-head' }, [
      el('span', { class: 'setrow-label', text: humanLabel(spec.key), title: spec.help || undefined }),
      el('span', { class: 'setrow-key', text: spec.key }),
    ]),
    el('div', { class: 'setrow-control' }, [control()]),
    say,
  ]);
  say.classList.add('setrow-say');
  return node;
}

function staticSettings(specs) {
  return el('div', { class: 'settings-grid' }, specs.map(staticRow));
}

async function load() {
  const banner = previewBanner({ today: 5, preview: 2 });
  banner.setAttribute('data-span', 'full');

  const modeSay = notice();
  const mode = segment(
    DATA.mode.choices.map((one) => ({ value: one, label: one })),
    DATA.mode.value,
    { onChange: () => wouldDo(modeSay, 'PUT /api/settings/automod_mode — arm, shadow or disarm automod') },
  );
  mode.setAttribute('data-key', 'automod_mode');
  mode.setAttribute('aria-label', 'Automod mode mode');
  mode.setAttribute('title', DATA.mode.help);
  const aside = document.getElementById('page-aside');
  if (aside) aside.replaceChildren(mode, modeSay);

  const book = section('Rules', 'Each rule is a burst counter: how many in how long, and what happens then.', {
    count: DATA.rules.length,
    open: true,
  });
  book.body.append(previewWas('Replaces Mode (now the switch beside the page title), Rules, Exemptions and All automod settings — four of today’s five sections.'));

  const head = el('div', { class: 'grid-row head', style: GRID }, [
    el('span', { text: 'Enabled' }),
    el('span', {}),
    el('span', {}),
    el('span', {}),
    el('span', { title: 'Window, seconds', text: 'Window' }),
    el('span', { title: 'Timeout, seconds', text: 'Timeout' }),
    el('span', {}),
  ]);
  const grid = el('div', { class: 'grid-table', style: 'min-width: 780px;' }, [head, ...DATA.rules.map(ruleRow)]);
  const scroll = el('div', { class: 'table-scroll' }, [grid]);
  book.body.append(
    searchOver(scroll, {
      label: 'Search the rule book',
      placeholder: 'a rule name, or what it does — spam, caps, invite',
      selector: '.grid-row:not(.head)',
      noun: 'rule(s)',
      empty: 'No rule matches what you typed.',
    }),
    scroll,
    foldout('Exemptions', [
      el('p', { class: 'section-note', text: 'Staff are always exempt on top of whatever is listed here.' }),
      staticSettings(DATA.exempt),
    ], { count: DATA.exempt.length }),
    foldout('All automod settings', [staticSettings(DATA.rest)], { count: DATA.rest.length }),
  );

  const logs = section('Logs', 'Everything this part of Black Bloc has done, whether or not it said so in Discord. '
    + 'Important means it acted on a member or failed.', { id: 'logs-automod', count: DATA.logs.length });
  logs.body.append(
    previewWas('Replaces the Logs section, unchanged — the one machinery surface that stays a place of its own.'),
    logsTable(DATA.logs, 'Automod has not done anything yet.'),
  );

  document.getElementById('dash').replaceChildren(banner, book.node, logs.node);
}

refresh = start({ tab: 'automod', load });
