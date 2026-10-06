import { api, refChannels, send, settings, settingsNamespace } from './api.js';
import {
  ask,
  askForm,
  badge,
  bar,
  button,
  card,
  channelLabel,
  channelSelect,
  el,
  field,
  foldout,
  keepSaying,
  limitCounter,
  listFilter,
  modeSwitch,
  notice,
  readSelect,
  run,
  sayAgain,
  sayNothing,
  section,
  settingsPanel,
  when,
} from './ui.js';

const TITLE = 'Sticky messages';
const SLUG = 'sticky';
const MODE_KEY = 'sticky_mode';
const TEXT_MAX = 1800;
const SAID = 'posts.sticky';
const NOTHING_YET = 'No channel has a sticky message.';
const NOTHING_MATCHES = 'No sticky message matches this.';
const GONE = 'a channel the server no longer has';
const POSTABLE = ['text', 'news'];
const NEED_A_CHANNEL = 'Pick the channel it sits in, then save again.';
const NEED_WORDS = 'A sticky message needs some words. Type what it should say and save again.';

const STATE_TONES = { live: 'ok', rehearsing: 'warn', stopped: 'danger' };
const FILTERS = [
  ['all', 'All', null],
  ['running', 'Running', (row) => !row.paused && !row.trouble],
  ['paused', 'Paused', (row) => row.paused && !row.trouble],
  ['stopped', 'Stopped', (row) => Boolean(row.trouble)],
];

const kept = { query: '', filter: 'all' };

function where(channelId, tail = '') {
  return `/api/sticky/${encodeURIComponent(channelId)}${tail}`;
}

function nameOf(row, channels) {
  const found = channels.find((one) => String(one.id) === String(row.channel_id));
  if (found) return channelLabel(found, channels);
  return row.channel_name ? `# ${row.channel_name}` : `${GONE} · ${row.channel_id}`;
}

function rowText(row, channels) {
  return [nameOf(row, channels), row.text, row.state, row.trouble || ''].join(' ');
}

function wordsBox(value = '') {
  const box = el('textarea', {
    class: 'input area',
    id: 'sticky-words',
    rows: '6',
    spellcheck: 'true',
  });
  box.value = value;
  return box;
}

/** The picker's own list, minus the kinds of channel a message cannot sit in. */
async function textChannelSelect() {
  const channels = await refChannels();
  const select = await channelSelect(null, { id: 'sticky-channel' });
  const kinds = new Map(channels.map((one) => [String(one.id), one.type]));
  for (const option of [...select.options]) {
    if (option.value && !POSTABLE.includes(kinds.get(option.value))) option.remove();
  }
  return select;
}

async function saveWords(channelId, text, say, reload) {
  const found = await send(where(channelId), 'PUT', { text });
  say.say(found.message, 'ok');
  keepSaying(SAID, say);
  reload();
}

async function addOne(say, reload) {
  const select = await textChannelSelect();
  const box = wordsBox();
  await askForm({
    title: 'A new sticky message',
    body: [
      field('Channel', select),
      field('What it says', box, limitCounter(box, TEXT_MAX)),
    ],
    confirmLabel: 'Save it',
    tone: 'warn',
    onConfirm: async () => {
      const channelId = readSelect(select, false);
      if (!channelId) return NEED_A_CHANNEL;
      if (!box.value.trim()) return NEED_WORDS;
      await saveWords(channelId, box.value, say, reload);
      return null;
    },
  });
}

async function editOne(row, name, say, reload) {
  const box = wordsBox(row.text);
  await askForm({
    title: name,
    body: [field('What it says', box, limitCounter(box, TEXT_MAX))],
    confirmLabel: 'Save it',
    tone: 'warn',
    onConfirm: async () => {
      if (!box.value.trim()) return NEED_WORDS;
      await saveWords(row.channel_id, box.value, say, reload);
      return null;
    },
  });
}

function actions(row, name, say, reload) {
  const act = async (method, tail) => {
    const done = await run(say, () => send(where(row.channel_id, tail), method, {}), (found) => found.message);
    if (done.ok) {
      keepSaying(SAID, say);
      reload();
    }
  };
  const moves = [button('Edit', () => editOne(row, name, say, reload))];
  if (row.trouble) moves.push(button('Try again', () => act('POST', '/resume'), { tone: 'warn' }));
  else if (row.paused) moves.push(button('Resume', () => act('POST', '/resume'), { tone: 'warn' }));
  else moves.push(button('Pause', () => act('POST', '/pause')));
  moves.push(button('Remove', async () => {
    const sure = await ask({
      title: `Remove the sticky message from ${name}?`,
      body: [row.text],
      confirmLabel: 'Remove it',
    });
    if (sure) await act('DELETE', '');
  }, { tone: 'danger' }));
  return bar(moves);
}

function stateLine(row) {
  const parts = [badge(row.state, STATE_TONES[row.state] || null)];
  if (row.posted_at) parts.push(el('span', { class: 'rowlist-note', text: when(row.posted_at) }));
  if (row.reposts) parts.push(el('span', { class: 'rowlist-note', text: `moved ${row.reposts}×` }));
  return el('span', { class: 'bar' }, parts);
}

function stickyRow(row, channels, say, reload) {
  const name = nameOf(row, channels);
  return el('div', { class: 'rowlist-row', 'data-channel': String(row.channel_id) }, [
    el('div', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name', text: name }),
      el('span', { class: 'rowlist-line', style: 'white-space: pre-wrap', text: row.text }),
      stateLine(row),
      row.trouble ? notice(row.trouble, 'danger') : null,
    ]),
    actions(row, name, say, reload),
  ]);
}

/** The Sticky messages section of the Posts page; `reload` redraws the page after a write. */
export async function stickySection(reload) {
  const [found, channels, registry] = await Promise.all([
    api('/api/sticky'),
    refChannels(),
    settings(),
  ]);
  const rows = Array.isArray(found) ? found : [];
  const specs = settingsNamespace(registry, 'posts')
    .filter((spec) => spec.key.startsWith('sticky_'));
  const mode = specs.find((spec) => spec.key === MODE_KEY);
  const say = sayAgain(SAID, notice());
  const asked = location.hash === `#sect-${SLUG}`;
  const one = section(TITLE, null, { count: rows.length, id: SLUG, open: asked });

  const items = rows.map((row) => ({ row, node: stickyRow(row, channels, say, reload) }));
  const filter = listFilter({
    items,
    value: (item) => item.row,
    text: (row) => rowText(row, channels),
    filters: FILTERS,
    filter: kept.filter,
    query: kept.query,
    label: 'Search the sticky messages',
    placeholder: 'Search the sticky messages…',
    empty: NOTHING_MATCHES,
    onChange: ({ query, filter: key }) => {
      kept.query = query;
      kept.filter = key;
    },
  });
  filter.apply();

  const add = button('New sticky message', () => addOne(say, reload), { tone: 'warn' });
  add.style.marginLeft = 'auto';
  const switcher = mode ? modeSwitch(mode, { say, onSaved: () => reload() }) : null;

  one.body.append(
    card(null, [
      el('div', { class: 'card-head' }, [...filter.parts, switcher ? switcher.node : null, add]),
      rows.length === 0
        ? sayNothing(NOTHING_YET)
        : el('div', { class: 'card-body flush' }, [...items.map((item) => item.node), filter.none]),
      say,
    ]),
    foldout('Settings', [
      await settingsPanel(specs.filter((spec) => spec.key !== MODE_KEY), {
        where: TITLE,
        onSaved: () => reload(),
      }),
    ], { count: specs.length - (mode ? 1 : 0) }),
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
