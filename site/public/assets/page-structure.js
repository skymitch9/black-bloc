import { api, listOf, names, refChannels, send, settings, settingsNamespace } from './api.js';
import { start } from './app.js';
import { logsTable } from './logs.js';
import {
  badge,
  bar,
  boldParts,
  button,
  channelLabel,
  el,
  field,
  foldout,
  idsIn,
  listFilter,
  modeSwitch,
  nameNode,
  notice,
  run,
  sayNothing,
  section,
  settingsPanel,
  table,
  when,
} from './ui.js';

const KEY_PREFIX = 'structure_backup_';
const MODE_KEY = 'structure_backup_mode';
const OPERATIONAL = [
  'structure_backup_hour',
  'structure_backup_keep',
  'structure_backup_notify',
  'structure_backup_channel_id',
  'structure_backup_shadow_channel_id',
  'structure_backup_notice_lines',
  'structure_backup_panel_minutes',
];
const NOTIFY_KEY = 'structure_backup_notify';
const NOTICE_KEYS = { on: 'structure_backup_channel_id', shadow: 'structure_backup_shadow_channel_id' };
const NOW = 'now';
const NOW_LABEL = 'The server now';
const AREAS = [
  ['all', 'All'],
  ['server', 'Server'],
  ['roles', 'Roles'],
  ['channels', 'Channels'],
  ['permissions', 'Permissions'],
];
const KIND_TONES = { added: 'ok', removed: 'danger', changed: 'warn', moved: null };
const OUTCOME_TONES = { saved: 'ok', unchanged: null, failed: 'danger' };
const LOG_ROWS = 20;
const LOG_KINDS = ['structure', 'web.structure'];

let refresh = () => {};

function snapshotLabel(row) {
  return `#${row.id} · ${when(row.taken_at)}`;
}

function takenBy(row) {
  if (row.source === 'daily') return badge('daily');
  return row.taken_by_id ? nameNode(row.taken_by_id, row.taken_by_name) : badge('by hand');
}

function lastSeen(row) {
  if (!row.checks) return null;
  return `${when(row.checked_at)} · ${row.checks} look(s)`;
}

