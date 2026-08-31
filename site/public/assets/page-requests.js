import { api, listOf, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
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
  el,
  field,
  foldout,
  keepSaying,
  memberPicker,
  notice,
  pager,
  run,
  sayAgain,
  sayNothing,
  searchField,
  section,
  segment,
  sentenceFor,
  settingsPanel,
  textAction,
} from './ui.js';

const PER_PAGE = 25;
const SHUT_PER_PAGE = 10;
const BOARD = 'approved,planned,in_progress';
const WHY_MAX = 1000;

const SETTINGS_NOTE = 'Whether requests are open, who may file one, whether a mod filing one ' +
  'skips the queue, where the bot says a request arrived, and whether it DMs the person who asked.';
const PENDING_NOTE = 'Waiting on an answer, longest wait first. Approving puts it on the board ' +
  'below; declining sends the person who asked exactly the reason you type.';
const BOARD_NOTE = 'Everything approved and not finished. The buttons here save as you press ' +
  'them — there is no separate Save for the status, the priority or who is on it.';
const DONE_NOTE = 'Requests that shipped. Nothing here needs anything from you; it is the ' +
  'record of what asking actually got built.';
const DECLINED_NOTE = 'The answers that were no, with the reason the person who asked was sent, ' +
  'and the ones they took back themselves.';
const FILE_NOTE = 'The same three fields as /request in Discord. Whoever is signed in is ' +
  'recorded as the person asking — there is no name to fill in.';
const MINE_NOTE = 'Every request you have filed and where each one got to. You can take back ' +
  'one nobody has answered yet.';
const MEMBER_FILE_NOTE = 'What you want built, and why it is worth building. Staff answer these ' +
  'on the same page you are looking at.';

const NO_PENDING = 'Nothing is waiting on an answer. Everything filed has been decided.';
const NO_BOARD = 'Nothing is approved and unfinished. Approve something above and it lands here.';
const NO_DONE = 'Nothing has shipped yet.';
const NO_DECLINED = 'Nothing has been declined.';
const NO_WITHDRAWN = 'Nobody has taken a request back.';
const NO_MINE = 'You have not filed anything yet. The form above is how.';
const NO_MATCH = 'Nothing filed matches what you typed.';

const NEED_A_WHAT = 'Say what you want built first — one line is enough.';
const NEED_A_WHY = 'Say why it is worth building. That is the part that decides the answer, so ' +
  'the form will not send without it.';
const NEED_A_PERSON = 'Nobody is picked yet, so nothing was changed. Type part of a name and ' +
  'choose somebody from the list.';
const NEED_A_NOTE = 'There is nothing to add yet.';

const SETTING_KEYS = [
  'request_mode',
  'request_who_can_file',
  'request_auto_approve_staff',
  'request_notify_channel_id',
  'request_dm_on_decision',
  'request_log_level',
];

const SAID = {
  pending: 'waiting',
  approved: 'approved',
  planned: 'planned',
  in_progress: 'in progress',
  done: 'done',
  declined: 'declined',
  withdrawn: 'withdrawn',
};

const TONE = {
  pending: 'warn',
  approved: 'info',
  planned: 'info',
  in_progress: 'info',
  done: 'ok',
  declined: null,
  withdrawn: null,
};

const BOARD_STEPS = [
  { value: 'approved', label: 'Approved' },
  { value: 'planned', label: 'Planned' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'done', label: 'Done' },
];

const PRIORITY_SAID = {
  1: '1 — do it first',
  2: '2 — soon',
  3: '3 — when there is room',
  4: '4 — nice to have',
  5: '5 — some day',
};

const ASSIGNEE_FILTERS = [
  ['', 'Anybody'],
  ['none', 'Nobody yet'],
  ['me', 'On me'],
];

const state = { pending: 1, board: 1, done: 1, declined: 1, mine: 1, q: '', assignee: '' };

let refresh = () => {};
let viewer = null;

/**
 * A due date is a DAY, so it is read as local midnight. `new Date('2026-09-10')`
 * is UTC midnight, which prints as the ninth anywhere west of Greenwich — the
 * page would name a different day from the one somebody typed.
 */
