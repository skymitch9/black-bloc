import { start } from './app.js';
import {
  ago,
  avatar,
  badge,
  bar,
  button,
  card,
  channelLabel,
  el,
  field,
  foldout,
  icon,
  nameNode,
  notice,
  openDrawer,
  roleChip,
  sayNothing,
  searchField,
  section,
  segment,
  table,
  untilWhen,
} from './ui.js';
import { previewBanner, previewWas, wouldDo } from './preview.js';

const DATA = {
  "menus": [
    {
      "name": "colours",
      "title": "Pick a colour",
      "description": "One at a time.",
      "mode": "single",
      "channel_id": "800000000000000002",
      "message_id": "810000000000000001",
      "approval": false,
      "expires_days": null,
      "retry_days": 7,
      "options": [
        {
          "role_id": "900000000000000003",
          "label": "Live now",
          "emoji": "🔴",
          "position": 0
        },
        {
          "role_id": "900000000000000004",
          "label": "Birthday",
          "emoji": "🎂",
          "position": 1
        }
      ]
    },
    {
      "name": "pings",
      "title": "What should we ping you for?",
      "description": null,
      "mode": "multiple",
      "channel_id": null,
      "message_id": null,
      "approval": false,
      "expires_days": null,
      "retry_days": 7,
      "options": [
        {
          "role_id": "900000000000000005",
          "label": "Members",
          "emoji": null,
          "position": 0
        }
      ]
    },
    {
      "name": "runner-status",
      "title": "Runner status",
      "description": "Staff say yes to these, and they run out after a week.",
      "mode": "multiple",
      "channel_id": "800000000000000002",
      "message_id": "810000000000000002",
      "approval": true,
      "expires_days": 7,
      "retry_days": 7,
      "options": [
        {
          "role_id": "900000000000000003",
          "label": "Runner",
          "emoji": "🏃",
          "position": 0
        }
      ]
    }
  ],
  "requests": [
    {
      "id": 4,
      "menu_id": "3",
      "menu_name": "runner-status",
      "user_id": "700000000000000004",
      "user_name": "Moth",
      "user_avatar": null,
      "role_id": "900000000000000003",
      "role_name": "Live now",
      "requested_at": "2026-09-20T23:20:42.365Z",
      "status": "pending",
      "decided_by_id": null,
      "decided_by_name": null,
      "decided_at": null,
      "deny_reason": null
    },
    {
      "id": 3,
      "menu_id": "3",
      "menu_name": "runner-status",
      "user_id": "700000000000000007",
      "user_name": "Dax",
      "user_avatar": null,
      "role_id": "900000000000000003",
      "role_name": "Live now",
      "requested_at": "2026-09-19T22:55:42.365Z",
      "status": "pending",
      "decided_by_id": null,
      "decided_by_name": null,
      "decided_at": null,
      "deny_reason": null
    },
    {
      "id": 2,
      "menu_id": "3",
      "menu_name": "runner-status",
      "user_id": "700000000000000002",
      "user_name": "Casey",
      "user_avatar": null,
      "role_id": "900000000000000003",
      "role_name": "Live now",
      "requested_at": "2026-09-16T19:55:42.365Z",
      "status": "approved",
      "decided_by_id": "700000000000000001",
      "decided_by_name": "Nick",
      "decided_at": "2026-09-16T21:35:42.365Z",
      "deny_reason": null
    },
    {
      "id": 1,
      "menu_id": "3",
      "menu_name": "runner-status",
      "user_id": "700000000000000005",
      "user_name": "spamlord99",
      "user_avatar": null,
      "role_id": "900000000000000003",
      "role_name": "Live now",
      "requested_at": "2026-09-14T17:55:42.365Z",
      "status": "denied",
      "decided_by_id": "700000000000000002",
      "decided_by_name": "Casey",
      "decided_at": "2026-09-14T19:35:42.365Z",
      "deny_reason": "Not until the trial run is over."
    }
  ],
  "grants": [
    {
      "id": 5,
      "user_id": "700000000000000002",
      "user_name": "Casey",
      "role_id": "900000000000000001",
      "role_name": "Aunties / Uncles",
      "source": "approval",
      "granted_by_id": "700000000000000001",
      "granted_by_name": "Nick",
      "granted_at": "2026-09-16T21:35:42.365Z",
      "expires_at": "2026-09-22T23:55:42.365Z",
      "removed_at": null,
      "removed_reason": null,
      "open": true
    },
    {
      "id": 4,
      "user_id": "700000000000000003",
      "user_name": "Rivet",
      "role_id": "900000000000000003",
      "role_name": "Live now",
      "source": "staff",
      "granted_by_id": "700000000000000001",
      "granted_by_name": "Nick",
      "granted_at": "2026-09-07T02:35:42.365Z",
      "expires_at": "2026-10-19T23:55:42.365Z",
      "removed_at": null,
      "removed_reason": null,
      "open": true
    },
    {
      "id": 3,
      "user_id": "700000000000000004",
      "user_name": "Moth",
      "role_id": "900000000000000004",
      "role_name": "Birthday",
      "source": "menu",
      "granted_by_id": null,
      "granted_by_name": null,
      "granted_at": "2026-08-31T03:55:42.365Z",
      "expires_at": null,
      "removed_at": null,
      "removed_reason": null,
      "open": true
    },
    {
      "id": 2,
      "user_id": "700000000000000006",
      "user_name": "Quiet Kid",
      "role_id": "900000000000000003",
      "role_name": "Live now",
      "source": "staff",
      "granted_by_id": "700000000000000002",
      "granted_by_name": "Casey",
      "granted_at": "2026-08-24T05:15:42.365Z",
      "expires_at": "2026-09-19T23:55:42.365Z",
      "removed_at": "2026-09-20T03:55:42.365Z",
      "removed_reason": "expired",
      "open": false
    },
    {
      "id": 1,
      "user_id": "700000000000000007",
      "user_name": "Dax",
      "role_id": "900000000000000005",
      "role_name": "Members",
      "source": "manual",
      "granted_by_id": null,
      "granted_by_name": null,
      "granted_at": "2026-08-17T06:35:42.365Z",
      "expires_at": null,
      "removed_at": "2026-09-20T18:55:42.365Z",
      "removed_reason": "ended_by_staff",
      "open": false
    }
  ],
  "applications": {
    "forms": 2,
    "pending": 2,
    "status": {
      "mode": "off",
      "forms": 2,
      "open_forms": 1,
      "pending": 2,
      "questions_max": 5
    }
  },
  "settings": [
    {
      "key": "role_menu_channel_id",
      "type": "channel",
      "value": "800000000000000002",
      "default": null,
      "help": "the channel /rolemenu offers first when a menu is posted"
    },
    {
      "key": "rolemenu_approval_channel_id",
      "type": "channel",
      "value": "800000000000000005",
      "default": null,
      "help": "where a role request card is posted for staff to answer; defaults to staff_channel_id"
    },
    {
      "key": "rolemenu_approver_role_id",
      "type": "role",
      "value": null,
      "default": null,
      "help": "role mentioned when a role request needs answering"
    },
    {
      "key": "rolemenu_log_level",
      "type": "enum",
      "value": "important",
      "default": "important",
      "help": "which role menus log lines reach the Discord log channel: off, important (anything that acted on a member, or failed) or all. Every line is kept on the dashboard and in `/rolemenu logs` either way",
      "choices": [
        "off",
        "important",
        "all"
      ]
    },
    {
      "key": "rolemenu_panel_minutes",
      "type": "int",
      "value": 10,
      "default": 10,
      "help": "minutes the /rolemenu panel stays live before its buttons disable themselves; 10 by default. The 'this panel has gone quiet' footer can only be written while Discord's 15-minute interaction window is still open, so 15 or more means the buttons simply stop working with no footer to explain it"
    }
  ],
  "mode": {
    "key": "rolemenu_mode",
    "type": "enum",
    "value": "off",
    "default": "off",
    "help": "whether members can pick roles from the panels; off takes them down, on posts them again; /rolemenu itself stays either way",
    "choices": [
      "off",
      "on"
    ]
  },
  "logs": [
    {
      "id": 25,
      "at": "2026-09-15T10:35:42.366Z",
      "kind": "rolemenu.role_given",
      "actor_id": "700000000000000004",
      "target_id": "900000000000000003",
      "reason": "colours",
      "details": null,
      "actor_name": "Moth",
      "target_name": "Live now",
      "feature": "rolemenu",
      "important": false,
      "summary": "colours",
      "via": "discord"
    }
  ],
  "channels": [
    {
      "id": "800000000000000001",
      "name": "welcome",
      "type": "text",
      "category_id": null,
      "position": 0
    },
    {
      "id": "800000000000000002",
      "name": "general",
      "type": "text",
      "category_id": null,
      "position": 1
    },
    {
      "id": "800000000000000003",
      "name": "blackbloc-logs",
      "type": "text",
      "category_id": null,
      "position": 2
    },
    {
      "id": "800000000000000004",
      "name": "bot-log",
      "type": "text",
      "category_id": null,
      "position": 3
    },
    {
      "id": "800000000000000005",
      "name": "staff-room",
      "type": "text",
      "category_id": null,
      "position": 4
    },
    {
      "id": "800000000000000006",
      "name": "announcements",
      "type": "text",
      "category_id": null,
      "position": 5
    },
    {
      "id": "800000000000000007",
      "name": "free-nitro-here",
      "type": "text",
      "category_id": null,
      "position": 6
    },
    {
      "id": "800000000000000008",
      "name": "Events",
      "type": "category",
      "category_id": null,
      "position": 7
    },
    {
      "id": "800000000000000009",
      "name": "Join to create",
      "type": "voice",
      "category_id": null,
      "position": 8
    },
    {
      "id": "800000000000000010",
      "name": "casey's room",
      "type": "voice",
      "category_id": null,
      "position": 9
    },
    {
      "id": "800000000000000011",
      "name": "modmail",
      "type": "category",
      "category_id": null,
      "position": 10
    },
    {
      "id": "800000000000000012",
      "name": "modmail-log",
      "type": "text",
      "category_id": "800000000000000011",
      "position": 11
    }
  ],
  "roles": [
    {
      "id": "900000000000000001",
      "name": "Aunties / Uncles",
      "color": "#e04a6d",
      "position": 12,
      "managed": false
    },
    {
      "id": "900000000000000002",
      "name": "Leads",
      "color": "#4eefff",
      "position": 14,
      "managed": false
    },
    {
      "id": "900000000000000003",
      "name": "Live now",
      "color": "#a35bff",
      "position": 5,
      "managed": false
    },
    {
      "id": "900000000000000004",
      "name": "Birthday",
      "color": "#ffd166",
      "position": 4,
      "managed": false
    },
    {
      "id": "900000000000000005",
      "name": "Members",
      "color": "#8a8f98",
      "position": 1,
      "managed": false
    },
    {
      "id": "900000000000000006",
      "name": "Server Booster",
      "color": "#f47fff",
      "position": 9,
      "managed": true
    },
    {
      "id": "900000000000000007",
      "name": "Events",
      "color": "#8a8f98",
      "position": 2,
      "managed": false
    },
    {
      "id": "900000000000000008",
      "name": "Casey pings",
      "color": "#8a8f98",
      "position": 3,
      "managed": false
    }
  ]
};

