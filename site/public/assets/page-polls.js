import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { openSection as goToSection } from './layout.js';
import { logsSection } from './logs.js';
import {
  ago,
  ask,
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
  linkAction,
  modeSwitch,
  nameNode,
  notice,
  pager,
  readSelect,
  roleSelect,
  run,
  sayAgain,
  sayNothing,
  section,
  segment,
  settingsPanel,
  table,
  textAction,
  untilWhen,
} from './ui.js';

const MODE_KEY = 'poll_mode';
const CLOSED_PER_PAGE = 10;
const SETTLED = 'closed,cancelled,denied';
const NATIVE_CAP = 10;
const PANEL_CAP = 25;

const KINDS = [
  ['single', 'Single choice'],
  ['checkbox', 'Checkbox — pick several'],
  ['yesno', 'Yes / no'],
  ['rating', 'Rating, 1-5'],
  ['date', 'Date / availability'],
];
const GENERATED = { yesno: ['Yes', 'No'], rating: ['1', '2', '3', '4', '5'] };

const SWITCH_HELP = 'Off hides Create on the /poll panel and refuses new polls. Nothing already ' +
  'running is closed, and every result Black Bloc has kept stays on this page.';
const NO_MODE_KEY = 'The bot did not report a poll_mode key, so this switch is not shown ' +
  'rather than guessed at.';

const OPEN_NOTE = 'Every poll taking votes right now. Ending one publishes the result; ' +
  'cancelling stops it without publishing anything.';
const REVIEW_NOTE = 'Polls waiting on a Lead. Approving posts it straight away and DMs the ' +
  'person who asked; denying DMs them the reason you type.';
const RECUR_NOTE = 'Polls that open again on their own. Pausing leaves everything it has ' +
  'already opened alone; so does deleting it.';
const CLOSED_NOTE = 'How every finished poll went. The export is a CSV of the totals, plus ' +
  'one row per voter when the poll kept them.';
const ARCHIVE_NOTE = 'Polls older than poll_archive_days. The totals are kept forever; the ' +
  'per-voter rows may have been dropped, and the export says so when they were.';
const CREATE_NOTE = 'The same rules as the /poll panel in Discord — Black Bloc picks the surface ' +
  'from what you ask for and tells you which one it picked.';
const SETTINGS_NOTE = 'Who may start a poll, how long one runs, where a poll made here goes, ' +
  'and when a finished one moves to the archive.';

const makeOne = () => textAction('Create a poll', () => goToSection('create-a-poll'));

const NO_OPEN = 'Nothing is taking votes right now. Start one below.';
const NO_REVIEW = 'Nobody is waiting on a Lead. A poll only waits when poll_review_mode is on.';
const NO_RECUR = 'No poll repeats on its own yet. Repeat… while writing one on the /poll panel in Discord starts one.';
const NO_CLOSED = 'No poll has finished yet.';
const NO_ARCHIVE = 'Nothing has been archived yet.';
const NEED_A_QUESTION = 'Write the question first — it is the heading everybody votes under.';
const NEED_OPTIONS = 'A poll needs at least two options.';
const NEED_A_START = 'A date poll needs a start date, like 2026-09-05.';

const STATUS_TONE = {
  open: 'ok',
  pending_review: 'warn',
  closed: null,
  cancelled: null,
  denied: null,
  archived: null,
};

const state = { page: 1 };

let refresh = () => {};

function said(row) {
  return String(row.status || '').replace(/_/g, ' ');
}

function totalOf(row) {
  if (typeof row.total_votes === 'number') return row.total_votes;
  return (row.options || []).reduce((sum, option) => sum + (option.votes || 0), 0);
}

/**
 * The same reading as the embed's bar chart, drawn rather than typed: one row
 * per option, widest first, and the winner marked only when there is exactly
 * one - a tie that marks two winners is the thing this is careful about.
 */
