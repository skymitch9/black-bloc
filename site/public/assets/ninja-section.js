import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { logsTable } from './logs.js';
import {
  ask,
  bar,
  button,
  card,
  channelSelect,
  el,
  field,
  foldout,
  idsIn,
  keepSaying,
  memberPicker,
  modeSwitch,
  notice,
  run,
  sayAgain,
  sayNothing,
  scrollerOf,
  section,
  settingsPanel,
  table,
  when,
} from './ui.js';

const TITLE = 'Ninja marks';
const SLUG = 'ninja';
const KEY_PREFIX = 'ninja_';
const MODE_KEY = 'ninja_mode';
const OPERATIONAL_KEYS = ['ninja_emoji', 'ninja_default_posts', 'ninja_default_minutes'];
const LOG_ROWS = 50;
const NO_LOGS = 'Nobody has been marked yet.';
const BECAUSE_WORDS = { posts: 'posts used up', time: 'time ran out', staff: 'ended by staff' };
const MOST = { posts: 1000, minutes: 43200 };

let reloadPage = async () => {};
let jumped = false;
const opened = new Set();

async function refresh() {
  const scroller = scrollerOf(document.getElementById('dash'));
  const at = scroller.scrollTop;
  await reloadPage();
  scroller.scrollTo({ top: at, behavior: 'instant' });
}

function kept(title, children, count) {
  const fold = foldout(title, children, { count, open: opened.has(title) });
  fold.addEventListener('toggle', () => (fold.open ? opened.add(title) : opened.delete(title)));
  return fold;
}

async function act(say, where, work, okText) {
  const done = await run(say, work, okText);
  if (done.ok) {
    keepSaying(where, say);
    refresh();
  }
  return done;
}

/** What is left of a mark, in the bot's own `ninja_left_*` shape. */
export function leftWords(row) {
  const posts = row.posts_left === null || row.posts_left === undefined ? null : Number(row.posts_left);
  const until = row.until ? `until ${when(row.until)}` : null;
  if (posts !== null && until) return `${posts} post(s) or ${until}`;
  return until || `${posts} post(s)`;
}

function marksCard(payload, specs) {
  const say = notice();
  const rows = listOf(payload, 'active');
  const modeSpec = specs.find((spec) => spec.key === MODE_KEY);
  const head = [el('span', { class: 'row-detail', text: payload.emoji || '—' })];
  if (modeSpec) head.push(modeSwitch(modeSpec, { say, onSaved: () => refresh() }).node);
  const list = table([
    { label: 'Member', cell: (row) => row.user_name || row.user_id },
    { label: 'Channel', cell: (row) => row.channel_name || row.channel_id },
    { label: 'Left', cell: (row) => leftWords(row) },
    { label: 'By', cell: (row) => row.made_by_name || row.made_by || '—' },
    { label: 'Made', cell: (row) => when(row.made_at) },
    {
      label: '',
      cell: (row) => bar([
        button('End', async () => {
          const sure = await ask({
            title: 'End this mark?',
            body: [`${row.user_name || row.user_id} · ${row.channel_name || row.channel_id}`],
            confirmLabel: 'End',
          });
          if (sure) await act(say, 'ninja.marks', () => api(`/api/ninja/${encodeURIComponent(row.id)}`, { method: 'DELETE' }), (found) => found?.message || 'Ended.');
        }, { tone: 'danger' }),
      ]),
    },
  ], rows, { empty: 'Nobody is marked.' });
  return card('Marked', [bar(head), list, say, sayAgain('ninja.marks', say)], { count: rows.length });
}

function numberBox(value, most) {
  const box = el('input', { class: 'input', type: 'number', min: '0', max: String(most), step: '1', inputmode: 'numeric', placeholder: 'No limit' });
  box.value = value || '';
  return box;
}