const SWITCH_HELP = 'Off takes the panels down; on posts every '
  + 'menu again, and nobody loses a role either way.';
const SEED_BODY = 'Six menus this server expects — pronouns, playstyle, mentoring, interests, '
  + 'event-alerts and runner-status. A name you already have is left exactly as it is, options '
  + 'and all, and nothing is posted until you post it.';
const APPROVAL_HELP = 'On, picking this role asks staff first instead of handing it over.';
const EXPIRES_HELP = 'Blank means the role never runs out.';
const RETRY_HELP = 'How long after a no before they may ask again.';
const CHANNEL_POSTED = 'Saving a different channel moves the panel: the old message comes down '
  + 'and a new one goes up.';
const REQUESTS_NOTE = 'What members have asked for on the menus that ask staff first. Approving '
  + 'hands the role over, tells them, and starts the clock if the menu has one.';
const TIMED_NOTE = 'Every role Black Bloc is holding a clock on. Ending one takes the role off '
  + 'now; letting it run out does the same thing on its own.';
const NO_REQUESTS = 'Nobody is waiting on staff. A menu only asks first when its Approval is on.';
const NO_DECIDED = 'Nothing has been decided yet.';
const NO_GRANTS = 'No role has a clock on it. Grant one below, or give a menu an "Expires after".';
const ASSIGN_HELP = 'The same path /rolemenu ▸ Hand roles out… takes: only the roles on the menu you pick '
  + 'are touched, and a clock starts if that menu has one.';
