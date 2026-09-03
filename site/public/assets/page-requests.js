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
  sentenceFor,
  settingsPanel,
  textAction,
} from './ui.js';

const PER_PAGE = 25;
const SHUT_PER_PAGE = 10;
const WHY_MAX = 1000;
const BUILT_MAX = 1000;
const SENT_BACK_MAX = 500;
const LINKED_MS = 2000;

const SETTINGS_NOTE = 'Whether requests are open, who may file one, where the bot says a request ' +
  'arrived, where it says one moved, and whether it DMs the person who asked each time.';
const OPEN_NOTE = 'Filed and not picked up, longest wait first. Every button here tells the ' +
  'person who asked — picking one up, putting it on hold, and declining it.';
const BOARD_NOTE = 'Being worked on. The buttons here save as you press them — there is no ' +
  'separate Save for the status, the priority or who is on it.';
const HELD_NOTE = 'Parked with a reason, and the reason is what the person who asked was sent. ' +
  'Resume puts one back where it came from.';
const REVIEW_NOTE = 'Built and waiting for somebody to look at it. Accept is the only way a ' +
  'request reaches Done, so what is written here is what the person who asked ends up reading.';
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

const NO_OPEN = 'Nothing is open. Everything filed has been picked up, finished or answered.';
const NO_BOARD = 'Nothing is being worked on. Pick something up above and it lands here.';
const NO_HELD = 'Nothing is on hold.';
const NO_REVIEW = 'Nothing is waiting to be checked. Press Ready to check on something being ' +
  'worked on and it lands here.';
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
const NEED_A_BUILT = 'Say what was built first. That line is what the person who asked reads on ' +
  'the card, so the form will not send without it.';
const NEED_A_SENDBACK = 'Say what is still to do. Whoever marked it ready is sent exactly this.';
const NO_SUCH_ONE = 'There is no request with that number, or it is not one this server has. ' +
  'The lists below are everything Black Bloc has.';
const NOT_YOURS_TO_SEE = 'That request is not one you filed, and only staff read the rest. Your ' +
  'own are below.';

const SETTING_KEYS = [
  'request_mode',
  'request_who_can_file',
  'request_notify_channel_id',
  'request_status_channel_id',
  'request_dm_on_decision',
  'request_channel_moves',
  'request_review_by_other',
  'request_log_level',
];

const SAID = {
  open: 'open',
  in_progress: 'in progress',
  review: 'ready to check',
  hold: 'on hold',
  done: 'done',
  declined: 'declined',
  withdrawn: 'withdrawn',
};

const TONE = {
  open: 'warn',
  in_progress: 'info',
  review: 'info',
  hold: 'warn',
  done: 'ok',
  declined: null,
  withdrawn: null,
};

/**
 * One button per move the row's own `moves` list allows, so a control that would
 * refuse is never drawn. Hold and Decline ask for the sentence the requester is
 * sent; the API refuses either without one, in words.
 */
const MOVES = {
  in_progress: { label: 'Pick it up', tone: 'warn' },
  hold: {
    label: 'Put it on hold',
    tone: 'quiet',
    reason: {
      title: (row) => `Park ${row.requester.name}'s request?`,
      body: 'They are sent exactly what you type here, and it moves to On hold.',
      confirm: 'Put it on hold',
      hint: 'Say what it is waiting on — this is the whole answer they get.',
    },
  },
  declined: {
    label: 'Decline',
    tone: 'danger',
    reason: {
      title: (row) => `Say no to ${row.requester.name}?`,
      body: 'They are sent exactly what you type here, and the request is closed for good.',
      confirm: 'Decline it',
      hint: 'Say why — this is the whole answer they get.',
    },
  },
};

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

const state = {
  open: 1, board: 1, review: 1, held: 1, done: 1, declined: 1, mine: 1, q: '', assignee: '',
};

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

