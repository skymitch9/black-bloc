import { api, listOf, names, refRoles, saveSetting, send, settings, settingsNamespace } from './api.js';
import { start, tabHref } from './app.js';
import { logsSection } from './logs.js';
import { modeWord } from './labels.js';
import {
  BY_DATE,
  BY_MARATHON,
  GIVE,
  NO_END,
  TAKE,
  endBody,
  fillLine,
  fillUnmatched,
  filled,
  freeMarathons,
  grantEndsWithMenu,
  heldRoles,
  menuFromHash,
  menuHash,
  noteKey,
  notTimed,
  previewBody,
  resolvedMoment,
  resultLines,
  saveBody,
  splitEvents,
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
  section,
  segment,
  settingsPanel,
  slugInput,
  table,
  textAction,
  untilWhen,
} from './ui.js';

const NEVER = 'never';
const NO_GRANTS = 'Nobody holds a role on a clock.';
const PICK_A_MEMBER = 'Pick the member this is about first.';
const PICK_A_ROLE = 'Pick the role to give them first.';
const NO_SUCH_EVENT = 'There is no event called {name} any more, so there is nothing to open.';
const BY_MARATHON_LABEL = 'A marathon';
const BY_DATE_LABEL = 'A date';
const SAVE_END = 'Save the end';
const MAKE_EVENT = 'Make the event';
const DELETE = 'Delete';
const DELETE_ASK = 'Delete {name}?';
const DELETE_YES = 'Delete it';
const NAME_FIELD = 'Name';
const DAY_FIELD = 'Day';
const TIME_FIELD = 'Time';
const BUFFER_FIELD = 'Buffer, days';
const MARATHON_FIELD = 'Marathon';
const ROLE_FIELD = 'Role';
const LABEL_FIELD = 'Label';
const REMOVE = 'Remove';
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
  focus: menuFromHash(location.hash),
  creating: false,
  panel: null,
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
const bare = (text) => plain(text).replace(/…$/, '');

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

const sayKey = (event) => `event:${event.name}`;

window.addEventListener('hashchange', () => {
  const wanted = menuFromHash(location.hash);
  if (!wanted) return;
  state.focus = wanted;
  refresh();
});

function openPanel(event, kind) {
  const same = state.panel && state.panel.name === event.name && state.panel.kind === kind;
  state.panel = same ? null : { name: event.name, kind };
  state.focus = event.name;
  refresh();
}

/** Re-read one event just before a confirm, so the number asked IS the number the pass takes. */
async function fresh(event) {
  return api(`/api/rolemenus/${encodeURIComponent(event.name)}`);
}

function marathonOptions(marathons, current, placeholder) {
  return [
    el('option', { value: '', text: placeholder }),
    ...marathons.map((one) => el('option', {
      value: String(one.id),
      text: one.label,
      selected: current !== null && String(current) === String(one.id) ? true : undefined,
    })),
  ];
}