const POST_AGAIN = 'Posting again makes a new message; the old one stops handing out roles.';
const NO_MENUS = 'No role menus exist yet.';
const NO_MATCH = 'No menu matches what you typed.';
const SETTINGS_NOTE = 'Where a menu goes, who answers role requests, and who gets pinged about them.';
const LOGS_NOTE = 'Everything this part of Black Bloc has done, whether or not it said so in '
  + 'Discord. Important means it acted on a member or failed.';
const NOTHING_LOGGED = 'Role menus has logged nothing at all yet.';
const NOT_POSTED = 'not posted';

const APPLICATIONS_NOTE = 'Forms staff write, that members fill in. Approving one hands the '
  + 'form’s role over, tells the applicant, and names whoever has to do the human step after it.';

const WAS_MENUS = 'Replaces four blocks: Role selection (the on/off switch), Menus, Post a menu '
  + '(one card per menu, so a menu lived in three places), and the Editing <name> section that '
  + 'was appended below both log tables.';
const WAS_REQUESTS = 'Replaces Requests — the pending cards and the Decided fold, unchanged.';
const WAS_TIMED = 'Replaces Timed roles, with Hand roles out and Grant a timed role folded away '
  + 'under the grants table instead of stacked below it.';
const WAS_MACHINERY = 'Replaces Settings, rolemenu logs and Application logs — the third leaves '
  + 'the page with Applications.';