/** "on hold — was: in progress", so a parked request says what it was parked from. */
function heldChip(row) {
  if (row.status !== 'hold' || !row.held_word) return null;
  return badge(`was: ${row.held_word}`, null);
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

/**
 * A card's own anchor, so the link button on every Discord embed
 * ({origin}/requests#r-N) lands on the request it names.
 */
function anchored(row, node) {
  node.id = `r-${row.id}`;
  return node;
}

function headBlock(row) {
  return el('div', { class: 'req-head' }, [
    requesterNode(row.requester),
    el('div', { class: 'req-headtext' }, [
      el('p', { class: 'req-what', text: row.what }),
      metaLine(row),
    ]),
    el('div', { class: 'req-marks' }, [statusPill(row), heldChip(row), dueChip(row)]),
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

/**
 * One button per legal move, built from the row's own `moves` list — the same
 * table `black_bloc/requests.py:TRANSITIONS` holds, so a button that would be
 * refused is never drawn at all.
 */
function moveButtons(row, say, which) {
  return (row.moves || []).map((wanted) => {
    const spec = MOVES[wanted];
    if (!spec) return null;
    return button(spec.label, async () => {
      const body = {};
      if (spec.reason) {
        const box = el('input', {
          class: 'input', type: 'text', placeholder: 'why — they are sent this',
        });
        const sure = await ask({
          title: spec.reason.title(row),
          body: [spec.reason.body, field('Reason', box, spec.reason.hint)],
          confirmLabel: spec.reason.confirm,
        });
        if (!sure) return;
        body.reason = box.value.trim();
      }
      const found = await saveRow(say, row, { status: wanted, ...body });
      if (!found) return;
      keepSaying(which, say);
      refresh();
    }, { tone: spec.tone, small: false });
  }).filter(Boolean);
}

function resumeButton(row, say, which) {
  return button('Resume', async () => {
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/resume`, 'POST', {}),
      (found) => found?.message || 'Off hold.',
    );
    if (!done.ok) return;
    keepSaying(which, say);
    refresh();
  }, { tone: 'warn', small: false });
}

/**
 * The move into review, which is the only one that asks for text the person who
 * asked will read. `built` is required and the API refuses an empty one in
 * words, so the dialog says so before the round trip rather than after it.
 */
function readyButton(row, say, which) {
  return button('Ready to check', async () => {
    const built = el('textarea', { class: 'input area', rows: '3', maxlength: String(BUILT_MAX) });
    built.value = row.built || '';
    const how = el('textarea', { class: 'input area', rows: '3', maxlength: String(BUILT_MAX) });
    how.value = row.how_to_test || '';
    const sure = await ask({
      title: `Say what was built for ${row.requester ? row.requester.name : 'this'}?`,
      body: [
        'Both lines show on the card in Discord and on this page. Either can be edited afterwards without moving the request.',
        field('What was built', built, 'One or two sentences. This is the whole answer they get.'),
        field('How to test it', how, 'Optional — the steps somebody follows to see it working.'),
      ],
      confirmLabel: 'Mark it ready to check',
    });
    if (!sure) return;
    if (!built.value.trim()) {
      say.say(NEED_A_BUILT, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/ready`, 'POST', {
        built: built.value.trim(),
        how_to_test: how.value.trim(),
      }),
      (found) => found?.message || 'Ready to check.',
    );
    if (!done.ok) return;
    keepSaying(which, say);
    refresh();
  }, { tone: 'warn', small: false });
}

function acceptButton(row, say, which) {
  return button('Accept', async () => {
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/accept`, 'POST', {}),
      (found) => found?.message || 'Done.',
    );
    if (!done.ok) return;
    keepSaying(which, say);
    refresh();
  }, { tone: 'ok', small: false });
}

function sendBackButton(row, say, which) {
  return button('Send back', async () => {
    const box = el('input', {
      class: 'input', type: 'text', maxlength: String(SENT_BACK_MAX),
      placeholder: 'what is still to do',
    });
    const sure = await ask({
      title: 'Send this one back?',
      body: [
        `${row.ready_by_name || 'Whoever marked it ready'} is sent exactly what you type, and it goes back to In progress.`,
        field('What needs doing', box, 'Say what is missing — this is the whole answer they get.'),
      ],
      confirmLabel: 'Send it back',
    });
    if (!sure) return;
    if (!box.value.trim()) {
      say.say(NEED_A_SENDBACK, 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/sendback`, 'POST', {
        reason: box.value.trim(),
      }),
      (found) => found?.message || 'Sent back.',
    );
    if (!done.ok) return;
    keepSaying(which, say);
    refresh();
  }, { tone: 'quiet', small: false });
}

