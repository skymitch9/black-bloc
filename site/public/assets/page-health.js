import { api, listOf, names, notesOf, send } from './api.js';
import { start, tabHref } from './app.js';
import {
  badge,
  bar,
  boldParts,
  button,
  card,
  duration,
  el,
  foldout,
  idsIn,
  linkAction,
  nameNode,
  sayNothing,
  section,
  sentenceFor,
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

const SELFTEST_NOTE = 'Black Bloc exercising itself against this server: every setting’s ' +
  'channel and role, every read these pages make, and every panel posted as a real card in ' +
  'Discord. The cards are deleted again a few minutes later; the lines are kept here under Test.';
const SELFTEST_NEVER = 'It has not run in this server yet. Run it and watch — nothing here is ' +
  'destructive, and the cards it posts are cleaned up on their own.';
const SELFTEST_GOING = 'A run is going right now. This card refreshes itself every 15 seconds ' +
  'until it finishes.';
const SELFTEST_LOGS = 'Every Test line';
const POLL_SECONDS = 15;

function selftestRow(run, purgeMinutes) {
  const done = Boolean(run.finished_at);
  const cleaned = run.purged_at
    ? `Its ${run.posted} card(s) were deleted ${when(run.purged_at)}.`
    : run.posted
      ? `${run.posted} card(s) are still in Discord; they go after ${purgeMinutes} minute(s).`
      : 'It posted nothing into Discord.';
  return row({
    name: `Run #${run.run_id} — ${when(run.started_at)}`,
    badge: done ? `${run.ok} ok · ${run.failed} failed` : 'running',
    state: done ? (run.failed ? 'danger' : 'ok') : 'warn',
    detail: done ? cleaned : SELFTEST_GOING,
    note: `Started from ${run.via}`,
  });
}

function failureRows(checks) {
  const bad = (checks || []).filter((check) => !check.ok);
  if (!bad.length) return sayNothing('Nothing failed.');
  return rows(bad.map((check) => row({
    name: check.name,
    state: 'danger',
    detail: check.detail,
    note: check.feature,
  })));
}

/**
 * Owner ask, 2026-09-05: "test it all". The Health page owns "is the bot well?",
 * so the button that proves it lives here rather than on Settings, which owns values.
 */
function selftest() {
  const one = section('Self-test', SELFTEST_NOTE, { id: 'selftest' });
  const body = el('div', { class: 'logs-results' });
  const said = el('p', { class: 'section-note', hidden: true });
  let timer = null;

  const stopPolling = () => {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  };

  const say = (text, tone = null) => {
    said.textContent = text;
    said.hidden = !text;
    said.setAttribute('data-tone', tone || '');
  };

  const run = button('Run the self-test', async () => {
    say('');
    try {
      await send('/api/selftest', 'POST', {});
    } catch (error) {
      const refusal = sentenceFor(error);
      say(refusal.text, refusal.tone);
      return;
    }
    await load();
  }, { tone: null });

  const load = async () => {
    stopPolling();
    let payload;
    try {
      payload = await api('/api/selftest');
    } catch (error) {
      body.replaceChildren(sayNothing(sentenceFor(error).text));
      return;
    }
    const runs = listOf(payload, 'runs');
    one.count(runs.length || null);
    run.disabled = payload.running !== null && payload.running !== undefined;
    if (!runs.length) {
      body.replaceChildren(sayNothing(SELFTEST_NEVER));
      return;
    }
    const latest = runs[0];
    const detail = await api(`/api/selftest/${latest.run_id}`);
    body.replaceChildren(
      rows([selftestRow(latest, payload.purge_minutes)]),
      failureRows(detail.checks),
      runs.length > 1
        ? foldout('Runs before this one', [rows(
          runs.slice(1).map((each) => selftestRow(each, payload.purge_minutes)),
        )], { count: runs.length - 1 })
        : null,
    );
    if (!latest.finished_at) timer = setTimeout(load, POLL_SECONDS * 1000);
  };

  one.body.append(
    bar([run, linkAction(SELFTEST_LOGS, `${tabHref('audit')}#logs`)]),
    said,
    body,
  );
  return { node: one.node, load };
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
  const proof = selftest();

  document.getElementById('dash').replaceChildren(
    ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
    one.node,
    proof.node,
    costs(money),
    three.node,
    four.node,
  );
  await proof.load();
}

start({
  tab: 'health',
  load,
});
