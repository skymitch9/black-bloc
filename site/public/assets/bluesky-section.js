import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { logsTable } from './logs.js';
import {
  ago,
  askForm,
  bar,
  button,
  card,
  el,
  field,
  foldout,
  idsIn,
  keepSaying,
  modeChip,
  notice,
  run,
  sayAgain,
  sayNothing,
  scrollerOf,
  section,
  segment,
  settingsPanel,
  table,
  when,
} from './ui.js';

const TITLE = 'Bluesky';
const SLUG = 'bluesky';
const KEY_PREFIX = 'bluesky_';
const LOG_ROWS = 50;
const NO_LOGS = 'Nothing has happened to the Bluesky mirror yet.';
const WORDING_KEYS = [
  'bluesky_template',
  'bluesky_repost_line',
  'bluesky_rehearsal_line',
  'bluesky_footer',
  'bluesky_open_label',
  'bluesky_profile_label',
];
const READ_NOW = 'Read now';
const POST_TO_TEST = 'Post to test';
const POST_LATEST = 'Post the latest…';
const COUNT_MOST = 10;
const KIND_WORDS = { own: 'post', repost: 'repost', reply: 'reply' };
const STATUS_WORDS = {
  posted: 'posted',
  would_post: 'test copy',
  skipped_old: 'too old',
  skipped_kind: 'not mirrored',
  claimed: 'sending',
  retry: 'will retry',
  failed: 'failed',
};
const WHERE_CHOICES = [
  { value: 'channel', label: 'The channel' },
  { value: 'test', label: 'The test channel' },
];

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

async function act(say, work, where = 'bluesky.status') {
  const done = await run(say, work, (found) => found?.message || 'Done.');
  if (done.ok) {
    keepSaying(where, say);
    refresh();
  }
  return done;
}

function readWords(payload) {
  if (payload.mode === 'off') return 'not read';
  if (!payload.last_read_at) return 'not read yet';
  return `read ${ago(payload.last_read_at).text}`;
}

async function postLatest(payload, say) {
  const count = el('input', {
    class: 'input', type: 'number', min: '1', max: String(COUNT_MOST), id: 'bluesky-count',
  });
  count.value = String(payload.seed_count || 2);
  const where = segment(WHERE_CHOICES, payload.channel_id ? 'channel' : 'test');
  let said = null;
  const done = await askForm({
    title: POST_LATEST,
    confirmLabel: 'Post',
    tone: 'warn',
    body: [field('How many', count), field('Where', where)],
    onConfirm: async () => {
      const found = await send('/api/bluesky/post-latest', 'POST', {
        count: Number(count.value),
        where: where.readValue(),
      });
      said = found?.message || 'Posted.';
      return null;
    },
  });
  if (done) {
    say.say(said, 'ok');
    keepSaying('bluesky.status', say);
    refresh();
  }
}

function statusCard(payload) {
  const say = notice();
  const pills = [
    modeChip(payload.mode, 'bluesky_mode'),
    el('span', { class: 'row-detail', text: `@${payload.handle}` }),
    el('span', { class: 'row-detail', text: readWords(payload), title: ago(payload.last_read_at).title }),
  ];
  const lines = [el('div', { class: 'bar' }, pills)];
  if (payload.last_error) lines.push(el('p', { class: 'row-note', 'data-tone': 'danger', text: payload.last_error }));
  const moves = [];
  if (payload.mode !== 'off') {
    moves.push(button(READ_NOW, () => act(say, () => send('/api/bluesky/read', 'POST', {})), { small: false }));
  }
  if (payload.test_home) {
    moves.push(button(POST_TO_TEST, () => act(say, () => send('/api/bluesky/rehearse', 'POST', {})), { tone: 'quiet' }));
  }
  moves.push(button(POST_LATEST, () => postLatest(payload, say), { tone: 'quiet' }));
  return card('Status', [...lines, bar(moves), say, sayAgain('bluesky.status', say)]);
}

function recentFold(rows, payload) {
  const say = notice();
  const list = table([
    { label: 'When', cell: (row) => when(row.posted_at || row.seen_at) },
    { label: 'Kind', cell: (row) => KIND_WORDS[row.kind] || row.kind },
    { label: 'Post', cell: (row) => row.text },
    { label: 'Where', cell: (row) => STATUS_WORDS[row.status] || row.status },
    {
      label: '',
      cell: (row) => bar([
        el('a', { class: 'btn quiet small', href: row.url, target: '_blank', rel: 'noopener', text: 'Bluesky' }),
        row.message_url
          ? el('a', { class: 'btn quiet small', href: row.message_url, target: '_blank', rel: 'noopener', text: 'Discord' })
          : null,
        payload.test_home
          ? button(POST_TO_TEST, () => act(say, () => send('/api/bluesky/rehearse', 'POST', { uri: row.uri }), 'bluesky.recent'), { tone: 'quiet' })
          : null,
      ].filter(Boolean)),
    },
  ], rows, { empty: 'Nothing has been read yet.' });
  return kept('Recent', [list, say, sayAgain('bluesky.recent', say)], rows.length);
}

async function settingsFold(specs) {
  if (!specs.length) return kept('Settings', [sayNothing('The bot reported no bluesky_ settings.')], 0);
  const wording = specs.filter((spec) => WORDING_KEYS.includes(spec.key));
  const operational = specs.filter((spec) => !WORDING_KEYS.includes(spec.key));
  return kept('Settings', [
    await settingsPanel(operational, { where: TITLE, onSaved: () => refresh() }),
    await settingsPanel(wording, { where: 'Wording' }),
  ], specs.length);
}

async function logsFold() {
  const payload = await api(`/api/actions?feature=posts&q=bluesky&per_page=${LOG_ROWS}`);
  const rows = listOf(payload, 'actions').filter((row) => /^(web\.)?bluesky\./.test(String(row.kind)));
  await names(idsIn(rows, ['actor_id', 'target_id']));
  return kept('Logs', [logsTable(rows, NO_LOGS)], rows.length);
}

/** The Bluesky section of the Posts page; `reload` redraws the page after a write. */
export async function blueskySection(reload) {
  reloadPage = reload;
  const [payload, all] = await Promise.all([api('/api/bluesky'), settings()]);
  const specs = settingsNamespace(all, 'posts').filter((spec) => spec.key.startsWith(KEY_PREFIX));
  const recent = listOf(payload, 'recent');
  const asked = location.hash === `#sect-${SLUG}`;
  const one = section(TITLE, null, { id: SLUG, open: asked });
  one.body.append(
    statusCard(payload),
    recentFold(recent, payload),
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
