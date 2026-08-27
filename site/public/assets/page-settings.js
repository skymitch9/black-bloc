import { settings } from './api.js';
import { start } from './app.js';
import { syncSubnav } from './layout.js';
import { el, sayNothing, searchBox, section, settingsPanel } from './ui.js';

const FIRST = 'core';

const NAMESPACE_NOTES = {
  core: 'The channels the whole bot leans on. staff_channel_id is also what decides who may see this dashboard.',
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

function filterBar(groups) {
  const said = el('span', { class: 'table-count' });
  const paint = (query) => {
    let keys = 0;
    let shown = 0;
    for (const group of groups) {
      let here = 0;
      for (const row of group.node.querySelectorAll('.setting')) {
        keys += 1;
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
    said.textContent = query === '' ? `${keys} key(s)` : `${shown} of ${keys} key(s)`;
    syncSubnav();
  };
  const input = searchBox({
    label: 'Filter settings',
    placeholder: 'part of a key, a type or its help — e.g. channel, mode, birthday',
    onQuery: paint,
  });
  paint('');
  return el('div', { class: 'filter-bar' }, [input, said]);
}

async function load() {
  const payload = await settings(true);
  const namespaces = order(payload);
  const target = document.getElementById('dash');

  if (namespaces.length === 0) {
    target.replaceChildren(sayNothing('The bot reports no settings at all, which means it could not read its own registry.'));
    return;
  }

  const groups = [];
  for (const namespace of namespaces) {
    const specs = payload[namespace];
    const group = section(namespace, NAMESPACE_NOTES[namespace] || null, { count: specs.length });
    group.body.append(await settingsPanel(specs, {
      empty: `Nothing is registered under ${namespace}.`,
    }));
    groups.push(group);
  }

  target.replaceChildren(
    el('p', { class: 'section-note', text: 'Every change goes through the same store the slash commands write to, is recorded on the Audit tab, and the bot picks it up straight away.' }),
    filterBar(groups),
    ...groups.map((group) => group.node),
  );
}

start({
  tab: 'settings',
  subtitle: 'Every key the bot reads, grouped the way the slash commands group them.',
  load,
});