const WAS_APPLICATIONS = 'Replaces the whole Applications section: a mode switch, pending cards, '
  + 'a decided fold, New form, a forms table, an Apply button card and a roster fold per form, '
  + 'and its own settings panel.';

const STATUS_TONE = {
  pending: 'warn',
  approved: 'ok',
  denied: null,
  withdrawn: null,
  granted_by_hand: 'ok',
};

const state = { query: '' };
let refresh = () => {};

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

const COLOURS = new Map(DATA.roles.map((role) => [String(role.id), role.color]));

function chipFor(roleId, roleName, note = null) {
  return roleChip(roleName || roleId, { color: COLOURS.get(String(roleId)) ?? null, note });
}

function channelName(id) {
  const found = DATA.channels.find((one) => String(one.id) === String(id));
  return found ? `#${found.name}` : null;
}

function channelPicker(value) {
  const select = el('select', { class: 'input' });
  select.append(el('option', { value: '', text: 'not set', selected: value ? undefined : true }));
  for (const channel of DATA.channels) {
    select.append(el('option', {
      value: String(channel.id),
      text: channelLabel(channel, DATA.channels),
      selected: String(channel.id) === String(value) || undefined,
    }));
  }
  return select;
}

function rolePicker(value) {
  const select = el('select', { class: 'input' });
  select.append(el('option', { value: '', text: 'not set', selected: value ? undefined : true }));
  for (const role of DATA.roles) {
    select.append(el('option', {
      value: String(role.id),
      text: `@${role.name}`,
      selected: String(role.id) === String(value) || undefined,
    }));
  }
  return select;
}

function daysBox(value, { min = '0' } = {}) {
  return el('input', {
    class: 'input',
    type: 'number',
    min,
    step: '1',
    value: value === null || value === undefined ? '' : String(value),
  });
}

function optionRow(option) {
  const role = rolePicker(option ? option.role_id : null);
  const label = el('input', { class: 'input', type: 'text', value: option ? option.label || '' : '' });
  const emoji = el('input', {
    class: 'input',
    type: 'text',
    value: option ? option.emoji || '' : '',
    placeholder: '🔴 or <:name:id>',
  });
  const node = el('div', { class: 'formrow' }, [
    field('Role', role),
    field('Label', label),
    field('Emoji', emoji),
    bar([button('Remove', () => node.remove(), { tone: 'quiet' })]),
  ]);
  return node;
}

/**
 * The editor AND that menu's post control, in the drawer the row opens — the
 * answer arrives over the row that asked for it, and *Post a menu* disappears.
 */