function dueOn(day) {
  if (!day) return null;
  const parts = String(day).split('-').map(Number);
  if (parts.length !== 3 || parts.some((one) => !Number.isFinite(one))) return null;
  const at = new Date(parts[0], parts[1] - 1, parts[2]);
  if (Number.isNaN(at.getTime())) return null;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((at - today) / 86400000);
  const title = at.toLocaleDateString([], {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
  if (days === 0) return { text: 'due today', title, days };
  if (days > 0) return { text: `due in ${days} day${days === 1 ? '' : 's'}`, title, days };
  const gone = Math.abs(days);
  return { text: `due ${gone} day${gone === 1 ? '' : 's'} ago`, title, days };
}

function dueChip(row) {
  const found = dueOn(row.due_on);
  if (!found) return null;
  const tone = found.days < 0 ? 'danger' : found.days <= 3 ? 'warn' : null;
  return el('span', {
    class: 'req-due',
    'data-tone': tone || undefined,
    title: found.title,
    text: found.text,
  });
}

function statusPill(row) {
  return badge(SAID[row.status] || row.status, TONE[row.status] ?? null);
}

/**
 * The requester's face and name. The Members page has no deep link of its own,
 * so this goes to the page rather than to a filter it cannot honour, and the
 * title says the id the row actually carries.
 */
function requesterNode(person) {
  const name = person && person.name ? person.name : 'somebody who has left';
  return el('a', {
    class: 'req-who',
    href: '/members.html',
    title: `${name} · Discord id ${person ? person.id : 'not known'} — open the Members page`,
  }, [avatar(name, person ? person.avatar : null), el('span', { class: 'req-who-name', text: name })]);
}

function metaLine(row) {
  const asked = ago(row.created_at);
  const parts = [`asked ${asked.text}`];
  if (row.priority !== null && row.priority !== undefined) parts.push(`priority ${row.priority}`);
  if (row.assignee) parts.push(`${row.assignee.name} is on it`);
  if (row.done_at) parts.push(`shipped ${ago(row.done_at).text}`);
  return el('span', { class: 'req-meta', title: asked.title, text: parts.join(' · ') });
}

function headBlock(row) {
  return el('div', { class: 'req-head' }, [
    requesterNode(row.requester),
    el('div', { class: 'req-headtext' }, [
      el('p', { class: 'req-what', text: row.what }),
      metaLine(row),
    ]),
    el('div', { class: 'req-marks' }, [statusPill(row), dueChip(row)]),
  ]);
}

/**
 * The why, clamped to two lines. The button is hidden unless the text really
 * did overflow — measured after the page is in the document, because a node
 * that has not been laid out has no height to compare.
 */
function whyBlock(why) {
  const text = el('p', { class: 'req-why', 'data-open': 'false', text: why || '' });
  const more = el('button', { class: 'req-more', type: 'button', text: 'Read the rest', hidden: true });
  more.addEventListener('click', () => {
    const open = text.getAttribute('data-open') === 'true';
    text.setAttribute('data-open', open ? 'false' : 'true');
    more.textContent = open ? 'Read the rest' : 'Show less';
  });
  return el('div', { class: 'req-whybox' }, [text, more]);
}

/**
 * Measured rather than guessed from the character count — but measured THREE
 * times, because the first reading is a lie in two ways: the self-hosted face
 * has not loaded yet (the fallback fits in two lines where Rajdhani needs
 * three), and a why inside a shut foldout has no height at all. So: now, once
 * the fonts land, on every disclosure, and again when the window changes width.
 */
function measureWhy() {
  for (const text of document.querySelectorAll('.req-why')) {
    const more = text.parentElement.querySelector('.req-more');
    if (!more) continue;
    if (text.getAttribute('data-open') === 'true') {
      more.hidden = false;
      continue;
    }
    more.hidden = text.scrollHeight <= text.clientHeight + 1;
  }
}

let measureSoon = null;

function remeasure() {
  measureWhy();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(measureWhy);
}

document.addEventListener('toggle', () => measureWhy(), true);
window.addEventListener('resize', () => {
  if (measureSoon) clearTimeout(measureSoon);
  measureSoon = setTimeout(measureWhy, 150);
});

function commentNode(one) {
  const at = ago(one.at);
  return el('div', { class: 'req-note' }, [
    el('span', { class: 'req-note-who', title: at.title, text: `${one.author.name} · ${at.text}` }),
    el('p', { class: 'req-note-text', text: one.text }),
  ]);
}

/**
 * The notes on one request, fetched the first time somebody opens the drawer.
 * Thirty requests would otherwise be thirty extra calls on every load for a
 * thread almost nobody opens.
 */
function commentsDrawer(row) {
  const list = el('div', { class: 'req-notes' });
  const say = notice();
  const box = el('input', { class: 'input', type: 'text', placeholder: 'a note for the other staff' });
  let shown = null;

  const add = button('Add the note', async () => {
    const text = box.value.trim();
    if (!text) {
      say.say(NEED_A_NOTE, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/comments`, 'POST', { text }),
      (found) => found?.message || 'Added.',
    );
    if (!done.ok) return;
    box.value = '';
    list.append(commentNode(done.found.comment));
    if (shown) shown.textContent = String(Number(shown.textContent) + 1);
  });

  const drawer = foldout('Notes', [
    list,
    el('div', { class: 'formrow' }, [field('Add a note', box), bar([add])]),
    say,
  ], { count: row.comment_count });
  shown = drawer.querySelector('.sect-count');

  let filled = false;
  drawer.addEventListener('toggle', async () => {
    if (!drawer.open || filled) return;
    filled = true;
    list.replaceChildren(sayNothing('Reading the notes…'));
    try {
      const found = await api(`/api/requests/${encodeURIComponent(row.id)}`);
      const notes = found.comments || [];
      list.replaceChildren(...(notes.length
        ? notes.map(commentNode)
        : [sayNothing('Nobody has said anything about this one yet.')]));
    } catch (error) {
      filled = false;
      const said = sentenceFor(error);
      list.replaceChildren(el('p', { class: 'notice', 'data-tone': said.tone, text: said.text }));
    }
  });
  return drawer;
}

async function saveRow(say, row, body, undo = null) {
  const done = await run(
    say,
    () => send(`/api/requests/${encodeURIComponent(row.id)}/status`, 'POST', body),
    (found) => found?.message || 'Saved.',
  );
  if (!done.ok) {
    if (undo) undo();
    return null;
  }
  return done.found.request;
}

function prioritySelect(row, say) {
  const box = el('select', { class: 'input' });
  box.append(el('option', { value: '', text: 'not set', selected: row.priority === null || undefined }));
  for (const step of [1, 2, 3, 4, 5]) {
    box.append(el('option', {
      value: String(step),
      text: PRIORITY_SAID[step],
      selected: String(row.priority) === String(step) || undefined,
    }));
  }
  box.addEventListener('change', async () => {
    const wanted = box.value === '' ? null : Number(box.value);
    const found = await saveRow(say, row, { priority: wanted }, () => {
      box.value = row.priority === null ? '' : String(row.priority);
    });
    if (found) row.priority = found.priority;
  });
  return box;
}

/**
 * Who is on it, as a line with a Change button rather than a search box on
 * every card — thirteen open cards would otherwise be thirteen search boxes.
 */
function assigneeControl(row, say) {
  const holder = el('div', { class: 'req-assign' });
  let paint = () => {};

  const open = () => {
    const picker = memberPicker({ label: 'Put somebody on it' });
    holder.replaceChildren(picker.node, bar([
      button('Save', async () => {
        if (!picker.id) {
          say.say(NEED_A_PERSON, 'warn');
          return;
        }
        const found = await saveRow(say, row, { assignee_id: picker.id });
        if (!found) return;
        row.assignee = found.assignee;
        paint();
      }),
      button('Cancel', () => paint(), { tone: 'quiet' }),
    ]));
  };

  // replaceChildren turns a null child into the WORD "null" — el() filters them
  // out, this does not — so the list is built and then filtered.
  paint = () => {
    holder.replaceChildren(...[
      el('span', { class: 'req-assign-now', text: row.assignee ? row.assignee.name : 'nobody yet' }),
      button('Change', open, { tone: 'quiet' }),
      row.assignee
        ? button('Take them off', async () => {
          const found = await saveRow(say, row, { assignee_id: null });
          if (!found) return;
          row.assignee = found.assignee;
          paint();
        }, { tone: 'quiet' })
        : null,
    ].filter(Boolean));
  };

  paint();
  return holder;
}

function notesRow(row, say) {
  const box = el('textarea', { class: 'input area', rows: '2', placeholder: 'staff only — the person who asked never sees this' });
  box.value = row.notes || '';
  const save = button('Save the note', async () => {
    const wanted = box.value.trim();
    const found = await saveRow(say, row, { notes: wanted === '' ? null : wanted });
    if (!found) return;
    row.notes = found.notes;
    save.disabled = true;
  }, { disabled: true });
  box.addEventListener('input', () => {
    save.disabled = box.value.trim() === String(row.notes || '').trim();
  });
  return el('div', { class: 'formrow' }, [
    field('Staff note', box, 'What is left to do, or what is blocking it.'),
    bar([save]),
  ]);
}

function boardCard(row) {
  const say = notice();
  const steps = segment(BOARD_STEPS, row.status, {
    onChange: async () => {
      const wanted = steps.readValue();
      if (wanted === row.status) return;
      const found = await saveRow(say, row, { status: wanted }, () => steps.setValue(row.status));
      if (!found) return;
      keepSaying('board', say);
      refresh();
    },
  });
  return card(null, [
    headBlock(row),
    whyBlock(row.why),
    el('div', { class: 'formrow' }, [
      field('Where it is', steps),
      field('Priority', prioritySelect(row, say)),
      field('Who is on it', assigneeControl(row, say)),
    ]),
    notesRow(row, say),
    commentsDrawer(row),
    say,
  ]);
}

function pendingCard(row) {
  const say = notice();

  const approve = button('Approve', async () => {
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/approve`, 'POST', {}),
      (found) => found?.message || 'Approved.',
    );
    if (!done.ok) return;
    keepSaying('pending', say);
    refresh();
  }, { tone: 'warn', small: false });

  const decline = button('Decline', async () => {
    const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — they are sent this' });
    const sure = await ask({
      title: `Say no to ${row.requester.name}?`,
      body: [
        'They are sent exactly what you type here, and the request comes off the board.',
        field('Reason', reason, 'Say why — this is the whole answer they get.'),
      ],
      confirmLabel: 'Decline it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/decline`, 'POST', {
        reason: reason.value.trim(),
      }),
      (found) => found?.message || 'Declined, and they have been told why.',
    );
    if (!done.ok) return;
    keepSaying('pending', say);
    refresh();
  }, { tone: 'danger', small: false });

  return card(null, [
    headBlock(row),
    whyBlock(row.why),
    bar([approve, decline]),
    commentsDrawer(row),
    say,
  ]);
}

function shutCard(row) {
  return card(null, [
    headBlock(row),
    whyBlock(row.why),
    row.decline_reason
      ? el('p', { class: 'req-reason', text: `Why not: ${row.decline_reason}` })
      : null,
    commentsDrawer(row),
  ]);
}

/**
 * A list can shrink under a reader who is on page three — somebody else decides
 * the last pending request and page three is suddenly past the end. Saying
 * "nothing here" then would be a lie about the list rather than about the page,
 * so the sentence names which one it is.
 */
/** One thing to do about an empty list: go back, widen, or file something. */
function emptyDo(which, payload, filterable = false) {
  const total = payload.total ?? 0;
  if (total > 0 && state[which] > 1) {
    return textAction('Go back to the first page', () => {
      state[which] = 1;
      refresh();
    });
  }
  if (filterable && (state.q || state.assignee)) {
    return textAction('Clear the filters', () => {
      state.q = '';
      state.assignee = '';
      refresh();
    });
  }
  return textAction('File a request', () => openSection('file-a-request'));
}

function emptySaid(which, payload, base, filterable = false) {
  const total = payload.total ?? 0;
  if (total > 0 && state[which] > 1) {
    return `Page ${state[which]} is past the end of this list — there ${total === 1 ? 'is 1' : `are ${total}`} in it. ` +
      'Go back a page.';
  }
  if (filterable && (state.q || state.assignee)) return NO_MATCH;
  return base;
}

function pagerFor(which, payload, rows, perPage) {
  const size = payload.per_page ?? perPage;
  const pages = payload.pages ?? Math.ceil((payload.total ?? 0) / size);
  return pager({
    page: state[which],
    hasMore: rows.length > 0 && state[which] < pages,
    count: rows.length,
    onPage: (to) => {
      state[which] = Math.max(1, to);
      return refresh();
    },
  });
}

function pendingSection(payload, rows, say) {
  const one = section('Pending', PENDING_NOTE, { count: payload.total ?? rows.length, open: true });
  one.body.append(
    rows.length === 0
      ? sayNothing(emptySaid('pending', payload, NO_PENDING, true), emptyDo('pending', payload, true))
      : el('div', { class: 'section-body' }, rows.map(pendingCard)),
    pagerFor('pending', payload, rows, PER_PAGE),
    say,
  );
  return one.node;
}

function boardSection(payload, rows, say) {
  const one = section('Planned & in progress', BOARD_NOTE, {
    count: payload.total ?? rows.length,
    open: true,
  });
  one.body.append(
    rows.length === 0
      ? sayNothing(emptySaid('board', payload, NO_BOARD, true), emptyDo('board', payload, true))
      : el('div', { class: 'section-body' }, rows.map(boardCard)),
    pagerFor('board', payload, rows, PER_PAGE),
    say,
  );
  return one.node;
}

function doneSection(payload, rows) {
  const total = payload.total ?? rows.length;
  const one = section('Done', DONE_NOTE, { count: total || null });
  one.body.append(foldout(
    'Requests that shipped',
    [
      rows.length === 0
        ? sayNothing(emptySaid('done', payload, NO_DONE), emptyDo('done', payload))
        : el('div', { class: 'section-body' }, rows.map(shutCard)),
      pagerFor('done', payload, rows, SHUT_PER_PAGE),
    ],
    { count: total },
  ));
  return one.node;
}

function declinedSection(payload, rows, gone) {
  const total = payload.total ?? rows.length;
  const one = section('Declined', DECLINED_NOTE, { count: total || null });
  one.body.append(
    foldout('Declined, with the reason', [
      rows.length === 0
        ? sayNothing(emptySaid('declined', payload, NO_DECLINED), emptyDo('declined', payload))
        : el('div', { class: 'section-body' }, rows.map(shutCard)),
      pagerFor('declined', payload, rows, SHUT_PER_PAGE),
    ], { count: total }),
    foldout('Taken back by the person who asked', [
      gone.length === 0
        ? sayNothing(NO_WITHDRAWN)
        : el('div', { class: 'section-body' }, gone.map(shutCard)),
    ], { count: gone.length }),
  );
  return one.node;
}

/**
 * The sentence under the button, rebuilt on every keystroke: what pressing it
 * will actually do, including whether this person's request skips the queue.
 */
function outcomeOf(form, auto) {
  const what = form.what.value.trim();
  if (!what) return NEED_A_WHAT;
  const why = form.why.value.trim();
  if (!why) return NEED_A_WHY;
  const due = dueOn(form.due.value.trim());
  const staff = viewer && viewer.staff === true;
  const skips = staff && auto
    ? ' It is approved the moment it lands, because you are staff.'
    : ' Staff answer it on this page, and you are told what they decided.';
  const dated = due ? ` It is marked ${due.text.replace(/^due /, 'due ')}.` : '';
  return `Files “${what}” under your name.${skips}${dated}`;
}

function fileForm(say, auto, { note = FILE_NOTE } = {}) {
  const what = el('input', { class: 'input', type: 'text', placeholder: 'what you want built', maxlength: String(WHY_MAX) });
  const why = el('textarea', { class: 'input area', rows: '3', placeholder: 'why it is worth building', maxlength: String(WHY_MAX) });
  const due = el('input', { class: 'input', type: 'date' });
  const outcome = el('p', { class: 'section-note' });
  const form = { what, why, due };
  const repaint = () => {
    outcome.textContent = outcomeOf(form, auto);
  };

  const file = button('File the request', async () => {
    if (!what.value.trim()) {
      say.say(NEED_A_WHAT, 'warn');
      return;
    }
    if (!why.value.trim()) {
      say.say(NEED_A_WHY, 'warn');
      return;
    }
    const body = { what: what.value.trim(), why: why.value.trim() };
    if (due.value.trim()) body.due_on = due.value.trim();
    const done = await run(
      say,
      () => send('/api/requests', 'POST', body),
      (found) => found?.message || 'Filed.',
    );
    if (!done.ok) return;
    keepSaying('file', say);
    refresh();
  }, { tone: 'warn', small: false });

  for (const box of [what, why, due]) box.addEventListener('input', repaint);
  due.addEventListener('change', repaint);
  repaint();

  return card(null, [
    el('p', { class: 'section-note', text: note }),
    el('div', { class: 'formrow' }, [
      field('What', what, 'One line. The detail goes in the why.'),
      field('Due date', due, 'Only when something actually depends on the date.'),
    ]),
    // A bare `.field` lays its label out beside the control; inside a formrow the
    // label sits above it. Why is one field wide, and it still belongs in a row.
    el('div', { class: 'formrow' }, [
      field('Why', why, 'What it fixes, or what it would let people do.'),
    ]),
    outcome,
    bar([file]),
    say,
  ]);
}

function fileSection(node) {
  const one = section('File a request', null, { open: true });
  one.body.append(node);
  return one.node;
}

function toolbar(pendingPayload, boardPayload) {
  const chips = ASSIGNEE_FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key || 'any',
    'aria-pressed': state.assignee === key ? 'true' : 'false',
    text: label,
    on: {
      click: () => {
        state.assignee = key;
        state.pending = 1;
        state.board = 1;
        refresh();
      },
    },
  }));
  const waiting = pendingPayload.total ?? 0;
  const open = boardPayload.total ?? 0;
  return el('div', { class: 'card' }, [
    el('div', { class: 'card-head' }, [
      searchField({
        label: 'Search requests',
        placeholder: 'Search what, why, notes or who asked…',
        onQuery: (query) => {
          if (query === state.q) return;
          state.q = query;
          state.pending = 1;
          state.board = 1;
          refresh();
        },
      }),
      el('div', { class: 'chipbar' }, chips),
      el('span', { class: 'topbar-gap' }),
      el('span', {
        class: 'table-count',
        text: `${waiting} waiting · ${open} on the board`,
      }),
      el('a', { class: 'btn quiet small', href: '/api/requests/export.csv', text: 'Export CSV' }),
    ]),
  ]);
}

