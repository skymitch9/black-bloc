import { api, listOf, names, notesOf } from './api.js';
import { start } from './app.js';
import { bar, button, el, field, idsIn, looksLikeId, nameNode, section, table, valueNode, when } from './ui.js';

const WEB = 'web.';

let kindFilter = '';

function idsInValues(rows) {
  const found = [];
  for (const row of rows) {
    const value = row?.value;
    for (const item of Array.isArray(value) ? value : [value]) {
      if (looksLikeId(String(item ?? ''))) found.push(String(item));
    }
  }
  return found;
}

function settingsTable(rows) {
  return table([
    { label: 'When', cell: (row) => when(row.updated_at || row.at), className: 'mono' },
    { label: 'Key', cell: (row) => el('span', { class: 'mono', text: row.key }) },
    { label: 'Value', cell: (row) => valueNode(row.value), className: 'wrap' },
    { label: 'By', cell: (row) => nameNode(row.updated_by || row.by, row.updated_by_name || row.by_name) },
  ], rows, { empty: 'No setting has been changed yet.' });
}

function actionsTable(rows) {
  return table([
    { label: 'When', cell: (row) => when(row.at), className: 'mono' },
    { label: 'What', cell: (row) => el('span', { class: 'kind', text: row.kind }) },
    { label: 'Who', cell: (row) => nameNode(row.actor_id, row.actor_name) },
    { label: 'Target', cell: (row) => nameNode(row.target_id, row.target_name) },
    { label: 'Why', cell: (row) => row.reason, className: 'wrap' },
  ], rows, { empty: 'Nothing has been done from this dashboard yet.' });
}

let refresh = () => {};

async function load() {
  const query = kindFilter ? `&kind=${encodeURIComponent(kindFilter)}` : '';
  const [audit, actions] = await Promise.all([
    api('/api/settings/audit?limit=100'),
    api(`/api/actions?limit=200${query}`),
  ]);

  const auditRows = listOf(audit, 'audit');
  const allActions = listOf(actions, 'actions');
  const actionRows = kindFilter ? allActions : allActions.filter((row) => String(row.kind || '').startsWith(WEB));

  await names(idsIn(auditRows, ['updated_by', 'by'])
    .concat(idsInValues(auditRows))
    .concat(idsIn(allActions, ['actor_id', 'target_id'])));

  const kind = el('input', { class: 'input', type: 'text', value: kindFilter, placeholder: 'web. or automod.timeout' });
  const apply = button('Filter', () => {
    kindFilter = kind.value.trim();
    refresh();
  });
  const clear = button('Only this dashboard', () => {
    kindFilter = '';
    refresh();
  }, { tone: 'quiet' });

  const one = section('Settings audit', 'Every settings change, whoever made it and however they made it.');
  one.body.append(settingsTable(auditRows));

  const two = section(
    kindFilter ? `Actions matching ${kindFilter}` : 'Actions taken from this dashboard',
    kindFilter
      ? 'Filtered by the kind you typed; the bot decides how loosely that matches.'
      : 'Web writes log a web.* kind, so the log tells a dashboard change apart from a slash command.',
  );
  two.body.append(
    el('div', { class: 'formrow' }, [field('Action kind', kind), bar([apply, clear])]),
    actionsTable(actionRows),
  );

  const notes = notesOf(audit).concat(notesOf(actions));
  document.getElementById('dash').replaceChildren(
    ...(notes.length ? [el('p', { class: 'section-note', text: notes.join(' ') })] : []),
    one.node,
    two.node,
  );
}

refresh = start({
  tab: 'audit',
  subtitle: 'Who changed which setting, and everything done from this dashboard.',
  load,
});
