import { api, listOf, names, notesOf } from './api.js';
import { start } from './app.js';
import {
  badge,
  boldParts,
  card,
  duration,
  el,
  foldout,
  idsIn,
  linkAction,
  nameNode,
  sayNothing,
  section,
  table,
  when,
} from './ui.js';

const COSTS_NOTE = 'Every dollar Black Bloc costs, in one place. The model figures are ' +
  'measured from its own ledger; hosting is what somebody typed in off the invoice; the free ' +
  'things are named at $0 rather than left out.';
const SECRETS_NOTE = 'The keys Black Bloc is configured with, by name. No value is ever read ' +
  'out of the bot, so this says set or unset and nothing else.';
const NO_MODELS = 'No model call has been paid for this month.';
const HOSTING_SETTING = '/settings.html#cost_hosting_usd';
const HOSTING_LINK = 'Fill it in';

const COUNT_LABELS = {
  role_menus_posted: 'Role menus posted',
  temp_channels: 'Temporary voice channels open',
  honeypot_hits_7d: 'Honeypot hits, last 7 days',
  open_events: 'Events open',
  open_modmail: 'Modmail tickets open',
};

function row({ name, badge = null, badgeTone = null, detail = null, note = null, state = null }) {
  const head = el('div', { class: 'row-head' }, [el('span', { class: 'row-name', text: name })]);
  if (badge !== null) head.append(el('span', { class: 'badge', text: String(badge) }));
  return el('li', { class: 'row', 'data-state': state || undefined }, [
    el('span', { class: 'dot' }),
    el('div', { class: 'row-body' }, [
      head,
      detail === null ? null : el('p', { class: 'row-detail', text: detail }),
      note === null ? null : el('p', { class: 'row-note', text: note }),
    ]),
  ]);
}

function rows(items) {
  return el('ul', { class: 'rows' }, items);
}

function health(status) {
  const bot = status.bot;
  const found = [
    row({
      name: 'Gateway',
      badge: bot.ready ? 'connected' : 'not ready',
      state: bot.ready ? 'ok' : 'danger',
      detail: bot.ready
        ? `${bot.latency_ms} ms to Discord · ${bot.guilds} server(s) · up ${duration(bot.uptime_seconds)}`
        : 'Black Bloc is running but has not finished connecting to Discord.',
      note: `Version ${bot.version}${bot.test_mode ? ' · TEST MODE: the bot speaks only in the test channel' : ''}`,
    }),
  ];
  if (status.open) {
    for (const [key, label] of Object.entries(COUNT_LABELS)) {
      if (!(key in status.open)) continue;
      found.push(row({ name: label, badge: String(status.open[key]), state: 'ok' }));
    }
  }
  return rows(found);
}

function loops(status) {
  const found = (status.loops || []).map((loop) => row({
    name: `${loop.cog} · ${loop.name}`,
    badge: loop.running ? 'running' : loop.failed ? 'stopped after an error' : 'stopped',
    state: loop.state,
    detail: loop.last_error
      ? `Last error: ${loop.last_error}`
      : loop.last_ok_at
        ? `Last success ${when(loop.last_ok_at)}`
        : 'This loop does not record its last success yet, so this is liveness, not health.',
    note: loop.next_iteration ? `Next run ${when(loop.next_iteration)}` : null,
  }));
  return found.length ? rows(found) : sayNothing('No loops are loaded.');
}

function tone(kind) {
  if (String(kind).includes('would_')) return 'would';
  if (String(kind).includes('_failed')) return 'failed';
  return null;
}

function actions(items) {
  return table([
    { label: 'When', cell: (item) => when(item.at), className: 'mono' },
    {
      label: 'What',
      cell: (item) => el('span', { class: 'kind', 'data-tone': tone(item.kind) || undefined, text: item.kind }),
    },
    { label: 'Who', cell: (item) => nameNode(item.actor_id, item.actor_name) },
    { label: 'Target', cell: (item) => nameNode(item.target_id, item.target_name) },
    { label: 'Why', cell: (item) => item.reason, className: 'wrap' },
  ], items, { empty: 'Black Bloc has not logged anything yet.' });
}

