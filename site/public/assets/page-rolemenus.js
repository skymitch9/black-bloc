import { api, listOf, names, refRoles, saveSetting, send, settings, settingsNamespace } from './api.js';
import { start, tabHref } from './app.js';
import { openSection } from './layout.js';
import { logsSection } from './logs.js';
import {
  ago,
  ask,
  avatar,
  badge,
  bar,
  button,
  card,
  channelSelect,
  el,
  field,
  foldout,
  idsIn,
  keepSaying,
  memberPicker,
  modeChip,
  nameNode,
  notice,
  readSelect,
  roleChip,
  roleSelect,
  run,
  sayAgain,
  sayNothing,
  searchOver,
  section,
  segment,
  settingsPanel,
  textAction,
  table,
  untilWhen,
} from './ui.js';

const MODE_KEY = 'rolemenu_mode';
const DEFAULT_CHANNEL_KEY = 'role_menu_channel_id';
const SWITCH_HELP = 'Off takes the panels down and hides the /rolemenu commands; on posts every ' +
  'menu again, and nobody loses a role either way.';
const TURNED_ON = 'On. Every menu that has a channel is posted there again, and the /rolemenu ' +
  'commands come back, within about five seconds.';
const TURNED_OFF = 'Off. The posted panels are removed and the /rolemenu commands disappear from ' +
  'Discord within about five seconds. Nobody loses a role and no menu is changed.';
const NO_KEY = 'The bot did not report a rolemenu_mode key, so this switch is not shown rather ' +
  'than guessed at.';

const SEED_BODY = 'Six menus this server expects — pronouns, playstyle, mentoring, interests, ' +
  'event-alerts and runner-status. A name you already have is left exactly as it is, options ' +
  'and all, and nothing is posted until you post it.';

const APPROVAL_HELP = 'On, picking this role asks staff first instead of handing it over.';
const EXPIRES_HELP = 'Blank means the role never runs out.';
const RETRY_HELP = 'How long after a no before they may ask again.';
const CHANNEL_POSTED = 'Saving a different channel moves the panel: the old message comes down ' +
  'and a new one goes up.';
const CHANNEL_UNPOSTED = 'This menu has no panel yet, so there is nothing to move — post it from ' +
  'Post a menu below.';

const REQUESTS_NOTE = 'What members have asked for on the menus that ask staff first. Approving ' +
  'hands the role over, tells them, and starts the clock if the menu has one.';
const TIMED_NOTE = 'Every role Black Bloc is holding a clock on. Ending one takes the role off ' +
  'now; letting it run out does the same thing on its own.';
const NO_REQUESTS = 'Nobody is waiting on staff. A menu only asks first when its Approval is on.';
const NO_DECIDED = 'Nothing has been decided yet.';
const NO_GRANTS = 'No role has a clock on it. Grant one below, or give a menu an "Expires after".';
const ASSIGN_HELP = 'The same path /rolemenu assign takes: only the roles on the menu you pick ' +
  'are touched, and a clock starts if that menu has one.';
const NO_MENU_TO_ASSIGN = 'No menu has a role on it yet, so there is nothing to hand out.';
const PICK_A_MEMBER = 'Pick the member this is about first.';
const PICK_A_ROLE = 'Pick the role to give them first.';
const A_REASON = 'Say why — they are sent exactly this.';

const APPLICATIONS_MODE_KEY = 'applications_mode';
const APPLICATIONS_NOTE = 'Forms staff write, that members fill in. Approving one hands the ' +
  'form\u2019s role over, tells the applicant, and names whoever has to do the human step after it.';
const APPLICATIONS_SWITCH = 'Off leaves /apply in Discord saying so and offering nobody a ' +
  'form, and stops the Apply buttons; shadow writes everything down but posts nothing, DMs ' +
  'nobody and hands no role over; on is the real thing.';
const NO_APPLICATION_FORMS = 'No application form exists yet. Make one below \u2014 the Twitch ' +
  'Team form is what this was built for.';
const NO_APPLICATIONS = 'Nobody is waiting on staff.';
const NO_DECIDED_APPLICATIONS = 'No application has been decided yet.';
const QUESTIONS_NOTE = 'Discord shows at most five boxes on one form, in this order.';
const FORM_NAME_HELP = 'Short, lower-case, no spaces \u2014 this is what the logs and the ' +
  '/apply panel name it by.';
const NEXT_STEP_HELP = 'The human step after an approval. The card says \u201c@owner \u2014 next ' +
  'step: \u2026\u201d and the applicant is told the same thing.';
const APPROVED_TEXT_HELP = 'What an approved applicant is DMed.';
const APPLICATION_EXPIRES_HELP = 'Blank or 0 means the role never runs out.';
const APPLICATION_RETRY_HELP = 'Blank uses applications_retry_days.';
const A_DENY_REASON = 'Say why \u2014 they are sent exactly this.';
const NO_ROLE_OPTION = 'No role \u2014 keep a list';
const ROLE_FIELD_HELP = 'Leave blank to keep a list instead of handing over a role.';
const NO_ROSTER_YET = 'Nobody is on this list yet.';
const NOT_LINKED = 'not linked';
const LEFT_THE_SERVER = 'left the server';
const A_REMOVE_REASON = 'Say why \u2014 they are sent exactly this.';
const COPIED = 'Copied. Paste it into the team page.';
const COULD_NOT_COPY = 'This browser would not let the page reach the clipboard, so nothing '
  + 'was copied. Select the lines in the table and copy them by hand.';

/** D4: the shape of one copied line. */
const ROSTER_LINE = (row) => {
  const login = row.twitch_login ? `twitch.tv/${row.twitch_login}` : 'no Twitch linked';
  const gone = row.in_server ? '' : ` (${LEFT_THE_SERVER})`;
  return `${row.user_name || row.user_id} \u2014 ${login}${gone}`;
};