function menuDrawer(menu) {
  const say = notice();
  const posted = Boolean(menu.message_id);
  const name = el('input', { class: 'input', type: 'text', value: menu.name, disabled: true });
  const title = el('input', { class: 'input', type: 'text', value: menu.title || '' });
  const description = el('input', { class: 'input', type: 'text', value: menu.description || '' });
  const mode = el('select', { class: 'input' }, ['multiple', 'single', 'staff'].map((one) =>
    el('option', { value: one, text: one, selected: menu.mode === one || undefined })));
  const approval = segment(
    [{ value: 'true', label: 'On' }, { value: 'false', label: 'Off' }],
    menu.approval ? 'true' : 'false',
  );
  const expires = daysBox(menu.expires_days);
  const retry = daysBox(menu.retry_days === null || menu.retry_days === undefined ? 7 : menu.retry_days, { min: '1' });
  const where = channelPicker(menu.channel_id);
  const list = el('div', {}, (menu.options || []).map((option) => optionRow(option)));

  return [
    el('div', { class: 'formrow' }, [
      field('Name', name, 'A menu keeps its name for life; make a new one to rename it.'),
      field('Title', title),
      field('Description', description),
      field('Mode', mode),
    ]),
    el('div', { class: 'formrow' }, [
      field('Approval', approval, APPROVAL_HELP),
      field('Expires after, days', expires, EXPIRES_HELP),
      field('Retry after, days', retry, RETRY_HELP),
    ]),
    el('h3', { text: 'Options' }),
    list,
    bar([button('Add option', () => list.append(optionRow(null)), { tone: 'quiet' })]),
    bar([
      button('Save menu', () => wouldDo(say, `PUT /api/rolemenus/${menu.name} — save the title, the mode, the approval, the clock and every option on it`), { small: false, tone: 'warn' }),
    ]),
    card('Where it is posted', [
      field('Post in', where, posted ? CHANNEL_POSTED : POST_AGAIN),
      bar([
        button('Post', () => wouldDo(say, `POST /api/rolemenus/${menu.name}/post — put the panel in ${where.options[where.selectedIndex].text}`), { tone: 'warn' }),
        button('Un-post', () => wouldDo(say, `POST /api/rolemenus/${menu.name}/unpost — delete the panel message, leaving the menu, its roles and everybody who has one untouched`), { tone: 'quiet', disabled: !posted }),
      ]),
      posted
        ? null
        : el('p', { class: 'field-help', text: 'Nothing is posted yet, so there is nothing to take down.' }),
    ]),
    bar([
      button('Delete this menu', () => wouldDo(say, `DELETE /api/rolemenus/${menu.name} — remove the menu and its options`), { tone: 'danger' }),
    ]),
    say,
  ];
}

function newMenuDrawer() {
  const say = notice();
  const name = el('input', { class: 'input', type: 'text' });
  const title = el('input', { class: 'input', type: 'text' });
  const description = el('input', { class: 'input', type: 'text' });
  const mode = el('select', { class: 'input' }, ['multiple', 'single', 'staff'].map((one) =>
    el('option', { value: one, text: one })));
  const approval = segment([{ value: 'true', label: 'On' }, { value: 'false', label: 'Off' }], 'false');
  const expires = daysBox(null);
  const retry = daysBox(7, { min: '1' });
  const list = el('div', {}, [optionRow(null)]);
  return [
    el('div', { class: 'formrow' }, [
      field('Name', name, 'Short, no spaces — this is how the slash commands find it.'),
      field('Title', title),
      field('Description', description),
      field('Mode', mode),
    ]),
    el('div', { class: 'formrow' }, [
      field('Approval', approval, APPROVAL_HELP),
      field('Expires after, days', expires, EXPIRES_HELP),
      field('Retry after, days', retry, RETRY_HELP),
    ]),
    el('h3', { text: 'Options' }),
    list,
    bar([button('Add option', () => list.append(optionRow(null)), { tone: 'quiet' })]),
    bar([
      button('Create menu', () => wouldDo(say, `POST /api/rolemenus — make a menu called “${name.value.trim() || 'a new menu'}” with the options listed here`), { small: false, tone: 'warn' }),
    ]),
    say,
  ];
}

const COLUMNS = 'grid-template-columns: 12px 130px minmax(0, 1fr) 90px 110px 90px minmax(0, 1.1fr) 160px 24px';

function optionNames(menu) {
  const parts = [];
  (menu.options || []).forEach((option, at) => {
    if (at > 0) parts.push(', ');
    parts.push(option.label || option.role_id);
  });
  return parts.join('');
}

function menuRow(menu) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: COLUMNS,
    'data-search': `${menu.name} ${menu.title || ''} ${menu.mode} ${optionNames(menu)}`.toLowerCase(),
    on: { click: () => openDrawer(`Editing ${menu.name}`, menuDrawer(menu)) },
  }, [
    el('span', { class: 'dot-sm', 'data-tone': menu.message_id ? 'ok' : 'danger' }),
    el('span', { class: 'cell-name mono', text: menu.name }),
    el('span', { class: 'cell-reason', text: menu.title || '—' }),
    el('span', { class: 'cell-kind' }, [badge(menu.mode)]),
    el('span', { class: 'cell-kind' }, [
      menu.approval ? badge('approval', 'warn') : el('span', { class: 'cell-quiet', text: 'no' }),
    ]),
    el('span', {
      class: 'cell-quiet',
      text: menu.expires_days ? `${menu.expires_days} day(s)` : 'never',
    }),
    el('span', { class: 'cell-kind' }, (menu.options || []).map((option) =>
      chipFor(option.role_id, option.label))),
    el('span', { class: 'cell-kind' }, [
      menu.message_id
        ? badge(channelName(menu.channel_id) || 'posted', 'ok')
        : badge(NOT_POSTED, 'danger'),
    ]),
    icon('chevronRight', 16),
  ]);
}