function dollars(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function thousands(value) {
  return Number(value || 0).toLocaleString();
}

function costRow(item) {
  return row({
    name: item.name,
    badge: item.kind === 'configured' && !item.amount_usd ? 'not filled in' : dollars(item.amount_usd),
    state: item.kind === 'free' ? 'ok' : item.amount_usd ? 'ok' : 'warn',
    detail: item.word,
  });
}

function models(rows) {
  return table([
    { label: 'Model', cell: (item) => `${item.provider_label} · ${item.model}`, className: 'mono' },
    { label: 'Tier', cell: (item) => item.tier },
    { label: 'Answers', cell: (item) => String(item.turns) },
    {
      label: 'Tokens',
      cell: (item) => thousands(Number(item.input_tokens) + Number(item.output_tokens)),
    },
    { label: 'This month', cell: (item) => dollars(item.spent_usd) },
    { label: 'Month before', cell: (item) => dollars(item.prior_usd) },
  ], rows, { empty: NO_MODELS });
}

function secrets(rows) {
  return table([
    { label: 'Name', cell: (item) => item.name, className: 'mono' },
    { label: 'Set', cell: (item) => badge(item.set ? 'set' : 'not set', item.set ? 'ok' : 'warn') },
    { label: 'What it is for', cell: (item) => item.what, className: 'wrap' },
  ], rows, { empty: 'Black Bloc reports no configured keys at all.' });
}

function costs(payload) {
  const total = payload?.total || {};
  const items = payload?.items || [];
  // Counted explicitly: left to itself the shared rail counts TABLE rows, which here would
  // read as eleven costs when it is really two model rows and nine key names.
  const one = section('Costs', COSTS_NOTE, { count: items.length + (payload?.models || []).length });
  one.body.append(card(null, [
    el('div', { class: 'chipbar' }, [
      el('span', { class: 'spend-figure', text: dollars(total.month_usd) }),
      el('span', { class: 'chat-answer-label', text: 'this month, everything in' }),
    ]),
    el('p', { class: 'section-note' }, boldParts(total.word || '')),
    el('p', { class: 'section-note', text: payload?.prior?.word || '' }),
    ...notesOf(payload).map((said) => el('p', { class: 'section-note', text: said })),
    total.hosting_usd
      ? null
      : sayNothing(
        'Hosting is the one figure nobody can read off the bot.',
        linkAction(HOSTING_LINK, HOSTING_SETTING),
      ),
  ]));
  one.body.append(rows(items.map(costRow)));
  one.body.append(el('div', { class: 'chatblock' }, [
    el('h4', { text: 'What the models charged' }),
    models(payload?.models || []),
  ]));
  one.body.append(foldout('Keys, by name', [secrets(payload?.secrets || [])], {
    count: (payload?.secrets || []).length || null,
  }));
  one.body.append(el('p', { class: 'section-note', text: SECRETS_NOTE }));
  return one.node;
}

async function load() {
  const [status, log, money] = await Promise.all([
    api('/api/status'),
    api('/api/actions?limit=50'),
    api('/api/costs'),
  ]);
  const items = listOf(log, 'actions');
  await names(idsIn(items, ['actor_id', 'target_id']));

  const notes = notesOf(status).concat(notesOf(log));
  const one = section('Health');
  one.body.append(health(status));
  const three = section('Loops', null, { count: (status.loops || []).length || null });
  three.body.append(loops(status));
  const four = section('Last 50 actions', null, { count: items.length });
  four.body.append(actions(items));

  document.getElementById('dash').replaceChildren(
    ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
    one.node,
    costs(money),
    three.node,
    four.node,
  );
}

start({
  tab: 'health',
  load,
});
