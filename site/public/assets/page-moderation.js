import { api, listOf, names, notesOf, send } from './api.js';
import { start } from './app.js';
import {
  ask,
  badge,
  bar,
  button,
  card,
  duration,
  el,
  field,
  idsIn,
  memberPicker,
  nameNode,
  notice,
  pager,
  run,
  section,
  table,
  when,
} from './ui.js';

const KINDS = ['warn', 'timeout', 'kick', 'ban', 'unban'];
const DESTRUCTIVE = ['kick', 'ban', 'unban'];

const state = { page: 1, userFilter: null, userName: null, openCase: null, days: 7 };

let refresh = () => {};

function actionBar() {
  const say = notice();
  const picker = memberPicker({ label: 'Member' });
  const kind = el('select', { class: 'input' });
  for (const one of KINDS) kind.append(el('option', { value: one, text: one }));
  const reason = el('input', { class: 'input', type: 'text', placeholder: 'why — the member is told this' });
  const length = el('input', { class: 'input', type: 'number', min: '60', step: '60', value: '300' });
  const lengthField = field('Timeout length, seconds', length, 'Discord refuses anything over 28 days.');
  const paintLength = () => { lengthField.hidden = kind.value !== 'timeout'; };
  kind.addEventListener('change', paintLength);
  paintLength();

  const go = button('Do it', async () => {
    if (!picker.id) {
      say.say('Pick the member this is about first.', 'warn');
      return;
    }
    const what = kind.value;
    if (DESTRUCTIVE.includes(what)) {
      const sure = await ask({
        title: `${what} ${picker.name}?`,
        body: [
          `This goes through the same path the slash command uses: a case is written, the mod log gets a line and ${picker.name} is told, depending on mod_dm_on_action.`,
          `Reason: ${reason.value.trim() || '(none yet — the bot will refuse without one)'}`,
        ],
        confirmLabel: `Yes, ${what}`,
      });
      if (!sure) return;
    }
    const body = { user_id: picker.id, reason: reason.value.trim() };
    if (what === 'timeout') body.duration = Number(length.value);
    const done = await run(say, () => send(`/api/mod/${what}`, 'POST', body), (found) =>
      found?.message || `Done — ${what} for ${picker.name}.`);
    if (done.ok) refresh();
  }, { tone: 'warn', small: false });

  return card('Take an action', [
    picker.node,
    el('div', { class: 'formrow' }, [field('What', kind), field('Reason', reason)]),
    lengthField,
    bar([go]),
    say,
  ]);
}

async function caseDetail(id) {
  const found = await api(`/api/mod/cases/${encodeURIComponent(id)}`);
  const row = found && found.case ? found.case : found;
  await names([row.user_id, row.moderator_id]);
  const say = notice();
  const apply = button('Apply now', async () => {
    const sure = await ask({
      title: `Apply case ${row.id}?`,
      body: [
        `This carries out what the shadow run only logged: ${(row.actions || [row.kind]).join(', ')} against ${row.user_name || row.user_id}.`,
      ],
      confirmLabel: 'Apply it',
    });
    if (!sure) return;
    const done = await run(say, () => send(`/api/mod/cases/${encodeURIComponent(row.id)}/apply`, 'POST', {}),
      'Applied. The case now says it was carried out.');
    if (done.ok) refresh();
  });

  return card(`Case ${row.id}`, [
    el('div', { class: 'formrow' }, [
      el('p', {}, ['Member: ', nameNode(row.user_id, row.user_name)]),
      el('p', {}, ['Moderator: ', nameNode(row.moderator_id, row.moderator_name)]),
    ]),
    el('p', { text: `${row.kind}${row.duration_s ? ` for ${duration(row.duration_s)}` : ''} · ${when(row.at)} · mode ${row.mode}` }),
    el('p', { text: `Reason: ${row.reason || 'none given'}` }),
    el('p', {}, [
      'Carried out: ',
      row.applied ? badge('yes', 'ok') : badge('no — shadow only', 'warn'),
      ...(Array.isArray(row.failed) && row.failed.length ? [' ', badge(`failed: ${row.failed.join(', ')}`, 'danger')] : []),
    ]),
    row.applied ? null : bar([apply]),
    say,
  ]);
}