const APPLICATION_TONE = {
  pending: 'warn',
  approved: 'ok',
  denied: null,
  withdrawn: null,
  removed: 'warn',
};

const STATUS_TONE = {
  pending: 'warn',
  approved: 'ok',
  denied: null,
  withdrawn: null,
  granted_by_hand: 'ok',
};

/** `rolemenus.html?member=<id>` is how a Members row hands one person over. */
function askedFor() {
  const wanted = new URLSearchParams(location.search).get('member');
  return wanted && /^\d+$/.test(wanted) ? wanted : null;
}

const state = { editing: null, creating: false, form: null, newForm: false, member: askedFor() };

let refresh = () => {};
let roleColours = new Map();

function chipFor(roleId, roleName, note = null) {
  const name = roleName || roleId;
  return roleChip(name, { color: roleColours.get(String(roleId)) ?? null, note });
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

function modeSwitch(spec) {
  const say = notice();
  const chip = modeChip(spec.value);
  let now = spec.value === 'on' ? 'on' : 'off';

  const flip = async (wanted) => {
    if (wanted === now) return;
    const done = await run(say, () => saveSetting(MODE_KEY, wanted), wanted === 'on' ? TURNED_ON : TURNED_OFF);
    if (done.ok) paint(done.found && done.found.value ? done.found.value : wanted);
  };

  const on = button('Turn on', () => flip('on'), { small: false });
  const off = button('Turn off', () => flip('off'), { small: false, tone: 'warn' });

  function paint(value) {
    now = value === 'on' ? 'on' : 'off';
    chip.textContent = now;
    chip.setAttribute('data-mode', now);
    on.disabled = now === 'on';
    off.disabled = now === 'off';
  }
  paint(spec.value);

  return card('Members picking roles', [
    field('Now', chip, spec.help || null),
    bar([on, off]),
    say,
  ]);
}

async function optionRow(option) {
  const role = await roleSelect(option ? option.role_id : null);
  const label = el('input', { class: 'input', type: 'text', value: option ? option.label || '' : '' });
  const emoji = el('input', { class: 'input', type: 'text', value: option ? option.emoji || '' : '', placeholder: '🔴 or <:name:id>' });
  const node = el('div', { class: 'formrow' }, [
    field('Role', role),
    field('Label', label),
    field('Emoji', emoji),
    bar([button('Remove', () => node.remove(), { tone: 'quiet' })]),
  ]);
  return {
    node,
    read: () => {
      const roleId = readSelect(role, false);
      if (!roleId) return null;
      return { role_id: roleId, label: label.value.trim() || null, emoji: emoji.value.trim() || null };
    },
  };
}

async function editor(menu) {
  const say = notice();
  const posted = Boolean(menu && menu.message_id);
  const name = el('input', { class: 'input', type: 'text', value: menu ? menu.name : '', disabled: menu ? true : undefined });
  const title = el('input', { class: 'input', type: 'text', value: menu ? menu.title || '' : '' });
  const description = el('input', { class: 'input', type: 'text', value: menu ? menu.description || '' : '' });
  const mode = el('select', { class: 'input' });
  for (const one of ['multiple', 'single', 'staff']) {
    mode.append(el('option', { value: one, text: one, selected: menu && menu.mode === one ? true : undefined }));
  }
  const approval = segment(
    [{ value: 'true', label: 'On' }, { value: 'false', label: 'Off' }],
    menu && menu.approval ? 'true' : 'false',
  );
  const expires = daysBox(menu ? menu.expires_days : null);
  const retry = daysBox(menu && menu.retry_days !== null && menu.retry_days !== undefined ? menu.retry_days : 7, { min: '1' });
  const where = await channelSelect(menu ? menu.channel_id : null);
  where.disabled = posted ? undefined : true;

  const options = [];
  const list = el('div');
  const addOption = async (option) => {
    const made = await optionRow(option);
    options.push(made);
    list.append(made.node);
  };
  for (const option of (menu && menu.options) || []) await addOption(option);
  if (!menu) await addOption(null);

  const save = button(menu ? 'Save menu' : 'Create menu', async () => {
    const body = {
      title: title.value.trim(),
      description: description.value.trim() || null,
      mode: mode.value,
      approval: approval.readValue() === 'true',
      expires_days: expires.value.trim() === '' ? 0 : Number(expires.value),
      options: options.map((one) => one.read()).filter(Boolean),
    };
    if (retry.value.trim() !== '') body.retry_days = Number(retry.value);
    if (!menu) body.name = name.value.trim();
    const moving = posted && readSelect(where, false) && readSelect(where, false) !== menu.channel_id
      ? readSelect(where, false)
      : null;
    if (moving) body.channel_id = moving;
    const done = await run(
      say,
      () => (menu
        ? send(`/api/rolemenus/${encodeURIComponent(menu.name)}`, 'PUT', body)
        : send('/api/rolemenus', 'POST', body)),
      (found) => {
        const what = found?.name || body.name || menu.name;
        const clock = body.expires_days ? ` It runs out after ${body.expires_days} days.` : '';
        if (moving) return `Saved ${what} and moved its panel — the old message is gone.${clock}`;
        return `Saved ${what} with ${body.options.length} option(s). Post it again for the change ` +
          `to show in Discord.${clock}`;
      },
    );
    if (done.ok) {
      keepSaying('menus', say);
      state.editing = null;
      state.creating = false;
      refresh();
    }
  }, { small: false });

  const close = button('Close editor', () => {
    state.editing = null;
    state.creating = false;
    refresh();
  }, { tone: 'quiet' });

  return card(menu ? `Editing ${menu.name}` : 'New menu', [
    el('div', { class: 'formrow' }, [
      field('Name', name, menu ? 'A menu keeps its name for life; make a new one to rename it.' : 'Short, no spaces — this is how the slash commands find it.'),
      field('Title', title),
      field('Description', description),
      field('Mode', mode),
    ]),
    el('div', { class: 'formrow' }, [
      field('Approval', approval, APPROVAL_HELP),
      field('Expires after, days', expires, EXPIRES_HELP),
      field('Retry after, days', retry, RETRY_HELP),
      field('Channel', where, posted ? CHANNEL_POSTED : CHANNEL_UNPOSTED),
    ]),
    el('h3', { text: 'Options' }),
    list,
    bar([button('Add option', () => addOption(null), { tone: 'quiet' })]),
    say,
  ], { actions: [save, close] });
}

async function postCard(menu, say) {
  const where = await channelSelect(menu.channel_id);
  return el('div', { class: 'formrow' }, [
    field('Post in', where),
    bar([
      button('Post', async () => {
        const channelId = readSelect(where, false);
        if (!channelId) {
          say.say('Pick a channel to post it in.', 'warn');
          return;
        }
        const sure = await ask({
          title: `Post ${menu.name}?`,
          body: [menu.message_id
            ? 'This posts a new message. The old one stops handing out roles once this one exists.'
            : 'This posts the menu where people can click it and get roles.'],
          confirmLabel: 'Post it',
          tone: 'warn',
        });
        if (!sure) return;
        const done = await run(say, () => send(`/api/rolemenus/${encodeURIComponent(menu.name)}/post`, 'POST', { channel_id: channelId }), 'Posted.');
        if (done.ok) {
          keepSaying('menus', say);
          refresh();
        }
      }, { tone: 'warn' }),
      button('Un-post', async () => {
        const sure = await ask({
          title: `Take ${menu.name}'s panel down?`,
          body: ['The message is deleted. The menu, its roles and everybody who already has one are untouched, and you can post it again whenever you want.'],
          confirmLabel: 'Take it down',
          tone: 'warn',
        });
        if (!sure) return;
        const done = await run(
          say,
          () => send(`/api/rolemenus/${encodeURIComponent(menu.name)}/unpost`, 'POST', {}),
          (found) => found?.message || 'The panel is down.',
        );
        if (done.ok) {
          keepSaying('menus', say);
          refresh();
        }
      }, { tone: 'quiet', disabled: !menu.message_id }),
    ]),
    menu.message_id ? null : el('p', { class: 'field-help', text: 'Nothing is posted yet, so there is nothing to take down.' }),
  ]);
}

function pendingCard(row, menu, say) {
  const clock = menu && menu.expires_days ? daysBox(menu.expires_days) : null;

  const approve = button('Approve', async () => {
    const body = {};
    if (clock) body.days = clock.value.trim() === '' ? 0 : Number(clock.value);
    const done = await run(
      say,
      () => send(`/api/rolemenus/requests/${encodeURIComponent(row.id)}/approve`, 'POST', body),
      (found) => found?.message || `Approved — ${row.user_name || row.user_id} has ${row.role_name}.`,
    );
    if (done.ok) {
      keepSaying('requests', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  const deny = button('Deny', async () => {
    const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — they are sent this' });
    const sure = await ask({
      title: `Say no to ${row.user_name || row.user_id}?`,
      body: [
        `They are DM'd the reason you type here, and told when they may ask for ${row.role_name} again.`,
        field('Reason', reason, A_REASON),
      ],
      confirmLabel: 'Deny it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/rolemenus/requests/${encodeURIComponent(row.id)}/deny`, 'POST', { reason: reason.value.trim() }),
      (found) => found?.message || `Denied, and ${row.user_name || row.user_id} has been told why.`,
    );
    if (done.ok) {
      keepSaying('requests', say);
      refresh();
    }
  }, { tone: 'danger', small: false });

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

function requestsSection(rows, menus, say) {
  const pending = rows.filter((row) => row.status === 'pending');
  const decided = rows.filter((row) => row.status !== 'pending');
  const byName = new Map(menus.map((menu) => [menu.name, menu]));
  const one = section('Requests', REQUESTS_NOTE, { count: pending.length });

  one.body.append(
    pending.length === 0
      ? sayNothing(
        state.member ? 'They are not waiting on anything.' : NO_REQUESTS,
        textAction('Open the menus', () => openSection('menus')),
      )
      : el('div', { class: 'section-body' }, pending.map((row) =>
        pendingCard(row, byName.get(row.menu_name) || null, say))),
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
  const extend = button('Extend', async () => {
    const more = daysBox(7, { min: '1' });
    const sure = await ask({
      title: `Give ${row.user_name || row.user_id} longer?`,
      body: [
        `The end date on ${row.role_name} is pushed back from where it is now, not from today.`,
        field('Days to add', more),
      ],
      confirmLabel: 'Push it back',
      tone: 'warn',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/roles/grants/${encodeURIComponent(row.id)}/extend`, 'POST', { days: Number(more.value) }),
      (found) => `Pushed back — ${row.user_name || row.user_id}'s ${row.role_name} runs out ` +
        `${untilWhen(found?.expires_at).text}.`,
    );
    if (done.ok) {
      keepSaying('timed', say);
      refresh();
    }
  }, { tone: 'quiet' });

  const end = button('End now', async () => {
    const sure = await ask({
      title: `Take ${row.role_name} off ${row.user_name || row.user_id}?`,
      body: ['The role comes off in Discord straight away and the clock is closed. Nothing is sent to them.'],
      confirmLabel: 'Take it off',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => api(`/api/roles/grants/${encodeURIComponent(row.id)}`, { method: 'DELETE' }),
      `Ended — ${row.user_name || row.user_id} does not have ${row.role_name} any more.`,
    );
    if (done.ok) {
      keepSaying('timed', say);
      refresh();
    }
  }, { tone: 'danger' });

  return el('div', { class: 'bar' }, [extend, end]);
}

async function grantForm(say) {
  const picker = memberPicker({ label: 'Member' });
  const role = await roleSelect(null);
  const days = daysBox(7, { min: '0' });
  const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — this only goes in the log' });

  const go = button('Grant it', async () => {
    if (!picker.id) {
      say.say(PICK_A_MEMBER, 'warn');
      return;
    }
    const roleId = readSelect(role, false);
    if (!roleId) {
      say.say(PICK_A_ROLE, 'warn');
      return;
    }
    const body = { user_id: picker.id, role_id: roleId, reason: reason.value.trim() || null };
    if (days.value.trim() !== '') body.days = Number(days.value);
    const done = await run(
      say,
      () => send('/api/roles/grants', 'POST', body),
      (found) => (found && found.expires_at
        ? `${found.user_name} has ${found.role_name}, and it runs out ${untilWhen(found.expires_at).text}.`
        : `${found?.user_name || picker.name} has ${found?.role_name || 'the role'}, with no end date.`),
    );
    if (done.ok) {
      keepSaying('timed', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  return card('Grant a timed role', [
    picker.node,
    el('div', { class: 'formrow' }, [
      field('Role', role),
      field('For, days', days, 'Blank means it never runs out.'),
      field('Reason', reason),
      bar([go]),
    ]),
  ]);
}

/** B7: the /rolemenu assign picker, as a form — one menu, one member, its own roles. */
function assignForm(menus, say) {
  const usable = menus.filter((menu) => (menu.options || []).length > 0);
  if (usable.length === 0) {
    return sayNothing(NO_MENU_TO_ASSIGN, textAction('Open the menus', () => openSection('menus')));
  }
  const picker = memberPicker({ label: 'Member' });
  const which = el('select', { class: 'input' }, usable.map((menu) =>
    el('option', { value: menu.name, text: `${menu.name} — ${menu.mode}` })));
  const boxes = el('div', { class: 'formrow' });

  const paint = () => {
    const menu = usable.find((one) => one.name === which.value) || usable[0];
    boxes.replaceChildren(...(menu.options || []).map((option) => {
      const box = el('input', {
        class: 'input switch',
        type: 'checkbox',
        value: String(option.role_id),
      });
      return el('label', { class: 'field' }, [box, ' ', chipFor(option.role_id, option.label)]);
    }));
  };
  which.addEventListener('change', paint);
  paint();

  const picked = () => [...boxes.querySelectorAll('input:checked')].map((box) => box.value);

  const go = (remove) => async () => {
    if (!picker.id) {
      say.say(PICK_A_MEMBER, 'warn');
      return;
    }
    const roleIds = picked();
    if (roleIds.length === 0) {
      say.say(PICK_A_ROLE, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/rolemenus/${encodeURIComponent(which.value)}/assign`, 'POST', {
        user_id: picker.id,
        role_ids: roleIds,
        remove,
      }),
      (found) => found?.message || 'Done.',
    );
    if (done.ok) {
      keepSaying('timed', say);
      refresh();
    }
  };

  return card('Hand roles out', [
    el('p', { class: 'field-help', text: ASSIGN_HELP }),
    picker.node,
    field('Menu', which),
    boxes,
    bar([
      button('Give these', go(false), { tone: 'warn', small: false }),
      button('Take these off', go(true), { tone: 'danger', small: false }),
    ]),
  ]);
}

async function timedSection(rows, menus, say) {
  const open = rows.filter((row) => row.open).length;
  const one = section('Timed roles', TIMED_NOTE, { count: open });
  one.body.append(
    table([
      { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
      { label: 'Role', cell: (row) => chipFor(row.role_id, row.role_name) },
      { label: 'Source', cell: (row) => badge(row.source) },
      { label: 'Given by', cell: (row) => nameNode(row.granted_by_id, row.granted_by_name) },
      { label: 'Ends', cell: endsCell },
      { label: '', cell: (row) => grantActions(row, say) },
    ], rows, { empty: state.member ? 'No role of theirs has a clock on it.' : NO_GRANTS }),
    assignForm(menus, say),
    await grantForm(say),
    say,
  );
  return one.node;
}

function onlyThem(rows, key) {
  return state.member ? rows.filter((row) => String(row[key]) === state.member) : rows;
}

function memberBanner(requests, grants) {
  if (!state.member) return null;
  const named = (requests.find((row) => String(row.user_id) === state.member)
    || grants.find((row) => String(row.user_id) === state.member) || {}).user_name;
  return el('p', { class: 'section-note' }, [
    el('span', { text: `Showing the requests and timed roles of ${named || `member ${state.member}`} only. ` }),
    el('a', { href: tabHref('rolemenus'), text: 'Show everybody' }),
  ]);
}

/** One question row on the form editor; position is wherever it ends up in the list. */
function questionRow(question, onMove) {
  const label = el('input', { class: 'input', type: 'text', value: question ? question.label : '' });
  const style = el('select', { class: 'input' });
  for (const one of ['short', 'long']) {
    style.append(el('option', { value: one, text: one, selected: question && question.style === one ? true : undefined }));
  }
  const required = segment(
    [{ value: 'true', label: 'Required' }, { value: 'false', label: 'Optional' }],
    question && question.required === false ? 'false' : 'true',
  );
  const placeholder = el('input', {
    class: 'input',
    type: 'text',
    value: question && question.placeholder ? question.placeholder : '',
    placeholder: 'grey hint inside the box',
  });
  const node = el('div', { class: 'formrow' }, [
    field('Question', label),
    field('Box', style),
    field('Answer', required),
    field('Hint', placeholder),
    bar([
      button('Up', () => onMove(node, -1), { tone: 'quiet' }),
      button('Down', () => onMove(node, 1), { tone: 'quiet' }),
      button('Remove', () => node.remove(), { tone: 'quiet' }),
    ]),
  ]);
  return {
    node,
    read: () => {
      const text = label.value.trim();
      if (!text) return null;
      return {
        label: text,
        style: style.value,
        required: required.readValue() === 'true',
        placeholder: placeholder.value.trim() || null,
      };
    },
  };
}

async function formEditor(form, questionsMax) {
  const say = notice();
  const name = el('input', { class: 'input', type: 'text', value: form ? form.name : '', disabled: form ? true : undefined });
  const title = el('input', { class: 'input', type: 'text', value: form ? form.title || '' : '' });
  const description = el('input', { class: 'input', type: 'text', value: form ? form.description || '' : '' });
  const role = await roleSelect(form ? form.role_id : null);
  const blankRole = role.querySelector('option[value=""]');
  if (blankRole) blankRole.textContent = NO_ROLE_OPTION;
  const channel = await channelSelect(form ? form.review_channel_id : null);
  const approver = await roleSelect(form ? form.approver_role_id : null);
  const owner = memberPicker({ label: 'Who does the next step' });
  const nextStep = el('input', { class: 'input', type: 'text', value: form && form.next_step ? form.next_step : '' });
  const approvedText = el('input', { class: 'input', type: 'text', value: form && form.approved_text ? form.approved_text : '' });
  const expires = daysBox(form ? form.expires_days : null);
  const retry = daysBox(form ? form.retry_days : null);
  const open = segment(
    [{ value: 'true', label: 'Open' }, { value: 'false', label: 'Closed' }],
    form && form.open === false ? 'false' : 'true',
  );

  const rows = [];
  const list = el('div');
  const move = (node, by) => {
    const held = [...list.children];
    const at = held.indexOf(node);
    const to = at + by;
    if (at < 0 || to < 0 || to >= held.length) return;
    list.insertBefore(by < 0 ? node : held[to], by < 0 ? held[to] : node);
  };
  const addQuestion = (question) => {
    if (list.children.length >= questionsMax) {
      say.say(`Discord shows at most ${questionsMax} boxes on one form, so no more were added.`, 'warn');
      return;
    }
    const made = questionRow(question, move);
    rows.push(made);
    list.append(made.node);
  };
  for (const question of (form && form.questions) || []) addQuestion(question);

  /** The order on screen IS the order stored, so read the DOM rather than the array. */
  const readQuestions = () => [...list.children]
    .map((node) => rows.find((one) => one.node === node))
    .filter(Boolean)
    .map((one) => one.read())
    .filter(Boolean);

  const save = button(form ? 'Save form' : 'Create form', async () => {
    const body = {
      title: title.value.trim(),
      description: description.value.trim() || null,
      role_id: readSelect(role, false) || (form ? '' : null),
      review_channel_id: readSelect(channel, false) || null,
      approver_role_id: readSelect(approver, false) || null,
      owner_user_id: owner.id || (form ? form.owner_user_id : null),
      next_step: nextStep.value.trim() || null,
      approved_text: approvedText.value.trim() || null,
      expires_days: expires.value.trim() === '' ? 0 : Number(expires.value),
      retry_days: retry.value.trim() === '' ? null : Number(retry.value),
      open: open.readValue() === 'true',
    };
    if (!form) body.name = name.value.trim();
    const done = await run(
      say,
      () => (form
        ? send(`/api/applications/forms/${encodeURIComponent(form.id)}`, 'PATCH', body)
        : send('/api/applications/forms', 'POST', body)),
      (found) => `Saved ${found?.name || body.name}.`,
    );
    if (!done.ok) return;
    const id = done.found?.id ?? (form ? form.id : null);
    if (id !== null) {
      const questions = await run(
        say,
        () => send(`/api/applications/forms/${encodeURIComponent(id)}/questions`, 'PUT', { questions: readQuestions() }),
        (found) => `Saved ${found?.name || ''} with ${(found?.questions || []).length} question(s).`,
      );
      if (!questions.ok) return;
    }
    keepSaying('applications', say);
    state.form = null;
    state.newForm = false;
    refresh();
  }, { small: false });

  const close = button('Close editor', () => {
    state.form = null;
    state.newForm = false;
    refresh();
  }, { tone: 'quiet' });

  const expiresField = field('Role lasts, days', expires, APPLICATION_EXPIRES_HELP);
  const syncRole = () => { expiresField.hidden = !readSelect(role, false); };
  role.addEventListener('change', syncRole);
  syncRole();

  return card(form ? `Editing ${form.name}` : 'New application form', [
    el('div', { class: 'formrow' }, [
      field('Name', name, form ? 'A form keeps its name for life; make a new one to rename it.' : FORM_NAME_HELP),
      field('Heading', title),
      field('Description', description),
      field('Taking applications', open),
    ]),
    el('div', { class: 'formrow' }, [
      field('Role it hands over', role, ROLE_FIELD_HELP),
      field('Cards go to', channel, 'Blank uses applications_channel_id.'),
      field('Who may decide', approver, 'Blank uses applications_approver_role_id, then staff.'),
    ]),
    owner.node,
    el('div', { class: 'formrow' }, [
      field('Next step', nextStep, NEXT_STEP_HELP),
      field('Approved message', approvedText, APPROVED_TEXT_HELP),
      expiresField,
      field('Apply again after, days', retry, APPLICATION_RETRY_HELP),
    ]),
    el('h3', { text: 'Questions' }),
    el('p', { class: 'field-help', text: QUESTIONS_NOTE }),
    list,
    bar([button('Add question', () => addQuestion(null), { tone: 'quiet' })]),
    say,
  ], { actions: [save, close] });
}

function answersList(row) {
  const found = row.answers || [];
  if (!found.length) return el('p', { class: 'field-help', text: 'They answered nothing.' });
  return el('dl', { class: 'answers' }, found.flatMap((one) => [
    el('dt', { text: one.label }),
    el('dd', { class: 'wrap', text: one.answer || '(left blank)' }),
  ]));
}

function applicationCard(row, say) {
  const approve = button('Approve', async () => {
    const done = await run(
      say,
      () => send(`/api/applications/${encodeURIComponent(row.id)}/decide`, 'POST', { status: 'approved' }),
      (found) => found?.message || `Approved — ${row.user_name || row.user_id} has the role.`,
    );
    if (done.ok) {
      keepSaying('applications', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  const deny = button('Deny', async () => {
    const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — they are sent this' });
    const sure = await ask({
      title: `Say no to ${row.user_name || row.user_id}?`,
      body: [
        'They are DM’d the reason you type here, and told when they may apply again.',
        field('Reason', reason, A_DENY_REASON),
      ],
      confirmLabel: 'Deny it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/applications/${encodeURIComponent(row.id)}/decide`, 'POST', {
        status: 'denied',
        reason: reason.value.trim(),
      }),
      (found) => found?.message || `Denied, and ${row.user_name || row.user_id} has been told why.`,
    );
    if (done.ok) {
      keepSaying('applications', say);
      refresh();
    }
  }, { tone: 'danger', small: false });

  const sent = ago(row.submitted_at);
  const head = el('div', { class: 'reqhead' }, [
    avatar(row.user_name || row.user_id, row.user_avatar),
    el('div', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: String(row.user_name || row.user_id) }),
      el('span', {
        class: 'rowlist-note',
        title: sent.title,
        text: `applied ${sent.text} · ${row.form_name || `form #${row.form_id}`}`,
      }),
    ]),
    badge(`#${row.id}`),
  ]);

  return card(null, [head, answersList(row), bar([approve, deny])]);
}

function decidedApplications(rows) {
  return table([
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Form', cell: (row) => row.form_name || `#${row.form_id}` },
    { label: 'Status', cell: (row) => badge(row.status, APPLICATION_TONE[row.status] || null) },
    { label: 'By', cell: (row) => nameNode(row.decided_by_id, row.decided_by_name) },
    {
      label: 'When',
      cell: (row) => {
        const said = ago(row.decided_at);
        return el('span', { class: 'cell-quiet', title: said.title, text: said.text });
      },
    },
    { label: 'Why not', cell: (row) => row.deny_reason, className: 'wrap' },
  ], rows, { empty: NO_DECIDED_APPLICATIONS });
}

function formsTable(forms, say) {
  return table([
    { label: 'Name', cell: (row) => el('span', { class: 'mono', text: row.name }) },
    { label: 'Heading', cell: (row) => row.title, className: 'wrap' },
    { label: 'Role', cell: (row) => (row.role_id ? chipFor(row.role_id, row.role_name) : badge('list', null)) },
    { label: 'Questions', cell: (row) => (row.questions || []).length },
    { label: 'Waiting', cell: (row) => (row.pending ? badge(String(row.pending), 'warn') : el('span', { class: 'cell-quiet', text: '0' })) },
    { label: 'Taking', cell: (row) => (row.open ? badge('open', 'ok') : badge('closed', 'warn')) },
    {
      label: 'Apply button',
      cell: (row) => (row.panel_message_id
        ? nameNode(row.panel_channel_id, row.panel_channel_name)
        : badge('not posted', 'warn')),
    },
    {
      label: '',
      cell: (row) => el('div', { class: 'bar' }, [
        button('Edit', () => {
          state.form = row.id;
          state.newForm = false;
          refresh();
        }, { tone: 'quiet' }),
        button('Delete', async () => {
          const sure = await ask({
            title: `Delete ${row.name}?`,
            body: ['The form and its questions go. Nobody loses a role they already have, and the applications already decided stay on the record.'],
            confirmLabel: 'Delete it',
          });
          if (!sure) return;
          const done = await run(
            say,
            () => api(`/api/applications/forms/${encodeURIComponent(row.id)}`, { method: 'DELETE' }),
            (found) => `Deleted ${found?.name || row.name}.`,
          );
          if (done.ok) {
            keepSaying('applications', say);
            refresh();
          }
        }, { tone: 'danger' }),
      ]),
    },
  ], forms, { empty: NO_APPLICATION_FORMS });
}

async function copyLines(lines, say) {
  const text = lines.join('\n');
  try {
    await navigator.clipboard.writeText(text);
    say.say(COPIED, 'ok');
  } catch (e) {
    say.say(COULD_NOT_COPY, 'warn');
  }
}

function rosterTable(rows, form, say) {
  return table([
    {
      label: 'Member',
      cell: (row) => el('div', { class: 'rowlist-main' }, [
        nameNode(row.user_id, row.user_name),
        row.in_server ? null : el('span', { class: 'rowlist-note', text: LEFT_THE_SERVER }),
      ]),
    },
    {
      label: 'Twitch',
      cell: (row) => (row.twitch_login
        ? el('a', {
          href: `https://twitch.tv/${row.twitch_login}`,
          target: '_blank',
          rel: 'noreferrer',
          text: `twitch.tv/${row.twitch_login}`,
        })
        : el('span', { class: 'cell-quiet', text: NOT_LINKED })),
    },
    {
      label: 'Since',
      cell: (row) => {
        const said = ago(row.decided_at);
        return el('span', { class: 'cell-quiet', title: said.title, text: said.text });
      },
    },
    { label: 'By', cell: (row) => row.decided_by_name },
    {
      label: '',
      cell: (row) => button('Take off the list', async () => {
        const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — they are sent this' });
        const sure = await ask({
          title: `Take ${row.user_name || row.user_id} off ${form.name}?`,
          body: [
            'They are DM’d the reason you type here, and told when they may apply again.',
            field('Reason', reason, A_REMOVE_REASON),
          ],
          confirmLabel: 'Take them off',
          tone: 'warn',
        });
        if (!sure) return;
        const done = await run(
          say,
          () => send(`/api/applications/${encodeURIComponent(row.application_id)}/remove`, 'POST', {
            reason: reason.value.trim(),
          }),
          (found) => found?.message || `${row.user_name || row.user_id} is off the list.`,
        );
        if (done.ok) {
          keepSaying('applications', say);
          refresh();
        }
      }, { tone: 'danger' }),
    },
  ], rows, {
    empty: NO_ROSTER_YET,
    tools: [textAction('Copy as text', () => copyLines(rows.map(ROSTER_LINE), say))],
  });
}

/** The list a no-role form keeps, fetched only when somebody opens the fold. */
function rosterFoldout(form, approved) {
  const say = notice();
  const body = el('div', { class: 'section-body' });
  const fold = foldout(`Approved for ${form.name}`, [body, say], { count: approved });
  let asked = false;
  fold.addEventListener('toggle', async () => {
    if (!fold.open || asked) return;
    asked = true;
    const rows = listOf(
      await api(`/api/applications/roster?form=${encodeURIComponent(form.id)}`),
      'roster',
    );
    const count = fold.querySelector('.sect-count');
    if (count) count.textContent = String(rows.length);
    body.replaceChildren(rosterTable(rows, form, say));
  });
  return fold;
}

async function panelCard(form, say) {
  const where = await channelSelect(form.panel_channel_id);
  return el('div', { class: 'formrow' }, [
    field('Apply button in', where),
    bar([
      button('Post it', async () => {
        const channelId = readSelect(where, false);
        if (!channelId) {
          say.say('Pick a channel to put the button in.', 'warn');
          return;
        }
        const done = await run(
          say,
          () => send(`/api/applications/forms/${encodeURIComponent(form.id)}/panel`, 'POST', { channel_id: channelId }),
          (found) => `The Apply button for ${found?.name || form.name} is up.`,
        );
        if (done.ok) {
          keepSaying('applications', say);
          refresh();
        }
      }, { tone: 'warn' }),
    ]),
  ]);
}

/** Off / shadow / on, saved the moment it is picked. */
function applicationsMode(spec) {
  const say = notice();
  let stored = spec.value === null || spec.value === undefined ? 'off' : String(spec.value);
  const picker = segment(
    (spec.choices || ['off', 'shadow', 'on']).map((one) => ({ value: one, label: one })),
    stored,
    {
      onChange: async () => {
        const wanted = picker.readValue();
        if (wanted === stored) return;
        const done = await run(say, () => saveSetting(APPLICATIONS_MODE_KEY, wanted), `Applications are ${wanted}.`);
        if (done.ok) {
          stored = wanted;
          refresh();
        } else {
          picker.setValue(stored);
        }
      },
    },
  );
  return el('div', {}, [field('Now', picker, APPLICATIONS_SWITCH), say]);
}

async function applicationsSection(allSettings, say) {
  const [forms, rows, status] = await Promise.all([
    api('/api/applications/forms'),
    api('/api/applications'),
    api('/api/applications/status'),
  ]);
  const formRows = listOf(forms, 'forms');
  const applications = onlyThem(listOf(rows, 'applications'), 'user_id');
  const waiting = applications.filter((row) => row.status === 'pending');
  const decided = applications.filter((row) => row.status !== 'pending');
  await names(idsIn(formRows, ['role_id', 'review_channel_id', 'approver_role_id', 'panel_channel_id']));

  const namespace = settingsNamespace(allSettings, 'applications');
  const mode = namespace.find((spec) => spec.key === APPLICATIONS_MODE_KEY);
  const one = section('Applications', APPLICATIONS_NOTE, { id: 'applications', count: waiting.length });

  if (mode) {
    one.body.append(card('Applications', [applicationsMode(mode)]));
  } else {
    one.body.append(sayNothing('The bot did not report an applications_mode key, so this switch is not shown rather than guessed at.'));
  }

  one.body.append(
    waiting.length === 0
      ? sayNothing(state.member ? 'They are not waiting on anything.' : NO_APPLICATIONS)
      : el('div', { class: 'section-body' }, waiting.map((row) => applicationCard(row, say))),
    foldout('Decided', [decidedApplications(decided)], { count: decided.length }),
    bar([
      button('New form', () => {
        state.newForm = true;
        state.form = null;
        refresh();
      }, { small: false }),
    ]),
    formsTable(formRows, say),
    say,
  );

  for (const form of formRows) {
    one.body.append(card(`Apply button for ${form.name}`, [await panelCard(form, say)]));
    one.body.append(rosterFoldout(
      form,
      applications.filter(
        (row) => row.status === 'approved' && String(row.form_id) === String(form.id),
      ).length,
    ));
  }

  one.body.append(await settingsPanel(namespace.filter((spec) => spec.key !== APPLICATIONS_MODE_KEY), {
    where: 'Applications',
    empty: 'The bot registers no application settings beyond the switch above.',
  }));

  if (state.newForm) {
    one.body.append(await formEditor(null, status.questions_max || 5));
  } else if (state.form) {
    const form = formRows.find((row) => row.id === state.form);
    if (form) one.body.append(await formEditor(form, status.questions_max || 5));
  }

  return one.node;
}

async function load() {
  const [payload, roles, allSettings, allRequests, allGrants] = await Promise.all([
    api('/api/rolemenus'),
    refRoles(),
    settings(true),
    api('/api/rolemenus/requests'),
    api('/api/roles/grants'),
  ]);
  const menus = listOf(payload, 'rolemenus');
  const requests = onlyThem(listOf(allRequests, 'requests'), 'user_id');
  const grants = onlyThem(listOf(allGrants, 'grants'), 'user_id');
  roleColours = new Map((roles || []).map((role) => [String(role.id), role.color]));

  const rolemenu = settingsNamespace(allSettings, 'rolemenu');
  const mode = rolemenu.find((spec) => spec.key === MODE_KEY);
  const defaultChannel = settingsNamespace(allSettings, 'core')
    .find((spec) => spec.key === DEFAULT_CHANNEL_KEY);
  const settingSpecs = (defaultChannel ? [defaultChannel] : [])
    .concat(rolemenu.filter((spec) => spec.key !== MODE_KEY));
  const optionIds = [];
  for (const menu of menus) for (const option of menu.options || []) optionIds.push(option.role_id);
  await names(idsIn(menus, ['channel_id']).concat(optionIds));

  const say = notice();
  const askSay = sayAgain('requests', notice());
  const applicationSay = sayAgain('applications', notice());
  const timedSay = sayAgain('timed', notice());

  const list = table([
    { label: 'Name', cell: (row) => el('span', { class: 'mono', text: row.name }) },
    { label: 'Title', cell: (row) => row.title, className: 'wrap' },
    { label: 'Mode', cell: (row) => badge(row.mode) },
    {
      label: 'Asks first',
      cell: (row) => (row.approval ? badge('approval', 'warn') : el('span', { class: 'cell-quiet', text: 'no' })),
    },
    {
      label: 'Runs out',
      cell: (row) => (row.expires_days
        ? `${row.expires_days} day(s)`
        : el('span', { class: 'cell-quiet', text: 'never' })),
    },
    {
      label: 'Options',
      cell: (row) => {
        const parts = [];
        (row.options || []).forEach((option, at) => {
          if (at > 0) parts.push(', ');
          parts.push(nameNode(option.role_id, option.role_name));
        });
        return parts.length ? el('span', {}, parts) : null;
      },
      className: 'wrap',
    },
    { label: 'Posted in', cell: (row) => (row.message_id ? nameNode(row.channel_id, row.channel_name) : badge('not posted', 'warn')) },
    {
      label: '',
      cell: (row) => el('div', { class: 'bar' }, [
        button('Edit', () => {
          state.editing = row.name;
          state.creating = false;
          refresh();
        }, { tone: 'quiet' }),
        button('Delete', async () => {
          const sure = await ask({
            title: `Delete ${row.name}?`,
            body: ['The menu and its options are removed. A message already posted stops working; nobody loses a role they already have.'],
            confirmLabel: 'Delete it',
          });
          if (!sure) return;
          const done = await run(say, () => api(`/api/rolemenus/${encodeURIComponent(row.name)}`, { method: 'DELETE' }), 'Deleted.');
          if (done.ok) refresh();
        }, { tone: 'danger' }),
      ]),
    },
  ], menus, { empty: 'No role menus exist yet.' });

  const one = section('Menus', null, { count: menus.length });
  one.body.append(
    bar([
      button('New menu', () => {
        state.creating = true;
        state.editing = null;
        refresh();
      }, { small: false }),
      button('Seed defaults', async () => {
        const sure = await ask({
          title: 'Create the default role menus?',
          body: [SEED_BODY],
          confirmLabel: 'Create them',
          tone: 'warn',
        });
        if (!sure) return;
        const done = await run(
          say,
          () => send('/api/rolemenus/seed', 'POST', {}),
          (found) => found?.message || 'Seeded.',
        );
        if (done.ok) {
          keepSaying('menus', say);
          refresh();
        }
      }, { small: false, tone: 'quiet' }),
    ], { sticky: true }),
    list,
    sayAgain('menus', say),
  );

  const two = section('Post a menu', 'Posting again makes a new message; the old one stops handing out roles.', {
    count: menus.length || null,
  });
  if (menus.length === 0) {
    two.body.append(sayNothing('There is no menu to post yet.'));
  } else {
    const box = el('div', { class: 'section-body' });
    for (const menu of menus) box.append(card(`Post ${menu.name}`, [await postCard(menu, say)]));
    two.body.append(
      searchOver(box, {
        label: 'Search the menus',
        placeholder: 'part of a menu name',
        noun: 'menu(s)',
        empty: 'No menu matches what you typed.',
      }),
      box,
    );
  }

  const switchboard = section('Role selection', SWITCH_HELP);
  switchboard.body.append(mode ? modeSwitch(mode) : sayNothing(NO_KEY));

  const box = section('Settings', 'Where a menu goes, who answers role requests, and who gets pinged about them.', {
    count: settingSpecs.length || null,
  });
  box.body.append(await settingsPanel(settingSpecs, {
    where: 'Settings',
    empty: 'The bot registers no role-menu settings beyond the switch above.',
  }));

  const banner = memberBanner(requests, grants);
  const nodes = [
    banner,
    switchboard.node,
    requestsSection(requests, menus, askSay),
    await timedSection(grants, menus, timedSay),
    one.node,
    two.node,
    box.node,
    await applicationsSection(allSettings, applicationSay),
    await logsSection('rolemenu'),
    await logsSection('applications', { title: 'Application logs' }),
  ].filter(Boolean);
  if (state.creating) {
    const made = section('New menu', null, { id: 'editor', open: true });
    made.body.append(await editor(null));
    nodes.push(made.node);
  } else if (state.editing) {
    const menu = menus.find((entry) => entry.name === state.editing);
    if (menu) {
      const made = section(`Editing ${menu.name}`, null, { id: 'editor', open: true });
      made.body.append(await editor(menu));
      nodes.push(made.node);
    }
  }

  document.getElementById('dash').replaceChildren(...nodes);
}

refresh = start({
  tab: 'rolemenus',
  load,
});