function resultBars(row) {
  const options = (row.options || []).slice()
    .sort((a, b) => (b.votes || 0) - (a.votes || 0) || a.position - b.position);
  if (options.length === 0) return sayNothing('This poll has no options stored.');
  const total = totalOf(row) || 0;
  return el('div', { class: 'pollbars' }, options.map((option) => {
    const share = total > 0 ? Math.round((100 * (option.votes || 0)) / total) : 0;
    return el('div', {
      class: 'pollbar-row',
      'data-winner': row.winner_position === option.position ? 'true' : undefined,
    }, [
      el('span', { class: 'pollbar-name', text: option.label, title: option.label }),
      el('span', { class: 'pollbar-track' }, [
        el('span', { class: 'pollbar-fill', style: `width: ${share}%` }),
      ]),
      el('span', {
        class: 'pollbar-count',
        text: `${option.votes || 0} · ${share}%`,
      }),
    ]);
  }));
}

function closesCell(row) {
  if (!row.closes_at) return el('span', { class: 'cell-quiet', text: 'not posted yet' });
  const until = untilWhen(row.closes_at);
  return el('span', {
    title: until.title,
    text: until.days < 0 ? 'overdue' : `closes ${until.text}`,
  });
}

function surfaceChip(row) {
  if (row.surface !== 'panel') return badge('native');
  const why = row.anonymous
    ? 'it is anonymous'
    : row.results === 'close'
      ? 'its bars stay hidden until it closes'
      : 'it has more options than a Discord poll carries';
  const chip = badge('panel', 'warn');
  chip.setAttribute('title', `Buttons rather than a Discord poll, because ${why}.`);
  return chip;
}

function pollActions(row, say) {
  const end = button('End now', async () => {
    const sure = await ask({
      title: `End ${row.question}?`,
      body: [
        'The vote closes at Discord, the result is posted under it, and this cannot be undone.',
      ],
      confirmLabel: 'End it',
      tone: 'warn',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/polls/${encodeURIComponent(row.id)}/end`, 'POST', {}),
      (found) => found?.message || 'Closed.',
    );
    if (done.ok) {
      keepSaying('open', say);
      refresh();
    }
  }, { tone: 'warn' });

  const cancel = button('Cancel', async () => {
    const sure = await ask({
      title: `Cancel ${row.question}?`,
      body: ['The vote stops and no result is published. Nobody is told.'],
      confirmLabel: 'Cancel it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/polls/${encodeURIComponent(row.id)}/cancel`, 'POST', {}),
      (found) => found?.message || 'Cancelled.',
    );
    if (done.ok) {
      keepSaying('open', say);
      refresh();
    }
  }, { tone: 'danger' });

  return el('div', { class: 'bar' }, [end, cancel]);
}

function openSection(rows, say) {
  const one = section('Open polls', OPEN_NOTE, { count: rows.length, open: true });
  one.body.append(
    table([
      { label: 'Question', cell: (row) => row.question, className: 'wrap' },
      { label: 'Kind', help: 'Single choice, multiple choice, or a date poll.', cell: (row) => badge(row.kind) },
      {
        label: 'Surface',
        help: 'Whether the poll is Discord’s own poll widget or the bot’s buttons.',
        cell: surfaceChip,
      },
      { label: 'Votes', help: 'Every vote cast so far, across all the options.', cell: (row) => String(totalOf(row)) },
      { label: 'Where', cell: (row) => nameNode(row.channel_id, row.channel_name) },
      { label: 'Closes', help: 'When voting stops. Hover for the exact time.', cell: closesCell },
      { label: '', cell: (row) => pollActions(row, say) },
    ], rows, { empty: NO_OPEN, emptyAction: makeOne(), foot: { noun: 'open poll', total: rows.length } }),
    say,
  );
  return one.node;
}