/**
 * The filter box is rebuilt on every keystroke, so the caret is put back where
 * it was rather than the page stealing focus mid-word.
 */
function keepTyping(typed) {
  if (typed === null) return;
  const box = document.querySelector('.searchfield .input.search');
  if (!box) return;
  box.value = typed;
  box.focus();
  box.setSelectionRange(typed.length, typed.length);
}

function filtered(extra) {
  const query = new URLSearchParams(extra);
  if (state.q) query.set('q', state.q);
  if (state.assignee === 'me' && viewer && viewer.user) query.set('assignee', String(viewer.user.id));
  else if (state.assignee) query.set('assignee', state.assignee);
  return query.toString();
}

function mineCard(row, say) {
  const withdraw = row.status === 'pending'
    ? button('Take it back', async () => {
      const sure = await ask({
        title: 'Take this request back?',
        body: ['Staff stop seeing it and nobody answers it. You can always file it again.'],
        confirmLabel: 'Take it back',
      });
      if (!sure) return;
      const done = await run(
        say,
        () => send(`/api/requests/${encodeURIComponent(row.id)}/withdraw`, 'POST', {}),
        (found) => found?.message || 'Withdrawn.',
      );
      if (!done.ok) return;
      keepSaying('mine', say);
      refresh();
    }, { tone: 'quiet' })
    : null;

  return card(null, [
    el('div', { class: 'req-head' }, [
      el('div', { class: 'req-headtext' }, [
        el('p', { class: 'req-what', text: row.what }),
        metaLine(row),
      ]),
      el('div', { class: 'req-marks' }, [statusPill(row), dueChip(row)]),
    ]),
    whyBlock(row.why),
    row.decline_reason
      ? el('p', { class: 'req-reason', text: `Why not: ${row.decline_reason}` })
      : null,
    withdraw ? bar([withdraw]) : null,
  ]);
}