/** When an event's roles come off: a marathon (plus a buffer), a typed date, or none. */
function endCard(event, marathons, zone) {
  const say = notice();
  const current = event.ends_source || NO_END;
  const offered = freeMarathons(marathons, event.name);
  const marathon = el('select', { class: 'input', 'data-end': 'marathon' }, marathonOptions(
    offered,
    current === BY_MARATHON ? event.ends_marathon_id : null,
    word('rolemenu_marathon_pick'),
  ));
  const buffer = el('input', {
    class: 'input',
    'data-end': 'buffer',
    type: 'number',
    min: '0',
    max: '365',
    step: '1',
    value: event.buffer_days === null || event.buffer_days === undefined ? '' : String(event.buffer_days),
    placeholder: String(event.buffer_default ?? ''),
  });
  const date = el('input', { class: 'input', type: 'date', 'data-end': 'date' });
  const time = el('input', { class: 'input', type: 'time', 'data-end': 'time' });
  const resolved = el('p', { class: 'field-help' });

  const byMarathon = el('div', { class: 'formrow' }, [field(MARATHON_FIELD, marathon), field(BUFFER_FIELD, buffer)]);
  const byDate = el('div', { class: 'formrow' }, [field(DAY_FIELD, date), field(TIME_FIELD, time)]);
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
    const body = endBody(event, picked());
    if (!body) return;
    if (body.ends_source === NO_END) {
      const sure = await ask({
        title: word('rolemenu_no_end_button'),
        body: [el('p', { class: 'ask-body' }, boldParts(word('rolemenu_no_end_question', { menu: event.title })))],
        confirmLabel: word('rolemenu_no_end_yes'),
        tone: 'warn',
      });
      if (!sure) return;
    }
    const done = await run(
      say,
      () => send(`/api/rolemenus/${encodeURIComponent(event.name)}`, 'PUT', body),
      (found) => `${found?.title || event.title}: ${found?.end_label || ''}`,
    );
    if (done.ok) {
      keepSaying(sayKey(event), say);
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
    save.hidden = endBody(event, now) === null;
  }
  for (const control of [marathon, buffer, date, time]) {
    control.addEventListener('input', paint);
    control.addEventListener('change', paint);
  }
  const node = el('div', { class: 'end-card' }, [how, byMarathon, byDate, resolved, bar([save]), say]);
  paint();
  return node;
}

function attachRow(event, marathons, say) {
  const offered = freeMarathons(marathons);
  if (!event.can_attach || offered.length === 0) return null;
  const pick = el('select', { class: 'input' }, marathonOptions(offered, null, word('rolemenu_marathon_pick')));
  const go = button(bare(word('rolemenu_attach_button')), async () => {
    if (!pick.value) return;
    const done = await run(
      say,
      () => send(`/api/rolemenus/${encodeURIComponent(event.name)}/attach`, 'POST', { marathon_id: pick.value }),
      (found) => `${found?.title || event.title}: ${found?.end_label || ''}`,
    );
    if (done.ok) {
      keepSaying(sayKey(event), say);
      refresh();
    }
  }, { tone: 'warn' });
  go.hidden = true;
  pick.addEventListener('change', () => { go.hidden = !pick.value; });
  return el('div', { class: 'formrow' }, [field(word('rolemenu_attach_button'), pick), bar([go])]);
}

function setByLine(event) {
  if (!event.ends_set_by) return null;
  const when = ago(event.ends_set_at);
  const [before, after = ''] = word('rolemenu_end_set_by_line', { when: when.text }).split('{who}');
  return el('p', { class: 'field-help', title: when.title }, [before, nameNode(event.ends_set_by), after]);
}

function lastPassLine(event) {
  if (!event.ended_at) return null;
  const when = ago(event.ended_at);
  return el('p', {
    class: 'field-help',
    title: when.title,
    text: word('rolemenu_ended_line', {
      when: when.text,
      members: event.last_pass ? event.last_pass.members : 0,
      failures: event.last_pass ? event.last_pass.failures : 0,
    }),
  });
}