function headRow() {
  return el('div', { class: 'grid-row head', style: COLUMNS }, [
    el('span'),
    el('span', { text: 'Name' }),
    el('span', { text: 'Title' }),
    el('span', { text: 'Mode' }),
    el('span', { text: 'Asks first' }),
    el('span', { text: 'Runs out' }),
    el('span', { text: 'Options' }),
    el('span', { text: 'Posted in' }),
    el('span'),
  ]);
}

function menusSection() {
  const say = notice();
  const rows = DATA.menus.map((menu) => ({ menu, node: menuRow(menu) }));
  const one = section('Menus', null, { count: DATA.menus.length, open: true });
  const foot = el('div', { class: 'grid-foot' });
  const grid = el('div', { class: 'grid-table', style: 'min-width: 1180px' }, [
    headRow(),
    ...rows.map((entry) => entry.node),
    foot,
  ]);
  const none = sayNothing(NO_MATCH);
  none.hidden = true;

  const paint = () => {
    let shown = 0;
    for (const entry of rows) {
      const hit = state.query === '' || (entry.node.getAttribute('data-search') || '').includes(state.query);
      entry.node.hidden = !hit;
      if (hit) shown += 1;
    }
    none.hidden = shown > 0;
    grid.hidden = shown === 0;
    foot.textContent = shown === rows.length
      ? `Showing ${rows.length} of ${rows.length} menu${rows.length === 1 ? '' : 's'}`
      : `Showing ${shown} of the ${rows.length} menu${rows.length === 1 ? '' : 's'} on this page`;
  };
  const search = searchField({
    label: 'Search the menus',
    placeholder: 'part of a menu name',
    onQuery: (query) => {
      state.query = query;
      paint();
    },
  });
  paint();

  const spec = DATA.mode;
  const picker = segment(
    (spec.choices || ['off', 'on']).map((choice) => ({ value: choice, label: choice })),
    spec.value,
    { onChange: () => wouldDo(say, `PUT /api/settings/rolemenu_mode — set members picking roles to ${picker.readValue()}`) },
  );
  picker.setAttribute('aria-label', 'Members picking roles');

  one.body.append(
    previewWas(WAS_MENUS),
    field('Members picking roles', picker, SWITCH_HELP),
    card(null, [
      el('div', { class: 'card-head' }, [
        search,
        bar([
          button('Seed defaults', () => wouldDo(say, `POST /api/rolemenus/seed — ${SEED_BODY}`), { tone: 'quiet' }),
        ]),
      ]),
      DATA.menus.length === 0
        ? sayNothing(NO_MENUS)
        : el('div', { class: 'table-scroll' }, [grid]),
      none,
    ]),
    say,
  );
  return one.node;
}

function pendingCard(row, say) {
  const menu = DATA.menus.find((one) => one.name === row.menu_name) || null;
  const clock = menu && menu.expires_days ? daysBox(menu.expires_days) : null;
  const approve = button('Approve', () => wouldDo(say, `POST /api/rolemenus/requests/${row.id}/approve — hand ${row.role_name} to ${row.user_name}, tell them, and start the clock if the menu has one`), { tone: 'warn', small: false });
  const deny = button('Deny', () => wouldDo(say, `POST /api/rolemenus/requests/${row.id}/deny — say no to ${row.user_name}, DM them the reason, and tell them when they may ask again`), { tone: 'danger', small: false });
  const asked = ago(row.requested_at);
  const head = el('div', { class: 'reqhead' }, [
    avatar(row.user_name || row.user_id, row.user_avatar),
    el('div', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: String(row.user_name || row.user_id) }),
      el('span', {
        class: 'rowlist-note',
        title: asked.title,
        text: `asked ${asked.text} · ${row.menu_name || `menu #${row.menu_id}`}`,
      }),
    ]),
    chipFor(row.role_id, row.role_name),
  ]);
  const controls = clock
    ? el('div', { class: 'formrow' }, [
      field('Give it for, days', clock, 'Blank or 0 hands it over with no end date.'),
      bar([approve, deny]),
    ])
    : bar([approve, deny]);
  return card(null, [head, controls]);
}

