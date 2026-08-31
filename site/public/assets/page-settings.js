import { settings } from './api.js';
import { start } from './app.js';
import { syncSubnav } from './layout.js';
import { logsSection } from './logs.js';
import { JUMP } from './palette.js';
import { el, keysSwitch, sayNothing, searchField, section, settingsEditor } from './ui.js';

const FIRST = 'core';
const FLASH_MS = 2400;

const CORE_LOGS_NOTE = 'Everything done from this dashboard and every settings change, ' +
  'whoever made it. Settings changes are routine — nothing here acts on a member — so switch ' +
  'to All to see them.';

const NAMESPACE_NOTES = {
  core: 'staff_channel_id is what decides who may see this dashboard.',
  automod: 'automod_rules has its own editor on the Automod tab; the JSON box here is the fallback.',
};

const NAMESPACE_NAMES = {
  core: 'The basics',
  mod: 'Moderation',
  automod: 'Automod',
  honeypot: 'Honeypot',
  modmail: 'Modmail',
  golive: 'Go-live',
  events: 'Events',
  birthday: 'Birthdays',
  tempvoice: 'Temp voice',
  rolemenu: 'Role menus',
  poll: 'Polls',
  chat: 'Chat',
  request: 'Requests',
};

const named = (namespace) => NAMESPACE_NAMES[namespace]
  || String(namespace).replace(/^./, (c) => c.toUpperCase());

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

/**
 * The command palette and a /settings.html#key link both land here: open the
 * group the row is in, take the page to it, and flash it so the eye finds it.
 */
function jumpToKey() {
  const key = decodeURIComponent(String(location.hash || '').replace(/^#/, ''));
  if (!key) return;
  const row = document.querySelector(`.setrow[data-key="${CSS.escape(key)}"]`);
  if (!row) return;
  const details = row.closest('details.sect-card');
  if (details) details.open = true;
  // `auto`, not `smooth`: a smooth scroll started while the page is still
  // settling is cancelled by the next layout and the row is never reached.
  row.scrollIntoView({ behavior: 'auto', block: 'center' });
  row.setAttribute('data-found', 'true');
  setTimeout(() => row.removeAttribute('data-found'), FLASH_MS);
}

window.addEventListener('hashchange', jumpToKey);
document.addEventListener(JUMP, jumpToKey);

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
    const group = section(named(namespace), NAMESPACE_NOTES[namespace] || null, { count: rows.length, id: namespace });
    group.details.querySelector('.sect-inner').classList.add('flush');
    group.body.append(...rows.map((spec) => byKey.get(spec.key).node));
    return { node: group.node, count: group.count, size: rows.length };
  });

  const filter = filterBox(groups, specs.length);
  if (aside) aside.replaceChildren(filter.box, filter.said, keysSwitch());

  target.replaceChildren(
    el('p', {
      class: 'section-note',
      text: 'The ⌫ beside a row puts it back to its default; nothing is written until you press ' +
        'Save Changes. Show keys puts each setting’s raw name back under it.',
    }),
    share(groups),
    await logsSection('core', { title: 'Logs', note: CORE_LOGS_NOTE }),
  );
  // After mountSections has applied the remembered open/closed state and
  // mountColumns has moved the blocks — otherwise the group is shut again
  // under the jump and the scroll lands nowhere.
  setTimeout(jumpToKey, 0);
}

start({ tab: 'settings', load });
