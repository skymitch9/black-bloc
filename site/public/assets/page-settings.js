import { settings } from './api.js';
import { start } from './app.js';
import { syncSubnav } from './layout.js';
import { logsSection } from './logs.js';
import { el, sayNothing, searchField, section, settingsEditor } from './ui.js';

const FIRST = 'core';

const CORE_LOGS_NOTE = 'Everything done from this dashboard and every settings change, ' +
  'whoever made it. Settings changes are routine — nothing here acts on a member — so switch ' +
  'to All to see them.';

const NAMESPACE_NOTES = {
  core: 'staff_channel_id is what decides who may see this dashboard.',
  automod: 'automod_rules has its own editor on the Automod tab; the JSON box here is the fallback.',
};

function order(payload) {
  const found = Object.keys(payload || {}).filter((key) => Array.isArray(payload[key]));
  found.sort((a, b) => {
    if (a === FIRST) return -1;
    if (b === FIRST) return 1;
    return a.localeCompare(b);
  });
  return found;
}

/** Two columns of roughly equal height, the way the mock lays them out. */
function share(groups) {
  const left = [];
  const right = [];
  let leftRows = 0;
  let rightRows = 0;
  for (const group of groups) {
    if (leftRows <= rightRows) {
      left.push(group.node);
      leftRows += group.size;
    } else {
      right.push(group.node);
      rightRows += group.size;
    }
  }
  return el('div', { class: 'twocol' }, [
    el('div', { class: 'colstack' }, left),
    el('div', { class: 'colstack' }, right),
  ]);
}

function filterBox(groups, keys) {
  const said = el('span', { class: 'table-count' });
  const paint = (query) => {
    let shown = 0;
    for (const group of groups) {
      let here = 0;
      for (const row of group.node.querySelectorAll('.setrow')) {
        const hit = query === '' || (row.getAttribute('data-search') || '').includes(query);
        row.hidden = !hit;
        if (hit) here += 1;
      }
      shown += here;
      group.node.hidden = query !== '' && here === 0;
      group.count(here);
      const details = group.node.querySelector('details.sect-card');
      if (details && query !== '') details.open = here > 0;
    }
    said.textContent = query === ''
      ? `${keys} keys · ${groups.length} groups`
      : `${shown} of ${keys} keys`;
    syncSubnav();
  };
  const box = searchField({
    label: 'Filter settings',
    placeholder: `Filter ${keys} keys…`,
    onQuery: paint,
  });
  paint('');
  return { box, said };
}

async function load() {
  const payload = await settings(true);
  const namespaces = order(payload);
  const target = document.getElementById('dash');
  const aside = document.getElementById('page-aside');

  if (namespaces.length === 0) {
    if (aside) aside.replaceChildren();
    target.replaceChildren(sayNothing('The bot reports no settings at all, which means it could not read its own registry.'));
    return;
  }

  const specs = namespaces.flatMap((namespace) => payload[namespace]);
  const editor = await settingsEditor(specs);
  const byKey = new Map(editor.rows.map((row) => [row.key, row]));

  const groups = namespaces.map((namespace) => {
    const rows = payload[namespace];
    const group = section(namespace, NAMESPACE_NOTES[namespace] || null, { count: rows.length });
    group.details.querySelector('.sect-inner').classList.add('flush');
    group.body.append(...rows.map((spec) => byKey.get(spec.key).node));
    return { node: group.node, count: group.count, size: rows.length };
  });

  const filter = filterBox(groups, specs.length);
  if (aside) aside.replaceChildren(filter.box, filter.said);

  editor.bar.classList.add('dock');
  target.replaceChildren(
    el('p', {
      class: 'section-note',
      text: 'Emptying a row puts it back to its default.',
    }),
    share(groups),
    editor.bar,
    await logsSection('core', { title: 'Logs', note: CORE_LOGS_NOTE }),
  );
}

start({ tab: 'settings', load });
