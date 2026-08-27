import { api, listOf, names, send } from './api.js';
import { start } from './app.js';
import {
  ask,
  badge,
  bar,
  button,
  card,
  el,
  field,
  idsIn,
  memberPicker,
  nameNode,
  namespaceSettings,
  notice,
  run,
  sayNothing,
  section,
  table,
} from './ui.js';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

let refresh = () => {};

function setCard() {
  const say = notice();
  const picker = memberPicker({ label: 'Member' });
  const month = el('select', { class: 'input' });
  MONTHS.forEach((name, at) => month.append(el('option', { value: String(at + 1), text: name })));
  const day = el('input', { class: 'input', type: 'number', min: '1', max: '31', value: '1' });
  const year = el('input', { class: 'input', type: 'number', min: '1900', max: '2020', placeholder: 'optional' });

  const save = button('Save birthday', async () => {
    if (!picker.id) {
      say.say('Pick the member first.', 'warn');
      return;
    }
    const done = await run(
      say,
      () => send(`/api/birthdays/${encodeURIComponent(picker.id)}`, 'PUT', {
        month: Number(month.value),
        day: Number(day.value),
        year: year.value ? Number(year.value) : null,
      }),
      `Saved. ${picker.name} is down for ${MONTHS[Number(month.value) - 1]} ${day.value}.`,
    );
    if (done.ok) refresh();
  });

  return card('Set a birthday', [
    picker.node,
    el('div', { class: 'formrow' }, [field('Month', month), field('Day', day), field('Year', year, 'Only used when birthday_show_age is on.')]),
    bar([save]),
    say,
  ]);
}

async function load() {
  const payload = await api('/api/birthdays');
  const rows = listOf(payload, 'birthdays');
  await names(idsIn(rows, ['user_id']));

  const say = notice();
  const byMonth = new Map();
  for (const row of rows) {
    const key = Number(row.month) || 0;
    byMonth.set(key, (byMonth.get(key) || []).concat([row]));
  }

  const monthTable = (list) => table([
    { label: 'Day', cell: (row) => String(row.day), className: 'mono' },
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Year', cell: (row) => (row.year ? String(row.year) : null) },
    { label: 'Wished', cell: (row) => (row.opted_in === false ? badge('opted out', 'warn') : badge('yes', 'ok')) },
    { label: 'From', cell: (row) => row.source },
    {
      label: '',
      cell: (row) => button('Remove', async () => {
        const sure = await ask({
          title: `Remove ${row.user_name || row.user_id}’s birthday?`,
          body: ['Black Bloc forgets the date. They can set it again themselves.'],
          confirmLabel: 'Remove it',
        });
        if (!sure) return;
        const done = await run(say, () => api(`/api/birthdays/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }), 'Removed.');
        if (done.ok) refresh();
      }, { tone: 'danger' }),
    },
  ], list.slice().sort((a, b) => a.day - b.day));

  const months = section('By month', `${rows.length} birthday(s) stored.`);
  if (rows.length === 0) months.body.append(sayNothing('No birthdays are stored yet.'));
  for (let at = 1; at <= 12; at += 1) {
    const list = byMonth.get(at);
    if (!list || list.length === 0) continue;
    months.body.append(card(MONTHS[at - 1], [monthTable(list)]));
  }
  months.body.append(say);

  const add = section('Add or change one');
  add.body.append(setCard());

  document.getElementById('dash').replaceChildren(add.node, months.node, await namespaceSettings('birthday'));
}

refresh = start({
  tab: 'birthdays',
  subtitle: 'Who has a birthday stored, by month.',
  load,
});