function mineSection(payload, rows, say) {
  const one = section('Your requests', MINE_NOTE, {
    count: payload.total ?? rows.length,
    open: true,
  });
  one.body.append(
    rows.length === 0
      ? sayNothing(emptySaid('mine', payload, NO_MINE), emptyDo('mine', payload))
      : el('div', { class: 'section-body' }, rows.map((row) => mineCard(row, say))),
    pagerFor('mine', payload, rows, PER_PAGE),
    say,
  );
  return one.node;
}

async function loadMember() {
  const mine = await api(`/api/requests/mine?page=${state.mine}&per_page=${PER_PAGE}`);
  const rows = listOf(mine, 'requests');
  const fileSay = sayAgain('file', notice());
  const mineSay = sayAgain('mine', notice());
  document.getElementById('dash').replaceChildren(
    fileSection(fileForm(fileSay, false, { note: MEMBER_FILE_NOTE })),
    mineSection(mine, rows, mineSay),
  );
  remeasure();
}

async function loadStaff() {
  const active = document.activeElement;
  const typed = active && active.classList && active.classList.contains('search') ? active.value : null;

  const [waiting, working, shipped, refused, gone, allSettings] = await Promise.all([
    api(`/api/requests?${filtered({ status: 'pending', page: String(state.pending), per_page: String(PER_PAGE) })}`),
    api(`/api/requests?${filtered({ status: BOARD, page: String(state.board), per_page: String(PER_PAGE) })}`),
    api(`/api/requests?status=done&page=${state.done}&per_page=${SHUT_PER_PAGE}`),
    api(`/api/requests?status=declined&page=${state.declined}&per_page=${SHUT_PER_PAGE}`),
    api('/api/requests?status=withdrawn&per_page=50'),
    settings(true),
  ]);

  const specs = settingsNamespace(allSettings, 'request')
    .filter((spec) => SETTING_KEYS.includes(spec.key));
  const auto = (specs.find((spec) => spec.key === 'request_auto_approve_staff') || {}).value === true;

  const pendingSay = sayAgain('pending', notice());
  const boardSay = sayAgain('board', notice());
  const fileSay = sayAgain('file', notice());

  const settingsBox = section('Settings', SETTINGS_NOTE, { count: specs.length || null });
  settingsBox.body.append(await settingsPanel(specs, {
    where: 'Settings',
    empty: 'The bot registers no request settings yet.',
  }));

  document.getElementById('dash').replaceChildren(
    toolbar(waiting, working),
    pendingSection(waiting, listOf(waiting, 'requests'), pendingSay),
    boardSection(working, listOf(working, 'requests'), boardSay),
    doneSection(shipped, listOf(shipped, 'requests')),
    declinedSection(refused, listOf(refused, 'requests'), listOf(gone, 'requests')),
    fileSection(fileForm(fileSay, auto)),
    settingsBox.node,
    await logsSection('request'),
  );
  keepTyping(typed);
  remeasure();
}

async function load(me) {
  viewer = me || null;
  if (me && me.staff !== true && me.member === true) return loadMember();
  return loadStaff();
}

refresh = start({ tab: 'requests', load });