function heldLine(event, say) {
  if (!event.ends_held_at || !event.open) return null;
  const take = button(word('rolemenu_use_held_button'), async () => {
    const now = await fresh(event).catch(() => event);
    const sure = await ask({
      title: word('rolemenu_use_held_button'),
      body: [el('p', { class: 'ask-body' }, boldParts(now.held_question || ''))],
      confirmLabel: word('rolemenu_use_held_yes'),
      tone: now.held_past ? 'danger' : 'warn',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/rolemenus/${encodeURIComponent(event.name)}/end-earlier`, 'POST', {}),
      (found) => `${found?.title || event.title}: ${found?.end_label || ''}`,
    );
    if (done.ok) {
      keepSaying(sayKey(event), say);
      refresh();
    }
  }, { tone: event.held_past ? 'danger' : 'warn' });
  return el('div', { class: 'bar menu-held' }, [
    notice(word('rolemenu_end_held_line', { to: event.held_label || '' }), 'warn'),
    take,
  ]);
}

function roleCounts(event) {
  const held = heldRoles(event);
  if (!held.length) return null;
  return el('div', { class: 'bar' }, held.map((one) => chipFor(one.role_id, one.label, String(one.count))));
}

async function endNow(event, say) {
  const now = await fresh(event).catch(() => event);
  const sure = await ask({
    title: plain(now.end_now_question),
    body: [],
    confirmLabel: word('rolemenu_end_now_yes'),
  });
  if (!sure) return;
  const done = await run(
    say,
    () => send(`/api/rolemenus/${encodeURIComponent(event.name)}/end-now`, 'POST', {}),
    (found) => resultLines(found).join(' '),
  );
  if (done.ok) {
    keepSaying(sayKey(event), say);
    refresh();
  }
}

async function rename(event, say) {
  const box = el('input', { class: 'input', type: 'text', value: event.title || '' });
  const sure = await ask({
    title: word('rolemenu_rename_title'),
    body: [field(word('rolemenu_event_name_label'), box)],
    confirmLabel: bare(word('rolemenu_rename_button')),
    tone: 'warn',
  });
  if (!sure || !box.value.trim() || box.value.trim() === event.title) return;
  const done = await run(
    say,
    () => send(`/api/rolemenus/${encodeURIComponent(event.name)}`, 'PUT', { title: box.value.trim() }),
    (found) => plain(word('rolemenu_event_renamed_said', { name: found?.title || box.value.trim() })),
  );
  if (done.ok) {
    keepSaying(sayKey(event), say);
    refresh();
  }
}

async function remove(event, say) {
  const sure = await ask({ title: DELETE_ASK.replace('{name}', event.title), body: [], confirmLabel: DELETE_YES });
  if (!sure) return;
  const done = await run(
    say,
    () => api(`/api/rolemenus/${encodeURIComponent(event.name)}`, { method: 'DELETE' }),
    `${event.title}: ${DELETE_YES}.`,
  );
  if (done.ok) {
    keepSaying(sayKey(event), say);
    refresh();
  }
}

/** Give from a list: a role, pasted lines and ticked members, matched before anything is written. */
function listPanel(event, timedRoles) {
  const say = notice();
  const role = el('select', { class: 'input' }, timedRoles.map((one) => el('option', { value: String(one.role_id), text: one.label })));
  const mode = segment([
    { value: GIVE, label: bare(word('rolemenu_give_button')) },
    { value: TAKE, label: bare(word('rolemenu_take_button')) },
  ], event.open ? GIVE : TAKE, { onChange: () => forget() });
  const pasted = el('textarea', { class: 'input', rows: '6', spellcheck: 'false' });
  const ticked = [];
  const tickedRow = el('div', { class: 'bar' });
  const picker = memberPicker({
    label: word('rolemenu_list_tick_label'),
    onPick: (member) => {
      if (!member || ticked.some((one) => one.id === member.id)) return;
      ticked.push(member);
      paintTicked();
      forget();
      picker.clear();
    },
  });
  const result = el('div', { class: 'list-result' });
  let preview = null;

  function paintTicked() {
    tickedRow.replaceChildren(...ticked.map((member) => button(`${member.name} ×`, () => {
      ticked.splice(ticked.indexOf(member), 1);
      paintTicked();
      forget();
    }, { tone: 'quiet' })));
  }
  function forget() {
    preview = null;
    result.replaceChildren();
  }
  for (const control of [role, pasted]) control.addEventListener('input', forget);
  role.addEventListener('change', forget);

  const check = button(word('rolemenu_list_check_button'), async () => {
    const body = previewBody({ roleId: role.value, text: pasted.value, ticked, mode: mode.readValue() });
    const done = await run(
      say,
      () => send(`/api/rolemenus/${encodeURIComponent(event.name)}/list/preview`, 'POST', body),
      '',
    );
    if (!done.ok) return;
    say.say('');
    preview = done.found;
    paintResult();
  }, { small: false });

  function paintResult() {
    const rows = preview.matched || [];
    const misses = preview.unmatched || [];
    const parts = [
      el('h4', { text: word('rolemenu_list_matched_head', { count: rows.length }) }),
      rows.length ? el('ul', { class: 'list-names' }, rows.map((one) => el('li', { 'data-note': one.note || undefined }, [
        nameNode(one.user_id, one.name),
        one.typed && !one.typed.startsWith('<@') && one.typed.toLowerCase() !== String(one.name).toLowerCase()
          ? el('span', { class: 'cell-quiet', text: ` · ${one.typed}` })
          : null,
        one.note ? el('span', { class: 'cell-quiet', text: ` · ${word(noteKey(one.note))}` }) : null,
      ]))) : null,
    ];
    if (misses.length) {
      parts.push(
        el('h4', { text: word('rolemenu_list_unmatched_head', { count: misses.length }) }),
        el('ul', { class: 'list-names', 'data-tone': 'warn' }, misses.map((one) => el('li', {}, [
          el('span', { class: 'mono', text: one.typed }),
          el('span', { class: 'cell-quiet', text: ` · ${word(noteKey(one.why))}` }),
        ]))),
      );
    }
    const count = (preview.to_save || []).length;
    if (count) {
      const key = preview.remove ? 'rolemenu_list_take_save' : 'rolemenu_list_give_save';
      parts.push(bar([button(word(key, { role: preview.role_name, count }), save, { tone: preview.remove ? 'danger' : 'warn', small: false })]));
    }
    result.replaceChildren(...parts.filter(Boolean));
  }

  async function save() {
    const done = await run(
      say,
      () => send(`/api/rolemenus/${encodeURIComponent(event.name)}/list`, 'POST', saveBody(preview)),
      (found) => plain(found?.message || ''),
    );
    if (!done.ok) return;
    keepSaying(sayKey(event), say);
    state.panel = null;
    refresh();
  }

  return card(word('rolemenu_list_title', { name: event.title }), [
    mode,
    el('div', { class: 'formrow' }, [field(ROLE_FIELD, role)]),
    el('div', { class: 'formrow' }, [field(word('rolemenu_list_paste_label'), pasted)]),
    el('div', { class: 'formrow' }, [picker.node]),
    tickedRow,
    bar([check]),
    result,
    say,
  ]);
}

/** Fill from the schedule: per part, who is matched, who is still to give, who nobody matched. */
async function fillPanel(event) {
  const say = notice();
  const body = el('div');
  const node = card(word('rolemenu_fill_title', { name: event.title }), [body, say]);
  let found;
  try {
    found = await api(`/api/rolemenus/${encodeURIComponent(event.name)}/fill`);
  } catch (error) {
    await run(say, () => Promise.reject(error), '');
    return node;
  }
  const lines = [];
  for (const line of found.lines || []) {
    const said = fillLine(line);
    lines.push(el('li', { text: word(said.key, said.values) }));
    const missed = fillUnmatched(line);
    if (missed) lines.push(el('li', { class: 'cell-quiet', text: word(missed.key, missed.values) }));
  }
  body.append(el('ul', { class: 'list-names' }, lines));
  if (found.missing > 0) {
    body.append(bar([button(word('rolemenu_fill_yes'), async () => {
      const done = await run(
        say,
        () => send(`/api/rolemenus/${encodeURIComponent(event.name)}/fill`, 'POST', {}),
        (answer) => plain(answer?.message || ''),
      );
      if (done.ok) {
        keepSaying(sayKey(event), say);
        state.panel = null;
        refresh();
      }
    }, { tone: 'warn', small: false })]));
  } else {
    body.append(el('p', { class: 'field-help', text: word('rolemenu_fill_nothing_said') }));
  }
  return node;
}

async function eventCard(event, { marathons, zone, timedRoles }) {
  const say = sayAgain(`event:${event.name}`, notice());
  const actions = [];
  if (event.open && timedRoles.length) {
    actions.push(button(word('rolemenu_list_button'), () => openPanel(event, 'list'), { small: false }));
  }
  if (event.can_fill) actions.push(button(word('rolemenu_fill_button'), () => openPanel(event, 'fill')));
  const assigned = event.assigned ? ` · ${word('rolemenu_site_assigned', { count: event.assigned })}` : '';
  const panel = state.panel && state.panel.name === event.name
    ? (state.panel.kind === 'fill' ? await fillPanel(event) : listPanel(event, timedRoles))
    : null;
  const moves = [button(bare(word('rolemenu_rename_button')), () => rename(event, say), { tone: 'quiet' })];
  if (event.open && timedRoles.length) moves.push(button(word('rolemenu_end_now_button'), () => endNow(event, say), { tone: 'danger' }));
  moves.push(button(DELETE, () => remove(event, say), { tone: 'danger' }));
  const node = card(event.title, [
    el('p', { class: 'menu-end', text: `${event.end_label}${assigned}` }),
    heldLine(event, say),
    roleCounts(event),
    setByLine(event),
    lastPassLine(event),
    panel,
    foldout(bare(word('rolemenu_set_end_button')), [endCard(event, marathons, zone), attachRow(event, marathons, say)]),
    bar(moves),
    say,
  ], { actions });
  node.setAttribute('data-menu', event.name);
  node.id = `event-${event.name}`;
  return node;
}

/** New event: a tracked marathon (one event each), or a name with a typed date. */
function newEventCard(marathons, zone) {
  const say = notice();
  const offered = freeMarathons(marathons);
  const how = segment([
    { value: BY_MARATHON, label: BY_MARATHON_LABEL },
    { value: BY_DATE, label: bare(word('rolemenu_no_marathon_button')) },
  ], offered.length ? BY_MARATHON : BY_DATE, { onChange: () => paint() });
  const marathon = el('select', { class: 'input' }, marathonOptions(offered, null, word('rolemenu_marathon_pick')));
  const name = el('input', { class: 'input', type: 'text' });
  const date = el('input', { class: 'input', type: 'date' });
  const time = el('input', { class: 'input', type: 'time' });
  const resolved = el('p', { class: 'field-help' });
  const byMarathon = el('div', { class: 'formrow' }, [field(MARATHON_FIELD, marathon)]);
  const byDate = el('div', { class: 'formrow' }, [field(DAY_FIELD, date), field(TIME_FIELD, time)]);
  const make = button(MAKE_EVENT, async () => {
    const body = how.readValue() === BY_MARATHON
      ? { title: name.value.trim(), marathon_id: marathon.value }
      : { title: name.value.trim(), ends_at: date.value ? `${date.value}${time.value ? ` ${time.value}` : ''}` : '' };
    const done = await run(
      say,
      () => send('/api/rolemenus', 'POST', body),
      (found) => plain(word('rolemenu_event_made_said', { name: found?.title || body.title })),
    );
    if (done.ok) {
      keepSaying('events', say);
      state.creating = false;
      state.focus = done.found?.name || null;
      refresh();
    }
  }, { small: false });

  function paint() {
    const byMarathonNow = how.readValue() === BY_MARATHON;
    byMarathon.hidden = !byMarathonNow;
    byDate.hidden = byMarathonNow;
    const chosen = offered.find((one) => String(one.id) === marathon.value);
    name.placeholder = byMarathonNow && chosen ? chosen.name : '';
    resolved.hidden = byMarathonNow || !date.value;
    resolved.textContent = resolvedMoment(date.value, time.value, zone);
    make.hidden = byMarathonNow ? !marathon.value : !name.value.trim();
  }
  for (const control of [marathon, name, date, time]) {
    control.addEventListener('input', paint);
    control.addEventListener('change', paint);
  }
  const node = card(word('rolemenu_new_event_title'), [
    how,
    byMarathon,
    el('div', { class: 'formrow' }, [field(word('rolemenu_event_name_label'), name)]),
    byDate,
    resolved,
    bar([make, button('Cancel', () => { state.creating = false; refresh(); }, { tone: 'quiet' })]),
    say,
  ]);
  paint();
  return node;
}

async function eventsSection(events, context, say) {
  const { open, ended } = splitEvents(events);
  const one = section(word('rolemenu_events_title'), null, { id: 'events', count: open.length, open: true });
  one.body.append(bar([
    button(word('rolemenu_new_event_button'), () => {
      state.creating = !state.creating;
      refresh();
    }, { small: false }),
  ], { sticky: true }));
  if (state.creating) one.body.append(newEventCard(context.marathons, context.zone));
  if (!open.length) one.body.append(sayNothing(word('rolemenu_no_events_line')));
  for (const event of open) one.body.append(await eventCard(event, context));
  if (ended.length) {
    const cards = [];
    for (const event of ended) cards.push(await eventCard(event, context));
    one.body.append(foldout(word('rolemenu_ended_title'), cards, {
      count: ended.length,
      open: ended.some((event) => event.name === state.focus),
    }));
  }
  one.body.append(say);
  return one.node;
}

/** The one list every event shares: who wears each role, how many are assigned, add and remove. */
async function timedSection(timedRoles, roles, say) {
  const one = section(word('rolemenu_timed_roles_title'), null, { id: 'timed-list', count: timedRoles.length });
  const rows = timedRoles.map((row) => el('div', { class: 'bar timed-row' }, [
    chipFor(row.role_id, row.label),
    el('span', { class: 'cell-quiet', text: ` ${row.wearing === null ? '' : word('rolemenu_site_wearing', { count: row.wearing })}${row.assigned ? ` · ${word('rolemenu_site_assigned', { count: row.assigned })}` : ''}` }),
    button(REMOVE, async () => {
      const done = await run(
        say,
        () => api(`/api/rolemenus/timed-roles/${encodeURIComponent(row.role_id)}`, { method: 'DELETE' }),
        plain(word('rolemenu_timed_removed_said', { name: row.role_name })),
      );
      if (done.ok) {
        keepSaying('timed-list', say);
        refresh();
      }
    }, { tone: 'quiet' }),
  ]));
  const free = notTimed(roles, timedRoles).filter((role) => role.name !== '@everyone');
  const pick = el('select', { class: 'input' }, [
    el('option', { value: '', text: word('rolemenu_timed_add_pick') }),
    ...free.map((role) => el('option', { value: String(role.id), text: role.name })),
  ]);
  const label = el('input', { class: 'input', type: 'text' });
  const add = button(bare(word('rolemenu_timed_add_pick')), async () => {
    if (!pick.value) return;
    const done = await run(
      say,
      () => send('/api/rolemenus/timed-roles', 'POST', { role_id: pick.value, label: label.value.trim() || null }),
      (found) => plain(word('rolemenu_timed_added_said', { name: found?.role_name || '' })),
    );
    if (done.ok) {
      keepSaying('timed-list', say);
      refresh();
    }
  }, { tone: 'warn' });
  add.hidden = true;
  pick.addEventListener('change', () => {
    add.hidden = !pick.value;
    label.placeholder = pick.selectedOptions[0] && pick.value ? pick.selectedOptions[0].textContent : '';
  });
  one.body.append(
    timedRoles.length ? el('div', { class: 'timed-list' }, rows) : sayNothing(word('rolemenu_no_timed_roles_line')),
    el('div', { class: 'formrow' }, [field(ROLE_FIELD, pick), field(LABEL_FIELD, label), bar([add])]),
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
  if (grantEndsWithMenu(row)) {
    const until = row.expires_at ? untilWhen(row.expires_at) : null;
    return el('span', { title: until ? until.title : '' }, [
      `${bare(word('rolemenu_event_title', { name: row.ends_with_menu }))}`,
      until ? ` · ${until.text}` : '',
    ]);
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
        keepSaying('grants', say);
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
      keepSaying('grants', say);
      refresh();
    }
  }, { tone: 'danger' }));

  return el('div', { class: 'bar' }, moves);
}

/** A role on no event's list, for a while: the timed list's roles are given from an event. */
async function grantForm(say, timedRoles) {
  const picker = memberPicker({ label: 'Member' });
  const role = await roleSelect(null);
  const listed = new Set(timedRoles.map((one) => String(one.role_id)));
  for (const option of [...role.options]) if (listed.has(option.value)) option.remove();
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
      keepSaying('grants', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  return foldout('Grant another role for a while', [
    picker.node,
    el('div', { class: 'formrow' }, [
      field('Role', role),
      field('For, days', days),
      field('Reason', reason),
      bar([go]),
    ]),
  ]);
}

async function grantsSection(rows, timedRoles, say) {
  const open = rows.filter((row) => row.open).length;
  const one = section(word('rolemenu_grants_title'), null, { id: 'grants', count: open });
  one.body.append(
    table([
      { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
      { label: 'Role', cell: (row) => chipFor(row.role_id, row.role_name) },
      { label: 'Source', cell: (row) => badge(String(row.source).replace(/_/g, ' ')) },
      { label: 'Given by', cell: (row) => nameNode(row.granted_by_id, row.granted_by_name) },
      { label: 'Ends', cell: endsCell },
      { label: '', cell: (row) => grantActions(row, say) },
    ], rows, { empty: state.member ? 'No role of theirs has a clock on it.' : NO_GRANTS }),
    await grantForm(say, timedRoles),
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
  const [payload, roles, allSettings, allGrants, timedPayload, marathonPayload] = await Promise.all([
    api('/api/rolemenus'),
    refRoles(),
    settings(true),
    api('/api/roles/grants'),
    api('/api/rolemenus/timed-roles'),
    api('/api/rolemenus/marathons'),
  ]);
  const events = listOf(payload, 'rolemenus');
  const timedRoles = listOf(timedPayload, 'timed_roles');
  const marathons = listOf(marathonPayload, 'marathons');
  const grants = onlyThem(listOf(allGrants, 'grants'), 'user_id');
  roleColours = new Map((roles || []).map((role) => [String(role.id), role.color]));

  const rolemenu = settingsNamespace(allSettings, 'rolemenu');
  roleWords = new Map(rolemenu.map((spec) => [spec.key, spec]));
  await names(idsIn(events, ['ends_set_by']));

  const say = sayAgain('events', notice());
  const timedSay = sayAgain('timed-list', notice());
  const grantsSay = sayAgain('grants', notice());
  const applicationSay = sayAgain('applications', notice());

  if (state.focus && !events.some((event) => event.name === state.focus)) {
    say.say(NO_SUCH_EVENT.replace('{name}', state.focus), 'warn');
    state.focus = null;
  }

  const box = section('Settings', null, { count: rolemenu.length || null });
  box.body.append(await settingsPanel(rolemenu, {
    where: 'Settings',
    empty: 'The bot registers no timed-role settings.',
  }));

  const context = { marathons, zone: zoneOf(allSettings), timedRoles };
  const nodes = [
    memberBanner(grants),
    state.member ? null : await eventsSection(events, context, say),
    state.member ? null : await timedSection(timedRoles, roles || [], timedSay),
    await grantsSection(grants, timedRoles, grantsSay),
    box.node,
    await applicationsSection(allSettings, applicationSay),
    await logsSection('rolemenu'),
    await logsSection('applications', { title: 'Application logs' }),
  ].filter(Boolean);

  document.getElementById('dash').replaceChildren(...nodes);
  const focused = state.focus ? document.getElementById(`event-${state.focus}`) : null;
  if (focused) focused.scrollIntoView({ block: 'start' });
}

refresh = start({
  tab: 'rolemenus',
  load,
});