function reviewCard(row, say) {
  const approve = button('Approve', async () => {
    const done = await run(
      say,
      () => send(`/api/polls/requests/${encodeURIComponent(row.id)}/approve`, 'POST', {}),
      (found) => found?.message || 'Approved.',
    );
    if (done.ok) {
      keepSaying('review', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  const deny = button('Deny', async () => {
    const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — they are sent this' });
    const sure = await ask({
      title: `Say no to ${row.creator_name || row.creator_id}?`,
      body: [
        'They are DM’d exactly what you type here, and the poll is never posted.',
        field('Reason', reason, 'Say why — they are sent this word for word.'),
      ],
      confirmLabel: 'Deny it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => send(`/api/polls/requests/${encodeURIComponent(row.id)}/deny`, 'POST', {
        reason: reason.value.trim(),
      }),
      (found) => found?.message || 'Denied, and they have been told why.',
    );
    if (done.ok) {
      keepSaying('review', say);
      refresh();
    }
  }, { tone: 'danger', small: false });

  const asked = ago(row.created_at);
  return card(null, [
    el('div', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: row.question }),
      el('span', {
        class: 'rowlist-note',
        title: asked.title,
        text: `${row.creator_name || row.creator_id} asked ${asked.text} · ${row.kind} · ` +
          `${(row.options || []).length} option(s) · open for ${row.hours}h`,
      }),
    ]),
    el('ol', { class: 'plain-list' }, (row.options || []).map((option) =>
      el('li', { text: option.label }))),
    bar([approve, deny]),
  ]);
}

function reviewSection(rows, say) {
  const one = section('Pending review', REVIEW_NOTE, { count: rows.length, open: rows.length > 0 });
  one.body.append(
    rows.length === 0
      ? sayNothing(NO_REVIEW, linkAction('Where review is switched on', '/settings.html'))
      : el('div', { class: 'section-body' }, rows.map((row) => reviewCard(row, say))),
    say,
  );
  return one.node;
}

function recurActions(row, say) {
  const flip = button(row.paused ? 'Start it' : 'Pause', async () => {
    const done = await run(
      say,
      () => send(`/api/polls/recurrences/${encodeURIComponent(row.id)}/pause`, 'POST', {
        paused: !row.paused,
      }),
      (found) => found?.message || (row.paused ? 'Running again.' : 'Paused.'),
    );
    if (done.ok) {
      keepSaying('recurring', say);
      refresh();
    }
  }, { tone: row.paused ? null : 'quiet' });

  const drop = button('Delete', async () => {
    const sure = await ask({
      title: `Stop ${row.question} repeating?`,
      body: ['It never opens again. Polls it has already opened are untouched.'],
      confirmLabel: 'Delete it',
    });
    if (!sure) return;
    const done = await run(
      say,
      () => api(`/api/polls/recurrences/${encodeURIComponent(row.id)}`, { method: 'DELETE' }),
      (found) => found?.message || 'Deleted.',
    );
    if (done.ok) {
      keepSaying('recurring', say);
      refresh();
    }
  }, { tone: 'danger' });

  return el('div', { class: 'bar' }, [flip, drop]);
}

function nextCell(row) {
  if (row.paused) return badge('paused', 'warn');
  if (!row.next_at) return el('span', { class: 'cell-quiet', text: 'not scheduled' });
  const until = untilWhen(row.next_at);
  return el('span', { title: until.title, text: until.text });
}

function recurringSection(rows, say) {
  const running = rows.filter((row) => !row.paused).length;
  const one = section('Repeating', RECUR_NOTE, { count: running || null });
  one.body.append(
    table([
      { label: 'Question', cell: (row) => row.question, className: 'wrap' },
      { label: 'Kind', help: 'Single choice, multiple choice, or a date poll.', cell: (row) => badge(row.kind) },
      { label: 'How often', cell: (row) => row.cadence_said, className: 'wrap' },
      { label: 'Next', help: 'When this one is due to be posted again. Paused ones say so.', cell: nextCell },
      { label: 'Where', cell: (row) => nameNode(row.channel_id, row.channel_name) },
      { label: 'Open for', help: 'How long each posting stays open for votes.', cell: (row) => `${row.hours}h` },
      { label: '', cell: (row) => recurActions(row, say) },
    ], rows, { empty: NO_RECUR, foot: { noun: 'repeating poll', total: rows.length } }),
    say,
  );
  return one.node;
}