function saveFile(name, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const href = URL.createObjectURL(blob);
  const link = el('a', { href, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

async function download(row, say) {
  await run(say, async () => {
    const found = await send(`/api/structure/snapshots/${encodeURIComponent(row.id)}/download`, 'POST', {});
    saveFile(found.snapshot.filename, found);
    return found;
  }, (found) => `Snapshot #${found.snapshot.id} downloaded.`);
}

function changeList(found) {
  const rows = listOf(found, 'changes');
  if (rows.length === 0) return sayNothing('Nothing differs between these two.');
  const items = rows.map((row) => ({
    row,
    node: el('div', { class: 'rowlist-row' }, [
      badge(row.kind, KIND_TONES[row.kind] || null),
      el('span', { class: 'rowlist-line' }, boldParts(row.text)),
    ]),
  }));
  const counts = new Map();
  for (const row of rows) counts.set(row.area, (counts.get(row.area) || 0) + 1);
  const filters = AREAS
    .filter(([key]) => key === 'all' || counts.has(key))
    .map(([key, label]) => (key === 'all'
      ? [key, `${label} ${rows.length}`, null]
      : [key, `${label} ${counts.get(key)}`, (row) => row.area === key]));
  const filter = listFilter({
    items,
    node: (item) => item.node,
    value: (item) => item.row,
    text: (row) => `${row.text} ${row.area} ${row.kind}`,
    filters,
    label: 'Search the changes',
    placeholder: 'role, channel or permission',
    empty: 'No change matches that.',
  });
  filter.apply();
  return el('div', {}, [
    el('div', { class: 'table-tools' }, filter.parts),
    el('div', { class: 'rowlist' }, items.map((item) => item.node)),
    filter.none,
  ]);
}

function compareCard(rows, results, say) {
  const older = el('select', {}, rows.map((row) => el('option', { value: String(row.id), text: snapshotLabel(row) })));
  const newer = el('select', {}, [
    el('option', { value: NOW, text: NOW_LABEL }),
    ...rows.map((row) => el('option', { value: String(row.id), text: snapshotLabel(row) })),
  ]);
  if (rows.length > 1) {
    older.value = String(rows[1].id);
    newer.value = String(rows[0].id);
  }
  const compare = async (old, wanted) => {
    older.value = String(old);
    newer.value = String(wanted);
    const done = await run(
      say,
      () => api(`/api/structure/compare?old=${encodeURIComponent(old)}&new=${encodeURIComponent(wanted)}`),
      (found) => `${found.count} change(s) between #${found.old.id} and ${found.new ? `#${found.new.id}` : NOW_LABEL.toLowerCase()}.`,
    );
    results.replaceChildren(done.ok ? changeList(done.found) : '');
  };
  const node = el('div', {}, [
    el('div', { class: 'settings-grid' }, [
      field('Older', older),
      field('Newer', newer),
    ]),
    bar([button('Compare', () => compare(older.value, newer.value), { small: false })]),
  ]);
  return { node, compare };
}

async function noticeBadge(mode, specs) {
  const key = NOTICE_KEYS[mode];
  if (!key) return null;
  const value = (wanted) => (specs.find((spec) => spec.key === wanted) || {}).value;
  if (value(NOTIFY_KEY) === false) return badge('notice off');
  const id = value(key);
  if (!id) return badge('notice goes nowhere', 'warn');
  const channels = await refChannels();
  const channel = channels.find((one) => String(one.id) === String(id));
  return badge(`notice → ${channel ? channelLabel(channel, channels) : id}`);
}

async function logRows() {
  const pages = await Promise.all(LOG_KINDS.map((kind) => api(`/api/actions?kind=${kind}&per_page=${LOG_ROWS}`)));
  const rows = pages
    .flatMap((payload) => listOf(payload, 'actions'))
    .sort((a, b) => Number(b.id) - Number(a.id))
    .slice(0, LOG_ROWS);
  await names(idsIn(rows, ['actor_id', 'target_id']));
  return rows;
}

async function load() {
  const [payload, all] = await Promise.all([api('/api/structure'), settings()]);
  const rows = listOf(payload, 'snapshots');
  await names(idsIn(rows, ['taken_by_id']));
  const specs = settingsNamespace(all, 'core').filter((spec) => spec.key.startsWith(KEY_PREFIX));
  const modeSpec = specs.find((spec) => spec.key === MODE_KEY);

  const say = notice();
  const results = el('div', {});
  const compared = notice();
  const comparer = compareCard(rows, results, compared);

  const look = payload.last_look;
  const state = el('div', { class: 'bar' }, [
    modeSpec ? modeSwitch(modeSpec, { say, label: 'Structure backup', onSaved: () => refresh() }).node : null,
    payload.mode === 'off' ? null : button('Take one now', async () => {
      const done = await run(say, () => send('/api/structure/snapshots', 'POST', {}), (found) => found.message);
      if (done.ok) refresh();
    }, { small: false }),
    look ? badge(`last look ${when(look.at)} · ${look.outcome}`, OUTCOME_TONES[look.outcome] || null) : null,
    await noticeBadge(payload.mode, specs),
  ]);
  const why = look && look.outcome === 'failed' && look.reason ? notice(look.reason, 'danger') : null;

  const list = table([
    { label: '#', cell: (row) => `#${row.id}`, className: 'mono' },
    { label: 'Taken', cell: (row) => when(row.taken_at), className: 'mono' },
    { label: 'By', cell: takenBy },
    { label: 'Roles', key: 'roles' },
    { label: 'Categories', key: 'categories' },
    { label: 'Channels', key: 'channels' },
    { label: 'Overwrites', key: 'overwrites' },
    { label: 'Unchanged since', cell: lastSeen, className: 'mono' },
    {
      label: '',
      cell: (row) => bar([
        button('What changed since', () => {
          document.getElementById('sect-compare')?.querySelector('details')?.setAttribute('open', '');
          return comparer.compare(row.id, NOW);
        }),
        button('Download', () => download(row, say), { tone: 'quiet' }),
      ]),
    },
  ], rows, { empty: 'No snapshot has been taken yet.' });

  const one = section('Snapshots', null, { count: rows.length, open: true });
  one.body.append(state, say, ...[why].filter(Boolean), list);

  const two = section('Compare', null, { id: 'compare', open: rows.length > 0 });
  two.body.append(...(rows.length ? [comparer.node, compared, results] : [sayNothing('There is nothing to compare until a snapshot exists.')]));

  const operational = specs.filter((spec) => OPERATIONAL.includes(spec.key));
  const wording = specs.filter((spec) => spec.key !== MODE_KEY && !OPERATIONAL.includes(spec.key));
  const three = section('Settings', null, { count: operational.length + wording.length });
  three.body.append(
    await settingsPanel(operational, { where: 'Settings' }),
    foldout('Wording', [await settingsPanel(wording, { where: 'Wording' })], { count: wording.length }),
  );

  const logged = await logRows();
  const four = section('Logs', null, { count: logged.length });
  four.body.append(logsTable(logged, 'Structure backup has logged nothing yet.'));

  document.getElementById('dash').replaceChildren(one.node, two.node, three.node, four.node);
}

refresh = start({
  tab: 'structure',
  load,
});
