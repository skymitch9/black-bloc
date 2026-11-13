import { api, listOf, names, refRoles, saveSetting, send, settings, settingsNamespace } from './api.js';
import { start, tabHref } from './app.js';
import { openSection } from './layout.js';
import { logsSection } from './logs.js';
import { modeWord } from './labels.js';
import {
  BY_DATE,
  BY_MARATHON,
  ENDS_WITH,
  NO_END,
  endBody,
  endLine,
  filled,
  grantEndsWithMenu,
  menuFromHash,
  menuHash,
  resolvedMoment,
  resultLines,
  wordsBody,
} from './rolemenus-end.js';
import {
  ago,
  ask,
  avatar,
  badge,
  bar,
  blankMeans,
  boldParts,
  button,
  capMark,
  card,
  channelSelect,
  el,
  field,
  fillTemplate,
  foldout,
  idsIn,
  keepSaying,
  memberPicker,
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
  slugInput,
  table,
  textAction,
  untilWhen,
} from './ui.js';

const NEVER = 'never';
const NO_GRANTS = 'No role has a clock on it.';
const NO_MENU_TO_ASSIGN = 'No menu has a role on it yet, so there is nothing to hand out.';
const PICK_A_MEMBER = 'Pick the member this is about first.';
const PICK_A_ROLE = 'Pick the role to give them first.';
const NO_MENUS = 'No role menus exist yet.';
const NO_MENU_MATCHES = 'No menu matches what you typed.';
const NO_SUCH_MENU = 'There is no role menu called {name} any more, so there is nothing to open.';
const BY_MARATHON_LABEL = 'A marathon';
const BY_DATE_LABEL = 'A date';
const SAVE_END = 'Save the end';
const ZONE_KEY = 'default_timezone';

const APPLICATIONS_MODE_KEY = 'applications_mode';
const NO_APPLICATION_FORMS = 'No application form exists yet. Make one below.';
const NO_APPLICATIONS = 'Nobody is waiting on staff.';
const NO_DECIDED_APPLICATIONS = 'No application has been decided yet.';
const NO_ROLE_OPTION = 'No role — keep a list';
const NO_ROSTER_YET = 'Nobody is on this list yet.';
const NOT_LINKED = 'not linked';
const LEFT_THE_SERVER = 'left the server';
const COPIED = 'Copied. Paste it into the team page.';
const COULD_NOT_COPY = 'This browser would not let the page reach the clipboard, so nothing '
  + 'was copied. Select the lines in the table and copy them by hand.';

/** D4: the shape of one copied line. */
const ROSTER_LINE = (row) => {
  const login = row.twitch_login ? `twitch.tv/${row.twitch_login}` : 'no Twitch linked';
  const gone = row.in_server ? '' : ` (${LEFT_THE_SERVER})`;
  return `${row.user_name || row.user_id} — ${login}${gone}`;
};

const APPLICATION_TONE = {
  pending: 'warn',
  approved: 'ok',
  denied: null,
  withdrawn: null,
  removed: 'warn',
};

/** `rolemenus.html?member=<id>` is how a Members row hands one person over. */
function askedFor() {
  const wanted = new URLSearchParams(location.search).get('member');
  return wanted && /^\d+$/.test(wanted) ? wanted : null;
}

const state = {
  editing: menuFromHash(location.hash),
  creating: false,
  form: null,
  newForm: false,
  member: askedFor(),
};

let refresh = () => {};
let roleColours = new Map();
let roleWords = new Map();

/** A rolemenu_* sentence as staff left it (the same words /rolemenu says), filled in. */
function word(key, values = {}) {
  const spec = roleWords.get(key);
  const shipped = spec ? String(spec.default ?? '') : key;
  const stored = spec && spec.value !== null && spec.value !== undefined ? String(spec.value) : shipped;
  return filled(stored.trim() ? stored : shipped, shipped, values, fillTemplate);
}

const plain = (text) => String(text || '').replace(/\*\*/g, '');

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

function openMenu(name) {
  if (menuFromHash(location.hash) === name) {
    state.editing = name;
    state.creating = false;
    refresh();
    return;
  }
  location.hash = menuHash(name);
}

function closeEditor() {
  state.editing = null;
  state.creating = false;
  if (location.hash) history.replaceState(null, '', `${location.pathname}${location.search}`);
  refresh();
}

window.addEventListener('hashchange', () => {
  const wanted = menuFromHash(location.hash);
  if (!wanted) return;
  state.editing = wanted;
  state.creating = false;
  refresh();
});

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

