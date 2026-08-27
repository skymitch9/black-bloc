import { api, listOf, names, notesOf } from './api.js';
import { FEATURE_TABS, start, tabHref } from './app.js';
import { el, idsIn, modeChip, nameNode, sayNothing, section, table, when } from './ui.js';

const COUNT_LABELS = {
  role_menus_posted: 'Role menus posted',
  temp_channels: 'Temp voice channels open',
  honeypot_hits_7d: 'Honeypot hits, 7 days',
  open_events: 'Events open',
  open_modmail: 'Modmail tickets open',
};

function title(feature) {
  return String(feature).replace(/^./, (c) => c.toUpperCase());
}

function modes(status) {
  const chips = (status.features || []).map((feature) => {
    const tab = FEATURE_TABS[feature.feature];
    const chip = el(tab ? 'a' : 'span', {
      class: 'chip',
      href: tab ? tabHref(tab) : undefined,
    }, [
      el('span', { text: title(feature.feature) }),
      modeChip(feature.mode),
    ]);
    return chip;
  });
  return chips.length ? el('div', { class: 'chipgrid' }, chips) : sayNothing('No feature reports a mode yet.');
}

function counts(status) {
  if (!status.open) {
    return sayNothing('The open counts could not be read, so they are left blank rather than shown as zero.');
  }
  const tiles = Object.entries(COUNT_LABELS)
    .filter(([key]) => key in status.open)
    .map(([key, label]) => el('div', { class: 'tile' }, [
      el('div', { class: 'tile-value', text: String(status.open[key]) }),
      el('div', { class: 'tile-label', text: label }),
    ]));
  return tiles.length ? el('div', { class: 'tiles' }, tiles) : sayNothing('Nothing is open.');
}

function actionRows(rows) {
  return table([
    { label: 'When', cell: (row) => when(row.at), className: 'mono' },
    { label: 'What', cell: (row) => el('span', { class: 'kind', text: row.kind }) },
    { label: 'Who', cell: (row) => nameNode(row.actor_id, row.actor_name) },
    { label: 'Target', cell: (row) => nameNode(row.target_id, row.target_name) },
    { label: 'Why', cell: (row) => row.reason, className: 'wrap' },
  ], rows, { empty: 'Black Bloc has not logged anything yet.' });
}

async function load() {
  const [status, actions] = await Promise.all([
    api('/api/status'),
    api('/api/actions?limit=10'),
  ]);
  const rows = listOf(actions, 'actions');
  await names(idsIn(rows, ['actor_id', 'target_id']));

  const notes = notesOf(status).concat(notesOf(actions));
  const feature = section('Modes', 'Click one to open the tab that changes it.');
  feature.body.append(modes(status));

  const open = section('Open now');
  open.body.append(counts(status));

  const recent = section('Last 10 actions');
  recent.body.append(actionRows(rows));

  document.getElementById('dash').replaceChildren(
    ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
    feature.node,
    open.node,
    recent.node,
  );
}

start({
  tab: 'overview',
  subtitle: 'Every feature’s mode, what is open, and the last ten things the bot did.',
  load,
});
