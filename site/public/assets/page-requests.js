import { api, listOf, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ago,
  ask,
  avatar,
  badge,
  bar,
  button,
  card,
  closeDrawer,
  el,
  field,
  foldout,
  icon,
  keepSaying,
  memberPicker,
  notice,
  openDrawer,
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

const PER_PAGE = 20;
const WHY_MAX = 1000;
const BUILT_MAX = 1000;
const SENT_BACK_MAX = 500;

const LIST_NOTE = 'Everything asked for, in one list. The chips narrow it to a state; a row opens ' +
  'the request, its thread and every move that is legal from where it has got to.';
const MACHINERY_NOTE = 'The reference half of the page: the request settings, and everything ' +
  'requests has done. Both are shut until you want them.';
const SETTINGS_NOTE = 'Whether requests are open, who may file one, where the bot says a request ' +
  'arrived, where it says one moved, and whether it DMs the person who asked each time.';
const FORUM_NOTE = 'With a forum, every request is a post of its own — the card is its first ' +
  'message, every move lands in the same post, and the post is tagged for wherever the request ' +
  'has got to. Make the forum puts one under the Blackmail category with that category’s own ' +
  'permissions. Leave it unmade and requests behave exactly as they do today.';
const OPEN_NOTE = 'Filed and not picked up, longest wait first. Every button here tells the ' +
  'person who asked — picking one up, putting it on hold, and declining it.';
const BOARD_NOTE = 'Being worked on. The buttons here save as you press them — there is no ' +
  'separate Save for the status, the priority or who is on it.';
const HELD_NOTE = 'Parked with a reason, and the reason is what the person who asked was sent. ' +
  'Resume puts one back where it came from.';
const REVIEW_NOTE = 'Built and waiting for somebody to look at it. Accept is the only way a ' +
  'request reaches Done, so what is written here is what the person who asked ends up reading.';
const CLOSED_NOTE = 'Requests that shipped, the answers that were no, and the ones the person ' +
  'who asked took back themselves. Nothing here needs anything from you.';
const ANY_NOTE = 'Every request this server has, whatever state it is in.';
const FILE_NOTE = 'The same three fields as /request in Discord. Whoever is signed in is ' +
  'recorded as the person asking — there is no name to fill in.';
const MINE_NOTE = 'Every request you have filed and where each one got to. You can take back ' +
  'one nobody has answered yet.';
const MEMBER_FILE_NOTE = 'What you want built, and why it is worth building. Staff answer these ' +
  'on the same page you are looking at.';
const SENT_EXACTLY = 'Put it on hold, Decline, Send back and Ready to check each ask for a line, ' +
  'and whoever it concerns is sent exactly what you type.';

const NO_OPEN = 'Nothing is open. Everything filed has been picked up, finished or answered.';
const NO_BOARD = 'Nothing is being worked on. Pick something up above and it lands here.';
const NO_HELD = 'Nothing is on hold.';
const NO_REVIEW = 'Nothing is waiting to be checked. Press Ready to check on something being ' +
  'worked on and it lands here.';
const NO_CLOSED = 'Nothing has shipped, been declined or been taken back yet.';
const NO_ANY = 'Nothing has been filed yet.';
const NO_MINE = 'You have not filed anything yet. File a request above is how.';
const NO_MATCH = 'Nothing filed matches what you typed.';
const GETTING_IT = 'Asking Black Bloc for this request…';

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
  'The list behind this is everything Black Bloc has.';
const NOT_YOURS_TO_SEE = 'That request is not one you filed, and only staff read the rest. Your ' +
  'own are behind this.';
const NO_NOTES_YET = 'Nobody has said anything about this one yet.';
const READING_NOTES = 'Reading the notes…';

const SHOWING = 'Showing {from}–{to} of {n} request{s}';
const SHOWING_SOME = 'Showing {shown} of the {n} on this page';
const SHOWING_ALL = 'All {n} of yours';

const SETTING_KEYS = [
  'request_mode',
  'request_who_can_file',
  'request_notify_channel_id',
  'request_status_channel_id',
  'request_forum_channel_id',
  'request_dm_on_decision',
  'request_channel_moves',
  'request_review_by_other',
  'request_check_fallback_channel',
  'request_check_on_ready',
  'request_post_buttons',
  'request_forum_adopts_posts',
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

const STATE_OF = {
  open: 'warn',
  in_progress: 'info',
  review: 'info',
  hold: 'warn',
  done: 'ok',
  declined: 'danger',
  withdrawn: null,
};

const CHIPS = [
  { key: 'open', label: 'Open', status: 'open', note: OPEN_NOTE, empty: NO_OPEN },
  { key: 'in_progress', label: 'In progress', status: 'in_progress', note: BOARD_NOTE, empty: NO_BOARD },
  { key: 'review', label: 'Ready to check', status: 'review', note: REVIEW_NOTE, empty: NO_REVIEW },
  { key: 'hold', label: 'On hold', status: 'hold', note: HELD_NOTE, empty: NO_HELD },
  { key: 'closed', label: 'Closed', status: 'done,declined,withdrawn', note: CLOSED_NOTE, empty: NO_CLOSED },
  { key: 'all', label: 'All', status: '', note: ANY_NOTE, empty: NO_ANY },
];

const MINE_CHIPS = [
  { key: 'all', label: 'All', has: null },
  { key: 'open', label: 'Open', has: (row) => row.status === 'open' },
  { key: 'in_progress', label: 'In progress', has: (row) => row.status === 'in_progress' },
  { key: 'review', label: 'Ready to check', has: (row) => row.status === 'review' },
  { key: 'hold', label: 'On hold', has: (row) => row.status === 'hold' },
  { key: 'closed', label: 'Closed', has: (row) => ['done', 'declined', 'withdrawn', 'moved'].includes(row.status) },
];

const ASSIGNEE_CHIPS = [
  ['me', 'On me'],
  ['none', 'Nobody yet'],
];

const MOVES = {
  in_progress: { label: 'Pick it up', tone: 'warn' },
  hold: {
    label: 'Put it on hold',
    tone: 'quiet',
    reason: {
      title: (row) => `Park ${row.requester ? row.requester.name : 'this'}'s request?`,
      body: 'It moves to On hold and waits there until somebody resumes it.',
      confirm: 'Put it on hold',
      hint: 'Say what it is waiting on.',
    },
  },
  declined: {
    label: 'Decline',
    tone: 'danger',
    reason: {
      title: (row) => `Say no to ${row.requester ? row.requester.name : 'this'}?`,
      body: 'The request is closed for good.',
      confirm: 'Decline it',
      hint: 'Say why.',
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

const COLUMNS = 'grid-template-columns: 12px minmax(0, 2.2fr) minmax(0, 1fr) '
  + 'minmax(150px, 1.1fr) minmax(0, 0.9fr) minmax(110px, 0.9fr) 24px';
const MINE_COLUMNS = 'grid-template-columns: 12px minmax(0, 2.4fr) minmax(150px, 1.1fr) '
  + 'minmax(110px, 0.9fr) 24px';

const state = { status: 'open', page: 1, q: '', assignee: '', mine: 1, chip: 'all', query: '' };
const shown = { id: null };

let refresh = () => {};
let viewer = null;
let staffing = true;
let deepLinked = false;

function full(node) {
  node.setAttribute('data-span', 'full');
  return node;
}

function plural(count) {
  return count === 1 ? '' : 's';
}

function said(text, values) {
  let out = String(text);
  for (const [key, value] of Object.entries(values)) out = out.replaceAll(`{${key}}`, String(value));
  return out;
}

function chipOf(key) {
  return CHIPS.find((one) => one.key === key) || CHIPS[0];
}

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

function readyChip(row) {
  if (!row.ready_by_name) return null;
  return badge(`ready by ${row.ready_by_name}`, null);
}

/** Who last asked the requester to try it, so nobody asks twice without meaning to. */
function askedChip(row) {
  if (!row.check_asked_at) return null;
  const when = ago(row.check_asked_at);
  const chip = badge(`asked by ${row.check_asked_by_name || 'somebody'} · ${when.text}`, 'info');
  if (when.title) chip.title = when.title;
  return chip;
}

function whoWords(person) {
  return person && person.name ? person.name : 'somebody who has left';
}

/**
 * The requester's face and name. The Members page has no deep link of its own,
 * so this goes to the page rather than to a filter it cannot honour, and the
 * title says the id the row actually carries.
 */
function requesterNode(person) {
  const name = whoWords(person);
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

/** There is no `updated_at` on a request, so the row says which stamp it is showing. */
function movedAt(row) {
  const stamp = row.decided_at || row.created_at;
  const when = ago(stamp);
  return el('span', {
    class: 'cell-quiet',
    title: when.title,
    text: `${row.decided_at ? 'moved' : 'filed'} ${when.text}`,
  });
}

function headBlock(row, marks) {
  return el('div', { class: 'req-head' }, [
    requesterNode(row.requester),
    el('div', { class: 'req-headtext' }, [
      el('p', { class: 'req-what', text: row.what }),
      metaLine(row),
    ]),
    el('div', { class: 'req-marks' }, marks || [
      statusPill(row),
      heldChip(row),
      askedChip(row),
      dueChip(row),
    ]),
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
 * The thread on one request and the box under it. The notes travel with the
 * request the modal already fetched, so opening a row is one call and not two.
 */
function commentsBlock(row, notes) {
  const list = el('div', { class: 'req-notes' }, notes.length
    ? notes.map(commentNode)
    : [sayNothing(NO_NOTES_YET)]);
  const say = notice();
  const box = el('input', { class: 'input', type: 'text', placeholder: 'a note for the other staff' });
  let shownCount = null;

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
    if (list.querySelector('.say-nothing')) list.replaceChildren();
    list.append(commentNode(done.found.comment));
    if (shownCount) shownCount.textContent = String(Number(shownCount.textContent) + 1);
  });

  const block = foldout('Notes', [
    list,
    el('div', { class: 'formrow' }, [field('Add a note', box), bar([add])]),
    say,
  ], { count: notes.length, open: notes.length > 0 });
  shownCount = block.querySelector('.sect-count');
  return block;
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
  refresh();
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

/** A move redraws the list under the modal, then the modal over the fresh row. */
async function after(row, done) {
  if (!done.ok) return;
  await refresh();
  await openRequest(row.id, `Request #${row.id}`, { message: (done.found || {}).message || '' });
}

/**
 * One button per legal move, built from the row's own `moves` list — the same
 * table `black_bloc/requests.py:TRANSITIONS` holds, so a button that would be
 * refused is never drawn at all.
 */
function moveButtons(row, say, moves) {
  return (moves || row.moves || []).map((wanted) => {
    const spec = MOVES[wanted];
    if (!spec) return null;
    return button(spec.label, async () => {
      const body = {};
      if (spec.reason) {
        const box = el('input', { class: 'input', type: 'text', placeholder: 'why' });
        const sure = await ask({
          title: spec.reason.title(row),
          body: [spec.reason.body, field('Reason', box, spec.reason.hint)],
          confirmLabel: spec.reason.confirm,
        });
        if (!sure) return;
        body.reason = box.value.trim();
      }
      const done = await run(
        say,
        () => send(`/api/requests/${encodeURIComponent(row.id)}/status`, 'POST', { status: wanted, ...body }),
        (found) => found?.message || 'Saved.',
      );
      await after(row, done);
    }, { tone: spec.tone, small: false });
  }).filter(Boolean);
}

function resumeButton(row, say) {
  return button('Resume', async () => {
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/resume`, 'POST', {}),
      (found) => found?.message || 'Off hold.',
    );
    await after(row, done);
  }, { tone: 'warn', small: false });
}

/**
 * The move into review, which is the only one that asks for text the person who
 * asked will read. `built` is required and the API refuses an empty one in
 * words, so the dialog says so before the round trip rather than after it.
 */
function readyButton(row, say) {
  return button('Ready to check', async () => {
    const built = el('textarea', { class: 'input area', rows: '3', maxlength: String(BUILT_MAX) });
    built.value = row.built || '';
    const how = el('textarea', { class: 'input area', rows: '3', maxlength: String(BUILT_MAX) });
    how.value = row.how_to_test || '';
    const sure = await ask({
      title: `Say what was built for ${row.requester ? row.requester.name : 'this'}?`,
      body: [
        'Both lines show on the card in Discord and on this page. Either can be edited afterwards without moving the request.',
        field('What was built', built, 'One or two sentences.'),
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
    await after(row, done);
  }, { tone: 'warn', small: false });
}

function acceptButton(row, say) {
  return button('Accept', async () => {
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/accept`, 'POST', {}),
      (found) => found?.message || 'Done.',
    );
    await after(row, done);
  }, { tone: 'ok', small: false });
}

function askCheckButton(row, say) {
  return button('Ask them to check', async () => {
    const done = await run(
      say,
      () => send(`/api/requests/${encodeURIComponent(row.id)}/check`, 'POST', {}),
      (found) => found?.message || 'They have been asked to check it.',
    );
    await after(row, done);
  }, { tone: 'quiet', small: false });
}

function sendBackButton(row, say) {
  return button('Send back', async () => {
    const box = el('input', {
      class: 'input', type: 'text', maxlength: String(SENT_BACK_MAX),
      placeholder: 'what is still to do',
    });
    const sure = await ask({
      title: 'Send this one back?',
      body: [
        `${row.ready_by_name || 'Whoever marked it ready'} gets this, and it goes back to In progress.`,
        field('What needs doing', box, 'Say what is missing.'),
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
    await after(row, done);
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
  const shownLines = [];
  if (row.built) shownLines.push(el('p', { class: 'req-built' }, [
    el('strong', { text: 'What was built: ' }),
    el('span', { text: row.built }),
  ]));
  if (row.how_to_test) shownLines.push(el('p', { class: 'req-built' }, [
    el('strong', { text: 'How to test it: ' }),
    el('span', { text: row.how_to_test }),
  ]));
  if (row.sent_back_reason) shownLines.push(el('p', { class: 'req-reason', text: `Sent back: ${row.sent_back_reason}` }));
  return shownLines;
}

// Send to... — a request staff turned into an event says so, and links where it went.
const MOVED_PAGE = { event: 'events.html', request: 'requests.html' };

function movedBlock(row) {
  if (!row.moved_word) return null;
  const [what] = row.moved_word.split(' ');
  const where = MOVED_PAGE[what];
  const line = el('p', { class: 'req-reason', text: `Moved → ${row.moved_word}` });
  if (where) {
    line.append(' ', el('a', { href: `/${where}`, text: 'open it' }));
  }
  return line;
}

function movesNote(moves) {
  return moves.length ? el('p', { class: 'field-help', text: SENT_EXACTLY }) : null;
}

function openBody(row, say) {
  const moves = moveButtons(row, say);
  return [
    headBlock(row),
    whyBlock(row.why),
    movesNote(moves),
    bar(moves),
  ];
}

function boardBody(row, say) {
  const moves = [readyButton(row, say), ...moveButtons(row, say)];
  return [
    headBlock(row),
    whyBlock(row.why),
    ...writtenBlock(row).filter((one) => one.className === 'req-reason'),
    el('div', { class: 'formrow' }, [
      field('Priority', prioritySelect(row, say)),
      field('Who is on it', assigneeControl(row, say)),
    ]),
    notesRow(row, say),
    movesNote(moves),
    bar(moves),
  ];
}

function reviewBody(row, say) {
  const left = (row.moves || []).filter((one) => one !== 'done' && one !== 'in_progress');
  const moves = [
    acceptButton(row, say),
    askCheckButton(row, say),
    sendBackButton(row, say),
    ...moveButtons(row, say, left),
  ];
  return [
    headBlock(row, [statusPill(row), readyChip(row), askedChip(row), dueChip(row)]),
    whyBlock(row.why),
    writtenRow(row, say, 'built', 'What was built', 'The whole answer the person who asked gets.'),
    writtenRow(row, say, 'how_to_test', 'How to test it', 'Optional — the steps to see it working.'),
    movesNote(moves),
    bar(moves),
  ];
}

function heldBody(row, say) {
  const left = (row.moves || []).filter((one) => one !== row.resume_to);
  const moves = [resumeButton(row, say), ...moveButtons(row, say, left)];
  return [
    headBlock(row),
    whyBlock(row.why),
    row.decline_reason
      ? el('p', { class: 'req-reason', text: `On hold because: ${row.decline_reason}` })
      : null,
    movesNote(moves),
    bar(moves),
  ];
}

function shutBody(row, say) {
  return [
    headBlock(row),
    whyBlock(row.why),
    movedBlock(row),
    row.decline_reason
      ? el('p', { class: 'req-reason', text: `Why not: ${row.decline_reason}` })
      : null,
    ...(row.status === 'done'
      ? [
        writtenRow(row, say, 'built', 'What was built', 'Editable — fixing a typo moves nothing.'),
        writtenRow(row, say, 'how_to_test', 'How to test it', 'Optional — the steps to see it working.'),
      ]
      : writtenBlock(row)),
  ];
}

/**
 * The modal is drawn as whatever the row actually IS. Drawing every one as a
 * review card would put Accept and Send back on an open request, and the API
 * would then refuse the click — a control that would be refused is never drawn.
 */
function bodyFor(row, say) {
  if (row.status === 'review') return reviewBody(row, say);
  if (row.status === 'in_progress') return boardBody(row, say);
  if (row.status === 'hold') return heldBody(row, say);
  if (row.status === 'open') return openBody(row, say);
  return shutBody(row, say);
}

const WITHDRAWABLE = ['open', 'hold'];

function mineBody(row, say) {
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
      closeDrawer();
      await refresh();
    }, { tone: 'quiet' })
    : null;

  return [
    el('div', { class: 'req-head' }, [
      el('div', { class: 'req-headtext' }, [
        el('p', { class: 'req-what', text: row.what }),
        metaLine(row),
      ]),
      el('div', { class: 'req-marks' }, [statusPill(row), heldChip(row), dueChip(row)]),
    ]),
    whyBlock(row.why),
    movedBlock(row),
    row.decline_reason
      ? el('p', {
        class: 'req-reason',
        text: `${row.status === 'hold' ? 'On hold because' : 'Why not'}: ${row.decline_reason}`,
      })
      : null,
    ...writtenBlock(row),
    withdraw ? bar([withdraw]) : null,
  ];
}

/**
 * Every Discord card's link button carries `{origin}/requests.html#r-N`, so the
 * hash is read with or without the `r-`, and always written back the bot's way.
 */
function wantedId() {
  const found = /^#?(?:r-)?(\d+)$/.exec(String(window.location.hash || ''));
  return found ? found[1] : null;
}

/** `close` is dispatched a task late, so a modal replaced in the meantime keeps its hash. */
function forgetHash() {
  const drawer = document.querySelector('dialog.drawer');
  if (drawer && drawer.open) return;
  shown.id = null;
  if (window.location.hash) {
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
  }
}

async function fetchOne(wanted) {
  if (staffing) return api(`/api/requests/${encodeURIComponent(wanted)}`);
  const mine = await api('/api/requests/mine?per_page=200');
  const row = listOf(mine, 'requests').find((one) => String(one.id) === String(wanted)) || null;
  return row ? { request: row, comments: [] } : null;
}

function drawerBody(row, notes, message) {
  const say = notice();
  if (message) say.say(message, 'ok');
  const body = staffing
    ? [...bodyFor(row, say), say, commentsBlock(row, notes)]
    : [...mineBody(row, say), say];
  return body.filter(Boolean);
}

async function openRequest(wanted, title, { row = null, message = '' } = {}) {
  shown.id = String(wanted);
  if (String(window.location.hash).replace(/^#/, '') !== `r-${shown.id}`) {
    const where = window.location.pathname + window.location.search;
    window.history.replaceState(null, '', `${where}#r-${shown.id}`);
  }
  if (row && !staffing) {
    openDrawer(`#${row.id} — ${row.what}`, drawerBody(row, [], message), { onClose: forgetHash });
    remeasure();
    return;
  }
  openDrawer(title, sayNothing(GETTING_IT), { onClose: forgetHash });
  try {
    const found = await fetchOne(wanted);
    if (!found) {
      openDrawer(title, [notice(NOT_YOURS_TO_SEE, 'warn')], { onClose: forgetHash });
      return;
    }
    openDrawer(
      `#${found.request.id} — ${found.request.what}`,
      drawerBody(found.request, found.comments || [], message),
      { onClose: forgetHash },
    );
    remeasure();
  } catch (error) {
    // A 404 or a 403 here is "that number is not one you can read", not an outage — the two
    // get different sentences, because the fixes are different (global refusal rule).
    const missing = error.status === 404 || error.status === 403;
    const line = missing
      ? { text: staffing ? NO_SUCH_ONE : NOT_YOURS_TO_SEE, tone: 'warn' }
      : sentenceFor(error);
    openDrawer(title, [notice(line.text, line.tone)], { onClose: forgetHash });
  }
}

/** The row IS the control — `button.grid-row`, the construct `page-posts.js:postRow` uses. */
function requestRow(row) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: COLUMNS,
    on: { click: () => openRequest(row.id, `Request #${row.id}`, { row }) },
  }, [
    el('span', { class: 'dot-sm', 'data-tone': STATE_OF[row.status] || null }),
    el('span', { class: 'req-headtext' }, [
      el('span', { class: 'cell-name', text: row.what }),
      el('span', { class: 'cell-quiet', text: row.why || '' }),
    ]),
    el('span', { class: 'cell-quiet', text: whoWords(row.requester) }),
    el('span', { class: 'cell-kind' }, [statusPill(row), heldChip(row), dueChip(row)]),
    el('span', { class: 'cell-quiet', text: row.assignee ? row.assignee.name : 'nobody yet' }),
    movedAt(row),
    icon('chevronRight', 16),
  ]);
}

function headRow() {
  return el('div', { class: 'grid-row head', style: COLUMNS }, [
    el('span'),
    el('span', { text: 'Request' }),
    el('span', { text: 'Who' }),
    el('span', { text: 'Status' }),
    el('span', { text: 'Assignee' }),
    el('span', { text: 'Updated' }),
    el('span'),
  ]);
}

function mineRow(row) {
  return el('button', {
    class: 'grid-row',
    type: 'button',
    style: MINE_COLUMNS,
    'data-search': `${row.what} ${row.why || ''} ${SAID[row.status] || row.status}`.toLowerCase(),
    on: { click: () => openRequest(row.id, `Request #${row.id}`, { row }) },
  }, [
    el('span', { class: 'dot-sm', 'data-tone': STATE_OF[row.status] || null }),
    el('span', { class: 'req-headtext' }, [
      el('span', { class: 'cell-name', text: row.what }),
      el('span', { class: 'cell-quiet', text: row.why || '' }),
    ]),
    el('span', { class: 'cell-kind' }, [statusPill(row), heldChip(row), dueChip(row)]),
    movedAt(row),
    icon('chevronRight', 16),
  ]);
}

function mineHeadRow() {
  return el('div', { class: 'grid-row head', style: MINE_COLUMNS }, [
    el('span'),
    el('span', { text: 'Request' }),
    el('span', { text: 'Status' }),
    el('span', { text: 'Updated' }),
    el('span'),
  ]);
}

/**
 * The sentence under the button, rebuilt on every keystroke: what pressing it
 * will actually do.
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

function fileForm(note) {
  const say = notice();
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
    keepSaying('requests', say);
    closeDrawer();
    await refresh();
  }, { tone: 'warn', small: false });

  for (const box of [what, why, due]) box.addEventListener('input', repaint);
  due.addEventListener('change', repaint);
  repaint();

  return [
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
  ];
}

function fileButton(note) {
  const made = button('File a request', () => {
    openDrawer('File a request', fileForm(note));
  }, { tone: 'warn' });
  made.style.marginLeft = 'auto';
  return made;
}

function statusChips(tally) {
  return el('div', { class: 'chipbar' }, CHIPS.map((one) => {
    const count = tally.get(one.key);
    return el('button', {
      class: 'chip-filter',
      type: 'button',
      'data-kind': one.key,
      title: one.note,
      'aria-pressed': state.status === one.key ? 'true' : 'false',
      text: count === null || count === undefined ? one.label : `${one.label} · ${count}`,
      on: {
        click: () => {
          state.status = one.key;
          state.page = 1;
          refresh();
        },
      },
    });
  }));
}

function assigneeChips() {
  return ASSIGNEE_CHIPS.map(([key, label]) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': key,
    'aria-pressed': state.assignee === key ? 'true' : 'false',
    text: label,
    on: {
      click: () => {
        state.assignee = state.assignee === key ? '' : key;
        state.page = 1;
        refresh();
      },
    },
  }));
}

/** One thing to do about an empty list: go back, widen, or file something. */
function emptyDo(payload) {
  const total = payload.total ?? 0;
  if (total > 0 && state.page > 1) {
    return textAction('Go back to the first page', () => {
      state.page = 1;
      refresh();
    });
  }
  if (state.q || state.assignee) {
    return textAction('Clear the filters', () => {
      state.q = '';
      state.assignee = '';
      state.page = 1;
      refresh();
    });
  }
  return textAction('File a request', () => openDrawer('File a request', fileForm(FILE_NOTE)));
}

/**
 * A list can shrink under a reader who is on page three — somebody else decides
 * the last open request and page three is suddenly past the end. Saying
 * "nothing here" then would be a lie about the list rather than about the page,
 * so the sentence names which one it is.
 */
function emptySaid(payload, base) {
  const total = payload.total ?? 0;
  if (total > 0 && state.page > 1) {
    return `Page ${state.page} is past the end of this list — there ${total === 1 ? 'is 1' : `are ${total}`} in it. ` +
      'Go back a page.';
  }
  if (state.q || state.assignee) return NO_MATCH;
  return base;
}

/** The row-count footer: "Showing 1-20 of 24 requests". */
function footFor(payload, rows) {
  if (rows.length === 0) return el('div', { class: 'grid-foot' });
  const size = payload.per_page ?? PER_PAGE;
  const total = payload.total ?? rows.length;
  const from = (state.page - 1) * size + 1;
  return el('div', {
    class: 'grid-foot',
    text: said(SHOWING, {
      from, to: from + rows.length - 1, n: total, s: plural(total),
    }),
  });
}

function pagerFor(payload, rows) {
  const size = payload.per_page ?? PER_PAGE;
  const pages = payload.pages ?? Math.ceil((payload.total ?? 0) / size);
  return pager({
    page: state.page,
    hasMore: rows.length > 0 && state.page < pages,
    count: rows.length,
    onPage: (to) => {
      state.page = Math.max(1, to);
      return refresh();
    },
  });
}

function listSection(payload, rows, tally, say) {
  const chip = chipOf(state.status);
  const one = section('Requests', LIST_NOTE, {
    count: tally.get(state.status) ?? payload.total ?? rows.length,
    id: 'requests',
    open: true,
  });
  const grid = el('div', { class: 'grid-table', style: 'min-width: 900px' }, [
    headRow(),
    ...rows.map(requestRow),
  ]);
  const search = searchField({
    label: 'Search requests',
    placeholder: 'Search what, why, notes or who asked…',
    value: state.q,
    onQuery: (query) => {
      if (query === state.q) return;
      state.q = query;
      state.page = 1;
      refresh();
    },
  });

  one.body.append(
    card(null, [
      el('div', { class: 'card-head' }, [
        search,
        statusChips(tally),
        el('div', { class: 'chipbar' }, assigneeChips()),
        el('span', { class: 'topbar-gap' }),
        el('a', { class: 'btn quiet small', href: '/api/requests/export.csv', text: 'Export CSV' }),
        fileButton(FILE_NOTE),
      ]),
      rows.length === 0
        ? sayNothing(emptySaid(payload, chip.empty), emptyDo(payload))
        : el('div', { class: 'table-scroll' }, [grid]),
      footFor(payload, rows),
    ]),
    pagerFor(payload, rows),
    say,
  );
  return full(one.node);
}

function mineSection(payload, rows, say) {
  const list = section('Your requests', MINE_NOTE, {
    count: payload.total ?? rows.length,
    id: 'your-requests',
    open: true,
  });
  const built = rows.map((row) => ({ row, node: mineRow(row) }));
  const foot = el('div', { class: 'grid-foot' });
  const grid = el('div', { class: 'grid-table', style: 'min-width: 640px' }, [
    mineHeadRow(),
    ...built.map((item) => item.node),
  ]);
  const none = sayNothing(NO_MATCH, textAction('Clear the filters', () => {
    state.chip = 'all';
    state.query = '';
    refresh();
  }));
  none.hidden = true;

  const paint = () => {
    const rule = (MINE_CHIPS.find((chip) => chip.key === state.chip) || MINE_CHIPS[0]).has;
    let hits = 0;
    for (const item of built) {
      const hit = (rule === null || rule(item.row))
        && (state.query === '' || (item.node.getAttribute('data-search') || '').includes(state.query));
      item.node.hidden = !hit;
      if (hit) hits += 1;
    }
    none.hidden = built.length === 0 || hits > 0;
    foot.textContent = hits === built.length
      ? said(SHOWING_ALL, { n: built.length })
      : said(SHOWING_SOME, { shown: hits, n: built.length });
  };

  const chips = el('div', { class: 'chipbar' }, MINE_CHIPS.map((chip) => el('button', {
    class: 'chip-filter',
    type: 'button',
    'data-kind': chip.key,
    'aria-pressed': state.chip === chip.key ? 'true' : 'false',
    text: chip.has === null
      ? `All · ${rows.length}`
      : `${chip.label} · ${rows.filter(chip.has).length}`,
    on: {
      click: (event) => {
        state.chip = chip.key;
        for (const other of event.currentTarget.parentElement.children) {
          other.setAttribute('aria-pressed', other.getAttribute('data-kind') === chip.key ? 'true' : 'false');
        }
        paint();
      },
    },
  })));

  const search = searchField({
    label: 'Search your requests',
    placeholder: 'Search your requests…',
    value: state.query,
    onQuery: (query) => {
      state.query = query;
      paint();
    },
  });
  paint();

  list.body.append(
    card(null, [
      el('div', { class: 'card-head' }, [
        search,
        chips,
        el('span', { class: 'topbar-gap' }),
        fileButton(MEMBER_FILE_NOTE),
      ]),
      built.length === 0
        ? sayNothing(NO_MINE, textAction('File a request', () => openDrawer('File a request', fileForm(MEMBER_FILE_NOTE))))
        : el('div', { class: 'table-scroll' }, [grid]),
      none,
      foot,
    ]),
    pager({
      page: state.mine,
      hasMore: built.length > 0 && state.mine < (payload.pages ?? 1),
      count: built.length,
      onPage: (to) => {
        state.mine = Math.max(1, to);
        return refresh();
      },
    }),
    say,
  );
  return full(list.node);
}

function requestForumCard(forumId) {
  const say = notice();
  const make = button('Make the forum', async () => {
    const done = await run(
      say,
      () => send('/api/requests/forum', 'POST', {}),
      (found) => found?.message || 'The request forum is up.',
    );
    if (done.ok) {
      keepSaying('requests', say);
      refresh();
    }
  }, { tone: 'warn' });
  return card('Request forum', [
    el('p', { text: FORUM_NOTE }),
    forumId
      ? sayNothing('Every request gets its own post there.')
      : sayNothing('There is no request forum yet, so cards go to the channels below.'),
    forumId
      ? sayNothing('Clear request_forum_channel_id below to let go of it.')
      : bar([make]),
    say,
  ]);
}

/** A shared block demoted out of the "On this page" rail so a fold is not a place. */
function unsectioned(node) {
  const inner = node.querySelector('.sect-inner');
  return inner ? [...inner.childNodes] : [node];
}

async function machinerySection(specs) {
  const one = section('Settings and logs', MACHINERY_NOTE, { id: 'machinery' });
  one.body.append(
    foldout('Settings', [
      el('p', { class: 'field-help', text: SETTINGS_NOTE }),
      requestForumCard((specs.find((spec) => spec.key === 'request_forum_channel_id') || {}).value ?? null),
      await settingsPanel(specs, {
        where: 'Settings',
        empty: 'The bot registers no request settings yet.',
      }),
    ], { count: specs.length }),
    foldout('Logs', unsectioned(await logsSection('request'))),
  );
  return full(one.node);
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

/** A count that could not be read is left OFF its chip rather than shown as nothing. */
function tallyOf(chip) {
  return api(`/api/requests?${filtered({ status: chip.status, page: '1', per_page: '1' })}`)
    .then((found) => found.total ?? 0)
    .catch(() => null);
}

async function honourTheLink(rows) {
  const wanted = wantedId();
  if (!wanted || deepLinked) return;
  deepLinked = true;
  const found = rows.find((one) => String(one.id) === wanted) || null;
  await openRequest(wanted, `Request #${wanted}`, { row: found });
}

async function loadMember() {
  const mine = await api(`/api/requests/mine?page=${state.mine}&per_page=${PER_PAGE}`);
  const rows = listOf(mine, 'requests');
  const say = sayAgain('mine', sayAgain('requests', notice()));
  document.getElementById('dash').replaceChildren(mineSection(mine, rows, say));
  remeasure();
  await honourTheLink(rows);
}

async function loadStaff() {
  const active = document.activeElement;
  const typed = active && active.classList && active.classList.contains('search') ? active.value : null;
  const chip = chipOf(state.status);

  const [payload, counts, allSettings] = await Promise.all([
    api(`/api/requests?${filtered({ status: chip.status, page: String(state.page), per_page: String(PER_PAGE) })}`),
    Promise.all(CHIPS.map(tallyOf)),
    settings(true),
  ]);

  const tally = new Map(CHIPS.map((one, at) => [one.key, counts[at]]));
  const rows = listOf(payload, 'requests');
  const specs = settingsNamespace(allSettings, 'request')
    .filter((spec) => SETTING_KEYS.includes(spec.key));
  const say = sayAgain('requests', notice());

  document.getElementById('dash').replaceChildren(
    listSection(payload, rows, tally, say),
    await machinerySection(specs),
  );
  keepTyping(typed);
  remeasure();
  await honourTheLink(rows);
}

async function load(me) {
  viewer = me || null;
  staffing = !(me && me.staff !== true && me.member === true);
  const head = document.getElementById('page-aside');
  if (head) head.replaceChildren();
  return staffing ? loadStaff() : loadMember();
}

window.addEventListener('hashchange', () => {
  const wanted = wantedId();
  if (!wanted) {
    if (shown.id) closeDrawer();
    return;
  }
  if (wanted === shown.id) return;
  openRequest(wanted, `Request #${wanted}`);
});

refresh = start({ tab: 'requests', load });