/** Words and roles; the end is its own card and its own save, so this one can never re-arm it. */
async function editor(menu) {
  const say = notice();
  const name = slugInput(el('input', { class: 'input', type: 'text', value: menu ? menu.name : '', disabled: menu ? true : undefined }));
  const title = el('input', { class: 'input', type: 'text', value: menu ? menu.title || '' : '' });
  const description = el('input', { class: 'input', type: 'text', value: menu ? menu.description || '' : '' });

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
    const body = wordsBody({
      name: menu ? undefined : name.value.trim(),
      title: title.value.trim(),
      description: description.value.trim() || null,
      options: options.filter((one) => one.node.isConnected).map((one) => one.read()).filter(Boolean),
    });
    const done = await run(
      say,
      () => (menu
        ? send(`/api/rolemenus/${encodeURIComponent(menu.name)}`, 'PUT', body)
        : send('/api/rolemenus', 'POST', body)),
      (found) => `Saved ${found?.name || body.name || menu.name} with ${body.options.length} role(s).`,
    );
    if (done.ok) {
      keepSaying('menus', say);
      if (menu) closeEditor();
      else openMenu(done.found?.name || body.name);
    }
  }, { small: false });

  return card(menu ? menu.title || menu.name : 'New menu', [
    el('div', { class: 'formrow' }, [
      field('Name', name),
      field('Title', title),
      field('Description', description),
    ]),
    el('h3', { text: 'Roles' }),
    list,
    bar([button('Add a role', () => addOption(null), { tone: 'quiet' })]),
    say,
  ], { actions: [save, button('Close editor', closeEditor, { tone: 'quiet' })] });
}

/** When a menu's roles come off: a marathon (plus a buffer), a typed date, or none. */
function endCard(menu, marathons, zone) {
  const say = notice();
  const current = menu.ends_source || NO_END;
  const marathon = el('select', { class: 'input', 'data-end': 'marathon' }, [
    el('option', { value: '', text: word('rolemenu_marathon_pick') }),
    ...marathons.map((one) => el('option', {
      value: String(one.id),
      text: one.label,
      selected: current === BY_MARATHON && String(menu.ends_marathon_id) === String(one.id) ? true : undefined,
    })),
  ]);
  const buffer = el('input', {
    class: 'input',
    'data-end': 'buffer',
    type: 'number',
    min: '0',
    max: '365',
    step: '1',
    value: menu.buffer_days === null || menu.buffer_days === undefined ? '' : String(menu.buffer_days),
    placeholder: String(menu.buffer_default ?? ''),
  });
  const date = el('input', { class: 'input', type: 'date', 'data-end': 'date' });
  const time = el('input', { class: 'input', type: 'time', 'data-end': 'time' });
  const resolved = el('p', { class: 'field-help' });

  const byMarathon = el('div', { class: 'formrow' }, [
    field('Marathon', marathon),
    field('Buffer, days', buffer),
  ]);
  const byDate = el('div', { class: 'formrow' }, [
    field('Day', date),
    field('Time', time),
  ]);
  const how = segment([
    { value: BY_MARATHON, label: BY_MARATHON_LABEL },
    { value: BY_DATE, label: BY_DATE_LABEL },
    { value: NO_END, label: word('rolemenu_no_end_button') },
  ], current, { onChange: () => paint() });

  const picked = () => ({
    how: how.readValue(),
    marathonId: marathon.value,
    buffer: buffer.value,
    date: date.value,
    time: time.value,
  });

  const save = button(SAVE_END, async () => {
    const body = endBody(menu, picked());
    if (!body) return;
    if (body.ends_source === NO_END) {
      const sure = await ask({
        title: word('rolemenu_no_end_button'),
        body: [el('p', { class: 'ask-body' }, boldParts(word('rolemenu_no_end_question', { menu: menu.name })))],
        confirmLabel: word('rolemenu_no_end_yes'),
        tone: 'warn',
      });
      if (!sure) return;
    }
    const done = await run(
      say,
      () => send(`/api/rolemenus/${encodeURIComponent(menu.name)}`, 'PUT', body),
      (found) => `${found?.name || menu.name}: ${found?.end_label || ''}`,
    );
    if (done.ok) {
      keepSaying('menus', say);
      refresh();
    }
  }, { small: false, tone: 'warn' });

  function paint() {
    const now = picked();
    byMarathon.hidden = now.how !== BY_MARATHON;
    buffer.closest('.field').hidden = !marathon.value;
    byDate.hidden = now.how !== BY_DATE;
    resolved.hidden = now.how !== BY_DATE || !date.value;
    resolved.textContent = resolvedMoment(date.value, time.value, zone);
    save.hidden = endBody(menu, now) === null;
  }
  for (const control of [marathon, buffer, date, time]) {
    control.addEventListener('input', paint);
    control.addEventListener('change', paint);
  }

  const node = card(word('rolemenu_set_end_title', { name: menu.name }), [
    el('p', { class: 'menu-end', text: endLine(menu) }),
    how,
    byMarathon,
    byDate,
    resolved,
    bar([save]),
    say,
  ]);
  paint();
  return node;
}

