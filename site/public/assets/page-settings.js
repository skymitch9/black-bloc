import { settings } from './api.js';
import { start } from './app.js';
import { el, sayNothing, section, settingsPanel } from './ui.js';

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

async function load() {
  const payload = await settings(true);
  const namespaces = order(payload);
  const target = document.getElementById('dash');

  if (namespaces.length === 0) {
    target.replaceChildren(sayNothing('The bot reports no settings at all, which means it could not read its own registry.'));
    return;
  }

  const nodes = [];
  for (const namespace of namespaces) {
    const specs = payload[namespace];
    const group = section(namespace, NAMESPACE_NOTES[namespace] || null);
    group.body.append(await settingsPanel(specs, {
      empty: `Nothing is registered under ${namespace}.`,
    }));
    nodes.push(group.node);
  }

  target.replaceChildren(
    el('p', { class: 'section-note', text: 'Every change goes through the same store the slash commands write to, is recorded on the Audit tab, and the bot picks it up straight away.' }),
    ...nodes,
  );
}

start({
  tab: 'settings',
  subtitle: 'Every key the bot reads, grouped the way the slash commands group them.',
  load,
});