async function markCard(payload) {
  const say = notice();
  const chosen = new Map();
  const chips = el('div', { class: 'pickchips-list' });
  const drawChips = () => chips.replaceChildren(...[...chosen].map(([id, name]) => el('span', { class: 'pickchip' }, [
    el('span', { text: name }),
    el('button', {
      type: 'button',
      class: 'pickchip-x',
      'aria-label': `Remove ${name}`,
      text: '×',
      on: { click: () => { chosen.delete(id); drawChips(); } },
    }),
  ])));
  const picker = memberPicker({
    label: 'Who',
    onPick: (member) => {
      if (!member) return;
      chosen.set(String(member.id), member.name);
      drawChips();
      picker.clear();
    },
  });
  const where = await channelSelect(payload.default_channel_id, { id: 'ninja-where' });
  const posts = numberBox(payload.default_posts, MOST.posts);
  const minutes = numberBox(payload.default_minutes, MOST.minutes);
  const mark = button('Mark', async () => {
    const done = await act(say, 'ninja.mark', () => send('/api/ninja', 'POST', {
      user_ids: [...chosen.keys()],
      channel_id: where.value || null,
      posts: posts.value.trim(),
      minutes: minutes.value.trim(),
    }), (found) => found?.message || 'Marked.');
    if (done.ok) {
      chosen.clear();
      drawChips();
    }
  }, { small: false });
  return card('Mark someone', [
    picker.node,
    el('div', { class: 'pickchips' }, [chips]),
    field('Where', where),
    field('Posts', posts),
    field('Minutes', minutes),
    bar([mark]),
    say,
    sayAgain('ninja.mark', say),
  ]);
}

function endedFold(rows) {
  const list = table([
    { label: 'Member', cell: (row) => row.user_name || row.user_id },
    { label: 'Channel', cell: (row) => row.channel_name || row.channel_id },
    { label: 'Ended', cell: (row) => when(row.ended_at) },
    { label: 'Why', cell: (row) => BECAUSE_WORDS[row.ended_because] || row.ended_because || '—' },
  ], rows, { empty: 'No mark has ended yet.' });
  return kept('Ended', [list], rows.length);
}

async function emotesCard() {
  let rows = [];
  try {
    rows = await api('/api/ref/emojis');
  } catch (error) {
    return sayNothing(error.message);
  }
  const list = table([
    { label: 'Emote', cell: (row) => `:${row.name}:` },
    { label: 'ninja_emoji', cell: (row) => el('code', { text: row.string }) },
  ], Array.isArray(rows) ? rows : [], { empty: 'The server has no emotes of its own.', search: true });
  return card('Server emotes', [list], { count: Array.isArray(rows) ? rows.length : 0 });
}

async function settingsFold(specs) {
  if (!specs.length) return kept('Settings', [sayNothing('The bot reported no ninja_ settings.')], 0);
  const operational = specs.filter((spec) => OPERATIONAL_KEYS.includes(spec.key));
  const wording = specs.filter((spec) => spec.key !== MODE_KEY && !OPERATIONAL_KEYS.includes(spec.key));
  return kept('Settings', [
    await settingsPanel(operational, { where: TITLE, onSaved: () => refresh() }),
    await emotesCard(),
    await settingsPanel(wording, { where: 'Wording' }),
  ], specs.length);
}

async function logsFold() {
  const payload = await api(`/api/actions?feature=core&q=ninja&per_page=${LOG_ROWS}`);
  const rows = listOf(payload, 'actions').filter((row) => /^(web\.)?ninja\./.test(String(row.kind)));
  await names(idsIn(rows, ['actor_id', 'target_id']));
  return kept('Logs', [logsTable(rows, NO_LOGS)], rows.length);
}

/** The Ninja marks section of the Posts page; `reload` redraws the page after a write. */
export async function ninjaSection(reload) {
  reloadPage = reload;
  const [payload, all] = await Promise.all([api('/api/ninja'), settings()]);
  const specs = settingsNamespace(all, 'core').filter((spec) => spec.key.startsWith(KEY_PREFIX));
  const active = listOf(payload, 'active');
  const asked = location.hash === `#sect-${SLUG}`;
  const one = section(TITLE, null, { count: active.length, id: SLUG, open: asked });
  one.body.append(
    marksCard(payload, specs),
    await markCard(payload),
    endedFold(listOf(payload, 'ended')),
    await settingsFold(specs),
    await logsFold(),
  );
  one.node.setAttribute('data-span', 'full');
  if (asked && !jumped) {
    jumped = true;
    requestAnimationFrame(() => {
      one.details.open = true;
      one.node.scrollIntoView({ block: 'start' });
    });
  }
  return one.node;
}
