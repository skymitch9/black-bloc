import { api, listOf, names, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  askForm,
  badge,
  bar,
  button,
  el,
  field,
  foldout,
  idsIn,
  keepSaying,
  listFilter,
  memberPicker,
  modeSwitch,
  nameNode,
  notice,
  run,
  sayAgain,
  sayNothing,
  section,
  settingsPanel,
  table,
  when,
} from './ui.js';

const KEY_PREFIX = 'pb_feed_';
const MODE_KEY = 'pb_feed_mode';
const AGAIN_KEY = 'pb_feed_post_again_label';
const AGAIN_SAID = 'pbs.again';
const OPERATIONAL = [
  'pb_feed_channel_id',
  'pb_feed_shadow_channel_id',
  'pb_feed_ping_role_id',
  'pb_feed_auto_match',
  'pb_feed_interval_minutes',
  'pb_feed_cycle_requests',
  'pb_feed_rematch_days',
  'pb_feed_max_age_days',
  'pb_feed_max_posts',
  'pb_feed_panel_minutes',
];
const STATE_WORDS = {
  matched: 'matched',
  none: 'no match',
  opted_out: 'opted out',
  blocked: 'blocked',
};
const WAITING = 'not looked up yet';
const STATE_TONES = { matched: 'ok', opted_out: 'warn', blocked: 'danger' };
const SOURCE_WORDS = { auto: 'from Twitch', staff: 'set by staff' };
const REASON_WORDS = {
  nobody: 'no account lists this Twitch channel',
  ambiguous: 'more than one account lists this Twitch channel',
  taken: 'that account is another member’s',
  runner_gone: 'the account is gone from speedrun.com',
  link_moved: 'their Twitch link changed',
  trouble: 'could not be looked up',
};
const NOT_NEWS_WORDS = {
  too_old: 'verified too long ago',
  before_baseline: 'verified before the first look',
  undated: 'with no verify date',
};
const OUTCOME_WORDS = {
  posted: 'posted',
  rehearsed: 'rehearsed',
  dry: 'not sent',
  held: 'held back',
  failed: 'failed',
  unconfirmed: 'not confirmed',
};
const OUTCOME_TONES = { posted: 'ok', rehearsed: 'warn', failed: 'danger', unconfirmed: 'danger' };
const FILTERS = [
  ['all', 'All', null],
  ['matched', 'Matched', (row) => row.state === 'matched'],
  ['none', 'No match', (row) => !row.state || row.state === 'none'],
  ['opted_out', 'Opted out', (row) => row.state === 'opted_out'],
  ['blocked', 'Blocked', (row) => row.state === 'blocked'],
];
const NOBODY_YET = 'Nobody has linked a Twitch channel or been matched yet.';
const NOBODY_MATCHES = 'Nobody matches this.';
const NO_POSTS = 'No personal best has been posted or rehearsed yet.';
const NO_LOGS = 'The personal best feed has logged nothing yet.';
const NEED_A_MEMBER = 'Pick the member first.';
const NEED_A_NAME = 'Type their speedrun.com name, then save again.';
const REASON_LABEL = 'Reason (the member is told)';
const LOG_ROWS = 20;
const AGAIN_NOTE = 'again';

const kept = { query: '', filter: 'all', mode: 'shadow' };
let refresh = () => {};

function where(userId, tail = '') {
  return `/api/pbs/${encodeURIComponent(userId)}${tail}`;
}

/** 1:02:03, 2:03 or 0:59, with thousandths only when the run has them. */
function timeWords(seconds) {
  const millis = Math.round(Math.max(0, Number(seconds) || 0) * 1000);
  const whole = Math.floor(millis / 1000);
  const part = millis % 1000;
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const secs = String(whole % 60).padStart(2, '0');
  const words = hours ? `${hours}:${String(minutes).padStart(2, '0')}:${secs}` : `${minutes}:${secs}`;
  return part ? `${words}.${String(part).padStart(3, '0')}` : words;
}

function outLink(text, href) {
  if (!href || !String(href).startsWith('https://')) return el('span', { text });
  return el('a', { href, target: '_blank', rel: 'noopener noreferrer', text });
}

function personText(row) {
  return [
    row.name,
    row.twitch_login || '',
    row.runner || '',
    STATE_WORDS[row.state] || WAITING,
    SOURCE_WORDS[row.source] || '',
  ].join(' ');
}

function nameBox() {
  return el('input', {
    class: 'input',
    type: 'text',
    id: 'pb-runner',
    maxlength: '64',
    autocomplete: 'off',
    spellcheck: 'false',
  });
}

function reasonBox() {
  return el('input', {
    class: 'input',
    type: 'text',
    id: 'pb-reason',
    maxlength: '300',
    autocomplete: 'off',
  });
}