async function parity(days) {
  const say = notice();
  const input = el('input', { class: 'input', type: 'number', min: '1', max: '30', value: String(days) });
  const body = el('div');
  const paint = (found) => {
    const report = (found && found.report) || {};
    body.replaceChildren(el('div', { class: 'tiles' }, [
      el('div', { class: 'tile' }, [el('div', { class: 'tile-value', text: String(report.agree ?? '—') }), el('div', { class: 'tile-label', text: 'Both saw it' })]),
      el('div', { class: 'tile' }, [el('div', { class: 'tile-value', text: String(report.carl_only ?? '—') }), el('div', { class: 'tile-label', text: 'Carl only' })]),
      el('div', { class: 'tile' }, [el('div', { class: 'tile-value', text: String(report.bloc_only ?? '—') }), el('div', { class: 'tile-label', text: 'Black Bloc only' })]),
    ]));
    for (const note of notesOf(found)) body.append(el('p', { class: 'field-help', text: note }));
  };

  const first = await api(`/api/mod/parity?days=${encodeURIComponent(days)}`);
  paint(first);

  const again = button('Measure', async () => {
    state.days = Number(input.value) || 7;
    const done = await run(say, () => api(`/api/mod/parity?days=${encodeURIComponent(state.days)}`), 'Measured.');
    if (done.ok) paint(done.found);
  });

  return card('Parity with Carl-bot', [
    el('div', { class: 'formrow' }, [field('Days', input), bar([again])]),
    body,
    say,
  ]);
}

async function load() {
  const query = new URLSearchParams({ page: String(state.page) });
  if (state.userFilter) query.set('user_id', state.userFilter);
  const payload = await api(`/api/mod/cases?${query.toString()}`);
  const rows = listOf(payload, 'cases');
  await names(idsIn(rows, ['user_id', 'moderator_id']));

  const picker = memberPicker({
    label: 'Only this member',
    onPick: (member) => {
      state.userFilter = member ? member.id : null;
      state.userName = member ? member.name : null;
      state.page = 1;
      state.openCase = null;
      refresh();
    },
  });

  const casesTable = table([
    { label: 'Case', cell: (row) => String(row.id), className: 'mono' },
    { label: 'When', cell: (row) => when(row.at), className: 'mono' },
    { label: 'What', cell: (row) => `${row.kind}${row.duration_s ? ` · ${duration(row.duration_s)}` : ''}` },
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'By', cell: (row) => nameNode(row.moderator_id, row.moderator_name) },
    { label: 'Carried out', cell: (row) => (row.applied ? badge('yes', 'ok') : badge('shadow', 'warn')) },
    { label: 'Why', cell: (row) => row.reason, className: 'wrap' },
    {
      label: '',
      cell: (row) => button('Open', () => {
        state.openCase = row.id;
        refresh();
      }, { tone: 'quiet' }),
    },
  ], rows, { empty: state.userFilter ? 'That member has no cases.' : 'No cases have been written yet.' });

  const hasMore = payload && payload.pages ? state.page < payload.pages : rows.length >= 10;

  const cases = section('Cases', state.userName ? `Filtered to ${state.userName}.` : null);
  cases.body.append(
    picker.node,
    casesTable,
    pager({
      page: state.page,
      hasMore,
      count: rows.length,
      onPage: (to) => {
        state.page = Math.max(1, to);
        refresh();
      },
    }),
  );
  if (state.openCase !== null) cases.body.append(await caseDetail(state.openCase));

  const act = section('Action bar', 'Every one of these is the same code path as the slash command, and lands in the same case table.');
  act.body.append(actionBar());

  const compare = section('Parity report');
  compare.body.append(await parity(state.days));

  document.getElementById('dash').replaceChildren(act.node, cases.node, compare.node);
}

refresh = start({
  tab: 'moderation',
  subtitle: 'Cases, the action bar and the Carl parity report.',
  load,
});