/**
 * `built` and `how_to_test` edited in place on a review or done card: a typo in
 * how-to-test must not need a state change to fix, so this is a partial
 * `/status` save and nothing moves.
 */
function writtenRow(row, say, name, label, hint) {
  const box = el('textarea', { class: 'input area', rows: '2', maxlength: String(BUILT_MAX) });
  box.value = row[name] || '';
  const save = button('Save', async () => {
    const wanted = box.value.trim();
    const found = await saveRow(say, row, { [name]: wanted === '' ? null : wanted });
    if (!found) return;
    row[name] = found[name];
    save.disabled = true;
  }, { disabled: true });
  box.addEventListener('input', () => {
    save.disabled = box.value.trim() === String(row[name] || '').trim();
  });
  return el('div', { class: 'formrow' }, [field(label, box, hint), bar([save])]);
}

function writtenBlock(row) {
  const shown = [];
  if (row.built) shown.push(el('p', { class: 'req-built' }, [
    el('strong', { text: 'What was built: ' }),
    el('span', { text: row.built }),
  ]));
  if (row.how_to_test) shown.push(el('p', { class: 'req-built' }, [
    el('strong', { text: 'How to test it: ' }),
    el('span', { text: row.how_to_test }),
  ]));
  if (row.sent_back_reason) shown.push(el('p', { class: 'req-reason', text: `Sent back: ${row.sent_back_reason}` }));
  return shown;
}

function readyChip(row) {
  if (!row.ready_by_name) return null;
  return badge(`ready by ${row.ready_by_name}`, null);
}

function boardCard(row) {
  const say = notice();
  return anchored(row, card(null, [
    headBlock(row),
    whyBlock(row.why),
    ...writtenBlock(row).filter((one) => one.className === 'req-reason'),
    el('div', { class: 'formrow' }, [
      field('Priority', prioritySelect(row, say)),
      field('Who is on it', assigneeControl(row, say)),
    ]),
    notesRow(row, say),
    bar([readyButton(row, say, 'board'), ...moveButtons(row, say, 'board')]),
    commentsDrawer(row),
    say,
  ]));
}

function reviewCard(row) {
  const say = notice();
  const moves = (row.moves || []).filter((one) => one !== 'done' && one !== 'in_progress');
  return anchored(row, card(null, [
    el('div', { class: 'req-head' }, [
      requesterNode(row.requester),
      el('div', { class: 'req-headtext' }, [
        el('p', { class: 'req-what', text: row.what }),
        metaLine(row),
      ]),
      el('div', { class: 'req-marks' }, [statusPill(row), readyChip(row), dueChip(row)]),
    ]),
    whyBlock(row.why),
    writtenRow(row, say, 'built', 'What was built', 'The whole answer the person who asked gets.'),
    writtenRow(row, say, 'how_to_test', 'How to test it', 'Optional — the steps to see it working.'),
    bar([
      acceptButton(row, say, 'review'),
      sendBackButton(row, say, 'review'),
      ...moveButtons({ ...row, moves }, say, 'review'),
    ]),
    commentsDrawer(row),
    say,
  ]));
}

function openCard(row) {
  const say = notice();
  return anchored(row, card(null, [
    headBlock(row),
    whyBlock(row.why),
    bar(moveButtons(row, say, 'open')),
    commentsDrawer(row),
    say,
  ]));
}

function heldCard(row) {
  const say = notice();
  const moves = (row.moves || []).filter((one) => one !== row.resume_to);
  return anchored(row, card(null, [
    headBlock(row),
    whyBlock(row.why),
    row.decline_reason
      ? el('p', { class: 'req-reason', text: `On hold because: ${row.decline_reason}` })
      : null,
    bar([
      resumeButton(row, say, 'held'),
      ...moveButtons({ ...row, moves }, say, 'held'),
    ]),
    commentsDrawer(row),
    say,
  ]));
}