async function setByHand(userId, title, say, picker = null) {
  const box = nameBox();
  const reason = reasonBox();
  await askForm({
    title,
    body: [
      picker ? picker.node : null,
      field('Their speedrun.com name', box),
      field(REASON_LABEL, reason),
    ],
    confirmLabel: 'Save it',
    tone: 'warn',
    onConfirm: async () => {
      const wanted = picker ? picker.id : userId;
      if (!wanted) return NEED_A_MEMBER;
      if (!box.value.trim()) return NEED_A_NAME;
      const found = await send(where(wanted), 'PUT', {
        runner: box.value.trim(),
        reason: reason.value.trim(),
      });
      say.say(found.message, 'ok');
      refresh();
      return null;
    },
  });
}

async function withReason(row, say, { title, confirmLabel, tone, method, tail }) {
  const reason = reasonBox();
  await askForm({
    title,
    body: [field(REASON_LABEL, reason)],
    confirmLabel,
    tone,
    onConfirm: async () => {
      const found = await send(where(row.user_id, tail), method, { reason: reason.value.trim() });
      say.say(found.message, 'ok');
      refresh();
      return null;
    },
  });
}

function actions(row, say) {
  const act = async (method, tail) => {
    const done = await run(say, () => send(where(row.user_id, tail), method, {}), (found) => found.message);
    if (done.ok) refresh();
  };
  const moves = [];
  if (row.state !== 'opted_out' && !row.opted_out_at && kept.mode !== 'off') {
    moves.push(button('Set by hand…', () => setByHand(row.user_id, row.name, say)));
  }
  if (row.state === 'matched') {
    if (kept.mode !== 'off') moves.push(button('Look now', () => act('POST', '/look')));
    moves.push(button('Unmatch', () => withReason(row, say, {
      title: `Unmatch ${row.name} from ${row.runner}?`,
      confirmLabel: 'Unmatch',
      tone: 'warn',
      method: 'DELETE',
      tail: '',
    })));
  }
  if (row.state === 'opted_out') {
    moves.push(button('Clear the opt-out', () => withReason(row, say, {
      title: `Clear ${row.name}’s opt-out?`,
      confirmLabel: 'Clear the opt-out',
      tone: 'warn',
      method: 'POST',
      tail: '/optin',
    }), { tone: 'warn' }));
  }
  if (row.state === 'blocked') {
    moves.push(button('Unblock', () => act('POST', '/unblock'), { tone: 'warn' }));
  } else {
    moves.push(button('Block', () => withReason(row, say, {
      title: `Block ${row.name}?`,
      confirmLabel: 'Block',
      tone: 'danger',
      method: 'POST',
      tail: '/block',
    }), { tone: 'danger' }));
  }
  return bar(moves);
}

function stateLine(row) {
  const parts = [badge(STATE_WORDS[row.state] || WAITING, STATE_TONES[row.state] || null)];
  if (row.state === 'matched') {
    parts.push(outLink(row.runner, row.runner_link));
    parts.push(el('span', { class: 'rowlist-note', text: SOURCE_WORDS[row.source] || '' }));
  } else if (row.reason && REASON_WORDS[row.reason]) {
    parts.push(el('span', { class: 'rowlist-note', text: REASON_WORDS[row.reason] }));
  }
  if (!row.here) parts.push(badge('left the server'));
  return el('span', { class: 'bar' }, parts);
}

function seenLine(row) {
  const parts = [];
  if (row.looked_at) parts.push(`looked ${when(row.looked_at)}`);
  if (row.last_pb_at) parts.push(`last new personal best ${when(row.last_pb_at)}`);
  if (parts.length === 0) return null;
  return el('span', { class: 'rowlist-note', text: parts.join(' · ') });
}

function notNewsLine(row) {
  const found = row.not_news;
  if (!found) return null;
  const parts = Object.entries(NOT_NEWS_WORDS)
    .filter(([key]) => Number(found[key]) > 0)
    .map(([key, words]) => `${found[key]} ${words}`);
  if (parts.length === 0) return null;
  return el('span', {
    class: 'rowlist-note',
    text: `recorded, not posted ${when(found.at)}: ${parts.join(' · ')}`,
  });
}

function personRow(row, say) {
  return el('div', { class: 'rowlist-row', 'data-member': String(row.user_id) }, [
    el('div', { class: 'rowlist-main' }, [
      el('span', { class: 'rowlist-name' }, [nameNode(row.user_id, row.name)]),
      row.twitch_login
        ? el('span', { class: 'rowlist-line mono', text: `twitch.tv/${row.twitch_login}` })
        : null,
      stateLine(row),
      seenLine(row),
      notNewsLine(row),
      row.look_error ? notice(row.look_error, 'danger') : null,
    ]),
    actions(row, say),
  ]);
}

function lookBadge(look) {
  if (!look || !look.at) return null;
  if (look.outcome === 'failed') return badge(`could not look ${when(look.at)}`, 'danger');
  return badge(`last look ${when(look.ok_at || look.at)}`, 'ok');
}

