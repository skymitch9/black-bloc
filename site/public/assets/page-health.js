import { api, listOf, names, notesOf } from './api.js';
import { start } from './app.js';
import { duration, el, idsIn, modeChip, nameNode, sayNothing, section, table, when } from './ui.js';

const COUNT_LABELS = {
  role_menus_posted: 'Role menus posted',
  temp_channels: 'Temporary voice channels open',
  honeypot_hits_7d: 'Honeypot hits, last 7 days',
  open_events: 'Events open',
  open_modmail: 'Modmail tickets open',
};

function row({ name, badge = null, badgeTone = null, detail = null, note = null, state = null }) {
  const head = el('div', { class: 'row-head' }, [el('span', { class: 'row-name', text: name })]);
  if (badge !== null) {
    head.append(badgeTone === 'mode' ? modeChip(badge) : el('span', { class: 'badge', text: String(badge) }));
  }
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

function features(status) {
  const found = (status.features || []).map((feature) => row({
    name: feature.feature.replace(/^./, (c) => c.toUpperCase()),
    badge: feature.mode === null || feature.mode === undefined ? 'not set' : String(feature.mode),
    badgeTone: 'mode',
    state: feature.mode === 'on' ? 'ok' : feature.mode === 'shadow' ? 'warn' : null,
    detail: feature.mode === 'shadow' ? 'Logging what it would do, doing nothing.' : null,
  }));
  return found.length ? rows(found) : sayNothing('No features report a mode yet.');
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

async function load() {
  const [status, log] = await Promise.all([
    api('/api/status'),
    api('/api/actions?limit=50'),
  ]);
  const items = listOf(log, 'actions');
  await names(idsIn(items, ['actor_id', 'target_id']));

  const notes = notesOf(status).concat(notesOf(log));
  const one = section('Health');
  one.body.append(health(status));
  const two = section('Features', 'Every feature’s mode, read from the settings the slash commands write.', {
    count: (status.features || []).length || null,
  });
  two.body.append(features(status));
  const three = section('Loops', null, { count: (status.loops || []).length || null });
  three.body.append(loops(status));
  const four = section('Last 50 actions', null, { count: items.length });
  four.body.append(actions(items));

  document.getElementById('dash').replaceChildren(
    ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
    one.node,
    two.node,
    three.node,
    four.node,
  );
}

start({
  tab: 'health',
  load,
});