function shutCard(row) {
  const say = row.status === 'done' ? notice() : null;
  return anchored(row, card(null, [
    headBlock(row),
    whyBlock(row.why),
    row.decline_reason
      ? el('p', { class: 'req-reason', text: `Why not: ${row.decline_reason}` })
      : null,
    ...(row.status === 'done'
      ? [
        writtenRow(row, say, 'built', 'What was built', 'Editable — fixing a typo moves nothing.'),
        writtenRow(row, say, 'how_to_test', 'How to test it', 'Optional — the steps to see it working.'),
      ]
      : []),
    commentsDrawer(row),
    say,
  ]));
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

/** The row-count footer the big lists wear: "Showing 1-10 of 24 requests". */
function footFor(which, payload, rows, perPage) {
  if (rows.length === 0) return document.createDocumentFragment();
  const size = payload.per_page ?? perPage;
  const total = payload.total ?? rows.length;
  const from = (state[which] - 1) * size + 1;
  return el('div', {
    class: 'grid-foot',
    text: `Showing ${from}–${from + rows.length - 1} of ${total} request${total === 1 ? '' : 's'}`,
  });
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

function openSectionOf(payload, rows, say) {
  const one = section('Open', OPEN_NOTE, { count: payload.total ?? rows.length, open: true });
  one.body.append(
    rows.length === 0
      ? sayNothing(emptySaid('open', payload, NO_OPEN, true), emptyDo('open', payload, true))
      : el('div', { class: 'section-body' }, rows.map(openCard)),
    footFor('open', payload, rows, PER_PAGE),
    pagerFor('open', payload, rows, PER_PAGE),
    say,
  );
  return one.node;
}

function boardSection(payload, rows, say) {
  const one = section('In progress', BOARD_NOTE, {
    count: payload.total ?? rows.length,
    open: true,
  });
  one.body.append(
    rows.length === 0
      ? sayNothing(emptySaid('board', payload, NO_BOARD, true), emptyDo('board', payload, true))
      : el('div', { class: 'section-body' }, rows.map(boardCard)),
    footFor('board', payload, rows, PER_PAGE),
    pagerFor('board', payload, rows, PER_PAGE),
    say,
  );
  return one.node;
}

function heldSection(payload, rows, say) {
  const one = section('On hold', HELD_NOTE, {
    count: payload.total ?? rows.length,
    open: true,
  });
  one.body.append(
    rows.length === 0
      ? sayNothing(emptySaid('held', payload, NO_HELD, true), emptyDo('held', payload, true))
      : el('div', { class: 'section-body' }, rows.map(heldCard)),
    footFor('held', payload, rows, PER_PAGE),
    pagerFor('held', payload, rows, PER_PAGE),
    say,
  );
  return one.node;
}

function reviewSection(payload, rows, say) {
  const one = section('Ready to check', REVIEW_NOTE, {
    count: payload.total ?? rows.length,
    open: true,
  });
  one.body.append(
    rows.length === 0
      ? sayNothing(emptySaid('review', payload, NO_REVIEW, true), emptyDo('review', payload, true))
      : el('div', { class: 'section-body' }, rows.map(reviewCard)),
    footFor('review', payload, rows, PER_PAGE),
    pagerFor('review', payload, rows, PER_PAGE),
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
      footFor('done', payload, rows, SHUT_PER_PAGE),
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
      footFor('declined', payload, rows, SHUT_PER_PAGE),
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
function outcomeOf(form) {
  const what = form.what.value.trim();
  if (!what) return NEED_A_WHAT;
  const why = form.why.value.trim();
  if (!why) return NEED_A_WHY;
  const due = dueOn(form.due.value.trim());
  const dated = due ? ` It is marked ${due.text.replace(/^due /, 'due ')}.` : '';
  return `Files “${what}” under your name. It lands open, whoever files it, and you are DMed ` +
    `every time staff move it.${dated}`;
}

function fileForm(say, { note = FILE_NOTE } = {}) {
  const what = el('input', { class: 'input', type: 'text', placeholder: 'what you want built', maxlength: String(WHY_MAX) });
  const why = el('textarea', { class: 'input area', rows: '3', placeholder: 'why it is worth building', maxlength: String(WHY_MAX) });
  const due = el('input', { class: 'input', type: 'date' });
  const outcome = el('p', { class: 'section-note' });
  const form = { what, why, due };
  const repaint = () => {
    outcome.textContent = outcomeOf(form);
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

function toolbar(openPayload, boardPayload) {
  const chips = ASSIGNEE_FILTERS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key || 'any',
    'aria-pressed': state.assignee === key ? 'true' : 'false',
    text: label,
    on: {
      click: () => {
        state.assignee = key;
        state.open = 1;
        state.board = 1;
        state.held = 1;
        refresh();
      },
    },
  }));
  const waiting = openPayload.total ?? 0;
  const open = boardPayload.total ?? 0;
  return el('div', { class: 'card' }, [
    el('div', { class: 'card-head' }, [
      searchField({
        label: 'Search requests',
        placeholder: 'Search what, why, notes or who asked…',
        onQuery: (query) => {
          if (query === state.q) return;
          state.q = query;
          state.open = 1;
          state.board = 1;
          state.held = 1;
          refresh();
        },
      }),
      el('div', { class: 'chipbar' }, chips),
      el('span', { class: 'topbar-gap' }),
      el('span', {
        class: 'table-count',
        text: `${waiting} open · ${open} in progress`,
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

const WITHDRAWABLE = ['open', 'hold'];

function mineCard(row, say) {
  const withdraw = WITHDRAWABLE.includes(row.status)
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

  return anchored(row, card(null, [
    el('div', { class: 'req-head' }, [
      el('div', { class: 'req-headtext' }, [
        el('p', { class: 'req-what', text: row.what }),
        metaLine(row),
      ]),
      el('div', { class: 'req-marks' }, [statusPill(row), heldChip(row), dueChip(row)]),
    ]),
    whyBlock(row.why),
    row.decline_reason
      ? el('p', {
        class: 'req-reason',
        text: `${row.status === 'hold' ? 'On hold because' : 'Why not'}: ${row.decline_reason}`,
      })
      : null,
    ...writtenBlock(row),
    withdraw ? bar([withdraw]) : null,
  ]));
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
    footFor('mine', payload, rows, PER_PAGE),
    pagerFor('mine', payload, rows, PER_PAGE),
    say,
  );
  return one.node;
}

/**
 * The number in `#r-7`, which every Discord card's link button carries. It is
 * read once per load and cleared as soon as it has been honoured, so a refresh
 * after a button press does not scroll the reader back up to it.
 */
function linkedId() {
  const found = /^#r-(\d+)$/.exec(String(window.location.hash || ''));
  return found ? found[1] : null;
}

let pinned = null;

/**
 * A request that is not on the page — a later pager page, or somebody else's
 * row a member cannot see in their own list. It is fetched on its own and
 * pinned above the sections rather than paging the reader around to find it.
 */
function pinnedCard(row, draw) {
  return el('div', { class: 'req-pinned' }, [
    el('div', { class: 'card-head' }, [
      el('h3', { text: `Request #${row.id}` }),
      el('span', { class: 'topbar-gap' }),
      textAction('Back to all', () => {
        pinned = null;
        window.history.replaceState(null, '', window.location.pathname);
        refresh();
      }),
    ]),
    draw(row),
  ]);
}

function pinnedSaid(text) {
  return el('div', { class: 'req-pinned' }, [
    el('div', { class: 'card-head' }, [
      el('h3', { text: 'That request' }),
      el('span', { class: 'topbar-gap' }),
      textAction('Back to all', () => {
        pinned = null;
        window.history.replaceState(null, '', window.location.pathname);
        refresh();
      }),
    ]),
    sayNothing(text),
  ]);
}

/**
 * The card is on the page: scroll to it and flash it for two seconds. Measured
 * rather than assumed — a card inside a shut foldout has no box to scroll to,
 * so the foldout is opened first.
 */
function flashLinked(wanted) {
  const node = document.getElementById(`r-${wanted}`);
  if (!node) return false;
  for (let up = node.parentElement; up; up = up.parentElement) {
    if (up.tagName === 'DETAILS') up.open = true;
  }
  node.scrollIntoView({ block: 'center', behavior: 'smooth' });
  node.classList.add('is-linked');
  setTimeout(() => node.classList.remove('is-linked'), LINKED_MS);
  return true;
}

/** Staff read any row; a member reads only their own, so each asks its own route. */
async function fetchOne(wanted, staff) {
  if (staff) return (await api(`/api/requests/${encodeURIComponent(wanted)}`)).request;
  const mine = await api('/api/requests/mine?per_page=200');
  return listOf(mine, 'requests').find((row) => String(row.id) === String(wanted)) || null;
}

async function honourTheLink(staff, draw) {
  const wanted = linkedId();
  if (!wanted || pinned === wanted) return;
  if (flashLinked(wanted)) {
    pinned = wanted;
    return;
  }
  pinned = wanted;
  const holder = document.getElementById('dash');
  try {
    const row = await fetchOne(wanted, staff);
    holder.prepend(row ? pinnedCard(row, draw) : pinnedSaid(staff ? NO_SUCH_ONE : NOT_YOURS_TO_SEE));
  } catch (error) {
    // A 404 or a 403 here is "that number is not one you can read", not an outage — the two
    // get different sentences, because the fixes are different (global refusal rule).
    const missing = error.status === 404 || error.status === 403;
    holder.prepend(pinnedSaid(missing ? (staff ? NO_SUCH_ONE : NOT_YOURS_TO_SEE) : sentenceFor(error).text));
  }
}

async function loadMember() {
  const mine = await api(`/api/requests/mine?page=${state.mine}&per_page=${PER_PAGE}`);
  const rows = listOf(mine, 'requests');
  const fileSay = sayAgain('file', notice());
  const mineSay = sayAgain('mine', notice());
  document.getElementById('dash').replaceChildren(
    fileSection(fileForm(fileSay, { note: MEMBER_FILE_NOTE })),
    mineSection(mine, rows, mineSay),
  );
  remeasure();
  await honourTheLink(false, (row) => mineCard(row, mineSay));
}

async function loadStaff() {
  const active = document.activeElement;
  const typed = active && active.classList && active.classList.contains('search') ? active.value : null;

  const [waiting, working, checking, parked, shipped, refused, gone, allSettings] = await Promise.all([
    api(`/api/requests?${filtered({ status: 'open', page: String(state.open), per_page: String(PER_PAGE) })}`),
    api(`/api/requests?${filtered({ status: 'in_progress', page: String(state.board), per_page: String(PER_PAGE) })}`),
    api(`/api/requests?${filtered({ status: 'review', page: String(state.review), per_page: String(PER_PAGE) })}`),
    api(`/api/requests?${filtered({ status: 'hold', page: String(state.held), per_page: String(PER_PAGE) })}`),
    api(`/api/requests?status=done&page=${state.done}&per_page=${SHUT_PER_PAGE}`),
    api(`/api/requests?status=declined&page=${state.declined}&per_page=${SHUT_PER_PAGE}`),
    api('/api/requests?status=withdrawn&per_page=50'),
    settings(true),
  ]);

  const specs = settingsNamespace(allSettings, 'request')
    .filter((spec) => SETTING_KEYS.includes(spec.key));

  const openSay = sayAgain('open', notice());
  const boardSay = sayAgain('board', notice());
  const reviewSay = sayAgain('review', notice());
  const heldSay = sayAgain('held', notice());
  const fileSay = sayAgain('file', notice());

  const settingsBox = section('Settings', SETTINGS_NOTE, { count: specs.length || null });
  settingsBox.body.append(await settingsPanel(specs, {
    where: 'Settings',
    empty: 'The bot registers no request settings yet.',
  }));

  document.getElementById('dash').replaceChildren(
    toolbar(waiting, working),
    openSectionOf(waiting, listOf(waiting, 'requests'), openSay),
    boardSection(working, listOf(working, 'requests'), boardSay),
    reviewSection(checking, listOf(checking, 'requests'), reviewSay),
    heldSection(parked, listOf(parked, 'requests'), heldSay),
    doneSection(shipped, listOf(shipped, 'requests')),
    declinedSection(refused, listOf(refused, 'requests'), listOf(gone, 'requests')),
    fileSection(fileForm(fileSay)),
    settingsBox.node,
    await logsSection('request'),
  );
  keepTyping(typed);
  remeasure();
  await honourTheLink(true, reviewCard);
}

async function load(me) {
  viewer = me || null;
  if (me && me.staff !== true && me.member === true) return loadMember();
  return loadStaff();
}

refresh = start({ tab: 'requests', load });
