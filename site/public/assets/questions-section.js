import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { logsTable } from './logs.js';
import {
  ask,
  bar,
  button,
  card,
  el,
  foldout,
  idsIn,
  keepSaying,
  notice,
  run,
  sayAgain,
  sayNothing,
  section,
  settingsPanel,
  table,
  when,
} from './ui.js';

const TITLE = 'Weekly questions';
const SLUG = 'questions';
const KEY_PREFIX = 'question_';
const LOG_ROWS = 50;
const NO_LOGS = 'Nothing has happened to the weekly questions yet.';
const WORDING_KEYS = ['question_template', 'question_thread_name_template', 'question_warn_template'];
const STATE_WORDS = {
  pending: 'waiting',
  posted: 'posted',
  skipped: 'skipped',
  skipped_empty: 'skipped — the queue was empty',
  missed: 'missed',
  taken_down: 'taken down',
};
const BY_WORDS = { owner: 'by the owner', bot: 'by Black Bloc' };
const STATUS_WORDS = { removed: 'removed', skipped: 'skipped' };

let refresh = () => {};

const path = (id, tail = '') => `/api/questions/${encodeURIComponent(id)}${tail}`;

async function act(say, where, work, okText) {
  const done = await run(say, work, okText);
  if (done.ok) {
    keepSaying(where, say);
    refresh();
  }
  return done;
}

function weekCard(payload) {
  const say = notice();
  const status = payload.state || 'pending';
  const moves = [];
  if (payload.mode !== 'off' && listOf(payload, 'queue').length && status !== 'posted') {
    moves.push(button('Post now', async () => {
      const first = listOf(payload, 'queue')[0];
      const sure = await ask({
        title: 'Post it now?',
        body: [first ? first.body : ''],
        confirmLabel: 'Post now',
        tone: null,
      });
      if (sure) await act(say, 'questions.week', () => send('/api/questions/post-now', 'POST', {}), 'Posted.');
    }, { small: false }));
  }
  if (status === 'pending' || status === 'skipped_empty') {
    moves.push(button('Skip this week', () => act(say, 'questions.week', () => send('/api/questions/skip', 'POST', {}), (found) => found?.message || 'Skipped.'), { tone: 'quiet' }));
  }
  if (status === 'skipped') {
    moves.push(button('Undo skip', () => act(say, 'questions.week', () => send('/api/questions/unskip', 'POST', {}), (found) => found?.message || 'Back on.'), { tone: 'quiet' }));
  }
  const lines = [
    el('p', { class: 'row-detail', text: `${when(payload.slot_at)} · ${STATE_WORDS[status] || status} · ${payload.mode}` }),
  ];
  if (!payload.owner_set) {
    lines.push(el('p', { class: 'row-note', text: 'question_owner_user_id is not set, so Black Bloc posts every week itself.' }));
  }
  return card('This week', [...lines, moves.length ? bar(moves) : null, say, sayAgain('questions.week', say)].filter(Boolean));
}

function addCard() {
  const say = notice();
  const box = el('textarea', { class: 'input', rows: '5', placeholder: 'One question per line' });
  const add = button('Add', async () => {
    const done = await act(say, 'questions.add', () => send('/api/questions', 'POST', { text: box.value }), (found) => found?.message || 'Added.');
    if (done.ok) box.value = '';
  }, { small: false });
  return card('Add questions', [box, bar([add]), say, sayAgain('questions.add', say)]);
}

function editInPlace(row, say) {
  const holder = el('div', { class: 'question-body' });
  const show = () => holder.replaceChildren(el('span', { text: row.body }));
  holder.addEventListener('dblclick', () => {
    const input = el('textarea', { class: 'input', rows: '2' });
    input.value = row.body;
    const save = button('Save', () => act(say, 'questions.queue', () => send(path(row.id), 'PUT', { body: input.value }), (found) => found?.message || 'Saved.'));
    holder.replaceChildren(input, bar([save, button('Cancel', show, { tone: 'quiet' })]));
    input.focus();
  });
  show();
  return holder;
}