function exportLink(row) {
  return el('a', {
    class: 'btn quiet small',
    href: `/api/polls/${encodeURIComponent(row.id)}/export.csv`,
    text: 'Export CSV',
  });
}

function closedCard(row) {
  const ended = ago(row.closed_at);
  return card(null, [
    el('div', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: row.question }),
      el('span', {
        class: 'rowlist-note',
        title: ended.title,
        text: `${ended.text} · ${totalOf(row)} vote(s) · ${row.kind} · ` +
          `started by ${row.creator_name || row.creator_id}`,
      }),
    ]),
    bar([badge(said(row), STATUS_TONE[row.status] ?? null), surfaceChip(row)]),
    row.deny_reason ? el('p', { class: 'section-note', text: `Why not: ${row.deny_reason}` }) : null,
    resultBars(row),
    bar([exportLink(row)]),
  ]);
}

function closedSection(payload, rows) {
  const one = section('Closed', CLOSED_NOTE, { count: payload.total ?? rows.length });
  one.body.append(
    rows.length === 0
      ? sayNothing(NO_CLOSED, makeOne())
      : el('div', { class: 'section-body' }, rows.map(closedCard)),
    pager({
      page: state.page,
      hasMore: rows.length > 0 && state.page * CLOSED_PER_PAGE < (payload.total ?? 0),
      count: rows.length,
      onPage: (to) => {
        state.page = Math.max(1, to);
        return refresh();
      },
    }),
  );
  return one.node;
}

function archiveSection(rows) {
  const one = section('Archive', ARCHIVE_NOTE, { count: rows.length || null });
  one.body.append(foldout(
    'Archived polls',
    [rows.length === 0
      ? sayNothing(NO_ARCHIVE, makeOne())
      : el('div', { class: 'section-body' }, rows.map(closedCard))],
    { count: rows.length },
  ));
  return one.node;
}

function optionRow(value, onChange) {
  const box = el('input', { class: 'input', type: 'text', value: value || '', placeholder: 'an answer' });
  box.addEventListener('input', onChange);
  const node = el('div', { class: 'formrow' }, [
    field('Option', box),
    bar([button('Remove', () => {
      node.remove();
      onChange();
    }, { tone: 'quiet' })]),
  ]);
  return { node, read: () => box.value.trim() };
}

/**
 * The sentence under the Create button, rebuilt on every keystroke: what
 * pressing it will do, in the words the bot itself would use. The surface is
 * derived here exactly as black_bloc/polls.py:surface_for derives it, so the
 * page never promises a Discord poll the bot would make a panel.
 */
function outcomeOf(form) {
  const question = form.question.value.trim();
  if (!question) return NEED_A_QUESTION;
  const labels = form.labels();
  if (form.kind.value === 'date' && !form.start.value.trim()) return NEED_A_START;
  if (labels.length < 2) return NEED_OPTIONS;
  if (labels.length > PANEL_CAP) {
    return `${labels.length} options is more than the ${PANEL_CAP} Black Bloc can put on one ` +
      'poll. Cut it down and the sentence here will say what happens.';
  }
  const anonymous = form.anonymous.readValue() === 'true';
  const hidden = form.results.readValue() === 'close';
  const why = anonymous
    ? 'nobody can be shown who voted'
    : hidden
      ? 'the bars stay hidden until it closes'
      : labels.length > NATIVE_CAP
        ? `${labels.length} options is more than a Discord poll carries`
        : null;
  const where = form.channelName();
  const hours = Number(form.hours.value) || 24;
  const shape = why
    ? `a Black Bloc panel — buttons rather than Discord's own poll, because ${why}`
    : "a Discord poll, on Discord's own voting UI";
  const held = form.review
    ? ' A Lead has to approve it before anybody sees it.'
    : '';
  const thread = form.thread.readValue() === 'true'
    ? ' A discussion thread opens under it.'
    : '';
  return `Posts “${question}” in ${where} with ${labels.length} options, open for ${hours} ` +
    `hour(s), as ${shape}.${held}${thread}`;
}