function decidedTable(rows) {
  return table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Role', cell: (row) => chipFor(row.role_id, row.role_name) },
    { label: 'Menu', cell: (row) => row.menu_name || `#${row.menu_id}` },
    { label: 'Status', cell: (row) => badge(row.status.replace(/_/g, ' '), STATUS_TONE[row.status] || null) },
    { label: 'By', cell: (row) => nameNode(row.decided_by_id, row.decided_by_name) },
    {
      label: 'When',
      cell: (row) => {
        const said = ago(row.decided_at);
        return el('span', { class: 'cell-quiet', title: said.title, text: said.text });
      },
    },
    { label: 'Why not', cell: (row) => row.deny_reason, className: 'wrap' },
  ], rows, { empty: NO_DECIDED });
}

function requestsSection() {
  const say = notice();
  const pending = DATA.requests.filter((row) => row.status === 'pending');
  const decided = DATA.requests.filter((row) => row.status !== 'pending');
  const one = section('Requests', REQUESTS_NOTE, { count: pending.length });
  one.body.append(
    previewWas(WAS_REQUESTS),
    pending.length === 0
      ? sayNothing(NO_REQUESTS)
      : el('div', { class: 'section-body' }, pending.map((row) => pendingCard(row, say))),
    foldout('Decided', [decidedTable(decided)], { count: decided.length }),
    say,
  );
  return one.node;
}

function endsCell(row) {
  if (!row.open) {
    const gone = ago(row.removed_at);
    return el('span', {
      class: 'cell-quiet',
      title: gone.title,
      text: `ended ${gone.text}${row.removed_reason ? ` · ${String(row.removed_reason).replace(/_/g, ' ')}` : ''}`,
    });
  }
  if (!row.expires_at) return el('span', { class: 'cell-quiet', text: 'no expiry' });
  const until = untilWhen(row.expires_at);
  return el('span', {
    title: until.title,
    text: until.days < 0 ? `overdue by ${Math.abs(until.days)} days` : `expires ${until.text}`,
  });
}

function grantActions(row, say) {
  if (!row.open) return null;
  return el('div', { class: 'bar' }, [
    button('Extend', () => wouldDo(say, `POST /api/roles/grants/${row.id}/extend — push ${row.user_name}’s ${row.role_name} back from where it ends now`), { tone: 'quiet' }),
    button('End now', () => wouldDo(say, `DELETE /api/roles/grants/${row.id} — take ${row.role_name} off ${row.user_name} straight away and close the clock`), { tone: 'danger' }),
  ]);
}

function assignFold(say) {
  const usable = DATA.menus.filter((menu) => (menu.options || []).length > 0);
  const which = el('select', { class: 'input' }, usable.map((menu) =>
    el('option', { value: menu.name, text: `${menu.name} — ${menu.mode}` })));
  const boxes = el('div', { class: 'formrow' });
  const paint = () => {
    const menu = usable.find((one) => one.name === which.value) || usable[0];
    boxes.replaceChildren(...(menu.options || []).map((option) => {
      const box = el('input', { class: 'input switch', type: 'checkbox', value: String(option.role_id) });
      return el('label', { class: 'field' }, [box, ' ', chipFor(option.role_id, option.label)]);
    }));
  };
  which.addEventListener('change', paint);
  paint();
  const member = el('input', { class: 'input', type: 'search', placeholder: 'type part of a name' });
  return foldout('Hand roles out', [
    el('p', { class: 'field-help', text: ASSIGN_HELP }),
    field('Member', member, 'Names come from the bot’s own copy of the member list.'),
    field('Menu', which),
    boxes,
    bar([
      button('Give these', () => wouldDo(say, `POST /api/rolemenus/${which.value}/assign — give the ticked roles to whoever is picked`), { tone: 'warn', small: false }),
      button('Take these off', () => wouldDo(say, `POST /api/rolemenus/${which.value}/assign — take the ticked roles off whoever is picked`), { tone: 'danger', small: false }),
    ]),
  ]);
}

function grantFold(say) {
  const member = el('input', { class: 'input', type: 'search', placeholder: 'type part of a name' });
  const role = rolePicker(null);
  const days = daysBox(7, { min: '0' });
  const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — this only goes in the log' });
  return foldout('Grant a timed role', [
    field('Member', member, 'Names come from the bot’s own copy of the member list.'),
    el('div', { class: 'formrow' }, [
      field('Role', role),
      field('For, days', days, 'Blank means it never runs out.'),
      field('Reason', reason),
      bar([
        button('Grant it', () => wouldDo(say, 'POST /api/roles/grants — hand the role over and start the clock'), { tone: 'warn', small: false }),
      ]),
    ]),
  ]);
}