function setByLine(menu) {
  if (!menu.ends_set_by) return null;
  const when = ago(menu.ends_set_at);
  const [before, after = ''] = word('rolemenu_end_set_by_line', { when: when.text }).split('{who}');
  return el('p', { class: 'field-help', title: when.title }, [
    before,
    nameNode(menu.ends_set_by),
    after,
  ]);
}

function lastPassLine(menu) {
  if (!menu.ended_at) return null;
  const when = ago(menu.ended_at);
  return el('p', {
    class: 'field-help',
    title: when.title,
    text: word('rolemenu_ended_line', {
      when: when.text,
      members: menu.last_pass ? menu.last_pass.members : 0,
      failures: menu.last_pass ? menu.last_pass.failures : 0,
    }),
  });
}

function heldLine(menu, say) {
  if (!menu.ends_held_at) return null;
  const take = button(word('rolemenu_use_held_button'), async () => {
    const sure = await ask({
      title: word('rolemenu_use_held_button'),
      body: [el('p', { class: 'ask-body' }, boldParts(menu.held_question || ''))],
      confirmLabel: word('rolemenu_use_held_yes'),
      tone: menu.held_past ? 'danger' : 'warn',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/rolemenus/${encodeURIComponent(menu.name)}/end-earlier`, 'POST', {}),
      (found) => `${found?.name || menu.name}: ${found?.end_label || ''}`,
    );
    if (done.ok) {
      keepSaying('menus', say);
      refresh();
    }
  }, { tone: menu.held_past ? 'danger' : 'warn' });
  return el('div', { class: 'bar menu-held' }, [
    notice(word('rolemenu_end_held_line', { to: menu.held_label || '' }), 'warn'),
    take,
  ]);
}

function menuCard(menu, say) {
  const actions = [button('Edit', () => openMenu(menu.name), { tone: 'quiet' })];
  if ((menu.options || []).length) {
    actions.push(button(word('rolemenu_end_now_button'), async () => {
      const sure = await ask({
        title: plain(menu.end_now_question),
        body: [],
        confirmLabel: word('rolemenu_end_now_yes'),
      });
      if (!sure) return;
      const done = await run(
        say,
        () => send(`/api/rolemenus/${encodeURIComponent(menu.name)}/end-now`, 'POST', {}),
        (found) => resultLines(found).join(' '),
      );
      if (done.ok) {
        keepSaying('menus', say);
        refresh();
      }
    }, { tone: 'danger' }));
  }
  actions.push(button('Delete', async () => {
    const sure = await ask({ title: `Delete ${menu.name}?`, body: [], confirmLabel: 'Delete it' });
    if (!sure) return;
    const done = await run(
      say,
      () => api(`/api/rolemenus/${encodeURIComponent(menu.name)}`, { method: 'DELETE' }),
      `Deleted ${menu.name}.`,
    );
    if (done.ok) {
      keepSaying('menus', say);
      if (state.editing === menu.name) closeEditor();
      else refresh();
    }
  }, { tone: 'danger' }));

  const roles = (menu.options || []).map((option) => chipFor(option.role_id, option.label || option.role_name));
  const node = card(menu.title || menu.name, [
    el('p', { class: 'menu-end' }, [
      el('span', { class: 'mono', text: menu.name }),
      ` · ${endLine(menu)}`,
    ]),
    setByLine(menu),
    lastPassLine(menu),
    heldLine(menu, say),
    roles.length ? el('div', { class: 'bar' }, roles) : null,
  ], { actions });
  node.setAttribute('data-menu', menu.name);
  return node;
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
  if (grantEndsWithMenu(row)) {
    return el('span', { title: until.title }, [
      `${ENDS_WITH} `,
      el('a', { href: menuHash(row.ends_with_menu), text: row.ends_with_menu }),
      ` · ${until.text}`,
    ]);
  }
  return el('span', {
    title: until.title,
    text: until.days < 0 ? `overdue by ${Math.abs(until.days)} days` : `expires ${until.text}`,
  });
}

function grantActions(row, say) {
  if (!row.open) return null;
  const moves = [];
  if (!grantEndsWithMenu(row)) {
    moves.push(button('Extend', async () => {
      const more = daysBox(7, { min: '1' });
      const sure = await ask({
        title: `Give ${row.user_name || row.user_id} longer?`,
        body: [field('Days to add', more)],
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
    }, { tone: 'quiet' }));
  }

  moves.push(button('End now', async () => {
    const sure = await ask({
      title: `Take ${row.role_name} off ${row.user_name || row.user_id}?`,
      body: [],
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
  }, { tone: 'danger' }));

  return el('div', { class: 'bar' }, moves);
}

async function grantForm(say) {
  const picker = memberPicker({ label: 'Member' });
  const role = await roleSelect(null);
  const days = daysBox(7, { min: '0' });
  days.placeholder = NEVER;
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
      field('For, days', days),
      field('Reason', reason),
      bar([go]),
    ]),
  ]);
}

/** B7: the /rolemenu hand-out picker, as a form — one menu, one member, its own roles. */
function assignForm(menus, say) {
  const usable = menus.filter((menu) => (menu.options || []).length > 0);
  if (usable.length === 0) {
    return sayNothing(NO_MENU_TO_ASSIGN, textAction('Open the menus', () => openSection('menus')));
  }
  const picker = memberPicker({ label: 'Member' });
  const which = el('select', { class: 'input' }, usable.map((menu) =>
    el('option', { value: menu.name, text: `${menu.name} · ${menu.end_label}` })));
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
  const one = section('Timed roles', null, { count: open });
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

function memberBanner(grants) {
  if (!state.member) return null;
  const named = (grants.find((row) => String(row.user_id) === state.member) || {}).user_name;
  return el('p', { class: 'section-note' }, [
    el('span', { text: `Showing the timed roles of ${named || `member ${state.member}`} only. ` }),
    el('a', { href: tabHref('rolemenus'), text: 'Show everybody' }),
  ]);
}

function menusSection(menus, say) {
  const one = section('Menus', null, { id: 'menus', count: menus.length, open: true });
  const box = el('div', { class: 'section-body' }, menus.map((menu) => menuCard(menu, say)));
  one.body.append(
    bar([
      button('New menu', () => {
        state.creating = true;
        state.editing = null;
        refresh();
      }, { small: false }),
    ], { sticky: true }),
    menus.length === 0
      ? sayNothing(NO_MENUS)
      : searchOver(box, {
        label: 'Search the menus',
        placeholder: 'part of a menu name',
        noun: 'menu(s)',
        empty: NO_MENU_MATCHES,
      }),
    box,
    say,
  );
  return one.node;
}

function zoneOf(allSettings) {
  const specs = Object.values(allSettings || {}).flat();
  const found = specs.find((spec) => spec && spec.key === ZONE_KEY);
  return found ? String(found.value || found.default || '') : '';
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
  const name = slugInput(el('input', { class: 'input', type: 'text', value: form ? form.name : '', disabled: form ? true : undefined }), { lower: true });
  const title = el('input', { class: 'input', type: 'text', value: form ? form.title || '' : '' });
  const description = el('input', { class: 'input', type: 'text', value: form ? form.description || '' : '' });
  const role = await roleSelect(form ? form.role_id : null);
  blankMeans(role, NO_ROLE_OPTION);
  const channel = blankMeans(await channelSelect(form ? form.review_channel_id : null), 'the default channel');
  const approver = blankMeans(await roleSelect(form ? form.approver_role_id : null), 'the default approvers');
  const owner = memberPicker({ label: 'Who does the next step' });
  const nextStep = el('input', { class: 'input', type: 'text', value: form && form.next_step ? form.next_step : '' });
  const approvedText = el('input', { class: 'input', type: 'text', value: form && form.approved_text ? form.approved_text : '' });
  const expires = daysBox(form ? form.expires_days : null);
  expires.placeholder = NEVER;
  const retry = daysBox(form ? form.retry_days : null);
  retry.placeholder = 'the default';
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
  const addButton = button('Add question', () => addQuestion(null), { tone: 'quiet' });
  const questionsMark = capMark(addButton, questionsMax);
  new MutationObserver(() => questionsMark.paint(list.children.length)).observe(list, { childList: true });
  questionsMark.paint(list.children.length);
  const addQuestion = (question) => {
    if (list.children.length >= questionsMax) {
      say.say(`Discord shows at most ${questionsMax} boxes on one form, so no more were added.`, 'warn');
      return;
    }
    const made = questionRow(question, move);
    rows.push(made);
    list.append(made.node);
    questionsMark.paint(list.children.length);
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

  const expiresField = field('Role lasts, days', expires);
  const syncRole = () => { expiresField.hidden = !readSelect(role, false); };
  role.addEventListener('change', syncRole);
  syncRole();

  return card(form ? `Editing ${form.name}` : 'New application form', [
    el('div', { class: 'formrow' }, [
      field('Name', name),
      field('Heading', title),
      field('Description', description),
      field('Taking applications', open),
    ]),
    el('div', { class: 'formrow' }, [
      field('Role it hands over', role),
      field('Cards go to', channel),
      field('Who may decide', approver),
    ]),
    owner.node,
    el('div', { class: 'formrow' }, [
      field('Next step', nextStep),
      field('DM on approval', approvedText),
      expiresField,
      field('Apply again after, days', retry),
    ]),
    el('h3', { text: 'Questions' }),
    list,
    bar([addButton, questionsMark]),
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
        field('Reason', reason),
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
            field('Reason', reason),
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

/** Off / test / on, saved the moment it is picked. */
function applicationsMode(spec) {
  const say = notice();
  let stored = spec.value === null || spec.value === undefined ? 'off' : String(spec.value);
  const picker = segment(
    (spec.choices || ['off', 'shadow', 'on']).map((one) => ({ value: one, label: modeWord(one, spec.key) })),
    stored,
    {
      onChange: async () => {
        const wanted = picker.readValue();
        if (wanted === stored) return;
        const done = await run(say, () => saveSetting(APPLICATIONS_MODE_KEY, wanted), `Applications are ${modeWord(wanted, spec.key)}.`);
        if (done.ok) {
          stored = wanted;
          refresh();
        } else {
          picker.setValue(stored);
        }
      },
    },
  );
  return el('div', {}, [field('Now', picker), say]);
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
  const one = section('Applications', null, { id: 'applications', count: waiting.length });

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
  const [payload, roles, allSettings, allGrants] = await Promise.all([
    api('/api/rolemenus'),
    refRoles(),
    settings(true),
    api('/api/roles/grants'),
  ]);
  const menus = listOf(payload, 'rolemenus');
  const grants = onlyThem(listOf(allGrants, 'grants'), 'user_id');
  roleColours = new Map((roles || []).map((role) => [String(role.id), role.color]));

  const rolemenu = settingsNamespace(allSettings, 'rolemenu');
  roleWords = new Map(rolemenu.map((spec) => [spec.key, spec]));
  const optionIds = [];
  for (const menu of menus) for (const option of menu.options || []) optionIds.push(option.role_id);
  await names(idsIn(menus, ['ends_set_by']).concat(optionIds));

  const say = sayAgain('menus', notice());
  const applicationSay = sayAgain('applications', notice());
  const timedSay = sayAgain('timed', notice());

  const box = section('Settings', null, { count: rolemenu.length || null });
  box.body.append(await settingsPanel(rolemenu, {
    where: 'Settings',
    empty: 'The bot registers no role-menu settings.',
  }));

  const editing = state.editing ? menus.find((entry) => entry.name === state.editing) : null;
  if (state.editing && !editing) {
    say.say(NO_SUCH_MENU.replace('{name}', state.editing), 'warn');
    state.editing = null;
  }
  let editorNode = null;
  if (state.creating) {
    const made = section('New menu', null, { id: 'editor', open: true });
    made.body.append(await editor(null));
    editorNode = made.node;
  } else if (editing) {
    const marathons = listOf(await api('/api/rolemenus/marathons'), 'marathons');
    const made = section(`Editing ${editing.name}`, null, { id: 'editor', open: true });
    made.body.append(await editor(editing), endCard(editing, marathons, zoneOf(allSettings)));
    editorNode = made.node;
  }

  const nodes = [
    memberBanner(grants),
    editorNode,
    menusSection(menus, say),
    await timedSection(grants, menus, timedSay),
    box.node,
    await applicationsSection(allSettings, applicationSay),
    await logsSection('rolemenu'),
    await logsSection('applications', { title: 'Application logs' }),
  ].filter(Boolean);

  document.getElementById('dash').replaceChildren(...nodes);
  if (editorNode) editorNode.scrollIntoView({ block: 'start' });
}

refresh = start({
  tab: 'rolemenus',
  load,
});