function queueCard(rows) {
  const say = notice();
  const moveTo = (row, direction) => () => act(say, 'questions.queue', () => send(path(row.id, '/move'), 'POST', { direction }), (found) => found?.message || 'Moved.');
  const edit = (row) => () => {
    const node = document.querySelector(`[data-question="${row.id}"] .question-body`);
    if (node) node.dispatchEvent(new MouseEvent('dblclick'));
  };
  const list = table([
    { label: '#', cell: (row, at) => String(at + 1), className: 'mono' },
    { label: 'Question', cell: (row) => el('div', { 'data-question': String(row.id) }, [editInPlace(row, say)]) },
    {
      label: '',
      cell: (row, at) => bar([
        at > 0 ? button('Up', moveTo(row, 'up'), { tone: 'quiet' }) : null,
        at < rows.length - 1 ? button('Down', moveTo(row, 'down'), { tone: 'quiet' }) : null,
        button('Edit', edit(row), { tone: 'quiet' }),
        button('Remove', async () => {
          const sure = await ask({ title: 'Remove this question?', body: [row.body], confirmLabel: 'Remove' });
          if (sure) await act(say, 'questions.queue', () => api(path(row.id), { method: 'DELETE' }), (found) => found?.message || 'Removed.');
        }, { tone: 'danger' }),
      ].filter(Boolean)),
    },
  ], rows, { empty: 'The queue is empty.' });
  return card('Queue', [list, say, sayAgain('questions.queue', say)], { count: rows.length });
}

function historyFold(rows) {
  const say = notice();
  const list = table([
    { label: 'When', cell: (row) => (row.resolved_at ? when(row.resolved_at) : null) },
    { label: 'Question', cell: (row) => row.body },
    { label: 'What happened', cell: (row) => (row.status === 'posted' ? `posted ${BY_WORDS[row.posted_by] || ''}`.trim() : STATUS_WORDS[row.status] || row.status) },
    {
      label: '',
      cell: (row) => {
        const moves = [];
        if (row.url) moves.push(el('a', { class: 'btn quiet small', href: row.url, target: '_blank', rel: 'noopener', text: 'Open in Discord' }));
        if (row.status === 'posted' && row.posted_by === 'bot') {
          moves.push(button('Take it down', async () => {
            const sure = await ask({ title: 'Take it down?', body: ['Black Bloc deletes its post and the question goes back to the top of the queue.'], confirmLabel: 'Take it down' });
            if (sure) await act(say, 'questions.history', () => send(path(row.id, '/take-down'), 'POST', {}), (found) => found?.message || 'Taken down.');
          }, { tone: 'danger' }));
        }
        if (row.status === 'removed') {
          moves.push(button('Put back', () => act(say, 'questions.history', () => send(path(row.id, '/requeue'), 'POST', {}), (found) => found?.message || 'Back in the queue.'), { tone: 'quiet' }));
        }
        return moves.length ? bar(moves) : null;
      },
    },
  ], rows, { empty: 'Nothing has gone up yet.' });
  return foldout('History', [list, say, sayAgain('questions.history', say)], { count: rows.length });
}

async function settingsFold(specs) {
  if (!specs.length) return foldout('Settings', [sayNothing('The bot reported no question_ settings.')], { count: 0 });
  const wording = specs.filter((spec) => WORDING_KEYS.includes(spec.key));
  const operational = specs.filter((spec) => !WORDING_KEYS.includes(spec.key));
  return foldout('Settings', [
    await settingsPanel(operational, { where: TITLE, onSaved: () => refresh() }),
    await settingsPanel(wording, { where: 'Wording' }),
  ], { count: specs.length });
}

async function logsFold() {
  const payload = await api(`/api/actions?feature=core&q=question&per_page=${LOG_ROWS}`);
  const rows = listOf(payload, 'actions').filter((row) => /^(web\.)?question\./.test(String(row.kind)));
  await names(idsIn(rows, ['actor_id', 'target_id']));
  return foldout('Logs', [logsTable(rows, NO_LOGS)], { count: rows.length });
}

/** The Weekly questions section of the Posts page; `reload` redraws the page after a write. */
export async function questionsSection(reload) {
  refresh = reload;
  const [payload, all] = await Promise.all([api('/api/questions'), settings()]);
  const specs = settingsNamespace(all, 'core').filter((spec) => spec.key.startsWith(KEY_PREFIX));
  const queue = listOf(payload, 'queue');
  const asked = location.hash === `#sect-${SLUG}`;
  const one = section(TITLE, null, { count: queue.length, id: SLUG, open: asked });
  one.body.append(
    weekCard(payload),
    addCard(),
    queueCard(queue),
    historyFold(listOf(payload, 'history')),
    await settingsFold(specs),
    await logsFold(),
  );
  one.node.setAttribute('data-span', 'full');
  if (asked) {
    requestAnimationFrame(() => {
      one.details.open = true;
      one.node.scrollIntoView({ block: 'start' });
    });
  }
  return one.node;
}
