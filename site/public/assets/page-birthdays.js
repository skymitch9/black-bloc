import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsSection } from './logs.js';
import {
  ask,
  bar,
  boldParts,
  button,
  card,
  el,
  field,
  idsIn,
  keepSaying,
  memberPicker,
  nameNode,
  namespaceSettings,
  notice,
  run,
  sayAgain,
  sayNothing,
  searchOver,
  section,
  table,
  templateEditor,
} from './ui.js';

const CHANGE = 'Change';
const REMOVE = 'Remove';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

let refresh = () => {};

const TEMPLATE_KEY = 'birthday_template';
const COLOR_KEY = 'birthday_color';
const SAMPLE = { name: 'Casey', age: '30' };
const BIRTHDAY_FEATURE = 'birthday';
const POST_KEYS = {
  button: 'birthday_post_button',
  confirm: 'birthday_post_confirm',
  unsent: 'birthday_post_unsent_label',
  again: 'birthday_post_again_label',
};

/** The staff door that posts today's wishes now; every word on it is a birthday_post_* key. */
function postTodayCard(specs) {
  const words = {};
  for (const [name, key] of Object.entries(POST_KEYS)) {
    const spec = specs.find((one) => one.key === key);
    if (!spec) return null;
    words[name] = String(spec.value ?? spec.default ?? '');
  }
  const say = notice();
  const moves = el('div', { class: 'post-today-moves' });
  moves.hidden = true;
  const go = (again) => async () => {
    moves.hidden = true;
    await run(
      say,
      () => send('/api/birthdays/post-today', 'POST', { again }),
      (found) => found?.said || 'Done.',
    );
  };
  moves.append(
    el('p', { class: 'field-help' }, boldParts(words.confirm)),
    bar([
      button(words.unsent, go(false)),
      button(words.again, go(true), { tone: 'warn' }),
      button('Cancel', () => { moves.hidden = true; }, { tone: 'quiet' }),
    ]),
  );
  const open = button(words.button, () => { moves.hidden = !moves.hidden; }, { small: false });
  return el('div', { class: 'post-today' }, [open, moves, say]);
}

/** A6: the card the bot itself would post, redrawn as you type. */
async function wordingCard(spec, color) {
  const swatch = el('span', { class: 'swatch', style: color ? `--swatch: ${color}` : undefined });
  const made = await templateEditor(spec, {
    sample: () => SAMPLE,
    preview: { feature: BIRTHDAY_FEATURE, sample: () => SAMPLE },
  });
  const preview = card('What a birthday wish looks like', [
    el('p', { class: 'field-help' }, [
      'Filled in with a made-up member. The embed’s colour is ',
      swatch,
      color ? ` ${color}` : ' not set',
      ', from birthday_color.',
    ]),
    made.mock.node,
    made.mock.say,
    made.say,
  ]);
  return [made.row.node, preview];
}

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
    if (done.ok) {
      keepSaying('birthdays.set', say);
      refresh();
    }
  });

  const node = card('Set a birthday', [
    picker.node,
    el('div', { class: 'formrow dateline' }, [field('Month', month), field('Day', day), field('Year', year)]),
    el('p', { class: 'field-help', text: 'The year is optional, and only used when birthday_show_age is on.' }),
    bar([save]),
    sayAgain('birthdays.set', say),
  ]);

  const fill = (row) => {
    picker.set({ id: row.user_id, name: row.user_name });
    month.value = String(Number(row.month) || 1);
    day.value = String(row.day ?? 1);
    year.value = row.year ? String(row.year) : '';
    say.say('');
    node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    day.focus({ preventScroll: true });
  };

  return { node, fill };
}

async function load() {
  const [payload, allSettings] = await Promise.all([api('/api/birthdays'), settings(true)]);
  const rows = listOf(payload, 'birthdays');
  const birthday = settingsNamespace(allSettings, 'birthday');
  const template = birthday.find((spec) => spec.key === TEMPLATE_KEY);
  const color = birthday.find((spec) => spec.key === COLOR_KEY);
  await names(idsIn(rows, ['user_id']));

  const aside = document.getElementById('page-aside');
  const poster = postTodayCard(birthday);
  if (aside) aside.replaceChildren(...(poster ? [poster] : []));

  const say = notice();
  const setter = setCard();
  const byMonth = new Map();
  for (const row of rows) {
    const key = Number(row.month) || 0;
    byMonth.set(key, (byMonth.get(key) || []).concat([row]));
  }

  const monthTable = (list) => table([
    { label: 'Day', cell: (row) => String(row.day), className: 'mono' },
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.user_name) },
    { label: 'Year', cell: (row) => (row.year ? String(row.year) : null) },
    {
      label: 'Wished',
      cell: (row) => button(row.opted_in === false ? 'opted out' : 'yes', async () => {
        const done = await run(
          say,
          () => send(`/api/birthdays/${encodeURIComponent(row.user_id)}/optin`, 'POST', {
            opted_in: row.opted_in === false,
          }),
          (found) => found?.message || 'Changed.',
        );
        if (done.ok) {
          keepSaying('birthdays.months', say);
          refresh();
        }
      }, { tone: row.opted_in === false ? 'warn' : 'quiet' }),
    },
    { label: 'From', cell: (row) => row.source },
    {
      label: '',
      cell: (row) => bar([button(CHANGE, () => setter.fill(row), { tone: 'quiet' }), button(REMOVE, async () => {
        const sure = await ask({
          title: `Remove ${row.user_name || row.user_id}’s birthday?`,
          body: ['Black Bloc forgets the date. They can set it again themselves.'],
          confirmLabel: 'Remove it',
        });
        if (!sure) return;
        const done = await run(say, () => api(`/api/birthdays/${encodeURIComponent(row.user_id)}`, { method: 'DELETE' }), 'Removed.');
        if (done.ok) {
          keepSaying('birthdays.months', say);
          refresh();
        }
      }, { tone: 'danger' })]),
    },
    // One filter over all twelve months, not a box on each — a month with two
    // people in it does not need its own search.
  ], list.slice().sort((a, b) => a.day - b.day), { search: false });

  const months = section('By month', `${rows.length} birthday(s) stored.`, { count: rows.length });
  if (rows.length === 0) {
    months.body.append(sayNothing('No birthdays are stored yet.'));
  } else {
    const box = el('div', { class: 'section-body' });
    for (let at = 1; at <= 12; at += 1) {
      const list = byMonth.get(at);
      if (!list || list.length === 0) continue;
      box.append(card(MONTHS[at - 1], [monthTable(list)]));
    }
    months.body.append(
      searchOver(box, {
        label: 'Search the birthday list',
        placeholder: 'a name, a month or a day',
        noun: 'month(s)',
        empty: 'No month has anybody matching that.',
      }),
      box,
    );
  }
  months.body.append(sayAgain('birthdays.months', say));

  const add = section('Add or change one');
  add.body.append(setter.node);

  const wording = section('Birthday wording');
  if (template) {
    wording.body.append(...await wordingCard(template, color ? color.value : null));
  } else {
    wording.body.append(sayNothing('The bot did not report a birthday_template key, so this editor is not shown rather than guessed at.'));
  }

  document.getElementById('dash').replaceChildren(
    add.node,
    months.node,
    wording.node,
    await namespaceSettings('birthday', { omit: [TEMPLATE_KEY] }),
    await logsSection('birthday'),
  );
}

refresh = start({
  tab: 'birthdays',
  load,
});