async function createForm(say) {
  const question = el('input', { class: 'input', type: 'text', placeholder: 'what you are asking' });
  const kind = el('select', { class: 'input' });
  for (const [value, label] of KINDS) kind.append(el('option', { value, text: label }));
  const hours = el('input', { class: 'input', type: 'number', min: '1', max: '768', value: '24' });
  const where = await channelSelect(null);
  const ping = await roleSelect(null);
  const anonymous = segment([{ value: 'false', label: 'Named' }, { value: 'true', label: 'Anonymous' }], 'false');
  const results = segment([{ value: 'live', label: 'Live bars' }, { value: 'close', label: 'Hidden until close' }], 'live');
  const thread = segment([{ value: 'false', label: 'No thread' }, { value: 'true', label: 'Open a thread' }], 'false');
  const start = el('input', { class: 'input', type: 'text', placeholder: '2026-09-05 or 2026-09-05 19:00' });
  const slots = el('input', { class: 'input', type: 'number', min: '2', max: '25', value: '5' });
  const step = el('input', { class: 'input', type: 'number', min: '1', max: '168', value: '1' });
  const stepUnit = segment([{ value: 'days', label: 'Days' }, { value: 'hours', label: 'Hours' }], 'days');

  const list = el('div');
  const outcome = el('p', { class: 'section-note' });
  const options = [];
  const form = {
    question,
    kind,
    hours,
    anonymous,
    results,
    thread,
    start,
    review: false,
    labels: () => (GENERATED[kind.value]
      ? GENERATED[kind.value]
      : kind.value === 'date'
        ? Array.from({ length: Math.max(0, Number(slots.value) || 0) }, (v, n) => `slot ${n + 1}`)
        : options.map((one) => one.read()).filter(Boolean)),
    channelName: () => {
      const picked = readSelect(where, false);
      const chosen = where.options[where.selectedIndex];
      return picked && chosen ? chosen.textContent : 'the default channel';
    },
  };
  const repaint = () => {
    outcome.textContent = outcomeOf(form);
  };

  const addOption = (value) => {
    const made = optionRow(value, repaint);
    options.push(made);
    list.append(made.node);
    repaint();
  };
  addOption('');
  addOption('');

  const typedBlock = el('div', {}, [
    el('h3', { text: 'Options' }),
    list,
    bar([button('Add option', () => addOption(''), { tone: 'quiet' })]),
  ]);
  const dateBlock = el('div', { class: 'formrow' }, [
    field('First slot', start, 'A date, or a date and a time when the hour matters.'),
    field('How many slots', slots, 'Two to twenty-five.'),
    field('Gap between slots', step),
    field('Counted in', stepUnit),
  ]);

  const paintKind = () => {
    typedBlock.hidden = Boolean(GENERATED[kind.value]) || kind.value === 'date';
    dateBlock.hidden = kind.value !== 'date';
    repaint();
  };
  kind.addEventListener('change', paintKind);
  for (const box of [question, hours, start, slots, step]) box.addEventListener('input', repaint);
  where.addEventListener('change', repaint);
  for (const seg of [anonymous, results, thread, stepUnit]) {
    seg.addEventListener('click', () => setTimeout(repaint, 0));
  }
  paintKind();

  const create = button('Create the poll', async () => {
    const body = {
      question: question.value.trim(),
      kind: kind.value,
      hours: Number(hours.value) || 24,
      anonymous: anonymous.readValue() === 'true',
      results: results.readValue(),
      auto_thread: thread.readValue() === 'true',
    };
    const channelId = readSelect(where, false);
    if (channelId) body.channel_id = channelId;
    const roleId = readSelect(ping, false);
    if (roleId) body.ping_role_id = roleId;
    if (kind.value === 'date') {
      body.start = start.value.trim();
      body.slots = Number(slots.value) || 5;
      body.step = Number(step.value) || 1;
      body.step_unit = stepUnit.readValue();
    } else if (!GENERATED[kind.value]) {
      body.options = options.map((one) => one.read()).filter(Boolean);
    }
    const done = await run(
      say,
      () => send('/api/polls', 'POST', body),
      (found) => [found?.message, found?.note].filter(Boolean).join(' '),
    );
    if (done.ok) {
      keepSaying('create', say);
      refresh();
    }
  }, { tone: 'warn', small: false });

  return card('Create a poll', [
    el('div', { class: 'formrow' }, [
      field('Question', question),
      field('Kind', kind),
      field('Open for, hours', hours, 'One hour to 32 days — Discord counts in whole hours.'),
    ]),
    typedBlock,
    dateBlock,
    el('div', { class: 'formrow' }, [
      field('Channel', where, 'Blank uses poll_channel_id.'),
      field('Ping', ping, 'Blank pings nobody.'),
      field('Voters', anonymous, 'Anonymous forces a Black Bloc panel.'),
      field('Results', results, 'Hidden until close forces one too.'),
      field('Thread', thread),
    ]),
    outcome,
    bar([create]),
    say,
  ]);
}