function peopleSection(payload, modeSpec) {
  const rows = listOf(payload, 'people');
  const say = notice();
  const look = payload.last_look;
  const items = rows.map((row) => ({ row, node: personRow(row, say) }));
  const filter = listFilter({
    items,
    value: (item) => item.row,
    text: personText,
    filters: FILTERS,
    filter: kept.filter,
    query: kept.query,
    label: 'Search the members',
    placeholder: 'Search the members…',
    empty: NOBODY_MATCHES,
    onChange: ({ query, filter: key }) => {
      kept.query = query;
      kept.filter = key;
    },
  });
  filter.apply();

  const add = kept.mode === 'off'
    ? null
    : button('Match a member…', () => setByHand(null, 'Match a member', say, memberPicker({ label: 'Member' })), { tone: 'warn' });
  if (add) add.style.marginLeft = 'auto';
  const one = section('Members', null, { count: rows.length, open: true });
  const why = look && look.outcome === 'failed' && look.reason ? notice(look.reason, 'danger') : null;
  one.body.append(...[
    el('div', { class: 'bar' }, [
      modeSpec ? modeSwitch(modeSpec, { say, label: 'Personal best feed', onSaved: () => refresh() }).node : null,
      lookBadge(look),
      add,
    ]),
    say,
    why,
    el('div', { class: 'table-tools' }, filter.parts),
    rows.length === 0
      ? sayNothing(NOBODY_YET)
      : el('div', { class: 'rowlist' }, [...items.map((item) => item.node), filter.none]),
  ].filter(Boolean));
  return one.node;
}

function postAgain(row, label, say) {
  return askForm({
    title: `${label}: ${row.name} · ${row.game || ''} · ${timeWords(row.seconds)}?`,
    body: [],
    confirmLabel: label,
    tone: 'warn',
    onConfirm: async () => {
      const found = await send(`/api/pbs/posts/${encodeURIComponent(row.id)}/again`, 'POST', {});
      say.say(found.message, 'ok');
      keepSaying(AGAIN_SAID, say);
      refresh();
      return null;
    },
  });
}

function postsSection(payload, specs) {
  const rows = listOf(payload, 'posts');
  const spec = specs.find((found) => found.key === AGAIN_KEY);
  const label = String((spec && (spec.value ?? spec.default)) || 'Post again');
  const say = sayAgain(AGAIN_SAID, notice());
  const one = section('Recent posts', null, { count: rows.length, open: rows.length > 0 });
  one.body.append(say, table([
    { label: 'When', cell: (row) => when(row.at), className: 'mono' },
    { label: 'Member', cell: (row) => nameNode(row.user_id, row.name) },
    { label: 'Game', key: 'game' },
    { label: 'Category', key: 'category' },
    { label: 'Time', cell: (row) => timeWords(row.seconds), className: 'mono' },
    { label: 'Place', cell: (row) => (row.place ? `#${row.place}` : null), className: 'mono' },
    {
      label: '',
      cell: (row) => el('span', { class: 'bar' }, [
        badge(OUTCOME_WORDS[row.outcome] || row.outcome, OUTCOME_TONES[row.outcome] || null),
        row.again_of ? el('span', { class: 'rowlist-note', text: AGAIN_NOTE }) : null,
        row.reason && row.outcome !== 'rehearsed' && row.outcome !== 'posted'
          ? el('span', { class: 'rowlist-note', text: row.reason })
          : null,
      ]),
    },
    { label: '', cell: (row) => outLink('Run', row.link) },
    {
      label: '',
      cell: (row) => (kept.mode === 'off'
        ? null
        : button(label, () => postAgain(row, label, say), { tone: 'warn' })),
    },
  ], rows, { empty: NO_POSTS }));
  return one.node;
}

async function settingsSection(specs) {
  const operational = OPERATIONAL
    .map((key) => specs.find((spec) => spec.key === key))
    .filter(Boolean);
  const wording = specs.filter((spec) => spec.key !== MODE_KEY && !OPERATIONAL.includes(spec.key));
  const one = section('Settings', null, { count: operational.length + wording.length });
  one.body.append(
    await settingsPanel(operational, { where: 'Settings', onSaved: () => refresh() }),
    foldout('Wording', [await settingsPanel(wording, { where: 'Wording' })], { count: wording.length }),
  );
  return one.node;
}

async function logsSectionNode() {
  const payload = await api(`/api/actions?feature=core&q=pbfeed&per_page=${LOG_ROWS}`);
  const rows = listOf(payload, 'actions').filter((row) => /^(web\.)?pbfeed\./.test(String(row.kind)));
  await names(idsIn(rows, ['actor_id', 'target_id']));
  const one = section('Logs', null, { count: rows.length });
  one.body.append(logsTable(rows, NO_LOGS));
  return one.node;
}

async function load() {
  const [payload, all] = await Promise.all([api('/api/pbs'), settings()]);
  kept.mode = payload.mode || 'off';
  await names(idsIn(listOf(payload, 'people'), ['user_id']).concat(idsIn(listOf(payload, 'posts'), ['user_id'])));
  const specs = settingsNamespace(all, 'core').filter((spec) => spec.key.startsWith(KEY_PREFIX));
  const modeSpec = specs.find((spec) => spec.key === MODE_KEY);

  document.getElementById('dash').replaceChildren(
    peopleSection(payload, modeSpec),
    postsSection(payload, specs),
    await settingsSection(specs),
    await logsSectionNode(),
  );
}

refresh = start({
  tab: 'pbs',
  load,
});