function timedSection() {
  const say = notice();
  const open = DATA.grants.filter((row) => row.open).length;
  const one = section('Timed roles', TIMED_NOTE, { count: open });
  one.body.append(
    previewWas(WAS_TIMED),
    table([
      { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
      { label: 'Role', cell: (row) => chipFor(row.role_id, row.role_name) },
      { label: 'Source', cell: (row) => badge(row.source) },
      { label: 'Given by', cell: (row) => nameNode(row.granted_by_id, row.granted_by_name) },
      { label: 'Ends', cell: endsCell },
      { label: '', cell: (row) => grantActions(row, say) },
    ], DATA.grants, { empty: NO_GRANTS }),
    assignFold(say),
    grantFold(say),
    say,
  );
  return one.node;
}

function settingControl(spec, say) {
  if (spec.type === 'enum') {
    const select = el('select', { class: 'input' }, (spec.choices || []).map((choice) =>
      el('option', { value: choice, text: choice, selected: String(spec.value) === String(choice) || undefined })));
    select.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${select.value}`));
    return select;
  }
  if (spec.type === 'int') {
    const input = el('input', { class: 'input', type: 'number', step: '1', value: String(spec.value) });
    input.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${input.value}`));
    return input;
  }
  const select = spec.type === 'role' ? rolePicker(spec.value) : channelPicker(spec.value);
  select.addEventListener('change', () => wouldDo(say, `PUT /api/settings/${spec.key} — set it to ${select.options[select.selectedIndex].text}`));
  return select;
}

function machinerySection() {
  const say = notice();
  const one = section('Settings and logs', 'The reference half of the page. Both are shut until '
    + 'you want them.', { id: 'machinery' });
  one.body.append(
    previewWas(WAS_MACHINERY),
    foldout('Settings', [
      el('p', { class: 'field-help', text: SETTINGS_NOTE }),
      ...DATA.settings.map((spec) => field(spec.key, settingControl(spec, say), spec.help)),
      say,
    ], { count: DATA.settings.length }),
    foldout('Logs', [
      el('p', { class: 'field-help', text: LOGS_NOTE }),
      DATA.logs.length === 0
        ? sayNothing(NOTHING_LOGGED)
        : table([
          { label: 'When', cell: (row) => el('span', { class: 'cell-quiet', title: ago(row.at).title, text: ago(row.at).text }) },
          { label: 'Kind', cell: (row) => el('span', { class: 'pill kindpill', 'data-important': row.important ? 'true' : 'false', text: row.kind }) },
          { label: 'Actor', cell: (row) => nameNode(row.actor_id, row.actor_name) },
          { label: 'Target', cell: (row) => nameNode(row.target_id, row.target_name) },
          { label: 'Summary', cell: (row) => row.summary, className: 'wrap' },
        ], DATA.logs),
    ], { count: DATA.logs.length }),
  );
  return one.node;
}

/**
 * Applications is a page, not a section (the audit's §4.18 proposal). It is a
 * line here rather than a heading, because it is not on this page any more.
 */
function applicationsLine() {
  const say = notice();
  const line = notice(
    `Applications moved to a page of its own — **${DATA.applications.forms} forms**, `
    + `**${DATA.applications.pending} waiting on staff**. ${APPLICATIONS_NOTE}`,
    'info',
  );
  return el('div', {}, [
    previewWas(WAS_APPLICATIONS),
    line,
    bar([
      button('Open Applications', () => wouldDo(say, 'GET /applications.html — open the Applications page, which this preview does not build'), { small: false }),
    ]),
    say,
  ]);
}

async function load() {
  const aside = document.getElementById('page-aside');
  if (aside) {
    aside.replaceChildren(button('New menu', () => openDrawer('New menu', newMenuDrawer()), {
      tone: 'warn',
      small: false,
    }));
  }
  document.getElementById('dash').replaceChildren(
    full(previewBanner({
      today: 9,
      preview: 4,
      note: 'Applications left for a page of its own, and a menu’s editor opens over its row.',
    })),
    full(applicationsLine()),
    full(menusSection()),
    full(requestsSection()),
    full(timedSection()),
    full(machinerySection()),
  );
}

refresh = start({ tab: 'rolemenus', load });