function createSection(node) {
  const one = section('Create a poll', CREATE_NOTE, { open: true });
  one.body.append(node);
  return one.node;
}

async function load() {
  const [openBody, waiting, repeating, settled, archived, allSettings] = await Promise.all([
    api('/api/polls?status=open&per_page=100'),
    api('/api/polls/requests'),
    api('/api/polls/recurrences'),
    api(`/api/polls?status=${SETTLED}&page=${state.page}&per_page=${CLOSED_PER_PAGE}`),
    api('/api/polls?status=archived&per_page=100'),
    settings(true),
  ]);

  const open = listOf(openBody, 'polls');
  const pending = listOf(waiting, 'polls');
  const recurring = listOf(repeating, 'recurrences');
  const closed = listOf(settled, 'polls');
  const archive = listOf(archived, 'polls');

  await names(idsIn(
    open.concat(pending, closed, archive, recurring),
    ['channel_id', 'creator_id', 'ping_role_id'],
  ));

  const poll = settingsNamespace(allSettings, 'poll');
  const mode = poll.find((spec) => spec.key === MODE_KEY);
  const settingSpecs = poll.filter((spec) => spec.key !== MODE_KEY);

  const openSay = sayAgain('open', notice());
  const reviewSay = sayAgain('review', notice());
  const recurSay = sayAgain('recurring', notice());
  const createSay = sayAgain('create', notice());

  const switchboard = section('Polls', SWITCH_HELP);
  const flip = mode ? modeSwitch(mode, { onSaved: () => refresh() }) : null;
  switchboard.body.append(flip
    ? card('Polls on this server', [field('Now', flip.node, SWITCH_HELP), flip.say])
    : sayNothing(NO_MODE_KEY));

  const settingsBox = section('Settings', SETTINGS_NOTE, { count: settingSpecs.length || null });
  settingsBox.body.append(await settingsPanel(settingSpecs, {
    where: 'Settings',
    empty: 'The bot registers no poll settings beyond the switch above.',
  }));

  document.getElementById('dash').replaceChildren(
    switchboard.node,
    reviewSection(pending, reviewSay),
    openSection(open, openSay),
    recurringSection(recurring, recurSay),
    closedSection(settled, closed),
    archiveSection(archive),
    createSection(await createForm(createSay)),
    settingsBox.node,
    await logsSection('poll'),
  );
}

refresh = start({ tab: 'polls', load });
